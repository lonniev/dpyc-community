#!/usr/bin/env python3
"""Show every open Renovate PR across the estate, and land the ones that are ready.

Written because the backlog gets cleared by hand, repeatedly, and by hand means
reading seven PRs' check state in seven browser tabs and then trusting your memory
of which were green.

── It does not invent a merge policy ────────────────────────────────────────────

`renovate-config.json` already states one, and this follows it:

    tollbooth-dpyc patch/minor   the ONE thing that self-merges, on green CI
    tollbooth-dpyc major         always manual — breaking changes
    everything else              the owner reviews; only the SDK pin bypasses
                                 the money-gate

"The owner reviews" is satisfied by a person running this and reading the report.
So it reports by default and merges nothing; `--merge` is a separate, deliberate
act. An approval on these repos is a TRIGGER rather than a verdict — code-owner
approval satisfies the last gate and the PR goes in — so nothing is ever approved
before its checks have been read.

── Why the update type is parsed from the body ──────────────────────────────────

Renovate's title does not reliably say. "update dependency foo to v3" is a major
and "update dependency foo to v3.1.2" is not, but "update frontend dependencies"
is a group that says nothing at all and may contain either. The body carries a
table of `old → new` for every package in the PR, so the majors are read from the
version numbers themselves rather than guessed from prose.

Usage:
    scripts/renovate_sweep.py                     # report on the discovered estate
    scripts/renovate_sweep.py --merge             # approve + land the ready ones
    scripts/renovate_sweep.py --merge cypher-mcp
    scripts/renovate_sweep.py --sdk-only --merge  # just the tollbooth-dpyc pins
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

OWNER = "lonniev"

#: A check that reported one of these is not a reason to hold back. SKIPPED is
#: normal — several agentic workflows skip by design on branches that are not
#: theirs. Anything else, PENDING included, means not green yet, and treating a
#: pending check as green is how a merge lands on an unfinished build.
FINE = {"SUCCESS", "SKIPPED", "NEUTRAL"}

#: `[`1.40.0` → `1.41.0`]` and `` `==0.89.1` → `==0.90.0` `` both appear.
BUMP = re.compile(r"`[^`0-9]*(\d+)\.(\d+)[^`]*`\s*(?:→|->)\s*`[^`0-9]*(\d+)\.(\d+)[^`]*`")


def gh(*args: str) -> str:
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        return ""
    return out.stdout


def estate(root: Path) -> list[str]:
    """The repos actually checked out here, so this never touches account cruft."""
    found = []
    for d in sorted(root.iterdir()):
        if not (d / ".git").is_dir():
            continue
        url = subprocess.run(
            ["git", "-C", str(d), "remote", "get-url", "origin"],
            capture_output=True, text=True,
        ).stdout
        if f"{OWNER}/" in url:
            found.append(d.name)
    return found


def crosses_a_major(body: str) -> bool:
    """Does any package in this PR change its major version?

    A 0.x line is its own case: under semver a 0.89 → 0.90 is a breaking change,
    but the preset says the SDK's minor bumps self-merge, so the literal major
    component is what is compared. Anything that moves 1.x → 2.x is held.
    """
    for a_major, _a_minor, b_major, _b_minor in BUMP.findall(body):
        if a_major != b_major:
            return True
    return False


def survey(repo: str, sdk_only: bool) -> list[dict]:
    raw = gh("pr", "list", "--repo", f"{OWNER}/{repo}", "--author", "app/renovate",
             "--state", "open", "--json",
             "number,title,body,mergeStateStatus,statusCheckRollup")
    if not raw.strip():
        return []
    out = []
    for pr in json.loads(raw):
        is_sdk = "tollbooth-dpyc" in pr["title"]
        if sdk_only and not is_sdk:
            continue

        checks = {
            (c.get("name") or c.get("context")): (c.get("conclusion") or c.get("state") or "PENDING")
            for c in (pr.get("statusCheckRollup") or [])
        }
        bad = sorted(n for n, v in checks.items() if v not in FINE)

        if crosses_a_major(pr.get("body") or ""):
            why = "major version change — manual by preset"
        elif not checks:
            why = "no checks reported at all — a PR nothing verified"
        elif bad:
            why = "not green: " + ", ".join(f"{n}={checks[n]}" for n in bad)
        elif pr["mergeStateStatus"] == "DIRTY":
            why = "conflicted — let Renovate rebase rather than fixing a lockfile by hand"
        elif pr["mergeStateStatus"] == "BEHIND":
            why = "behind base — needs an update-branch"
        else:
            why = ""

        out.append({"repo": repo, "number": pr["number"], "title": pr["title"],
                    "sdk": is_sdk, "why": why})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repos", nargs="*", help="bare repo names; default = the estate here")
    ap.add_argument("--merge", action="store_true", help="approve and land the ready ones")
    ap.add_argument("--sdk-only", action="store_true", help="only tollbooth-dpyc pins")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    args = ap.parse_args()

    repos = args.repos or estate(Path(args.root))
    rows = [r for repo in repos for r in survey(repo, args.sdk_only)]
    ready = [r for r in rows if not r["why"]]

    for r in rows:
        tag = "READY" if not r["why"] else "HOLD "
        print(f"  {r['repo']:<18} #{r['number']:<5} {tag} {r['title'][:60]}")
        if r["why"]:
            print(f"      {r['why']}")

    print(f"\n{len(rows)} open, {len(ready)} ready, {len(rows) - len(ready)} held back.")
    if not ready:
        return 0
    if not args.merge:
        print("Report only. Re-run with --merge to approve and land the ready ones.")
        return 0

    for r in ready:
        full = f"{OWNER}/{r['repo']}"
        n = str(r["number"])
        # Approve first: code-owner review is the gate these wait on, and the owner
        # can approve a Renovate PR precisely because Renovate authored it.
        gh("pr", "review", n, "--repo", full, "--approve",
           "--body", "Checks green; landing per the shared Renovate preset.")
        if gh("pr", "merge", n, "--repo", full, "--squash", "--delete-branch"):
            print(f"  merged  {full}#{n}")
        elif gh("pr", "merge", n, "--repo", full, "--squash", "--auto", "--delete-branch"):
            print(f"  queued  {full}#{n} (auto-merge)")
        else:
            print(f"  FAILED  {full}#{n} — merge refused; look at this one by hand")
    return 0


if __name__ == "__main__":
    sys.exit(main())
