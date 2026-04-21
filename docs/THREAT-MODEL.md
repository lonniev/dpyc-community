# DPYC Ecosystem Threat Model

**Framework:** STRIDE + Data Flow Diagrams  
**Version:** 1.0  
**Date:** 2026-04-20  
**Scope:** All DPYC Honor Chain components — SDK, Operators, Authority, Oracle, external dependencies  
**Classification:** Public (no secrets — this document references architecture, not credentials)

---

## 1. System Overview

DPYC is a federated micropayment network for MCP tool monetization. Identity is a Nostr keypair (npub/nsec). Payment is Bitcoin Lightning. Storage is Neon Postgres with field-level encryption. Transport is SSE over HTTPS via FastMCP Cloud.

### 1.1 Actor Profiles

| Actor | Identity | Trust Level | Secrets Held | Threat Posture |
|-------|----------|-------------|--------------|----------------|
| **Patron** | npub + nsec | Untrusted (external) | nsec, API credentials (vaulted) | May be malicious, automated, or compromised |
| **Operator** | npub + nsec | Semi-trusted (registered) | nsec (env), BTCPay key (vault), Authority npub | Trusted to run service; nsec compromise = full tenant breach |
| **Authority** | npub + nsec | Trusted (certified) | nsec (env), Neon URL, operator ledgers | Certificate forgery if nsec compromised |
| **First Curator** | npub + nsec | Root of trust | nsec, authority approval power | Entire Honor Chain compromise if nsec lost |
| **AI Agent** | Delegated patron session | Untrusted | Session-scoped proof cache | All tool arguments treated as adversarial input |
| **Anonymous** | None | Untrusted | None | Can call Oracle (free); blocked from paid tools |

### 1.2 External Dependencies

| Dependency | Role | Trust Model |
|-----------|------|-------------|
| Nostr Relays | DM transport, event gossip | Untrusted — all events are signed; relays see metadata only |
| BTCPay Server | Lightning invoice creation/settlement | Untrusted — API key auth; no cryptographic settlement proof at MCP layer |
| Neon Postgres | Persistent vault storage | Untrusted for plaintext — field-level AES-256-GCM encryption; Neon sees ciphertext only |
| FastMCP Cloud | SSE transport, OAuth tenant | Partially trusted — TLS + OAuth; operator identity tokens held by platform |
| PyPI | SDK distribution | Untrusted — supply chain risk mitigated by pinned versions + Renovate |
| OpenTimestamps | Bitcoin-anchored audit proofs | Untrusted — append-only Merkle inclusion; verifiable independently |

---

## 2. Data Flow Diagrams

### 2.1 DFD Level 0 — System Context

```
                    ┌─────────────┐
                    │  Nostr      │
                    │  Relays     │
                    └──────┬──────┘
                           │ NIP-44 DMs
                           │ NIP-09 deletions
                           │ Kind-27235 proofs
    ┌──────────┐    ┌──────┴──────┐    ┌──────────────┐
    │  Patron  │───▶│  Operator   │───▶│  Authority   │
    │ (npub)   │◀───│  MCP Server │◀───│  MCP Server  │
    └──────────┘    └──────┬──────┘    └──────┬───────┘
         │                 │                   │
         │                 │                   │
    ┌────┴─────┐    ┌──────┴──────┐    ┌──────┴───────┐
    │ Lightning│    │  Neon       │    │  BTCPay      │
    │ Wallet   │    │  Postgres   │    │  Server      │
    └──────────┘    └─────────────┘    └──────────────┘
```

**Trust boundaries** (dashed lines in formal notation):
- **TB1:** Patron ↔ Operator MCP (public internet, SSE/HTTPS)
- **TB2:** Operator MCP ↔ Authority MCP (server-to-server, proof-gated)
- **TB3:** Operator MCP ↔ Neon Postgres (HTTPS SQL API, encrypted fields)
- **TB4:** Operator MCP ↔ Nostr Relays (WebSocket, signed events)
- **TB5:** Operator MCP ↔ BTCPay (HTTPS, token auth)
- **TB6:** Patron ↔ Nostr Relays (WebSocket, patron signs DMs)
- **TB7:** FastMCP Cloud ↔ Operator code (platform boundary)

