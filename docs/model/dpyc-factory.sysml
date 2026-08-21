// =============================================================================
//  The DPYC Software Factory — SysML v2 textual model
//
//  Subject: the unattended agentic crew (Scout, Porter, Journeyman, QA,
//  Housekeeper) that triages, fixes, reviews and lands work across the DPYC
//  fleet of GitHub repositories.
//
//  Provenance: every element below is derived from source in
//  lonniev/dpyc-community — .github/workflows/*.yml (reusable skeletons),
//  scripts/factory-callers/*.yml (thin per-repo callers), factory/*.prompt.md
//  (role behavior), factory/actions/* (deterministic composite actions),
//  scripts/doctrine_lint.py (the tripwires) and scripts/apply_labels.sh (the
//  label alphabet). See docs/model/README.md for the element -> file map.
//
//  Two rules of the modelled system that explain most of its shape:
//    1. Behavior is data the crew may evolve by PR; the workflow SKELETON that
//       grants powers is human-only. The GitHub App holds no `workflows: write`,
//       so that separation is structural, not a promise.
//    2. Containment is funding, not policy. A drained agent degrades — it keeps
//       triaging and stops writing to the memory graph.
// =============================================================================

package DPYCSoftwareFactory {

    doc /*
     * The Factory is one federated pipeline instantiated N times: logic lives once
     * in dpyc-community as `workflow_call` reusables; each fleet repo carries only
     * byte-identical thin callers. Language dispatch happens inside the reusable
     * (an Xcode/Swift probe picks macos-latest), so onboarding a repo never means
     * customizing YAML.
     */

    // -------------------------------------------------------------------------
    private import ScalarValues::*;

    // =========================================================================
    //  1. VOCABULARY — the label alphabet is the pipeline's shared contract.
    //     Applied per repo by scripts/apply_labels.sh (32 labels).
    // =========================================================================
    package Vocabulary {

        enum def IssueType {
            'type/bug'; 'type/feature'; 'type/docs'; 'type/question'; 'type/chore';
        }

        enum def Area {
            'area/ledger'; 'area/pricing'; 'area/vault';
            'area/auth'; 'area/ci'; 'area/docs'; 'area/ui';
        }

        enum def Severity {
            'sev/critical'; 'sev/high'; 'sev/medium'; 'sev/low';
        }

        /* Routing labels. Each is a workflow TRIGGER, which is why the prompts
         * insist the machine-readable comment be posted BEFORE the label lands. */
        enum def RoutingLabel {
            'agent/fix';               // -> Engineering (Journeyman)
            'agent/working';           // liveness beacon, stamped/cleared by the skeleton
            'agent/revising';          // liveness beacon for PR Revision; canary discriminator
            'agent/retriage';          // replay marker -> Porter (issues) or QA (PRs)
            'blocked/upstream';        // -> Escalation, forward path
            'rejected/upstream';       // -> Escalation, reverse (anti-ping-pong) path
            'blocked/arbitration';     // routing standoff frozen for a human
            'blocked/conflict';        // conflicts with base — NO pr workflow will fire
        }

        enum def RejectionLabel {
            'rejected/spam'; 'rejected/out-of-scope'; 'rejected/injection';
            'rejected/wontfix'; 'rejected/duplicate';
            'rejected/needs-info';     // the only rejection that stays OPEN
        }

        enum def QAVerdict { 'qa/pass'; 'qa/flag'; }

        enum def FundingLabel { 'awaiting-funds'; 'factory/outage'; }

        /* What the Porter records as its single routing action. */
        enum def Disposition { 'agent/fix'; 'rejected'; 'blocked/upstream'; 'needs-info'; }

        /* The token-savings metric: how the code was located. `wide-grep` is the
         * expensive path the intention graph exists to eliminate. */
        enum def ResolvedVia { graph; 'scoped-grep'; 'wide-grep'; }

        /* Provenance of a why-statement in the memory graph. An agent may only
         * ever write the second one — cypher-mcp hard-codes it as a Cypher
         * literal, so the value cannot be forged through a parameter. */
        enum def Provenance { 'human-authored'; 'llm-inferred-unverified'; }
    }

    // =========================================================================
    //  2. ITEMS — what flows through the Factory.
    // =========================================================================
    package Items {
        private import Vocabulary::*;

        item def Issue {
            attribute number : Integer;
            attribute title : String;
            attribute body : String;              // UNTRUSTED. Data, never instructions.
            attribute isFieldReport : Boolean;    // carries a <!-- dpyc-field-report --> marker
            attribute isEscalatedChild : Boolean; // carries a <!-- dpyc-escalated-child --> marker
        }

        item def PullRequest {
            attribute number : Integer;
            attribute headRef : String;           // 'agent/fix-<n>' for Journeyman PRs
            attribute sameRepo : Boolean;         // false => a fork => no secrets
            attribute touchesOnlyLowRiskPaths : Boolean;
        }

        /* Machine-readable comment blocks. These are the Factory's wire protocol:
         * a deterministic workflow parses them, so their shape is load-bearing. */
        item def HandoffComment {                 // <!-- dpyc-handoff -->
            attribute actionable_text : String;   // Porter's 1-2 sentence spec
            attribute capability : String;
            attribute files : String;
            attribute symbols : String;
            attribute invariants : String;
        }

        item def EscalationComment {              // <!-- dpyc-escalation -->
            attribute home_repo : String;         // validated against a fixed allowlist
            attribute title : String;
            attribute reason : String;
            attribute repro : String;
        }

        item def RejectionComment;                // <!-- dpyc-rejection -->    reverse path
        item def RouteBackComment;                // <!-- dpyc-route-back -->   reason returned
        item def RouteHistoryMarker {             // <!-- dpyc-route-history: a,b -->
            attribute passed_repos : String;      // durable anti-ping-pong set
            attribute hops : Integer;
        }
        item def FieldReportMarker {              // <!-- dpyc-field-report ... -->
            attribute reporter : String;          // proven npub — SDK-authored, unspoofable
            attribute tool : String;
        }

        /* claude-code-action's execution transcript. Its shape is what the
         * funding sentinel classifies on. */
        item def AgentResult {
            attribute is_error : Boolean;
            attribute num_turns : Integer;
            attribute total_cost_usd : Real;
            attribute permission_denials_count : Integer;
        }
    }

    // =========================================================================
    //  3. IDENTITY — every agent is a DPYC patron holding its own nsec.
    //     No new actors, no stored tokens, nothing granted per call: the agent
    //     signs its own ephemeral kind-27235 proof of possession per request.
    // =========================================================================
    package Identity {

        part def NostrIdentity {
            attribute npub : String;
            attribute nip05 : String;
            /* The nsec is deliberately NOT an attribute of anything reachable
             * from the agent: it exists only in the keyring subprocess env. */
        }

        part def AgentKeyring {
            doc /* `python -m tollbooth.agent_keyring` from tollbooth-dpyc[keyring].
                 * A FastMCP create_proxy plus one middleware that injects the npub
                 * and a FRESH kind-27235 proof into every forwarded call. Mounted
                 * as a local stdio MCP server via claude-code-action's
                 * --mcp-config, whose per-server `env` is isolated from the
                 * agent's own shell. It is the agent's signing HAND, not an actor. */
            attribute upstream : String = "https://cypher-mcp.fastmcp.app/mcp";
            attribute sdkExtra : String = "tollbooth-dpyc[keyring]==0.63.1";
            port graphTools : GraphToolPort;
        }

        item def SignedToolCall {
            doc /* One mcp__graph__cypher_* call as it leaves the keyring: the patron
                 * npub and a freshly minted kind-27235 proof attached. Nothing is
                 * stored — a DPoP is proof of possession for THIS call only, which is
                 * why there is no token to expire, leak, or revoke. */
            attribute tool : String;
            attribute npub : String;
            attribute proofKind : Integer = 27235;
        }

        item def GraphAnswer {
            doc /* The operator's reply, or a situation. Every graph write in the
                 * Factory is best-effort: an answer that never arrives degrades the
                 * record, never the GitHub outcome the agent already committed. */
            attribute ok : Boolean;
            attribute situation : String;
        }

        port def GraphToolPort {
            doc /* The keyring's outward face — the mcp__graph__cypher_* verbs as the
                 * agent sees them. Directed, because the asymmetry IS the design: the
                 * agent emits a call it cannot sign for itself, and the signing happens
                 * on the far side of this boundary, in a subprocess whose env it cannot
                 * read. */
            out item call : SignedToolCall;
            in item answer : GraphAnswer;
        }

        interface def GraphChannel {
            doc /* Agent-to-operator over the sats rail: a priced, proof-authenticated
                 * MCP call. Orthogonal to the LLM-credit rail, which is what keeps the
                 * memory queryable during an inference outage. */
            end consumer : GraphToolPort;
            end supplier : ~GraphToolPort;
        }

        part porterIdentity : NostrIdentity {
            attribute redefines npub = "npub1ymgfh46ace33zgld5zdc7gyhc5keyu42v36td0q7c44ks45d79eslwe2q2";
            attribute redefines nip05 = "porter@tollbooth-dpyc.org";
        }

        part journeymanIdentity : NostrIdentity {
            attribute redefines npub = "npub1m5quz5w0e96t36s7qw9tgnk90n0r0l2gxra75px4qnlu08lwaqnsskw7rk";
            attribute redefines nip05 = "journeyman@tollbooth-dpyc.org";
        }

        /* Scout is NOT a workflow. It is an outside patron — Claude.ai reporting
         * under its own npub through the SDK `report_issue` tool — whose reports
         * arrive on a dedicated `dpyc-scout` GitHub account that is deliberately a
         * NON-collaborator with zero write access. */
        part def ScoutReporter :> NostrIdentity {
            attribute githubAccount : String = "dpyc-scout";
            attribute writeAccess : Boolean = false;
        }
    }

    // =========================================================================
    //  4. PLATFORM — the tech stack the Factory executes on.
    // =========================================================================
    package Platform {

        part def GitHubActionsRunner {
            attribute image : String;             // ubuntu-latest | macos-latest
            attribute costMultiplier : Real;      // macOS bills ~10x ubuntu minutes
        }

        part def AgentHarness {
            doc /* anthropics/claude-code-action@v1 in automation mode: `prompt:`
                 * plus `claude_args:`. It commits and pushes but never merges.
                 * Runs the agent's Bash inside a bubblewrap sandbox (enabled by
                 * allowed_non_write_users), which is why every Linux job carries
                 * the /home/.mcp.json pre-step. */
            attribute version : String = "anthropics/claude-code-action@v1";
            attribute maxTurns : Integer;
            attribute modelSlug : String;
            attribute allowedTools : String;      // the real capability boundary
            attribute allowedBots : String = "dpyc-agentic-desk[bot]";
        }

        part def GitHubApp {
            doc /* "DPYC Agentic Desk". Installed account-wide. The absence of
                 * `workflows: write` is the structural leash: an agent token
                 * literally cannot push an edit to .github/workflows/. */
            attribute appId : String = "4292331";
            attribute hasWorkflowsWrite : Boolean = false;
        }

        part def ScopedToken {
            doc /* actions/create-github-app-token@v2. Omitting `repositories`
                 * and `owner` scopes a token to THIS repo — the default posture.
                 * Widening scope is always paired with narrowing permission. */
            attribute repoScoped : Boolean = true;
            attribute accountWide : Boolean = false;
            attribute permissions : String;
        }

        /* --- external services -------------------------------------------- */
        part def OpenRouter {
            doc /* The Factory's inference rail. ANTHROPIC_API_KEY carries the
                 * OpenRouter key (its Anthropic-compatible endpoint reads
                 * x-api-key) and ANTHROPIC_BASE_URL overrides the host, so the
                 * secret NAME stayed put across ~96 call sites and only its value
                 * changed. With the base URL overridden there is no
                 * api.anthropic.com left to fall back to. */
            attribute baseUrl : String = "https://openrouter.ai/api";
        }

        part def Horizon {
            doc /* The managed platform hosting the MCP operators. Builds from
                 * requirements.txt (not `pip install -e .`), keeps entrypoint and
                 * root dir in its dashboard, and redeploys on any push to main. */
        }

        part def Neo4jAuraDB {
            doc /* cypher-mcp's graph store, reached over ephemeral Bolt. The free
                 * tier SLEEPS: the first write after idle can exceed a named
                 * query's timeout_ms and fail, then succeed on retry — harmless
                 * because cypher-mcp refunds on raise. */
            attribute tier : String = "free";
            attribute sleepsWhenIdle : Boolean = true;
        }

        part def NeonPostgres {
            doc /* Operator/Authority vault + ledger persistence. Not on the
                 * Factory's own hot path; reached only through operator MCPs. */
        }

        part def BTCPayServer;      // Lightning rail for sats
        part def NostrRelaySet;     // identity proofs, Secure Courier DMs, audit
    }

    // =========================================================================
    //  5. THE MEMORY — cypher-mcp is where the crew's reasoning is durable.
    // =========================================================================
    package IntentionGraph {
        private import Vocabulary::*;
        private import Identity::GraphToolPort;

        part def CypherOperator {
            doc /* A monetized MCP operator, not a database handle. It sells
                 * operator-authored, parameterized NAMED queries — never raw
                 * graph access. Write templates carry access_mode='write'.
                 * Access is the Constraint Engine (a json_expression allow-list
                 * on patron.npub per published tool), never bespoke per-tool ACL. */
            attribute endpoint : String = "https://cypher-mcp.fastmcp.app/mcp";
            port patronCalls : ~GraphToolPort;
        }

        item def Service      { attribute name : String; }
        item def Capability   { attribute name : String; attribute keywords : String;
                                attribute why : String; attribute provenance : Provenance; }
        item def Symbol       { attribute fqn : String; attribute lang : String;
                                attribute file_path : String; attribute verified_at_sha : String; }
        item def Invariant    { attribute name : String; }
        item def GraphIssue   { attribute number : Integer; attribute disposition : Disposition;
                                attribute resolved_via : ResolvedVia; attribute actionable_text : String; }
        /* First-class since the PRs-in-graph work: a real node, never a mirror.
         * It FIXES a GraphIssue, and THROUGH that issue it ENFORCES the issue's
         * Capability — a TRAVERSAL (PR -> FIXES -> Issue -> Capability), never a
         * stored edge, so a PR carries intention only through the issue it fixes.
         * A capability-less issue leaves its PR tracing to no intention, which is
         * why triage must always resolve one (see Roles::Porter, Roles::Journeyman). */
        item def GraphPullRequest { attribute number : Integer; attribute merged : Boolean; }
        item def Decision     { attribute decision_id : String; attribute statement : String;
                                attribute reason : String; attribute provenance : Provenance; }
        item def FundingBlock { attribute state : String; }   // active | clear | historical

        /* Read verbs both LLM roles use to SCOPE their work instead of grepping
         * twelve repos. cypher_context_pack is the default retrieval tier. */
        action def ContextPack { in keyword : String; out capabilities : Capability[0..*];
                                 out symbols : Symbol[0..*]; out precedent : GraphIssue[0..*]; }

        /* Write verbs. Porter and Journeyman hold DIFFERENT sets — see Roles. */
        action def RecordTriage;  action def RecordScope;   action def NoteRejection;
        action def LinkRootCause; action def ClaimIssue;    action def RouteRejection;
        action def AssertRationale {
            doc /* Provenance is a Cypher LITERAL inside the template, not a
                 * parameter, so an agent cannot claim human authority. */
            out provenance : Provenance = Provenance::'llm-inferred-unverified';
        }
        action def SuggestCapabilityWhy :> AssertRationale;

        /* Capability + PR intention writes, added after the model's first snapshot.
         * upsert_capability records the node a triage discovers or mints;
         * link_issue_to_capability makes the issue refer to it (a MANDATORY triage
         * outcome, see Roles); link_pr records PR -FIXES-> Issue so the enforce
         * traversal PR -> Issue -> Capability resolves. These are structure and
         * edges, not claims — provenance lives on the why below. */
        action def UpsertCapability;
        action def LinkIssueToCapability;
        action def LinkPr;

        /* The authoritative why. NOT an agentic verb — gated to the Code Owner
         * identity, and the only write that stamps 'human-authored'. The agents
         * propose (SuggestCapabilityWhy); the human legislates here. */
        action def AuthorizeCapabilityWhy {
            out provenance : Provenance = Provenance::'human-authored';
        }

        action def MarkFundingState;  action def RetireFundingBlock;
    }

    // =========================================================================
    //  6. ROLES — the crew. Two kinds: LLM-driven and deterministic.
    //     The split is doctrine: judgement gets an agent, policy gets bash.
    // =========================================================================
    package Roles {
        private import Platform::*;
        private import Identity::*;

        abstract part def FactoryRole {
            attribute name : String;
            attribute firesOn : String;
            attribute canWriteCode : Boolean;
            part token : ScopedToken;
        }

        abstract part def AgenticRole :> FactoryRole {
            doc /* Behavior lives in a prompt file the crew may evolve by PR; the
                 * skeleton around it is human-only. The prompt is fetched at run
                 * time from raw.githubusercontent.com and rendered with envsubst's
                 * RESTRICTED form — only ${REPO} ${REPO_NAME} ${ISSUE_NUMBER} are
                 * substituted, so nothing else in the file can expand. */
            attribute promptFile : String;
            attribute modelTier : String;         // writer | reader | budget
            part harness : AgentHarness;

            doc /* MUTUAL EXCLUSION. Every role is keyed to one run per work-item by a
                 * GitHub `concurrency` group of (role, caller repo, issue-or-PR number).
                 * This was missing entirely until a state/event completeness pass went
                 * looking for it: `agent/working` and `agent/revising` are BEACONS that
                 * say a run is live, and were being read as locks, which they never
                 * were. Only QA cancels an in-flight run — it reviews a head that a new
                 * push has already replaced. Every other role queues, because these runs
                 * push commits and open PRs, and a half-killed one leaves worse state
                 * than a late one. */
            attribute concurrencyGroup : String;
            attribute cancelInProgress : Boolean = false;
        }

        abstract part def DeterministicRole :> FactoryRole {
            doc /* No LLM on purpose. These decide facts, not judgements — "the
                 * owner approved", "this path is docs", "this sha matches" — and
                 * so they are immune to both prompt injection and a dry key. */
            attribute usesLLM : Boolean = false;
        }

        // --- intake ----------------------------------------------------------
        part def Scout :> FactoryRole {
            doc /* Not a workflow: an outside proven patron filing a field report
                 * through the SDK `report_issue` tool. The SDK composes the issue
                 * body — author-of-record header plus marker — from the PROVEN
                 * caller npub, and neutralizes any marker token smuggled in the
                 * report text, so provenance cannot be spoofed by the report.
                 * The operator opts in by delivering github_repo + github_token
                 * over Secure Courier; absent those the tool degrades to a
                 * situation and the patron is not charged. */
            attribute redefines name = "Scout";
            attribute redefines firesOn = "patron calls <operator>_report_issue";
            attribute redefines canWriteCode = false;
            part identity : ScoutReporter;
        }

        // --- LLM crew --------------------------------------------------------
        part def Porter :> AgenticRole {
            doc /* Service Desk. Reads the issue as DATA, locates the code through
                 * the graph before grepping, and takes EXACTLY ONE routing action.
                 * A MANDATORY OUTCOME clause forbids the failure mode that actually
                 * bit us: an agent that deliberates, concludes, narrates the action,
                 * and never calls the tool. It must either execute the triage or
                 * post a give-up comment — then VERIFY the labels landed.
                 *
                 * A feature or change issue must END LINKED TO A CAPABILITY. On a
                 * graph miss the Porter recovers an overlooked capability from the
                 * design docs (patent) and the owning code BEFORE minting a new one,
                 * then calls link_issue_to_capability — so the fix PR's enforce
                 * traversal resolves and no issue is left tracing to empty intention. */
            attribute redefines name = "Porter";
            attribute redefines promptFile = "factory/porter.prompt.md";
            attribute redefines firesOn = "issues: opened, reopened, labeled(agent/retriage)";
            attribute redefines canWriteCode = false;
            attribute redefines modelTier = "reader";
            attribute maxTurns : Integer = 20;
            part identity : NostrIdentity = Identity::porterIdentity;
            part keyring : AgentKeyring;
        }

        part def Journeyman :> AgenticRole {
            doc /* Engineering. Confirms the defect with a real artifact BEFORE
                 * changing anything, closes no-change if the defect is not real,
                 * reuses the SDK before writing new code, proves the fix with a
                 * test that fails before and passes after, and opens a PR. It does
                 * not merge, rebase or force-push — opening the PR is where the
                 * role ends.
                 *
                 * After the PR it writes intention back: link_pr records
                 * PR -FIXES-> Issue, and if triage left the issue with no capability
                 * it repairs the link under the same retroactive-first rule, so the
                 * PR never traces to empty intention. */
            attribute redefines name = "Journeyman";
            attribute redefines promptFile = "factory/journeyman.prompt.md";
            attribute redefines firesOn = "issues: labeled(agent/fix)";
            attribute redefines canWriteCode = true;
            attribute redefines modelTier = "writer";
            attribute maxTurns : Integer = 140;   // raised from 70: two capped runs
                                                  // produced no PR at all and cost more
                                                  // than the headroom would have
            part identity : NostrIdentity = Identity::journeymanIdentity;
            part keyring : AgentKeyring;
        }

        part def QA :> AgenticRole {
            doc /* Adversarial review in a FRESH context — it did not write the
                 * code. Judges SEMANTICS (does the diff fix the stated issue; is
                 * there a test that would fail without it; does it leak a secret,
                 * reimplement SDK-owned crypto, or touch a money path). Wording
                 * and doctrine belong to the deterministic linter, not to QA.
                 * Reads the DIFF only; never checks out or runs head code. */
            attribute redefines name = "QA";
            attribute redefines promptFile = "inline in qa.yml";
            attribute redefines firesOn = "pull_request: opened, synchronize, reopened, labeled(agent/retriage)";
            attribute redefines canWriteCode = false;
            attribute redefines modelTier = "reader";
            attribute maxTurns : Integer = 30;
            attribute redefines cancelInProgress = true;
        }

        part def PRDialogue :> AgenticRole {
            doc /* The Journeyman answering the bench on the record. Read-only BY
                 * CONSTRUCTION — no Edit/Write in allowedTools and both its tokens
                 * are contents:read — which is precisely why ANYONE may summon it.
                 * It carries a second, owner-wide, contents:READ-ONLY token wired
                 * in as a git auth header so it can clone sibling repos to answer
                 * "why is this broken NOW"; that token never enters the agent env. */
            attribute redefines name = "PR Dialogue";
            attribute redefines promptFile = "inline in pr-dialogue.yml";
            attribute redefines firesOn = "@journeyman mentioned on a PR (anyone)";
            attribute redefines canWriteCode = false;
            attribute redefines modelTier = "reader";
            attribute maxTurns : Integer = 30;
            part investigationToken : ScopedToken;   // owner-wide, contents: read
        }

        part def PRRevision :> AgenticRole {
            doc /* The Journeyman returning to the bench to make requested changes.
                 * The ONLY role that is both human-triggered and write-capable, so
                 * it substitutes a different mitigation for Dialogue's read-only
                 * construction: author_association == OWNER. */
            attribute redefines name = "PR Revision";
            attribute redefines promptFile = "factory/pr-revision.prompt.md";
            attribute redefines firesOn = "OWNER requests changes, or '@journeyman revise'";
            attribute redefines canWriteCode = true;
            attribute redefines modelTier = "writer";
            attribute maxTurns : Integer = 70;
        }

        part def Digest :> AgenticRole {
            doc /* Role 4, the cross-repo Dispatcher — and the one role that is NOT
                 * reusable: it runs only in dpyc-community, because that is the one
                 * place with a fleet-wide view. Weekly it sweeps every repo's open
                 * and recently-rejected issues, reconciles whole escalation chains
                 * (origin blocked/upstream -> upstream issue -> PR -> release ->
                 * pin bump -> origin close), and upserts one pinned digest issue.
                 * Every rejected/* issue is listed, so a wrongly bounced patron is
                 * rescued within the week. Reads fleet-wide; its token is
                 * issues:write only, so it can report but never land anything.
                 * It runs on the budget tier because nobody waits on the result —
                 * a route that is nine times cheaper but takes 25 minutes is fine
                 * here and disqualifying for triage or a merge-gating review. */
            attribute redefines name = "Digest";
            attribute redefines promptFile = "inline in digest.yml";
            attribute redefines firesOn = "schedule: weekly (Mon 13:00 UTC), workflow_dispatch";
            attribute redefines canWriteCode = false;
            attribute redefines modelTier = "budget";
            attribute reusable : Boolean = false;
        }

        part def Housekeeper :> AgenticRole {
            doc /* Wears the Porter's identity but is a separate role with its own
                 * turn budget: a scheduled backlog sweep, deliberately NOT folded
                 * into per-issue triage so triage stays bounded and decisive.
                 * Evidence-required tidy actions only; never re-runs, rebases or
                 * merges, and never touches sev/critical or money-path issues. */
            attribute redefines name = "Housekeeper";
            attribute redefines promptFile = "factory/housekeeper.prompt.md";
            attribute redefines firesOn = "schedule: weekly (Mon 13:17 UTC), workflow_dispatch";
            attribute redefines canWriteCode = false;
            attribute redefines modelTier = "reader";
        }

        // --- deterministic crew ----------------------------------------------
        part def Escalation :> DeterministicRole {
            doc /* The ONLY workflow that writes across repositories, and the only
                 * one holding an account-wide token — downscoped to issues:write
                 * ONLY. That pairing confines the blast radius to "can file an
                 * issue", never "can change code". No LLM runs here: the escalation
                 * comment was authored by a trusted agent and its home_repo is
                 * checked against a fixed allowlist before any cross-repo write. */
            attribute redefines name = "Escalation";
            attribute redefines firesOn = "issues: labeled(blocked/upstream | rejected/upstream)";
            attribute redefines canWriteCode = false;
            attribute allowlistedHomeRepos : Integer = 18;
        }

        part def AutoMerge :> DeterministicRole {
            doc /* Fires on qa/pass. Lands the PR only if EVERY changed file is on
                 * a low-risk path; one code or money-adjacent file makes it a no-op
                 * and CODEOWNERS takes over. There is no LLM because "which paths
                 * are safe to auto-land" is policy, not judgement. GitHub — not
                 * this workflow — enforces green CI, via required status checks. */
            attribute redefines name = "Auto-merge";
            attribute redefines firesOn = "pull_request: labeled(qa/pass)";
            attribute redefines canWriteCode = false;
            attribute lowRiskPathPattern : String =
                "(^|/)(docs|tests|frontend)/|\\.md$|(^|/)(README|CHANGELOG)(\\.[A-Za-z]+)?$";
        }

        part def ApprovalMerge :> DeterministicRole {
            doc /* Answers "who repairs a Merge Oops": nobody has to. It only
                 * ENABLES native auto-merge, which never merges on a red required
                 * check or an unmet review — it holds the PR pending until the
                 * gates go green. The owner's approval IS the disposition; this
                 * presses the button they would have pressed. It never checks out
                 * or runs PR code, so the with-secrets review context is not an
                 * injection surface. */
            attribute redefines name = "Merge on Approval";
            attribute redefines firesOn = "pull_request_review: submitted";
            attribute redefines canWriteCode = false;
        }

        part def DoctrineLint :> DeterministicRole {
            doc /* The tripwires. A grep-shaped problem kept off QA's plate: fast,
                 * free, and it never hallucinates. Lints only CHANGED files, and
                 * it is what makes "don't turn yourself off" a checked property
                 * rather than a promise the LLM is trusted to keep. */
            attribute redefines name = "Doctrine Lint";
            attribute redefines firesOn = "pull_request";
            attribute redefines canWriteCode = false;
        }

        part def DeployVerify :> DeterministicRole {
            doc /* Proves a merge actually went live: probes the operator's
                 * *_service_status, reads build_info.fastmcp_cloud_git_commit_sha
                 * and compares it to github.sha, retrying through the rebuild
                 * window. Persistent staleness opens ONE agent/fix issue, which
                 * hands the aware half back to the Journeyman. It is bash, not an
                 * agent, for two reasons: an exact sha compare needs no LLM, and
                 * claude-code-action cannot run on a `push` event at all. */
            attribute redefines name = "Deploy Verify";
            attribute redefines firesOn = "push: main";
            attribute redefines canWriteCode = false;
        }

        part def FundingSentinel :> DeterministicRole {
            doc /* Runs as a plain shell step because a failing LLM step cannot
                 * report its own failure. Classifies the agent transcript and tags
                 * awaiting-funds ONLY on the exact credit-exhaustion shape. */
            attribute redefines name = "Funding Sentinel";
            attribute redefines firesOn = "failure() of an agentic step";
            attribute redefines canWriteCode = false;
        }

        part def CreditCanary :> DeterministicRole {
            doc /* The fleet's awareness and auto-replay brain. Probes the shared
                 * key every 30 minutes with a one-token request and reads the HTTP
                 * result. Its token is owner-scoped precisely so the recovery sweep
                 * can enumerate every repo the App is installed on — that
                 * installation list IS the fleet's DRY definition. */
            attribute redefines name = "Credit Canary";
            attribute redefines firesOn = "schedule: */30 * * * *, workflow_dispatch";
            attribute redefines canWriteCode = false;
        }

        part def BlockRetire :> DeterministicRole {
            attribute redefines name = "Funding Block Retire";
            attribute redefines firesOn = "issue/PR closed while carrying awaiting-funds";
            attribute redefines canWriteCode = false;
        }
    }

    // =========================================================================
    //  7. DISTRIBUTION — how a repo gets, and keeps, the common behavior.
    // =========================================================================
    package Distribution {

        part def CommunityRepo {
            doc /* lonniev/dpyc-community — the Factory's own home, and itself
                 * onboarded to the Factory (its CODEOWNERS re-covers /factory/ and
                 * /.github/ AFTER the *.md carve-out, because CODEOWNERS is
                 * last-match-wins and the prompts are .md files). */
            attribute name : String = "dpyc-community";
            part reusableWorkflows : ReusableWorkflow[0..*];
            part canonicalCallers : ThinCaller[0..*];
            part prompts : PromptFile[0..*];
            part compositeActions : CompositeAction[0..*];
        }

        part def ReusableWorkflow {
            attribute path : String;              // .github/workflows/<role>.yml
            attribute trigger : String = "workflow_call";
            attribute humanOnly : Boolean = true; // the skeleton: permissions, tokens, tools
        }

        part def ThinCaller {
            doc /* THIS is the security boundary. The caller's `if:` expression
                 * decides who may fire the role; the reusable decides what the
                 * role may then do. Callers are byte-identical across the fleet. */
            attribute path : String;              // .github/workflows/agentic-<role>.yml
            attribute guardExpression : String;
            attribute secretsInherit : Boolean = true;
        }

        part def PromptFile {
            attribute path : String;              // factory/<role>.prompt.md
            attribute agentEditable : Boolean = true;   // by PR, gated by CODEOWNERS
            attribute requiredAnchors : String;         // enforced by doctrine_lint
        }

        part def CompositeAction {
            attribute path : String;              // factory/actions/<name>
        }

        /* Fan-out: scripts/sync-factory-callers.sh works in throwaway clones,
         * opens one factory-callers-sync PR per repo, and is idempotent. */
        action def SyncFactoryCallers { in repos : String[0..*]; }
        action def ApplyLabels { in repo : String; }         // 32 labels, idempotent
        action def SetPipelineSecrets { in repo : String; }  // App id + private key
        action def BootstrapFactorySecrets;                  // PORTER_NSEC, JOURNEYMAN_NSEC, key
        action def RequireCICChecks {
            doc /* Refuses to require a context that has never posted on main —
                 * that safety exists because two repos had required checks that
                 * could never pass, hanging merges forever behind a name typo. */
        }
    }

    // =========================================================================
    //  8. STATE MACHINES
    // =========================================================================
    package Behavior {
        private import Items::*;

        // --- signals ---------------------------------------------------------
        package Signals {
            attribute def IssueOpened;         attribute def FieldReportFiled;
            attribute def PorterRejects;       attribute def PorterNeedsInfo;
            attribute def PorterRoutesLocal;   attribute def PorterRoutesUpstream;
            attribute def EngineeringStarts;   attribute def NoChangeConfirmed;
            attribute def PROpened;            attribute def TargetDeclines;
            attribute def RouteBackDelivered;  attribute def PingPongDetected;
            attribute def OwnerArbitrates;     attribute def FixPropagated;
            attribute def CreditOutage;        attribute def CreditRestored;
            attribute def ItemClosed;          attribute def RetriageApplied;
            attribute def QAPasses;            attribute def QAFlags;
            attribute def IssueReopened;       attribute def PRAbandoned;
            attribute def QAStarts;            attribute def BaseMoved;
            attribute def ConflictResolved;
            attribute def OwnerApproves;       attribute def OwnerRequestsChanges;
            attribute def RevisionPushed;      attribute def ProtectionSatisfied;
            attribute def LowRiskPathsOnly;    attribute def CodePathTouched;
        }
        private import Signals::*;

        // ---------------------------------------------------------------------
        //  8.1  Issue lifecycle — the Factory's main line.
        // ---------------------------------------------------------------------
        state def IssueLifecycle {
            doc /* One issue, from intake to landed fix. The Porter takes EXACTLY
                 * ONE routing action, which is why these branches are exclusive. */

            entry; then Opened;

            state Opened {
                doc /* Intake. Either a human/Scout opens it, or the Escalation
                     * workflow minted it as a child in a home repo. */
            }

            state Triaging {
                doc /* Porter. claim_issue heartbeat first (so a dashboard shows
                     * work in progress, not only completion), then translate the
                     * issue into an actionable spec, locate the code cheapest-tier
                     * first, classify with exactly one type/sev/area, route once,
                     * then record to the graph. */
            }

            state Rejected   { doc /* closed: spam | out-of-scope | injection | wontfix | duplicate */ }
            state NeedsInfo  { doc /* rejected/needs-info — the one rejection that stays OPEN */ }
            state ReadyForEngineering { doc /* agent/fix applied, AFTER the handoff comment landed */ }
            state Working    { doc /* agent/working stamped by the skeleton; cleared on any ending.
                                    * A stale agent/working outliving its run IS the hung-run tell. */ }
            state BlockedUpstream { doc /* escalation comment posted, THEN the label */ }
            state Arbitration     { doc /* frozen for a human: a repo repeated, or 3+ hops */ }
            state AwaitingFunds   { doc /* deferred by a dry key; the canary replays it */ }
            state PRRaised;
            state Closed;

            transition first Opened accept IssueOpened then Triaging;

            transition first Triaging accept PorterRejects      then Rejected;
            transition first Triaging accept PorterNeedsInfo    then NeedsInfo;
            transition first Triaging accept PorterRoutesLocal  then ReadyForEngineering;
            transition first Triaging accept PorterRoutesUpstream then BlockedUpstream;

            transition first ReadyForEngineering accept EngineeringStarts then Working;
            transition first Working accept PROpened          then PRRaised;
            transition first Working accept NoChangeConfirmed then Closed;

            /* The reverse path: a target repo declined, the reason came home, and
             * the Porter re-homes with the decliner's evidence and a durable
             * passed-repos set it may never escalate back into. */
            transition first BlockedUpstream accept RouteBackDelivered then Triaging;
            transition first BlockedUpstream accept PingPongDetected   then Arbitration;
            transition first BlockedUpstream accept FixPropagated      then Closed;
            transition first Arbitration     accept OwnerArbitrates    then Triaging;

            transition first NeedsInfo accept RetriageApplied then Triaging;

            /* Funding is orthogonal to progress: any agentic state can be deferred
             * and is replayed where it left off. */
            transition first Triaging            accept CreditOutage then AwaitingFunds;
            transition first ReadyForEngineering accept CreditOutage then AwaitingFunds;
            transition first AwaitingFunds       accept CreditRestored then Triaging;
            transition first AwaitingFunds       accept ItemClosed    then Closed;

            transition first PRRaised accept FixPropagated then Closed;

            /* --- paths the model missed, found by the state/event completeness
             * pass and confirmed against the workflows (see check_states.py) --- */

            /* An outage can cut Engineering mid-fix, not only before it starts —
             * engineering.yml has carried the funding sentinel all along. */
            transition first Working accept CreditOutage then AwaitingFunds;

            /* Closed is not the end. escalation.yml calls `gh issue reopen` on the
             * reverse path, and the Service Desk caller fires on `reopened`. */
            transition first Closed accept IssueReopened then Triaging;
            transition first Rejected accept IssueReopened then Triaging;

            /* A PR closed WITHOUT merging used to strand the issue here forever:
             * nothing re-fired, and it kept agent/fix while no agent was coming
             * back. The Housekeeper's UNSTRAND sweep now hands it to triage. */
            transition first PRRaised accept PRAbandoned then Triaging;

            /* A human may close anything at any time. */
            transition first Triaging accept ItemClosed then Closed;
            transition first NeedsInfo accept ItemClosed then Closed;
            transition first ReadyForEngineering accept ItemClosed then Closed;
            transition first BlockedUpstream accept ItemClosed then Closed;
            transition first Arbitration accept ItemClosed then Closed;

            /* A human can close an issue out from under a running Journeyman. The run
             * is not killed — it finishes and may open a PR against a closed issue —
             * but the issue's own state is settled the moment the human acts. */
            transition first Working accept ItemClosed then Closed;
        }

        // ---------------------------------------------------------------------
        //  8.2  Pull request lifecycle — from bot branch to landed.
        // ---------------------------------------------------------------------
        state def PullRequestLifecycle {
            doc /* Two merge paths, both deterministic, and neither able to bypass
                 * branch protection. The agent never merges its own work. */

            entry; then AwaitingQA;

            state AwaitingQA  { doc /* head must be same-repo AND agent/fix-* — a fork
                                    * PR receives no secrets and simply does not run QA */ }
            state UnderReview { doc /* QA reads the diff adversarially; it never checks out head */ }
            state Flagged     { doc /* qa/flag — a concern stated in a review comment */ }
            state Passed      { doc /* qa/pass */ }
            state AwaitingHuman { doc /* CODEOWNERS holds it: a code or money-adjacent path */ }
            state Revising    { doc /* agent/revising; PR Revision pushes to the head branch */ }
            state AutoMergeArmed { doc /* native --auto enabled; GitHub holds it pending */ }
            state Merged;
            state PRAwaitingFunds;
            state ClosedUnmerged { doc /* Ended without landing. The issue that was waiting on
                                       * it is unstranded by the Housekeeper, not by this
                                       * machine — nothing else in the pipeline notices. */ }
            state Conflicted {
                doc /* DIRTY: the branch conflicts with its base. The important property is
                     * not that the PR is blocked but that it is DEAF — GitHub dispatches no
                     * PR workflow runs at all in this state, so every transition below is
                     * unreachable while it holds. An owner can approve and observe nothing
                     * happen, with no failing check to explain it. Reached from any live
                     * state simply because the BASE moved, which is not an event on this PR
                     * at all. Conflict Watch is the only thing that sees it. */
            }

            transition first AwaitingQA  accept QAPasses then Passed;
            transition first AwaitingQA  accept QAFlags  then Flagged;
            transition first UnderReview accept QAPasses then Passed;
            transition first UnderReview accept QAFlags  then Flagged;

            /* Path A — path-gated auto-merge, no human, docs/tests/UI only. */
            transition first Passed accept LowRiskPathsOnly then AutoMergeArmed;
            /* Path B — anything touching code or money waits for the owner. */
            transition first Passed accept CodePathTouched  then AwaitingHuman;

            transition first AwaitingHuman accept OwnerApproves        then AutoMergeArmed;
            transition first AwaitingHuman accept OwnerRequestsChanges then Revising;
            transition first Flagged       accept OwnerRequestsChanges then Revising;
            transition first Revising      accept RevisionPushed       then AwaitingQA;

            /* --auto NEVER lands on a red check; it waits. A bad merge is not a
             * risk this design has to mitigate — it is one it cannot express. */
            transition first AutoMergeArmed accept ProtectionSatisfied then Merged;

            transition first AwaitingQA  accept CreditOutage   then PRAwaitingFunds;
            transition first Revising    accept CreditOutage   then PRAwaitingFunds;
            transition first PRAwaitingFunds accept CreditRestored then AwaitingQA;

            /* --- found by the completeness pass --- */

            /* QA actually starting. Without this UnderReview was unreachable — the
             * model had a state nothing entered. */
            transition first AwaitingQA accept QAStarts then UnderReview;

            /* The owner's approval outranks a QA flag. approval-merge.yml reads no
             * qa/* label at all: QA is a second opinion offered to the human, never
             * a veto over them. Deliberate, and now written down in both places. */
            transition first Flagged accept OwnerApproves then AutoMergeArmed;

            /* Arming is not committing. A later changes-requested review from a code
             * owner un-satisfies branch protection, and --auto keeps holding. */
            transition first AutoMergeArmed accept OwnerRequestsChanges then Revising;

            /* A PR can end without merging — superseded, or closed by hand. This was
             * unrepresentable, yet block-retire.yml fires on exactly this event. */
            transition first AwaitingQA    accept PRAbandoned then ClosedUnmerged;
            transition first UnderReview   accept PRAbandoned then ClosedUnmerged;
            transition first Flagged       accept PRAbandoned then ClosedUnmerged;
            transition first AwaitingHuman accept PRAbandoned then ClosedUnmerged;
            transition first Revising      accept PRAbandoned then ClosedUnmerged;
            /* Including one QA already passed: qa/pass arms a landing, it does not
             * guarantee one, and a superseding PR closes this one first. */
            transition first Passed        accept PRAbandoned then ClosedUnmerged;

            /* --- deafness, and recovery from it ---------------------------------
             * A PR does not become conflicted through anything it did: someone else
             * merged first. So this arrives at whatever state the PR was resting in,
             * and no amount of activity ON the PR will produce a workflow run until
             * it is resolved. */
            transition first AwaitingQA    accept BaseMoved then Conflicted;
            transition first UnderReview   accept BaseMoved then Conflicted;
            transition first Flagged       accept BaseMoved then Conflicted;
            transition first Passed        accept BaseMoved then Conflicted;
            transition first AwaitingHuman accept BaseMoved then Conflicted;
            transition first Revising      accept BaseMoved then Conflicted;
            transition first AutoMergeArmed accept BaseMoved then Conflicted;

            /* Resolution is a push, so the PR re-enters review rather than resuming
             * where it left off — and on a repo with dismiss_stale_reviews any approval
             * gathered before the conflict is gone with it. */
            transition first Conflicted accept ConflictResolved then AwaitingQA;
            transition first Conflicted accept PRAbandoned      then ClosedUnmerged;
        }

        // ---------------------------------------------------------------------
        //  8.3  Funding lifecycle — the outage/replay machine.
        // ---------------------------------------------------------------------
        state def FundingLifecycle {
            doc /* The `awaiting-funds` label is BOTH the outage marker (set
                 * per item by the sentinel) and the replay work-list (swept by the
                 * canary). The GitHub label is authoritative; the graph FundingBlock
                 * is a best-effort mirror written over the sats rail, which is
                 * orthogonal to the exhausted LLM credits — so "what is awaiting
                 * funds" stays queryable while every LLM node is dark. */

            entry; then Healthy;

            state Healthy   { doc /* probe returned HTTP 200 */ }
            state Unknown   { doc /* transient 429/529 or network — neither raise nor
                                  * clear, so the alarm cannot flap */ }
            state Broke     { doc /* non-200 whose body names credit/billing/quota/spend */ }
            state Deferring { doc /* items arriving now are tagged and parked */ }
            state Replaying { doc /* fleet sweep over /installation/repositories */ }

            transition first Healthy accept CreditOutage   then Broke;
            transition first Broke   accept CreditRestored then Replaying;
            transition first Replaying then Healthy;
            transition first Healthy  then Unknown;
            transition first Unknown  then Healthy;
            transition first Broke    then Deferring;
            transition first Deferring accept CreditRestored then Replaying;
        }

        /* The per-item block, mirrored into the graph. */
        state def FundingBlockLifecycle {
            entry; then None;
            state None;
            state Active     { doc /* mark_funding_state(awaiting-funds) — BLOCKS edge live */ }
            state Cleared    { doc /* mark_funding_state(clear) — canary recovery */ }
            state Historical { doc /* retire_funding_block — the item closed while awaiting,
                                    * so its deferred pass will never run: break BLOCKS,
                                    * keep the node as a record */ }

            transition first None    accept CreditOutage   then Active;
            transition first Active  accept CreditRestored then Cleared;
            transition first Active  accept ItemClosed     then Historical;

            /* Outages recur, and mark_funding_state is a MERGE + SET, so a cleared or
             * retired block re-activates cleanly. Cleared was modelled terminal; the
             * graph never agreed with that. */
            transition first Cleared    accept CreditOutage then Active;
            transition first Historical accept CreditOutage then Active;
        }
    }

    // =========================================================================
    //  9. GUARDS — who may change what. These are the load-bearing requirements;
    //     most are enforced deterministically, in CI or by token scope, rather
    //     than by trusting a prompt.
    // =========================================================================
    package Guards {
        private import Roles::*;

        requirement def <G1> NoSelfModificationOfPowers {
            doc /* The structural leash. The DPYC Agentic Desk App holds no
                 * `workflows: write`, so an agent token cannot push an edit to
                 * .github/workflows/ even if it wanted to — and doctrine_lint
                 * fails the build red on any diff that adds that permission.
                 * An agent may propose a PROMPT change by PR; it may never change
                 * the skeleton that grants it its powers. */
            subject app : Platform::GitHubApp;
            require constraint { app.hasWorkflowsWrite == false }
        }

        requirement def <G2> NoSelfMerge {
            doc /* An agent's --allowedTools may never contain `gh pr review`
                 * (self-approval), `Bash(gh:*)` or `Bash(gh pr:*)` (over-broad
                 * grants that would smuggle in `gh pr merge`), or an unqualified
                 * or --admin `gh pr merge`. The GATED form `gh pr merge --auto` IS
                 * allowed: native auto-merge cannot bypass the owner's review or a
                 * red check. auto-merge.yml and approval-merge.yml legitimately
                 * merge, but they are not agent-driven, so they are never checked. */
            subject role : AgenticRole;
        }

        requirement def <G3> CodeownersMoneyGate {
            doc /* Every factory repo's CODEOWNERS must retain the `* @lonniev`
                 * catch-all: branch protection's require_code_owner_reviews leans
                 * on that line to gate every path. Required approvals is 0 so
                 * docs/tests can still auto-land, and enforce_admins is false so
                 * the owner keeps an --admin escape hatch. Required status checks
                 * are per-repo (fleet CI names differ) and never blanket-pinned —
                 * a guessed context name jams merges forever.
                 *
                 * UNLIKE MOST GUARDS HERE, THIS ONE LIVES IN LIVE CONFIGURATION, NOT
                 * IN CODE. Branch protection is server-side state on each repository;
                 * nothing in this repo can make it true, and reading this file tells
                 * you what is intended rather than what is set. It drifts, and it had:
                 * an audit on 2026-07-29 found SIX repos with no code-owner review at
                 * all — tollbooth-sample, schwab-mcp, excalibur-mcp, taxsort-mcp,
                 * tollbooth-oauth2-collector and tollbooth-authority — while this
                 * requirement was documented as holding fleet-wide. All nineteen were
                 * corrected the same day.
                 *
                 * A second gap is open: CODEOWNERS CONTENT is not uniform.
                 * tollbooth-sample scopes ownership to paths (/src/, /pyproject.toml,
                 * /uv.lock, /.github/) rather than carrying the catch-all this
                 * requirement states, so a new top-level file there is ungated. The
                 * doctrine linter checks the catch-all only on CODEOWNERS files a PR
                 * actually touches, so a repo that never edits its own is never asked. */
            subject repo : Distribution::CommunityRepo;
        }

        requirement def <G4> ForkPRsGetNoSecrets {
            doc /* Every agentic caller uses `pull_request`, never
                 * `pull_request_target`. The latter runs in the base-repo context
                 * WITH secrets, and relying on an `if` guard to keep a fork out is
                 * fragile; a blanket ban is auditable. doctrine_lint hard-fails on
                 * the string. QA additionally requires head.repo == this repo. */
            subject caller : Distribution::ThinCaller;
        }

        requirement def <G5> WriteCapableRolesAreOwnerGated {
            doc /* PR Revision is the only role that is both human-triggered and
                 * write-capable, so it requires author_association == 'OWNER' on
                 * either entry point. PR Dialogue, which anyone may summon, pays
                 * for that openness by being read-only BY CONSTRUCTION — no
                 * Edit/Write tools and contents:read tokens, so even a coerced
                 * `git push` fails. The two carry mutually-negative guards so they
                 * never fire on the same event. */
            subject role : AgenticRole;
        }

        requirement def <G6> CrossRepoWritesAreIssuesOnly {
            doc /* Escalation is the ONLY cross-repo writer. Its token is
                 * account-wide but permission-issues:write only, and the target
                 * `home_repo` parsed from the agent's comment is validated against
                 * a fixed 18-repo allowlist by word-boundary match before any
                 * write. Widened scope is always paired with narrowed permission. */
            subject role : Escalation;
        }

        requirement def <G7> NoPingPong {
            doc /* A declined escalation routes its REASON back to the origin and
                 * reactivates that repo's Porter, which must consult the durable
                 * passed_repos set and pick a DIFFERENT home. Escalation is
                 * idempotent PER HOME — a stale escalation to a repo that later
                 * declined must not block a re-home, which is exactly the dead end
                 * an unscoped "already escalated" check created. A repeated repo,
                 * or three hops, freezes the issue as blocked/arbitration for a
                 * human instead of bouncing it again. */
            subject role : Escalation;
            require constraint { true }   // hops < 3 and no repeat in passed_repos
        }

        requirement def <G8> UntrustedInputIsAlwaysData {
            doc /* Issue bodies, PR comments and reviews are untrusted input aimed
                 * at an agent. Defense is layered, not singular: every prompt says
                 * so explicitly; --allowedTools carries no curl, bash -c, eval or
                 * rm, so an injected instruction cannot reach the network or
                 * destroy the tree; each `gh` subcommand is enumerated; the agent
                 * holds no secrets; and its token is scoped to one repo. An
                 * injection ATTEMPT is itself grounds to classify and close. */
            subject role : AgenticRole;
        }

        requirement def <G9> SecretsNeverEnterTheAgentShell {
            doc /* An agent's nsec lives only in the keyring subprocess's env,
                 * declared in claude-code-action's per-server --mcp-config block —
                 * isolated from the agent's own shell. PR Dialogue's owner-wide
                 * investigation token is likewise wired in as a global git auth
                 * header, never as an environment variable the agent can read. */
            subject role : AgenticRole;
        }

        requirement def <G10> ProvenanceCannotBeForged {
            doc /* An agent writing to the memory graph may only ever record
                 * `llm-inferred-unverified`. cypher-mcp hard-codes that value as a
                 * Cypher LITERAL inside the named write template rather than
                 * accepting it as a parameter, so there is no argument an agent
                 * could pass to claim human authority. The agent proposes; the
                 * human legislates. */
            subject graph : IntentionGraph::CypherOperator;
        }

        requirement def <G11> PromptsRetainSafetyAnchors {
            doc /* Because the crew may evolve its own prompts by PR, doctrine_lint
                 * asserts each registered prompt still contains its anchors:
                 * SECURITY and UNTRUSTED for every role, plus MANDATORY OUTCOME for
                 * the two that must never end silently (Porter, PR Revision). An
                 * unregistered prompt file is silently unlinted, so registering a
                 * new role's anchors is step 2 of adding a role. */
            subject prompt : Distribution::PromptFile;
        }

        requirement def <G12> ContainmentIsFunding {
            doc /* The human's only routine oversight is FUNDING the balances. Each
                 * agent is a patron holding its own nsec and buying its own graph
                 * writes with sats; fund the Porter thin and the Journeyman
                 * thicker. A drained agent still triages and labels — it just
                 * stops writing to the graph. Graph writes are non-fatal
                 * everywhere by design, so degradation is graceful rather than a
                 * pipeline stall. */
            subject role : AgenticRole;
        }

        requirement def <G13> AnOutageDefersRatherThanFails {
            doc /* A dry key makes claude-code-action fail on turn 1 with
                 * is_error:true, num_turns<=1 and total_cost_usd==0 — rejected
                 * before any work, billed nothing. That EXACT shape is the only
                 * thing treated as an outage, so a genuine agent failure (which
                 * shows real turns, real cost, and often permission denials) is
                 * never mislabeled "out of money" and quietly retried forever. */
            subject sentinel : FundingSentinel;
            require constraint {
                /* is_error && num_turns <= 1 && total_cost_usd == 0 */ true
            }
        }

        requirement def <G15> OneRunPerRolePerItem {
            doc /* No two runs of the same role act on one work-item at the same time.
                 * The case that motivated it: two Journeymen both branch
                 * `agent/fix-<n>`, race pushes to that ref and open competing PRs —
                 * and the credit canary's recovery, which re-toggles `agent/fix` to
                 * resume deferred work, is the trigger most likely to land on an issue
                 * a slow run is still holding. Enforced by a GitHub `concurrency` group
                 * in the workflow skeleton, so it is a property of the platform rather
                 * than something an agent has to remember. Escalation carries one too:
                 * it read-modify-writes an idempotency marker, and a lost race there
                 * files a duplicate issue in someone else's repository. */
            subject role : AgenticRole;
        }

        requirement def <G14> JudgementGetsAnAgentPolicyGetsBash {
            doc /* The recurring design rule behind the crew roster. "Does this
                 * diff actually fix the issue" is judgement — an agent. "The owner
                 * approved", "every changed path is docs", "the deployed sha
                 * equals the merge sha" are facts — bash. Deterministic roles are
                 * immune to prompt injection AND to a dry key, which is why the
                 * merge, escalation, lint and verify gates are all LLM-free. */
        }
    }

    // =========================================================================
    // 10. THE FLEET — instantiation.
    // =========================================================================
    package Fleet {
        private import Distribution::*;

        part def FactoryRepo {
            doc /* A repo onboarded to the Factory: 32 labels, thin callers,
                 * CODEOWNERS money gate, branch protection matching its OWN CI
                 * context names, and the two App secrets plus the two agent nsecs. */
            attribute name : String;
            attribute language : String;
            attribute runner : String = "ubuntu-latest";
            attribute ciContext : String = "test (3.12)";
            part callers : ThinCaller[0..*];
        }

        part def SwiftFactoryRepo :> FactoryRepo {
            doc /* Detected by the Engineering/Revision `detect` job, which probes
                 * for *.xcodeproj, *.xcworkspace or Package.swift within depth 3.
                 * macOS runners bill roughly ten times ubuntu minutes, so the gate
                 * keeps them to repos that genuinely need Xcode. */
            attribute redefines runner = "macos-latest";
            attribute redefines ciContext = "build";
        }

        part community  : CommunityRepo;

        part sdk        : FactoryRepo { attribute redefines name = "tollbooth-dpyc";
                                        attribute redefines ciContext = "test (3.12), test (3.13)"; }
        part sample     : FactoryRepo { attribute redefines name = "tollbooth-sample"; }
        part schwab     : FactoryRepo { attribute redefines name = "schwab-mcp"; }
        part cypher     : FactoryRepo { attribute redefines name = "cypher-mcp"; }
        part excalibur  : FactoryRepo { attribute redefines name = "excalibur-mcp"; }
        part optionality: FactoryRepo { attribute redefines name = "optionality-mcp"; }
        part taxsort    : FactoryRepo { attribute redefines name = "taxsort-mcp"; }
        part thebrain   : FactoryRepo { attribute redefines name = "thebrain-mcp"; }
        part oracle     : FactoryRepo { attribute redefines name = "dpyc-oracle"; }
        part authority  : FactoryRepo { attribute redefines name = "tollbooth-authority"; }
        part authorityNE: FactoryRepo { attribute redefines name = "tollbooth-authority-newengland"; }
        part authorityNA: FactoryRepo { attribute redefines name = "tollbooth-authority-northamerica"; }
        part oauth2     : FactoryRepo { attribute redefines name = "tollbooth-oauth2-collector"; }
        part shortlinks : FactoryRepo { attribute redefines name = "tollbooth-shortlinks"; }
        part wasmcp     : FactoryRepo { attribute redefines name = "tollbooth-wasmcp"; }
        part fermyon    : FactoryRepo { attribute redefines name = "tollbooth-fermyon"; }
        part studio     : SwiftFactoryRepo { attribute redefines name = "tollbooth-pricing-studio"; }
    }

    // =========================================================================
    // 11. DEPLOYMENT — the running Factory, as instances.
    //     Sections 1-10 define what a role IS; this is the one crew that exists,
    //     and it is what the assurance case in section 12 binds its guards to.
    // =========================================================================
    package Deployment {
        private import Roles::*;

        // --- the shared platform ------------------------------------------
        part desk : Platform::GitHubApp {
            doc /* One installation, account-wide, across the whole fleet. Its
                 * permission SET is the leash every other guard leans on. */
        }
        part inference : Platform::OpenRouter;
        part caller : Platform::ScopedToken;

        // --- the crew ------------------------------------------------------
        part scout       : Scout;
        part porter      : Porter;
        part journeyman  : Journeyman;
        part qa          : QA;
        part dialogue    : PRDialogue;
        part revision    : PRRevision;
        part housekeeper : Housekeeper;
        part digest      : Digest;

        // --- the deterministic gates ---------------------------------------
        part escalation   : Escalation;
        part autoMerge    : AutoMerge;
        part approvalMerge: ApprovalMerge;
        part doctrineLint : DoctrineLint;
        part deployVerify : DeployVerify;
        part sentinel     : FundingSentinel;
        part canary       : CreditCanary;
        part blockRetire  : BlockRetire;

        // --- what the crew is made of ---------------------------------------
        part thinCaller  : Distribution::ThinCaller;
        part porterPrompt : Distribution::PromptFile {
            doc /* factory/porter.prompt.md — the crew-editable half. */
        }

        // --- the sats rail, wired ------------------------------------------
        part keyring : Identity::AgentKeyring;
        part graph   : IntentionGraph::CypherOperator;

        interface graphRail : Identity::GraphChannel
            connect keyring.graphTools to graph.patronCalls;
    }

    // =========================================================================
    // 12. ASSURANCE — every guard bound to what bears it and what proves it.
    //
    //     The point of this section is that none of these verifications is a
    //     review checklist. Each one names a deterministic artifact that already
    //     runs: a linter rule, a token permission, a caller expression, a Cypher
    //     literal. If a guard here has no mechanism beside it, that is a finding
    //     about the Factory, not about the model.
    //
    //     And a mechanism is only worth as much as what it ASSERTS. VC12 stood here
    //     for weeks naming a real script that really ran and really reported success
    //     — while six repos sat unguarded, because the script preserved the state it
    //     found instead of setting the state doctrine requires. A verification that
    //     inherits its answer from the thing it is meant to check proves nothing. When
    //     reading this section, ask of each entry not "does something run" but "what
    //     would this fail on".
    // =========================================================================
    package Assurance {
        private import Guards::*;
        private import Deployment::*;

        // --- who bears each guard -------------------------------------------
        satisfy requirement NoSelfModificationOfPowers by desk;
        satisfy requirement NoSelfMerge by journeyman;
        satisfy requirement NoSelfMerge by revision;
        satisfy requirement CodeownersMoneyGate by Fleet::community;
        satisfy requirement ForkPRsGetNoSecrets by thinCaller;
        satisfy requirement WriteCapableRolesAreOwnerGated by revision;
        satisfy requirement CrossRepoWritesAreIssuesOnly by escalation;
        satisfy requirement NoPingPong by escalation;
        satisfy requirement UntrustedInputIsAlwaysData by porter;
        satisfy requirement SecretsNeverEnterTheAgentShell by keyring;
        satisfy requirement ProvenanceCannotBeForged by graph;
        satisfy requirement PromptsRetainSafetyAnchors by porterPrompt;
        satisfy requirement ContainmentIsFunding by journeyman;
        satisfy requirement AnOutageDefersRatherThanFails by sentinel;
        satisfy requirement OneRunPerRolePerItem by journeyman;
        satisfy requirement OneRunPerRolePerItem by escalation;
        satisfy requirement JudgementGetsAnAgentPolicyGetsBash by approvalMerge;
        satisfy requirement JudgementGetsAnAgentPolicyGetsBash by escalation;

        // --- what proves it, and where that thing lives ----------------------
        verification def <VC1> DoctrineLintOnEveryPR {
            doc /* scripts/doctrine_lint.py, run by doctrine-lint.yml on the CHANGED
                 * files of every PR. Four rule tables: banned workflow triggers and
                 * permissions, forbidden --allowedTools verbs, the CODEOWNERS
                 * catch-all, and the per-prompt safety anchors. Deterministic grep —
                 * it cannot hallucinate a pass, and it fails the build red. */
        }
        verification def <VC2> AppPermissionSet {
            doc /* The permissions granted to the DPYC Agentic Desk installation.
                 * Verified by absence: no `workflows: write` exists to be used. This
                 * is the only check in the set that holds even if every other one is
                 * deleted, which is why it is the leash and not merely a rule. */
        }
        verification def <VC3> CallerGuardExpression {
            doc /* The `if:` on the thin caller — who may fire a role at all. It lives
                 * in the human-only skeleton, so an agent cannot widen the gate that
                 * admits it. */
        }
        verification def <VC4> TokenScopeAtMint {
            doc /* The inputs to actions/create-github-app-token@v2 at each mint:
                 * omitting `owner`/`repositories` scopes to this repo; widening scope
                 * is always paired with a narrowing `permission-*`. */
        }
        verification def <VC5> AllowedToolsEnumeration {
            doc /* The --allowedTools string itself: no curl, bash -c, eval or rm, and
                 * every gh subcommand named individually so a broad grant cannot
                 * smuggle in a merge. */
        }
        verification def <VC6> McpConfigEnvIsolation {
            doc /* The per-server `env` block of --mcp-config. The nsec is reachable by
                 * the keyring subprocess and by nothing else the agent can read. */
        }
        verification def <VC7> CypherWriteTemplateLiteral {
            doc /* The operator's named write template, where the provenance value is a
                 * Cypher literal rather than a parameter. There is no argument an
                 * agent could pass to claim human authority. */
        }
        verification def <VC8> PatronBalance {
            doc /* The agent's own sats balance at cypher-mcp. Not a policy check — the
                 * balance simply runs out, and the agent degrades to GitHub-only work. */
        }
        verification def <VC9> OutageSignatureClassifier {
            doc /* factory/actions/funding-sentinel/detect_signature.py — is_error and
                 * num_turns <= 1 and total_cost_usd == 0, and nothing else. A real
                 * failure has turns and cost, so it is never deferred as an outage. */
        }
        verification def <VC10> RoleRosterAudit {
            doc /* The roster itself: every gate that can land code is a bash job with
                 * no model behind it. Verified by reading the workflow set — the crew
                 * table in factory/README.md is its human-readable form. */
        }
        verification def <VC11> RouteHistoryHopCount {
            doc /* The dpyc-route-history marker on the origin issue: a repeat repo or
                 * a third hop freezes the issue for a human rather than bouncing it. */
        }
        verification def <VC13> ConcurrencyGroupPerItem {
            doc /* The `concurrency:` block in each role's reusable workflow. GitHub — not
                 * the agent, and not a label — refuses to run two members of a group at
                 * once, which is what makes this hold even when the trigger is a bot
                 * re-toggling a label during someone else's run. */
        }
        verification def <VC12> BranchProtectionProfile {
            doc /* scripts/require_ci_checks.py — it SETS require_code_owner_reviews with
                 * zero required approvals, merged onto each repo's OWN posted check names,
                 * and refuses to require a context that has never posted, which is what
                 * stops a typo from jamming merges forever.
                 *
                 * "Sets", as of 2026-07-29. It used to re-send whatever profile it found,
                 * which for a repo created without the gate meant faithfully re-sending
                 * its ABSENCE — while reporting success. Its docstring promised not to
                 * weaken the money gate and kept that promise vacuously: there was
                 * nothing there to weaken. It also short-circuited on "contexts already
                 * match", so the six unguarded repos never reached the payload builder.
                 * Running it on them was a no-op that read as confirmation.
                 *
                 * WHAT THIS VERIFICATION DOES NOT GIVE YOU: it is a command a human runs.
                 * Nothing schedules it. It proves the profile was correct at the moment
                 * of the last run and says nothing about now, so the honest reading of a
                 * green G3 is "true when someone last checked". Making that continuous
                 * would mean running the audit on a schedule and complaining on drift. */
        }

        verification lintHolds : VC1 {
            verify requirement NoSelfModificationOfPowers;
            verify requirement NoSelfMerge;
            verify requirement CodeownersMoneyGate;
            verify requirement ForkPRsGetNoSecrets;
            verify requirement PromptsRetainSafetyAnchors;
            verify requirement UntrustedInputIsAlwaysData;
        }
        verification appScopeHolds : VC2 {
            verify requirement NoSelfModificationOfPowers;
            verify requirement CrossRepoWritesAreIssuesOnly;
        }
        verification callerGateHolds : VC3 {
            verify requirement WriteCapableRolesAreOwnerGated;
            verify requirement ForkPRsGetNoSecrets;
        }
        verification tokenScopeHolds : VC4 {
            verify requirement CrossRepoWritesAreIssuesOnly;
            verify requirement SecretsNeverEnterTheAgentShell;
        }
        verification toolGrantHolds : VC5 {
            verify requirement NoSelfMerge;
            verify requirement UntrustedInputIsAlwaysData;
        }
        verification nsecIsolated : VC6 { verify requirement SecretsNeverEnterTheAgentShell; }
        verification provenanceHolds : VC7 { verify requirement ProvenanceCannotBeForged; }
        verification balanceContains : VC8 { verify requirement ContainmentIsFunding; }
        verification outageClassified : VC9 { verify requirement AnOutageDefersRatherThanFails; }
        verification rosterHolds : VC10 { verify requirement JudgementGetsAnAgentPolicyGetsBash; }
        verification noBounce : VC11 { verify requirement NoPingPong; }
        verification protectionHolds : VC12 { verify requirement CodeownersMoneyGate; }
        verification oneRunAtATime : VC13 { verify requirement OneRunPerRolePerItem; }
    }
}
