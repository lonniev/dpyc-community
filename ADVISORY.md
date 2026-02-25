# DPYC Network Advisory

> Last updated: 2026-02-25

## Current Advisories

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
