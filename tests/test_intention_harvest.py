"""Tests for the Intention Service forward-map harvester (Task 2).

Pins the pure planners and — most importantly — the security boundary: the derived pass
and all structural edges are Journeyman writes; only the authoritative why and the
invariants are Operator writes; provenance is never a parameter. The cypher-mcp gate is
the real enforcer, but these tests keep the harvester from ever *intending* a mis-signed
call.

Run: pytest tests/test_intention_harvest.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import intention_harvest as ih  # noqa: E402
from intention_harvest import (  # noqa: E402
    JOURNEYMAN, OPERATOR, Service,
    canonical_service_name, keywords_from_tools, load_operators, parse_patent_schedule,
    plan_authored, plan_derived, plan_patent,
)


def test_npub_from_nsec_round_trips_and_handles_empty():
    import pytest
    PrivateKey = pytest.importorskip("pynostr.key").PrivateKey
    pk = PrivateKey()  # random keypair
    assert ih.npub_from_nsec(pk.nsec) == pk.public_key.bech32()  # derives the matching npub
    assert ih.npub_from_nsec("") == ""                            # empty in -> empty out


def test_parse_patent_schedule_reads_the_committed_doc(tmp_path):
    md = tmp_path / "sched.md"
    md.write_text(
        "# Reference Numeral Schedule\n\n"
        "## Nostr / Identity (600-series)\n\n"
        "| Ref. | Element | Appears in FIG. |\n"
        "|------|---------|-----------------|\n"
        "| 610 | Secure Courier channel | 5 |\n"
        "| 614 | Poison nonce | 5 |\n\n"
        "## Governance (700-series)\n\n"
        "| 708 | Ban process | 6 |\n"
    )
    els = parse_patent_schedule(md)
    assert len(els) == 3
    sc = next(e for e in els if e["ref"] == 610)
    assert sc == {"ref": 610, "name": "Secure Courier channel", "figures": "5",
                  "claim_family": "Nostr / Identity (600-series)"}
    assert next(e for e in els if e["ref"] == 708)["claim_family"] == "Governance (700-series)"
    # header/separator rows (non-numeric first cell) are skipped
    assert all(isinstance(e["ref"], int) for e in els)


def test_parse_the_real_patent_schedule():
    doc = REPO_ROOT / "docs" / "patent" / "REFERENCE-NUMERAL-SCHEDULE.md"
    if not doc.exists():
        import pytest
        pytest.skip("patent schedule not present")
    els = parse_patent_schedule(doc)
    assert len(els) >= 100  # ~121 numerals
    assert any(e["ref"] == 610 and "Courier" in e["name"] for e in els)


def test_plan_patent_upserts_elements_and_links_traces():
    elements = [{"ref": 610, "name": "Secure Courier channel", "figures": "5", "claim_family": "CF4"}]
    manifest = {
        "capabilities": [{"name": "Secure Courier", "patent_refs": [610]}],
        "invariants": [{"name": "Credentials are never echoed", "patent_refs": [610, 614]}],
    }
    calls = plan_patent(elements, manifest)
    tools = [c.tool for c in calls]
    assert "upsert_patent_element" in tools
    assert tools.count("link_capability_to_patent") == 1
    assert tools.count("link_invariant_to_patent") == 2
    # patent tracing is Journeyman-signed (a citation index, not authoritative why)
    assert all(c.role == JOURNEYMAN for c in calls)
    # refs are ints, never strings
    assert all(isinstance(c.params.get("patent_ref", 0), int) for c in calls)


def test_canonical_service_name_slugifies_and_skips_npub_placeholders():
    assert canonical_service_name("schwab-mcp") == "schwab-mcp"
    assert canonical_service_name("Excalibur MCP") == "excalibur-mcp"
    assert canonical_service_name("tollbooth-fermyon") == "tollbooth-fermyon"
    assert canonical_service_name("npub1qchpfnuw76g") is None
    assert canonical_service_name("") is None
    assert canonical_service_name(None) is None


# --- role wiring -------------------------------------------------------------

def test_role_property_matches_table():
    for tool, role in ih.ROLE_FOR_TOOL.items():
        assert ih._call(tool, x=1).role == role

def test_unknown_tool_is_rejected():
    with pytest.raises(KeyError):
        ih._call("delete_everything")


# --- load_operators ----------------------------------------------------------

def test_load_operators_flattens_and_skips_non_operators(tmp_path):
    (tmp_path / "op1.json").write_text(json.dumps({
        "npub": "npub1a", "role": "operator",
        "services": [{"name": "schwab-mcp", "url": "https://s/mcp", "description": "brokerage"}],
    }))
    (tmp_path / "op2.json").write_text(json.dumps({
        "npub": "npub1b", "role": "operator",
        "services": [{"name": "thebrain-mcp", "url": "https://b/mcp"}],
    }))
    (tmp_path / "advocate.json").write_text(json.dumps({  # not an operator -> skipped
        "npub": "npub1c", "role": "advocate", "services": [{"name": "collector"}],
    }))
    (tmp_path / "nonpub.json").write_text(json.dumps({  # no npub -> skipped
        "role": "operator", "services": [{"name": "ghost"}],
    }))
    svcs = load_operators(tmp_path)
    names = {s.name for s in svcs}
    assert names == {"schwab-mcp", "thebrain-mcp"}
    assert next(s for s in svcs if s.name == "schwab-mcp").npub == "npub1a"


# --- keyword extraction ------------------------------------------------------

def test_keywords_strip_prefix_dedup_and_append_description():
    svc = Service("schwab-mcp", "npub1a", "u", "Charles Schwab brokerage data")
    tools = [
        {"name": "schwab_get_option_chain"},
        {"name": "schwab_get_stock_quote"},
        {"name": "schwab_get_option_chain"},  # dup
    ]
    kw = keywords_from_tools(svc, tools)
    parts = [p.strip() for p in kw.split(",")]
    assert parts.count("get option chain") == 1
    assert "get stock quote" in parts
    assert parts[-1] == "charles schwab brokerage data"


# --- derived plan ------------------------------------------------------------

def test_plan_derived_registers_all_and_caps_only_reachable():
    services = [
        Service("schwab-mcp", "npub1a", "u1", "brokerage"),
        Service("cold-mcp", "npub1b", "u2", "cold"),  # unreachable: no tools
    ]
    tools_by = {"schwab-mcp": [{"name": "schwab_get_quote"}]}
    calls = plan_derived(services, tools_by)
    kinds = [(c.tool, c.params.get("repo_name") or c.params.get("owner_repo")) for c in calls]
    assert ("register_service", "schwab-mcp") in kinds
    assert ("register_service", "cold-mcp") in kinds
    assert ("upsert_capability", "schwab-mcp") in kinds
    assert ("upsert_capability", "cold-mcp") not in kinds  # unreachable -> no capability
    assert all(c.role == JOURNEYMAN for c in calls)  # derived pass is Journeyman-only


# --- authored plan -----------------------------------------------------------

def _manifest():
    return {
        "capabilities": [{
            "name": "Secure Courier",
            "owners": ["tollbooth-dpyc"],
            "consumers": ["schwab-mcp"],
            "keywords": "courier",
            "why": "because\n   reasons  wrap",
            "symbols": ["tollbooth.secure_courier.SecureCourier"],
        }],
        "invariants": [{
            "name": "nsec only",
            "rule": "operators are nsec only",
            "guards": ["tollbooth.identity"],
        }],
    }

def test_plan_authored_roles_and_ordering():
    calls = plan_authored(_manifest())
    tools = [c.tool for c in calls]
    # structure precedes the authoritative why
    assert tools.index("upsert_capability") < tools.index("authorize_capability_why")
    role_of = {c.tool: c.role for c in calls}
    assert role_of["upsert_capability"] == JOURNEYMAN
    assert role_of["link_capability_consumer"] == JOURNEYMAN
    assert role_of["bind_capability_to_symbol"] == JOURNEYMAN
    assert role_of["authorize_capability_why"] == OPERATOR
    assert role_of["assert_invariant"] == OPERATOR
    assert role_of["guard_invariant_symbol"] == OPERATOR

def test_authored_why_whitespace_is_collapsed():
    why = next(c for c in plan_authored(_manifest())
               if c.tool == "authorize_capability_why").params["why"]
    assert why == "because reasons wrap"


# --- the security boundary (the point of the whole design) -------------------

def test_only_operator_writes_authoritative_or_invariants():
    calls = plan_authored(_manifest()) + plan_derived(
        [Service("s", "npub1", "u", "d")], {"s": [{"name": "s_do"}]})
    operator_only = {"authorize_capability_why", "assert_invariant", "guard_invariant_symbol"}
    for c in calls:
        if c.tool in operator_only:
            assert c.role == OPERATOR
        else:
            assert c.role == JOURNEYMAN

def test_provenance_is_never_a_call_param():
    calls = plan_authored(_manifest()) + plan_derived(
        [Service("s", "npub1", "u", "d")], {"s": [{"name": "s_do"}]})
    for c in calls:
        assert "provenance" not in c.params, c.tool
