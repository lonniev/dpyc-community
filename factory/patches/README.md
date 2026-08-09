# Factory patches awaiting human apply

The factory App token deliberately lacks `workflows: write`, so agent PRs cannot
push `.github/workflows/*` even when the fix belongs there. When a fix needs a
workflow skeleton change, the agent ships:

1. The load-bearing **actions / scripts / tests** (this PR can land those).
2. A **unified diff** under this directory for a human (or a credentials path
   that holds `workflows`) to apply in a follow-up commit on the same branch or
   a sibling PR.

## issue-181-workflow-preflight.patch

Wires `factory/actions/credit-preflight` into every agentic reusable workflow
and upgrades `factory-credit-canary.yml` from a 1-token probe to an OpenRouter
balance + `CREDIT_FLOOR` check. Apply after the actions from #181 are on the
branch (or on `main`):

```bash
git apply factory/patches/issue-181-workflow-preflight.patch
# or:  patch -p1 < factory/patches/issue-181-workflow-preflight.patch
```

Touched workflows:

- `engineering.yml`, `service-desk.yml`, `qa.yml`, `pr-revision.yml`,
  `pr-dialogue.yml`, `housekeeper.yml` — preflight before the model; skip green
  when broke; sentinel only when the model actually ran.
- `factory-credit-canary.yml` — balance endpoint + floor alarm (forecast, not
  only corpse).

Operator dial after apply: set repo/org variable `CREDIT_FLOOR` (USD-equivalent
credits; default `0` = only overdrawn is broke).
