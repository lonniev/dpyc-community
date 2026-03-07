# DPYC™ Network Advisory

> Last updated: 2026-03-07

## Current Advisories

### Tax Incidence Fix and Legacy Royalty Removal (2026-03-07)

**Affects:** All operators and patrons in the DPYC ecosystem

Two related economic bugs have been identified and resolved:

**1. Tax Incidence Bug — Patron was paying certification fee instead of operator**

The certification fee (2% ad valorem) was incorrectly deducted from the patron's invoice amount. When a patron purchased 1000 api_sats, the BTCPay invoice was created for `net_sats` (980) instead of the full `amount_sats` (1000). The patron received fewer credits than requested. The correct behavior: the operator absorbs the certification fee as a cost of doing business, and the patron pays the full sticker price.

**2. Legacy Royalty Payout — double-taxation removed**

A legacy "royalty payout" side effect fired a separate 2% BTCPay payout to a configured originator address on every settled invoice — in addition to the Authority certification fee already deducted from the operator's reserve. This resulted in double-taxation. The correct model: the certification fee cascade is the sole taxation mechanism. Authorities are Operators of their upstream Authority; the Prime Authority collects revenue through the same cascade as every other Authority.

**What changed:**

| Component | Version | Key Changes |
|-----------|---------|-------------|
| tollbooth-dpyc | **0.1.78** | Invoice uses `amount_sats` (not `net_sats`). Royalty payout function, config fields, and BTCPay payout checks removed entirely. |
| thebrain-mcp | **1.9.6** | Royalty ENV vars removed. `check_payment` no longer fires payout. `purchase_credits` docstring corrected. |
| excalibur-mcp | **0.6.14** | Same royalty cleanup. Tax docstring corrected. |
| tollbooth-authority | **0.3.8** | Upstream royalty payout removed. `certify_credits` `net_sats` documented as operator-only accounting field. |
| dpyc-oracle | **0.2.3** | `economic_model()` updated — describes cascade as sole revenue mechanism, removes "curator royalty" reference. |

**Action required:**
1. Update `tollbooth-dpyc` to >= 0.1.78
2. Update all MCP servers to latest versions
3. Remove `TOLLBOOTH_ROYALTY_ADDRESS`, `TOLLBOOTH_ROYALTY_PERCENT`, `TOLLBOOTH_ROYALTY_MIN_SATS` ENV vars from deployments
4. Redeploy services

### Authority Curator Onboarding via Nostr DM Challenge-Response (2026-03-06)

**Affects:** New Authority operators joining the DPYC ecosystem

A new 3-step protocol allows Authority curators to onboard without manual env var configuration or server restarts. The entire flow uses Nostr DM challenge-response with Schnorr-signed anti-replay protection.

**Protocol flow:**

1. `register_authority_npub(npub)` — Authority sends DM challenge to candidate
2. Candidate replies via Nostr client: `claim = @@@yes@@@` with poison slug
3. `confirm_authority_claim(npub)` — verifies candidate DM, sends approval request to Prime Authority
4. Prime replies via Nostr client: `approval = @@@yes@@@` with poison slug
5. `check_authority_approval(npub)` — checks Prime approval, persists curator npub, registers in community

**What changed:**

| Component | Version | Key Changes |
|-----------|---------|-------------|
| tollbooth-dpyc | **0.1.77** | New `authority_config` key-value table in NeonVault for persisting curator npub. `get_config()` / `set_config()` methods. |
| dpyc-oracle | **0.2.2** | New `register_authority()` tool — commits `members/authorities/{npub}.json` via GitHub API. Updated `how_to_join()` Authority tier with concrete 7-step onboarding. |
| tollbooth-authority | **0.3.7** | 3 new onboarding tools. `OnboardingState` machine. Vault-persisted curator npub (no restart). Oracle MCP-to-MCP registration. `report_upstream_purchase` reads npub from vault. Actor catalog 11 → 14 tools. |

**Architecture:** Candidate↔Authority DM challenge, Authority→Prime DM approval, Authority→Oracle MCP-to-MCP registration. All identity proof via Schnorr-signed Nostr events.

**Action required:**
1. Update `tollbooth-dpyc` to >= 0.1.77
2. Update `tollbooth-authority` to >= 0.3.7
3. Redeploy Authority service
4. Start a new MCP session to pick up the 3 new tool registrations
5. New Authority curators: follow `how_to_join()` Authority tier instructions

### Oracle Delegation: Operator→Oracle Direct Routing (2026-03-04)

**Affects:** All operators in the DPYC ecosystem

Operators can now delegate community queries to the DPYC Oracle via direct MCP-to-MCP routing — no separate MCP connection from the AI agent needed. Five free Oracle tools are now available through any Operator server:

