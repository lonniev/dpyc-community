#!/usr/bin/env python3
"""Collect OTS notarization status from all registered operators.

Reads the member registry, calls list_notarizations on each operator's
MCP endpoint, and writes docs/ots-status.json with bounded history
(max 10 notarizations per operator, max 30 days old).

Usage:
    python scripts/collect-ots-status.py
"""

import asyncio
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import httpx
except ImportError:
    print("httpx required: pip install httpx", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY = REPO_ROOT / "members" / "read-only-lookup-cache.json"
OUTPUT = REPO_ROOT / "docs" / "ots-status.json"

MAX_ENTRIES_PER_OPERATOR = 10
MAX_AGE_DAYS = 30
TIMEOUT = 15.0


def _parse_sse_json(text: str) -> dict:
    """Extract the JSON-RPC response from an SSE text/event-stream body."""
    for line in text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return {}


async def call_list_notarizations(endpoint: str) -> list[dict]:
    """Call list_notarizations via MCP Streamable-HTTP."""
    url = endpoint.rstrip("/")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Initialize session
        init_body = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "ots-collector", "version": "1.0"},
            },
        }
        init_resp = await client.post(url, json=init_body, headers=headers)
        session_id = init_resp.headers.get("mcp-session-id", "")
        if session_id:
            headers["mcp-session-id"] = session_id

        # Discover the slug-prefixed tool name
        list_body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        list_resp = await client.post(url, json=list_body, headers=headers)
        ct_list = list_resp.headers.get("content-type", "")
        if "text/event-stream" in ct_list:
            list_data = _parse_sse_json(list_resp.text)
        else:
            list_data = list_resp.json()
        tools = list_data.get("result", {}).get("tools", [])
        tool_name = next(
            (t["name"] for t in tools if t["name"].endswith("_list_notarizations")),
            None,
        )
        if not tool_name:
            return []  # OTS not enabled on this operator

        # Call list_notarizations
        body = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": {"limit": MAX_ENTRIES_PER_OPERATOR},
            },
        }
        resp = await client.post(url, json=body, headers=headers)
        resp.raise_for_status()

        # Response may be JSON or SSE — handle both
        ct = resp.headers.get("content-type", "")
        if "text/event-stream" in ct:
            data = _parse_sse_json(resp.text)
        else:
            data = resp.json()

        # MCP response: {"result": {"content": [{"type": "text", "text": "..."}]}}
        content = data.get("result", {}).get("content", [])
        if content and content[0].get("type") == "text":
            parsed = json.loads(content[0]["text"])
            return parsed.get("notarizations", [])
    return []


async def collect_all() -> dict:
    """Collect OTS status from all operators."""
    with open(REGISTRY) as f:
        registry = json.load(f)

    members = registry.get("members", [])
    cutoff = (datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)).isoformat()

    operators = []
    for m in members:
        if m.get("role") not in ("operator", "authority"):
            continue
        services = m.get("services", [])
        endpoint = services[0]["url"] if services else ""
        if not endpoint:
            continue
        operators.append({
            "npub": m["npub"],
            "display_name": m.get("display_name", m["npub"][:20]),
            "endpoint": endpoint,
            "role": m["role"],
        })

    results = []
    for op in operators:
        entry = {
            "npub": op["npub"],
            "display_name": op["display_name"],
            "role": op["role"],
            "notarizations": [],
            "status": "unreachable",
            "error": None,
        }
        try:
            notarizations = await call_list_notarizations(op["endpoint"])
            # Filter old entries and cap count
            recent = [
                n for n in notarizations
                if n.get("created_at", "") >= cutoff
            ][:MAX_ENTRIES_PER_OPERATOR]
            entry["notarizations"] = recent

            if not recent:
                entry["status"] = "never"
            else:
                latest_status = recent[0].get("status", "unknown")
                # Check staleness: no notarization in 7 days
                latest_created = recent[0].get("created_at", "")
                stale_cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
                if latest_created < stale_cutoff:
                    entry["status"] = "stale"
                else:
                    entry["status"] = latest_status
        except Exception as e:
            entry["error"] = str(e)[:200]

        results.append(entry)

    # Summary stats
    total_notarizations = sum(len(r["notarizations"]) for r in results)
    confirmed = sum(
        sum(1 for n in r["notarizations"] if n.get("status") == "confirmed")
        for r in results
    )
    active_this_week = sum(
        1 for r in results
        if r["notarizations"] and r["status"] not in ("never", "stale", "unreachable")
    )

    return {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "operators": len(results),
            "total_notarizations": total_notarizations,
            "confirmed": confirmed,
            "coverage_percent": round(100 * active_this_week / max(len(results), 1)),
        },
        "operators": results,
    }


async def main():
    print("Collecting OTS status from operators...")
    status = await collect_all()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(status, f, indent=2)

    s = status["summary"]
    print(
        f"Done: {s['operators']} operators, "
        f"{s['total_notarizations']} notarizations, "
        f"{s['confirmed']} confirmed, "
        f"{s['coverage_percent']}% coverage"
    )


if __name__ == "__main__":
    asyncio.run(main())
