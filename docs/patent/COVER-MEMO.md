# Patent Submission Package — Cover Memo

**From**: Lonnie VanZandt, Inventor
**Date**: March 2026
**Re**: Provisional Patent Application — Tollbooth DPYC Economic Architecture

---

## What This Package Contains

| File | Purpose |
|------|---------|
| `PROVISIONAL-SPEC-DRAFT.md` | Full specification draft in USPTO format (Title, Background, Summary, Detailed Description, Abstract, Appendices) |
| `fig1-system-architecture.mermaid` | FIG. 1 — System architecture (Authority → Operator → Consumer) |
| `fig2-balance-lifecycle.mermaid` | FIG. 2 — Pre-funded balance lifecycle |
| `fig3-constraint-engine.mermaid` | FIG. 3 — Constraint Engine evaluation pipeline |
| `fig4-certification-flow.mermaid` | FIG. 4 — Trust chain certification flow |
| `fig5-secure-courier.mermaid` | FIG. 5 — Secure Courier credential exchange |
| `fig6-governance-flow.mermaid` | FIG. 6 — Network governance data flow |

Mermaid diagrams can be rendered at https://mermaid.live or converted to
formal patent figures by a draftsperson.

## Five Claim Families

1. **Pre-Funded Balance Monetization** — Consumers pre-fund api_sats via Lightning;
   tool invocations deduct from balance. No per-request payment negotiation.
2. **Composable Constraint Engine** — Pipeline of pricing constraints (temporal,
   supply, rate-limit, surge, promotional, custom expression) producing final price.
3. **Hierarchical Trust Chain** — Authority certifies Operator purchases via Schnorr
   signatures; each layer uses same protocol (self-similar / fractal pattern).
4. **Nostr-Based Identity** — npub as universal ID; NIP-44/NIP-17 encrypted
   credential exchange; signature-based citizenship verification.
5. **Network Governance** — GitHub-native registry under version control; economic
   defense through network effects rather than proprietary code.

## Prior Art Timeline

- **Feb 16, 2026**: GPG-signed tag `v1.0.0-prior-art` on `thebrain-mcp` repo
- **Feb 17, 2026**: Repository made public; README with patent notice live
- **Grace period expiry**: ~Feb 17, 2027 (AIA one-year grace period)
- **Filing target**: Mid-2026 as provisional (~$320 micro-entity)

## Key Prior Art to Distinguish

- **L402** (Lightning Labs, 2020): Challenge-response per request, Macaroons, no balance model
- **x402** (Coinbase, 2025): Challenge-response per request, USDC stablecoins, centralized Facilitator
- **MCP platforms** (MCPize, PayMCP, Masumi, etc.): Traditional payment rails, no constraint engine, no trust chain

None implements pre-funded balances, composable constraints, self-similar trust chains,
Nostr identity, or network governance. The combination is novel.

## Alice/Mayo Considerations

Claims 1-3 are strongest for surviving abstract-idea scrutiny — they describe specific
technical processes with specific protocol interactions (Lightning Network BOLT-11
invoices, Schnorr signature verification, constraint pipeline evaluation with defined
composition rules). Claims 4-5 strengthen overall disclosure and provide additional
inventive steps.

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