### 2.2 DFD Level 1 — Patron Tool Call (Hot Path)

```
Patron ──[npub, proof, tool_kwargs]──▶ MCP Tool Entry
                                          │
                    ┌─────────────────────┤
                    ▼                     ▼
            verify_proof()         pricing_resolver
            (Schnorr sig,          (tool pricing,
             60s window,            constraint gates)
             replay check)               │
                    │                     ▼
                    ▼              debit_or_deny()
            proven_npub_cache      (ledger load,
            (session-bound,         AES-256-GCM
             vault-backed)          decrypt,
                                    optimistic
                                    concurrency)
                                         │
                                         ▼
                                   Domain Tool
                                   (business logic)
                                         │
                                         ▼
                                   Result ──▶ Patron
```

### 2.3 DFD Level 1 — Secure Courier Credential Flow

```
Operator ──[open_channel(patron_npub)]──▶ Nostr Relay
                                              │
                                    NIP-44 encrypted DM
                                    (credential template)
                                              │
                                              ▼
Patron ◀── receives DM in Nostr client ──────┘
   │
   │  Patron fills template, replies via Nostr client
   │  (patron nsec signs the reply)
   ▼
Nostr Relay ◀── NIP-44 encrypted reply
   │
   ▼
Operator ──[receive(sender_npub)]──▶ Poll relay
   │                                      │
   │                              Decrypt with
   │                              HKDF(operator_nsec,
   │                                   patron_npub)
   │                                      │
   │                              Validate against
   │                              CredentialTemplate
   │                                      │
   │                              ┌───────┴───────┐
   │                              ▼               ▼
   │                        VaultCipher      NIP-09
   │                        encrypt()        delete DM
   │                        (AES-256-GCM)    from relay
   │                              │
   │                              ▼
   │                        Neon Postgres
   │                        (ciphertext only)
   │
   ▼
Return to patron: {success, field_count}
(credentials NEVER echoed in response)
```

### 2.4 DFD Level 1 — Authority Certification

```
Operator ──[certify_credits(amount, proof)]──▶ Authority MCP
                                                    │
                                            verify_proof()
                                            (operator npub,
                                             Schnorr sig)
                                                    │
                                            compute fee:
                                            max(TAX_MIN,
                                                ceil(amount *
                                                TAX_RATE / 100))
                                                    │
                                            debit operator
                                            balance (Neon)
                                                    │
                                            sign certificate:
                                            Kind 30079 event
                                            (Schnorr, JTI,
                                             expiration)
                                                    │
                                                    ▼
                              Certificate ──▶ Operator ──▶ Patron
                              (publicly verifiable against
                               Authority npub)
```

---

## 3. STRIDE Threat Catalog

### 3.1 Spoofing

| ID | Threat | Target | Mitigation | Residual Risk |
|----|--------|--------|------------|---------------|
| S-1 | Attacker forges identity proof (kind-27235) | TB1: Patron ↔ Operator | Schnorr signature verification against claimed npub; 60-second validity window | None — Schnorr is unforgeable without nsec |
| S-2 | Attacker replays a valid proof | TB1 | Event ID recorded in `_consumed_proofs` with expiry; rejected on reuse | In-memory store — lost on cold restart. **Vault-backed proof cache mitigates but has a race window during restart.** |
| S-3 | Attacker impersonates Authority | TB2: Operator ↔ Authority | Certificate (kind 30079) verified against known Authority npub; JTI replay check | Operator must securely obtain Authority npub (currently config/env) |
| S-4 | Attacker spoofs BTCPay settlement | TB5: Operator ↔ BTCPay | API token authentication on BTCPay polling | **No cryptographic settlement proof** — if BTCPay API token is stolen, attacker can fake settlement status |
| S-5 | Rogue Nostr relay injects fake DMs | TB4/TB6 | All DMs are NIP-44 encrypted + signed; relay cannot forge patron's nsec signature | Relay can *withhold* DMs (censorship) but not forge them |
| S-6 | AI agent spoofs patron npub in tool args | TB1 | Proof required — agent cannot sign for a different npub without their nsec | Proof cache could be exploited if session ID is predictable (see S-8) |
| S-7 | Attacker registers with stolen npub | Oracle/Authority | Registration is idempotent; no secret is granted at registration | Attacker gets a zero-balance ledger entry; useless without nsec to prove or fund |
| S-8 | Session ID prediction for proof cache hijack | TB7: FastMCP ↔ Operator | Session ID generated by FastMCP runtime (opaque) | **Depends on FastMCP session ID entropy** — if predictable, attacker could inherit cached proof |

