"""Deterministically decide whether a claude-code-action result is a funding outage.

Two shapes count as an outage (issue #181):

1. **Hard reject before inference** — ``is_error`` + ``num_turns <= 1`` +
   ``total_cost_usd == 0``. A capped/disabled key rejected on turn 1 with no bill.
2. **Mid-run 402** — ``api_error_status == 402`` (int or str), regardless of turns
   or spend. OpenRouter reserves ``max_tokens`` up front; a nearly-dry account
   serves cheap early turns and refuses the first expensive one. Turns and cost
   are the wrong discriminator for that path — the 402 is the fact.

Any other failure prints "no" and is left untagged, so a real tool error is never
mislabeled as "out of money".

Usage:  python3 detect_signature.py <execution-output.json>  -> prints "yes"|"no"
Robust to the file being a JSON array of stream events, a single result object,
or newline-delimited JSON (JSONL).
"""

from __future__ import annotations

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


def _is_402(result: dict) -> bool:
    """True when the result carries an HTTP 402 payment-required status."""
    status = result.get("api_error_status")
    if status is None:
        return False
    try:
        return int(status) == 402
    except (TypeError, ValueError):
        return False


def is_outage(events: list) -> bool:
    result = next(
        (e for e in reversed(events)
         if isinstance(e, dict) and e.get("type") == "result"),
        None,
    )
    if not result:
        return False
    if result.get("is_error") is not True:
        return False

    # Arm 2 (issue #181): a 402 is the fact, regardless of turns or spend.
    if _is_402(result):
        return True

    # Arm 1: classic hard-reject before inference.
    return (
        result.get("num_turns", 99) <= 1
        and result.get("total_cost_usd", 1) in (0, 0.0)
    )


def main() -> None:
    try:
        with open(sys.argv[1], encoding="utf-8") as fh:
            raw = fh.read()
    except (OSError, IndexError):
        print("no")
        return
    print("yes" if is_outage(_events(raw)) else "no")


if __name__ == "__main__":
    main()
