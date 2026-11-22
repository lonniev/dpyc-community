#!/usr/bin/env python3
"""Index a Python package's code Symbols into the factory graph, from the code outward.

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

LANG = "python"


@dataclass(frozen=True)
class Definition:
    """One definition found in the code: its dotted import path and the file it lives in."""
    path: str        # e.g. tollbooth.runtime.OperatorRuntime.debit_or_deny
    file_path: str   # repo-relative, e.g. src/tollbooth/runtime.py
    kind: str        # "class" | "function" | "name"


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
# Comparing with the graph (pure, unit-tested)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Outcome:
    fqn: str
    verdict: str          # new | moved | unanchored | ok | gone | malformed
    file_path: str | None = None
    was: str | None = None


def compare(repo: str, index: PackageIndex, public: dict[str, Definition],
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
        d = index.defs.get(fqn.partition(":")[2])
        if d is None:
            outcomes.append(Outcome(fqn, "gone", was=file))
        elif not file:
            outcomes.append(Outcome(fqn, "unanchored", d.file_path))
        elif file != d.file_path:
            outcomes.append(Outcome(fqn, "moved", d.file_path, was=file))
        else:
            outcomes.append(Outcome(fqn, "ok", d.file_path))

    for path, d in sorted(public.items()):
        fqn = f"{repo}:{path}"
        if fqn not in in_graph:
            outcomes.append(Outcome(check_symbol_fqn(fqn), "new", d.file_path))
    return outcomes


def plan(repo: str, sha: str, outcomes: list[Outcome]) -> list[Call]:
    calls: list[Call] = []
    for o in outcomes:
        if o.verdict == "new":
            calls.append(_call("index_symbol", repo_name=repo, symbol_fqn=o.fqn, lang=LANG))
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
    ap.add_argument("--src", default="src", help="source root inside the repo")
    ap.add_argument("--package", default="", help="top-level package (default: repo's, "
                    "e.g. tollbooth-dpyc -> tollbooth)")
    ap.add_argument("--extra-module", action="append", default=[],
                    help="a module imported directly by the fleet but not re-exported from "
                         "__init__ (repeatable), e.g. tollbooth.holder_auth")
    ap.add_argument("--graph-rows", type=Path,
                    help="offline: a JSON file of symbols_in_service rows instead of a live read")
    ap.add_argument("--url", default=os.environ.get("CYPHER_MCP_URL",
                                                    "https://cypher-mcp.fastmcp.app/mcp"))
    ap.add_argument("--dry-run", action="store_true", help="report and print the plan; no writes")
    args = ap.parse_args()

    root = args.root.expanduser().resolve()
    package = args.package or args.repo.split("-")[0]
    index = index_package(root, args.src, package)
    public = public_api(index, package, tuple(args.extra_module))
    if not public:
        print(f"  ! {package}/__init__.py has no __all__; nothing public to index",
              file=sys.stderr)

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

    outcomes = compare(args.repo, index, public, rows)
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