### 3.2 Tampering

| ID | Threat | Target | Mitigation | Residual Risk |
|----|--------|--------|------------|---------------|
| T-1 | Modify patron balance in transit | TB3: Operator ↔ Neon | AES-256-GCM encryption (integrity tag); optimistic concurrency version column | Neon admin with DB access sees ciphertext only; cannot produce valid ciphertext without operator nsec |
| T-2 | Modify certificate claims | TB2 | Kind 30079 Schnorr signature covers all fields; any modification invalidates sig | None — Schnorr provides integrity |
| T-3 | Modify tool_kwargs after proof validation | TB1 | Proof binds to capability (tool name) but **not to specific kwargs** | **tool_kwargs are not signed** — attacker could replay proof with different arguments within the 60s window. Mitigated by event ID anti-replay. |
| T-4 | SQL injection via Neon HTTP API | TB3 | Parameterized queries in `NeonVault._execute()` | Dependent on correct parameterization in all vault methods |
| T-5 | Tamper with pricing model in Neon | TB3 | Pricing model loaded from Neon at runtime; encrypted if nsec provided | **If Neon credentials (connection string) are compromised**, attacker could alter pricing to zero-cost |
| T-6 | Modify DM content on relay | TB4/TB6 | NIP-44 ChaCha20-Poly1305 authenticated encryption; AEAD tag prevents tampering | None — AEAD provides integrity |

### 3.3 Repudiation

| ID | Threat | Target | Mitigation | Residual Risk |
|----|--------|--------|------------|---------------|
| R-1 | Patron denies making a purchase | Operator ledger | Ledger mutations recorded in Neon `transactions` table; Nostr audit events (kind-specific) | Patron could claim they didn't initiate the tool call; **no patron-signed receipt exists for individual tool calls** |
| R-2 | Operator denies receiving payment | Authority ledger | Authority's Neon ledger records all `certify_credits` calls with JTI + Schnorr certificate | Certificate is cryptographic proof of certification — non-repudiable |
| R-3 | Authority denies certifying credits | Operator | Certificate (kind 30079) is Schnorr-signed by Authority nsec — publicly verifiable | None — signature is non-repudiable |
| R-4 | Patron denies sending credentials via Courier | Operator | DM is signed by patron's nsec (Nostr event signature) | DM is deleted after receipt (NIP-09) — **original signed event is gone from relay; only vault ciphertext remains** |
| R-5 | Ledger history disputed | All | OpenTimestamps notarization anchors ledger snapshots to Bitcoin blockchain | OTS proves *existence at time* but not *completeness* — operator could omit entries before notarizing |

### 3.4 Information Disclosure

| ID | Threat | Target | Mitigation | Residual Risk |
|----|--------|--------|------------|---------------|
| I-1 | Nsec exposure in logs/responses | Operator runtime | CLAUDE.md absolute prohibition; `SecureCourier.receive()` strips credentials before return | Human error — a code change could accidentally log nsec. **No runtime scanner enforces this.** |
| I-2 | Nostr DM metadata leakage | TB4/TB6 | NIP-44 encrypts content; metadata (timestamp, sender npub, recipient npub) visible to relays | **Relays know who communicates with whom and when** — traffic analysis possible |
| I-3 | Neon connection string exposure | TB3/TB7 | Stored in env var; passed via HTTPS header | **If FastMCP Cloud env is compromised**, full DB access is possible (ciphertext only, but still) |
| I-4 | Credential template reveals expected fields | TB4 | Template sent in NIP-44 DM (encrypted) | Only patron and operator see it; but template structure is in source code (public repo) |
| I-5 | Timing side-channel on proof verification | TB1 | Schnorr verification is constant-time in secp256k1 library | Python-level timing may leak proof validity before full verification completes |
| I-6 | Balance inference from error messages | TB1 | `debit_or_deny` returns "Insufficient credit balance" without revealing exact balance | Attacker can binary-search balance by varying tool cost (if tool pricing varies by kwargs) |
| I-7 | BTCPay API key exposure | TB5 | Delivered via Secure Courier, encrypted at rest in Neon vault (AES-256-GCM, operator nsec-derived key) | **Requires operator nsec to decrypt** — vault compromise alone yields only ciphertext |
| I-8 | Credential card (ncred1) interception | Patron device | Bech32-encoded, encrypted with operator nsec-derived key | **If patron's device is compromised**, ncred1 is recoverable — but useless without operator's nsec to decrypt |

