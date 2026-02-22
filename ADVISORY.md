# DPYC Network Advisory

> Last updated: 2026-02-22

## Current Advisories

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
- `certify_purchase` issues Ed25519-signed JWT certificates
- `purchase_credits` validates certificates and creates invoices for net amount
- Anti-replay JTI tracking operational

No action required — this is an informational milestone.

## How Advisories Work

This file is maintained in the [dpyc-community](https://github.com/lonniev/dpyc-community) repository. The [DPYC Oracle](https://github.com/lonniev/dpyc-oracle) fetches it live via its `network_advisory()` tool. Updates happen via PR — no Oracle redeploy needed.

To check advisories programmatically, call the Oracle's `network_advisory()` or `network_versions()` tools.
