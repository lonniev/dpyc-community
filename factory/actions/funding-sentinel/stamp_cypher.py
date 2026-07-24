"""Stamp the funding-outage state onto the intention graph — DETERMINISTIC, no LLM.

The sibling of the GitHub `awaiting-funds` label: when a broke ANTHROPIC_API_KEY defers an
agent, the funding-sentinel tags the issue/PR on GitHub AND calls this to reflect the same
fact in the cypher graph, so "what is awaiting funds" is queryable even while every LLM node
is dark. The credit canary calls it again with --state clear on recovery, in lockstep with
clearing the label.

This pays *sats*, not LLM credits — an orthogonal funding rail — via the operator's published
`cypher_mark_funding_state` tool, signed with a patron nsec (Porter/Journeyman). It is
strictly BEST-EFFORT: the GitHub label is the authoritative breadcrumb; a graph-stamp failure
(Cypher's own 402, an expired proof, a cold start, no nsec) must NEVER fail the catch. So every
path here exits 0.

Identity is nsec-only: the npub is a pure function of the nsec, so we derive it rather than
ask for both (no chance of a mismatch).

Env:
  DPYC_KEYRING_UPSTREAM  the operator MCP URL (defaults to the cypher-mcp cloud endpoint)
  STAMP_NSEC             the calling agent's patron nsec (held only here, never emitted)

Usage:
  python3 stamp_cypher.py --repo <repo_name> --kind issue|pr --number <n> --state awaiting-funds|clear
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

DEFAULT_UPSTREAM = "https://cypher-mcp.fastmcp.app/mcp"


def _npub_from_nsec(nsec: str) -> str:
    """Derive the bech32 npub from an nsec (bech32 ``nsec1…`` or hex) — the SDK's own idiom."""
    from pynostr.key import PrivateKey  # type: ignore[import-untyped]

    pk = PrivateKey.from_nsec(nsec) if nsec.startswith("nsec1") else PrivateKey(bytes.fromhex(nsec))
    return pk.public_key.bech32()


async def _stamp(upstream: str, nsec: str,
                 repo: str, kind: str, number: int, state: str, url: str) -> None:
    # Lazy imports: the SDK primitive that mints the proof, and the MCP client. Reusing
    # PatronSigner keeps proof-signing DRY (never reimplement crypto).
    from tollbooth.patron_signer import PatronSigner
    from fastmcp import Client

    npub = _npub_from_nsec(nsec)
    # 'historical' retires the block (breaks its BLOCKS edge, keeps the node) when its item
    # closed while awaiting funds; awaiting-funds/clear set the state on an active block.
    if state == "historical":
        tool = "cypher_retire_funding_block"
        params = {"repo_name": repo, "kind": kind, "number": number}
    else:
        tool = "cypher_mark_funding_state"
        params = {"repo_name": repo, "kind": kind, "number": number, "state": state, "url": url}
    signed = PatronSigner(npub, nsec).authenticate(tool, params)  # injects npub + fresh kind-27235 proof
    async with Client(upstream) as client:
        res = await client.call_tool(tool, signed)
        print(f"stamp_cypher: {tool}({repo} {kind}#{number} -> {state}) ok: "
              f"{getattr(res, 'data', res)}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Reflect a funding-outage (or its clearance) in the cypher graph.")
    ap.add_argument("--repo", required=True, help="Repository name (short, e.g. 'tollbooth-sample').")
    ap.add_argument("--kind", required=True, choices=["issue", "pr"])
    ap.add_argument("--number", required=True, type=int)
    ap.add_argument("--state", required=True, choices=["awaiting-funds", "clear", "historical"])
    ap.add_argument("--url", default="",
                    help="Canonical GitHub URL of the issue/PR (built from CI env; required for "
                         "awaiting-funds/clear, unused for historical).")
    ap.add_argument("--upstream", default=os.environ.get("DPYC_KEYRING_UPSTREAM", DEFAULT_UPSTREAM))
    args = ap.parse_args()

    nsec = os.environ.get("STAMP_NSEC", "").strip()
    if not nsec:
        print("stamp_cypher: no STAMP_NSEC — skipping graph stamp (best-effort).", file=sys.stderr)
        return 0

    try:
        asyncio.run(_stamp(args.upstream, nsec, args.repo, args.kind, args.number, args.state, args.url))
    except Exception as e:  # noqa: BLE001 — a catch handler must never throw; the label already carries the fact.
        print(f"stamp_cypher: graph stamp failed (best-effort, ignored): {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
