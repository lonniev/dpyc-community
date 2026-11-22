#!/usr/bin/env python3
"""Index a package's code Symbols (Python or TypeScript) into the factory graph, from the code outward.

``symbol_audit.py`` reads the graph and asks whether each anchor still points at live code.
This is the other direction: read the CODE and bring the graph up to date with it. Together
they keep the graph's ``Symbol`` layer honest, so an agent that asks the graph "where is X"
gets a place that exists.

What it indexes — the PUBLIC API, never a blanket dump (``index_symbol``'s own rule):

  * every name in the package's ``__init__.__all__``, resolved through its import to the
    module that DEFINES it (``tollbooth.OperatorRuntime`` is ``tollbooth.runtime.OperatorRuntime``);
  * the public methods of every exported class (``OperatorRuntime.debit_or_deny``);
  * plus every Symbol the graph already holds for this repo, public or not, because someone
    anchored it on purpose.

How it reads the code: Python's own ``ast``, never a regex. Every def, class and module-level
name in the package is indexed — private ones too — so a graph Symbol that is not public can
still be found if it moved.

What it writes, per symbol, Journeyman-signed through the published templates:

    new       public in the code, absent from the graph   -> index_symbol + anchor_symbol
    moved     in both, but the graph's file_path is stale  -> anchor_symbol
    unanchored in both, the graph never recorded a file    -> anchor_symbol
    ok        in both, same file                           -> nothing
    gone      in the graph, nowhere in the code            -> REPORTED, never deleted

A gone symbol is never deleted: an authored ``why``, a ``GUARDS`` edge or an Issue's
``ROOT_CAUSE`` may hang off it, and only a human may decide what that history means now.

The graph must never gate a release, so a write failure is reported and the exit code says
so, but the caller runs this as advisory.

Usage:
    # preview, no network, no nsec:
    python scripts/symbol_index.py --repo tollbooth-dpyc --root ../tollbooth-dpyc --dry-run

    # live, Journeyman key from env:
    JOURNEYMAN_NSEC="$(cat <secure-file>)" \\
      python scripts/symbol_index.py --repo tollbooth-dpyc --root ../tollbooth-dpyc
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import json
import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from intention_harvest import (  # the shared naming doctrine and the signed-call driver
    JOURNEYMAN,
    SLUG,
    Call,
    RoleKey,
    _apply,
    _call,
    _print_plan,
    check_symbol_fqn,
    npub_from_nsec,
)


@dataclass(frozen=True)
class Definition:
    """One definition found in the code: the part of its fqn after ``<repo>:``, and its file."""
    path: str        # tollbooth.runtime.OperatorRuntime.debit_or_deny | holder#holderEnabled
    file_path: str   # repo-relative, e.g. src/tollbooth/runtime.py
    kind: str        # "class" | "function" | "name"
    lang: str = "python"


# --------------------------------------------------------------------------- #
# Reading the code (pure, unit-tested)
# --------------------------------------------------------------------------- #

def module_path(file: Path, src_root: Path) -> str:
    """``src/tollbooth/runtime.py`` under ``src`` -> ``tollbooth.runtime``; a package's
    ``__init__.py`` is the package itself."""
    parts = list(file.relative_to(src_root).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _assigned_names(node: ast.stmt) -> list[str]:
    if isinstance(node, ast.Assign):
        return [t.id for t in node.targets if isinstance(t, ast.Name)]
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [node.target.id]
    return []


def definitions_in(tree: ast.Module, module: str, file_path: str) -> list[Definition]:
    """Every module-level def/class/name, and every def/class nested in a class.

    Functions nested inside functions are not addressable by import, so they are skipped.
    """
    out: list[Definition] = []

    def walk_class(cls: ast.ClassDef, prefix: str) -> None:
        for node in cls.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out.append(Definition(f"{prefix}.{node.name}", file_path, "function"))
            elif isinstance(node, ast.ClassDef):
                out.append(Definition(f"{prefix}.{node.name}", file_path, "class"))
                walk_class(node, f"{prefix}.{node.name}")

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append(Definition(f"{module}.{node.name}", file_path, "function"))
        elif isinstance(node, ast.ClassDef):
            out.append(Definition(f"{module}.{node.name}", file_path, "class"))
            walk_class(node, f"{module}.{node.name}")
        else:
            for name in _assigned_names(node):
                out.append(Definition(f"{module}.{name}", file_path, "name"))
    return out


def imports_in(tree: ast.Module, module: str, is_package: bool) -> dict[str, str]:
    """Module-level ``from X import a as b`` -> {"b": "X.a"}, relative imports resolved.

    ``from .x import y`` is relative to the package a module sits in, which for an
    ``__init__.py`` is the module itself — hence ``is_package``.
    """
    out: dict[str, str] = {}
    pkg = module.split(".")
    here = pkg if is_package else pkg[:-1]
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        base = node.module or ""
        if node.level:
            anchor = here[: len(here) - (node.level - 1)]
            base = ".".join([*anchor, base] if base else anchor)
        for alias in node.names:
            if alias.name != "*":
                out[alias.asname or alias.name] = f"{base}.{alias.name}"
    return out


def dunder_all(tree: ast.Module) -> list[str]:
    """The literal ``__all__`` list or tuple, or [] if there is none."""
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and "__all__" in _assigned_names(node):
            value = node.value
            if isinstance(value, (ast.List, ast.Tuple)):
                return [e.value for e in value.elts
                        if isinstance(e, ast.Constant) and isinstance(e.value, str)]
    return []


@dataclass
class PackageIndex:
    """Everything defined in a package, plus each module's imports, for resolving re-exports."""
    defs: dict[str, Definition]
    imports: dict[str, dict[str, str]]   # module -> {local name -> imported dotted path}
    trees: dict[str, ast.Module]

    def resolve(self, dotted: str, _depth: int = 0) -> Definition | None:
        """Follow re-exports until the dotted path lands on a real definition."""
        if dotted in self.defs:
            return self.defs[dotted]
        if _depth > 10:
            return None
        module, _, name = dotted.rpartition(".")
        target = self.imports.get(module, {}).get(name)
        return self.resolve(target, _depth + 1) if target else None


