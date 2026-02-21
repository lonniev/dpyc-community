# DPYP — DPYC Protocol Specifications

DPYP (DPYC Protocol) documents define the wire-format contracts between Authorities and Operators in the Tollbooth trust chain. Each spec has a unique identifier embedded in JWT certificates so both sides can detect incompatibility at runtime.

## Naming Convention

Identifiers follow the pattern: `dpyp-NN-slug`

- **`dpyp`** — prefix (DPYC Protocol)
- **`NN`** — two-digit sequence number, zero-padded
- **`slug`** — lowercase hyphenated description

Examples: `dpyp-01-base-certificate`, `dpyp-02-chained-authority`

## Active Protocols

| Identifier                   | Status | Description                  |
|------------------------------|--------|------------------------------|
| `dpyp-01-base-certificate`   | Active | Base JWT certificate schema  |

## NIP-78 Relay Discovery

Protocol specs are also published as [NIP-78](https://github.com/nostr-protocol/nips/blob/master/78.md) application-specific data events on Nostr relays. This enables decentralized discovery — any client can query for active protocols without hitting GitHub.

**Event structure:**

- Kind: `30078` (parameterized replaceable)
- `d` tag: protocol identifier (e.g., `dpyp-01-base-certificate`)
- Additional tags: `dpyp-version`, `status`, `repo`, `spec`
- Content: human-readable summary of the protocol

**Query example:**

```json
{"kinds": [30078], "#d": ["dpyp-01-base-certificate"]}
```

**Relays:** `wss://relay.damus.io`, `wss://nos.lol`

**Tooling:** [pynostr](https://github.com/holgern/pynostr) for Python. See `scripts/publish_dpyp.py` for the publishing script.

Note: NIP-78 discovery is an evolution path for the protocol registry. It is not a runtime dependency — Operators and Authorities use the `dpyc_protocol` JWT claim for version negotiation, not relay queries.
