# DPYC Honor Chain

**Membership registry and governance for the Don't-Pester-Your-Customer Tollbooth community.**

**[Read the DPYC Creed](https://github.com/lonniev/dpyc-community/blob/main/CREED.md)** — our founding declaration of values.

## What is DPYC?

**Don't Pester Your Customer** — a philosophy for API monetization using pre-funded Bitcoin Lightning balances instead of KYC, stablecoins, or per-request payment negotiation.

Customers fund their balance once with a Lightning payment, then use API services without interruption. No credit cards. No identity verification. No payment popups mid-session. Just sats in, service out.

## What is the Honor Chain?

The DPYC Honor Chain is a voluntary community of Tollbooth Operators and Authorities, organized as a **Network Society** in the [Balaji Srinivasan tradition](https://thenetworkstate.com/). Members agree to:

1. **Use BTC and Lightning** for all commerce within the ecosystem
2. **Avoid saving customer PII** — especially financial data (the DPYC philosophy)
3. **Properly identify their upstream Tollbooth Authority** via their Nostr npub
4. **Honor their Authority's tax rate** as the cost of participating in the chain
5. **Accept community governance** including member banning for violations

## How It Works

**Identity** is a [Nostr](https://nostr.com/) keypair. Your `npub` is your member ID everywhere in the ecosystem.

**The registry** is [`members.json`](members.json) in this repository. It is the source of truth for member standing. When a Tollbooth Authority certifies a purchase, it checks this registry to verify the operator's `npub` is active.

**Governance** uses GitHub's native tools — PRs for membership changes, Issues for ban proposals, branch protection for integrity. Git's Merkle tree provides a tamper-evident audit trail.

### Honor Chain Structure

```
Prime Authority (Lonnie VanZandt)
  npub1z4j4sv8pe6utdkxxxclkzkpt58awpu50ar4dxt7p9gaxn9du4xzq64te4v
  |
  +-- thebrain-mcp (Operator)
  |     npub1h8t6wyvfvuccut2yt67n4aag699lt76x0lek5c8ygl5khnw02p3q7nvy90
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

3. **Your Authority submits a PR** adding your `npub` to [`members.json`](members.json) with your role, services, and their npub as your `upstream_authority_npub`.

4. **PR reviewed and merged** — the CI workflow validates the registry, and an Authority with repo access approves.

## How Banning Works

1. **Issue opened** on this repo with evidence of the violation
2. **Community discussion** — 72-hour period for Authorities to weigh in
3. **PR submitted** changing the member's `status` to `"banned"` with a `ban_reason` linking the Issue
4. **Banned members** retain their record (transparency) but can no longer transact through the Honor Chain
5. **Appeals** via new Issue referencing the original ban — community review, restore PR if upheld

See [GOVERNANCE.md](GOVERNANCE.md) for the full governance process.

## Related Repositories

| Repository | Purpose |
|-----------|---------|
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

Apache License 2.0 — see [LICENSE](LICENSE) for details.
