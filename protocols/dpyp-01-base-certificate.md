# DPYP-01: Base Certificate

| Field      | Value                                                                              |
|------------|------------------------------------------------------------------------------------|
| Identifier | `dpyp-01-base-certificate`                                                          |
| Status     | Active                                                                              |
| Author     | `npub1l94pd4qu4eszrl6ek032ftcnsu3tt9a7xvq2zp7eaxeklp6mrpzssmq8pf` (Prime Authority) |
| Created    | 2026-02-20                                                                          |
| Revised    | 2026-06-13 — Nostr-event certificate (supersedes the original Ed25519 JWT form)     |

## Summary

Defines the base certificate an Authority issues to attest a Tollbooth purchase order. The certificate is a **Schnorr-signed Nostr event** (kind 30079) that carries the purchase amount, the certification fee, and the resulting patron credit. Every certificate names the protocol it follows in its `dpyc_protocol` claim, and every Operator checks that claim against the protocols it understands before honoring the certificate.

> **Wire-format note:** The first revision of DPYP-01 specified a JWT signed with Ed25519. The live format is the Nostr event described here, signed with Schnorr/BIP-340. The identifier `dpyp-01-base-certificate` carries forward; the JWT form is retired.

## Event

| Property     | Value                                            |
|--------------|--------------------------------------------------|
| `kind`       | `30079` — NIP-33 parameterized replaceable event |
| `pubkey`     | The signing Authority's Nostr public key (hex)   |
| `created_at` | Issuance time (Unix epoch seconds)               |
| `sig`        | Schnorr / BIP-340 signature over the event       |

### Tags

| Tag          | Example                       | Meaning                                                                              |
|--------------|-------------------------------|--------------------------------------------------------------------------------------|
| `d`          | `["d", "<uuid>"]`             | Certificate ID (JTI) — the anti-replay key and the NIP-33 replaceable identifier      |
| `p`          | `["p", "<operator_pubkey>"]`  | The Operator the certificate is issued to (public key, hex)                            |
| `t`          | `["t", "tollbooth-cert"]`     | Marks the event as a Tollbooth certificate                                             |
| `L`          | `["L", "dpyc.tollbooth"]`     | NIP-32 label namespace                                                                 |
| `expiration` | `["expiration", "<unix>"]`    | NIP-40 expiration timestamp (Unix epoch seconds)                                      |

### Content

The event `content` is a compact JSON object:

| Claim           | Type   | Description                                            |
|-----------------|--------|--------------------------------------------------------|
| `dpyc_protocol` | string | Protocol identifier — `"dpyp-01-base-certificate"`     |
| `sub`           | string | Operator identity (npub or operator ID)                |
| `amount_sats`   | int    | Total purchase amount in satoshis                      |
| `fee_sats`      | int    | Certification fee deducted from the Operator's balance |
| `net_sats`      | int    | `amount_sats - fee_sats` — effective patron credit     |

Example `content`:

```json
{"sub":"npub1operator…","amount_sats":1000,"fee_sats":20,"net_sats":980,"dpyc_protocol":"dpyp-01-base-certificate"}
```

## Verification Rules

An Operator honors a certificate when every check below passes, in order:

1. **Structure** — the event parses as a valid Nostr event.
2. **Signature** — the Schnorr/BIP-340 signature is valid for the event.
3. **Signer** — `pubkey` matches the registered Authority's npub.
4. **Kind** — `kind` is `30079`.
5. **Expiration** — an `expiration` tag is present and lies in the future.
6. **Certificate ID** — a `d` tag (JTI) is present.
7. **Anti-replay** — the JTI is recorded; a JTI seen before within its TTL is rejected.
8. **Protocol** — `content.dpyc_protocol` is present and is one the Operator understands.

## Compatibility

- Authorities MUST keep the required tags and content claims stable; a breaking format change ships under a new DPYP identifier.
- Authorities MAY add optional tags or content claims at any time.
- Operators MUST ignore tags and claims they do not recognize (forward compatibility).
- Operators MUST honor only certificates whose `dpyc_protocol` they understand.

## Implementations

- **Authority (signing)**: [`tollbooth-dpyc`](https://github.com/lonniev/tollbooth-dpyc) — `authority/nostr_signing.py:AuthorityNostrSigner.sign_certificate_event()`
- **Operator (verifying)**: [`tollbooth-dpyc`](https://github.com/lonniev/tollbooth-dpyc) — `nostr_certificate.py:verify_nostr_certificate()`
