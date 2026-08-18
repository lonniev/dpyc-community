"""Mirror a GitHub Pull Request into the intention graph — DETERMINISTIC, no LLM.

Fired by the pr-mirror workflow on every `pull_request` event (opened, ready_for_review,
converted_to_draft, synchronize, reopened, closed), so a PR is visible in the cypher Lab
Notebook WHILE IT IS ACTIVE — the analyst's board of upcoming changes — not only after it
merges. It calls the operator's `cypher_upsert_pull_request` tool, which MERGEs a
:PullRequest node keyed by (repo_name, number) and SETs its live state.

This pays *sats*, signed with the Journeyman patron nsec (the same identity that writes the
FIXES edge via `link_pr`). Identity is nsec-only: the npub is a pure function of the nsec, so
we derive it rather than ask for both. It is BEST-EFFORT — a graph miss (Cypher's own 402, an
expired proof, a cold start, no nsec) must never fail a PR's checks; the next event heals the
mirror. So every path exits 0.

Env:
  DPYC_KEYRING_UPSTREAM  the operator MCP URL (defaults to the cypher-mcp cloud endpoint)
  MIRROR_NSEC            the Journeyman patron nsec (held only here, never emitted)

Usage:
  python3 mirror_pr.py --repo <repo_name> --number <n> --url <html_url> --title <t> \
      --state open|closed [--draft true|false] [--author <login>] [--head-sha <sha>] \
      [--base-ref <ref>] [--head-ref <ref>] [--merged-at <iso>] [--created-at <iso>]
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


async def _mirror(upstream: str, nsec: str, params: dict) -> None:
    # Reuse the SDK's proof-signer + MCP client (never reimplement crypto).
    from fastmcp import Client
    from tollbooth.patron_signer import PatronSigner

    npub = _npub_from_nsec(nsec)
    tool = "cypher_upsert_pull_request"
    signed = PatronSigner(npub, nsec).authenticate(tool, params)  # injects npub + fresh kind-27235 proof
    async with Client(upstream) as client:
        res = await client.call_tool(tool, signed)
        print(f"mirror_pr: {tool}({params['repo_name']}#{params['number']} -> {params['state']}) ok: "
              f"{getattr(res, 'data', res)}")


def _opt(v: str) -> str | None:
    """An empty CLI string (an absent GitHub field) becomes a bound null, not ''."""
    v = (v or "").strip()
    return v or None


def main() -> int:
    ap = argparse.ArgumentParser(description="Mirror a GitHub PR into the cypher intention graph.")
    ap.add_argument("--repo", required=True, help="Repository name (short, e.g. 'cypher-mcp').")
    ap.add_argument("--number", required=True, type=int)
    ap.add_argument("--url", required=True, help="The PR's canonical GitHub URL (html_url).")
    ap.add_argument("--title", required=True)
    ap.add_argument("--state", required=True, choices=["open", "closed"])
    ap.add_argument("--draft", default="false", choices=["true", "false"])
    ap.add_argument("--author", default="")
    ap.add_argument("--head-sha", default="")
    ap.add_argument("--base-ref", default="")
    ap.add_argument("--head-ref", default="")
    ap.add_argument("--merged-at", default="")
    ap.add_argument("--created-at", default="")
    ap.add_argument("--upstream", default=os.environ.get("DPYC_KEYRING_UPSTREAM", DEFAULT_UPSTREAM))
    args = ap.parse_args()

    nsec = os.environ.get("MIRROR_NSEC", "").strip()
    if not nsec:
        print("mirror_pr: no MIRROR_NSEC — skipping graph mirror (best-effort).", file=sys.stderr)
        return 0

    params = {
        "repo_name": args.repo,
        "number": args.number,
        "url": args.url,
        "title": args.title,
        "state": args.state,
        "draft": args.draft == "true",
        "author": _opt(args.author),
        "head_sha": _opt(args.head_sha),
        "base_ref": _opt(args.base_ref),
        "head_ref": _opt(args.head_ref),
        "merged_at": _opt(args.merged_at),
        "created_at": _opt(args.created_at),
    }

    try:
        asyncio.run(_mirror(args.upstream, nsec, params))
    except Exception as e:  # noqa: BLE001 — the mirror is best-effort; the next event heals it.
        print(f"mirror_pr: graph mirror failed (best-effort, ignored): {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
