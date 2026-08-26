# Changelog

All notable changes to this project will be documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [1.4.0] — 2026-08-26

### Added — one identity for a code symbol, fleet-wide

- **Symbol naming convention** (`factory/README.md` → "Symbol names in the graph", stated
  inline in `porter`/`journeyman`/`pr-revision` prompts): a symbol is
  `<repo>:<what a developer of that language would write to import it>`, split on the first
  colon. Every symbol-bearing write resolves through `MERGE (sym:Symbol {fqn: $symbol_fqn})`,
  so `fqn` is a symbol's *only* identity and it is **not** scoped by repo — `index_symbol`'s
  `repo_name` buys an `IN_SERVICE` edge, which accumulates but cannot disambiguate. Two repos
  indexing `server.main` produced one node wearing two services; a fleet scaffolded from one
  template is exactly that population. Python/Swift/Rust carry no file path (`anchor_symbol`
  already records `file_path` + `verified_at_sha`, so location is deliberately not identity,
  and baking it in makes a file move orphan every `REALIZED_BY`/`GUARDS`/authored `why`);
  TypeScript keeps its path because in TS the path *is* the module identity.
- **`check_symbol_fqn`** in `scripts/intention_harvest.py` — raises on a malformed name where
  `connection_coverage` only nudges. The two describe different failures: a *missing* link is
  a partial graph (fine — link generously, never gate); a *malformed* fqn is a wrong graph, a
  junk node no query will ever find again. Every graph write MERGEs and none MATCHes, so
  nothing downstream can reject one — the harvester is the last place that can. Shape only;
  whether the repo exists and the symbol still does belong to a graph-wide audit.
- Porter's in-flight duplicate check keys on this string, so the convention is what keeps two
  spellings of one function from reading as two symbols and dispatching a duplicate fix.

### Added — PR Revision role + REUSE BEFORE BUILD

- **PR Revision** (`factory/pr-revision.prompt.md`, `.github/workflows/pr-revision.yml`,
  `scripts/factory-callers/agentic-pr-revision.yml`): the Journeyman returns to the bench
  and applies the owner's requested changes to a PR already under review. Previously there
  was no path from a review to a code change — `@journeyman` reached only the read-only PR
  Dialogue, and Engineering fired solely on `issues.labeled == agent/fix`, so the owner's
  only lever was re-labeling the issue and discarding the review. Revision checks out the
  PR's own head branch (no other role checks out head code), makes the change, re-runs the
  project's checks, and pushes onto that branch. It never force-pushes, rebases, merges, or
  submits a review.
- **Trust gate — the first human-triggered, write-capable role.** Dialogue is safe against
  an injected comment because it has no write tools and read-only tokens; Revision cannot
  keep that mitigation, so it substitutes `author_association == 'OWNER'` on the caller
  (the same association `approval-merge.yml` gates the merge on). Two owner-only entry
  points: a **Request changes** review, or a comment carrying `@journeyman revise`. A plain
  `@journeyman` still reaches the read-only Dialogue, which anyone may summon.
- **Dialogue yields**: `agentic-pr-dialogue.yml` gains negative guards
  (`!contains(…, '@journeyman revise')`, `review.state != 'changes_requested'`) so the two
  roles never fire on the same event.
- **Declines on an approved PR**: if a PR already carries an OWNER approval, Revision posts
  a comment and pushes nothing — auto-merge may be armed, and where branch protection lacks
  dismiss-stale-reviews a push could otherwise land code the owner never read.
- **QA re-verdict fix**: Revision strips `qa/pass`/`qa/flag` before pushing. QA re-reviews
  on `synchronize`, but re-applying a label it already carries emits no `labeled` event, so
  `auto-merge` would never re-arm and the PR would sit silently passed-but-unmerged.
- **Label**: `agent/revising`, cleared only on a *completed* revision — so it doubles as the
  stuck tell and as the credit canary's discriminator.
- **Canary**: a PR carrying `agent/revising` is no longer replayed as a QA re-review (which
  would re-review un-revised code and could stamp `qa/pass` on work the owner sent back).
  It clears the funding flag and asks the owner to re-request. Revision is deliberately NOT
  bot-re-fireable — letting the bot re-trigger a write-capable role would dissolve the very
  boundary the OWNER gate exists to hold.

### Added — REUSE BEFORE BUILD (Journeyman step 5)