| Tool | Description |
|------|-------------|
| `brain_how_to_join` | DPYC onboarding instructions |
| `brain_get_tax_rate` | Current certification fee rate |
| `brain_lookup_member` | Look up a member by Nostr npub |
| `brain_dpyc_about` | DPYC ecosystem description |
| `brain_network_advisory` | Active network advisories |

**What changed:**

| Component | Version | Key Changes |
|-----------|---------|-------------|
| tollbooth-dpyc | **0.1.68** | New `OracleClient` class — generic MCP-to-MCP delegate for Oracle calls. New `resolve_oracle_service()` — walks authority chain to Prime Authority to find the `dpyc-oracle` service. |
| thebrain-mcp | **1.9.5** | 5 new `@tool` functions delegating to Oracle. Cached `_resolve_oracle_service_url()` for process-lifetime resolution. Actor stubs replaced with real delegation. |
| dpyc-community | — | Prime Authority's `services[]` now includes `dpyc-oracle` FastMCP Cloud URL for endpoint discovery. |

**Architecture:** Operator→Oracle (2-hop direct routing). Oracle tools are free and unauthenticated — no Authority intermediation, no credits required.

**Action required:**
1. Update `tollbooth-dpyc` to >= 0.1.68
2. Update `thebrain-mcp` to >= 1.9.5
3. Redeploy operator services
4. Start a new MCP session to pick up the 5 new tool registrations

### Auto-Certify purchase_credits: One-Step Credit Purchase (2026-03-03)

**Affects:** All operators in the DPYC ecosystem

The `purchase_credits` tool on operator servers (thebrain-mcp, excalibur-mcp) no longer requires a pre-obtained Authority certificate. The operator server now contacts its upstream Authority behind the scenes via **Horizon OAuth server-to-server MCP call**, obtains a signed certificate, and creates the Lightning invoice — all in one tool call.

**What changed:**

| Component | Version | Key Changes |
|-----------|---------|-------------|
| tollbooth-dpyc | **0.1.66** | New `AuthorityCertifier` class — `fastmcp.Client` with `auth="oauth"` for server-to-server certificate acquisition. New `resolve_authority_service()` — resolves operator npub to Authority MCP endpoint URL via community registry. |
| thebrain-mcp | **1.9.4** | `purchase_credits` drops `certificate` parameter — auto-certifies internally. `purchase_credits` and `check_payment` actor stubs wired to server.py. |
| excalibur-mcp | **0.6.8** | Same auto-certify pattern as thebrain-mcp. |
| dpyc-community | — | Authority member's `services[]` now includes `tollbooth-authority` FastMCP Cloud URL for endpoint discovery. |

**New call flow (simplified):**
1. `purchase_credits(amount_sats=100)` — one call, no pre-setup
2. Pay the Lightning invoice
3. `check_payment(invoice_id)` — credits land in your balance

**Old call flow (removed):**
1. ~~`authority_certify_credits(operator_id, amount_sats)` — get JWT~~ (no longer needed)
2. ~~`purchase_credits(amount_sats, certificate=JWT)` — pass JWT~~ (certificate param removed)

**Action required:**
1. Update `tollbooth-dpyc` to >= 0.1.66
2. Update `thebrain-mcp` to >= 1.9.4
3. Update `excalibur-mcp` to >= 0.6.8
4. Redeploy all operator services
5. Start a new MCP session to pick up the updated tool signatures

### Unified Commerce Terminology: tax → certification fee (2026-03-02)

**Affects:** All operators and Authorities in the DPYC ecosystem

The "tax" vocabulary has been retired across the entire stack. The Authority charges a **certification fee** on each purchase order — computed by `ToolPricing.compute()` — not a separate tax. Certificate claims now emit `fee_sats` instead of `tax_paid_sats`.

| Component | Version | Key Changes |
|-----------|---------|-------------|
| tollbooth-dpyc | **0.1.58** | Removed `purchase_tax_credits_tool()` → replaced by `direct_purchase_tool()`. Certificate verification returns `fee_sats` (reads both `fee_sats` and `tax_paid_sats` from incoming certs for backward compat). |
| tollbooth-authority | **0.3.2** | `certify_credits` response and Nostr event claims emit `fee_sats` only (`tax_paid_sats` removed). Deprecated v0.1.x tool shims removed: `purchase_tax_credits`, `check_tax_payment`, `tax_balance`, `certify_purchase`. New tools: `account_statement`, `account_statement_infographic` (SVG). |
| dpyc-community | — | GOVERNANCE.md, README.md, DPYP-01 protocol spec updated: "tax" → "certification fee" / "fee schedule" / `fee_sats`. |

**New tools in tollbooth-authority v0.3.2:**
- `account_statement` — structured JSON operator account (balance, deposits, fees paid, certified amount, tranches, fee schedule)
- `account_statement_infographic` — SVG rendering of the above, dark-themed with Bitcoin-orange accents

