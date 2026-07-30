#!/usr/bin/env python3
"""Validate relays.json against its schema, plus the one business rule.

Extracted from validate-relays.yml's inline heredoc so the always-on `validate`
gate and the path-filtered relays workflow run the SAME check rather than two
copies that can drift apart.

Usage:
    python scripts/validate_relays.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    from jsonschema import Draft202012Validator

    with open(REPO_ROOT / "relays.json") as f:
        data = json.load(f)
    with open(REPO_ROOT / "schemas" / "relays.schema.json") as f:
        schema = json.load(f)

    errors = sorted(
        Draft202012Validator(schema).iter_errors(data),
        key=lambda e: list(e.path),
    )
    if errors:
        for e in errors:
            loc = "/".join(str(p) for p in e.path) or "<root>"
            print(f"  [{loc}] {e.message}")
        return 1

    # Business rule: at most one primary relay.
    primaries = [r for r in data["relays"] if r.get("primary")]
    if len(primaries) > 1:
        print(f"  At most one relay may be primary; found {len(primaries)}.")
        return 1

    print(
        f"relays.json valid — {len(data['relays'])} relay(s), "
        f"{len(primaries)} primary."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