- `factory/journeyman.prompt.md` gains a step between the upstream check and implementation.
  Step 4 asks *"does this fix belong in another repo?"*; step 5 asks the different question
  *"does this ability already exist in code I should be calling?"* — resolve via
  `cypher_which_service_handles` / `cypher_list_capabilities`, then grep the installed
  `tollbooth` package, and if new protocol/crypto/transport code is written anyway the PR
  body must name what was searched and why the wheel cannot carry it. Steps 5–10 renumbered
  to 6–11. Nothing previously told the agent to reuse before building; QA caught DRY
  violations only after the fact.

### Added — factory documentation

- `factory/README.md`: the crew table, the Dialogue-vs-Revision split, the trust model, and
  a step-by-step **adding a new role** procedure (prompt → doctrine-lint anchors → reusable
  skeleton → caller gate → canary discriminator → label → sync → document). None of this was
  written down before; role knowledge lived only in prompt files and shell-script headers.
- `scripts/doctrine_lint.py`: `pr-revision.prompt.md` registered in `FACTORY_PROMPT_ANCHORS`
  (`SECURITY`, `UNTRUSTED`, `MANDATORY OUTCOME`) — unregistered prompts are silently unlinted.

Rollout after merge: `apply_labels.sh` fleet-wide (the `agent/revising` label must exist
before the workflow can apply it), then `sync-factory-callers.sh` to propagate the new caller
and the Dialogue guards. The callers reference the reusable workflows `@main`, so this must
merge first. The same sync also repairs stale callers in `dpyc-oracle`,
`tollbooth-shortlinks`, and `tollbooth-wasmcp` (older model pins; missing `agent/retriage`
replay triggers; escalation missing `rejected/upstream`).

### Added — factory credit-outage awareness + auto-replay

- **Funding sentinel** (`factory/actions/funding-sentinel`): a deterministic (no-LLM)
  composite action wired into the Service Desk failure path. When a triage run fails
  with the credit-exhaustion signature (`is_error:true`, `num_turns<=1`,
  `total_cost_usd==0` — reached Anthropic, rejected before any work), it tags the issue
  `awaiting-funds` and leaves a one-time breadcrumb. A genuine agent error (turns burned,
  money spent) does **not** match, so real failures are never mislabeled.
