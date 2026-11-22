"""Tests for the code-outward Symbol indexer.

The package under test is written to a temp dir, so every case states exactly the code it
reads. The traps pinned here:

  * a name exported from ``__init__`` must be indexed where it is DEFINED, not where it is
    re-exported — otherwise a file move renames the node
  * private methods of an exported class are not public API
  * a graph Symbol that is gone from the code is reported and never written
  * a graph Symbol that is private but still present is found (it moved), not called gone

Run: pytest tests/test_symbol_index.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from symbol_index import (
    _ts_resolve_spec,
    compare,
    index_package,
    plan,
    public_api,
    ts_definitions,
    ts_entry_points,
    ts_index,
    ts_public_api,
)

REPO = "demo-dpyc"


def _write(root: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return root


PACKAGE = {
    "src/demo/__init__.py": (
        "from demo.runtime import Runtime\n"
        "from .helpers import shout as yell\n"
        "from demo.reexport import Deep\n"
        "__version__ = '1'\n"
        "__all__ = ['Runtime', 'yell', 'Deep', '__version__']\n"
    ),
    "src/demo/runtime.py": (
        "class Runtime:\n"
        "    def debit(self): ...\n"
        "    async def refund(self): ...\n"
        "    def _secret(self): ...\n"
        "    class Policy:\n"
        "        def allow(self): ...\n"
        "def _private_helper(): ...\n"
    ),
    "src/demo/helpers.py": "def shout(): ...\n",
    "src/demo/reexport.py": "from demo.deep.model import Deep\n",
    "src/demo/deep/__init__.py": "",
    "src/demo/deep/model.py": "class Deep:\n    pass\n",
    "src/demo/holder.py": "def verify(): ...\ndef _inner(): ...\nLIMIT = 3\n",
}


def _index(tmp_path: Path):
    root = _write(tmp_path, PACKAGE)
    return root, index_package(root, "src", "demo")


def test_exports_resolve_to_the_defining_module(tmp_path):
    _, idx = _index(tmp_path)
    public = public_api(idx, "demo")
    assert "demo.runtime.Runtime" in public
    assert "demo.helpers.shout" in public            # relative import, renamed with `as`
    assert "demo.deep.model.Deep" in public           # followed through a re-export chain
    assert "demo.Runtime" not in public
    assert public["demo.runtime.Runtime"].file_path == "src/demo/runtime.py"


def test_exported_class_brings_public_members_only(tmp_path):
    _, idx = _index(tmp_path)
    public = public_api(idx, "demo")
    assert {"demo.runtime.Runtime.debit", "demo.runtime.Runtime.refund",
            "demo.runtime.Runtime.Policy", "demo.runtime.Runtime.Policy.allow"} <= set(public)
    assert "demo.runtime.Runtime._secret" not in public
    assert "demo.runtime._private_helper" not in public
    assert not any("__version__" in p for p in public)


def test_extra_module_adds_its_public_defs(tmp_path):
    _, idx = _index(tmp_path)
    assert "demo.holder.verify" not in public_api(idx, "demo")
    public = public_api(idx, "demo", ("demo.holder",))
    assert "demo.holder.verify" in public
    assert "demo.holder._inner" not in public
    assert "demo.holder.LIMIT" not in public


def test_verdicts(tmp_path):
    _, idx = _index(tmp_path)
    public = public_api(idx, "demo")
    rows = [
        {"symbol": f"{REPO}:demo.runtime.Runtime.debit", "file": "src/demo/runtime.py"},
        {"symbol": f"{REPO}:demo.runtime.Runtime.refund", "file": "src/demo/old.py"},
        {"symbol": f"{REPO}:demo.runtime.Runtime", "file": None},
        {"symbol": f"{REPO}:demo.runtime._private_helper", "file": "src/demo/gone.py"},
        {"symbol": f"{REPO}:demo.runtime.Deleted", "file": "src/demo/runtime.py"},
        {"symbol": "demo.runtime.Runtime", "file": None},                   # no repo prefix
        {"symbol": "other-repo:demo.runtime.Runtime", "file": None},       # not ours
        {"symbol": f"{REPO}:demo.runtime.Runtime.debit", "file": "src/demo/runtime.py"},
    ]
    by = {o.fqn: o for o in compare(REPO, idx.defs, public, rows)}
    assert by[f"{REPO}:demo.runtime.Runtime.debit"].verdict == "ok"
    moved = by[f"{REPO}:demo.runtime.Runtime.refund"]
    assert (moved.verdict, moved.was, moved.file_path) == (
        "moved", "src/demo/old.py", "src/demo/runtime.py")
    assert by[f"{REPO}:demo.runtime.Runtime"].verdict == "unanchored"
    # private, but anchored on purpose and still in the code: re-anchor, never "gone"
    assert by[f"{REPO}:demo.runtime._private_helper"].verdict == "moved"
    assert by[f"{REPO}:demo.runtime.Deleted"].verdict == "gone"
    assert by["demo.runtime.Runtime"].verdict == "malformed"
    assert "other-repo:demo.runtime.Runtime" not in by
    assert by[f"{REPO}:demo.helpers.shout"].verdict == "new"


def test_plan_never_writes_gone_or_malformed(tmp_path):
    _, idx = _index(tmp_path)
    public = public_api(idx, "demo")
    rows = [{"symbol": f"{REPO}:demo.runtime.Deleted", "file": "src/demo/runtime.py"},
            {"symbol": "demo.bare", "file": None}]
    calls = plan(REPO, "abc123", compare(REPO, idx.defs, public, rows))
    touched = {c.params["symbol_fqn"] for c in calls}
    assert f"{REPO}:demo.runtime.Deleted" not in touched
    assert "demo.bare" not in touched
    new = f"{REPO}:demo.helpers.shout"
    assert [c.tool for c in calls if c.params["symbol_fqn"] == new] == [
        "index_symbol", "anchor_symbol"]
    anchor = next(c for c in calls if c.tool == "anchor_symbol" and c.params["symbol_fqn"] == new)
    assert anchor.params == {"symbol_fqn": new, "file_path": "src/demo/helpers.py",
                             "verified_at_sha": "abc123"}
    assert all(c.role == "journeyman" for c in calls)


def test_moved_only_reanchors(tmp_path):
    _, idx = _index(tmp_path)
    rows = [{"symbol": f"{REPO}:demo.runtime.Runtime.refund", "file": "src/demo/old.py"}]
    calls = plan(REPO, "s", compare(REPO, idx.defs, {}, rows))
    assert [(c.tool, c.params["file_path"]) for c in calls] == [
        ("anchor_symbol", "src/demo/runtime.py")]


# --- TypeScript ---------------------------------------------------------------

WEB = {
    "package.json": (
        '{"exports": {".": {"types": "./dist/index.d.ts", "default": "./dist/index.js"},'
        ' "./react": {"default": "./dist/react/index.js"}, "./theme.css": "./theme.css"}}'
    ),
    "src/index.ts": (
        "// export function commentedOut() {}\n"
        "export { holderEnabled, type HolderConnection } from \"./holder.ts\";\n"
        "export * from \"./identity.ts\";\n"
        "export { renamed as publicName } from \"./internal.ts\";\n"
        "export { useState } from \"react\";\n"
    ),
    "src/holder.ts": (
        "const TOKENS = 'x';\n"
        "export function holderEnabled(): boolean { return true; }\n"
        "export interface HolderConnection { npub: string }\n"
        "function hidden() {}\n"
    ),
    "src/identity.ts": "export const isLoggedIn = () => true;\nexport async function logOut() {}\n",
    "src/internal.ts": "function renamed() {}\nexport { renamed };\n",
    "src/react/index.ts": "export { default as AccountPage, type Props } from \"./AccountPage.tsx\";\n",
    "src/react/AccountPage.tsx": (
        "export interface Props { a: string }\n"
        "export default function AccountPage(p: Props) { return null; }\n"
    ),
    "src/holder.test.ts": "export function testOnly() {}\n",
}


def _web(tmp_path: Path):
    root = _write(tmp_path, WEB)
    modules = ts_index(root)
    return root, modules


def test_ts_entry_points_map_dist_to_src(tmp_path):
    root, _ = _web(tmp_path)
    assert ts_entry_points(root) == ["src/index.ts", "src/react/index.ts"]


def test_ts_public_api_resolves_to_declaring_file_without_src(tmp_path):
    root, modules = _web(tmp_path)
    public = ts_public_api(modules, ts_entry_points(root))
    assert set(public) == {
        "holder#holderEnabled", "holder#HolderConnection",       # named, incl. `type`
        "identity#isLoggedIn", "identity#logOut",                # through `export *`
        "internal#renamed",                                      # `as` rename, local export
        "react/AccountPage#AccountPage", "react/AccountPage#Props",  # `default as`
    }
    assert public["react/AccountPage#AccountPage"].file_path == "src/react/AccountPage.tsx"
    assert public["holder#holderEnabled"].lang == "typescript"


def test_ts_definitions_include_private_but_not_tests_or_comments(tmp_path):
    _, modules = _web(tmp_path)
    defs = ts_definitions(modules)
    assert "holder#hidden" in defs and "holder#TOKENS" in defs
    assert not any("testOnly" in k or "commentedOut" in k for k in defs)


def test_ts_fqns_pass_the_naming_check_and_plan_typescript(tmp_path):
    root, modules = _web(tmp_path)
    public = ts_public_api(modules, ts_entry_points(root))
    calls = plan("web", "sha", compare("web", ts_definitions(modules), public, []))
    langs = {c.params["lang"] for c in calls if c.tool == "index_symbol"}
    assert langs == {"typescript"}
    assert "web:holder#holderEnabled" in {c.params["symbol_fqn"] for c in calls}


def test_ts_relative_specifiers_climb_out_of_their_folder():
    files = {"src/holder.ts", "src/react/NpubGate.tsx", "src/react/index.ts"}
    assert _ts_resolve_spec("../holder.ts", "src/react/NpubGate.tsx", files) == "src/holder.ts"
    assert _ts_resolve_spec("../holder.js", "src/react/NpubGate.tsx", files) == "src/holder.ts"
    assert _ts_resolve_spec("./index", "src/react/NpubGate.tsx", files) == "src/react/index.ts"
    assert _ts_resolve_spec("react", "src/react/NpubGate.tsx", files) is None
