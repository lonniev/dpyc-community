#!/usr/bin/env python3
"""Harvest the DPYC Intention Service forward map into the cypher-mcp factory graph.

The forward map answers "which service handles X" before a file is opened. It is
*derived* (recomputed, self-correcting) and cheap, and it is written through the
operator-published, parameterized templates in cypher-mcp — never raw Cypher. Design:
PersonalBrain 60c4c06d ("Intention Service"), Task 2.

DRY — the graph is populated straight from the authoritative sources, never a mirror file:

  * Code is the Rock of Truth.  * The patent docs explain it narratively.
  * The cypher graph makes intention RAG-available to agents.

There is NO committed ``capabilities.yaml`` / ``patent_elements.yaml`` — a fourth copy would
duplicate those three. Passes (no LLM):

  derived  — per service, read its live ``tools/list`` and register the Service plus a
             Capability carrying keywords drawn from its tool surface. Journeyman-signed.
  patent   — parse the committed ``docs/patent/REFERENCE-NUMERAL-SCHEDULE.md`` (the source of
             truth for the numerals) into ``PatentElement`` nodes. Journeyman-signed.
  authored — write the cross-cutting Capability whys + Invariants + patent links. The whys
             are grounded in the patent narrative and code docstrings; they are authored
             DIRECTLY into the graph (the intention store), driven by a TRANSIENT,
             UNCOMMITTED manifest passed via ``--manifest`` (scratchpad) — never in change
             control. Whys/invariants are **Operator**-signed ('human-authored'); structural
             edges + patent links are Journeyman-signed. No provenance is ever a parameter.

The security boundary is the *key*: a Journeyman (LLM) key can only reach the
no-provenance / advice templates; only the Operator key reaches the 'human-authored' ones.
This script merely signs each call with the right role's nsec; the cypher-mcp gate is the
enforcer. See ``cypher-mcp/scripts/factory_vocabulary.py``.

OPSEC — the two passes run in different places, with different keys:
  * ``--mode derived`` is the RECURRING job (scheduled CI), signed with the factory's OWN
    ``JOURNEYMAN_NSEC``. No other operator's nsec is ever placed in that CI.
  * ``--mode authored`` is run OCCASIONALLY BY THE HUMAN who owns the cypher graph, with
    that owner's own operator nsec fed from a secure file — never a standing CI secret.
    No domain holds another operator's nsec on a recurring basis.

Usage:
    # preview any plan without a server or any nsec:
    python scripts/intention_harvest.py --dry-run --mode derived

    # recurring derived pass (CI or you), Journeyman key from env:
    JOURNEYMAN_NSEC="$(cat <secure-file>)" \
      python scripts/intention_harvest.py --mode derived \
        --journeyman-npub npub1... --url https://cypher-mcp.fastmcp.app/mcp

    # occasional authored pass (human-run only), operator/graph-owner key from a secure file:
    OPERATOR_NSEC="$(cat <secure-file>)" \
      python scripts/intention_harvest.py --mode authored \
        --operator-npub npub1... --url https://cypher-mcp.fastmcp.app/mcp
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError:  # pragma: no cover - yaml is a runtime dep; tests install it
    yaml = None

SLUG = "cypher"

# Roles — the calling identity per template. Source of truth for the gate lives in
# cypher-mcp/scripts/factory_vocabulary.py (allow_roles); this mirrors the write subset the
# harvester uses so we sign each call with the right key.
JOURNEYMAN = "journeyman"
OPERATOR = "operator"

ROLE_FOR_TOOL: dict[str, str] = {
    "register_service": JOURNEYMAN,
    "upsert_capability": JOURNEYMAN,
    "link_capability_consumer": JOURNEYMAN,
    "bind_capability_to_symbol": JOURNEYMAN,
    "index_symbol": JOURNEYMAN,
    "authorize_capability_why": OPERATOR,
    "assert_invariant": OPERATOR,
    "guard_invariant_symbol": OPERATOR,
    # Patent tracing — a citation index of the public reference-numeral schedule.
    "upsert_patent_element": JOURNEYMAN,
    "link_capability_to_patent": JOURNEYMAN,
    "link_invariant_to_patent": JOURNEYMAN,
}


@dataclass(frozen=True)
class Call:
    """One planned write: which role signs it, which published tool, with what params."""
    tool: str
    params: dict[str, Any]

    @property
    def role(self) -> str:
        return ROLE_FOR_TOOL[self.tool]


def _call(tool: str, **params: Any) -> Call:
    if tool not in ROLE_FOR_TOOL:
        raise KeyError(f"unknown factory tool: {tool}")
    return Call(tool=tool, params=params)


# --------------------------------------------------------------------------- #
# Pure planning (unit-tested; no I/O)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Service:
    name: str
    npub: str
    url: str
    description: str = ""


def canonical_service_name(name: str | None) -> str | None:
    """Normalize a member record's service name to a canonical repo slug, or None to skip.

    members/operators/*.json is inconsistent: some names are already slugs
    ('schwab-mcp'), one is a display name ('Excalibur MCP' -> 'excalibur-mcp'), and a few
    placeholder records carry the npub as the name. Slugifying handles the display names;
    npub-as-name records are malformed and skipped. Canonical names must match the repo
    slugs the graph keys Services by, or the graph fragments.
    """
    if not name or name.lower().startswith("npub1"):
        return None
    return "-".join(name.lower().split())


def load_operators(operators_dir: Path) -> list[Service]:
    """Read members/operators/*.json into a flat list of Services (one per service entry).

    Service names are normalized to canonical repo slugs; unresolvable (npub-as-name)
    records are skipped with a warning — never silently dropped.
    """
    services: list[Service] = []
    for path in sorted(Path(operators_dir).glob("*.json")):
        rec = json.loads(path.read_text())
        npub = rec.get("npub", "")
        if rec.get("role") != "operator" or not npub:
            continue
        for svc in rec.get("services", []) or []:
            name = canonical_service_name(svc.get("name"))
            if not name:
                print(f"  ! skipping unnamed/placeholder service in {path.name} "
                      f"(name={svc.get('name')!r})", file=sys.stderr)
                continue
            services.append(Service(
                name=name, npub=npub,
                url=svc.get("url", ""), description=svc.get("description", ""),
            ))
    return services


def _tool_base_name(tool_name: str) -> str:
    """'schwab_get_option_chain' -> 'get option chain' (strip the service slug prefix)."""
    base = tool_name.split("_", 1)[-1] if "_" in tool_name else tool_name
    return base.replace("_", " ").strip()


def keywords_from_tools(service: Service, tools: Iterable[dict[str, Any]]) -> str:
    """Derive a comma-joined keyword blob from a service's tool surface + its description.

    Deterministic and order-stable: unique tool base-names (sans slug prefix), then the
    service description. This is what which_service_handles(keyword) matches on.
    """
    seen: list[str] = []

    def add(term: str) -> None:
        term = " ".join(term.lower().split())
        if term and term not in seen:
            seen.append(term)

    for t in tools:
        name = t.get("name") or ""
        if name:
            add(_tool_base_name(name))
    if service.description:
        add(service.description)
    return ", ".join(seen)


def plan_derived(services: list[Service],
                 tools_by_service: dict[str, list[dict[str, Any]]]) -> list[Call]:
    """The per-service derived pass: register each Service and a keyword Capability for it.

    Only services we could reach (present in tools_by_service) get a Capability; every
    known service is still registered so the graph knows the actor exists.
    """
    calls: list[Call] = []
    for svc in services:
        calls.append(_call("register_service", repo_npub=svc.npub, repo_name=svc.name))
        tools = tools_by_service.get(svc.name)
        if tools is None:
            continue
        cap = f"{svc.name} service"
        calls.append(_call("upsert_capability", name=cap, owner_repo=svc.name,
                            keywords=keywords_from_tools(svc, tools)))
    return calls


def plan_authored(manifest: dict[str, Any]) -> list[Call]:
    """The authored pass: transcribe the (transient, uncommitted) manifest into the graph.

    Structural edges (owners/consumers/symbols) are Journeyman writes (no provenance); the
    authoritative why and the invariants are Operator writes (provenance 'human-authored',
    fixed by the template). Ordered so a Capability/Invariant node exists before edges
    reference it.
    """
    calls: list[Call] = []
    for cap in manifest.get("capabilities", []) or []:
        name = cap["name"]
        keywords = cap.get("keywords", "")
        owners = cap.get("owners", []) or []
        # Structure first (Journeyman): each owner creates the Capability + OWNED_BY.
        for owner in owners:
            calls.append(_call("upsert_capability", name=name, owner_repo=owner,
                               keywords=keywords))
        for consumer in cap.get("consumers", []) or []:
            calls.append(_call("link_capability_consumer", name=name, consumer_repo=consumer))
        for fqn in cap.get("symbols", []) or []:
            calls.append(_call("bind_capability_to_symbol", name=name, symbol_fqn=fqn))
        # Authoritative why (Operator).
        if cap.get("why"):
            calls.append(_call("authorize_capability_why", name=name,
                               why=" ".join(cap["why"].split())))
    for inv in manifest.get("invariants", []) or []:
        name = inv["name"]
        calls.append(_call("assert_invariant", name=name,
                           rule=" ".join(inv.get("rule", "").split())))
        for fqn in inv.get("guards", []) or []:
            calls.append(_call("guard_invariant_symbol", name=name, symbol_fqn=fqn))
    return calls


def load_manifest(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("pyyaml is required to read the manifest")
    return yaml.safe_load(Path(path).read_text()) or {}


def parse_patent_schedule(md_path: Path) -> list[dict[str, Any]]:
    """Parse the committed REFERENCE-NUMERAL-SCHEDULE.md into PatentElement rows.

    The patent doc IS the source of truth for the numerals — there is no mirror file.
    Each ``## <Section>`` header becomes the element's claim_family; each table row
    ``| <ref> | <name> | <figures> |`` becomes an element. DRY: the graph is populated
    straight from the authoritative document.
    """
    elements: list[dict[str, Any]] = []
    section = ""
    for line in Path(md_path).read_text().splitlines():
        s = line.strip()
        if s.startswith("## "):
            section = s[3:].strip()
            continue
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) >= 3 and cells[0].isdigit():
                elements.append({"ref": int(cells[0]), "name": cells[1],
                                 "figures": cells[2], "claim_family": section})
    return elements


def plan_patent(elements: list[dict[str, Any]], manifest: dict[str, Any]) -> list[Call]:
    """The patent pass: transcribe the reference-numeral schedule into PatentElement nodes
    and trace each capability/invariant to the numerals it is DESCRIBED_IN. A citation
    index — Journeyman-signed. Requires the patent templates to be seeded + priced first.
    """
    calls: list[Call] = []
    for e in elements:
        calls.append(_call("upsert_patent_element", ref=int(e["ref"]), name=e["name"],
                           figures=str(e.get("figures", "")), claim_family=e.get("claim_family", "")))
    for cap in manifest.get("capabilities", []) or []:
        for ref in cap.get("patent_refs", []) or []:
            calls.append(_call("link_capability_to_patent", name=cap["name"], patent_ref=int(ref)))
    for inv in manifest.get("invariants", []) or []:
        for ref in inv.get("patent_refs", []) or []:
            calls.append(_call("link_invariant_to_patent", name=inv["name"], patent_ref=int(ref)))
    return calls


# --------------------------------------------------------------------------- #
# Driver (live)
# --------------------------------------------------------------------------- #

@dataclass
class RoleKey:
    npub: str
    nsec: str


def npub_from_nsec(nsec: str) -> str:
    """Derive the bech32 npub from an nsec — the nsec fully determines it. So the recurring
    harvester needs only the JOURNEYMAN_NSEC secret (already set fleet-wide by
    bootstrap-factory-secrets.sh); no separate npub var to configure or drift."""
    if not nsec:
        return ""
    from pynostr.key import PrivateKey
    return PrivateKey.from_nsec(nsec).public_key.bech32()


async def _list_tools(url: str) -> list[dict[str, Any]]:
    from fastmcp import Client
    async with Client(url) as client:
        tools = await client.list_tools()
    out: list[dict[str, Any]] = []
    for t in tools:
        out.append({"name": getattr(t, "name", ""),
                    "description": getattr(t, "description", "") or ""})
    return out


async def _apply(url: str, calls: list[Call], keys: dict[str, RoleKey]) -> int:
    from fastmcp import Client
    from tollbooth.identity_proof import create_proof

    missing = {c.role for c in calls} - {r for r, k in keys.items() if k.npub and k.nsec}
    if missing:
        print(f"  ! missing key(s) for role(s): {sorted(missing)}", file=sys.stderr)
        return 2

    async with Client(url) as client:
        async def call(c: Call) -> dict[str, Any]:
            key = keys[c.role]
            # create_proof signs at whole-second resolution with a fixed body, so two calls
            # for the same tool in one second mint an identical event (replay-rejected).
            # Re-sign after the second ticks over.
            for attempt in range(3):
                payload = {**c.params, "npub": key.npub,
                           "dpop_token": create_proof(key.nsec, f"{SLUG}_{c.tool}")}
                res = await client.call_tool(f"{SLUG}_{c.tool}", payload)
                data = res.data if hasattr(res, "data") else res
                data = data if isinstance(data, dict) else {"raw": data}
                if "proof" in str(data.get("error", "")).lower() and attempt < 2:
                    await asyncio.sleep(1.1)
                    continue
                return data
            return data

        ok = 0
        for c in calls:
            r = await call(c)
            err = r.get("error")
            print(f"  [{c.role}] {c.tool} {json.dumps(c.params)[:80]}: "
                  f"{r.get('message') or err or 'ok'}")
            ok += 0 if err else 1
        print(f"  applied {ok}/{len(calls)} calls")
    return 0 if ok == len(calls) else 1


def _print_plan(calls: list[Call]) -> None:
    by_role: dict[str, int] = {}
    for c in calls:
        by_role[c.role] = by_role.get(c.role, 0) + 1
        print(f"  [{c.role}] {SLUG}_{c.tool}({json.dumps(c.params)})")
    print(f"  -- {len(calls)} calls: " +
          ", ".join(f"{n} {r}" for r, n in sorted(by_role.items())))


# --------------------------------------------------------------------------- #

def build_plan(mode: str, services: list[Service],
               tools_by_service: dict[str, list[dict[str, Any]]],
               manifest: dict[str, Any],
               patent_elements: list[dict[str, Any]]) -> list[Call]:
    calls: list[Call] = []
    if mode in ("derived", "all"):
        calls += plan_derived(services, tools_by_service)
    if mode in ("authored", "all"):
        calls += plan_authored(manifest)
    if mode in ("patent", "all"):
        calls += plan_patent(patent_elements, manifest)
    return calls


def main() -> int:
    here = Path(__file__).resolve().parent
    root = here.parent  # dpyc-community/
    ap = argparse.ArgumentParser(description="Harvest the Intention Service forward map.")
    ap.add_argument("--mode", choices=["derived", "authored", "patent", "all"], default="all")
    ap.add_argument("--url", default=os.environ.get("CYPHER_MCP_URL",
                                                    "https://cypher-mcp.fastmcp.app/mcp"))
    ap.add_argument("--operators-dir", default=str(root / "members" / "operators"))
    # Patent elements are parsed straight from the committed patent doc (the source of truth) —
    # no mirror file. The capability manifest is a TRANSIENT, UNCOMMITTED authoring input
    # (scratchpad) used only for an occasional authored/link run; it is never in change control.
    ap.add_argument("--patents", default=str(root / "docs" / "patent" / "REFERENCE-NUMERAL-SCHEDULE.md"),
                    help="the committed patent reference-numeral schedule (markdown).")
    ap.add_argument("--manifest", default="",
                    help="OPTIONAL transient capability manifest (uncommitted) for an authoring run.")
    ap.add_argument("--journeyman-npub", default=os.environ.get("JOURNEYMAN_NPUB", ""))
    ap.add_argument("--operator-npub", default=os.environ.get("OPERATOR_NPUB", ""))
    ap.add_argument("--dry-run", action="store_true",
                    help="print the write plan; no network, no nsec")
    args = ap.parse_args()

    services = load_operators(Path(args.operators_dir))
    # The manifest (capability whys + patent links) is optional and never committed. Patent
    # element NODES come from the committed doc regardless.
    manifest = (load_manifest(Path(args.manifest))
                if args.manifest and args.mode in ("authored", "patent", "all") else {})
    patent_elements = (parse_patent_schedule(Path(args.patents))
                       if args.mode in ("patent", "all") else [])

    # In derived mode we need each reachable service's live tool surface.
    tools_by_service: dict[str, list[dict[str, Any]]] = {}
    if args.mode in ("derived", "all") and not args.dry_run:
        for svc in services:
            if not svc.url:
                continue
            try:
                tools_by_service[svc.name] = asyncio.run(_list_tools(svc.url))
            except Exception as exc:  # a cold/unreachable service is skipped, not fatal
                print(f"  ! tools/list failed for {svc.name}: {exc}", file=sys.stderr)

    calls = build_plan(args.mode, services, tools_by_service, manifest, patent_elements)

    if args.dry_run:
        _print_plan(calls)
        return 0

    # npub defaults to the value derived from the matching nsec (the nsec determines it),
    # so a CI run needs only the *_NSEC secret — no npub var to set or keep in sync.
    jnsec = os.environ.get("JOURNEYMAN_NSEC", "")
    onsec = os.environ.get("OPERATOR_NSEC", "")
    keys = {
        JOURNEYMAN: RoleKey(args.journeyman_npub or npub_from_nsec(jnsec), jnsec),
        OPERATOR: RoleKey(args.operator_npub or npub_from_nsec(onsec), onsec),
    }
    return asyncio.run(_apply(args.url, calls, keys))


if __name__ == "__main__":
    raise SystemExit(main())
