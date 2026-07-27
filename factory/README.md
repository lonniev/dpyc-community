# The DPYC™ Software Factory

An unattended crew of agents that triages, fixes, reviews, and lands work across the
fleet. This directory holds the crew's **behavior** (prompt files) and its one composite
action. The **skeletons** — permissions, tokens, `--allowedTools` — live in
`.github/workflows/*.yml` and are human-only: an agent may propose a prompt change by PR,
but never edits the workflow that grants it its powers.

Each repo carries only a **thin caller** (`.github/workflows/agentic-*.yml`) that
delegates to a reusable workflow here. Callers are byte-identical everywhere; language
dispatch happens inside the reusable workflow (`engineering.yml` sniffs for
`*.xcodeproj`/`Package.swift` and picks `macos-latest`), so onboarding a repo never means
customizing YAML.

## The crew

| Role | Fires on | Can write code? | Behavior lives in |
|---|---|---|---|
| **Porter** (Service Desk) | issue opened / `agent/retriage` | no — triages and labels | `porter.prompt.md` |
| **Journeyman** (Engineering) | issue labeled `agent/fix` | **yes** — branch + PR | `journeyman.prompt.md` |
| **QA** | PR opened/synchronized on `agent/fix-*` | no — labels `qa/pass` / `qa/flag` | inline in `qa.yml` |
| **PR Dialogue** | any `@journeyman` mention on a PR | no — answers on the record | inline in `pr-dialogue.yml` |
| **PR Revision** | OWNER requests changes, or `@journeyman revise` | **yes** — pushes to the PR branch | `pr-revision.prompt.md` |
| **Housekeeper** | schedule | no — tidies stale state | `housekeeper.prompt.md` |
| **Escalation** | `blocked/upstream` / `rejected/upstream` | no — routes across repos | `escalation.yml` |
| **approval-merge / auto-merge** | OWNER approval / `qa/pass` | no — deterministic, no LLM | those workflows |

Two more pieces run without an LLM: `factory/actions/funding-sentinel` tags an item
`awaiting-funds` when the shared Anthropic key is exhausted, and
`factory-credit-canary.yml` replays that deferred work when credit returns.

### Dialogue vs Revision

Both answer to `@journeyman`, and the split is deliberate:

- **A question** → Dialogue. Read-only by construction: no `Edit`/`Write` in its
  `--allowedTools`, and both its tokens are `contents: read`, so even a coerced
  `git push` fails. *Anyone* may summon it, precisely because it cannot do anything.
- **A change order** → Revision. Has `Edit`, `Write`, and `contents: write`. Because it
  cannot keep Dialogue's mitigation, it substitutes a different one: the caller requires
  `author_association == 'OWNER'`. Only the repository owner can command commits.

`agentic-pr-dialogue.yml` carries negative guards (`!contains(…, '@journeyman revise')`,
`review.state != 'changes_requested'`) so the two never fire on the same event.

## Trust model, in one paragraph

Issue text, PR comments, and reviews are **untrusted data** — every prompt says so, and
the workflows assume a prompt-injection attempt is always possible. Defense is layered:
narrow `--allowedTools` (no `curl`, `bash -c`, `eval`, `rm`; every `gh` subcommand
enumerated so a broad grant can't smuggle `gh pr merge`), least-privilege App tokens
scoped to one repo, `pull_request` never `pull_request_target` (so forks get no secrets),
CODEOWNERS as the money-path human gate, and `scripts/doctrine_lint.py` in CI to keep it
that way — it fails the build on `workflows: write`, on self-approval verbs, on
unqualified `gh pr merge`, and if a prompt loses its safety anchors.

## Adding a new role

This is the procedure the PR Revision role was built with; follow it as the worked example.

1. **Write the behavior** — `factory/<role>.prompt.md`. Placeholders are filled by
   `envsubst`'s restricted form, so only the ones you name in the workflow are substituted.
   Include a `SECURITY` / `UNTRUSTED` preamble and, for any role that must not end
   silently, a `MANDATORY OUTCOME` clause.
2. **Register its anchors** — add the prompt's basename to `FACTORY_PROMPT_ANCHORS` in
   `scripts/doctrine_lint.py`. Unregistered prompts are silently unlinted.
3. **Write the skeleton** — `.github/workflows/<role>.yml`, a `workflow_call` reusable.
   Mint the App token, render the prompt from `raw.githubusercontent.com` (this workflow's
   checkout is the *caller's* repo, not this one), keep the Linux-guarded bwrap
   `/home/.mcp.json` pre-step, and wire the funding sentinel so an outage defers instead
   of failing silently.
4. **Write the caller** — `scripts/factory-callers/agentic-<role>.yml`. This is the
   security boundary: the `if:` expression decides who may fire the role. Guard against
   the bot's own events, and gate any write-capable role on `author_association`.
5. **Teach the canary** — `factory-credit-canary.yml` replays deferred work by label. A
   new role needs a discriminator, or its stalled work gets replayed as the wrong role.
6. **Add any new label** to `scripts/apply_labels.sh`, then `scripts/apply_labels.sh <repo>`.
7. **Roll it out** — `scripts/sync-factory-callers.sh` (no args auto-discovers the fleet).
   It works in throwaway clones, opens a `factory-callers-sync` PR per repo, and is
   idempotent; `MERGE=admin` squash-merges once you trust the diff.
8. **Document it** — add a row to the crew table above.

Separately, a *fresh* peer repo also needs `scripts/apply_labels.sh`, `.github/CODEOWNERS`,
`scripts/set_pipeline_secrets.sh`, and `scripts/bootstrap-factory-secrets.sh`. Branch
protection is per-repo (its own CI check names) and is deliberately never blanket-applied.