- **Credit canary** (`.github/workflows/factory-credit-canary.yml`): scheduled every 30 min.
  Probes the shared `ANTHROPIC_API_KEY` with a 1-token request and reads the HTTP result —
  no agent involved (a failing LLM step can't report its own failure). BROKE → opens/keeps
  a `factory/outage` tracking issue. HEALTHY → closes the alarm and **replays**: sweeps every
  repo the factory App is installed on for open `awaiting-funds` issues and swaps the tag for
  `agent/retriage`, re-firing Porter. Nothing opened during an outage stays skipped.
- **Labels**: `awaiting-funds` (outage marker + replay work-list) and `agent/retriage`
  (replay trigger) added to the taxonomy in `apply_labels.sh`.
- **Service Desk caller** now also triggers on `issues.labeled`, guarded to `agent/retriage`
  so the canary can re-fire Porter without looping on Porter's own labels. The Porter prompt
  strips `agent/retriage` during triage.

Rollout after merge (see PR): `apply_labels.sh` fleet-wide (the new labels must exist before
the sentinel/canary can apply them), then `sync-factory-callers.sh` to propagate the caller
trigger.

### Added — extend the sentinel to the whole team (Engineering + QA)

- The funding sentinel now also guards the **Engineering** (`engineering.yml`) and **QA**
  (`qa.yml`) failure paths, so those nodes defer-and-replay instead of failing silently when
  the key is capped. Engineering tags its `agent/fix` issue; QA tags its PR.
- The **canary recovery replay** now routes each deferred item to the node that was skipped:
  an `awaiting-funds` issue *without* `agent/fix` → re-fire Porter (add `agent/retriage`);
  *with* `agent/fix` → re-fire Engineering (re-toggle `agent/fix`); an `awaiting-funds` PR →
  re-fire QA (add `agent/retriage`).
- The **QA caller** gains a `pull_request.labeled` trigger guarded to `agent/retriage` (so the
  canary can re-fire QA without looping on its own `qa/pass`/`qa/flag` labels); the QA prompt
  strips the marker on review. Requires a second `sync-factory-callers.sh` pass.

## [1.3.0] — 2026-06-11

### Added
- Network advisory for the June 2026 tollbooth-dpyc v0.44.2–v0.44.5 series,
  including a **security advisory** for the v0.44.2 credential-card redemption
  leak (raw credentials could be echoed when redeeming an `ncred` card; fixed).

### Changed
- `network-status.json` refreshed to current component versions (it was stale
  at the v0.13.5 era): tollbooth-dpyc 0.44.5 (**minimum raised to 0.44.2** — the
  security floor), tollbooth-authority 0.10.1, thebrain-mcp 1.12.0, excalibur-mcp
  0.9.1, schwab-mcp 0.11.1, taxsort-mcp 0.27.1, tollbooth-sample 0.3.1. Advisory
  and architecture notes updated to reflect event-loop hardening (v0.44.3) and
  the in-progress `register_standard_tools` → `tollbooth.tools.*` decomposition.

## [1.2.0] — 2026-04-19

### Added
- TrancheLifetime constraint: configurable credit expiration replacing DemurrageConstraint
- Constraint scoping: per-tool (`tool_ids`) and per-patron (`patron_npubs`, max 10) targeting
- Happy Hour recurrence: user-facing fields (`in_effect`, `until`, `repeats`, `apply_on`, `percent_off`, `max_discount`)
- Per-operator Neon schema isolation with `encrypted_blob` column for credential storage
- Authority schema created symmetrically with operator schemas
- Cold start inline retry: 3 attempts with 2-second backoff on vault hydration
- Patron-chosen proof cache duration via `parse_duration` (24h cap)
- Secure Courier: human-in-the-loop proof requirement and destructive relay drain documented
- Network advisory for April 2026 releases (v0.10.0–v0.13.5)

### Changed
- Schema symmetry: `public` Postgres schema eliminated; all data in named operator/authority schemas
- OAuth: credential field mapping consolidated, `/callback` suffix removed, `scope` removed for Schwab
- All MCPs pinned to tollbooth-dpyc==0.13.5
- Pricing Studio v1.8.0 with constraint scoping UI and Happy Hour editor
- network-status.json updated with architecture notes on schema symmetry

### Fixed
- `encrypted_blob` column creation in per-operator schema isolation
- OAuth redirect URI `/callback` suffix causing 404s on some providers

## [1.1.0] — 2026-03-04

- docs: update README for file-per-member directory structure
- Merge pull request #45 from lonniev/feat/file-per-member
- feat: refactor members.json into file-per-member directory tree
- Merge pull request #44 from lonniev/feat/trademark-foundation
- feat: add common-law trademark notices (DPYC™, Tollbooth DPYC™, Don't Pester Your Customer™)
- Merge pull request #43 from lonniev/chore/v0.1.69-network-status
- chore: bump network-status for tollbooth-dpyc 0.1.69, thebrain-mcp 1.9.6
- docs: Oracle delegation advisory and version bumps
- Merge pull request #42 from lonniev/feat/oracle-registry
- feat: register dpyc-oracle service under Prime Authority
- Merge pull request #41 from lonniev/feat/update-network-status
- docs: update network-status and advisory for auto-certify release
- Merge pull request #40 from lonniev/feat/authority-service-url
- feat: add Authority service endpoint to registry
- Merge pull request #39 from lonniev/lonniev-patch-1
- Add new member entry for Lonnie VanZandt (Twitter)
- Merge pull request #38 from lonniev/docs/release-notes-v0.1.58-v0.3.2
- docs: release notes for unified commerce terminology (v0.1.58 / v0.3.2)
- Merge pull request #37 from lonniev/docs/unified-commerce-model
- docs: replace tax terminology with certification fee
- Merge pull request #36 from lonniev/chore/release-notes-0.1.57
- chore: release notes for tollbooth-dpyc 0.1.57
- advisory: tollbooth-dpyc 0.1.55 tempered greedy @@@ regex (#35)
- advisory: tollbooth-dpyc 0.1.54 / thebrain-mcp 1.9.1 hotfixes (#34)
- advisory: thebrain-mcp 1.9.0 Secure Courier + NeonCredentialVault (#33)
- Merge pull request #32 from lonniev/release/tollbooth-dpyc-0.1.52
- docs: tollbooth-dpyc 0.1.52 — LNURL-pay resolution for Lightning payouts
- NSEC-Only Identity advisory + version bump all components
- Merge pull request #29 from lonniev/feat/authority-separation
- Merge pull request #30 from lonniev/worktree-patent-docs
- Add provisional patent specification draft and cover memo
- Register Lonnie-Authority and excalibur-mcp, update operator upstream refs
- Merge pull request #28 from lonniev/worktree-patent-docs
- Add USPTO-compliant patent figures and reference schedule
- Merge pull request #27 from lonniev/fix/advisory-feb28-versions
- Add advisory for tollbooth-dpyc 0.1.47 + excalibur-mcp 0.6.2
- Merge pull request #26 from lonniev/feat/whitepaper-and-landscape
- Add Tollbooth whitepaper, competitive landscape analysis, and README links
- Merge pull request #25 from lonniev/feat/readme-update
- Resolve merge conflict — keep both Economic Model and DPYP-01 link
- Add excalibur-mcp to the Certification Chain and link certificate protocol
- Merge pull request #24 from lonniev/feat/economics-svg
- Merge pull request #23 from lonniev/feat/logo-url
- Add 5-Authority network economics SVG and README section
- Add DPYC logo reference to README for Oracle discoverability
- Merge pull request #22 from lonniev/advisory/nip44-encrypted-audit
- Advisory: NIP-44 encrypted audit events for patron privacy
- Merge pull request #21 from lonniev/advisory/nostr-only-certificates
- Advisory: Nostr-only certificates — JWT/Ed25519 removed
- Merge pull request #20 from lonniev/advisory/security-hardening-v0.1.25
- Update network advisory for security audit remediation
- Merge pull request #19 from lonniev/fix/ssl-cert-verification
- Fix SSL certificate verification bypass in publish_dpyp.py
- Merge pull request #18 from lonniev/chore/authority-0.2.0-advisory
- Update advisory for tollbooth-authority 0.2.0 and tollbooth-dpyc 0.1.24
- Merge pull request #17 from lonniev/chore/ots-0.1.23-advisory
- Update advisory for tollbooth-dpyc 0.1.23 (OTS Bitcoin anchoring)
- Advisory: tollbooth-dpyc 0.1.22 serverless flush strategy
- Add NeonVault advisory: 5-8x faster vault persistence via Neon Postgres
- Merge pull request #15 from lonniev/feat/bump-dpyc-0.1.17
- Bump tollbooth-dpyc current to 0.1.17 (account_statement_tool)
- Merge pull request #14 from lonniev/feat/tranche-credit-expiration-advisory
- Advisory: tollbooth-dpyc 0.1.16 tranche-based credit expiration
- Merge pull request #13 from lonniev/feat/advisory-update
- Update advisory: service_status endpoints and citizenship onboarding
- Merge pull request #12 from lonniev/feat/citizen-tier
- Update governance: citizenship is instant, no PR review needed
- Add citizen tier to schema, validation, and governance
- Merge pull request #11 from lonniev/update/release-report-0.1.15
- Update release report: tollbooth-dpyc 0.1.15, minimum 0.1.14
- Add network-status.json and ADVISORY.md for version discovery (#10)
- Add "Why Tollbooth?" section positioning value vs x402/L402 (#9)
- Merge pull request #8 from lonniev/fix/readme-operator-npub
- Fix stale operator npub in README Certification Chain diagram
- Fix publish script: pynostr 0.7 API + websocket-client
- Merge pull request #7 from lonniev/feat/dpyp-01-spec
- Add DPYP-01 base certificate spec and NIP-78 publish script
- Merge pull request #6 from lonniev/feat/dpyc-creed
- Merge pull request #5 from lonniev/fix/readme-self-link-and-npub
- Merge pull request #4 from lonniev/fix/stale-governance-npub
- Add DPYC Creed — founding declaration of values
- Add self-link, fix stale npub, convert to absolute URLs
- Fix stale Prime Authority npub in GOVERNANCE.md
- Merge pull request #3 from lonniev/feat/logo-assets
- Add DPYC logo assets
- Merge pull request #2 from lonniev/fix/rotate-operator-npub
- Rotate Operator (thebrain-mcp) npub after lost private key
- Merge pull request #1 from lonniev/fix/rotate-authority-npub
- Rotate Prime Authority npub after lost private key
- Found the DPYC Social Contract — membership registry, governance, and CI
- Initial commit

