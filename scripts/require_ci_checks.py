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

# Canonical required contexts per repo (post-normalization). Python consumers all post the single
# canonical context `test (3.12)`; the SDK keeps its 3.12+3.13 matrix; Wasm/Swift/docs/site repos
# each keep their one natural gate. Keep this list in lockstep with the fleet's ci.yml conventions.
CONTEXTS: dict[str, list[str]] = {
    # Shared SDK — must work on both runtimes.
    "tollbooth-dpyc": ["test (3.12)", "test (3.13)"],
    # Python operators / authorities / utilities — canonical single context.
    "tollbooth-sample": ["test (3.12)"],
    "schwab-mcp": ["test (3.12)"],
    "excalibur-mcp": ["test (3.12)"],
    "cypher-mcp": ["test (3.12)"],
    "optionality-mcp": ["test (3.12)"],
    "taxsort-mcp": ["test (3.12)"],
    "thebrain-mcp": ["test (3.12)"],
    "dpyc-oracle": ["test (3.12)"],
    "tollbooth-oauth2-collector": ["test (3.12)"],
    "tollbooth-shortlinks": ["test (3.12)"],
    "tollbooth-authority": ["test (3.12)"],
    "tollbooth-authority-newengland": ["test (3.12)"],
    "tollbooth-authority-northamerica": ["test (3.12)"],
    "dpyc-community": ["test (3.12)"],
    # Wasm/Spin — genuinely multi-component; require all intentional always-run jobs.
    "tollbooth-wasmcp": ["Python adapter", "Rust crypto component", "Bridge Worker", "Secret scan"],
    "tollbooth-fermyon": ["Python operator", "Secret scan"],
    # Swift / static site — each repo's one natural build gate.
    # tollbooth-pricing-studio needs a PR-triggered `build` (its testflight build is push-only);
    # added separately before this is pinned.
    "tollbooth-pricing-studio": ["build"],
    "tollbooth-dpyc-site": ["Cloudflare Pages"],
    # Excluded on purpose: network-states-of-the-internet (a fork, not ours — cannot gate);
    # pricing-studio (local-only, no GitHub remote).
}


def gh_json(path: str) -> tuple[int, dict | list | None]:
    """GET a gh api path; return (status, parsed json or None). status 0 == success."""
    proc = subprocess.run(
        ["gh", "api", path], capture_output=True, text=True
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


def observed_contexts(repo: str) -> set[str]:
    """Check-run names that have actually posted on the default branch."""
    _, data = gh_json(f"repos/{OWNER}/{repo}/commits/{BRANCH}/check-runs")
    if not isinstance(data, dict):
        return set()
    return {run.get("name", "") for run in data.get("check_runs", [])}


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

    rpr = prot.get("required_pull_request_reviews")
    if rpr is None:
        payload["required_pull_request_reviews"] = None
    else:
        payload["required_pull_request_reviews"] = {
            "dismiss_stale_reviews": rpr.get("dismiss_stale_reviews", False),
            "require_code_owner_reviews": rpr.get("require_code_owner_reviews", False),
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
            seen = observed_contexts(repo)
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
            seen_now = observed_contexts(repo)
            phantom = [c for c in have if c not in seen_now]
            if phantom:
                status_note += f"  ⛔ REQUIRED BUT NOT POSTING (hang risk): {phantom}"

        if sorted(have) == sorted(pinnable) and prot is not None:
            print(f"{repo}: already required {have} — no change{status_note}")
            continue

        arrow = f"{have or '∅'} -> {pinnable}"
        create = "  [CREATE protection]" if prot is None else ""
        print(f"{repo}: {arrow}{create}{status_note}")

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
