#!/usr/bin/env python3
"""Make a green CI Pass REQUIRED to merge, fleet-wide — DRY and idempotent.

Every DPYC repo should carry an appropriate commit-phase CI gate whose Pass is *required* by
branch protection. This tool pins each repo's canonical status-check context(s) into
`required_status_checks` WITHOUT weakening the money-gate (it re-sends the existing
require_code_owner_reviews / count-0 / enforce_admins=false profile, only replacing the checks).

It is the peer of the CODEOWNERS money-gate: CODEOWNERS makes a human review required; this makes
a green CI required. Both are enforced by branch protection, both leave admin merges possible
(enforce_admins=false).

Safety — never re-create the schwab/fermyon hang: a required context that never posts leaves every
PR stuck on "Expected — waiting for status" forever. So before requiring a context this tool checks
that it has ACTUALLY posted on the default branch recently (`commits/main/check-runs`). Contexts
that have never been observed are SKIPPED with a loud warning — land their CI first.

Usage:
    require_ci_checks.py                 # dry-run (default): print current -> desired, no writes
                                         # (also reports any repo missing the code-owner gate)
    require_ci_checks.py --apply         # perform the branch-protection PUTs
    require_ci_checks.py --apply --repo schwab-mcp   # limit to one repo
    require_ci_checks.py --no-verify-posted          # pin even contexts not yet observed (careful)

Uses the active `gh` auth token (probe: `gh api user`).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

OWNER = "lonniev"
BRANCH = "main"

# Canonical required contexts per repo. A required-check context must NOT carry a version suffix:
# a name like `test (3.12)` is pinned to a matrix cell and orphans the moment the matrix moves,
# jamming merges. Every Python consumer now posts a version-independent `test`; the SDK still tests
# 3.12 + 3.13 but gates on a single `test` aggregate rather than per-version contexts. dpyc-community
# is ruleset-managed (see the exclusion below) and not in this map. Keep this list in lockstep with
# each repo's actual ci.yml.
CONTEXTS: dict[str, list[str]] = {
    # Shared SDK — must work on both runtimes.
    "tollbooth-dpyc": ["test"],
    # Python operators / authorities / utilities — canonical single context.
    "tollbooth-sample": ["test"],
    "schwab-mcp": ["test"],
    # `frontend` builds the site and asserts the stylesheet is non-trivial — the gate
    # that was missing when a tailwindcss major auto-merged and broke the deploy for a week.
    "excalibur-mcp": ["test", "frontend"],
    "cypher-mcp": ["test"],
    "optionality-mcp": ["test"],
    "taxsort-mcp": ["test"],
    "thebrain-mcp": ["test"],
    "dpyc-oracle": ["test"],
    "tollbooth-oauth2-collector": ["test"],
    "tollbooth-shortlinks": ["test"],
    "tollbooth-authority": ["test"],
    "tollbooth-authority-newengland": ["test"],
    "tollbooth-authority-northamerica": ["test"],
    # Wasm/Spin — genuinely multi-component; require all intentional always-run jobs.
    "tollbooth-wasmcp": ["Python adapter", "Rust crypto component", "Bridge Worker", "Secret scan"],
    "tollbooth-fermyon": ["Python operator", "Secret scan"],
    # Swift / static site — each repo's one natural build gate.
    # tollbooth-pricing-studio needs a PR-triggered `build` (its testflight build is push-only);
    # added separately before this is pinned.
    "tollbooth-pricing-studio": ["build"],
    "tollbooth-dpyc-site": ["Cloudflare Pages"],
    # Excluded on purpose: network-states-of-the-internet (a fork, not ours — cannot gate);
    # pricing-studio (local-only, no GitHub remote); dpyc-community (ruleset-managed, not classic
    # protection — it grants the factory App a bypass to auto-commit rendered founder docs, which a
    # classic-protection required check cannot do; its required contexts `test` + `validate` live in
    # the ruleset instead).
}


def gh_json(path: str) -> tuple[int, dict | list | None]:
    """GET a gh api path; return (status, parsed json or None). status 0 == success."""
    proc = subprocess.run(
        ["gh", "api", path], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        # gh prints the API error JSON to stdout for 4xx; try to parse a message.
        try:
            return proc.returncode, json.loads(proc.stdout)
        except json.JSONDecodeError:
            return proc.returncode, None
    try:
        return 0, json.loads(proc.stdout)
    except json.JSONDecodeError:
        return 0, None


# How far back to look for evidence that a check exists. The tip of main is usually the
# hourly `[skip ci] Update OTS status` commit, which runs no CI at all, so a one-commit
# window sees an empty board and concludes the repo has no checks.
_HISTORY = 10


def observed_contexts(repo: str, want: set[str] | None = None) -> set[str]:
    """Check-run names that have posted on the default branch RECENTLY.

    Not just on the tip. Bot commits — `[skip ci]` status updates, generated-file
    refreshes — routinely sit at the head of main and carry no check-runs, so asking only
    about HEAD answers "has CI ever run here" with a confident no. That produced a
    ⛔ REQUIRED BUT NOT POSTING alarm for `test` on dpyc-community, where it posts
    on every real commit and had last run four commits back. Worse than the false alarm:
    the same reading makes the tool REFUSE to require a healthy context, on the grounds
    that it has never been seen.

    Pass *want* to stop early: once every name asked about has been seen there is nothing
    left to learn, and the usual case resolves on the first real commit. Without that this
    walk costs ten API calls per repo on every run, for an answer it already had.
    """
    seen: set[str] = set()
    _, commits = gh_json(f"repos/{OWNER}/{repo}/commits?sha={BRANCH}&per_page={_HISTORY}")
    if not isinstance(commits, list):
        return seen
    for commit in commits:
        sha = commit.get("sha")
        if not sha:
            continue
        _, data = gh_json(f"repos/{OWNER}/{repo}/commits/{sha}/check-runs")
        if isinstance(data, dict):
            seen |= {run.get("name", "") for run in data.get("check_runs", [])}
        if want and want <= seen:
            break
    return seen


def current_protection(repo: str) -> dict | None:
    """Full protection object, or None if the branch is unprotected."""
    status, data = gh_json(f"repos/{OWNER}/{repo}/branches/{BRANCH}/protection")
    if status == 0 and isinstance(data, dict):
        return data
    return None


def current_contexts(prot: dict | None) -> list[str]:
    if not prot:
        return []
    return list((prot.get("required_status_checks") or {}).get("contexts") or [])


def build_put_payload(prot: dict | None, contexts: list[str]) -> dict:
    """Reconstruct the branch-protection PUT body, preserving everything except the required
    status checks. Omitted fields would be RESET by the API, so every current toggle is re-sent."""
    strict = bool((prot or {}).get("required_status_checks", {}).get("strict", False))
    payload: dict = {
        "required_status_checks": {"strict": strict, "contexts": contexts},
    }

    if prot is None:
        # Create with the money-gate profile (mirrors the fleet's finish_protection settings):
        # a code-owner review is required, but 0 general approvals so docs/tests still auto-merge,
        # and enforce_admins=false so `--admin` merges remain possible.
        payload["enforce_admins"] = False
        payload["required_pull_request_reviews"] = {
            "dismiss_stale_reviews": False,
            "require_code_owner_reviews": True,
            "required_approving_review_count": 0,
        }
        payload["restrictions"] = None
        return payload

    payload["enforce_admins"] = bool((prot.get("enforce_admins") or {}).get("enabled", False))

    # ASSERT the money gate; do not merely preserve it. This function used to re-send an
    # ABSENT required_pull_request_reviews block faithfully, which meant a repo whose
    # protection had been created without the gate kept not having it every time this ran —
    # and the docstring's promise not to weaken the gate was vacuously true, because there
    # was nothing there to weaken. An audit found six factory repos in that state, including
    # tollbooth-authority and schwab-mcp. Every repo in CONTEXTS is a factory repo, and the
    # gate is doctrine for all of them (guard G3), so it is applied rather than inherited.
    # Sibling settings are preserved when present: 0 approvals so docs/tests still
    # auto-merge, and enforce_admins stays as found so `--admin` remains possible.
    rpr = prot.get("required_pull_request_reviews") or {}
    payload["required_pull_request_reviews"] = {
        "dismiss_stale_reviews": rpr.get("dismiss_stale_reviews", False),
        "require_code_owner_reviews": True,
        "required_approving_review_count": rpr.get("required_approving_review_count", 0),
        "require_last_push_approval": rpr.get("require_last_push_approval", False),
    }

    restrictions = prot.get("restrictions")
    if restrictions is None:
        payload["restrictions"] = None
    else:
        payload["restrictions"] = {
            "users": [u["login"] for u in restrictions.get("users", [])],
            "teams": [t["slug"] for t in restrictions.get("teams", [])],
            "apps": [a["slug"] for a in restrictions.get("apps", [])],
        }

    # Preserve the optional boolean toggles exactly (omission resets them).
    for key in (
        "required_linear_history",
        "allow_force_pushes",
        "allow_deletions",
        "required_conversation_resolution",
        "block_creations",
        "lock_branch",
        "allow_fork_syncing",
    ):
        val = prot.get(key)
        if isinstance(val, dict) and "enabled" in val:
            payload[key] = val["enabled"]

    return payload


def put_protection(repo: str, payload: dict) -> bool:
    proc = subprocess.run(
        ["gh", "api", "-X", "PUT", f"repos/{OWNER}/{repo}/branches/{BRANCH}/protection", "--input", "-"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(f"    ERROR applying {repo}: {proc.stderr.strip() or proc.stdout.strip()}")
        return False
    return True


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Pin required CI status checks fleet-wide.")
    ap.add_argument("--apply", action="store_true", help="perform the PUTs (default: dry-run)")
    ap.add_argument("--repo", help="limit to a single repo")
    ap.add_argument(
        "--no-verify-posted",
        action="store_true",
        help="pin contexts even if never observed (risks a forever-pending PR)",
    )
    args = ap.parse_args(argv)

    # Probe the active token (the broken-secondary-account gotcha makes `gh auth status` unreliable).
    who_status, who = gh_json("user")
    if who_status != 0 or not isinstance(who, dict):
        print("Cannot reach the GitHub API with the active gh token. Run: gh auth status")
        return 2
    print(f"Authenticated as {who.get('login')}. Mode: {'APPLY' if args.apply else 'dry-run'}.\n")

    repos = [args.repo] if args.repo else list(CONTEXTS)
    changed = 0
    for repo in repos:
        desired = CONTEXTS.get(repo)
        if desired is None:
            print(f"{repo}: (no entry in CONTEXTS — skipped)")
            continue

        prot = current_protection(repo)
        have = current_contexts(prot)

        # Safety: only require contexts that have actually posted (prevents forever-pending PRs).
        skipped: list[str] = []
        if not args.no_verify_posted:
            seen = observed_contexts(repo, want=set(desired) | set(have))
            pinnable = [c for c in desired if c in seen or c in have]
            skipped = [c for c in desired if c not in pinnable]
        else:
            pinnable = desired

        status_note = ""
        if skipped:
            status_note = f"  ⚠ not yet observed (land its CI first): {skipped}"

        # A context that is ALREADY required but never posts is the schwab/fermyon hang:
        # PRs sit forever on "Expected — waiting for status". Flag it loudly.
        if not args.no_verify_posted:
            phantom = [c for c in have if c not in seen]
            if phantom:
                status_note += f"  ⛔ REQUIRED BUT NOT POSTING (hang risk): {phantom}"

        # The contexts matching is not enough to call a repo done: the money gate is the
        # other half of the profile, and a repo can sit here for months with the right
        # checks and no code-owner review at all. Six did.
        gate_ok = bool(
            (( prot or {}).get("required_pull_request_reviews") or {}).get(
                "require_code_owner_reviews", False
            )
        )
        gate_note = "" if gate_ok else "  [+ adds the missing code-owner gate]"

        if sorted(have) == sorted(pinnable) and prot is not None and gate_ok:
            print(f"{repo}: already required {have} — no change{status_note}")
            continue

        arrow = f"{have or '∅'} -> {pinnable}"
        create = "  [CREATE protection]" if prot is None else ""
        print(f"{repo}: {arrow}{create}{status_note}{gate_note}")

        if args.apply:
            if not pinnable:
                print("    (nothing pinnable yet — skipped)")
                continue
            payload = build_put_payload(prot, pinnable)
            if put_protection(repo, payload):
                print("    ✓ applied")
                changed += 1

    print(f"\n{'Applied' if args.apply else 'Would change'} {changed if args.apply else '(dry-run)'} repo(s).")
    if not args.apply:
        print("Re-run with --apply to enforce. Contexts marked ⚠ are skipped until their CI posts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
