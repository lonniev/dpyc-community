"""Tests for the fleet usage scan (scripts/symbol_usage.py).

Every case writes the SDK and its consumers to a temp dir, so it states exactly the code it
reads. The traps pinned here are the ones that would mark LIVE code unused, since that asks
a human to retire it:

  * a method called through an instance in a module that never imports the SDK
  * a Protocol member implemented as a nested tool function, not a class method
  * a framework hook (an override of an external base) that nothing in the fleet calls
  * a TypeScript import that climbs out of its folder (``../holder.ts``)
  * a helper the SDK exports for consumers' TESTS

and the ones that would hide dead code: a vendored copy of the SDK, the SDK's own tests, a
re-export, and a sibling's docstring are not uses.

Run: pytest tests/test_symbol_usage.py
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from symbol_index import index_package, ts_entry_map, ts_index
from symbol_usage import (
    Observation,
    changed,
    class_shapes,
    fleet_checkouts,
    js_imports,
    observe,
    plan_usage,
    py_consumer_uses,
    py_internal_refs,
    ts_consumer_uses,
    ts_internal_refs,
)

PRESET = '{"extends": ["local>lonniev/dpyc-community:renovate-config"]}'


def _write(root: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return root


# --- Python -------------------------------------------------------------------

SDK = {
    "src/demo/__init__.py": (
        "from demo.runtime import Runtime, helper\n"
        "from demo.proto import OperatorProtocol\n"
        "from demo.consts import LABEL\n"
        "__all__ = ['Runtime', 'helper', 'OperatorProtocol', 'LABEL']\n"
    ),
    "src/demo/runtime.py": (
        "class Runtime:\n"
        "    def debit(self): ...\n"
        "    def never_called(self): ...\n"
        "def helper(): ...\n"
        "def sibling():\n"
        "    return helper()\n"
        "def register_tools(mcp):\n"
        "    async def how_to_join(): ...\n"
    ),
    "src/demo/proto.py": (
        "from typing import Protocol\n"
        "class OperatorProtocol(Protocol):\n"
        "    async def how_to_join(self): ...\n"
        "    async def tool_catalog(self): ...\n"
    ),
    "src/demo/errors.py": (
        "class Refused(Exception):\n"
        "    def with_traceback(self, tb): ...\n"
        "    def explain(self): ...\n"
    ),
    "src/demo/consts.py": '"""LABEL is documented here, which is not a use."""\nLABEL = "x"\n',
}


def _sdk(tmp_path: Path):
    root = _write(tmp_path / "demo-sdk", SDK)
    index = index_package(root, "src", "demo")
    return root, index, class_shapes(index, "demo", root / "src")


def test_imports_reexports_and_module_attributes_resolve_to_the_definition(tmp_path):
    _root, index, shapes = _sdk(tmp_path)
    app = _write(tmp_path / "app", {
        "server.py": "import demo.runtime as rt\nfrom demo import Runtime\nrt.helper()\n"})
    used = py_consumer_uses(app, "demo", index, shapes)
    assert {"demo.runtime.Runtime", "demo.runtime.helper"} <= used
    assert "demo.consts.LABEL" not in used


def test_a_method_called_through_an_instance_counts_repo_wide(tmp_path):
    _root, index, shapes = _sdk(tmp_path)
    app = _write(tmp_path / "app", {
        "server.py": "from demo import Runtime\nruntime = Runtime()\n",
        "store.py": "class Store:\n    def go(self):\n        return self._runtime.debit()\n",
    })
    used = py_consumer_uses(app, "demo", index, shapes)
    assert "demo.runtime.Runtime.debit" in used
    assert "demo.runtime.Runtime.never_called" not in used


def test_a_repo_that_never_imports_the_sdk_uses_nothing(tmp_path):
    _root, index, shapes = _sdk(tmp_path)
    other = _write(tmp_path / "other", {"x.py": "def debit(): ...\nobj.debit()\n"})
    assert py_consumer_uses(other, "demo", index, shapes) == set()


def test_a_vendored_copy_of_the_sdk_is_not_a_consumer(tmp_path):
    _root, index, shapes = _sdk(tmp_path)
    app = _write(tmp_path / "fermyon", {
        "component/deps/demo/runtime.py": "from demo.runtime import helper\nhelper()\n",
        "app.py": "from demo import Runtime\n",
    })
    assert "demo.runtime.helper" not in py_consumer_uses(app, "demo", index, shapes)


def test_consumer_tests_are_usage(tmp_path):
    _root, index, shapes = _sdk(tmp_path)
    app = _write(tmp_path / "app", {"tests/test_x.py": "from demo import LABEL\n"})
    assert "demo.consts.LABEL" in py_consumer_uses(app, "demo", index, shapes)


def test_a_protocol_member_is_used_where_a_function_implements_it(tmp_path):
    root, index, shapes = _sdk(tmp_path)
    refs = py_internal_refs(root, "src", "demo", index, shapes)
    assert refs["demo.proto.OperatorProtocol.how_to_join"] >= 1  # nested tool function
    assert refs["demo.proto.OperatorProtocol"] >= 1                # so the Protocol is used
    assert refs["demo.proto.OperatorProtocol.tool_catalog"] == 0   # nobody implements it


def test_an_override_of_an_external_base_is_a_framework_hook(tmp_path):
    _root, _index, shapes = _sdk(tmp_path)
    assert "demo.errors.Refused.with_traceback" in shapes.framework_hooks
    assert "demo.errors.Refused.explain" not in shapes.framework_hooks


def test_internal_refs_count_reads_never_reexports_or_docstrings(tmp_path):
    root, index, shapes = _sdk(tmp_path)
    _write(root, {"tests/test_runtime.py": "from demo.runtime import Runtime\nRuntime().never_called()\n"})
    refs = py_internal_refs(root, "src", "demo", index, shapes)
    assert refs["demo.runtime.helper"] == 1            # sibling() calls it; __init__ only re-exports
    assert refs["demo.consts.LABEL"] == 0              # docstring + re-export
    assert refs["demo.runtime.Runtime.never_called"] == 0  # the SDK's own tests do not count


# --- TypeScript -----------------------------------------------------------------

WEB = {
    "package.json": (
        '{"name": "@demo/web", "exports": {".": {"default": "./dist/index.js"},'
        ' "./react": {"default": "./dist/react.js"}}}'
    ),
    "src/index.ts": (
        'export { holderEnabled } from "./holder.ts";\n'
        'export * from "./tour.ts";\n'
        'export { DM_RELAYS } from "./nostrDm.ts";\n'
    ),
    "src/react.ts": 'export { default as AccountPage } from "./react/AccountPage.tsx";\n',
    "src/holder.ts": "export function holderEnabled() { return true; }\n",
    "src/tour.ts": "export function lintTours() {}\nexport function unusedHelper() {}\n",
    "src/nostrDm.ts": "export const DM_RELAYS = ['wss://x'];\n",
    "src/react/AccountPage.tsx": (
        'import { holderEnabled as enabled } from "../holder.ts";\n'
        "export default function AccountPage() { return enabled(); }\n"
    ),
}


def _web(tmp_path: Path):
    root = _write(tmp_path / "web", WEB)
    return root, ts_index(root), ts_entry_map(root)


def test_js_import_shapes():
    text = (
        'import "./side.css"\n'
        'import Def, { a, b as c, type T } from "@demo/web"\n'
        'import * as ns from "@demo/web/react"\n'
        "ns.AccountPage; ns.AccountPage\n"
        'const L = lazy(() => import("@demo/web/react").then((m) => ({ default: m.Lazy })))\n'
        'const { d: dd, e } = await import("@demo/web")\n'
        '// import { commented } from "@demo/web"\n'
    )
    got = {(spec, name) for spec, name, _ in js_imports(text)}
    assert {("@demo/web", "default"), ("@demo/web", "a"), ("@demo/web", "b"),
            ("@demo/web", "T"), ("@demo/web/react", "AccountPage"),
            ("@demo/web/react", "Lazy"), ("@demo/web", "d"), ("@demo/web", "e")} <= got
    assert not any(name == "commented" for _, name in got)
    assert not any("side.css" in spec for spec, _ in got)  # side effect: no binding, no swallow


def test_ts_consumer_uses_resolve_through_entry_points(tmp_path):
    _root, modules, entries = _web(tmp_path)
    site = _write(tmp_path / "site", {
        "frontend/src/App.tsx": 'import { AccountPage } from "@demo/web/react";\n',
        "frontend/src/tour.test.ts": 'import { lintTours } from "@demo/web";\n',
    })
    used = ts_consumer_uses(site, "@demo/web", modules, entries)
    assert used == {"react/AccountPage#AccountPage", "tour#lintTours"}


def test_ts_internal_refs_follow_parent_folder_imports(tmp_path):
    root, modules, _ = _web(tmp_path)
    refs = ts_internal_refs(root, modules)
    assert refs["holder#holderEnabled"] == 1   # AccountPage.tsx reads it as `enabled`
    assert refs["nostrDm#DM_RELAYS"] == 0      # only re-exported
    assert refs["tour#unusedHelper"] == 0


# --- The fleet and the graph ------------------------------------------------------

def test_the_fleet_is_the_renovate_preset_minus_the_sdk(tmp_path):
    _write(tmp_path / "demo-sdk", {"renovate.json": PRESET})
    _write(tmp_path / "Site-A", {"renovate.json": PRESET})
    _write(tmp_path / "stranger", {"renovate.json": "{}"})
    (tmp_path / "loose-dir").mkdir()
    assert list(fleet_checkouts(tmp_path, "Demo-SDK")) == ["site-a"]


def test_only_changed_observations_are_written(tmp_path):
    _root, index, _shapes = _sdk(tmp_path)
    uses = {"app-b": {"demo.runtime.helper"}, "app-a": {"demo.runtime.helper"}}
    internal = Counter({"demo.runtime.Runtime": 2})
    universe = ["demo-sdk:demo.runtime.helper", "demo-sdk:demo.runtime.Runtime",
                "demo-sdk:demo.consts.LABEL", "demo-sdk:demo.gone", "other:demo.runtime.helper"]
    obs = observe("demo-sdk", index.defs, uses, internal, universe)
    assert [o.fqn for o in obs] == universe[:3]               # gone and foreign skipped
    assert obs[0].consumers == ("app-a", "app-b")             # sorted, stable
    assert [o.usage for o in obs] == ["used", "used", "unused"]

    rows = {
        "demo-sdk:demo.runtime.helper": {"usage": "used", "consumers": ["app-b", "app-a"]},
        "demo-sdk:demo.runtime.Runtime": {"usage": "used", "consumers": [], "internal_refs": 9},
        "demo-sdk:demo.consts.LABEL": {"usage": "used", "consumers": ["app-a"]},
    }
    calls = plan_usage("sha1", obs, rows)
    assert [(c.tool, c.params["symbol_fqn"]) for c in calls] == [
        ("observe_symbol_usage", "demo-sdk:demo.consts.LABEL")]
    assert calls[0].params == {"symbol_fqn": "demo-sdk:demo.consts.LABEL", "consumer_repos": [],
                               "internal_refs": 0, "observed_at_sha": "sha1"}
    assert calls[0].role == "journeyman"


def test_a_never_observed_symbol_is_written():
    assert changed(Observation("r:x", (), 1), {"symbol": "r:x"})
    assert changed(Observation("r:x", (), 1), None)