### 3.5 Denial of Service

| ID | Threat | Target | Mitigation | Residual Risk |
|----|--------|--------|------------|---------------|
| D-1 | Proof flooding (many valid proofs) | Operator runtime | `_consumed_proofs` cleanup every 120s; proof window is 60s | **Memory exhaustion** if attacker generates thousands of valid proofs (requires nsec, so self-DoS or compromised key) |
| D-2 | Tool call flooding (zero-balance patron) | Operator runtime | `debit_or_deny` rejects quickly on zero balance; constraint gates (SurgeConstraint) can throttle | **No IP-level rate limiting** at MCP layer — depends on FastMCP Cloud |
| D-3 | Neon unavailability | Vault/ledger | Operator returns "warming up, retry in 10-15s" — serverless cold start pattern | Extended Neon outage = full service outage; **no local cache fallback for ledger** |
| D-4 | Relay unavailability | Secure Courier | Vault-first fast path bypasses relay; `resolve_relays()` tries multiple relays | If all relays are down simultaneously, Courier onboarding fails (but existing sessions survive via vault) |
| D-5 | BTCPay unavailability | Payments | `BTCPayConnectionError` / `BTCPayTimeoutError` surfaced to patron | **Cannot purchase credits during outage** — existing balance continues to work |
| D-6 | JTI store memory growth | Authority | `_JTIStore._seen` dict grows with every certificate | **No TTL cleanup observed** — long-running Authority could accumulate unbounded JTI entries |
| D-7 | Adversarial tool_kwargs (large payloads) | Operator runtime | No explicit size limit on tool arguments at MCP layer | **FastMCP may impose limits**, but no DPYC-layer validation on argument size |

### 3.6 Elevation of Privilege

| ID | Threat | Target | Mitigation | Residual Risk |
|----|--------|--------|------------|---------------|
| E-1 | Patron calls operator-restricted tool | Operator runtime | `identity.category == "restricted"` requires proof signed by operator nsec specifically | None — patron's nsec cannot produce a valid proof for operator's npub |
| E-2 | Operator forges Authority certificate | TB2 | Certificate must be signed by Authority's nsec; operator only holds their own nsec | None — Schnorr is unforgeable |
| E-3 | Patron accesses another patron's session | Operator runtime | Proof cache bound to `(session_id, npub)` — different npub requires new proof | **If patron can predict/steal session ID** (see S-8), they inherit cached proof |
| E-4 | Lateral movement: compromised operator accesses other operators' Neon data | TB3 | Per-operator Postgres schema; LOGIN role per operator with ownership transferred | **If Neon connection string is shared** (misconfiguration), cross-tenant access possible |
| E-5 | AI agent escalates beyond patron's intent | TB1 | Proof is human-in-the-loop (patron must consciously approve); 1-hour TTL | **Within the 1-hour proof window**, AI agent acts with full patron authority on all tools |
| E-6 | OAuth2 collector can derive auth code decryption key | TB (Advocate) | Auth code encrypted with AES-256-GCM, key = `SHA-256(npub)` | Cipher upgraded from XOR to AES-256-GCM, but **key derivation unchanged** — npub is public, so collector (or anyone with Neon access) can derive the key and decrypt. Confidentiality depends on collector integrity, not cryptography. |

---

## 4. Attack Chains (Multi-Step Exploits)

### Chain 1: Operator Nsec Theft → BTCPay Token → Free Credits

1. Attacker obtains operator's nsec (compromised machine, leaked env var)
2. Attacker decrypts BTCPay API credentials from Neon vault (AES-256-GCM, nsec-derived key)
3. Attacker creates invoices via BTCPay API directly, marks them as settled
4. Attacker calls `check_payment` with the fake-settled invoice ID (S-4)
5. Authority credits the operator's balance with unearned sats
6. **Impact:** Unlimited free credits; Authority's Lightning wallet is not actually funded

