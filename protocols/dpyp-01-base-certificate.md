# DPYP-01: Base Certificate

| Field       | Value                          |
|-------------|--------------------------------|
| Identifier  | `dpyp-01-base-certificate`     |
| Status      | Active                         |
| Author      | `npub1l94pd4qu4eszrl6ek032ftcnsu3tt9a7xvq2zp7eaxeklp6mrpzssmq8pf` (Prime Authority) |
| Created     | 2026-02-20                     |

## Summary

Defines the base JWT certificate schema for Tollbooth purchase orders. Every Authority MUST include the `dpyc_protocol` claim in signed certificates, and every Operator MUST verify the claim matches a protocol it understands.

## JWT Claims

### Required

| Claim            | Type   | Description                                                |
|------------------|--------|------------------------------------------------------------|
| `sub`            | string | Operator identity (npub or legacy operator ID)             |
| `jti`            | string | Unique certificate ID (UUID) for anti-replay               |
| `iat`            | int    | Issued-at timestamp (Unix epoch seconds)                   |
| `exp`            | int    | Expiration timestamp (Unix epoch seconds)                  |
| `dpyc_protocol`  | string | Protocol identifier — MUST be `"dpyp-01-base-certificate"` |
| `amount_sats`    | int    | Total purchase amount in satoshis                          |
| `tax_paid_sats`  | int    | Tax deducted from operator balance                         |
| `net_sats`       | int    | `amount_sats - tax_paid_sats` — effective user credit      |

### Optional

| Claim             | Type   | Description                                      |
|-------------------|--------|--------------------------------------------------|
| `authority_npub`  | string | Nostr npub of the signing Authority              |

## Signature

Certificates MUST be signed with **Ed25519** (`EdDSA` algorithm in JWT header). The Authority's public key is distributed out-of-band via `operator_status` or hardcoded in `TollboothConfig`.

## Verification Rules

1. **Signature**: Verify EdDSA signature against the Authority's public key.
2. **Expiration**: Reject certificates where `exp < now`.
3. **Anti-replay**: Record `jti`; reject duplicates within the TTL window.
4. **Protocol**: Extract `dpyc_protocol`. Reject if missing or not in the Operator's understood set.

## Compatibility

- **Authorities** MUST NOT remove or rename required claims without publishing a new DPYP identifier.
- **Authorities** MAY add new optional claims at any time.
- **Operators** MUST ignore unknown claims (forward compatibility).
- **Operators** MUST reject certificates with an unrecognized `dpyc_protocol` value.

## Implementations

- **Authority**: [`tollbooth-authority`](https://github.com/lonniev/tollbooth-authority) — `certificate.py:create_certificate_claims()`
- **Operator SDK**: [`tollbooth-dpyc`](https://github.com/lonniev/tollbooth-dpyc) >= 0.1.8 — `certificate.py:verify_certificate()`
