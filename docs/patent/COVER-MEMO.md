# Patent Submission Package — Cover Memo

**From**: Lonnie VanZandt, Inventor
**Date**: April 2026
**Re**: Provisional Patent Application — Tollbooth DPYC Economic Architecture

**Title**: System and Method for Pre-Funded Balance Monetization of Tool-Based APIs
with Composable Constraint Pricing, Hierarchical Trust Chains,
Cryptographic Identity, and Network Governance

---

## What This Package Contains

| File | Purpose |
|------|---------|
| `SB16-FILLED.pdf` | PTO/SB/16 Provisional cover sheet (filled) |
| `SB15A-FILLED.pdf` | PTO/SB/15A Micro entity certification (filled) |
| `PROVISIONAL-SPEC-DRAFT.pdf` | Full specification in USPTO format (35 pages) |
| `REFERENCE-NUMERAL-SCHEDULE.pdf` | Reference numerals for FIGS. 1-7 (6 pages) |
| `PATENT-FIGURES-ALL.pdf` | Patent drawings — FIGS. 1-6 (6 sheets, B&W, Letter) |
| `FILING-PACKAGE.pdf` | Consolidated filing PDF (all of the above) |

### Patent Figures

| Figure | Description |
|--------|-------------|
| FIG. 1 | System architecture — Authority → Operator → Consumer trust chain |
| FIG. 2 | Pre-funded balance lifecycle with intentional demurrage |
| FIG. 3 | Constraint Engine evaluation pipeline |
| FIG. 4 | Trust chain certification flow with Schnorr signatures |
| FIG. 5 | Secure Courier credential exchange via Nostr relay |
| FIG. 6 | Network governance data flow |

## Three Principal Innovations (over known pre-funded balance architectures)

1. **Intentional Demurrage** — All credits expire. Mandatory tranche expiration
   prevents the system from becoming a bank, asset storehouse, or custodial wallet.
   Operators never hold open-ended financial obligations. Structurally incapable of
   functioning as a VASP.
2. **Composable Constraint Engine with AI-Assisted Deployment** — Pipeline of
   named pricing constraints (temporal, surge, supply, promotional, loyalty, custom
   expression) runtime-configurable via AI-conducted structured interviews with
   schema validation, adversarial review, and cryptographically authenticated
   deployment to live MCP endpoints.
3. **Secure Courier Credential Exchange** — Out-of-band, human-in-the-loop
   credential delivery via NIP-44 encrypted Nostr DMs with anti-replay poison nonces
   (Interlock Protocol), timestamp freshness (Wide-Mouth Frog), and destructive
   relay reads. No email, no OAuth, no PII.

## Six Claim Families

1. **Pre-Funded Balance with Intentional Demurrage** — Consumers pre-fund api_sats
   via Lightning; tool invocations deduct from balance; credits expire by design.
2. **Composable Constraint Engine** — Pipeline of pricing constraints (temporal,
   supply, rate-limit, surge, promotional, custom expression) producing final price.
   Runtime-configurable, AI-assisted design and deployment.
3. **Hierarchical Trust Chain** — Authority certifies Operator purchases via Schnorr
   signatures; each layer uses same protocol (self-similar / fractal pattern).
4. **Nostr-Based Identity + Secure Courier** — npub as universal ID; Secure Courier
   credential exchange via NIP-44/NIP-17 encrypted DMs with anti-replay protection.
5. **Network Governance** — GitHub-native registry under version control; economic
   defense through network effects rather than proprietary code.
6. **AI-Assisted Pricing Campaign Design** — Structured six-stage AI interview
   co-designs pricing models with Operators; client-side pipeline validation against
   constraint schema; multi-provider adversarial second opinion; NIP-98-authenticated
   deployment to live MCP endpoints. Community-managed system prompts.

## Prior Art Timeline

- **Feb 16, 2026**: GPG-signed tag `v1.0.0-prior-art` on `thebrain-mcp` repo
- **Feb 17, 2026**: Repository made public; README with patent notice live
- **Grace period expiry**: ~Feb 17, 2027 (AIA one-year grace period)
- **Filed**: April 2026 as provisional ($65 micro-entity)

## Key Prior Art (Acknowledged and Distinguished)

**Pre-funded credit balances** are acknowledged as known prior art in the
specification. Cloud API providers (Google, OpenAI, Anthropic), billing platforms
(Lago, Orb), and MPP (Stripe/Tempo, March 2026) implement prepaid credit models.
The invention does not claim novelty in the abstract concept of pre-funded balance
deduction. Rather, the novel contributions are: (a) intentional demurrage preventing
VASP/banking classification, (b) composable constraint engine with AI-assisted
deployment, and (c) Secure Courier credential exchange.

**Per-request payment protocols** (distinguished by architecture):
- **L402** (Lightning Labs, 2020): Challenge-response per request, Macaroons, no balance model, no demurrage, no constraints
- **x402** (Coinbase, 2025): Challenge-response per request, USDC stablecoins, centralized Facilitator, no demurrage
- **PaidMCP** (Alby, 2025): Lightning + NWC + MCP tools, per-request payment
- **Sats4AI**: L402-based MCP marketplace, per-request

**MCP monetization platforms** (distinguished by missing components):
- **MCPize, PayMCP, Masumi, xpay.sh**: No composable constraints, no trust chain, no Nostr identity, no demurrage

**Prior art search results** filed separately in `PRIOR-ART-PATENT-SEARCH.md` and
`PRIOR-ART-NON-PATENT-SEARCH.md`. Closest patent hit: Pappas US20260087492A1
(pre-funded AI agent balances, Sep 2025) — blockchain-generic, no Lightning, no
constraints, no trust chain. Three claim families (4, 5, 6) have zero prior art.

## Alice/Mayo Considerations

Claims 1-3 are strongest for surviving abstract-idea scrutiny — they describe specific
technical processes with specific protocol interactions (Lightning Network BOLT-11
invoices, Schnorr signature verification, constraint pipeline evaluation with defined
composition rules). Claim 6 adds a strong machine-or-transformation hook: the AI
interview process transforms unstructured Operator intent into validated, schema-
conformant pricing models deployed via cryptographically authenticated MCP tool calls.
Claims 4-5 strengthen overall disclosure and provide additional inventive steps.

## Open Source Strategy

All code is Apache License 2.0. The patent grant in Section 3 of Apache 2.0 provides
defensive protection: licensees receive a patent grant that terminates if they initiate
patent litigation against the licensor. The patent filing protects against third parties
(e.g., Coinbase/x402) patenting substantially similar methods.

## Inventor Contact

Lonnie VanZandt
205 Ridgeline Road, Panton, Vermont 05491

## Disclaimer

This draft was prepared by the inventor with AI assistance (Claude, Anthropic).
It requires review and revision by a registered patent attorney or agent before
filing with the USPTO.
