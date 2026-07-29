# DPYC™ Software Factory — architecture model

A formal model of the agentic pipeline that triages, fixes, reviews and lands work across
the fleet: its crew, the common behavior every repo inherits from this repository, the
guards on who may change what, both funding rails, the tech stack, and the state machines
that govern an issue, a pull request, and an outage.

| File | What it is |
|---|---|
| [`dpyc-factory.sysml`](./dpyc-factory.sysml) | The model — SysML v2 textual notation. Twelve packages: vocabulary, items, identity, platform, intention graph, roles, distribution, behavior (state machines), guards, fleet, deployment, assurance. |
| [`diagrams.md`](./diagrams.md) | Six Mermaid renderings — tech stack, crew, issue lifecycle, PR lifecycle, funding rails, escalation sequence — plus the guard map as a table. |
| [`factory-model.html`](./factory-model.html) | The two above, plus the model source, as one print-ready page. **Generated — never hand-edit.** |
| `build_page.py`, `page.css` | The generator. `python3 build_page.py` rewrites `factory-model.html` from the sources beside it. |
| `check.mjs`, `package.json` | Diagram checks. `npm install && node check.mjs` parses and renders every mermaid block; exits non-zero on failure. |
| `check_states.py` | State-machine completeness. Asks which *ambient* events — those GitHub, the canary or a human can deliver at any moment — have no transition in a given state. Exits non-zero on any unexplained gap. |

Mermaid was chosen over PlantUML because GitHub renders it inline with no toolchain — the
diagrams stay readable in the same place the source they describe lives.

## What is deliberately *not* in the model

- **The Digest's prose output and the Housekeeper's tidy heuristics.** Both are inline
  prompts whose specifics change often; the model captures their trigger, scope, token
  and tier, which is what governs their blast radius.
- **Per-repo CI internals** beyond runner OS and required-check name. Each repo's
  `ci.yml` is its own concern; the Factory only cares that a green context exists and is
  required.
- **The DPYC network's own economics** — Authorities, certification, demurrage. The
  Factory *consumes* that network as a patron; it does not define it.

## Provenance — element → source map

Every modelled element traces to code in this repository. Where a comment in the model
explains *why* something is shaped the way it is, that rationale came from the source
file's own header comments, which are unusually rich.

| Model element | Source |
|---|---|
| `Roles::Porter`, `Behavior::IssueLifecycle` triage branches | `factory/porter.prompt.md`, `.github/workflows/service-desk.yml` |
| `Roles::Journeyman`, no-change close, reuse-before-build, prove-the-fix | `factory/journeyman.prompt.md`, `.github/workflows/engineering.yml` |
| `Roles::QA`, the invariant checklist | `.github/workflows/qa.yml` (inline prompt) |
| `Roles::PRDialogue` / `PRRevision`, and the split between them | `.github/workflows/pr-dialogue.yml`, `pr-revision.yml`, `factory/pr-revision.prompt.md`, `factory/README.md` |
| `Roles::Housekeeper` | `.github/workflows/housekeeper.yml`, `factory/housekeeper.prompt.md` |
| `Roles::Digest` | `.github/workflows/digest.yml` |
| `Roles::Escalation`, `Guards::G6`, `G7`, escalation sequence | `.github/workflows/escalation.yml` |
| `Roles::AutoMerge` + the low-risk path pattern | `.github/workflows/auto-merge.yml` |
| `Roles::ApprovalMerge` | `.github/workflows/approval-merge.yml` |
| `Roles::DoctrineLint`, `Guards::G1`–`G4`, `G11` | `scripts/doctrine_lint.py`, `.github/workflows/doctrine-lint.yml` |
| `Roles::DeployVerify` | `.github/workflows/deploy-verify.yml`, `scripts/deploy-verify-caller.yml` |
| `Roles::FundingSentinel`, `Guards::G13` | `factory/actions/funding-sentinel/{action.yml,detect_signature.py}` |
| `Roles::CreditCanary`, `Behavior::FundingLifecycle`, the replay table | `.github/workflows/factory-credit-canary.yml` |
| `Roles::BlockRetire`, `Behavior::FundingBlockLifecycle` | `.github/workflows/block-retire.yml`, `factory/actions/funding-sentinel/stamp_cypher.py` |
| `Roles::Scout`, `Identity::ScoutReporter` | `tollbooth-dpyc/src/tollbooth/tools/report_issue.py`, the FIELD REPORTS clause in `factory/porter.prompt.md`, `allowed_non_write_users` in `service-desk.yml` |
| `Identity::AgentKeyring`, `Guards::G9` | the `--mcp-config` blocks in `service-desk.yml` / `engineering.yml`; `tollbooth.agent_keyring` in the SDK |
| `Platform::OpenRouter`, the tier map | `factory/actions/resolve-model/action.yml` |
| `Vocabulary::*` — all 32 labels | `scripts/apply_labels.sh` |
| `Distribution::ThinCaller` and every caller guard | `scripts/factory-callers/agentic-*.yml` |
| `Distribution::SyncFactoryCallers`, `ApplyLabels`, `RequireCICChecks` | `scripts/sync-factory-callers.sh`, `apply_labels.sh`, `require_ci_checks.py` |
| `Guards::G3` (branch protection profile) | `scripts/require_ci_checks.py`, `scripts/factory-CODEOWNERS` |
| `IntentionGraph::*`, `Guards::G10` | cypher-mcp's `scripts/factory_vocabulary.py` write templates; the `mcp__graph__*` grants in the role workflows |
| `Fleet::*` | the escalation allowlist in `escalation.yml`, cross-checked against the working-directory checkouts |

