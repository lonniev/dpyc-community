"""OpenRouter credit-balance helpers — DETERMINISTIC, no LLM.

Shared by the per-run credit-preflight action and the factory credit canary.
The balance endpoint is the right health check for "will the next real run
finish"; a 1-token probe only answers "can I make one cheap call right now",
which stays true through a partial drain (issue #181 / cypher-mcp#70).

Usage (CLI, for the composite action / canary shell):
  python3 check_credits.py [--floor N] [--json PATH]
    Reads OpenRouter credits JSON from PATH (default stdin / OPENROUTER_CREDITS_JSON).
    Prints: state=<healthy|low|broke|unknown> remaining=<float> total=<float> usage=<float>
    Exit 0 always (classification is in the state line; the caller decides policy).

Env:
  OPENROUTER_CREDITS_JSON  optional inline JSON body if --json is omitted and stdin is empty
  CREDIT_FLOOR             default floor when --floor is omitted (operator dial; default 0)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any


def remaining(total_credits: float, total_usage: float) -> float:
    return float(total_credits) - float(total_usage)


def is_overdrawn(total_credits: float, total_usage: float) -> bool:
    return remaining(total_credits, total_usage) <= 0.0


def below_floor(total_credits: float, total_usage: float, floor: float = 0.0) -> bool:
    return remaining(total_credits, total_usage) < float(floor)


def classify(total_credits: float, total_usage: float, floor: float = 0.0) -> str:
    """healthy | low | broke.

    broke  — remaining <= 0 (overdrawn or exactly empty)
    low    — 0 < remaining < floor (only when floor > 0)
    healthy — remaining >= floor (or > 0 when floor is 0)
    """
    left = remaining(total_credits, total_usage)
    if left <= 0.0:
        return "broke"
    if float(floor) > 0.0 and left < float(floor):
        return "low"
    return "healthy"


def parse_credits_body(body: str | dict[str, Any]) -> tuple[float, float] | None:
    """Extract (total_credits, total_usage) from an OpenRouter /api/v1/credits body.

    Expected shape: {"data":{"total_credits":70,"total_usage":60.09}}
    Returns None if the body cannot be parsed or lacks the fields.
    """
    try:
        data = json.loads(body) if isinstance(body, str) else body
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    inner = data.get("data", data)
    if not isinstance(inner, dict):
        return None
    if "total_credits" not in inner or "total_usage" not in inner:
        return None
    try:
        return float(inner["total_credits"]), float(inner["total_usage"])
    except (TypeError, ValueError):
        return None


def format_summary(total: float, usage: float, floor: float, state: str) -> str:
    left = remaining(total, usage)
    lines = [
        "## Factory LLM credits",
        "",
        "| | |",
        "|---|---|",
        f"| total_credits | {total:.4f} |",
        f"| total_usage | {usage:.4f} |",
        f"| **remaining** | **{left:.4f}** |",
        f"| floor | {floor:.4f} |",
        f"| state | `{state}` |",
        "",
    ]
    if state == "broke":
        lines.append(
            "> **Broke** — remaining ≤ 0. Agentic runs should skip the model and tag "
            "`awaiting-funds` rather than die mid-flight."
        )
    elif state == "low":
        lines.append(
            f"> **Low** — remaining is below the operator floor ({floor:.4f}). "
            "Top up before the next real run drains the account."
        )
    else:
        lines.append("Credits look sufficient for another agentic run.")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Classify OpenRouter credit balance.")
    ap.add_argument("--floor", type=float, default=None,
                    help="Operator floor; remaining below this is 'low' (default CREDIT_FLOOR or 0).")
    ap.add_argument("--json", default="",
                    help="Path to a saved /api/v1/credits response body.")
    ap.add_argument("--summary", default="",
                    help="If set, append a markdown summary to this file (GITHUB_STEP_SUMMARY).")
    args = ap.parse_args()

    floor = args.floor
    if floor is None:
        try:
            floor = float(os.environ.get("CREDIT_FLOOR", "0") or "0")
        except ValueError:
            floor = 0.0

    body = ""
    if args.json:
        try:
            with open(args.json, encoding="utf-8") as fh:
                body = fh.read()
        except OSError as e:
            print(f"state=unknown remaining= error=read_failed:{e}", file=sys.stderr)
            print("state=unknown")
            return 0
    else:
        if not sys.stdin.isatty():
            body = sys.stdin.read()
        if not body.strip():
            body = os.environ.get("OPENROUTER_CREDITS_JSON", "")

    parsed = parse_credits_body(body)
    if parsed is None:
        print("state=unknown remaining= total= usage=")
        # Still emit GITHUB_OUTPUT-friendly lines on stdout for the shell wrapper.
        return 0

    total, usage = parsed
    state = classify(total, usage, floor=floor)
    left = remaining(total, usage)
    # Machine-readable single line + key=value lines the composite action greps into $GITHUB_OUTPUT.
    print(f"state={state}")
    print(f"remaining={left}")
    print(f"total={total}")
    print(f"usage={usage}")
    print(f"floor={floor}")

    if args.summary:
        try:
            with open(args.summary, "a", encoding="utf-8") as fh:
                fh.write(format_summary(total, usage, floor, state))
        except OSError as e:
            print(f"summary_write_failed={e}", file=sys.stderr)

    # GitHub warning annotation when low or broke — surfaces in the job UI without failing.
    if state in ("low", "broke"):
        print(
            f"::warning::Factory LLM credits {state}: remaining={left:.4f} "
            f"(total={total:.4f}, usage={usage:.4f}, floor={floor:.4f})"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
