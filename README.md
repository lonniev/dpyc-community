# DPYC Honor Chain

> **This registry:** [`github.com/lonniev/dpyc-community`](https://github.com/lonniev/dpyc-community)

**Membership registry and governance for the Don't-Pester-Your-Customer Tollbooth community.**

**[Read the DPYC Creed](https://github.com/lonniev/dpyc-community/blob/main/CREED.md)** — our founding declaration of values.

## What is DPYC?

**Don't Pester Your Customer** — a philosophy for API monetization using pre-funded Bitcoin Lightning balances instead of KYC, stablecoins, or per-request payment negotiation.

Customers fund their balance once with a Lightning payment, then use API services without interruption. No credit cards. No identity verification. No payment popups mid-session. Just sats in, service out.

## Why Tollbooth?

Tollbooth monetizes **complete business information** — full MCP tool responses — not raw REST data fragments. A single Tollbooth-metered tool call delivers a ready-to-use answer that would otherwise require assembling dozens of individual API calls.

**Fewer round-trips, no interruptions.** Pre-funded Lightning balances mean each tool call is a single HTTP request. Protocols like [x402](https://github.com/AIM-Intelligence/x402) and [L402](https://docs.lightning.engineering/the-lightning-network/l402) take a different approach — gating individual REST endpoints with per-request payment challenges (402 → pay invoice → retry). That pattern works well for simple resource access, but adds 6+ HTTP round-trips per request and interrupts agent workflows with payment redirects.

**For AI agents:** your tool chain will never be interrupted by payment ceremonies. Fund once, call tools, get answers.

| | Tollbooth (MCP) | x402 / L402 (REST) |
|---|---|---|
| **What's metered** | Complete tool responses (business information) | Individual REST endpoints (data fragments) |
| **Round-trips per call** | 1 (pre-funded balance) | 6+ (challenge → pay → retry) |
| **Agent experience** | Seamless — no mid-session interruptions | Payment redirects between calls |
| **Identity** | Nostr npub (no KYC) | Varies by implementation |

x402 and L402 are respected approaches solving real problems in HTTP-native monetization. Tollbooth operates at a different layer — the MCP tool layer — where the unit of value is a complete answer, not a data fragment.

## What is the Honor Chain?

The DPYC Honor Chain is a voluntary community of Tollbooth Operators and Authorities, organized as a **Network Society** in the [Balaji Srinivasan tradition](https://thenetworkstate.com/). Members agree to:

1. **Use BTC and Lightning** for all commerce within the ecosystem
2. **Avoid saving customer PII** — especially financial data (the DPYC philosophy)
3. **Properly identify their upstream Tollbooth Authority** via their Nostr npub
4. **Honor their Authority's tax rate** as the cost of participating in the chain
5. **Accept community governance** including member banning for violations

## How It Works

**Identity** is a [Nostr](https://nostr.com/) keypair. Your `npub` is your member ID everywhere in the ecosystem.

**The registry** is [`members.json`](https://github.com/lonniev/dpyc-community/blob/main/members.json) in this repository. It is the source of truth for member standing. When a Tollbooth Authority certifies a purchase, it checks this registry to verify the operator's `npub` is active.

**Governance** uses GitHub's native tools — PRs for membership changes, Issues for ban proposals, branch protection for integrity. Git's Merkle tree provides a tamper-evident audit trail.

### Honor Chain Structure

```
Prime Authority (Lonnie VanZandt)
  npub1l94pd4qu4eszrl6ek032ftcnsu3tt9a7xvq2zp7eaxeklp6mrpzssmq8pf
  |
  +-- thebrain-mcp (Operator)
  |     npub1y20qa7d3ddmh6730hdr0u0r08zys4p7pyk30uhur9edx4d88q4zqnr3q2h
  |
  +-- Authority A (registered DPYC member)
  |     +-- Operator A1
  |     +-- Operator A2
  |     +-- Sub-Authority A-sub
  |           +-- Operator A-sub-1
  ...
```

Value flows from **actual API consumption at the edges**, not from recruitment. Each Authority collects a small tax from its Operators, motivating them to vet onboarding, police downstream, and maintain standing. This is a **franchise model**, not MLM.

## How to Join

1. **Generate a Nostr keypair** — use any Nostr client, or:
   ```bash
   pip install nostr-sdk
   python -c "from nostr_sdk import Keys; k = Keys.generate(); print(f'npub: {k.public_key().to_bech32()}'); print(f'nsec: {k.secret_key().to_bech32()}')"
   ```

2. **Find a sponsoring Authority** — an existing Authority in the Honor Chain who will vouch for you.

3. **Your Authority submits a PR** adding your `npub` to [`members.json`](https://github.com/lonniev/dpyc-community/blob/main/members.json) with your role, services, and their npub as your `upstream_authority_npub`.

4. **PR reviewed and merged** — the CI workflow validates the registry, and an Authority with repo access approves.

## How Banning Works

1. **Issue opened** on this repo with evidence of the violation
2. **Community discussion** — 72-hour period for Authorities to weigh in
3. **PR submitted** changing the member's `status` to `"banned"` with a `ban_reason` linking the Issue
4. **Banned members** retain their record (transparency) but can no longer transact through the Honor Chain
5. **Appeals** via new Issue referencing the original ban — community review, restore PR if upheld

See [GOVERNANCE.md](https://github.com/lonniev/dpyc-community/blob/main/GOVERNANCE.md) for the full governance process.

## Related Repositories

| Repository | Purpose |
|-----------|---------|
| **[dpyc-community](https://github.com/lonniev/dpyc-community)** | **This repo — Honor Chain registry and governance** |
| [dpyc-oracle](https://github.com/lonniev/dpyc-oracle) | Free community concierge MCP — membership, governance, onboarding |
| [tollbooth-dpyc](https://github.com/lonniev/tollbooth-dpyc) | Operator-side Python library for MCP monetization |
| [tollbooth-authority](https://github.com/lonniev/tollbooth-authority) | Authority-side certification and tax collection |
| [thebrain-mcp](https://github.com/lonniev/thebrain-mcp) | First Tollbooth Operator — TheBrain MCP Server |

## Built On

- [Nostr](https://nostr.com/) — decentralized identity and social protocol
- [Bitcoin / Lightning Network](https://lightning.network/) — payments
- [BTCPay Server](https://btcpayserver.org/) — self-hosted payment processing
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) — AI tool interoperability
- [GitHub](https://github.com/) — governance and tamper-evident registry

## Further Reading

[The Phantom Tollbooth on the Lightning Turnpike](https://stablecoin.myshopify.com/blogs/our-value/the-phantom-tollbooth-on-the-lightning-turnpike) — the full story of how we're monetizing the monetization of AI APIs.

## License

Apache License 2.0 — see [LICENSE](https://github.com/lonniev/dpyc-community/blob/main/LICENSE) for details.
