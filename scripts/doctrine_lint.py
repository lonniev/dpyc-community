#!/usr/bin/env python3
"""DPYC doctrine linter — a deterministic grep, not an agent.

Catches wording/brand violations that are cheap and unambiguous, so the QA agent is
reserved for semantic review. Scans PROSE/DOC files only (Markdown + a few UI-copy
globs); it deliberately never inspects Python identifiers, so a legitimate ``user``
variable in code is never flagged.

Usage:
    doctrine_lint.py FILE [FILE ...]      # lint the given files (non-prose files skipped)

Exit status:
    0  no hard violations (warnings may still be printed)
    1  one or more hard violations

Hard violations (fail CI):
    - the literal "FastMCP Cloud"   (the correct name for the managed platform is Horizon)
    - the literal "Honor Chain"     (retired term; use "Social Contract" / "Certification Chain")
    - the ® symbol applied to a DPYC mark (these are common-law ™ marks, never ®)

Warnings (never fail CI):
    - first mention of a DPYC mark that is missing the ™ symbol
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Only these files are considered prose/doc/UI-copy and get scanned.
PROSE_SUFFIXES = {".md", ".mdx", ".markdown", ".txt", ".rst"}
# UI copy sometimes lives in these; extend per repo as needed.
PROSE_NAME_HINTS = ("README", "CHANGELOG", "GETTING-STARTED")

MARKS = ("Don't Pester Your Customer", "Tollbooth DPYC", "DPYC")

# --- hard rules -------------------------------------------------------------
FORBIDDEN_LITERALS = {
    "FastMCP Cloud": 'Use "Horizon" — the managed platform is never called "FastMCP Cloud".',
    "Honor Chain": 'Retired term. Use "Social Contract" and/or "Certification Chain".',
}
# ® applied to any mark, e.g. "DPYC®" or "Tollbooth DPYC ®"
REGISTERED_ON_MARK = re.compile(
    r"(?:Don't Pester Your Customer|Tollbooth DPYC|DPYC)\s*®"
)


def is_prose(path: Path) -> bool:
    if path.suffix.lower() in PROSE_SUFFIXES:
        return True
    return any(hint in path.name for hint in PROSE_NAME_HINTS)


def lint_text(text: str) -> tuple[list[str], list[str]]:
    """Return (hard_violations, warnings) as human-readable strings with line numbers."""
    hard: list[str] = []
    warn: list[str] = []
    lines = text.splitlines()

    for i, line in enumerate(lines, start=1):
        for literal, advice in FORBIDDEN_LITERALS.items():
            if literal in line:
                hard.append(f"L{i}: forbidden phrase '{literal}'. {advice}")
        if REGISTERED_ON_MARK.search(line):
            hard.append(
                f"L{i}: ® applied to a DPYC mark — these are common-law ™ marks, use ™ not ®."
            )

    # Warn once per mark if its first mention lacks ™ (and isn't a longer mark's substring).
    for mark in MARKS:
        m = re.search(re.escape(mark) + r"(.?)", text)
        if not m:
            continue
        trailing = m.group(1)
        # DPYC as a bare prefix (DPYC-community, dpyc-oracle) is not a mark use; skip those.
        if mark == "DPYC" and trailing in {"-", "_", "/"}:
            continue
        if trailing not in {"™", "®"}:
            warn.append(f"first mention of '{mark}' is missing ™.")

    return hard, warn


def main(argv: list[str]) -> int:
    files = [Path(a) for a in argv]
    if not files:
        print("doctrine_lint: no files given (nothing to lint).")
        return 0

    total_hard = 0
    for path in files:
        if not path.exists() or not is_prose(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"doctrine_lint: cannot read {path}: {exc}", file=sys.stderr)
            continue
        hard, warn = lint_text(text)
        for w in warn:
            print(f"::warning file={path}::doctrine: {w}")
        for h in hard:
            print(f"::error file={path}::doctrine: {h}")
        total_hard += len(hard)

    if total_hard:
        print(f"\ndoctrine_lint: {total_hard} hard violation(s). Failing.")
        return 1
    print("doctrine_lint: clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