## Reading the model

Three ideas explain most of its shape, and they are worth holding while reading:

1. **Behavior is data; powers are not.** Role prompts live in `factory/*.prompt.md` and
   the crew may evolve them by PR. The workflow skeleton that grants permissions, mints
   tokens and sets `--allowedTools` is human-only — and that separation is *structural*,
   because the GitHub App carries no `workflows: write`, so an agent token cannot push
   such an edit even under a successful injection.
2. **Judgement gets an agent; policy gets bash.** Every gate that could actually land
   code — merge, escalation, lint, deploy verification — is LLM-free, which makes it
   immune both to prompt injection and to an exhausted key at the moment it matters.
3. **Containment is funding, not policy.** Each agent is a DPYC patron holding its own
   nsec and buying its own memory-graph writes with sats. The human's routine oversight
   is topping up balances; a drained agent degrades gracefully rather than stalling.

## Verification

Both files are machine-checked. Neither check is wired into CI yet.

**The model** parses clean under [nomograph-sysml](https://github.com/nomograph-ai/sysml),
a Rust CLI over `tree-sitter-sysml`:

```
cargo install nomograph-sysml
sysml validate docs/model/dpyc-factory.sysml
{"file":"docs/model/dpyc-factory.sysml","valid":true,"diagnostics":[]}
```

Indexing reports 455 elements and 890 relationships, including all 14 requirements, four
state machines with 42 transitions, ten enumerations and twelve packages — so the grammar
is understood, not merely tokenized.

`sysml check all` still reports findings, and as of **v0.2.0 every one of them is a tool
limitation rather than a defect in the model**. Each was isolated to a minimal reproducer:

| Check | Findings | Why |
|---|---|---|
| `DanglingReferences` | 199 | `String` / `Boolean` / `Integer` / `Real` resolve to the SysML v2 standard library, which is not in the index; the remainder are literal value bindings (`= "reader"`, `= false`) counted as unresolved targets. |
| `OrphanRequirements`, `UnverifiedRequirements`, `MissingVerification` | 14 / 14 / 24 | The indexer extracts only `Member` and `TypedBy` relationships — `Satisfy` and `Verify` are never produced, so these checks cannot pass for any model. An eight-line file with `satisfy requirement R by t;` and `verify requirement R;` reports the same findings. |
| `UnconnectedPorts` | 3 | `Connect` is likewise not extracted, and the check also flags port *definitions*, which are never themselves connected. |
| `MetamodelConformance` | 1 | Reports `port def GraphToolPort` as having no type. A port def *is* a type; a two-line canonical port def reproduces it. |

So treat a clean `validate` as the meaningful signal today, and the `check` counts as noise
until the indexer grows those relationship kinds.

With thanks to [Nomograph Labs](https://nomograph.ai/) for the tool — a hand-authored model
is only a claim until something with a real grammar agrees with it.

**The state machines** are checked for completeness by `check_states.py`. Its first run
found six gaps, and acting on them changed the *workflows*, not just the model:

- **No mutual exclusion existed anywhere.** Not one role workflow had a `concurrency:`
  block, so two Journeymen could branch the same `agent/fix-<n>` and race pushes — with the
  credit canary's `agent/fix` re-toggle as the likeliest trigger. `agent/working` was a
  beacon being read as a lock. Every role now carries a per-item concurrency group
  (guard G15); QA is the only one that cancels in flight, because it would otherwise
  review a head that a new push already replaced.
- **A PR closed without merging stranded its issue.** It kept `agent/fix` while no agent
  was coming back, and nothing in the pipeline noticed. The Housekeeper gained an UNSTRAND
  sweep that returns such issues to triage.
- **An owner approval overrides `qa/flag`,** because `approval-merge.yml` reads no `qa/*`
  label at all. That is the intended ordering — QA advises the human rather than vetoing
  them — but it was undocumented, and is now stated in the workflow itself.

The other three were model drift from workflows that already handled the case, and the
check now holds the model to them.

**The diagrams** all parse and render under Mermaid's own engine —
`check.mjs` in this directory runs `mermaid.parse()` then `mermaid.render()` over every
fenced block in `diagrams.md`. Two constructs to avoid in a **sequence** diagram, both of which
bit this document: a literal `--` in message text is lexed as the start of an arrow token,
and a `;` anywhere in a note ends the statement early.

## Caveats

Both files are a snapshot of `main` as read on 2026-07-29. The Factory changes itself by
PR, so re-derive rather than trust this model when the answer matters — `factory/README.md`
is the crew's own living table, and the workflow headers are the authoritative rationale.

The assurance case in §12 is written for a conformant reader. Because nomograph 0.2.0 does
not extract those relationships, its traceability is currently legible to humans and to
other SysML v2 tooling, but invisible to the checker.