def index_package(repo_root: Path, src: str, package: str) -> PackageIndex:
    src_root = repo_root / src
    defs: dict[str, Definition] = {}
    imports: dict[str, dict[str, str]] = {}
    trees: dict[str, ast.Module] = {}
    for file in sorted((src_root / package).rglob("*.py")):
        rel = file.relative_to(repo_root).as_posix()
        module = module_path(file, src_root)
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=rel)
        trees[module] = tree
        imports[module] = imports_in(tree, module, is_package=file.name == "__init__.py")
        for d in definitions_in(tree, module, rel):
            defs.setdefault(d.path, d)
    return PackageIndex(defs, imports, trees)


def _public(name: str) -> bool:
    return not name.startswith("_")


def public_api(index: PackageIndex, package: str,
               extra_modules: tuple[str, ...] = ()) -> dict[str, Definition]:
    """The package's public surface: ``__all__`` resolved to defining modules, plus the public
    methods (and nested classes) of every exported class.

    ``extra_modules`` adds every public top-level def/class of a module the fleet imports
    directly though ``__init__`` does not re-export it (``tollbooth.holder_auth``).
    """
    out: dict[str, Definition] = {}

    def add(d: Definition) -> None:
        out[d.path] = d
        if d.kind == "class":
            prefix = d.path + "."
            for path, member in index.defs.items():
                tail = path[len(prefix):] if path.startswith(prefix) else ""
                if tail and all(_public(p) for p in tail.split(".")):
                    out[path] = member

    tree = index.trees.get(package)
    for name in dunder_all(tree) if tree is not None else []:
        if not name.startswith("__") and (d := index.resolve(f"{package}.{name}")):
            add(d)
    for module in extra_modules:
        prefix = module + "."
        for path, d in list(index.defs.items()):
            tail = path[len(prefix):] if path.startswith(prefix) else ""
            if tail and "." not in tail and _public(tail) and d.kind != "name":
                add(d)
    return out


# --------------------------------------------------------------------------- #
# TypeScript (pure, unit-tested)
# --------------------------------------------------------------------------- #
# A TypeScript symbol's fqn is its module path under ``src/``, extension dropped, then ``#``
# and the name: ``tollbooth-web:holder#holderEnabled``, ``tollbooth-web:react/AccountPage#
# AccountPage``. The leading ``src/`` is dropped as it is for Python.
#
# Read with regexes over EXPORT statements and top-level declarations, not a compiler: the
# repo's TypeScript is 7 (the native compiler), which has no stable JS API to call. Exports
# are a small, regular grammar, and the patterns below are anchored at the start of a line,
# so a nested declaration is never mistaken for a top-level one.

TS_SUFFIXES = (".ts", ".tsx")
_TS_DECL = re.compile(
    r"^(export\s+)?(?:declare\s+)?(default\s+)?(?:abstract\s+)?(?:async\s+)?"
    r"(function\*?|class|const|let|var|interface|type|enum)\s+([A-Za-z_$][\w$]*)",
    re.MULTILINE)