**Severity:** Critical (but **prerequisite is nsec compromise**, which is already game-over for the operator)  
**Prerequisite:** Operator nsec theft  
**Mitigation:** Add cryptographic proof of Lightning settlement (e.g., preimage verification) as defense-in-depth; nsec compromise is the root cause

### Chain 2: Session ID Prediction → Proof Cache Hijack → Account Takeover

1. Attacker observes or predicts FastMCP session ID (S-8)
2. Attacker sends tool call with target patron's npub and the predicted session ID
3. If proof cache has a valid entry for `(session_id, target_npub)`, proof is waived (E-3)
4. Attacker calls paid tools on target patron's balance
5. **Impact:** Balance drain, unauthorized data access

**Severity:** High  
**Prerequisite:** Predictable session IDs  
**Mitigation:** Ensure FastMCP session IDs are cryptographically random; consider binding proof cache to additional entropy (IP, user-agent hash)

### Chain 3: Neon Connection String Leak → Pricing Manipulation → Zero-Cost Drain

1. Attacker obtains operator's Neon connection string (I-3)
2. Attacker modifies pricing model in Neon to set all tool costs to 0 (T-5)
3. Patron calls tools for free indefinitely
4. Operator's Authority balance is drained (tools execute but no revenue collected)
5. **Impact:** Financial loss to operator; service runs at a loss

**Severity:** High  
**Prerequisite:** Neon connection string compromise  
**Mitigation:** Encrypt pricing model at rest with operator nsec; sign pricing model with operator key and verify at load time

### Chain 4: OAuth2 Collector Compromise → Upstream API Takeover

1. Attacker compromises OAuth2 Collector advocate service or its Neon database (E-6)
2. Attacker derives AES-256-GCM key via `SHA-256(patron_npub)` — npub is public
3. Attacker decrypts stored auth codes and exchanges them for upstream access tokens
4. Attacker accesses upstream API (Schwab, etc.) as the patron
5. **Impact:** Full upstream API access; financial data exposure (Schwab), social media control (X/Twitter)

**Severity:** Critical  
**Prerequisite:** OAuth2 Collector service or database compromise  
**Note:** Cipher was upgraded from XOR to AES-256-GCM, but key derivation from public npub remains the weakness  
**Mitigation:** Replace `SHA-256(npub)` key derivation with NIP-44 asymmetric encryption using operator's public key; collector cannot decrypt

### Chain 5: Balance Inference + Surge Timing → Economic Griefing

1. Attacker probes `debit_or_deny` with varying tool costs to binary-search patron's balance (I-6)
2. Attacker times heavy tool calls during SurgeConstraint active periods to maximize cost multiplier
3. Attacker triggers tool calls that drain patron's balance at inflated prices
4. **Impact:** Patron's balance depleted faster than expected; economic griefing

**Severity:** Medium  
**Prerequisite:** Valid npub + proof; knowledge of surge pricing windows  
**Mitigation:** Rate-limit failed debit attempts per npub; avoid revealing balance-specific error distinctions

---

## 5. Risk Heat Map

```
              ┌─────────────────────────────────────────────┐
  Critical    │  E-6+Chain4                                   │
              │  (OAuth Collector — public key derivation)    │
              ├─────────────────────────────────────────────┤
  High        │  S-8+E-3     I-3+T-5      D-6   Chain1     │
              │  (Session)   (Neon leak)   (JTI) (nsec-gated) │
              ├─────────────────────────────────────────────┤
  Medium      │  I-2  I-6    D-2  D-7     R-1  R-4         │
              │  (metadata)  (flooding)    (repudiation)    │
              ├─────────────────────────────────────────────┤
  Low         │  I-4  I-5    T-3  I-8     D-1              │
              │  (template)  (kwargs)      (proof flood)    │
              └─────────────────────────────────────────────┘
               Spoofing/     Tampering/    Repudiation/
               EoP           InfoDisc      DoS
```

---

## 6. Secure Design Recommendations

### 6.1 Critical Priority

