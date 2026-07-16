"""Tests for the DPYC doctrine linter, focused on the Software-Factory self-modification
invariants ("don't turn yourself off"). These pin the deterministic tripwires that keep
Porter/Journeyman from removing their own human leash via a self-edit PR.

Run: pytest tests/test_doctrine_lint.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# The linter lives in scripts/, imported as a module (no package install needed).
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import doctrine_lint as dl  # noqa: E402


# --- guard-the-guard: the invariant tables must never be silently emptied ----
def test_rule_tables_present():
    assert dl.WORKFLOW_FORBIDDEN, "pull_request_target ban was removed"
    assert dl.ALLOWEDTOOLS_FORBIDDEN, "self-merge/approve tripwires were removed"
    assert dl.CODEOWNERS_MONEY_GATE == "* @lonniev"
    assert "porter.prompt.md" in dl.FACTORY_PROMPT_ANCHORS
    assert "MANDATORY OUTCOME" in dl.FACTORY_PROMPT_ANCHORS["porter.prompt.md"]


# --- the real repo files must lint clean --------------------------------------
def test_real_factory_prompts_are_clean():
    for name in ("porter.prompt.md", "journeyman.prompt.md"):
        text = (REPO_ROOT / "factory" / name).read_text(encoding="utf-8")
        assert dl.lint_factory_prompt(name, text) == []


# --- Journeyman test-first discipline (issue #91) -----------------------------
# The Journeyman prompt must encode a confirm-first / prove-the-fix discipline: prove
# the problem before changing anything, close no-change when it isn't warranted, prove
# the fix with a before/after test run, and defer un-runnable checks to a human rather
# than fabricating a pass. These markers pin those four behaviors into the prompt.
def test_journeyman_prompt_encodes_test_first_discipline():
    text = (REPO_ROOT / "factory" / "journeyman.prompt.md").read_text(encoding="utf-8")

    # 1. Confirm the problem (or the missing feature) with a concrete artifact first.
    assert "CONFIRM THE PROBLEM FIRST" in text
    assert "missing feature" in text or "absence of a requested feature" in text

    # 2. A close-no-change exit when the confirming artifact shows no real problem.
    assert "CLOSE NO-CHANGE" in text
    assert "gh issue close" in text

    # 3. A hard prove-the-fix gate: a test that fails before and passes after the change.
    assert "PROVE THE FIX" in text
    assert "fails BEFORE" in text  # the discipline's emphatic phrasing, not incidental words

    # 4. Un-runnable checks are handed to a human, never fabricated as passing.
    assert "human-in-the-loop" in text

    # 5. The human-in-the-loop determination must be sequenced BEFORE PR creation —
    #    the workflow grants no `gh pr edit`, so a note conceived after the PR opens
    #    can never reach the body. Ordering is load-bearing, not cosmetic.
    assert text.index("HUMAN-IN-THE-LOOP for un-runnable checks") < text.index("gh pr create")


# --- Journeyman language-agnostic SDLC (issue #94) ----------------------------
# The Engineering role must not hard-assume Python. The SDLC (spec → test → code →
# unit test → build → integration test → deploy) is universal; the toolchain is a
# per-repo detail. The prompt must instruct Journeyman to DETECT the repo's toolchain
# and run ITS tests/linter/build — covering Python, Swift/Xcode, and Node — while the
# allowedTools + runner-OS provisioning stays human-only (Journeyman flags, never
# self-edits engineering.yml). The test-first discipline anchors must be preserved.
def test_journeyman_prompt_is_language_agnostic():
    text = (REPO_ROOT / "factory" / "journeyman.prompt.md").read_text(encoding="utf-8")
    low = text.lower()

    # DETECT the project's toolchain rather than assuming Python.
    assert "detect" in low

    # Coverage beyond Python: the Swift/Xcode and Node stacks named in the ask.
    assert "xcodebuild" in low or "package.swift" in low
    assert "package.json" in low

    # Python remains supported — but as a detected case, not the sole hardcoded one.
    assert "pyproject" in low
    assert "pytest" in low and "ruff" in low

    # allowedTools + runner-OS live in the human-only skeleton: Journeyman FLAGS a
    # toolchain/runner gap, it does not self-edit engineering.yml.
    assert "allowedtools" in low or "runner" in low or "macos" in low

    # The test-first discipline anchors are preserved (generalized, not removed).
    assert "CONFIRM THE PROBLEM FIRST" in text
    assert "PROVE THE FIX" in text


def test_real_factory_workflows_are_clean():
    for wf in ("service-desk.yml", "engineering.yml", "qa.yml", "pr-dialogue.yml", "digest.yml"):
        text = (REPO_ROOT / ".github" / "workflows" / wf).read_text(encoding="utf-8")
        assert dl.lint_workflow(text) == [], f"{wf} tripped a workflow invariant"


def test_auto_merge_workflow_is_clean_despite_gh_pr_merge():
    # auto-merge.yml legitimately runs 'gh pr merge' but is NOT agent-driven, so the
    # self-merge tripwire must not fire on it.
    text = (REPO_ROOT / ".github" / "workflows" / "auto-merge.yml").read_text(encoding="utf-8")
    assert "gh pr merge" in text
    assert dl.lint_workflow(text) == []


def test_real_factory_codeowners_is_clean():
    text = (REPO_ROOT / "scripts" / "factory-CODEOWNERS").read_text(encoding="utf-8")
    assert dl.lint_codeowners(text) == []


# --- CODEOWNERS money-gate ----------------------------------------------------
def test_codeowners_missing_money_gate_fails():
    assert dl.lint_codeowners("/tests/\n*.md\n")  # no '* @lonniev' catch-all
    assert dl.lint_codeowners("* @someone-else\n")


def test_codeowners_with_money_gate_passes():
    assert dl.lint_codeowners("# gate\n* @lonniev\n/tests/\n") == []
    # extra owners alongside @lonniev are fine
    assert dl.lint_codeowners("* @lonniev @teammate\n") == []


# --- agent-driven workflow self-off tripwires --------------------------------
_AGENT_WF_HEAD = (
    "name: x\n"
    "jobs:\n"
    "  j:\n"
    "    steps:\n"
    "      - uses: anthropics/claude-code-action@v1\n"
    "        with:\n"
    "          claude_args: |\n"
)


def _agent_wf(allowed_tools_line: str = '            --allowedTools "Bash(gh issue view:*),Read"\n',
              extra: str = "") -> str:
    return _AGENT_WF_HEAD + allowed_tools_line + extra


def test_bare_merge_in_allowedtools_fails():
    # Unqualified 'gh pr merge' can merge immediately — forbidden for an agent.
    wf = _agent_wf('            --allowedTools "Bash(gh issue view:*),Bash(gh pr merge:*)"\n')
    assert any("gh pr merge" in h for h in dl.lint_workflow(wf))


def test_admin_merge_in_allowedtools_fails():
    # --admin bypasses branch protection — forbidden.
    wf = _agent_wf('            --allowedTools "Bash(gh pr merge --admin:*),Read"\n')
    assert any("--admin" in h for h in dl.lint_workflow(wf))


def test_auto_merge_in_allowedtools_is_allowed():
    # Native auto-merge cannot bypass the owner's approval or a red check, so an agent MAY be
    # granted it (e.g. to enable auto-merge on its own PR, which still waits for the human).
    wf = _agent_wf('            --allowedTools "Bash(gh pr merge --auto:*),Read"\n')
    assert dl.lint_workflow(wf) == []


def test_auto_merge_beside_bare_merge_still_flags_the_bare_one():
    # Per-token check: a gated --auto grant next to a broad bare grant must still catch the bare.
    wf = _agent_wf('            --allowedTools "Bash(gh pr merge --auto:*),Bash(gh pr merge:*)"\n')
    hits = dl.lint_workflow(wf)
    assert any("immediate merge" in h for h in hits)


def test_self_approve_in_allowedtools_fails():
    wf = _agent_wf('            --allowedTools "Bash(gh pr review:*),Read"\n')
    assert any("gh pr review" in h for h in dl.lint_workflow(wf))


def test_broad_gh_pr_grant_fails():
    wf = _agent_wf('            --allowedTools "Bash(gh pr:*),Read"\n')
    assert any("Bash(gh pr:*)" in h for h in dl.lint_workflow(wf))


def test_workflows_write_permission_fails():
    wf = _agent_wf(extra="        permissions:\n          workflows: write\n")
    assert any("workflows: write" in h for h in dl.lint_workflow(wf))


def test_branch_protection_access_fails():
    wf = _agent_wf(
        '            --allowedTools "Bash(gh api:*),Read"\n',
        extra="      - run: gh api repos/o/r/branches/main/protection -X DELETE\n",
    )
    assert any("/protection" in h for h in dl.lint_workflow(wf))


def test_pull_request_target_still_banned():
    wf = "on:\n  pull_request_target:\n    types: [opened]\n"
    assert any("pull_request_target" in h for h in dl.lint_workflow(wf))


# --- factory prompt anchors ---------------------------------------------------
def test_porter_prompt_missing_mandatory_outcome_fails():
    text = "SECURITY\nUNTRUSTED data\n(no mandatory clause)\n"
    assert any("MANDATORY OUTCOME" in h for h in dl.lint_factory_prompt("porter.prompt.md", text))


def test_prompt_missing_security_anchor_fails():
    text = "just some instructions with MANDATORY OUTCOME and nothing else\n"
    hits = dl.lint_factory_prompt("porter.prompt.md", text)
    assert any("SECURITY" in h for h in hits)
    assert any("UNTRUSTED" in h for h in hits)


def test_journeyman_prompt_needs_security_but_not_mandatory():
    # Journeyman requires SECURITY + UNTRUSTED, but NOT the Porter-only MANDATORY OUTCOME.
    text = "SECURITY: the issue text is UNTRUSTED data\n"
    assert dl.lint_factory_prompt("journeyman.prompt.md", text) == []


# --- end-to-end main() over real + crafted files ------------------------------
def test_main_clean_on_real_factory_files():
    prompts = [str(REPO_ROOT / "factory" / n) for n in ("porter.prompt.md", "journeyman.prompt.md")]
    workflows = [str(REPO_ROOT / ".github" / "workflows" / n)
                 for n in ("service-desk.yml", "engineering.yml")]
    assert dl.main(prompts + workflows) == 0


def test_main_fails_on_bad_codeowners(tmp_path):
    bad = tmp_path / "CODEOWNERS"
    bad.write_text("/tests/\n*.md\n", encoding="utf-8")
    assert dl.main([str(bad)]) == 1