_TS_EXPORT_LIST = re.compile(
    r"^export\s+(?:type\s+)?\{([^}]*)\}\s*(?:from\s*[\"']([^\"']+)[\"'])?",
    re.MULTILINE)
_TS_EXPORT_STAR = re.compile(r"^export\s+\*\s+from\s*[\"']([^\"']+)[\"']", re.MULTILINE)
_TS_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_TS_LINE_COMMENT = re.compile(r"^\s*//.*$", re.MULTILINE)
_TS_KIND = {"function": "function", "function*": "function", "class": "class"}


@dataclass
class TsModule:
    file_path: str                                  # repo-relative
    decls: dict[str, tuple[str, bool]]              # name -> (kind, exported)
    reexports: dict[str, tuple[str | None, str]]    # exported name -> (from file | None, local name)
    stars: list[str]                                # files re-exported with `export *`
    default_name: str | None = None                 # `export default function X` -> "X"


def ts_module_path(file_path: str) -> str:
    """``src/react/AccountPage.tsx`` -> ``react/AccountPage``."""
    p = file_path.removeprefix("src/")
    for suffix in TS_SUFFIXES:
        if p.endswith(suffix):
            return p[: -len(suffix)]
    return p


def _ts_resolve_spec(spec: str, from_file: str, files: set[str]) -> str | None:
    """A relative import specifier -> the repo-relative file it names, if it is in ``files``."""
    if not spec.startswith("."):
        return None  # a package import is not this repo's symbol
    # normpath, never Path(): pathlib keeps "..", so src/react/../holder.ts matched nothing
    base = os.path.normpath((Path(from_file).parent / spec).as_posix())
    stem = re.sub(r"\.(?:js|jsx|ts|tsx)$", "", base)
    for cand in (base, *(stem + s for s in TS_SUFFIXES),
                 *(f"{stem}/index{s}" for s in TS_SUFFIXES)):
        if cand in files:
            return cand
    return None


def parse_ts_module(text: str, file_path: str, files: set[str]) -> TsModule:
    text = _TS_LINE_COMMENT.sub("", _TS_BLOCK_COMMENT.sub("", text))
    decls: dict[str, tuple[str, bool]] = {}
    default_name: str | None = None
    for m in _TS_DECL.finditer(text):
        decls.setdefault(m.group(4), (_TS_KIND.get(m.group(3), "name"), bool(m.group(1))))
        if m.group(1) and m.group(2):
            default_name = m.group(4)
    reexports: dict[str, tuple[str | None, str]] = {}
    for m in _TS_EXPORT_LIST.finditer(text):
        source = _ts_resolve_spec(m.group(2), file_path, files) if m.group(2) else None
        if m.group(2) and source is None:
            continue  # re-exported from a package: not this repo's symbol
        for item in m.group(1).split(","):
            item = re.sub(r"^\s*type\s+", "", item).strip()
            if not item:
                continue
            local, _, exported = (p.strip() for p in item.partition(" as "))
            reexports[exported or local] = (source, local)
    stars = [f for spec in _TS_EXPORT_STAR.findall(text)
             if (f := _ts_resolve_spec(spec, file_path, files))]
    return TsModule(file_path, decls, reexports, stars, default_name)


def ts_index(repo_root: Path, src: str = "src") -> dict[str, TsModule]:
    """Every .ts/.tsx module under ``src``, tests and declaration files excluded."""
    files = sorted(
        p.relative_to(repo_root).as_posix() for p in (repo_root / src).rglob("*")
        if p.suffix in TS_SUFFIXES and not p.name.endswith(".d.ts")
        and ".test." not in p.name and ".spec." not in p.name)
    known = set(files)
    return {f: parse_ts_module((repo_root / f).read_text(encoding="utf-8"), f, known)
            for f in files}


def ts_definitions(modules: dict[str, TsModule]) -> dict[str, Definition]:
    """Every top-level declaration, exported or not, keyed by its fqn body."""
    out: dict[str, Definition] = {}
    for f, mod in modules.items():
        for name, (kind, _exported) in mod.decls.items():
            path = f"{ts_module_path(f)}#{name}"
            out[path] = Definition(path, f, kind, "typescript")
    return out


