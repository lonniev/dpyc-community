# Reference Numeral Schedule

All reference numerals used across FIGS. 1-7 are listed below.
The same element carries the same numeral in every figure where it appears.

## System Entities (100-series)

| Ref. | Element | Appears in FIG. |
|------|---------|-----------------|
| 100 | Pre-funded balance monetization system | 1 |
| 102 | Consumer / AI agent | 1, 2, 5 |
| 104 | Operator MCP service | 1, 2, 4 |
| 106 | Authority certification service | 1, 4, 6 |
| 108 | First Curator | 1 |
| 110 | Community registry (members.json) | 1, 4, 6 |
| 112 | Oracle service | 1, 5, 6 |
| 114 | Governance document | 1, 6 |
| 116 | OperatorRuntime (core protocol engine) | 1, 2, 3, 4 |
| 118 | register_standard_tools() | 1 |

## Settlement Layer (200-series)

| Ref. | Element | Appears in FIG. |
|------|---------|-----------------|
| 200 | BTCPay Server | 1, 2, 4 |
| 202 | Lightning Network | 1, 2 |
| 204 | Lightning invoice (BOLT-11) | 2, 4 |
| 206 | Payment settlement confirmation | 2 |

## Balance / Ledger (300-series)

| Ref. | Element | Appears in FIG. |
|------|---------|-----------------|
| 300 | Consumer credit ledger | 2, 3 |
| 302 | Credit tranche | 2 |
| 304 | api_sats credit units | 2 |
| 306 | Credit unit parity (1:1 sat-to-api_sat ratio) | 2 |
| 308 | FIFO deduction | 2, 3 |
| 310 | Tranche expiration (demurrage) | 2 |
| 312 | Purchase credits request | 2, 4 |
| 314 | Balance sufficiency check | 2, 3 |
| 316 | Tool invocation request | 2, 3 |
| 318 | Tool response | 2, 3 |

## Constraint Engine (400-series)

| Ref. | Element | Appears in FIG. |
|------|---------|-----------------|
| 400 | Constraint engine | 3 |
| 402 | Constraint pipeline | 3 |
| 404 | Constraint context object | 3 |
| 406 | Ledger snapshot | 3 |
| 408 | Patron identity | 3 |
| 410 | Environment snapshot | 3 |
| 412 | Constraint result | 3 |
| 414 | Price modifier | 3 |
| 416 | Temporal window constraint | 3 |
| 418 | Finite supply constraint | 3 |
| 420 | Periodic refresh constraint | 3 |
| 422 | Coupon constraint | 3 |
| 424 | Free trial constraint | 3 |
| 426 | Loyalty discount constraint | 3 |
| 428 | Bulk bonus constraint | 3 |
| 430 | Happy hour constraint | 3 |
| 432 | JSON expression constraint | 3 |
| 434 | Final price calculation | 3 |
| 436 | Price modifier accumulator | 3 |
| 438 | Surge pricing constraint | 3 |
| 440 | Expression constraint | 3 |
| 442 | Demand tracking (get_global_demand) | 3 |
| 444 | Auto-seed default pricing model | 3 |
| 446 | check_price standard tool | 3 |
| 448 | list_constraint_types standard tool | 3 |

## Trust Chain / Certificates (500-series)

| Ref. | Element | Appears in FIG. |
|------|---------|-----------------|
| 500 | Hierarchical trust chain | 1, 4 |
| 502 | Signed certificate | 4 |
| 504 | Schnorr signature operation | 4, 5 |
| 506 | Certificate claims | 4 |
| 508 | Anti-replay store (JTI) | 4 |
| 510 | Certification fee | 4 |
| 512 | Net amount (after fee) | 4 |
| 514 | Gross amount (before fee) | 4 |
| 516 | Signature verification | 4 |
| 518 | Automatic upstream certification (cascading real-time certify) | 4 |
| 520 | Upstream certificate (returned for audit transparency) | 4 |

## Nostr / Identity (600-series)

| Ref. | Element | Appears in FIG. |
|------|---------|-----------------|
| 600 | Nostr relay network | 1, 5 |
| 602 | Nostr public key (npub) | 5, 6 |
| 604 | Encrypted direct message | 5 |
| 606 | NIP-44 encryption layer | 5 |
| 608 | NIP-17 gift wrap layer | 5 |
| 610 | Secure Courier channel | 5 |
| 612 | Credential vault | 5 |
| 614 | Poison nonce | 5 |
| 616 | Citizenship challenge | 5 |
| 618 | Signature verification (citizenship) | 5 |
| 620 | Vault encryption (AES-256-GCM, nsec-derived key) | 4, 5 |
| 622 | Credential card (ncred1... token) | 5 |
| 624 | Identity credential (Nostr kind 30080) | 5 |
| 626 | NIP-04 bootstrap DM (Authority → Operator) | 4 |
| 628 | OAuth2 authorization flow (patron alternative) | 5 |
| 630 | Operator credential template | 4, 5 |
| 632 | Patron credential template | 5 |

## Governance (700-series)

| Ref. | Element | Appears in FIG. |
|------|---------|-----------------|
| 700 | Version-controlled repository | 6 |
| 702 | Branch protection rules | 6 |
| 704 | CI validation pipeline | 6 |
| 706 | Pull request | 6 |
| 708 | Ban process | 6 |
| 710 | Runtime registry verification | 6 |
| 712 | Tax rate configuration | 6 |
| 714 | Member record | 6 |

## Campaign Design Tool (800-series)

| Ref. | Element | Appears in FIG. |
|------|---------|-----------------|
| 800 | Pricing Studio application | 7 |
| 802 | AI consultant (LLM) | 7 |
| 804 | Community-managed system prompt | 7 |
| 806 | Structured interview stage (1-6) | 7 |
| 808 | Machine-parseable progress block | 7 |
| 810 | Revenue projection block | 7 |
| 812 | Campaign JSON extraction | 7 |
| 814 | Client-side constraint catalog | 7 |
| 816 | Pipeline validation and repair | 7 |
| 818 | Second opinion provider (independent LLM) | 7 |
| 820 | Peer review (structured critique) | 7 |
| 822 | Cross-provider feedback injection | 7 |
| 824 | Campaign comparison (A/B/C variants) | 7 |
| 826 | NIP-98 operator proof (kind 27235) | 7 |
| 828 | set_pricing_model MCP tool call | 7 |
| 830 | Atomic model activation | 7 |

## Tenant Isolation / Persistence Security (900-series)

| Ref. | Element | Appears in FIG. |
|------|---------|-----------------|
| 900 | Operator tenant schema | 4 |
| 902 | Schema name derivation (SHA-256 of npub) | 4 |
| 904 | Schema-qualified connection URL | 4 |
| 906 | HKDF-SHA256 key derivation | 4 |
| 908 | AES-256-GCM encryption/decryption | 4 |
| 910 | Bootstrap protocol (nsec → config discovery) | 4 |
| 912 | Authority `get_operator_config` tool | 4 |
| 914 | `bootstrap_config` table (npub-keyed provisioned config) | 4 |
| 916 | Transparent plaintext-to-encrypted migration | 4 |
| 918 | Template-driven onboarding status computation | 4 |
| 920 | Operator deregistration (schema lifecycle) | 4 |
| 922 | Patron credential partition (service, npub) key | 4, 5 |
| 924 | Cross-restart patron session restoration | 4 |
