# The DPYC™ Software Factory — rendered views

Mermaid renderings of the model in [`dpyc-factory.sysml`](./dpyc-factory.sysml). GitHub
renders these inline; so does any Markdown viewer with Mermaid support.

Every element traces to source in this repository — see the
[element → file map](./README.md#provenance--element--source-map).

---

## 1. Tech stack

The Factory spans four planes. Only the control plane is GitHub; the memory and money
planes are the DPYC network itself, which is why an agent's graph write is a paid,
signed, patron-authenticated call rather than a database connection.

```mermaid
flowchart TB
    subgraph SRC["📦 Source of truth — lonniev/dpyc-community"]
        RW["📜 Reusable workflows<br/><code>.github/workflows/*.yml</code><br/><i>workflow_call · human-only skeletons</i>"]:::src
        PR["📝 Role prompts<br/><code>factory/*.prompt.md</code><br/><i>crew-editable by PR</i>"]:::src
        CA["🧩 Composite actions<br/><code>resolve-model · funding-sentinel</code>"]:::src
        DL{{"🚧 doctrine_lint.py<br/><i>the tripwires</i>"}}:::det
        SC["🛠 sync-callers · apply_labels · require_ci_checks"]:::src
    end

    subgraph CTRL["🐙 Control plane — GitHub"]
        TC["🔗 Thin callers in 18 repos<br/><i>byte-identical · the if: guard is the boundary</i>"]:::src
        APP(["🔐 GitHub App · id 4292331<br/><i>account-wide · NO workflows:write</i>"]):::gate
        BP{{"🛡 Branch protection + CODEOWNERS<br/><i>code-owner review · approvals 0</i>"}}:::det
    end

    subgraph EXEC["🖥 Execution plane — Actions runners"]
        UB["🐧 ubuntu-latest<br/><i>default for every role</i>"]:::ext
        MAC["🍎 macos-latest<br/><i>when *.xcodeproj / Package.swift is found</i>"]:::ext
        CCA["🤖 claude-code-action@v1<br/><i>automation mode · bubblewrap sandbox</i>"]:::agent
        KR["🔑 tollbooth.agent_keyring<br/><i>stdio MCP · holds the nsec · signs each call</i>"]:::agent
    end

    subgraph INF["🧠 Inference — OpenRouter"]
        W["✍️ writer — Journeyman, Revision"]:::agent
        R["🔍 reader — Porter, QA, Housekeeper, Dialogue"]:::agent
        B["📰 budget — Digest"]:::agent
    end

    subgraph MEM["🕸 Memory + money — the DPYC network"]
        CY["🗝 cypher-mcp<br/><i>named priced queries · never raw access</i>"]:::ext
        AU[("🕸 Neo4j AuraDB<br/><i>ephemeral Bolt · free tier sleeps</i>")]:::data
        LN(["⚡ BTCPay Lightning<br/><i>sats per graph call</i>"]):::money
        NR(["📡 Nostr relays<br/><i>kind-27235 proofs</i>"]):::money
        HZ["☁️ Horizon<br/><i>hosts the MCP operators</i>"]:::ext
        NE[("🗄 Neon Postgres<br/><i>operator vaults + ledgers</i>")]:::data
    end

    RW -->|"uses: …@main"| TC
    SC -->|"one PR per repo"| TC
    TC -->|"secrets: inherit"| EXEC
    APP -->|"mints per-run scoped tokens"| EXEC
    DL --> BP
    PR -->|"curl at run time + restricted envsubst"| CCA
    CA --> CCA
    TC --> UB
    TC --> MAC
    UB --> CCA
    MAC --> CCA
    CCA -->|"--mcp-config, per-server env"| KR
    CCA --> INF
    KR -->|"npub + fresh proof per call"| CY
    CY --> AU
    CY --> LN
    KR --> NR
    CY -.hosted on.-> HZ
    HZ -.-> NE

    classDef agent fill:#ede4ff,stroke:#5319e7,stroke-width:1.5px,color:#2a0d6e
    classDef det   fill:#e2f5e6,stroke:#0e8a16,stroke-width:1.5px,color:#0a4a10
    classDef gate  fill:#fff0dc,stroke:#f7931a,stroke-width:1.5px,color:#6b3f00
    classDef src   fill:#f1f2f6,stroke:#8b93a7,color:#2a2f3a
    classDef ext   fill:#e8eef7,stroke:#5b7fa6,color:#1f3a5f
    classDef data  fill:#e3edf9,stroke:#3f6fa8,stroke-width:1.5px,color:#12324f
    classDef money fill:#fdeedd,stroke:#d98014,stroke-width:1.5px,color:#6b3f00
```

**Stack facts worth keeping in view.** Python 3.12 is canonical fleet-wide, with the SDK
alone on a 3.12/3.13 matrix, which it gates behind a single `test` aggregate. A required-check
context avoids a version suffix — every repo posts `test`, not `test (3.12)` — because a name pinned
to a matrix cell orphans the moment the matrix moves; required checks are set per repo from that
repo's *actual* posted contexts, since a guessed name jams merges forever. `ANTHROPIC_API_KEY` is a name that outlived its provider: it carries the
OpenRouter key, whose Anthropic-compatible endpoint reads the same `x-api-key` header, so
the cutover changed one secret value instead of ~96 call sites.

---

## 2. The crew, and who is allowed to fire it

Judgement gets an agent; policy gets bash. Every gate that could land code is on the
deterministic side of this line, which is what makes the pipeline immune to both prompt
injection *and* a dry key at exactly the moments that matter.

```mermaid
flowchart LR
    subgraph AGENTIC["🧠 LLM roles — judgement"]
        SCOUT["🔭 <b>Scout</b><br/>outside patron via SDK report_issue<br/><i>dpyc-scout · non-collaborator</i>"]:::agent
        PORTER["🛎 <b>Porter</b> — Service Desk<br/><i>reader · 20 turns · issue ops only</i>"]:::agent
        JM["🔧 <b>Journeyman</b> — Engineering<br/><i>writer · 140 turns · contents:write</i>"]:::agent
        QA["🔍 <b>QA</b><br/><i>reader · 30 turns · diff only</i>"]:::agent
        DIA["💬 <b>PR Dialogue</b><br/><i>read-only by construction · anyone may summon</i>"]:::agent
        REV["✍️ <b>PR Revision</b><br/><i>writer · OWNER-gated</i>"]:::agent
        HK["🧹 <b>Housekeeper</b><br/><i>weekly sweep · Porter identity</i>"]:::agent
        DG["📰 <b>Digest</b> — the Dispatcher<br/><i>budget · fleet-wide · not reusable</i>"]:::agent
    end

    subgraph DET["⚙️ Deterministic roles — policy"]
        ESC{{"🚚 <b>Escalation</b><br/><i>only cross-repo writer · issues:write only</i>"}}:::det
        AM{{"🚦 <b>Auto-merge</b><br/><i>path allowlist</i>"}}:::det
        APM{{"🔏 <b>Merge on Approval</b><br/><i>--auto, cannot bypass protection</i>"}}:::det
        DLINT{{"🚧 <b>Doctrine Lint</b><br/><i>the tripwires</i>"}}:::det
        DV{{"📡 <b>Deploy Verify</b><br/><i>sha compare after merge</i>"}}:::det
        FS{{"🩺 <b>Funding Sentinel</b>"}}:::det
        CC{{"🐤 <b>Credit Canary</b><br/><i>every 30 min</i>"}}:::det
        BR{{"🗃 <b>Block Retire</b>"}}:::det
        CW{{"⛔ <b>Conflict Watch</b><br/><i>hourly · flags PRs the pipeline cannot see</i>"}}:::det
    end

    HUMAN(["👤 Human or stranger"]):::human
    OWNER(["👑 Repository owner"]):::human
    ANY(["👥 Any reviewer"]):::human
    MERGED(["✅ merged"]):::done

    SCOUT -->|"files a field report"| PORTER
    HUMAN -->|"opens an issue"| PORTER
    PORTER -->|"agent/fix"| JM
    PORTER -->|"blocked/upstream"| ESC
    ESC -->|"files agent/fix upstream"| JM
    JM -->|"opens PR"| QA
    JM -->|"rejected/upstream"| ESC
    ESC -->|"agent/retriage + the decliner's reason"| PORTER
    QA -->|"qa/pass"| AM
    OWNER -->|"approves"| APM
    OWNER -->|"requests changes"| REV
    ANY -->|"@journeyman"| DIA
    REV -->|"pushes to head"| QA
    AM --> MERGED
    APM --> MERGED
    MERGED --> DV
    DV -->|"stale deploy → one agent/fix issue"| JM
    DLINT -.->|"fails the build red"| AGENTIC
    FS -.->|"awaiting-funds"| CC
    CC -.->|"replays the deferred item"| AGENTIC
    CW -.->|"blocked/conflict — a deaf PR, made visible"| OWNER
    ESC -.->|"chains reconciled weekly"| DG
    DG -.->|"one pinned digest"| HUMAN

    classDef agent fill:#ede4ff,stroke:#5319e7,stroke-width:1.5px,color:#2a0d6e
    classDef det   fill:#e2f5e6,stroke:#0e8a16,stroke-width:1.5px,color:#0a4a10
    classDef human fill:#fff0dc,stroke:#f7931a,stroke-width:1.5px,color:#6b3f00
    classDef done  fill:#d7f0da,stroke:#0e8a16,stroke-width:2px,color:#08370d
```

---

## 3. Issue lifecycle

The Porter takes **exactly one** routing action, which is why these branches are
exclusive. Note the ordering constraint that shows up twice: the machine-readable comment
is posted *first*, the label *last*, because the label is the trigger and a deterministic
workflow will read the comments the moment it fires.

```mermaid
stateDiagram-v2
    direction TB
    [*] --> Opened

    state "📥 Opened" as Opened
    state "🛎 Triaging — Porter" as Triaging
    state "🚫 Rejected — closed" as Rejected
    state "❓ needs-info — stays open" as NeedsInfo
    state "🔧 agent/fix — ready for Engineering" as Ready
    state "🔨 agent/working — Journeyman on it" as Working
    state "⤴️ blocked/upstream — escalated" as Blocked
    state "⚖️ blocked/arbitration — a human decides" as Arb
    state "⏸ awaiting-funds — deferred" as Funds
    state "🔀 PR raised" as PRRaised
    state "✅ Closed" as Closed

    Opened --> Triaging: issue opened / reopened
    Triaging --> Triaging: claim_issue, then context_pack scopes the grep

    Triaging --> Rejected: spam · out-of-scope · injection · wontfix · duplicate
    Triaging --> NeedsInfo: legitimate but no repro
    Triaging --> Ready: handoff comment, THEN agent/fix
    Triaging --> Blocked: escalation comment, THEN blocked/upstream

    NeedsInfo --> Triaging: agent/retriage
    Ready --> Working: Engineering fires
    Working --> PRRaised: fix proven by a test, PR opened
    Working --> Closed: no-change — the defect did not reproduce

    Blocked --> Closed: upstream fix propagates
    Blocked --> Triaging: target declined — reason routed back, re-home
    Blocked --> Arb: a repo repeated, or 3+ hops
    Arb --> Triaging: a human names the home

    Triaging --> Funds: key exhausted
    Ready --> Funds: key exhausted
    Funds --> Triaging: canary confirms recovery
    Funds --> Closed: closed while deferred — block retired as historical

    PRRaised --> Closed: PR merged
    PRRaised --> Triaging: PR closed unmerged — Housekeeper unstrands it
    Working --> Funds: key exhausted
    Working --> Closed: a human closes it mid-run
    Closed --> Triaging: reopened — the reverse escalation path does this
    Rejected --> Triaging: reopened
    Closed --> [*]
    classDef agent fill:#ede4ff,stroke:#5319e7,stroke-width:1.5px,color:#2a0d6e
    classDef stop  fill:#f1f2f6,stroke:#8b93a7,color:#2a2f3a
    classDef warn  fill:#ffe6e2,stroke:#d93f0b,stroke-width:1.5px,color:#6b1c00
    classDef money fill:#fdeedd,stroke:#d98014,stroke-width:1.5px,color:#6b3f00
    classDef done  fill:#d7f0da,stroke:#0e8a16,stroke-width:1.5px,color:#08370d
    classDef human fill:#fff0dc,stroke:#f7931a,stroke-width:1.5px,color:#6b3f00

    class Triaging,Ready,Working agent
    class Rejected,NeedsInfo stop
    class Blocked warn
    class Arb human
    class Funds money
    class PRRaised,Closed done
```

---

## 4. Pull request lifecycle

One state here is unlike the others. **`blocked/conflict` is not blocked, it is deaf**:
GitHub dispatches no PR workflow runs at all while a pull request conflicts with its base,
so QA, auto-merge and Merge on Approval never hear about it. An owner can approve and watch
nothing happen, with no failing check to explain the silence. A PR enters it without doing
anything — someone else merged first — which is why the hourly Conflict Watch sweep exists
to notice and say so.

Two merge paths, both deterministic, neither able to bypass branch protection. The
"Merge Oops" question answers itself here: `--auto` never lands on a red required check —
it *holds* until the gates go green, so a bad merge is not a risk this design mitigates,
it is one the design cannot express.

```mermaid
stateDiagram-v2
    direction TB
    [*] --> AwaitingQA

    state "⏳ Awaiting QA" as AwaitingQA
    state "🚩 qa/flag — concern raised" as Flagged
    state "🔍 qa/pass" as Passed
    state "👑 Awaiting the owner — CODEOWNERS holds it" as Human
    state "✍️ agent/revising — PR Revision at the bench" as Revising
    state "🔏 Auto-merge armed — GitHub holds it pending" as Armed
    state "✅ Merged" as Merged
    state "⏸ awaiting-funds" as PRFunds
    state "🗃 Closed unmerged — the Housekeeper unstrands the waiting issue" as Abandoned
    state "⛔ blocked/conflict — DIRTY: no PR workflow fires at all" as Conflicted

    AwaitingQA --> Passed: diff fixes the issue, test present, invariants intact
    AwaitingQA --> Flagged: any concern
    note right of AwaitingQA
        Only same-repo agent/fix-* branches reach QA.
        A fork PR receives no secrets, so it never runs.
    end note

    Passed --> Armed: every changed path is docs / tests / frontend / *.md
    Passed --> Human: any code or money-adjacent path
    Flagged --> Human

    Human --> Armed: OWNER approves
    Human --> Revising: OWNER requests changes, or "@journeyman revise"
    Flagged --> Revising: OWNER requests changes
    Revising --> AwaitingQA: revision pushed to the head branch

    Armed --> Merged: branch protection satisfied — required checks green + code-owner review
    Armed --> Revising: OWNER later requests changes — --auto keeps holding
    Flagged --> Armed: OWNER approves anyway — QA advises, it does not veto

    AwaitingQA --> PRFunds: key exhausted
    Revising --> PRFunds: key exhausted
    PRFunds --> AwaitingQA: canary recovery
    PRFunds --> Revising: mid-revision — the owner re-requests, never the bot
    AwaitingQA --> Abandoned: closed without merging
    Flagged --> Abandoned
    Passed --> Abandoned
    Human --> Abandoned
    Revising --> Abandoned
    AwaitingQA --> Conflicted: the base moved — someone else merged first
    Passed --> Conflicted
    Human --> Conflicted
    Revising --> Conflicted
    Armed --> Conflicted
    Conflicted --> AwaitingQA: conflict resolved — a push, so review starts over
    Conflicted --> Abandoned: closed instead
    Merged --> [*]
    Abandoned --> [*]
    classDef agent fill:#ede4ff,stroke:#5319e7,stroke-width:1.5px,color:#2a0d6e
    classDef stop  fill:#f1f2f6,stroke:#8b93a7,color:#2a2f3a
    classDef warn  fill:#ffe6e2,stroke:#d93f0b,stroke-width:1.5px,color:#6b1c00
    classDef money fill:#fdeedd,stroke:#d98014,stroke-width:1.5px,color:#6b3f00
    classDef done  fill:#d7f0da,stroke:#0e8a16,stroke-width:1.5px,color:#08370d
    classDef human fill:#fff0dc,stroke:#f7931a,stroke-width:1.5px,color:#6b3f00

    class AwaitingQA,UnderReview,Revising agent
    class Flagged warn
    class Passed,Merged done
    class Human human
    class Armed done
    class PRFunds money
    class Abandoned stop
    class Conflicted warn
```

---

## 5. Funding — two independent rails

The crew spends on two rails that fail independently, and the design leans on that. LLM
credits buy inference; **sats** buy graph writes. When the inference rail is dry, the sats
rail still works — which is exactly how "what is currently awaiting funds" stays queryable
while every LLM node is dark.

```mermaid
stateDiagram-v2
    direction LR
    state "🧠 Rail A — LLM credits · one shared key · OpenRouter" as RailA {
        [*] --> Healthy
        Healthy --> Unknown: transient 429 / 529 / network
        Unknown --> Healthy: next probe returns 200
        Healthy --> Broke: non-200 naming credit / billing / quota / spend
        Broke --> Deferring: sentinel tags each affected item
        Deferring --> Replaying: probe returns 200 again
        Broke --> Replaying: probe returns 200 again
        Replaying --> Healthy: fleet swept, work re-fired
    }

    state "⚡ Rail B — sats · per-agent patron balance" as RailB {
        [*] --> Funded
        Funded --> Drained: balance spent
        Drained --> Funded: the human tops up
        note right of Drained
            Containment is funding, not policy.
            A drained agent still triages and labels;
            only its graph writes stop. Every graph
            call is best-effort and non-fatal.
        end note
    }
```

**Outage detection is a signature, not a guess.** A dry key makes the action fail on turn 1
with `is_error:true`, `num_turns <= 1`, `total_cost_usd == 0` — rejected before any work,
billed nothing. That exact shape is the *only* thing tagged `awaiting-funds`; a genuine
agent failure shows real turns, real cost, and usually permission denials, so it is never
mislabeled and quietly retried forever.

**Replay is discriminated by what the item already carries**, because the labels record
which node the outage cut:

| Item | Carries | Node that was skipped | Recovery action |
|---|---|---|---|
| Issue | no `agent/fix` | Porter | add `agent/retriage` |
| Issue | `agent/fix` | Engineering | re-toggle `agent/fix` |
| PR | no `agent/revising` | QA | add `agent/retriage` |
| PR | `agent/revising` | PR Revision | **comment only** — the owner must re-request |

That last row is a deliberate refusal. PR Revision is gated on a human owner review, and
letting the bot re-trigger a write-capable role would dissolve exactly the boundary that
gate exists to hold.

---

## 6. Escalation and the anti-ping-pong loop

Escalation is the only workflow that writes across repositories, and it holds the only
account-wide token — downscoped to `issues: write` and nothing else. Widened scope is
always paired with narrowed permission.

The markers named below are HTML comments in the issue thread — `<!-- dpyc-escalation -->`,
`<!-- dpyc-rejection -->`, `<!-- dpyc-route-history: a,b -->` — written out in full in
§Items of the model. They are named rather than quoted here because a literal `--` inside a
Mermaid sequence message is lexed as the start of an arrow token and breaks the diagram.

```mermaid
sequenceDiagram
    autonumber
    participant O as 🐙 Origin repo
    participant P as 🛎 Porter @ origin
    participant E as ⚙️ Escalation<br/>deterministic
    participant H as 🐙 Home repo
    participant J as 🔧 Journeyman @ home

    P->>O: post the dpyc-escalation marker comment
    P->>O: apply blocked/upstream (the trigger — always last)
    O->>E: issues.labeled
    E->>E: parse home_repo, validate against the 18-repo allowlist
    E->>E: per-home idempotency — already escalated to THIS home?
    E->>H: gh issue create, labeled agent/fix, stamped Origin: + escalated-child
    E->>O: comment, stamped dpyc-escalated for that home

    alt Home owns it
        H->>J: agent/fix fires Engineering
        J->>H: fix + test + PR
        Note over O,H: origin closes when the fix propagates
    else Home declines
        J->>H: post a dpyc-rejection marker naming the true owner, or why it is a no-op
        J->>H: apply rejected/upstream, then STOP — never re-route to a third repo
        H->>E: issues.labeled
        E->>O: post the reason back, stamped dpyc-route-history: a,b
        E->>H: close the child as not planned
        alt repeat repo, or 3+ hops
            E->>O: blocked/arbitration + @-mention the owner
            Note over O: frozen for a human — it will never bounce again
        else still routable
            E->>O: agent/retriage — reopens the Porter WITH the decline reason in hand
            Note over P: the passed-repos set is durable —<br/>escalating back into it is never an option
        end
    end
```

The subtle bug this shape had to fix: idempotency was originally *unscoped* — any
"already escalated" marker stopped further routing. That meant an issue declined by its
first home could never be re-homed. Idempotency is now **per home**, so each home is
escalated at most once while a re-home stays possible.

---

## 7. Guard map — who can change what

Most of these are enforced by something in this repository — a linter rule, a token scope, a
caller expression — so reading the code tells you whether they hold. **G3 is the exception:
branch protection is live server-side state that no file here controls.** It was documented as
holding fleet-wide while six repos had no gate at all. Where a guard's mechanism is
configuration rather than code, the table says when it was last verified, not that it is
currently true.

| # | Guard | Enforced by | Mechanism, not a promise |
|---|---|---|---|
| G1 | An agent cannot change the powers it is granted | GitHub App scope + `doctrine_lint` | The App holds no `workflows: write`, so the token *cannot* push a `.github/workflows/` edit; the linter fails red if a diff adds the permission |
| G2 | No self-merge, no self-approval | `doctrine_lint` on `--allowedTools` | Bans `gh pr review`, `Bash(gh:*)`, `Bash(gh pr:*)`, bare and `--admin` `gh pr merge`; permits only the gated `gh pr merge --auto` |
| G3 | Money paths need a human | CODEOWNERS + branch protection | `* @lonniev` catch-all with `require_code_owner_reviews`; approvals set to 0 so docs still auto-land; `enforce_admins` false keeps the owner's escape hatch. **Live server-side config, not code — it drifts.** An audit on 2026-07-29 found six repos with no gate at all; all 19 corrected, and `require_ci_checks.py` now *sets* the profile rather than preserving what it finds. Nothing schedules that audit, so read a green G3 as "true when someone last ran it" |
| G4 | Fork PRs get no secrets | `pull_request` only, banned `pull_request_target` | The trigger is banned outright rather than guarded by an `if`, because a blanket ban is auditable |
| G5 | Write-capable + human-triggered ⇒ owner-only | Caller `if:` expression | PR Revision requires `author_association == 'OWNER'`; PR Dialogue pays for open access by having no write tools and `contents: read` tokens |
| G6 | Cross-repo writes are issues-only | Token permission + allowlist | Account-wide token downscoped to `permission-issues: write`; `home_repo` word-boundary-matched against 18 repos before any write |
| G7 | No issue ping-pong | Escalation reverse path | Durable `passed_repos` set; a repeat repo or 3 hops freezes the issue as `blocked/arbitration` |
| G8 | Untrusted input is always data | Prompt anchors + `--allowedTools` | No `curl`, `bash -c`, `eval` or `rm`; every `gh` subcommand enumerated; the agent holds no secrets; an injection *attempt* is itself grounds to close |
| G9 | Secrets never enter the agent shell | `--mcp-config` per-server env; git auth header | The nsec lives only in the keyring subprocess; Dialogue's investigation token is a git header, never an env var |
| G10 | Provenance cannot be forged | cypher-mcp write template | `llm-inferred-unverified` is a Cypher **literal**, not a parameter — there is no argument that claims human authority |
| G11 | Prompts keep their safety anchors | `doctrine_lint` | `SECURITY` + `UNTRUSTED` everywhere, plus `MANDATORY OUTCOME` for Porter and PR Revision |
| G12 | Containment is funding | Per-agent patron balance | Fund the Porter thin, the Journeyman thicker; a drained agent degrades, it does not stall the pipeline |
| G13 | An outage defers, it does not fail | Funding sentinel signature | Only `is_error && turns ≤ 1 && cost == 0` counts as an outage |
| G15 | One run per role per work-item | GitHub `concurrency` group | Group is (role, repo, item number). Two Journeymen would branch the same `agent/fix-<n>` and race pushes; the canary's `agent/fix` re-toggle is the likeliest trigger. Only QA cancels in flight — it would otherwise stamp a verdict on a head that a new push replaced |
| G14 | Judgement gets an agent, policy gets bash | Role roster | Every merge, escalation, lint and verify gate is LLM-free, and therefore immune to injection and to a dry key |