def _ts_resolve(modules: dict[str, TsModule], file: str, name: str,
                depth: int = 0) -> Definition | None:
    """Where is the export ``name`` of ``file`` actually declared?"""
    mod = modules.get(file)
    if mod is None or depth > 20:
        return None
    if name == "default" and mod.default_name:
        name = mod.default_name
    if name in mod.decls and mod.decls[name][1]:
        kind = mod.decls[name][0]
        return Definition(f"{ts_module_path(file)}#{name}", file, kind, "typescript")
    if name in mod.reexports:
        source, local = mod.reexports[name]
        if source is None:  # `export { local as name }` of a local declaration
            if local in mod.decls:
                return Definition(f"{ts_module_path(file)}#{local}", file,
                                  mod.decls[local][0], "typescript")
            return None
        return _ts_resolve(modules, source, local, depth + 1)
    for star in mod.stars:
        if (d := _ts_resolve(modules, star, name, depth + 1)):
            return d
    return None


def _ts_exported_names(modules: dict[str, TsModule], file: str,
                       seen: frozenset[str] = frozenset()) -> set[str]:
    mod = modules.get(file)
    if mod is None or file in seen:
        return set()
    names = {n for n, (_k, exported) in mod.decls.items() if exported}
    names |= set(mod.reexports)
    for star in mod.stars:
        names |= _ts_exported_names(modules, star, seen | {file})
    names.discard("default")
    return names


def ts_entry_points(repo_root: Path, src: str = "src") -> list[str]:
    """The source files behind package.json ``exports`` (``./dist/x.js`` -> ``src/x.ts``)."""
    pkg = json.loads((repo_root / "package.json").read_text())
    exports = pkg.get("exports") or {}
    targets: list[str] = []
    for value in (exports.values() if isinstance(exports, dict) else [exports]):
        target = value.get("default") or value.get("import") if isinstance(value, dict) else value
        if isinstance(target, str) and target.endswith(".js"):
            targets.append(target)
    out: list[str] = []
    for t in targets:
        stem = re.sub(r"^\./(?:dist|build|lib)/", f"{src}/", t)[: -len(".js")]
        for suffix in TS_SUFFIXES:
            if (repo_root / (stem + suffix)).is_file():
                out.append(stem + suffix)
                break
    return out


def ts_public_api(modules: dict[str, TsModule], entries: list[str]) -> dict[str, Definition]:
    out: dict[str, Definition] = {}
    for entry in entries:
        for name in sorted(_ts_exported_names(modules, entry)):
            if (d := _ts_resolve(modules, entry, name)):
                out[d.path] = d
    return out


# --------------------------------------------------------------------------- #
# Comparing with the graph (pure, unit-tested)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Outcome:
    fqn: str
    verdict: str          # new | moved | unanchored | ok | gone | malformed
    file_path: str | None = None
    was: str | None = None
    lang: str = "python"


def compare(repo: str, defs: dict[str, Definition], public: dict[str, Definition],
            graph_rows: list[dict[str, Any]]) -> list[Outcome]:
    """Sort every symbol into a verdict. Graph rows are ``symbols_in_service`` rows:
    ``{"symbol": fqn, "lang": ..., "file": ...}``."""
    outcomes: list[Outcome] = []
    in_graph: dict[str, str | None] = {}
    for row in graph_rows:
        fqn = row.get("symbol") or row.get("fqn") or ""
        if fqn and fqn not in in_graph:
            in_graph[fqn] = row.get("file")

    for fqn, file in sorted(in_graph.items()):
        try:
            check_symbol_fqn(fqn)
        except ValueError:
            outcomes.append(Outcome(fqn, "malformed", was=file))
            continue
        if not fqn.startswith(f"{repo}:"):
            continue  # IN_SERVICE to this repo but named for another: not ours to judge
        d = defs.get(fqn.partition(":")[2])
        if d is None:
            outcomes.append(Outcome(fqn, "gone", was=file))
        elif not file:
            outcomes.append(Outcome(fqn, "unanchored", d.file_path, lang=d.lang))
        elif file != d.file_path:
            outcomes.append(Outcome(fqn, "moved", d.file_path, was=file, lang=d.lang))
        else:
            outcomes.append(Outcome(fqn, "ok", d.file_path, lang=d.lang))

    for path, d in sorted(public.items()):
        fqn = f"{repo}:{path}"
        if fqn not in in_graph:
            outcomes.append(Outcome(check_symbol_fqn(fqn), "new", d.file_path, lang=d.lang))
    return outcomes


def plan(repo: str, sha: str, outcomes: list[Outcome]) -> list[Call]:
    calls: list[Call] = []
    for o in outcomes:
        if o.verdict == "new":
            calls.append(_call("index_symbol", repo_name=repo, symbol_fqn=o.fqn, lang=o.lang))
        if o.verdict in ("new", "moved", "unanchored"):
            calls.append(_call("anchor_symbol", symbol_fqn=o.fqn, file_path=o.file_path,
                               verified_at_sha=sha))
    return calls


