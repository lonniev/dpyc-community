# How to Add a New Authority

The path from "I want to certify Operators" to a live, registered Authority MCP.

## 1. Identity

Generate a Nostr keypair for the Authority. Keep the `nsec` in a vault you trust.

```bash
nak key generate
```

## 2. Region & Sponsor

- Pick a Neon Postgres region **distinct from your sponsor Authority's**. Geographic separation is what your tenants pay your cert fee for.
- Pick a sponsor Authority. Default: the DPYC Prime Authority. Alternatives: any registered Authority willing to certify you.

## 3. Workspace

- Scaffold from [`lonniev/tollbooth-authority`](https://github.com/lonniev/tollbooth-authority) into a new GitHub repo.
- Edit `pyproject.toml`, `fastmcp.json`, `src/tollbooth_authority/server.py` for your name and region.
- Make sure `fastmcp.json` lists only **two** required secrets — `TOLLBOOTH_NOSTR_OPERATOR_NSEC` and `NEON_DATABASE_URL`. BTCPay credentials arrive later via Secure Courier.
- Push to GitHub.

## 4. Registry

- Add `members/authorities/{your_npub}.json` to [`lonniev/dpyc-community`](https://github.com/lonniev/dpyc-community).
- Set `upstream_authority_npub` to your sponsor's npub.
- Set `services[0].url` to your future Horizon URL (`https://{repo-name}.fastmcp.app/mcp`).
- Open a PR or commit directly if you have bypass permission.

## 5. Infrastructure

- Provision a Neon project in your chosen region. Copy the **pooled** `NEON_DATABASE_URL`.
- Provision (or share) a BTCPay store scoped to this Authority.
- Deploy the GitHub repo to Prefect Horizon (`fastmcp.cloud`):
  - Connect the repo
  - Set the two secrets from step 3
  - Entrypoint: `src/tollbooth_authority/server.py:mcp`

## 6. Secure Courier — Deliver BTCPay

After Horizon shows the service live, from any MCP client (Pricing Studio, Claude Desktop, Claude Code):

1. `request_credential_channel` against your own Authority's MCP
2. Reply via Nostr DM with `{btcpay_host, btcpay_api_key, btcpay_store_id}` as JSON
3. `receive_credentials` to vault them encrypted at rest

## 7. Self-Registration Challenge-Response

With your nsec in Pricing Studio's Keychain (or any client that can sign Nostr DMs):

1. Call `register_authority_npub(your_npub)` on your own Authority's MCP
2. Sign the challenge DM the parent sends back
3. Call `confirm_authority_claim(your_npub)` — parent verifies and approves
4. Call `check_authority_approval(your_npub)` — on success, you're trusted by your parent

Pricing Studio's `ClaimAuthoritySheet` orchestrates all four steps.

## 8. Pre-Fund Cert-Fee Balance

Every cert your Authority issues to an Operator deducts a small fee from your pre-funded balance with your sponsor. Top up:

1. Against your sponsor Authority's MCP: `purchase_credits(amount_sats, npub=your_authority_npub)`
2. Pay the Lightning invoice
3. Your Authority can now certify Operators

## Reference deployments

| Authority | Sponsor | Neon region |
|---|---|---|
| [Lonnie-Authority](https://github.com/lonniev/tollbooth-authority) | Prime | `aws-us-east-1` |
| [NorthAmerica](https://github.com/lonniev/tollbooth-authority-northamerica) | Prime | `aws-us-west-2` |
| [NewEngland](https://github.com/lonniev/tollbooth-authority-newengland) | NorthAmerica | `aws-us-east-1` |