**Removed tools in tollbooth-authority v0.3.2:**
- `purchase_tax_credits` → use `purchase_credits`
- `check_tax_payment` → use `check_payment`
- `tax_balance` → use `check_balance`
- `certify_purchase` → use `certify_credits`

**Action required:**
1. Update `tollbooth-dpyc` to >= 0.1.58
2. Update `tollbooth-authority` to >= 0.3.2
3. If your code reads `tax_paid_sats` from `certify_credits` responses, switch to `fee_sats`
4. If your code calls any removed tool names, switch to the current names (see table above)
5. Redeploy

### tollbooth-dpyc 0.1.57: Pop-and-Acknowledge Relay DMs (2026-03-02)

**Affects:** All operators using Secure Courier credential delivery

Every DM encountered during `receive_credentials` is now consumed from the relay (NIP-09 deletion + local queue purge) regardless of validity. Each popped message gets a reply DM to the sender explaining acceptance or rejection. This keeps relay queues clean and gives users immediate feedback on malformed credentials.

| Version | Change |
|---------|--------|
| **0.1.56** | Purge stale DMs from local queue after poison match |
| **0.1.57** | Pop-and-acknowledge all DMs — wrong poison, no @@@ markers, NIP-04 rejected, undecryptable — all popped with reason reply |

**Action required:**
1. Update `tollbooth-dpyc` to >= 0.1.57
2. Redeploy

### tollbooth-dpyc 0.1.55 / thebrain-mcp 1.9.1: Secure Courier Hotfixes (2026-03-02)

**Affects:** All operators using Secure Courier credential delivery

Three hotfixes for issues discovered during the first live Secure Courier onboarding:

| Component | Version | Fix |
|-----------|---------|-----|
| thebrain-mcp | **1.9.1** | `AuditedVault` unwrap used wrong attribute (`_vault` → `_inner`). `receive_credentials` and `forget_credentials` crashed with `'AuditedVault' object has no attribute '_execute'`. |
| tollbooth-dpyc | **0.1.54** | `@@@` delimiter regex uses `re.DOTALL` so values spanning line breaks (injected by mobile Nostr clients like 0xchat) are parsed. Removed `(REQUIRED)` / `(optional)` labels from welcome DM template. |
| tollbooth-dpyc | **0.1.55** | Replaced `re.DOTALL` + `.+?` with tempered greedy token `(?:[^@]\|@(?!@@))*` — prevents first field's capture from bleeding across adjacent `@@@` delimiters. Fixes `brain_id` not parsing after `api_key` succeeded. |

**Action required:**
1. Update `tollbooth-dpyc` to >= 0.1.55
2. Update `thebrain-mcp` to >= 1.9.1
3. Redeploy

### BREAKING: thebrain-mcp 1.9.0 — Secure Courier + NeonCredentialVault (2026-03-01)

**Affects:** All thebrain-mcp users (credential flow completely replaced)

Credentials are now delivered via **encrypted Nostr DMs** (Secure Courier), not typed into the MCP chat. The passphrase-based vault (PersonalBrainVault / TheBrainVault) has been removed entirely. Credential persistence moved to **NeonCredentialVault** (Neon serverless Postgres — same DB as the commerce ledger).

**What changed:**

| Component | Version | Key Changes |
|-----------|---------|-------------|
| tollbooth-dpyc | **0.1.53** | New `NeonCredentialVault` class — `CredentialVaultBackend` implementation sharing NeonVault's httpx client. Composite PK `(service, npub)`. |
| thebrain-mcp | **1.9.0** | Secure Courier wiring. `register_credentials`, `upgrade_credentials`, `activate_session`, `activate_dpyc` **removed**. New tools: `request_credential_channel`, `receive_credentials`, `forget_credentials` (all FREE). vault.py stripped to session-only. `cryptography` dependency removed. |

**Removed tools** (no longer available):
- `register_credentials` → replaced by `request_credential_channel` + `receive_credentials`
- `upgrade_credentials` → no longer needed (no passphrase vault)
- `activate_session` → replaced by `receive_credentials` vault-first lookup
- `activate_dpyc` → removed (was already deprecated)

**New user flow:**
1. `session_status` → returns onboarding `next_steps`
2. `request_credential_channel(recipient_npub=<npub>)` → welcome DM arrives in Nostr client
3. User replies via Nostr DM: `{"api_key": "...", "brain_id": "..."}`
4. `receive_credentials(sender_npub=<npub>)` → credentials vaulted, session activated

**Returning users:** `receive_credentials(sender_npub=<npub>)` does a vault-first lookup in NeonCredentialVault — instant activation, no relay I/O, no passphrase.

**Action required:**
1. Update `tollbooth-dpyc` to >= 0.1.53
2. Update `thebrain-mcp` to >= 1.9.0
3. Ensure `NEON_DATABASE_URL` is set (NeonVault is now mandatory — TheBrainVault fallback removed)
4. Existing users must re-register via the Secure Courier flow (hard cutover, no migration)
5. Start a new MCP session to pick up the new tools

