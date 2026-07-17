"""Deterministically decide whether a claude-code-action result is a funding outage.

A capped/exhausted ANTHROPIC_API_KEY makes the action fail on turn 1 with
is_error:true, num_turns<=1, total_cost_usd==0 — it reached Anthropic, was
rejected before any work, and billed nothing. That exact shape is the ONLY thing
we treat as an outage; any other failure prints "no" and is left untagged.

Usage:  python3 detect_signature.py <execution-output.json>  -> prints "yes"|"no"
Robust to the file being a JSON array of stream events, a single result object,
or newline-delimited JSON (JSONL).
"""

import json
import sys


def _events(raw: str) -> list:
    raw = raw.strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        # JSONL: one JSON object per line.
        out = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return out


def is_outage(events: list) -> bool:
    result = next(
        (e for e in reversed(events)
         if isinstance(e, dict) and e.get("type") == "result"),
        None,
    )
    if not result:
        return False
    return (
        result.get("is_error") is True
        and result.get("num_turns", 99) <= 1
        and result.get("total_cost_usd", 1) in (0, 0.0)
    )


def main() -> None:
    try:
        raw = open(sys.argv[1], encoding="utf-8").read()
    except (OSError, IndexError):
        print("no")
        return
    print("yes" if is_outage(_events(raw)) else "no")


if __name__ == "__main__":
    main()
