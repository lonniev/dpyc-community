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
    - workflow: the 'pull_request_target' trigger (runs with base-repo secrets)

Software-Factory self-modification invariants ("don't turn yourself off") — hard violations:
    - CODEOWNERS that drops the money-gate rule '* @lonniev'
    - an agent-driven factory workflow that grants the agent self-merge / self-approval
      ('gh pr merge' or 'gh pr review' in --allowedTools, or an over-broad 'Bash(gh pr:*)')
    - such a workflow granting 'workflows: write' or branch-protection API access
    - a factory role prompt (factory/*.prompt.md) that removes its load-bearing safety
      anchors (the SECURITY / UNTRUSTED block; Porter's MANDATORY OUTCOME clause)

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

# --- workflow (GitHub Actions) hard rules -----------------------------------
# Forbidden triggers/patterns in .github/workflows/*.yml. The Software Factory bans
# pull_request_target: it runs in the base-repo context WITH secrets, so relying on an
# `if` guard to keep a fork's PR out is fragile. A blanket ban is auditable; use
# pull_request instead (fork PRs correctly receive no secrets — the load-bearing property).
WORKFLOW_FORBIDDEN = {
    "pull_request_target": (
        "Forbidden trigger 'pull_request_target' (runs with base-repo secrets). "
        "Use 'pull_request' — fork PRs then correctly receive no secrets."
    ),
}

# --- Software-Factory self-modification invariants --------------------------
# Porter (Service Desk) and Journeyman (Engineering) may evolve their OWN behavior via PR,
# but a self-edit must never remove the human leash. These deterministic tripwires fail CI
# red on any diff that would weaken it, so "don't turn yourself off" is a checked property,
# not a promise the LLM is trusted to keep. The human merge gate is the ultimate backstop
# (the agent never merges its own definition); these make the common attack fail before review.

# The catch-all owner rule that must survive in any CODEOWNERS the factory can touch.
# Branch protection's require_code_owner_reviews leans on this line to gate every path.
CODEOWNERS_MONEY_GATE = "* @lonniev"

# Verbs that must never appear in an agent's --allowedTools: they hand it the power to land
# its own PR or unlock its own gate. (The deterministic auto-merge.yml / approval-merge.yml
# legitimately merge, but they are not agent-driven — no allowedTools — so never checked here.)
ALLOWEDTOOLS_FORBIDDEN = {
    "gh pr review": "grants self-approval — approving reviews are the human's, not the agent's.",
    "Bash(gh pr:*)": "over-broad gh-pr grant (would include 'gh pr merge') — allow specific subcommands only.",
    "Bash(gh:*)": "over-broad gh grant (would include 'gh pr merge') — allow specific subcommands only.",
}
# 'gh pr merge' is handled separately: the GATED form `gh pr merge --auto` is allowed (native
# auto-merge cannot bypass branch protection — it holds on a red check and needs the owner's
# review), but `--admin` and immediate/bare merge (which DO bypass) are forbidden in an agent's
# allowedTools. Checked per comma-separated token so a broad grant beside an --auto one is caught.
def _merge_grant_violation(token: str) -> str | None:
    if "gh pr merge" not in token:
        return None
    if "--admin" in token:
        return f"'{token.strip()}' grants --admin merge — bypasses branch protection; forbidden."
    if "--auto" in token:
        return None  # gated auto-merge: cannot bypass the owner's approval or a red check
    return (
        f"'{token.strip()}' grants unqualified 'gh pr merge' (immediate merge) — only "
        "'gh pr merge --auto' (gated by branch protection) may be granted to an agent."
    )
# 'workflows: write' would let the agent rewrite the guardrail YAML itself (permissions,
# token, allowedTools) — the one permission that would make every other tripwire bypassable.
WORKFLOW_WRITE_PERM = re.compile(r"workflows:\s*write")

# The load-bearing safety anchors each factory prompt must retain. Keyed by file basename.
FACTORY_PROMPT_ANCHORS: dict[str, tuple[str, ...]] = {
    "porter.prompt.md": ("SECURITY", "UNTRUSTED", "MANDATORY OUTCOME"),
    "journeyman.prompt.md": ("SECURITY", "UNTRUSTED"),
    # PR Revision is the only human-triggered role that can write code, so it carries
    # the MANDATORY OUTCOME anchor too: a run that silently pushes nothing and says
    # nothing is indistinguishable from a run that never fired.
    "pr-revision.prompt.md": ("SECURITY", "UNTRUSTED", "MANDATORY OUTCOME"),
}


def is_prose(path: Path) -> bool:
    if path.suffix.lower() in PROSE_SUFFIXES:
        return True
    return any(hint in path.name for hint in PROSE_NAME_HINTS)


def is_workflow(path: Path) -> bool:
    p = path.as_posix()
    return (".github/workflows/" in p) and path.suffix.lower() in {".yml", ".yaml"}


def is_codeowners(path: Path) -> bool:
    return path.name == "CODEOWNERS"


def is_factory_prompt(path: Path) -> bool:
    return path.name in FACTORY_PROMPT_ANCHORS and "factory/" in path.as_posix()


def lint_workflow(text: str) -> list[str]:
    """Hard violations for a workflow YAML file. Comment lines are ignored so a note
    that merely mentions a forbidden token doesn't trip the rule.

    The self-modification tripwires apply ONLY to agent-driven factory workflows (those
    that run claude-code-action / declare --allowedTools): a workflow with no agent cannot
    be a self-off vector, and the deterministic auto-merge.yml must stay free to merge."""
    hard: list[str] = []
    agent_driven = ("claude-code-action" in text) or ("allowedTools" in text)
    for i, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("#"):
            continue
        for token, advice in WORKFLOW_FORBIDDEN.items():
            if token in line:
                hard.append(f"L{i}: {advice}")
        if not agent_driven:
            continue
        if "allowedTools" in line:
            for verb, advice in ALLOWEDTOOLS_FORBIDDEN.items():
                if verb in line:
                    hard.append(f"L{i}: '{verb}' in --allowedTools — {advice}")
            # 'gh pr merge' per-token: allow --auto, forbid --admin / bare immediate merge.
            for token in re.split(r'[,"]', line):
                merge_violation = _merge_grant_violation(token)
                if merge_violation:
                    hard.append(f"L{i}: {merge_violation}")
        if WORKFLOW_WRITE_PERM.search(line):
            hard.append(
                f"L{i}: 'workflows: write' would let the factory agent rewrite its own "
                "guardrail YAML — forbidden."
            )
        if "/protection" in line:
            hard.append(
                f"L{i}: touches branch-protection ('/protection') — gate config is human-only, "
                "never granted to the factory agent."
            )
    return hard


def lint_codeowners(text: str) -> list[str]:
    """The money-gate catch-all owner rule must remain. Any non-comment rule line whose
    first token is '*' and which names @lonniev satisfies it (extra owners are fine)."""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if parts and parts[0] == "*" and "@lonniev" in parts[1:]:
            return []
    return [
        (
            f"CODEOWNERS is missing the money-gate rule '{CODEOWNERS_MONEY_GATE}'. Every path "
            "must require @lonniev review — the factory may not remove its own human merge gate."
        )
    ]


# The commit-phase gate must run the same check the deploy performs. Horizon builds by
# running `fastmcp inspect <entrypoint>`, which IMPORTS the module — so anything registered
# at module scope is exercised there and nowhere else unless CI does it too.
#
# optionality-mcp went four days and eighteen commits without deploying because
# tollbooth-dpyc 0.82.0 deleted `register_job_spec`, which `server.py` still called at import
# time. Every build failed; the service kept serving the last image that had built. CI was
# green throughout, because no test imported the entrypoint — the suite could not fail for
# the reason production was broken. Fifteen "fix the deploy" PRs merged green against a
# module that could not be loaded.
#
# `ci.yml` may legitimately differ between repos (extra frontend/worker/Rust jobs, a wider
# python matrix), so this is not enforced by copying a file. The STEP is the invariant, and
# this is its canonical text:
CI_ENTRYPOINT_STEP = """      - name: Entrypoint inspects (the check Horizon performs at build time)
        run: |
          [ -f fastmcp.json ] || { echo "no fastmcp.json — not a FastMCP deployment; skipping"; exit 0; }
          ENTRY=$(python -c "import json;print(json.load(open('fastmcp.json'))['server'])")
          case "$ENTRY" in *:*) TARGET="$ENTRY";; *) TARGET="$ENTRY:mcp";; esac
          echo "inspecting $TARGET"
          # Repos install either with pip (CLI on PATH) or with uv (CLI inside the
          # project venv). Invoke it the way this repo resolves its own deps.
          if [ -f uv.lock ] && command -v uv >/dev/null 2>&1; then
            uv run fastmcp inspect -f fastmcp -o /tmp/server-info.json "$TARGET"
          else
            fastmcp inspect -f fastmcp -o /tmp/server-info.json "$TARGET"
          fi
"""

# Matched loosely so reformatting, renaming the step, or changing the output path does not
# trip the rule — only actually dropping the check does.
CI_ENTRYPOINT_MARKER = "fastmcp inspect"


def lint_ci_workflow(text: str) -> list[str]:
    """A Python CI workflow must inspect the deploy entrypoint, not only run tests.

    Scoped by BEHAVIOUR, not filename: any workflow that runs pytest is a commit-phase
    gate and owes the same guarantee. Keying on ``ci.yml`` was the first shape of this
    rule and it had a hole — the three Authorities call their workflow ``test.yml``, so
    they escaped the invariant entirely while appearing to be covered. A guard whose
    scope depends on a filename silently exempts whoever renamed the file.

    The step self-skips where there is no ``fastmcp.json``, so the rule needs no per-repo
    exception — a repo that is not a FastMCP deployment still carries it at no cost.
    """
    # An agent-driven workflow is not a gate — it mentions pytest because its PROMPT
    # tells the Journeyman to run tests. Linting those demanded a deploy-inspect step
    # inside engineering.yml, which would be nonsense.
    if ("claude-code-action" in text) or ("allowedTools" in text):
        return []
    # Must actually RUN pytest, not merely name it.
    if not any(
        "pytest" in line and ("run:" in line or line.lstrip().startswith("-"))
        for line in text.splitlines()
    ):
        return []
    if CI_ENTRYPOINT_MARKER in text:
        return []
    return [
        (
            "this workflow runs pytest but never inspects the deploy entrypoint. A suite "
            "that does not import the entrypoint cannot fail for the reason a build fails "
            "— this is the optionality-mcp outage (four days stale, CI green throughout). "
            "Add:\n" + CI_ENTRYPOINT_STEP
        )
    ]


def lint_factory_prompt(name: str, text: str) -> list[str]:
    """A factory role prompt must retain its load-bearing safety anchors. Removing the
    SECURITY/UNTRUSTED framing or (for Porter) the MANDATORY OUTCOME clause via a
    self-edit is exactly the 'turn yourself off' move this gate forbids."""
    hard: list[str] = []
    for anchor in FACTORY_PROMPT_ANCHORS.get(name, ()):
        if anchor not in text:
            hard.append(
                f"factory prompt '{name}' no longer contains its required safety anchor "
                f"'{anchor}' — a self-edit may not remove it."
            )
    return hard


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
        if not path.exists():
            continue
        factory_prompt = is_factory_prompt(path)
        codeowners = is_codeowners(path)
        workflow = is_workflow(path)
        # Factory prompts are operational instructions, not brand prose — lint them for
        # safety anchors only, never for ™ / brand wording (which would be noise).
        prose = is_prose(path) and not factory_prompt
        if not (prose or workflow or codeowners or factory_prompt):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"doctrine_lint: cannot read {path}: {exc}", file=sys.stderr)
            continue
        hard: list[str] = []
        if prose:
            phard, warn = lint_text(text)
            hard += phard
            for w in warn:
                print(f"::warning file={path}::doctrine: {w}")
        if workflow:
            hard += lint_workflow(text)
            # Any workflow that runs pytest is the commit-phase gate, whatever it is
            # called — `ci.yml` here, `test.yml` on the Authorities.
            hard += lint_ci_workflow(text)
        if codeowners:
            hard += lint_codeowners(text)
        if factory_prompt:
            hard += lint_factory_prompt(path.name, text)
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