### tollbooth-dpyc 0.1.52: LNURL-pay Resolution for Lightning Payouts (2026-03-01)

**Affects:** All operators with royalty payouts configured (`TOLLBOOTH_ROYALTY_ADDRESS`)

BTCPay's Lightning payout processor can only auto-pay BOLT11 invoices (`lnbc...`), not Lightning addresses (`user@domain`). Previously, royalty payouts passed the Lightning address directly to `create_payout()`, causing payouts to get stuck in "Awaiting Payment" forever.

**What changed:**

| Component | Version | Key Changes |
|-----------|---------|-------------|
| tollbooth-dpyc | **0.1.52** | New `lnurl.py` module resolves Lightning addresses to BOLT11 invoices via LNURL-pay protocol (LUD-06 + LUD-16) before calling `create_payout()`. No new dependencies — uses httpx. |

**Key behaviors:**
- Destinations already in BOLT11 format (`lnbc...`) skip resolution entirely
- Resolution failures return an error dict — never block credit settlement
- New `payout_destination` field in payout results shows the resolved invoice prefix
- No configuration changes needed — existing `TOLLBOOTH_ROYALTY_ADDRESS` (e.g., `tollbooth@btcpay.digitalthread.link`) works automatically

**Action required:**
1. Update `tollbooth-dpyc` to >= 0.1.52 (or leave at >= 0.1.51 — backward compatible)
2. Redeploy your service — payouts will auto-resolve and auto-pay within 1 minute
3. Cancel any stuck payouts in BTCPay from before this fix

### BREAKING: NSEC-Only Identity — Authority Separation and npub Env Purge (2026-03-01)

**Affects:** All operators and Authorities in the DPYC ecosystem

