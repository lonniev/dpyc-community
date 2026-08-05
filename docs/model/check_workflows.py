#!/usr/bin/env python3
"""Structural check over the factory's workflow graph — the implementation of the model.

`check_states.py` asks whether the *model* is complete. This asks whether the *workflows
that implement it* will actually start. They are different failure modes: a modelled
transition that nothing implements is a gap you can read, while a workflow GitHub refuses
to parse is a gap that reads as ordinary silence.

The rule enforced here comes from a real outage. A job that calls a reusable workflow
(`uses: owner/repo/.github/workflows/x.yml@ref`) accepts ONLY the keys in ALLOWED below.
Any other key — `continue-on-error`, `runs-on`, `steps`, `env`, `timeout-minutes` — is a
parse error for the ENTIRE FILE, so nothing in it runs, including the jobs that were fine.

What makes it worth a checker rather than a code review is how it fails:

  * `conclusion: failure` with **zero jobs** — a startup failure,
  * no log to open (`gh run view --log-failed` answers "log not found"),
  * no annotation, and
  * `gh run list` prints the workflow's FILE PATH instead of its `name:`, because the
    `name:` never parsed.

On 2026-08-05 that took `deploy-verify` down across the factory. Six excalibur-mcp merges
shipped with no deploy verification before anyone looked, and six sibling operator repos
were one merge away from the same. The offending key had been added deliberately, by a fix
whose intent was correct — `continue-on-error` is simply the obvious spelling of "this must
not gate shipping", and it is the one spelling that is illegal there.

`scripts/factory-callers/` is checked too, and matters more than the local workflows: those
files are DISTRIBUTED to every operator repo, so one bad key there arms the whole fleet.

Usage:  python3 check_workflows.py [--verbose]      exit 1 on any violation
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]

# Directories whose *.yml are GitHub Actions workflows. `factory-callers` holds the thin
# callers copied out to operator repos — a violation there ships to every one of them.
WORKFLOW_DIRS = (".github/workflows", "scripts/factory-callers")

# Keys GitHub permits on a job that calls a reusable workflow. Anything else is a parse
# error for the whole file. Sourced from the Actions workflow syntax reference; keep it in
# that order so a diff against the docs is easy to read.
ALLOWED = frozenset(
    {"name", "uses", "with", "secrets", "needs", "if", "permissions", "strategy", "concurrency"},
)

# Why each commonly-attempted key is refused, so the failure message teaches instead of
# merely forbidding. A key absent from here still fails — this only enriches the report.
WHY = {
    "continue-on-error": (
        "a caller cannot make a reusable-workflow job non-fatal. Give the CALLEE an "
        "`advisory` input and put `continue-on-error` on its steps, where the key is legal"
    ),
    "steps": "the called workflow owns the steps; the caller passes `with`/`secrets` only",
    "runs-on": "the called workflow chooses its own runner",
    "env": "pass values through `with:` — a caller's env does not reach the callee",
    "timeout-minutes": "set the timeout on the callee's jobs",
    "outputs": "declare outputs in the callee's `on.workflow_call.outputs`",
    "container": "the called workflow chooses its own execution environment",
    "services": "the called workflow declares its own service containers",
    "defaults": "the called workflow sets its own defaults",
}


def violations(path: Path, verbose: bool = False) -> list[str]:
    """Every reason `path` would fail to start, as human-readable lines."""
    rel = path.relative_to(ROOT)
    try:
        doc = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        # A file that will not parse dies exactly as loudly as a bad job key: not at all.
        return [f"{rel}: does not parse as YAML — {exc}"]

    if not isinstance(doc, dict):
        return [f"{rel}: top level is {type(doc).__name__}, expected a mapping"]

    found = []
    for job_name, job in (doc.get("jobs") or {}).items():
        if not isinstance(job, dict) or "uses" not in job:
            continue
        extra = sorted(set(job) - ALLOWED)
        if not extra:
            if verbose:
                print(f"  ok   {rel}: job `{job_name}` calls {job['uses']}")
            continue
        for key in extra:
            reason = WHY.get(key, "not permitted on a reusable-workflow call")
            found.append(
                f"{rel}: job `{job_name}` sets `{key}`, which GitHub rejects — {reason}.\n"
                f"    The whole FILE fails to parse: zero jobs, no log, and the run "
                f"renders as its path rather than its name.",
            )
    return found


def main() -> int:
    verbose = "--verbose" in sys.argv
    files = sorted(
        p
        for d in WORKFLOW_DIRS
        for p in (ROOT / d).glob("*.yml")
        if (ROOT / d).is_dir()
    )
    if not files:
        print("check_workflows: found no workflow files — is the layout still right?")
        return 1

    failures = [line for f in files for line in violations(f, verbose)]
    if failures:
        print(f"check_workflows: {len(failures)} violation(s) across {len(files)} file(s)\n")
        for line in failures:
            print(f"::error::{line}")
        return 1

    print(f"check_workflows: {len(files)} workflow file(s) clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
