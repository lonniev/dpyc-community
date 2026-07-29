#!/usr/bin/env python3
"""State-machine completeness check over docs/model/dpyc-factory.sysml.

`sysml validate` proves the model is well-formed. It says nothing about whether the
behavior is *complete* — which is where the interesting defects live. This asks the
question a formal reading asks: for each state, which events can arrive, and does the
machine say what happens?

The naive form of that question (every state x every event) is almost all noise: most
pairs are nonsensical. What matters in a webhook-driven pipeline is the AMBIENT events —
the ones GitHub, the credit canary, or a human can deliver at any moment regardless of
what the machine currently believes. An ambient event with no transition is not a
theoretical hole; it is an event that will arrive and be silently dropped.

Its first run found six gaps. One was a real system defect (no mutual exclusion anywhere:
two Journeymen could branch the same ref); the rest were places the model had drifted from
workflows that already handled the case. Both kinds are worth catching, which is why
IGNORABLE below demands a reason string rather than a bare allow-list — an unhandled event
must be argued for, not merely tolerated.

Usage:  python3 check_states.py [--verbose]      exit 1 on any unexplained gap
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

MODEL = Path(__file__).resolve().parent / "dpyc-factory.sysml"

# Events deliverable at any time, per machine. Keep this list honest: adding an event
# here asserts "the outside world can produce this whenever it likes", which is the
# claim that makes an unhandled pair a bug.
AMBIENT: dict[str, tuple[str, ...]] = {
    "IssueLifecycle": ("ItemClosed", "CreditOutage", "IssueReopened"),
    "PullRequestLifecycle": ("PRAbandoned", "CreditOutage", "OwnerApproves", "OwnerRequestsChanges"),
    "FundingBlockLifecycle": ("CreditOutage", "ItemClosed"),
}

# (machine, state, event) -> why no transition is needed. A reason is mandatory.
IGNORABLE: dict[tuple[str, str, str], str] = {
    ("IssueLifecycle", "Opened", "ItemClosed"):
        "Not yet triaged; a close here is indistinguishable from never having been filed.",
    ("IssueLifecycle", "Opened", "CreditOutage"):
        "No agent has run yet, so there is nothing to defer.",
    ("IssueLifecycle", "Opened", "IssueReopened"): "Already open.",
    ("IssueLifecycle", "Triaging", "IssueReopened"): "Already open.",
    ("IssueLifecycle", "NeedsInfo", "IssueReopened"): "Stays open by definition.",
    ("IssueLifecycle", "ReadyForEngineering", "IssueReopened"): "Already open.",
    ("IssueLifecycle", "Working", "IssueReopened"): "Already open.",
    ("IssueLifecycle", "BlockedUpstream", "IssueReopened"): "Already open.",
    ("IssueLifecycle", "Arbitration", "IssueReopened"): "Already open.",
    ("IssueLifecycle", "PRRaised", "IssueReopened"): "Already open.",
    ("IssueLifecycle", "AwaitingFunds", "IssueReopened"): "Already open.",
    ("IssueLifecycle", "PRRaised", "ItemClosed"):
        "Closing the issue while its PR is open is the merge path arriving early; "
        "FixPropagated already lands there.",
    ("IssueLifecycle", "Rejected", "ItemClosed"): "Already closed.",
    ("IssueLifecycle", "Closed", "ItemClosed"): "Already closed.",
    ("IssueLifecycle", "Rejected", "CreditOutage"): "Closed items are not worked.",
    ("IssueLifecycle", "Closed", "CreditOutage"): "Closed items are not worked.",
    ("IssueLifecycle", "NeedsInfo", "CreditOutage"):
        "Waiting on a human, not on an agent.",
    ("IssueLifecycle", "BlockedUpstream", "CreditOutage"):
        "Waiting on another repository's pipeline, which funds itself.",
    ("IssueLifecycle", "Arbitration", "CreditOutage"): "Frozen for a human; no agent runs.",
    ("IssueLifecycle", "PRRaised", "CreditOutage"):
        "The PR carries its own funding state — see PullRequestLifecycle.",
    ("IssueLifecycle", "AwaitingFunds", "CreditOutage"): "Already deferred.",

    ("PullRequestLifecycle", "Merged", "PRAbandoned"): "Terminal; a merged PR cannot be abandoned.",
    ("PullRequestLifecycle", "Merged", "CreditOutage"): "Terminal.",
    ("PullRequestLifecycle", "Merged", "OwnerApproves"): "Terminal.",
    ("PullRequestLifecycle", "Merged", "OwnerRequestsChanges"): "Terminal.",
    ("PullRequestLifecycle", "ClosedUnmerged", "PRAbandoned"): "Already closed.",
    ("PullRequestLifecycle", "ClosedUnmerged", "CreditOutage"): "No agent runs on a closed PR.",
    ("PullRequestLifecycle", "ClosedUnmerged", "OwnerApproves"): "Nothing to land.",
    ("PullRequestLifecycle", "ClosedUnmerged", "OwnerRequestsChanges"): "Nothing to revise.",
    ("PullRequestLifecycle", "AutoMergeArmed", "PRAbandoned"):
        "Closing an armed PR disarms it in GitHub; no state of ours survives it.",
    ("PullRequestLifecycle", "AutoMergeArmed", "CreditOutage"):
        "Armed is a GitHub state; no agent is running to be cut.",
    ("PullRequestLifecycle", "AutoMergeArmed", "OwnerApproves"): "Already armed; re-approval is a no-op.",
    ("PullRequestLifecycle", "PRAwaitingFunds", "CreditOutage"): "Already deferred.",
    ("PullRequestLifecycle", "PRAwaitingFunds", "PRAbandoned"):
        "block-retire.yml owns this: it drops the label and retires the block.",
    ("PullRequestLifecycle", "PRAwaitingFunds", "OwnerApproves"):
        "Approval during an outage still arms the merge; the deferred agent is QA, not the gate.",
    ("PullRequestLifecycle", "PRAwaitingFunds", "OwnerRequestsChanges"):
        "The canary deliberately will not replay Revision; the owner re-requests on recovery.",
    ("PullRequestLifecycle", "Passed", "CreditOutage"): "QA has finished; no agent is running.",
    ("PullRequestLifecycle", "AwaitingHuman", "CreditOutage"): "Waiting on a person.",
    ("PullRequestLifecycle", "Flagged", "CreditOutage"): "QA has finished; no agent is running.",
    ("PullRequestLifecycle", "UnderReview", "CreditOutage"):
        "Reached via AwaitingQA, which carries the deferral.",
    ("PullRequestLifecycle", "AwaitingQA", "OwnerApproves"):
        "Legal, and approval-merge arms it; the review outcome is tracked from Passed/Flagged.",
    ("PullRequestLifecycle", "UnderReview", "OwnerApproves"): "As AwaitingQA.",
    ("PullRequestLifecycle", "Passed", "OwnerApproves"):
        "Already heading to AutoMergeArmed via the path gate.",
    ("PullRequestLifecycle", "Revising", "OwnerApproves"): "Approving mid-revision arms on the new head.",
    ("PullRequestLifecycle", "AwaitingQA", "OwnerRequestsChanges"): "Reaches Revising once QA reports.",
    ("PullRequestLifecycle", "UnderReview", "OwnerRequestsChanges"): "As AwaitingQA.",
    ("PullRequestLifecycle", "Passed", "OwnerRequestsChanges"): "Reaches Revising via AwaitingHuman.",
    ("PullRequestLifecycle", "Revising", "OwnerRequestsChanges"): "Already revising.",

    ("FundingBlockLifecycle", "None", "ItemClosed"): "No block exists to retire.",
    ("FundingBlockLifecycle", "Active", "CreditOutage"): "Already blocked.",
    ("FundingBlockLifecycle", "Cleared", "ItemClosed"):
        "The block was already cleared; closing leaves nothing to retire.",
    ("FundingBlockLifecycle", "Historical", "ItemClosed"): "Already retired.",
}

# States that are allowed to have no outgoing transition.
TERMINAL_OK = {("PullRequestLifecycle", "Merged"), ("PullRequestLifecycle", "ClosedUnmerged")}
# States entered from the machine's initial pseudo-state rather than a transition.
INITIAL_OK = {("IssueLifecycle", "Opened"), ("PullRequestLifecycle", "AwaitingQA"),
              ("FundingLifecycle", "Healthy"), ("FundingBlockLifecycle", "None")}


def parse(src: str) -> dict[str, tuple[list[str], list[tuple[str, str, str]]]]:
    out = {}
    for m in re.finditer(r"state def (\w+)\s*\{", src):
        name, i, depth = m.group(1), m.end(), 1
        while depth:
            if src[i] == "{":
                depth += 1
            elif src[i] == "}":
                depth -= 1
            i += 1
        body = re.sub(r"/\*.*?\*/", "", src[m.end():i], flags=re.DOTALL)
        out[name] = (
            re.findall(r"^\s*state\s+(?:\"[^\"]*\"\s+as\s+)?(\w+)", body, re.MULTILINE),
            re.findall(r"transition\s+first\s+(\w+)(?:\s+accept\s+(\w+))?\s+then\s+(\w+)\s*;", body),
        )
    return out


def main(argv: list[str]) -> int:
    verbose = "--verbose" in argv
    machines = parse(MODEL.read_text())
    problems: list[str] = []

    for name, (states, trans) in machines.items():
        handled = {(s, e) for s, e, _ in trans if e}
        sources = {s for s, _, _ in trans}
        targets = {d for _, _, d in trans}

        for ev in AMBIENT.get(name, ()):
            for st in states:
                if (st, ev) in handled or (name, st, ev) in IGNORABLE:
                    continue
                problems.append(
                    f"{name}.{st}: unhandled ambient event '{ev}' — add a transition, "
                    f"or an IGNORABLE entry saying why it cannot arrive."
                )

        for st in states:
            if st not in sources and (name, st) not in TERMINAL_OK:
                problems.append(f"{name}.{st}: no outgoing transition (unintended terminal).")
            if st not in targets and (name, st) not in INITIAL_OK:
                problems.append(f"{name}.{st}: no incoming transition (unreachable).")

        seen: dict[tuple[str, str], str] = {}
        for s, e, d in trans:
            if e and (s, e) in seen and seen[(s, e)] != d:
                problems.append(
                    f"{name}.{s}: event '{e}' goes to both {seen[(s, e)]} and {d} "
                    f"(nondeterministic)."
                )
            elif e:
                seen[(s, e)] = d

        if verbose:
            amb = len(AMBIENT.get(name, ()))
            print(f"  {name}: {len(states)} states, {len(trans)} transitions, "
                  f"{amb} ambient events, {len(handled)} handled pairs")

    if problems:
        print(f"state completeness: {len(problems)} problem(s)\n")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"state completeness: clean ({len(machines)} machines).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