All services now derive their own npub from `TOLLBOOTH_NOSTR_OPERATOR_NSEC` and resolve their upstream authority dynamically from the [DPYC community registry](https://github.com/lonniev/dpyc-community/blob/main/members.json). Hardcoded npub env vars have been purged.

**What changed:**

| Component | Version | Key Changes |
|-----------|---------|-------------|
| tollbooth-dpyc | **0.1.51** | New `DPYCRegistry` class with `resolve_authority_npub()` moved into the shared library; exported from `tollbooth` top-level |
| tollbooth-authority | **0.3.1** | Local `registry.py` replaced with re-export from tollbooth-dpyc; `dpyc_authority_npub` and `dpyc_upstream_authority_npub` config fields removed; `report_upstream_purchase` admin auth uses `signer.npub` |
| excalibur-mcp | **0.6.5** | `dpyc_operator_npub` and `dpyc_authority_npub` config fields removed; new `_resolve_authority_npub()` derives identity at runtime |
| thebrain-mcp | **1.8.0** | Same pattern as excalibur-mcp; `purchase_credits` and `btcpay_status` use registry resolution |
| dpyc-community | — | New members: "Lonnie-Authority" (dedicated authority identity) and "excalibur-mcp" (operator); thebrain-mcp upstream updated |

**Identity separation:** The Prime Authority's personal npub (`npub1l94pd4...`) is now distinct from the operational Authority identity (`npub1fuhq0c...`, "Lonnie-Authority"). Each operator has its own keypair and resolves its upstream authority from the registry.

**Removed env vars** (no longer recognized — DELETE from all deployments):
- `DPYC_AUTHORITY_NPUB` — replaced by registry resolution via `DPYCRegistry.resolve_authority_npub()`
- `DPYC_OPERATOR_NPUB` — replaced by deriving from `TOLLBOOTH_NOSTR_OPERATOR_NSEC`
- `DPYC_UPSTREAM_AUTHORITY_NPUB` — replaced by registry resolution

**Action required:**
1. Update `tollbooth-dpyc` to >= 0.1.51
2. Update `tollbooth-authority` to >= 0.3.1
3. Update `excalibur-mcp` to >= 0.6.5
4. Update `thebrain-mcp` to >= 1.8.0
5. **Delete** `DPYC_AUTHORITY_NPUB`, `DPYC_OPERATOR_NPUB`, and `DPYC_UPSTREAM_AUTHORITY_NPUB` from all deployments
6. Ensure `TOLLBOOTH_NOSTR_OPERATOR_NSEC` is set on each service (each service needs its own unique keypair)
7. Redeploy all services

**Supersedes:** The "Ensure `DPYC_AUTHORITY_NPUB` is set on all Operator services" guidance from the 2026-02-25 Nostr-Only advisory is now obsolete. That env var no longer exists.

### tollbooth-dpyc 0.1.47 / excalibur-mcp 0.6.2: DRY Version + NIP-17 Inbound Fix (2026-02-28)

**Affects:** All operators and downstream MCP servers

**tollbooth-dpyc 0.1.46** — NIP-17 inbound receive path fix:
- Gift wrap events with fuzzed `created_at` (0-48h past per NIP-17 spec) were silently discarded by the local freshness filter. The relay filter correctly widened `since` by 48h, but the local candidate loop applied the narrow 15-min window. Fixed by widening the local cutoff for kind 1059 events.
- Two user-facing messages in `open_channel()` still referenced "JSON" instead of the @@@ delimiter format. Fixed.

**tollbooth-dpyc 0.1.47** — DRY version:
- `__version__` now reads from `importlib.metadata.version()` instead of a hardcoded string. `pyproject.toml` is the single source of truth.

**excalibur-mcp 0.6.2** — DRY version + dep bump:
- Same `importlib.metadata` fix. Bumps tollbooth-dpyc dependency to >= 0.1.46.

**Action required:**
1. Update `tollbooth-dpyc` to >= 0.1.47
2. Redeploy your service — NIP-17 DM replies will now be received correctly
3. Verify with `service_status()` — versions should report from package metadata

### tollbooth-dpyc 0.1.28: NIP-44 Encrypted Audit Events — Patron Privacy (2026-02-25)

**Affects:** All operators publishing Nostr audit events

Audit event `content` is now **NIP-44v2 encrypted** to the patron's npub when the patron is identified by an npub. Only the patron's nsec can decrypt their balance data. Observers see event metadata (kind, tags, pubkey) but not the encrypted content.

**Key behaviors:**
- **npub patrons**: Content encrypted via NIP-44v2 (secp256k1 ECDH + HKDF + ChaCha20-Poly1305). Events include `["encrypted", "nip44"]` tag.
- **Plaintext fallback refused**: If NIP-44 deps are unavailable for npub patrons, events are silently skipped (never published in cleartext).
- **Non-npub patrons**: Legacy Horizon IDs still get plaintext events (no behavioral change).
- **Zero new dependencies**: Uses `coincurve` and `cryptography` already present as transitive deps of `pynostr`.

**Patron verification flow** (future tool):
1. Filter relay: `kinds=[30078], #p=[my_hex_pubkey], #t=["tollbooth-audit"]`
2. Decrypt each event: `nip44_decrypt(my_nsec, operator_pubkey, event.content)`
3. Result: full plaintext audit record with balance, deposits, tool usage

**Action required:**
1. Update `tollbooth-dpyc` to >= 0.1.28
2. Redeploy your service — encryption activates automatically for npub patrons
3. No configuration changes needed

### BREAKING: Nostr-Only Certificates — JWT/Ed25519 Removed (2026-02-25)

**Affects:** All operators and Authorities in the DPYC ecosystem

The certificate system has been migrated from Ed25519 JWTs to **Nostr Schnorr-signed events (kind 30079)** as the sole certificate mechanism. `PyJWT` and `cryptography` (for signing) have been removed as dependencies.

**What changed:**

| Component | Version | Key Changes |
|-----------|---------|-------------|
| tollbooth-dpyc | **0.1.27** | `verify_certificate()` deleted; `verify_certificate_auto()` Nostr-only; `authority_public_key` config removed; `PyJWT[crypto]` dep dropped |
| tollbooth-authority | **0.3.0** | `signing.py`, `certificate.py`, `generate_keypair.py` deleted; `PyJWT`, `cryptography` deps dropped; `AUTHORITY_SIGNING_KEY` env var removed; nsec now mandatory |
| thebrain-mcp | latest | `AUTHORITY_PUBLIC_KEY` env var removed; trust gate requires `DPYC_AUTHORITY_NPUB` only |

**Removed env vars** (no longer recognized):
- `AUTHORITY_PUBLIC_KEY` — replaced by `DPYC_AUTHORITY_NPUB`
- `AUTHORITY_SIGNING_KEY` — replaced by `TOLLBOOTH_NOSTR_OPERATOR_NSEC`

**Action required:**
1. Update `tollbooth-dpyc` to >= 0.1.27
2. Update `tollbooth-authority` to >= 0.3.0
3. Ensure `TOLLBOOTH_NOSTR_OPERATOR_NSEC` is set on your Authority (nsec from your DPYC keypair)
4. Ensure `DPYC_AUTHORITY_NPUB` is set on all Operator services
5. Remove any `AUTHORITY_PUBLIC_KEY` or `AUTHORITY_SIGNING_KEY` env vars from your deployments
6. Redeploy all services and start new MCP sessions

### SECURITY: Critical + High Severity Fixes Across Ecosystem (2026-02-24)

**Affects:** All operators and services in the DPYC ecosystem

A full security audit identified 12 findings (1 Critical, 4 High, 5 Medium, 5 Low). The Critical and all High findings have been remediated:

**C-1 (Critical): SSL Certificate Verification Disabled** — `ssl.CERT_NONE` in Nostr relay WebSocket connections allowed MITM attacks on the audit trail.
- Fixed in: tollbooth-dpyc 0.1.25, dpyc-community `scripts/publish_dpyp.py`

**H-1 (High): Path Traversal in Attachment Tools** — User-supplied file paths in `add_file_attachment` and `get_attachment_content` were not validated, allowing arbitrary file read/write on the server.
- Fixed in: thebrain-mcp (PR #92) — new `_validate_path_within()` helper enforces `attachment_safe_directory`

**H-2 (High): Missing Authorization on `report_upstream_purchase`** — Any authenticated user could call this admin-only tool to inflate the upstream supply ledger.
- Fixed in: tollbooth-authority (PR #33) — caller's npub must match `DPYC_AUTHORITY_NPUB`

**H-3 (High): `whoami` Exposed Raw JWT Claims** — Raw Authorization header JWT was decoded without verification and returned to callers.
- Fixed in: thebrain-mcp (PR #92) — only verified `fastmcp-*` headers and DPYC session status returned

**H-4 (High): Outdated `cryptography` Dependency Floor** — Floor `>=42.0.0` admitted versions with known CVEs.
- Fixed in: thebrain-mcp (PR #92) and tollbooth-authority (PR #34) — bumped to `cryptography>=46.0.5`

**Action required:**
1. Update `tollbooth-dpyc` to >= 0.1.25 (**Critical security fix**)
2. Redeploy `tollbooth-authority` (admin auth + crypto floor)
3. Redeploy `thebrain-mcp` (path traversal + whoami + crypto floor)
4. Verify with `service_status()` on each service

### tollbooth-authority 0.2.0: Self-Similar Operator Naming + ToolPricing (2026-02-23)

**Affects:** All operators and downstream MCP servers calling the Authority

**Breaking change**: All Authority MCP tool names have been renamed to standard Tollbooth Operator conventions. Manual tax math replaced with `ToolPricing.compute()` from tollbooth-dpyc 0.1.24.

**Tool renames:**

| Old (v0.1.x) | New (v0.2.0) | Notes |
|---|---|---|
| `purchase_tax_credits` | `purchase_credits` | Deprecated shim returns error with migration guidance |
| `check_tax_payment` | `check_payment` | Deprecated shim returns error with migration guidance |
| `tax_balance` | `check_balance` | Deprecated shim returns error with migration guidance |
| `certify_purchase` | `certify_credits` | Deprecated shim delegates to `certify_credits` (pass-through) |

**Fee computation now uses ToolPricing:**
- Old: `max(TAX_MIN_SATS, ceil(amount_sats * TAX_RATE_PERCENT / 100))`
- New: `ToolPricing(rate_percent=2.0, rate_param="amount_sats", min_cost=10).compute(amount_sats=N)`
- **Behavioral equivalence verified** — identical output for all inputs

**New in responses:**
- `certify_credits` returns both `fee_sats` (new) and `tax_paid_sats` (kept for backward compat) in the response
- `operator_status` includes a `certification_fee` info block

**Downstream updated:**
- thebrain-mcp PR #91 (merged) — calls `certify_credits`, removed legacy `purchase_tax_credits_tool` re-export

**Action required:**
1. Update `tollbooth-dpyc` to >= 0.1.24
2. Update `tollbooth-authority` to >= 0.2.0
3. Update any MCP server code that calls old tool names (`certify_purchase` still works as pass-through, but the other three will return errors)
4. Redeploy and start a new MCP session

### tollbooth-dpyc 0.1.24: ToolPricing Dataclass (2026-02-23)

**Affects:** All operators and Authorities

New `ToolPricing` dataclass for standardized fee/tax computation:
- `ToolPricing(rate_percent, rate_param, min_cost)` — replaces ad-hoc `max(min, ceil(...))` patterns
- `compute(**kwargs)` method takes the pricing parameter by name and returns the fee in sats
- Exported from `tollbooth` top-level package

Used by tollbooth-authority 0.2.0 for certification fee computation. Available to any operator for custom pricing logic.

**No action required** — additive change. Operators can optionally adopt `ToolPricing` for their own fee calculations.

### tollbooth-dpyc 0.1.23: OpenTimestamps Bitcoin Anchoring (2026-02-23)

**Affects:** All operators seeking Bitcoin-grade ledger immutability

**Fourth trust layer**: periodically anchor a Merkle root of all ledger balances to Bitcoin via OpenTimestamps. Patrons can independently verify their balance was included in a Bitcoin-committed hash.

New modules in tollbooth-dpyc:
- `ots.py`: `MerkleTree` (SHA-256, deterministic), `InclusionProof` (verifiable), `OTSCalendarClient` (async multi-calendar)
- `tools/anchors.py`: `anchor_ledger_tool`, `get_anchor_proof_tool`, `list_anchors_tool`

Extended:
- `NeonVault`: new `anchors` table, `fetch_all_balances`, anchor CRUD methods
- `TollboothConfig`: `ots_enabled`, `ots_calendars` fields

New MCP tools in thebrain-mcp:
- `anchor_ledger` — operator tool, builds Merkle tree + submits to OTS calendars
- `get_anchor_proof` — patron tool (1 sat), generates verifiable inclusion proof
- `list_anchors` — free informational tool, lists recent anchor records

**Zero new dependencies** — uses stdlib `hashlib` for Merkle tree, existing `httpx` for OTS calendar HTTP calls. Reserved `ots = []` extras group for future use.

**Full trust stack now complete:**

| Layer | Purpose | Latency |
|---|---|---|
| LedgerCache | Real-time balance authority | Zero |
| NeonVault | ACID Postgres persistence | ~32ms |
| AuditedVault | Nostr event audit trail | Zero (bundled) |
| **OTS Anchoring** | **Bitcoin-anchored state proof** | **Zero (decoupled)** |

**Downstream pins updated:**
- thebrain-mcp PR #90 (merged)
- tollbooth-authority PR #31 (merged)

**Action required:**
1. Update `tollbooth-dpyc` to >= 0.1.23
2. Set `TOLLBOOTH_OTS_ENABLED=true` and optionally `TOLLBOOTH_OTS_CALENDARS` in your environment
3. Redeploy your service
4. Start a new MCP session to pick up the new tools

### tollbooth-dpyc 0.1.22: Serverless-Aware Per-Entry Flush Strategy (2026-02-23)

**Affects:** All operators running on serverless platforms (FastMCP Cloud)

The `LedgerCache` flush strategy has been upgraded from a global monotonic-clock timer to **per-entry flush triggers**. In serverless environments where there is no background process between requests, the old global `_maybe_flush()` timer could not advance, risking dirty entries being lost on process eviction.

New flush triggers (evaluated per cache entry on `get()`):
- **Count-based**: flush after N dirty marks (configurable `flush_batch_size`, default 10)
- **Staleness-based**: flush after T seconds since last flush (configurable `flush_staleness_secs`, default 120)

New convenience methods:
- **`debit(user_id, tool_name, cost)`** — hydrate + flush-due check + debit + mark_dirty in one call
- **`write_through_credit(user_id)`** — mark dirty + immediate flush for credit settlements

**Hot path preserved**: 9 out of 10 debits are pure in-memory dict lookup + integer subtraction. The 10th amortizes one vault write. Max loss on serverless eviction = `(N-1) × max_cost_per_call` (90 api_sats at defaults) — operator absorbs the loss, patron never loses credits.

**Backward compatible** — no operator server changes required. Existing `get()` callers benefit transparently. New config fields (`flush_batch_size`, `flush_staleness_secs`) added to `TollboothConfig` with sane defaults.

**Downstream pins updated:**
- thebrain-mcp PR #89 (merged)
- tollbooth-authority PR #30 (merged)

**Action required:**
1. Update `tollbooth-dpyc` to >= 0.1.22
2. Optionally tune `flush_batch_size` and `flush_staleness_secs` in your `TollboothConfig`
3. Redeploy your service

### tollbooth-dpyc 0.1.20: NeonVault — Serverless Postgres Persistence (2026-02-23)

**Affects:** All operators seeking faster, cheaper vault persistence

A new `NeonVault` backend is available as an alternative to `TheBrainVault`. It uses [Neon](https://neon.tech) serverless Postgres via their SQL-over-HTTP API — no new dependencies beyond the existing httpx requirement.

**Performance:** NeonVault averages ~32ms per store/fetch (single HTTP round-trip), compared to TheBrainVault's 200-400ms per store and 150-250ms per fetch (multiple hops through TheBrain's cloud API). That's a **5-8x speedup** on the write path and **5-7x on reads**.

Key features:
- **ACID persistence** with optimistic concurrency control (version-guarded UPDATE, UPSERT fallback)
- **Append-only transaction journal** for audit snapshots
- **Zero new dependencies** — uses httpx (already required) and Neon's HTTP endpoint
- **Idempotent schema migration** via `ensure_schema()` on startup
- **Full `VaultBackend` protocol** — drop-in replacement for `TheBrainVault`

**No action required** — `TheBrainVault` continues to work. Operators who want the performance improvement can switch by constructing `NeonVault(database_url=...)` and passing it to `LedgerCache`. Requires a free Neon account and a Postgres connection string.

### tollbooth-dpyc 0.1.16: Tranche-Based Credit Expiration (2026-02-22)

**Affects:** All operators and Authorities

Credits are now stored as ordered tranches with optional TTL-based expiration. Key changes:

- **FIFO consumption**: debits draw from the oldest non-expired tranche first
- **Per-tier TTL**: tier config JSON supports `credit_ttl_seconds` per tier (default 7 days for operators)
- **Authority balances never expire**: Authorities pass `default_credit_ttl_seconds=None`
- **Compensating tranches for rollback**: rollbacks create a new never-expiring tranche instead of modifying old ones
- **Schema v4**: no backward compatibility with v1-v3 ledgers (fresh ledger on old schema)
- **No re-seeding**: users who let credits expire must purchase new ones

**Minimum version bumped to 0.1.16** — tranche-based `UserLedger` is now required. `balance_api_sats` is a computed property (sum of non-expired tranches), not a stored field.

**Action required:**
1. Update `tollbooth-dpyc` to >= 0.1.16
2. Add `credit_ttl_seconds` to your config if you want non-default expiration (default: 604800 = 7 days; `None` = never)
3. Redeploy your service

### Version Diagnostic Endpoints Across All Services (2026-02-22)

**Affects:** All DPYC ecosystem services

All three MCP services now expose a free `service_status()` tool that reports software versions and runtime info. This enables programmatic version agreement verification across the ecosystem without incurring charges.

- **dpyc-oracle** 0.1.1: reports dpyc_oracle, python, fastmcp, httpx, nostr_sdk versions
- **tollbooth-authority** 0.1.1: reports tollbooth_authority, tollbooth_dpyc, fastmcp, python versions
- **thebrain-mcp** (existing): reports versions via `btcpay_status`

**No action required** — the new tool is automatically available after redeployment.

### dpyc-oracle 0.1.1: Nostr Signature-Based Citizenship Onboarding (2026-02-22)

**Affects:** New community members

The Oracle now supports self-service citizenship onboarding via Nostr Schnorr signature verification. Two new tools:

- `request_citizenship(npub, display_name)` — issues a challenge nonce
- `confirm_citizenship(npub, challenge_id, signed_event_json)` — verifies the signature and commits membership directly to `main`

Citizens are admitted instantly after proving npub ownership. No PR review delay. The `citizen` role has been added to the registry schema and governance documents.

**Action required:** None for existing members. New citizens can onboard via any Claude conversation connected to the Oracle.

### tollbooth-dpyc 0.1.15: Soft-Delete Vault Operations (2026-02-22)

**Affects:** All operators using TheBrainVault

`TheBrainVault` now provides `soft_delete_member()` which avoids TheBrain's slow `DELETE /thoughts` endpoint that leaves ghost entries in the Azure-cached graph for hours. Soft-deleted thoughts are unlinked, renamed to `DELETED <id>`, annotated with a reason, and optionally moved to a Trash Can thought.

Also adds `_update_thought`, `_delete_link`, and `_create_link` API helpers. Constructor accepts optional `trash_thought_id` for trash-can routing.

**Minimum version bumped to 0.1.14** — child-based vault discovery is now required (link-label discovery removed).

**Action required:**
1. Update `tollbooth-dpyc` to >= 0.1.15
2. Redeploy your service

### Authority Operators: Redeploy for npub-Primary Identity (2026-02-21)

**Affects:** tollbooth-authority >= 0.1.1, thebrain-mcp >= 1.0.0

The Authority now enforces npub-primary identity for all operator registrations and certificate issuance. Operators must re-register with their correct DPYC npub if they previously registered with a Horizon user ID.

**Action required:**
1. Update `tollbooth-dpyc` to >= 0.1.11 (vault consolidation)
2. Redeploy your Authority or Operator service
3. Re-register with `register_operator(npub=...)` if your registration predates this change

### Vault Consolidation Complete (2026-02-21)

**Affects:** tollbooth-dpyc 0.1.11, thebrain-mcp 1.0.0

The `TheBrainVault` implementation is now canonical in `tollbooth-dpyc`. Both the Authority and Personal Brain services share the same vault library. The old `PersonalBrainVault` in thebrain-mcp has been removed.

**Action required:** No action for most operators. If you maintained a custom vault integration, migrate to `tollbooth.vaults.thebrain.TheBrainVault`.

## Resolved Advisories

### E2E Trust Chain Proven (2026-02-19)

The complete Tollbooth trust chain has been verified end-to-end:
- Authority funded via Lightning
- `certify_credits` (formerly `certify_purchase`) issues Ed25519-signed JWT certificates
- `purchase_credits` validates certificates and creates invoices for net amount
- Anti-replay JTI tracking operational

No action required — this is an informational milestone.

## How Advisories Work

This file is maintained in the [dpyc-community](https://github.com/lonniev/dpyc-community) repository. The [DPYC Oracle](https://github.com/lonniev/dpyc-oracle) fetches it live via its `network_advisory()` tool. Updates happen via PR — no Oracle redeploy needed.

To check advisories programmatically, call the Oracle's `network_advisory()` or `network_versions()` tools.
