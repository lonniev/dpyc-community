#!/usr/bin/env python3
"""Weekly audit of every operator's bootstrap config on the Nostr relays.

Asks the Oracle for the Authorities, then calls each one's
``authority_audit_bootstrap_configs``. That tool measures how many relays hold
each operator's config, republishes any held by fewer than three relays or sent
more than six days ago, and measures again, all before it answers. It runs in
the foreground because Horizon freezes a process between requests, so a
background refresh rarely finished (2026-09-29: four operators were left with
no copy on any relay).

Exits non-zero when an Authority cannot be audited or an operator is still
thin afterwards, so a red run tells the owner.

Usage:
    python scripts/audit-bootstrap-configs.py
"""

import asyncio
import json
import os
import sys

try:
    from fastmcp import Client
except ImportError:
    print("fastmcp required: pip install fastmcp", file=sys.stderr)
    sys.exit(1)

ORACLE_URL = "https://dpyc-oracle.fastmcp.app/mcp"
AUDIT_TOOL = "authority_audit_bootstrap_configs"


def _body(result) -> dict:
    if isinstance(getattr(result, "data", None), dict):
        return result.data
    return json.loads(result.content[0].text)


async def _authorities() -> list[dict]:
    async with Client(ORACLE_URL) as oracle:
        listing = _body(await oracle.call_tool("list_services", {"kind": "authority", "probe": False}))
    return [s for s in listing.get("services", []) if s.get("role") == "authority" and s.get("url")]


async def _audit(authority: dict) -> dict:
    try:
        async with Client(authority["url"]) as client:
            return _body(await client.call_tool(AUDIT_TOOL, {}, raise_on_error=False))
    except Exception as exc:  # noqa: BLE001 — reported, and fails the run
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}


def _report(name: str, result: dict) -> list[str]:
    lines = [f"### {name}", ""]
    if not result.get("success"):
        return lines + [f"**Audit failed:** {result.get('error', result)}", ""]
    lines += [
        f"{len(result['operators'])} operators, {result['relays']} relays in the registry.",
        "",
        "| Operator | Relays before | Relays after | Republished | Why |",
        "|---|---|---|---|---|",
    ]
    for o in result["operators"]:
        lines.append(
            f"| `{o['operator']}` | {o['holders_before']} | {o['holders_after']} "
            f"| {'yes' if o['republished'] else ''} | {o['reason']} |"
        )
    if result["still_thin"]:
        lines += ["", f"**Still thin:** {', '.join(result['still_thin'])}"]
    return lines + [""]


async def _audit_all() -> tuple[list[dict], list[dict]]:
    authorities = await _authorities()
    return authorities, await asyncio.gather(*(_audit(a) for a in authorities))


def main() -> int:
    authorities, results = asyncio.run(_audit_all())
    if not authorities:
        print("The Oracle listed no Authorities.", file=sys.stderr)
        return 1

    lines = ["## Bootstrap config audit", ""]
    healthy = True
    for authority, result in zip(authorities, results, strict=True):
        lines += _report(authority.get("display_name") or authority["service_name"], result)
        healthy &= bool(result.get("success")) and not result.get("still_thin")

    text = "\n".join(lines)
    print(text)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a") as f:
            f.write(text + "\n")
    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(main())
