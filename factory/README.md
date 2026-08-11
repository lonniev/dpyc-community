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

### Opening a PR you did not author

One piece serves work done *outside* a runner. GitHub refuses to let an account approve a
PR it authored, so a change made at the keyboard and pushed with the owner's credentials
**cannot pass the code-owner gate** — it can only be forced past it with
`gh pr merge --admin`, which bypasses G3 rather than satisfying it.

`open-pr-as-app.yml` lends the crew's identity to that work. Three steps, in order:

1. **Push the branch yourself**, with your own credentials. Nothing here pushes code for
   you, deliberately — that is what keeps the token narrow.
2. **Open the PR as the App**, from any machine, with nothing to configure:
   ```
   gh workflow run "Open a PR as the factory App" --repo lonniev/dpyc-community \
     -f repo=<target-repo> -f head=<branch> -f title="…" -f body="…"
   ```
   The private key never leaves the runner. It is already a repo secret, and secrets are
   write-only — which is exactly why the work goes to the secret instead of copying a
   `.pem` onto a laptop.
3. **Push one more commit to wake CI.** GitHub suppresses workflow dispatch for events
   raised by an App token, so a PR opened this way starts with **no checks at all**. One
   commit from a human credential triggers them. Skip this and you have a PR that is
   approvable but unverified — strictly worse than the `--admin` merge it replaced. This
   is the step people miss; the workflow comments on the PR to say so.

The token can only turn an existing branch into a PR: `pull-requests: write` plus
`contents: read`, so no pushing and no merging. And **the body must name whoever actually
wrote the change** — the workflow rejects one that does not. A PR wearing the App's name
reads as "the factory did this", and the same principle that makes cypher-mcp hard-code
`llm-inferred-unverified` as a Cypher literal applies to a convenience: it may not claim
authority it does not have.

Filing an **issue** needs none of this — any harness holding a Scout credential can call
the SDK's `report_issue` and the Porter takes it from there.

### Bringing a new repo into all of this

The pieces above only reach a repo that carries the thin callers, the five secrets, a
CODEOWNERS, and branch protection. Wiring those up is its own procedure, and it is
deliberately separate from building an operator: `bootstrap-dpyc-operator` (shipped in
`tollbooth-sample`) serves anyone who wants to run a DPYC service, while adoption binds a
repo to *this* account — `@lonniev` as code owner, this App's key, the Porter and Journeyman
nsecs, `io.github.lonniev/*` in the registry.

See `skills/adopt-dpyc-operator/`. A repo can be a working operator and not be adopted;
roastify-mcp was exactly that for a day — live, credentialled, serving real data, and merging
its own commits to `main` with nothing watching.

Three more pieces run without an LLM (issue #181):

- `factory/actions/credit-preflight` reads the OpenRouter **balance** before every
  agentic model call, writes remaining credit into `$GITHUB_STEP_SUMMARY`, and —
  when overdrawn — tags `awaiting-funds` and skips the model green (no partial work,
  no stranded graph claim). The operator dial is the repo variable `CREDIT_FLOOR`
  (default 0 = only overdrawn is broke).
- `factory/actions/funding-sentinel` is the post-run backstop: it tags an item
  `awaiting-funds` on a hard reject *or* a mid-run HTTP 402 (`api_error_status == 402`,
  regardless of turns/spend).
- `factory-credit-canary.yml` reads the same balance on a 30-minute tick, alarms on
  broke **or** below-floor (forecast, not just corpse), and replays deferred work when
  remaining is healthy again.

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

## Symbol names in the graph

Every graph write that names code — `anchor_symbol`, `index_symbol`,
`bind_capability_to_symbol`, `bind_rationale_to_symbol`, `guard_invariant_symbol` — resolves
it through the same line: `MERGE (sym:Symbol {fqn: $symbol_fqn})`. Two consequences set the
convention, and both fail **silently**:

- **`fqn` is the only identity.** `index_symbol` takes a `repo_name`, but spends it on an
  `IN_SERVICE` relationship, which can only accumulate — it cannot disambiguate. Two repos
  indexing `server.main` produce *one* node wearing two services. A fleet of operators
  scaffolded from one template is exactly the population where that happens.
- **Every write MERGEs; none MATCHes.** There is no such thing as a rejected `fqn`. A typo,
  or a second convention from a second author, mints a fresh node and links to it happily.

So the name is:

```
<repo>:<the string a developer of that language would write to import it>
```

Split on the **first** colon. The repo prefix is mandatory.

| lang | example |
|---|---|
| python | `tollbooth-dpyc:tollbooth.runtime.OperatorRuntime.debit_or_deny` |
| typescript | `excalibur-mcp:frontend/src/lib/schedulerState#deriveSchedulerState` |
| swift | `pricing-studio:PricingStudioCore.ConstraintSolver.resolve` |
| rust | `tollbooth-wasmcp:dpyc_crypto::schnorr::verify` |

It is one rule, not four: the surface differs because the languages differ. Python and Swift
have real module paths; TypeScript's module identity *is* its path, so it keeps the path
(extension dropped, `#` before the symbol).

**Never put the file path in a Python/Swift/Rust `fqn`.** `anchor_symbol` already records
`file_path` and `verified_at_sha` as properties — location is deliberately not identity.
Encode it and a file move renames the node, orphaning every `REALIZED_BY`, `GUARDS`, and
authored `why` pointing at it, with no error. Also excluded: signatures, arity, line numbers,
`def`/`class` markers, a leading `src.`, and the file extension.

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
