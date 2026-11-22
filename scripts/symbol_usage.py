#!/usr/bin/env python3
"""Observe which fleet repos use each SDK symbol, and mark the ones nothing uses.

``symbol_index.py`` keeps the graph's ``Symbol`` layer in step with the SDK's code. This
asks the next question: who USES each symbol? It reads every fleet repo's imports of the
SDK, counts the SDK's own references, and records the answer per symbol through the
Journeyman-only ``observe_symbol_usage`` template:

    CONSUMED_BY  -> one edge per fleet repo that imports the symbol
    usage        -> 'unused' when no fleet repo imports it AND the SDK never refers to it

This is an OBSERVATION, re-made every sweep, so a symbol that is used again clears itself.
Deciding that a symbol is obsolete is a human's call (``retire_symbol``); nothing here
retires, deletes or mints a Symbol. A symbol the graph does not hold yet is skipped: the
indexer adds it, and the next sweep observes it.

The fleet: every checkout under ``--consumers`` whose ``renovate.json`` extends the
dpyc-community preset, which is how a repo joins the fleet's dependency chain. The SDK's own
repo is never its own consumer; its references are counted as ``internal_refs``.

How a use is recognised:

  Python      ``from tollbooth.x import a``, ``import tollbooth.x as m`` then ``m.a``,
              re-exports followed to the defining module. A method counts as used in a repo
              that imports the SDK and calls ``.method`` or overrides it in a subclass.
  TypeScript  static ``import``/``export ... from "@tollbooth-dpyc/web[/sub]"``, namespace
              imports (``ns.name``) and dynamic ``import(...)`` (``m.name``, destructuring).

A consumer's tests ARE usage: removing the symbol breaks that repo's CI, and the SDK exports
helpers meant for exactly that (``lintTours``, ``localeProblems``). The SDK's own tests are
not: an SDK that only tests a symbol still has no use for it.

Every rule above errs toward "used": a false "used" hides dead code for a sweep, while a
false "unused" would ask a human to retire live code.

Only what changed is written: the graph's last observation comes back with
``symbols_in_service``, and a symbol is re-observed when its consumer set or its usage
flips. ``internal_refs`` is recorded as of the observing sha.

Usage:
    # preview against the local checkouts, no network, no nsec:
    python scripts/symbol_usage.py --repo tollbooth-dpyc --root ../tollbooth-dpyc \\
        --consumers .. --dry-run

    # live, Journeyman key from env:
    JOURNEYMAN_NSEC="$(cat <secure-file>)" python scripts/symbol_usage.py \\
        --lang typescript --repo tollbooth-web --root ../tollbooth-web --consumers ..
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import functools
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from intention_harvest import (
    JOURNEYMAN,
    Call,
    RoleKey,
    _apply,
    _call,
    _print_plan,
    npub_from_nsec,
)
from symbol_index import (
    TS_SUFFIXES,
    Definition,
    PackageIndex,
    TsModule,
    _graph_rows,
    _ts_resolve,
    _ts_resolve_spec,
    head_sha,
    index_package,
    module_path,
    public_api,
    ts_definitions,
    ts_entry_map,
    ts_index,
    ts_module_path,
    ts_public_api,
)

SKIP_DIRS = frozenset({".git", ".venv", "venv", "node_modules", "site-packages", "dist",
                       "build", "__pycache__", ".tox", ".mypy_cache", ".ruff_cache",
                       ".pytest_cache", ".wrangler", ".svelte-kit", "coverage"})
TEST_DIRS = frozenset({"tests", "test", "__tests__", "e2e"})
JS_SUFFIXES = (*TS_SUFFIXES, ".js", ".jsx", ".mts", ".mjs")


# --------------------------------------------------------------------------- #
# Walking a checkout (pure, unit-tested)
# --------------------------------------------------------------------------- #

def is_test_path(rel: str) -> bool:
    parts = rel.split("/")
    name = parts[-1]
    return (any(p in TEST_DIRS for p in parts[:-1])
            or name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py"
            or ".test." in name or ".spec." in name)


def source_files(root: Path, suffixes: tuple[str, ...],
                 vendored: frozenset[str] = frozenset(), tests: bool = False) -> list[str]:
    """Repo-relative source files under ``root``, built files excluded (and test files,
    unless ``tests``), and any
    directory named in ``vendored`` pruned: a consumer's directory named after the SDK's
    package is a vendored COPY of the SDK (tollbooth-fermyon's ``deps/tollbooth``), whose
    files define the symbols rather than use them."""
    out: list[str] = []
    for here, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs
                         if d not in SKIP_DIRS and d not in vendored and not d.startswith("."))
        for f in sorted(files):
            if f.endswith(suffixes) and not f.endswith(".d.ts"):
                rel = (Path(here) / f).relative_to(root).as_posix()
                if tests or not is_test_path(rel):
                    out.append(rel)
    return out


def fleet_checkouts(consumers: Path, sdk_repo: str) -> dict[str, Path]:
    """``{repo slug: checkout}`` for every fleet repo under ``consumers``, the SDK excluded.

    A repo is in the fleet when its renovate.json extends the dpyc-community preset."""
    out: dict[str, Path] = {}
    for d in sorted(p for p in consumers.iterdir() if p.is_dir()):
        if d.name.lower() == sdk_repo.lower():
            continue
        try:
            renovate = (d / "renovate.json").read_text(encoding="utf-8")
        except OSError:
            continue
        if "lonniev/dpyc-community" in renovate:
            out[d.name.lower()] = d
    return out


# --------------------------------------------------------------------------- #
# Python (pure, unit-tested)
# --------------------------------------------------------------------------- #

def _in_package(dotted: str, package: str) -> bool:
    return dotted == package or dotted.startswith(package + ".")


def py_bindings(tree: ast.Module, module: str, is_package: bool,
                package: str | None) -> dict[str, str]:
    """Every name a module binds to something in ``package`` (any import when ``None``), at
    any depth: local name ->
    dotted path (``from .x import a as b`` -> ``{"b": "pkg.x.a"}``; ``import pkg.x as m``
    -> ``{"m": "pkg.x"}``; ``import pkg.x`` -> ``{"pkg": "pkg"}``)."""
    here = module.split(".") if is_package else module.split(".")[:-1]
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                anchor = here[: len(here) - (node.level - 1)]
                base = ".".join([*anchor, base] if base else anchor)
            if package is not None and not _in_package(base, package):
                continue
            for alias in node.names:
                if alias.name != "*":
                    out[alias.asname or alias.name] = f"{base}.{alias.name}"
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if package is not None and not _in_package(alias.name, package):
                    continue
                if alias.asname:
                    out[alias.asname] = alias.name
                else:
                    out[alias.name.split(".")[0]] = alias.name.split(".")[0]
    return out


def _chain(node: ast.expr) -> list[str] | None:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        return [node.id, *reversed(parts)]
    return None


def py_references(tree: ast.Module, bindings: dict[str, str],
                  index: PackageIndex) -> Counter[str]:
    """Definition paths this module refers to, counted per site: a bound name read, or an
    attribute chain off a bound module (``m.Runtime``, ``pkg.runtime.Runtime``)."""
    refs: Counter[str] = Counter()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in bindings:
            if (d := index.resolve(bindings[node.id])):
                refs[d.path] += 1
        elif isinstance(node, ast.Attribute):
            chain = _chain(node)
            if chain and chain[0] in bindings:
                dotted = ".".join([bindings[chain[0]], *chain[1:]])
                if (d := index.resolve(dotted)):
                    refs[d.path] += 1
    return refs


def _base_classes(tree: ast.Module, bindings: dict[str, str],
                  index: PackageIndex) -> list[tuple[ast.ClassDef, str]]:
    """(class, SDK base class path) for each class here that subclasses an SDK class."""
    out: list[tuple[ast.ClassDef, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            chain = _chain(base)
            if chain and chain[0] in bindings:
                dotted = ".".join([bindings[chain[0]], *chain[1:]])
                if (d := index.resolve(dotted)) and d.kind == "class":
                    out.append((node, d.path))
    return out


def py_method_uses(tree: ast.Module, bindings: dict[str, str], index: PackageIndex,
                   methods: dict[str, list[str]]) -> set[str]:
    """Method paths this module plausibly uses: any ``.name`` that is the name of an SDK
    method (instances arrive from factories, so the receiver's type is unknowable without a
    type checker), and any method a subclass of an SDK class overrides."""
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in methods:
            used.update(methods[node.attr])
    for cls, base in _base_classes(tree, bindings, index):
        for item in cls.body:
            if (isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and (path := f"{base}.{item.name}") in index.defs):
                used.add(path)
    return used


def method_names(index: PackageIndex) -> dict[str, list[str]]:
    """``{"debit": ["pkg.runtime.Runtime.debit", ...]}`` for every function nested in a class."""
    classes = {p for p, d in index.defs.items() if d.kind == "class"}
    out: dict[str, list[str]] = defaultdict(list)
    for path, d in index.defs.items():
        owner, _, name = path.rpartition(".")
        if d.kind == "function" and owner in classes:
            out[name].append(path)
    return dict(out)


@dataclass
class ClassShapes:
    """What the SDK's classes promise beyond their own call sites.

    ``protocol_members``: ``{"how_to_join": [path, ...]}`` for each method of a
    ``typing.Protocol`` class. A Protocol is a structural contract, so a member is used
    wherever a function of that name is DEFINED: the implementation is the use. The fleet's
    Protocols are tool catalogs, implemented as tool functions nested in a registrar
    (``register_standard_tools``'s ``async def how_to_join()``), not as class methods.

    ``framework_hooks``: methods that override a method of an external base class
    (``HolderAuthProvider.authorize`` overrides FastMCP's ``OAuthProvider.authorize``).
    The framework calls them, so nothing in the fleet ever will."""
    protocol_members: dict[str, list[str]]
    framework_hooks: set[str]

    def implemented_by(self, tree: ast.Module, own_protocols: bool = True) -> set[str]:
        """Protocol members that ``tree`` implements by defining a function of that name. With
        ``own_protocols=False`` (the SDK's own modules) a Protocol does not implement itself."""
        skip: set[int] = set()
        if not own_protocols:
            for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
                if _is_protocol(cls):
                    skip.update(id(item) for item in cls.body)
        found: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and id(node) not in skip:
                for member in self.protocol_members.get(node.name, ()):
                    found |= {member, member.rpartition(".")[0]}  # the Protocol, too
        return found


def _is_protocol(cls: ast.ClassDef) -> bool:
    return any((c := _chain(b)) and c[-1] == "Protocol" for b in cls.bases)


@functools.cache
def _external_members(dotted: str) -> frozenset[str] | None:
    """The attribute names of an external class, by importing it; ``None`` when it cannot be
    imported (then every override is assumed to be a hook — the safe direction)."""
    import importlib

    module, _, name = dotted.rpartition(".")
    module = module or "builtins"  # `class X(Exception)` names a builtin, imported from nowhere
    try:
        return frozenset(dir(getattr(importlib.import_module(module), name)))
    except Exception:  # noqa: BLE001 — any failure to import means "unknown", never fatal
        return None


def _shape_class(cls: ast.ClassDef, path: str, bindings: dict[str, str], package: str,
                 index: PackageIndex, protocol_members: dict[str, list[str]],
                 hooks: set[str]) -> None:
    methods = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if _is_protocol(cls):
        for m in methods:
            protocol_members[m.name].append(f"{path}.{m.name}")
    for base in cls.bases:
        chain = _chain(base)
        if not chain or chain[-1] in ("Protocol", "object", "Generic"):
            continue
        dotted = ".".join([bindings.get(chain[0], chain[0]), *chain[1:]])
        if _in_package(dotted, package) or dotted in index.defs:
            continue
        members = _external_members(dotted)
        hooks.update(f"{path}.{m.name}" for m in methods
                     if members is None or m.name in members)
    for n in cls.body:
        if isinstance(n, ast.ClassDef):
            _shape_class(n, f"{path}.{n.name}", bindings, package, index, protocol_members, hooks)


def class_shapes(index: PackageIndex, package: str, src_root: Path) -> ClassShapes:
    protocol_members: dict[str, list[str]] = defaultdict(list)
    hooks: set[str] = set()
    for module, tree in index.trees.items():
        is_package = (src_root / module.replace(".", "/") / "__init__.py").is_file()
        bindings = py_bindings(tree, module, is_package, None)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                _shape_class(node, f"{module}.{node.name}", bindings, package, index,
                             protocol_members, hooks)
    return ClassShapes(dict(protocol_members), hooks)


def py_consumer_uses(repo_root: Path, package: str, index: PackageIndex,
                     shapes: ClassShapes) -> set[str]:
    """Every SDK definition path a consumer repo uses.

    Method calls and Protocol implementations are judged repo-wide, once the repo imports
    the SDK anywhere: the runtime is built in ``server.py`` and called as
    ``self._runtime.get_patron_credential(...)`` from a module that never imports it."""
    methods = method_names(index)
    used: set[str] = set()
    trees: list[ast.Module] = []
    for rel in source_files(repo_root, (".py",), frozenset({package}), tests=True):
        try:
            tree = ast.parse((repo_root / rel).read_text(encoding="utf-8"), filename=rel)
        except (SyntaxError, UnicodeDecodeError):
            continue
        trees.append(tree)
        bindings = py_bindings(tree, "", False, package)
        if not bindings:
            continue
        for dotted in bindings.values():  # an import is a use, even in a string annotation
            if (d := index.resolve(dotted)):
                used.add(d.path)
        used |= set(py_references(tree, bindings, index))
        used |= py_method_uses(tree, bindings, index, methods)
    if used:
        for tree in trees:
            used |= py_method_uses(tree, {}, index, methods)
            used |= shapes.implemented_by(tree)
    return used


def py_internal_refs(repo_root: Path, src: str, package: str, index: PackageIndex,
                     shapes: ClassShapes) -> Counter[str]:
    """Reference sites inside the SDK itself (re-exports are not uses: an import is not a
    read). A module's own top-level names are bound to it, so a sibling call counts; so does
    each SDK class implementing a Protocol member, and each framework hook (one site: the
    framework is the caller)."""
    methods = method_names(index)
    src_root = repo_root / src
    refs: Counter[str] = Counter()
    for file in sorted((src_root / package).rglob("*.py")):
        module = module_path(file, src_root)
        tree = index.trees.get(module)
        if tree is None:
            continue
        bindings = py_bindings(tree, module, file.name == "__init__.py", package)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                bindings.setdefault(node.name, f"{module}.{node.name}")
        refs += py_references(tree, bindings, index)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in methods:
                for path in methods[node.attr]:
                    refs[path] += 1
        refs.update(shapes.implemented_by(tree, own_protocols=False))
    refs.update(shapes.framework_hooks)
    return refs


# --------------------------------------------------------------------------- #
# TypeScript (pure, unit-tested)
# --------------------------------------------------------------------------- #

# The clause excludes quotes, so a side-effect ``import "./x.css"`` without a semicolon can
# never swallow the next statement.
_JS_FROM = re.compile(
    r"\b(?:import|export)\s+(?:type\s+)?([\w\s{},*$]*?)\s*from\s*[\"']([^\"']+)[\"']")
_JS_DYNAMIC_THEN = re.compile(
    r"import\(\s*[\"']([^\"']+)[\"']\s*\)\s*\.then\(\s*\(?\s*([\w$]+)\s*\)?\s*=>")
_JS_DYNAMIC_NS = re.compile(
    r"(?:const|let|var)\s+([\w$]+)\s*=\s*await\s+import\(\s*[\"']([^\"']+)[\"']\s*\)")
_JS_DYNAMIC_DESTRUCTURE = re.compile(
    r"(?:const|let|var)\s*\{([^}]*)\}\s*=\s*await\s+import\(\s*[\"']([^\"']+)[\"']\s*\)")
_JS_COMMENTS = re.compile(r"/\*.*?\*/|(?<![:\"'\w])//[^\n]*", re.DOTALL)


def _named(items: str) -> list[tuple[str, str]]:
    """``"a, b as c, type d"`` -> ``[("a", "a"), ("b", "c"), ("d", "d")]`` (imported, local)."""
    out: list[tuple[str, str]] = []
    for item in items.split(","):
        item = re.sub(r"^\s*type\s+", "", item).strip()
        if item:
            name, _, local = (p.strip() for p in item.partition(" as "))
            out.append((name, local or name))
    return out


def js_imports(text: str) -> list[tuple[str, str, str]]:
    """Every binding a module takes from another: ``(specifier, imported name, local name)``.

    The imported name is ``default`` for a default import and ``*`` for a namespace; a
    namespace's member reads (``ns.x``) come back as their own ``(spec, "x", "")`` rows, as
    do a dynamic import's ``m.x`` reads and destructured names."""
    text = _JS_COMMENTS.sub("", text)
    out: list[tuple[str, str, str]] = []
    namespaces: list[tuple[str, str]] = []
    for m in _JS_FROM.finditer(text):
        clause, spec = m.group(1).strip(), m.group(2)
        if (ns := re.search(r"\*\s+as\s+([\w$]+)", clause)):
            namespaces.append((spec, ns.group(1)))
            out.append((spec, "*", ns.group(1)))
        elif clause.strip() == "*":
            out.append((spec, "*", ""))
        if (brace := re.search(r"\{([^}]*)\}", clause)):
            out += [(spec, name, local) for name, local in _named(brace.group(1))]
        default = re.match(r"([\w$]+)\s*(?:,|$)", clause)
        if default and not clause.startswith("{"):
            out.append((spec, "default", default.group(1)))
    for m in _JS_DYNAMIC_THEN.finditer(text):
        namespaces.append((m.group(1), m.group(2)))
    for m in _JS_DYNAMIC_NS.finditer(text):
        namespaces.append((m.group(2), m.group(1)))
    for m in _JS_DYNAMIC_DESTRUCTURE.finditer(text):
        out += [(m.group(2), name, "") for name, _local in
                _named(m.group(1).replace(":", " as "))]
    for spec, ns in namespaces:
        for member in sorted(set(re.findall(rf"(?<![\w$.]){re.escape(ns)}\.([\w$]+)", text))):
            out.append((spec, member, ""))
    return out


def web_subpath(spec: str, package_name: str) -> str | None:
    """``@tollbooth-dpyc/web/react`` -> ``./react``; ``@tollbooth-dpyc/web`` -> ``.``."""
    if spec == package_name:
        return "."
    if spec.startswith(package_name + "/"):
        return "./" + spec[len(package_name) + 1:]
    return None


def ts_consumer_uses(repo_root: Path, package_name: str, modules: dict[str, TsModule],
                     entries: dict[str, str]) -> set[str]:
    used: set[str] = set()
    for rel in source_files(repo_root, JS_SUFFIXES, tests=True):
        try:
            text = (repo_root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if package_name not in text:
            continue
        for spec, name, _local in js_imports(text):
            sub = web_subpath(spec, package_name)
            entry = entries.get(sub) if sub else None
            if entry is None or name == "*":
                continue
            if (d := _ts_resolve(modules, entry, name)):
                used.add(d.path)
    return used


def _without_module_syntax(text: str) -> str:
    """The module's code minus its import/export-list statements, so a name that is only
    re-exported is not counted as read."""
    text = _JS_COMMENTS.sub("", text)
    text = _JS_FROM.sub("", text)
    return re.sub(r"\bexport\s+(?:type\s+)?\{[^}]*\}\s*;?", "", text)


def ts_internal_refs(repo_root: Path, modules: dict[str, TsModule]) -> Counter[str]:
    """Reference sites inside the SDK: each read of a name a module declares or imports
    from a sibling module, the declaration itself excluded."""
    files = set(modules)
    refs: Counter[str] = Counter()
    for f, mod in modules.items():
        raw = (repo_root / f).read_text(encoding="utf-8")
        body = _without_module_syntax(raw)
        bindings: dict[str, tuple[str, int]] = {}  # local -> (def path, sites not reads)
        for name in mod.decls:
            bindings[name] = (f"{ts_module_path(f)}#{name}", 1)
        for spec, name, local in js_imports(raw):
            source = _ts_resolve_spec(spec, f, files)
            if source is None or name == "*":
                continue
            if (d := _ts_resolve(modules, source, name)):
                if local:
                    bindings[local] = (d.path, 0)
                else:
                    refs[d.path] += 1  # a namespace member read
        for local, (path, own) in bindings.items():
            hits = len(re.findall(rf"(?<![\w$.]){re.escape(local)}(?![\w$])", body))
            if hits - own > 0:
                refs[path] += hits - own
    return refs


# --------------------------------------------------------------------------- #
# Comparing with the graph (pure, unit-tested)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Observation:
    fqn: str
    consumers: tuple[str, ...]
    internal_refs: int

    @property
    def usage(self) -> str:
        return "unused" if not self.consumers and self.internal_refs == 0 else "used"


def observe(repo: str, defs: dict[str, Definition], uses: dict[str, set[str]],
            internal: Counter[str], universe: list[str]) -> list[Observation]:
    """One observation per symbol in ``universe`` (fqns) that the code still defines."""
    out: list[Observation] = []
    for fqn in universe:
        prefix, _, path = fqn.partition(":")
        if prefix != repo or path not in defs:
            continue
        consumers = tuple(sorted(r for r, paths in uses.items() if path in paths))
        out.append(Observation(fqn, consumers, internal.get(path, 0)))
    return out


def changed(obs: Observation, row: dict[str, Any] | None) -> bool:
    """Does the graph's last observation differ in what it SAYS (usage, consumers)?"""
    if row is None:
        return True
    return (row.get("usage") != obs.usage
            or sorted(row.get("consumers") or []) != list(obs.consumers))


def plan_usage(sha: str, observations: list[Observation],
               rows: dict[str, dict[str, Any]]) -> list[Call]:
    return [_call("observe_symbol_usage", symbol_fqn=o.fqn, consumer_repos=list(o.consumers),
                  internal_refs=o.internal_refs, observed_at_sha=sha)
            for o in observations if changed(o, rows.get(o.fqn))]


def format_usage_report(repo: str, observations: list[Observation], fleet: list[str],
                        writes: int) -> str:
    unused = [o for o in observations if o.usage == "unused"]
    internal_only = [o for o in observations if not o.consumers and o.internal_refs]
    head = (f"{repo}: {len(observations)} symbols observed across {len(fleet)} fleet repos · "
            f"{len(unused)} unused · {len(internal_only)} used only inside the SDK · "
            f"{writes} to write")
    lines = [head]
    lines += [f"  [unused] {o.fqn}" for o in unused]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Driver (live)
# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="the SDK's repo slug, e.g. tollbooth-dpyc")
    ap.add_argument("--root", required=True, type=Path, help="the SDK's checkout")
    ap.add_argument("--consumers", required=True, type=Path,
                    help="a directory holding the fleet's checkouts, one per repo")
    ap.add_argument("--lang", choices=["python", "typescript"], default="python")
    ap.add_argument("--src", default="src")
    ap.add_argument("--package", default="",
                    help="Python package (default: tollbooth-dpyc -> tollbooth) or npm name "
                         "(default: package.json's name)")
    ap.add_argument("--extra-module", action="append", default=[],
                    help="as for symbol_index.py: public symbols no entry point re-exports")
    ap.add_argument("--graph-rows", type=Path,
                    help="offline: a JSON file of symbols_in_service rows instead of a live read")
    ap.add_argument("--url", default=os.environ.get("CYPHER_MCP_URL",
                                                    "https://cypher-mcp.fastmcp.app/mcp"))
    ap.add_argument("--dry-run", action="store_true", help="report and print the plan; no writes")
    args = ap.parse_args()

    root = args.root.expanduser().resolve()
    fleet = fleet_checkouts(args.consumers.expanduser().resolve(), args.repo)
    if not fleet:
        print(f"  ! no fleet checkouts under {args.consumers}; refusing to call everything "
              "unused", file=sys.stderr)
        return 2

    uses: dict[str, set[str]] = {}
    if args.lang == "typescript":
        modules = ts_index(root, args.src)
        defs = ts_definitions(modules)
        entries = ts_entry_map(root, args.src)
        package_name = args.package or json.loads((root / "package.json").read_text())["name"]
        extra = [f for f in modules if ts_module_path(f) in args.extra_module]
        public = ts_public_api(modules, [*entries.values(), *extra])
        for slug, checkout in fleet.items():
            uses[slug] = ts_consumer_uses(checkout, package_name, modules, entries)
        internal = ts_internal_refs(root, modules)
    else:
        package = args.package or args.repo.split("-")[0]
        index = index_package(root, args.src, package)
        defs = index.defs
        public = public_api(index, package, tuple(args.extra_module))
        shapes = class_shapes(index, package, root / args.src)
        for slug, checkout in fleet.items():
            uses[slug] = py_consumer_uses(checkout, package, index, shapes)
        internal = py_internal_refs(root, args.src, package, index, shapes)

    nsec = os.environ.get("JOURNEYMAN_NSEC", "")
    key = RoleKey(npub_from_nsec(nsec), nsec)
    if args.graph_rows:
        rows = json.loads(args.graph_rows.read_text())
    elif key.nsec:
        rows = asyncio.run(_graph_rows(args.url, args.repo, key))
    else:
        print("  ! no JOURNEYMAN_NSEC and no --graph-rows: observing the public API as if the "
              "graph held it", file=sys.stderr)
        rows = [{"symbol": f"{args.repo}:{p}"} for p in sorted(public)]
    by_fqn = {r["symbol"]: r for r in rows if r.get("symbol")}

    observations = observe(args.repo, defs, uses, internal, sorted(by_fqn))
    calls = plan_usage(head_sha(root), observations, by_fqn)
    print(format_usage_report(args.repo, observations, sorted(fleet), len(calls)))
    if args.dry_run or not calls:
        _print_plan(calls)
        return 0
    if not key.nsec:
        print("  ! JOURNEYMAN_NSEC is not set; cannot write", file=sys.stderr)
        return 2
    return asyncio.run(_apply(args.url, calls, {JOURNEYMAN: key}))


if __name__ == "__main__":
    raise SystemExit(main())
