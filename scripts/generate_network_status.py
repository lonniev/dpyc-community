#!/usr/bin/env python3
"""Regenerate network-status.json from live fleet state (issue #112).

`network-status.json` is CLAUDE.md §7's "authoritative snapshot", yet it was
hand-maintained and therefore rotted (it claimed the fleet was two releases
behind where it actually was). The durable fix is to *derive* the machine-known
parts — the running version of each component, and the fleet's `tollbooth-dpyc`
SDK version — from the same stateless `*_service_status` probe that
`deploy-verify.yml` uses, while preserving the human-authored `minimum` floors,
`changelog_url`s, `advisory`, `architecture_notes`, and `protocols`.

The probe layer (network) is kept separate from `assemble_network_status` (pure)
so the assembler can be unit-tested with canned payloads and no network — see
tests/test_generate_network_status.py.

A component is refreshed only if a probe reports it; unreachable or oracle-shaped
endpoints are skipped, not failed, and their previous `current` is preserved. New
services with no human-authored floor are NOT invented — `minimum` is a security
floor only a human may set.

Usage:
    python scripts/generate_network_status.py            # probe + rewrite the file
    python scripts/generate_network_status.py --dry-run  # print, don't write
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MEMBERS_DIR = REPO_ROOT / "members"
OUTPUT = REPO_ROOT / "network-status.json"

# The role directories whose services expose a *_service_status tool worth probing.
MEMBER_DIRS = ("operators", "authorities", "advocates")
TIMEOUT = 25.0


# --------------------------------------------------------------------------- #
# Pure assembler — no network, unit-tested.
# --------------------------------------------------------------------------- #
def _version_key(version: str) -> tuple:
    """Sort key that orders versions numerically ('1.10.0' > '1.9.0')."""
    parts = []
    for chunk in str(version).split("."):
        num = "".join(c for c in chunk if c.isdigit())
        parts.append(int(num) if num else 0)
    return tuple(parts)


def latest_version(versions) -> str | None:
    """Return the highest version string, or None if there are none."""
    versions = [v for v in versions if v]
    if not versions:
        return None
    return max(versions, key=_version_key)


def assemble_network_status(existing: dict, probes: list, last_updated: str) -> dict:
    """Refresh the machine-derivable parts of the snapshot from probe payloads.

    ``existing``     the current network-status.json (preserves component order,
                     ``minimum``, ``changelog_url``, and the human prose sections).
    ``probes``       a list of ``*_service_status`` payload dicts; each contributes
                     ``current`` for its ``service`` and its ``tollbooth_dpyc_version``
                     toward the fleet SDK version. Malformed payloads are ignored.
    ``last_updated`` ISO date to stamp.
    """
    # 1. Fold probes into per-component versions + the fleet SDK version.
    derived: dict[str, str] = {}
    dpyc_versions: list[str] = []
    for p in probes:
        if not isinstance(p, dict):
            continue
        service = p.get("service")
        version = p.get("version")
        if service and version:
            derived[service] = version
        sdk = p.get("tollbooth_dpyc_version")
        if sdk:
            dpyc_versions.append(sdk)
    fleet_sdk = latest_version(dpyc_versions)
    if fleet_sdk:
        derived["tollbooth-dpyc"] = fleet_sdk

    # 2. Rebuild components in the existing order, refreshing only `current`.
    #    Unprobed components keep their prior value; `minimum`/`changelog_url` are
    #    human-authored and copied verbatim. New probed services are NOT added —
    #    a component without a human-set `minimum` floor would be a fabrication.
    components: dict[str, dict] = {}
    for key, comp in existing.get("components", {}).items():
        refreshed = dict(comp)
        if key in derived:
            refreshed["current"] = derived[key]
        components[key] = refreshed

    # 3. Reassemble, preserving human prose + protocols verbatim, stamping the date.
    return {
        "components": components,
        "protocols": existing.get("protocols", []),
        "last_updated": last_updated,
        "advisory": existing.get("advisory", ""),
        "architecture_notes": existing.get("architecture_notes", ""),
    }


# --------------------------------------------------------------------------- #
# Network layer — stateless MCP probe (mirrors deploy-verify.yml).
# --------------------------------------------------------------------------- #
def _parse_sse_json(text: str) -> dict:
    """Extract the JSON-RPC response from an SSE text/event-stream body."""
    for line in text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _mcp_call(url: str, method: str, params: dict) -> dict:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return _parse_sse_json(resp.read().decode())


def probe_service(url: str) -> dict | None:
    """Return a service's ``*_service_status`` payload, or None if unavailable.

    The status tool is named per-operator (weather_service_status, bare
    service_status, ...), so it is discovered from tools/list by suffix rather
    than guessed — exactly as deploy-verify.yml does.
    """
    listed = _mcp_call(url, "tools/list", {})
    tools = listed.get("result", {}).get("tools", [])
    status_tool = next(
        (t["name"] for t in tools if t.get("name", "").endswith("service_status")),
        None,
    )
    if not status_tool:
        return None  # oracle-shaped / no status tool
    called = _mcp_call(url, "tools/call", {"name": status_tool, "arguments": {}})
    content = called.get("result", {}).get("content", [])
    if content and content[0].get("type") == "text":
        return json.loads(content[0]["text"])
    return None


def load_service_urls(members_dir: Path = MEMBERS_DIR) -> list[tuple]:
    """Collect (display_name, url) for every active member service on an /mcp endpoint."""
    services = []
    for role_dir in MEMBER_DIRS:
        for path in sorted(glob.glob(str(members_dir / role_dir / "*.json"))):
            member = json.loads(Path(path).read_text())
            if member.get("status") != "active":
                continue
            for svc in member.get("services", []):
                url = svc.get("url", "")
                if url.endswith("/mcp"):
                    services.append((svc.get("name", url), url))
    return services


def collect_probes(services: list) -> list:
    """Probe every service, skipping (not failing) the unreachable ones."""
    probes = []
    for name, url in services:
        try:
            payload = probe_service(url)
        except Exception as e:  # noqa: BLE001 — unreachable is expected, not fatal
            print(f"  skip {name} ({url}): {str(e)[:120]}", file=sys.stderr)
            continue
        if payload:
            print(
                f"  ok   {name}: {payload.get('service')} "
                f"v{payload.get('version')} (dpyc {payload.get('tollbooth_dpyc_version')})",
                file=sys.stderr,
            )
            probes.append(payload)
        else:
            print(f"  skip {name} ({url}): no service_status tool", file=sys.stderr)
    return probes


def write_status(status: dict, output: Path = OUTPUT) -> None:
    """Write the snapshot deterministically (indent=2, trailing newline)."""
    output.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print, don't write")
    args = parser.parse_args(argv)

    existing = json.loads(OUTPUT.read_text())
    services = load_service_urls()
    print(f"Probing {len(services)} member services...", file=sys.stderr)
    probes = collect_probes(services)

    today = datetime.now(timezone.utc).date().isoformat()
    status = assemble_network_status(existing, probes, last_updated=today)

    if args.dry_run:
        print(json.dumps(status, indent=2, ensure_ascii=False))
        return 0

    write_status(status)
    print(f"Wrote {OUTPUT} ({len(probes)} services probed, stamped {today}).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