| Rec | Addresses | Action |
|-----|-----------|--------|
| **R-1** | E-6, Chain 4 | Replace `SHA-256(npub)` auth code encryption with NIP-44 asymmetric encryption using operator's public key; collector cannot decrypt |
| **R-2** | D-6 | Add TTL-based cleanup to `_JTIStore._seen` — evict entries older than max certificate lifetime |

### 6.1a Accepted Risks

| ID | Addresses | Rationale |
|----|-----------|-----------|
| **A-1** | S-4, Chain 1 | BTCPay settlement trust gap is accepted. Chain 1 requires operator nsec compromise, which is already game-over (vault decryption, identity spoofing, full tenant breach). Adding preimage verification is not practical — BTCPay (the payee) already knows the preimage, so asking it to prove its own honesty is circular. Patron-submitted preimage would work cryptographically but adds UX friction for negligible incremental security given the nsec prerequisite. |

### 6.2 High Priority

| Rec | Addresses | Action |
|-----|-----------|--------|
| **R-3** | S-8, E-3, Chain 2 | Audit FastMCP session ID entropy; consider binding proof cache to `(session_id, npub, client_fingerprint)` |
| **R-4** | I-3, T-5, Chain 3 | Sign pricing model with operator nsec at write time; verify signature at load time |
| **R-5** | S-2 | Persist `_consumed_proofs` to vault for cold-restart replay protection (or accept the ~60s race window) |
| **R-6** | I-1 | Add a runtime secret scanner — grep for nsec/key patterns in all outbound strings before they reach logs or responses |

### 6.3 Medium Priority

| Rec | Addresses | Action |
|-----|-----------|--------|
| **R-7** | D-2, D-7 | Add per-npub rate limiting at the MCP layer (token bucket or sliding window) independent of FastMCP Cloud |
| **R-8** | I-6, Chain 5 | Normalize error messages — return identical error for "insufficient balance" and "tool not found" to prevent balance probing |
| **R-9** | R-1 | Consider patron-signed receipts (kind event) for non-repudiable purchase records |
| **R-10** | R-4 | Retain Nostr DM event ID + signature hash in vault after NIP-09 deletion, as proof of credential delivery |
| **R-11** | I-2 | Document Nostr metadata exposure in patron onboarding materials; patrons should understand relay operators see DM graph |

---

## 7. Invariants to Monitor

These security invariants should be verified continuously (CI, runtime assertions, or periodic audit):

1. **Nsec never appears in logs, responses, or error messages**
2. **Every paid tool call passes through `debit_or_deny`** (no bypass path)
3. **Proof window never exceeds 60 seconds**
4. **Vault cipher key is derived from nsec via HKDF — never hardcoded**
5. **Certificate JTI is unique across the Authority's lifetime**
6. **Credentials are stripped from all Courier responses**
7. **DM deletion is attempted after every successful `receive()`**
8. **Neon queries are parameterized — no string interpolation**
9. **Each operator has a distinct Neon schema and LOGIN role**
10. **Proof cache TTL never exceeds 3600 seconds**

---

## Appendix A: STRIDE Category Reference

| Category | Question Asked | DPYC Primary Control |
|----------|---------------|---------------------|
| **S**poofing | Can an attacker pretend to be someone else? | Schnorr-signed Nostr proofs (kind-27235) |
| **T**ampering | Can an attacker modify data in transit or at rest? | AES-256-GCM field encryption + NIP-44 DM encryption |
| **R**epudiation | Can an actor deny performing an action? | Nostr audit trail + OpenTimestamps + Authority certificates |
| **I**nformation Disclosure | Can secrets or PII leak? | Vault encryption + credential stripping + env-only secrets |
| **D**enial of Service | Can an attacker degrade or block service? | Constraint gates + vault-first fallback + serverless retry |
| **E**levation of Privilege | Can an attacker gain unauthorized access? | Proof-gated ACL + session-bound caches + per-operator schemas |

## Appendix B: Notation

- **TB*N*:** Trust Boundary identifier
- **S/T/R/I/D/E-*N*:** STRIDE threat identifier
- **Chain *N*:** Multi-step exploit scenario
- **R-*N*:** Recommendation identifier
- **DFD:** Data Flow Diagram (textual Mermaid-compatible format)
- **Kind *N*:** Nostr event kind per NIP specification