def format_report(repo: str, outcomes: list[Outcome]) -> str:
    counts = Counter(o.verdict for o in outcomes)
    order = ("new", "moved", "unanchored", "ok", "gone", "malformed")
    lines = [f"{repo}: " + " · ".join(f"{counts[v]} {v}" for v in order if counts.get(v))]
    for o in outcomes:
        if o.verdict == "moved":
            lines.append(f"  [moved] {o.fqn}  {o.was} -> {o.file_path}")
        elif o.verdict in ("gone", "malformed"):
            lines.append(f"  [{o.verdict}] {o.fqn}" + (f"  (was {o.was})" if o.was else ""))
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Driver (live)
# --------------------------------------------------------------------------- #

async def _graph_rows(url: str, repo: str, key: RoleKey) -> list[dict[str, Any]]:
    from tollbooth.mcp_client import service_client

    async with service_client(url, key.nsec) as client:
        res = await client.call_tool(f"{SLUG}_symbols_in_service",
                                     {"repo_name": repo, "npub": key.npub})
    data = res.data if hasattr(res, "data") else res
    if not isinstance(data, dict) or not data.get("success", True) or data.get("error"):
        raise RuntimeError(f"symbols_in_service failed: {data!r}"[:300])
    if data.get("truncated"):
        # Benign for correctness: a row cut off can only make a public symbol look new, and
        # index/anchor MERGE, so re-writing it is idempotent. Gone is judged on rows we saw.
        print("  ! graph listing truncated; some 'new' may already exist", file=sys.stderr)
    return list(data.get("rows") or [])


def head_sha(root: Path) -> str:
    return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
                          capture_output=True, text=True).stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="repo slug, e.g. tollbooth-dpyc")
    ap.add_argument("--root", required=True, type=Path, help="that repo's checkout")
    ap.add_argument("--lang", choices=["python", "typescript"], default="python")
    ap.add_argument("--src", default="src", help="source root inside the repo")
    ap.add_argument("--package", default="", help="top-level package (default: repo's, "
                    "e.g. tollbooth-dpyc -> tollbooth)")
    ap.add_argument("--extra-module", action="append", default=[],
                    help="a module that holds public symbols though no entry point re-exports "
                         "it (repeatable): tollbooth.holder_auth (Python), holder (TypeScript)")
    ap.add_argument("--graph-rows", type=Path,
                    help="offline: a JSON file of symbols_in_service rows instead of a live read")
    ap.add_argument("--url", default=os.environ.get("CYPHER_MCP_URL",
                                                    "https://cypher-mcp.fastmcp.app/mcp"))
    ap.add_argument("--dry-run", action="store_true", help="report and print the plan; no writes")
    args = ap.parse_args()

    root = args.root.expanduser().resolve()
    if args.lang == "typescript":
        modules = ts_index(root, args.src)
        defs = ts_definitions(modules)
        entries = ts_entry_points(root, args.src)
        for extra in args.extra_module:  # e.g. "holder" -> src/holder.ts
            entries += [f for f in modules if ts_module_path(f) == extra]
        public = ts_public_api(modules, entries)
    else:
        package = args.package or args.repo.split("-")[0]
        index = index_package(root, args.src, package)
        defs = index.defs
        public = public_api(index, package, tuple(args.extra_module))
    if not public:
        print("  ! no public API found; nothing new to index", file=sys.stderr)

    nsec = os.environ.get("JOURNEYMAN_NSEC", "")
    key = RoleKey(npub_from_nsec(nsec), nsec)
    if args.graph_rows:
        rows = json.loads(args.graph_rows.read_text())
    elif key.nsec:
        rows = asyncio.run(_graph_rows(args.url, args.repo, key))
    else:
        print("  ! no JOURNEYMAN_NSEC and no --graph-rows: comparing against an empty graph",
              file=sys.stderr)
        rows = []

    outcomes = compare(args.repo, defs, public, rows)
    print(format_report(args.repo, outcomes))
    calls = plan(args.repo, head_sha(root), outcomes)
    if args.dry_run or not calls:
        _print_plan(calls)
        return 0
    if not key.nsec:
        print("  ! JOURNEYMAN_NSEC is not set; cannot write", file=sys.stderr)
        return 2
    return asyncio.run(_apply(args.url, calls, {JOURNEYMAN: key}))


if __name__ == "__main__":
    raise SystemExit(main())
