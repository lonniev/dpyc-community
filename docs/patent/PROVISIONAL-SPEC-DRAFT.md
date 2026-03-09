# PROVISIONAL PATENT APPLICATION SPECIFICATION

## DRAFT — FOR ATTORNEY REVIEW ONLY

> **Legal Disclaimer**: This specification was prepared by the inventor with AI assistance
> (Claude, Anthropic). It requires review by a registered patent attorney or agent before
> filing with the United States Patent and Trademark Office. This document does not
> constitute legal advice. Claude is not a lawyer.

> **Filing Target**: Mid-2026 as provisional application (~$320 micro-entity fee)

> **Prior Art Disclosure Date**: February 17, 2026 (public repository at
> `github.com/lonniev/thebrain-mcp` with GPG-signed tag `v1.0.0-prior-art` dated
> February 16, 2026)

---

## Title of the Invention

**System and Method for Pre-Funded Balance Monetization of Tool-Based APIs
with Composable Constraint Pricing, Hierarchical Trust Chains,
Cryptographic Identity, and Network Governance**

---

## Cross-Reference to Related Applications

None. This is the initial provisional filing.

---

## Field of the Invention

The present invention relates generally to methods and systems for monetizing
application programming interfaces (APIs), and more particularly to a system for
monetizing tool-based API services through pre-funded credit balances settled via
cryptocurrency micropayment networks, with composable pricing constraints, hierarchical
multi-party revenue distribution, decentralized cryptographic identity, and community
governance mechanisms.

---

## Background of the Invention

### The Problem of API Monetization

Application programming interfaces (APIs) are the primary mechanism through which
software systems exchange data and invoke functionality. The emergence of AI agent
frameworks — particularly the Model Context Protocol (MCP) specification for connecting
AI assistants to external tools — has created a new class of API consumer: autonomous
software agents that invoke dozens or hundreds of tool calls per session without human
intervention at each step.

Traditional API monetization approaches fall into three categories, each with
significant limitations in the AI agent context:

**Subscription models** require the API consumer to commit to recurring payments
regardless of actual usage. This "pestering" of the customer — demanding payment
decisions before value is received — creates friction that discourages adoption and
penalizes intermittent users. Subscription management overhead (billing cycles,
plan tiers, overage charges, cancellation flows) consumes engineering resources
unrelated to the core service.

**Per-request payment negotiation models** (exemplified by the L402 protocol and the
x402 protocol, described below) require a payment interaction at the point of service.
When a client sends a request, the server responds with HTTP status 402 (Payment
Required) along with payment instructions. The client must then construct a payment,
transmit it, await confirmation, and resubmit the original request with proof of
payment. This challenge-response pattern introduces latency, interrupts tool call
chains, and requires the client to maintain payment channel state alongside
application state.

**Marketplace aggregation models** (exemplified by platforms such as MCPize, Apify,
and Masumi Network) interpose a centralized marketplace between API providers and
consumers. The marketplace handles billing, typically through conventional payment
processors (Stripe, credit card networks). These platforms extract significant
revenue shares (15% or more), require providers to conform to marketplace terms,
and introduce single points of failure. None provide the provider with direct
control over pricing policy or customer relationships.

### Prior Art

#### L402 Protocol (Lightning Labs, 2020)

The L402 protocol (originally named LSAT) was published by Lightning Labs in March
2020. It defines a mechanism for HTTP-native API payments using the Lightning Network.
When a server receives an unauthenticated request, it returns HTTP 402 with a
`WWW-Authenticate` header containing a Lightning invoice and a macaroon (a
bearer credential with attenuable caveats). The client pays the invoice, receives a
preimage, and combines the preimage with the macaroon to form an L402 token that
authenticates subsequent requests.

L402 is implemented through Aperture, a reverse proxy that intercepts requests,
verifies L402 tokens, and forwards authenticated requests to the upstream service.

L402 limitations relevant to the present invention:

- Every request that lacks a valid token triggers a payment negotiation cycle
- No mechanism for pre-funding a balance that covers multiple future requests
- Pricing rules are configured ad hoc in the reverse proxy; no composable
  constraint system exists
- Single-party architecture with no multi-layer revenue distribution
- Identity is bound to macaroons, not to a portable cryptographic keypair
- No community governance or network coordination mechanism

The L402 specification mentions "top-up" functionality in passing but does not
define a pre-funded balance architecture. It mentions "surge pricing" as a
possibility but provides no mechanism for implementing it.

#### x402 Protocol (Coinbase, 2025)

The x402 protocol was launched by Coinbase in late 2025, with a partnership
announced with Cloudflare in December 2025 for integration into Cloudflare's
infrastructure. x402 defines a stablecoin-based (USDC) payment mechanism embedded
in HTTP headers. The server responds with 402 and a JSON payment requirements
object; the client constructs a payment payload, signs it with a wallet key, and
includes it in a `PAYMENT-SIGNATURE` header on the retry request. A "facilitator"
service (hosted by Coinbase) verifies the signature and settles the payment on-chain.

x402 limitations relevant to the present invention:

- Same challenge-response pattern as L402 — no pre-funded balance
- Two payment "schemes" only: "exact" (fixed price) and "upto" (variable with ceiling);
  no composable constraint pipeline
- Relies on a centralized Facilitator service operated by Coinbase
- Identity is a blockchain wallet address, not a portable network identity
- No hierarchical trust chain or revenue distribution mechanism
- No governance layer — Coinbase controls the Facilitator and the Foundation
- Uses stablecoins (USDC) pegged to fiat currency, not native cryptocurrency

#### MCP Monetization Platforms (2025-2026)

Several platforms have emerged to monetize MCP tool services:

- **MCPize**: Marketplace model with 85% revenue share, Stripe-based payments
- **PayMCP/Walleot**: Decorator-based tool pricing (`@price`) with multiple payment modes
  via a centralized wallet service
- **Masumi Network**: Blockchain-based (Cardano-adjacent) payment integration
- **Moesif**: Traditional API analytics and billing wrapping Stripe/Chargebee/Zuora
- **Apify**: MCP server marketplace with conventional payment rails

None of these platforms use the Lightning Network for settlement. None implement
a pre-funded credit balance model. None have composable constraint-based pricing.
None have hierarchical trust chains with royalty distribution. None use
decentralized cryptographic identity. None have community governance mechanisms.

### Unmet Need

There exists a need for an API monetization system that:

1. Eliminates per-request payment negotiation by allowing consumers to pre-fund
   a credit balance from which individual tool invocations are deducted
2. Provides API operators with a composable, programmable pricing policy engine
   rather than ad hoc price configurations
3. Supports multi-party revenue distribution through a hierarchical trust chain
   where each layer uses the same protocol, enabling franchise-like scaling
4. Uses portable, decentralized cryptographic identity that requires no
   personally identifiable information, email addresses, passwords, or OAuth tokens
5. Provides community governance mechanisms that make the network's economic value
   reside in participation rather than in proprietary code

---

## Summary of the Invention

The present invention provides an integrated system and method for monetizing
tool-based APIs through five interconnected architectural components:

**First**, a pre-funded balance monetization system in which API consumers purchase
credit units ("api_sats") via Lightning Network micropayments, and individual tool
invocations deduct from that balance according to per-tool pricing rules, eliminating
per-request payment negotiation entirely.

**Second**, a composable constraint engine that evaluates a pipeline of pricing
constraints on each tool invocation — including temporal windows, finite supply caps,
periodic refresh limits, congestion-based surge pricing, ad valorem pricing proportional
to response value, and promotional modifiers — to produce a final deduction amount.

**Third**, a hierarchical trust chain with self-similar royalty distribution, in which
an Authority certifies purchase orders for downstream Operators using cryptographic
signatures, and each layer in the hierarchy implements the same protocol pattern. An
Authority is structurally an Operator whose customers happen to be other Operators.
Revenue flows through the chain via certification fees.

**Fourth**, a Nostr-based identity and credential exchange system in which each
participant is identified by a Nostr public key (npub), citizenship is verified through
cryptographic signature challenges, and API credentials are exchanged through encrypted
direct messages on the Nostr relay network — requiring no email, passwords, OAuth, or
personally identifiable information.

**Fifth**, a network governance system implemented through version-controlled community
registries on a collaborative source code platform (GitHub), in which membership,
dispute resolution, tax rates, and governance rules are managed through pull requests,
providing cryptographic auditability through the platform's Merkle-tree commit history.

These five components operate as a unified system referred to herein as the "Tollbooth"
architecture, governed by a voluntary community referred to as the "Don't Pester Your
Customer" (DPYC) Honor Chain.

---

## Brief Description of the Drawings

**FIG. 1** — System architecture diagram showing the relationship between Authority,
Operator, and Consumer tiers, including Lightning Network settlement, the community
registry, and the Nostr identity layer.

**FIG. 2** — Pre-funded balance lifecycle showing the sequence from credit purchase
through Lightning invoice generation, settlement, balance crediting, per-tool deduction,
tranche expiration, and balance top-up.

**FIG. 3** — Constraint Engine evaluation pipeline showing how a tool invocation
traverses a stack of composable constraints to produce a final price, including
the PriceModifier accumulation logic.

**FIG. 4** — Trust chain certification flow showing the cryptographic handshake
between Authority, Operator, and payment processor, including certificate generation,
signature verification, and royalty extraction.

**FIG. 5** — Nostr identity and credential exchange sequence showing the Secure
Courier protocol for privacy-preserving credential delivery using NIP-44 encrypted
direct messages on the Nostr relay network.

**FIG. 6** — Network governance data flow showing the relationship between the
community registry, the Oracle service, and the runtime membership verification
performed during purchase certification.

*(Drawings to be prepared as formal patent figures from the Mermaid source
diagrams accompanying this specification.)*

---

## Detailed Description of Preferred Embodiments

The following description presents the preferred embodiments of the invention in
sufficient detail to enable a person skilled in the art of distributed systems,
API design, and cryptocurrency payment protocols to reproduce the system.

### 1. System Overview and Terminology

The system comprises the following principal actors and components:

**Consumer** — An end user or AI agent that invokes tools on an Operator's MCP
service. The Consumer holds a credit balance denominated in api_sats and is
identified by a Nostr npub.

**Operator** — A service provider that exposes one or more tools through the Model
Context Protocol (MCP). The Operator runs the Tollbooth middleware, which gates tool
access behind a credit balance check. The Operator holds a BTCPay Server store and
a Lightning Network node (or connection to one) for receiving payments. The Operator
is identified by a Nostr npub and is a registered member of the DPYC Honor Chain.

**Authority** — A certification service that signs purchase orders for downstream
Operators. The Authority is structurally an Operator whose tools include the
`certify_credits` tool. The Authority collects a certification fee (functionally
equivalent to a tax or royalty) on each purchase order it signs. The Authority is
identified by a Nostr npub and is a registered member of the DPYC Honor Chain.

**First Curator** — The root Authority in the trust chain. The First Curator
self-signs its own certification events. The First Curator's npub is recorded in
the community registry under version control. There is exactly one First Curator
at any time.

**api_sats** — The internal unit of account for credit balances. api_sats are
purchased with real Bitcoin satoshis via Lightning Network invoices. The exchange
rate between real satoshis and api_sats is determined by a configurable multiplier
(the "VIP multiplier") that allows Operators to offer volume incentives. api_sats
have no value outside the Operator's service and are not redeemable for Bitcoin.

**Tollbooth** — The middleware library that an Operator integrates into their MCP
server. Tollbooth handles credit balance management, per-tool cost deduction,
constraint evaluation, Lightning invoice generation via BTCPay Server, certificate
verification, and ledger persistence.

**Honor Chain** — The voluntary community of Operators and Authorities, organized
as a network society. Members agree to common principles including the use of Bitcoin
and Lightning for all commerce, avoidance of storing personally identifiable information
on customers, proper identification of upstream Authorities, and acceptance of
community governance.

**Community Registry** — A JSON file (`members.json`) stored in a version-controlled
repository on GitHub. The registry records each member's Nostr npub, role (Citizen,
Operator, Authority, or First Curator), status (active or banned), membership date,
upstream Authority npub, and associated services.

**Oracle** — A free, publicly accessible MCP service that provides onboarding
guidance, governance document retrieval, member lookup, and citizenship verification
for the Honor Chain. The Oracle charges no api_sats for its tools.

### 2. Pre-Funded Balance Monetization (Claim Family 1)

#### 2.1 Architectural Distinction from Prior Art

The fundamental architectural distinction between the present invention and all
identified prior art (L402, x402, marketplace platforms) is the separation of the
payment event from the service event.

In challenge-response systems (L402, x402), the payment and service events are
temporally coupled: each service request either succeeds (bearer token present) or
triggers a payment negotiation (402 response with invoice). The client must complete
payment before receiving service. This coupling introduces latency proportional to
the payment network's confirmation time on every unauthenticated request, and requires
the client to maintain payment state alongside application state.

In the present invention, the payment event (purchasing api_sats) is decoupled from
the service event (invoking a tool). The consumer purchases credits in advance. Each
tool invocation is a simple deduction from an in-memory balance — a subtraction
operation with sub-millisecond latency. The consumer experiences no payment ceremony
during tool use.

This decoupling is expressed as: **the toll is already paid**. The consumer passes
through the tollbooth without stopping.

#### 2.2 Credit Purchase Flow

The credit purchase flow proceeds as follows:

1. **Certificate Request**: The Operator's `purchase_credits` tool receives a request
   specifying the desired amount in satoshis and a cryptographically signed certificate
   from the Operator's upstream Authority (described in Section 4). If no certificate
   is provided and the Operator does not require Authority certification, the purchase
   proceeds without certification.

2. **Certificate Verification**: If a certificate is provided, the Tollbooth middleware
   verifies the cryptographic signature against the Authority's known public key,
   validates the certificate's claims (amount, timestamp, anti-replay identifier),
   and extracts the net amount (original amount minus the Authority's certification fee).

3. **Invoice Generation**: The Tollbooth middleware calls the BTCPay Server's Greenfield
   API to create a Lightning Network invoice for the verified amount. The invoice
   includes metadata linking it to the consumer's identity (Nostr npub or OAuth-derived
   patron identifier).

4. **Lightning Settlement**: The consumer pays the Lightning invoice using any
   Lightning-compatible wallet. BTCPay Server confirms settlement.

5. **Balance Crediting**: Upon confirmed settlement, the Tollbooth middleware credits
   the consumer's ledger with api_sats equal to the paid amount multiplied by the
   Operator's configured VIP multiplier. Credits are granted idempotently — calling
   `check_payment` multiple times for the same invoice ID results in credits being
   granted exactly once.

6. **Tranche Creation**: Each credit purchase creates a discrete "tranche" in the
   consumer's ledger. Each tranche records the purchase amount, the grant timestamp,
   and an expiration timestamp (configurable by the Operator, default 30 days).
   Tranches are consumed in first-in-first-out (FIFO) order. Expired tranches are
   not deducted from but are removed from the available balance.

#### 2.3 Per-Tool Deduction

Each tool exposed by the Operator is annotated with a cost in api_sats using a
decorator pattern:

```python
@paid_tool(cost_api_sats=2)
async def search_thoughts(query_text: str) -> dict:
    """Full-text search across thought names and content."""
    ...
```

When a consumer invokes a tool, the Tollbooth middleware:

1. Evaluates the Constraint Engine (Section 3) to determine the effective cost,
   which may differ from the base cost due to active constraints.
2. Checks whether the consumer's available balance (sum of non-expired tranches)
   is sufficient.
3. If sufficient, deducts the effective cost from the oldest non-expired tranche
   (FIFO) and permits the tool invocation to proceed.
4. If insufficient, returns an error indicating the required balance and providing
   a direct path to purchase additional credits. The tool invocation does not proceed.
5. Records the deduction in the consumer's daily usage log, including the tool name,
   cost, and timestamp.

#### 2.4 Ledger Persistence

The consumer's ledger (balance, tranches, usage log, invoice history) is persisted
in an encrypted vault. In the preferred embodiment, the vault is implemented as a
server-side key-value store (NeonVault) that survives process restarts and serverless
cold starts. An in-memory LRU cache provides sub-millisecond read performance, with
write-behind flushing to the persistent store on a configurable interval.

The ledger is associated with the consumer's identity (derived from OAuth
authentication in the preferred embodiment, or from a Nostr npub in the decentralized
embodiment). Ledger data is never exposed to the consumer in full — only summary
views (current balance, usage statistics, invoice history) are returned through
read-only tools.

#### 2.5 Demurrage and Expiration

Purchased api_sats are subject to expiration (demurrage). Each credit tranche carries
an expiration timestamp. Upon expiration, the remaining api_sats in the tranche are
removed from the consumer's available balance. This design choice serves three purposes:

1. **Prevents store-of-value accumulation**: Without expiration, consumers would treat
   pre-funded balances as deposits, creating an implicit fiduciary obligation for the
   Operator to maintain backward compatibility with historical protocol versions
   indefinitely.
2. **Encourages timely consumption**: Expiration creates a natural incentive for
   consumers to use purchased credits, driving API traffic and revenue.
3. **Simplifies ledger management**: Expired tranches can be pruned from the ledger,
   bounding storage growth.

The expiration period is configurable per Operator. The preferred embodiment uses
a 30-day default.

### 3. Composable Constraint Engine (Claim Family 2)

#### 3.1 Architecture

The Constraint Engine is a pipeline evaluator that determines the effective cost and
access permission for each tool invocation. It is the mechanism by which Operators
implement programmable pricing policies without modifying application code.

The engine comprises:

- **ToolConstraint**: An abstract base class defining the interface for all constraints.
  Each constraint implements `evaluate(context) -> ConstraintResult` and
  `describe() -> str`.
- **ConstraintContext**: An immutable data structure containing the information
  available to constraints during evaluation: a `LedgerSnapshot` (current balance,
  total consumed, total deposited), a `PatronIdentity` (the consumer's identifier
  and associated metadata), and an `EnvironmentSnapshot` (current UTC timestamp,
  day of week, configured timezone).
- **ConstraintResult**: The output of a single constraint evaluation. Contains an
  `allowed` boolean, an optional `reason` string, an optional `retry_after` timestamp,
  an optional `PriceModifier`, and an optional metadata dictionary.
- **PriceModifier**: A value object that encodes a price adjustment. Supports
  `discount_percent` (0-100), `discount_sats` (flat reduction), `free` (boolean),
  and `bonus_multiplier` (value > 1.0 grants bonus credits). Modifiers compose:
  percentages compound multiplicatively, sat discounts add, free propagates
  (if any modifier sets free=true, the result is free).
- **ConstraintEngine**: The pipeline evaluator. Accepts a list of ToolConstraint
  instances and an evaluation mode. Modes are:
  - `ALL_MUST_PASS`: Every constraint must return `allowed=true` for the invocation
    to proceed. PriceModifiers from all passing constraints are accumulated.
  - `ANY_MUST_PASS`: At least one constraint must return `allowed=true`.
  - `FIRST_MATCH`: The first constraint that returns a definitive result (either
    allowed or denied with a reason) determines the outcome.

#### 3.2 Baked-In Constraint Classes

The preferred embodiment includes eight constraint classes implemented as
native code (Python) for performance and reliability:

1. **TemporalWindowConstraint**: Gates tool access to specified wall-clock hours
   and days of week. Supports timezone specification using the IANA timezone database.
   Example: tool available Monday-Friday 9:00-17:00 America/New_York. Outside the
   window, returns `allowed=false` with `retry_after` indicating when the window
   next opens.

2. **FiniteSupplyConstraint**: Limits total invocations of a tool to a fixed count,
   either globally (across all consumers) or per-consumer. Example: tool may be
   invoked at most 1,000 times total, or at most 50 times per consumer. When the
   supply is exhausted, returns `allowed=false` with reason indicating exhaustion.

3. **PeriodicRefreshConstraint**: Implements rolling-window rate limits with automatic
   refresh. Specifies a maximum invocation count and a refresh period as an ISO 8601
   duration. Example: at most 100 invocations per PT5H (5 hours). The window rolls
   forward continuously; invocations older than the period are no longer counted.

4. **CouponConstraint**: Validates a promotional code provided by the consumer.
   Supports configurable expiration dates, maximum total redemptions, and maximum
   per-consumer redemptions. Valid coupons produce a PriceModifier (discount or free).
   Expired or exhausted coupons return a neutral result (neither allowing nor denying).

5. **FreeTrialConstraint**: Grants the first N invocations of a tool at zero cost.
   Never denies — after the trial is consumed, returns a neutral result and the
   base price applies. Per-consumer tracking.

6. **LoyaltyDiscountConstraint**: Applies a discount when the consumer's total
   historical consumption (total_consumed_api_sats) exceeds a configurable threshold.
   Rewards sustained usage with reduced pricing.

7. **BulkBonusConstraint**: Applies tiered bonus multipliers based on cumulative
   consumption levels. Example: after 1,000 api_sats consumed, receive 1.1x bonus;
   after 10,000, receive 1.25x. Multipliers affect the api_sats credited per purchase,
   not the Lightning invoice amount.

8. **HappyHourConstraint**: Combines temporal window gating with a discount modifier.
   Unlike TemporalWindowConstraint, HappyHourConstraint never denies access — it
   returns a discount during the specified window and a neutral result outside it.

#### 3.3 Extensible Expression Constraint

For operators requiring custom pricing logic beyond the eight baked-in classes, the
system provides a `JsonExpressionConstraint` that evaluates safe expressions
specified in JSON configuration.

The expression evaluator uses abstract syntax tree (AST) analysis to ensure safety.
It supports comparison operators (`==`, `!=`, `>`, `<`, `>=`, `<=`), logical operators
(`and`, `or`, `not`), and field resolution against the ConstraintContext:

- `ledger.balance_api_sats` — current available balance
- `ledger.total_consumed_api_sats` — lifetime consumption
- `ledger.total_deposited_api_sats` — lifetime deposits
- `env.hour` — current hour (0-23) in configured timezone
- `env.day_of_week` — current day (0=Monday through 6=Sunday)
- `patron.id` — consumer identifier

The evaluator explicitly prohibits `eval()`, `exec()`, `compile()`, `import`,
attribute access on arbitrary objects, and any operation not in the permitted
operator whitelist. A static analysis test verifies these safety properties.

#### 3.4 Constraint Configuration

Constraints are defined per-tool in a JSON configuration file loaded at Operator
startup. Example:

```json
{
  "tools": {
    "search_thoughts": {
      "base_cost_api_sats": 2,
      "constraints": [
        {
          "type": "TemporalWindowConstraint",
          "params": {
            "start_hour": 9, "end_hour": 17,
            "days": [0, 1, 2, 3, 4],
            "timezone": "America/New_York"
          }
        },
        {
          "type": "FreeTrialConstraint",
          "params": {"free_invocations": 10}
        }
      ],
      "evaluation_mode": "ALL_MUST_PASS"
    }
  }
}
```

A `CONSTRAINT_REGISTRY` maps type strings to constraint classes. Custom constraint
classes can be registered by the Operator at startup, enabling arbitrary extensions
without modifying the Tollbooth library.

### 4. Hierarchical Trust Chain with Self-Similar Royalty Distribution (Claim Family 3)

#### 4.1 The Self-Similar Pattern

The core architectural insight of the trust chain is that an Authority is
structurally identical to an Operator. The only positional difference is that an
Authority's consumers are other Operators (who call `certify_credits`), while an
Operator's consumers are end users or AI agents (who call domain-specific tools).

This self-similarity means:

- The same Tollbooth middleware runs at every tier
- The same credit purchase flow (Section 2.2) applies at every tier
- The same constraint engine (Section 3) can apply pricing policies at every tier
- The same ledger management (Section 2.4) tracks balances at every tier
- No special-case code exists for "Authority" versus "Operator" — the distinction
  is purely in which tools are exposed and who the consumers are

This eliminates the need for separate tax collection machinery, separate balance
management systems, or separate protocol definitions at different tiers. The
Authority's revenue is earned through the `certify_credits` tool fee, not through
an architecturally distinct taxation mechanism.

In the preferred embodiment, the self-similar pattern extends to the certification
client itself: the same `AuthorityCertifier` class used by an Operator to obtain
a certificate from its Authority is also used by that Authority to obtain a
certificate from its upstream Authority, automatically, at certification time.
This means no tier in the chain requires manual supply management or pre-purchased
certificate inventories — each certification request cascades upstream in real-time.

#### 4.2 Certification Flow

When an Operator wishes to sell credits to its consumers, it must first obtain
a signed certificate from its upstream Authority:

1. **Operator requests certification**: The Operator calls the Authority's
   `certify_credits` tool, specifying the desired purchase amount in satoshis.

2. **Authority verifies standing**: The Authority fetches the community registry
   (`members.json`) from the version-controlled repository and verifies that the
   Operator's Nostr npub has `status: "active"`. If the Operator is banned or
   unregistered, the certification is refused.

3. **Authority calculates fee**: The Authority deducts its certification fee
   from the requested amount. In the preferred embodiment, the fee is the
   `certify_credits` tool's configured cost in api_sats, which is denominated in
   the Authority's own credit system.

4. **Authority signs certificate**: The Authority generates a certificate containing:
   - `gross_sats`: the original requested amount
   - `net_sats`: the amount after fee deduction (what the Operator will receive)
   - `fee_sats`: the Authority's fee
   - `operator_npub`: the requesting Operator's Nostr public key
   - `authority_npub`: the signing Authority's Nostr public key
   - `timestamp`: UTC timestamp of certification
   - `jti`: a unique anti-replay identifier (UUID)
   - `expires_at`: certificate expiration (configurable, default 10 minutes)

   The certificate is signed using the Authority's Schnorr private key
   (secp256k1 curve, as used in the Nostr protocol and Bitcoin's Taproot). The
   signature covers the SHA-256 hash of the canonical JSON serialization of the
   certificate claims.

5. **Operator receives certificate**: The signed certificate is returned to the
   Operator as a compact token (base64-encoded JSON with appended signature).

6. **Operator presents certificate to payment system**: When the Operator's
   `purchase_credits` tool is called by a consumer, the Operator passes the
   Authority's certificate. The Tollbooth middleware verifies the signature,
   checks the anti-replay identifier against a local store of used JTIs,
   validates the expiration, and creates a Lightning invoice for `net_sats`
   (not `gross_sats`). This ensures the Authority's fee is honored — the
   Operator cannot invoice for more than the Authority certified.

7. **Anti-replay**: Each certificate's JTI is recorded upon first use. Subsequent
   attempts to present a certificate with a previously used JTI are rejected.
   JTI records are pruned after the certificate's maximum possible lifetime
   (expiration time plus a safety margin).

#### 4.3 Chain Topology

The trust chain forms a tree rooted at the First Curator:

```
First Curator (self-signs)
  └── Authority A
        ├── Operator A1
        ├── Operator A2
        └── Sub-Authority A-sub
              ├── Operator A-sub-1
              └── Operator A-sub-2
```

Each Authority obtains its own certificates from its upstream Authority. In the
preferred embodiment, this upstream certification is performed automatically and
in real-time: when a non-Prime Authority's `certify_credits` tool is invoked by
a downstream Operator, the Authority simultaneously calls its upstream Authority's
`certify_credits` tool using the same `AuthorityCertifier` client class that
Operators use (described in Section 2.2, step 1). This creates a cascading
chain of real-time certifications — a single downstream request triggers
certification at every tier up to the First Curator.

The First Curator self-signs — this is logically consistent because the First
Curator is the root of trust. The self-signed certificate is distinguishable
(the `authority_npub` and `operator_npub` fields are the same) but valid.
The First Curator's `certify_credits` implementation detects the absence of an
upstream Authority address and skips the upstream call.

Revenue flows upward through the chain. Each certification event extracts a fee
at each layer. The fee amount at each layer is determined by that layer's
`certify_credits` tool pricing — which may itself be subject to constraint
evaluation (Section 3). The upstream certificate is included in the response
to the downstream caller for audit transparency (`upstream_certificate`,
`upstream_jti` fields).

#### 4.4 Principal-Agent Separation

The system supports separation between the economic actor (Principal) who funds
a balance and the operational actor (Agent) who invokes tools. This enables
delegation scenarios such as:

- A fleet operator (Principal) funding API access for individual drivers (Agents)
- A parent (Principal) funding educational tool access for a child (Agent)
- A business owner (Principal) provisioning API access for employees (Agents)

In this embodiment, the certificate carries both the Principal's npub and the
Agent's npub. The Constraint Engine can evaluate policies based on either identity,
enabling Principals to set per-Agent limits (maximum spending, time restrictions,
tool access restrictions) through constraint configuration.

### 5. Nostr-Based Identity and Credential Exchange (Claim Family 4)

#### 5.1 Identity Primitive

Every participant in the system is identified by a Nostr public key (npub), a
bech32-encoded representation of a secp256k1 public key as defined by the Nostr
protocol (NIP-01). The corresponding private key (nsec) is held exclusively by
the participant and is never transmitted to, stored by, or accessible to any
other system component.

The choice of Nostr keypairs as the identity primitive provides:

- **Portability**: The same npub identifies a participant across all Operators,
  Authorities, and the community registry. No per-service accounts.
- **Self-sovereignty**: No centralized identity provider. The participant generates
  their own keypair using standard cryptographic tools.
- **No PII**: Registration requires only an npub — no email address, phone number,
  legal name, or government identifier.
- **Cryptographic verifiability**: Ownership of an npub is provable through digital
  signature. The Nostr protocol's event signing mechanism provides this natively.
- **Communication channel**: The same npub that serves as an identifier also provides
  a messaging address on the Nostr relay network, enabling the Secure Courier
  protocol (Section 5.3).

#### 5.2 Citizenship Verification

New participants join the Honor Chain through a cryptographic signature challenge:

1. The applicant calls the Oracle's `request_citizenship` tool, providing their
   npub and a display name.
2. The Oracle generates a random nonce and returns it along with a challenge ID
   and signing instructions. The challenge has a 10-minute expiration.
3. The applicant constructs a Nostr event (kind 1, per NIP-01) with content
   containing the string `DPYC-CITIZENSHIP:<nonce>`, and signs it with their
   private key.
4. The applicant calls `confirm_citizenship` with the challenge ID, their npub,
   and the signed event JSON.
5. The Oracle verifies:
   - The challenge exists and has not expired
   - The Schnorr signature is valid per NIP-01
   - The event's pubkey matches the claimed npub
   - The event content contains the issued nonce
   - The npub is not already registered
6. On success, the Oracle commits the new member directly to `members.json`
   in the community registry repository, with role "citizen", status "active",
   and upstream_authority_npub set to the First Curator's npub.

This flow proves the applicant controls the private key corresponding to the
claimed npub, without the private key ever leaving the applicant's device or
being transmitted over any network.

#### 5.3 Secure Courier Credential Exchange

When an Operator's MCP service requires external API credentials from a consumer
(for example, API keys for an upstream service that the MCP tools proxy), the
Secure Courier protocol enables privacy-preserving credential delivery using
the Nostr relay network:

1. **Channel Opening**: The consumer calls `request_credential_channel`, optionally
   providing their npub. The Operator's service sends a welcome direct message
   to the consumer's npub via the Nostr relay network.

2. **Encrypted Delivery**: The consumer replies to the welcome message with their
   credentials in a structured format. The reply is encrypted using NIP-44
   (versioned encryption using XChaCha20-Poly1305 with HKDF-SHA256 key derivation)
   and wrapped using NIP-17 (gift-wrapped direct messages) for metadata privacy.
   The NIP-17 wrapping ensures that relay operators cannot determine the sender,
   recipient, or content of the message.

3. **Credential Receipt**: The consumer calls `receive_credentials`. The service
   scans configured Nostr relays for encrypted direct messages from the consumer's
   npub, decrypts the NIP-44 payload, validates the credential format against
   a service-specific template, and stores the credentials in an encrypted vault.

4. **Vault Storage**: Credentials are encrypted with a consumer-provided passphrase
   using a key derivation function and stored in the server-side vault. The
   passphrase is never stored — the consumer must provide it at each session
   activation.

5. **Anti-Replay**: Each credential delivery includes a "poison nonce" — a random
   value embedded in the welcome message that must appear in the reply. This
   binds the credential delivery to a specific channel opening event and prevents
   replay of old credential messages.

6. **Relay Cleanup**: After successful credential receipt, the encrypted message
   is deleted from the relay to minimize the exposure window of encrypted credential
   material on third-party infrastructure.

7. **Ephemeral Agent**: When the consumer's npub is identical to the Operator's
   npub (self-onboarding), the Secure Courier generates a one-time ephemeral
   Nostr keypair. The welcome DM is sent from this ephemeral identity, and
   the consumer replies to it. The ephemeral keypair is discarded after
   credential receipt. This avoids the silent failure mode where Nostr relays
   drop self-addressed DMs, and is consistent with NIP-17's ephemeral key
   pattern for metadata protection.

The Secure Courier ensures that API credentials never appear in the chat interface
between the consumer and the AI assistant. They travel on a separate, encrypted
channel — conceptually a "diplomatic pouch" — that is inaccessible to the AI
model, the chat platform, or any intermediary.

### 6. Network Governance as Economic Defense (Claim Family 5)

#### 6.1 Design Philosophy

The Tollbooth software is open source under the Apache License 2.0. A bad actor
could clone the entire codebase, replace the Authority's wallet address with their
own, and collect revenue without participating in the Honor Chain. Software
protection is deliberately not pursued. Instead, the system's economic defense
resides in the network itself: a cloned Tollbooth operating outside the Honor Chain
has no community trust, no Authority chain, no cross-Operator interoperability,
and no access to the Oracle's onboarding and governance services. The clone is
a standalone API behind a paywall — possible, but economically uncompetitive with
the network.

This design is intentional and draws from network economics: the value of
participation in a network grows with the number of participants (Metcalfe's Law),
while the cost of replicating the software is fixed. As the network grows, the
economic moat widens without any change to the software.

#### 6.2 Community Registry

The community registry (`members.json`) is the canonical record of Honor Chain
membership. It is stored in a GitHub repository with the following protections:

- **Branch protection**: The `main` branch requires pull requests, at least one
  approving review from an Authority, passing CI validation, and prohibits
  force-pushes and branch deletions.
- **CI validation**: Automated checks enforce JSON schema compliance, npub format
  validation (bech32 encoding, correct length), uniqueness (no duplicate npubs),
  and upstream reference integrity (every member's `upstream_authority_npub` must
  reference an existing active member).
- **Git-as-blockchain**: Every commit in the repository hashes its parent in a
  Merkle tree, forming a tamper-evident chain. Signed commits provide
  cryptographic attribution. The `git log` serves as a block explorer. The pull
  request history serves as a consensus record.

Each member record contains:

```json
{
  "npub": "npub1...",
  "display_name": "Operator Name",
  "role": "operator",
  "status": "active",
  "member_since": "2026-02-20",
  "upstream_authority_npub": "npub1...",
  "services": [
    {
      "name": "service-name",
      "url": "https://service.example.com/mcp",
      "description": "Service description"
    }
  ]
}
```

#### 6.3 Membership Hierarchy

The Honor Chain defines four membership tiers:

**Citizen** — The entry tier. Requires only a Nostr npub. Verified through the
signature challenge (Section 5.2). Citizens can consume API services as consumers
and participate in governance discussions. Sponsored by the First Curator by default.

**Operator** — Runs one or more monetized MCP services. Requires sponsorship by
an Authority, a BTCPay Server store, and installation of the Tollbooth middleware.
Operators collect api_sats from consumer traffic and pay certification fees to
their upstream Authority.

**Authority** — Certifies purchase orders for downstream Operators. Requires
sponsorship by an existing Authority (or the First Curator). Collects certification
fees. Responsible for vetting onboarding, monitoring downstream conduct, and
maintaining network integrity in their region of the chain.

**First Curator** — The singular root of the trust chain. Identified by a Nostr
npub recorded in the community registry under version control. Appoints the
initial Authorities, resolves governance disputes, and can issue bans by decree.
Succession mechanism for the First Curator role is defined in the governance
document and subject to community amendment.

#### 6.4 Dispute Resolution and Banning

Members who violate community principles (collecting payments without proper
certification, storing consumer PII, misrepresenting Authority affiliation,
operating cloned Tollbooths outside the Honor Chain) are subject to banning:

1. An Issue is opened on the community repository with evidence of the violation.
2. A 72-hour discussion period allows Authorities to weigh in.
3. If consensus supports banning, a pull request changes the member's status to
   "banned" with a `ban_reason` linking to the Issue and a `banned_at` timestamp.
4. The pull request is reviewed and merged by an Authority with repository access.

A banned member's `certify_credits` requests are refused by all Authorities
that check the registry — cutting off their ability to transact. The member's
record remains in `members.json` for transparency and auditability.

Appeals follow the same process: a new Issue, community review, and a restoring
pull request if upheld.

#### 6.5 Tax Rate Governance

The community tax rate (the certification fee percentage) is stored in the
community repository and fetched by Operators at deployment time and on periodic
refresh. Changes to the tax rate follow the same pull request process as membership
changes, providing version-controlled history of all rate modifications.

This mechanism ensures that no single party can unilaterally change the economic
terms of the network. The First Curator proposes; the community reviews; the
merge constitutes consensus.

#### 6.6 Runtime Registry Verification

At the point of certification (Section 4.2, step 2), the Authority performs a
real-time check against the community registry:

1. Fetch `members.json` from the repository (with caching and configurable
   refresh intervals to balance freshness against API rate limits).
2. Look up the requesting Operator's npub.
3. Verify `status == "active"`.
4. If banned or not found, refuse certification with a descriptive error.
5. If active, proceed with certification.

This check is the enforcement mechanism that gives the registry its economic
power: a banned member cannot obtain certificates, cannot create invoices,
and therefore cannot sell API access through the Honor Chain.

---

## Abstract

A system and method for monetizing tool-based application programming interfaces
(APIs) through pre-funded credit balances, composable pricing constraints,
hierarchical trust chains, decentralized cryptographic identity, and community
governance.

API consumers pre-fund credit balances denominated in internal units (api_sats) via
Lightning Network micropayments. Individual tool invocations deduct from the balance
according to pricing rules evaluated by a composable Constraint Engine supporting
temporal windows, supply caps, rate limits, surge pricing, promotional modifiers, and
custom expressions.

Revenue is distributed through a hierarchical trust chain in which Authorities
certify purchase orders for downstream Operators using Schnorr digital signatures.
Each layer in the hierarchy implements the same protocol pattern — an Authority is
structurally an Operator whose consumers are other Operators.

Participants are identified by Nostr public keys (npubs). Citizenship is verified
through cryptographic signature challenges. API credentials are exchanged through
encrypted direct messages (NIP-44, NIP-17) on the Nostr relay network, eliminating
the need for email, passwords, OAuth tokens, or personally identifiable information.

The system is governed through a version-controlled community registry on a
collaborative source code platform, providing cryptographic auditability through
Merkle-tree commit history. Economic defense resides in network participation rather
than in proprietary code.

---

## Appendix A: Implementation References

The preferred embodiment is implemented across the following open-source repositories
and deployed services:

| Component | Repository | Purpose |
|-----------|-----------|---------|
| Tollbooth Library | `tollbooth-dpyc` (PyPI) | Operator-side middleware: credit management, constraint engine, certificate verification, Lightning integration |
| Authority Service | `tollbooth-authority` | Authority-side MCP service: purchase certification, registry verification, Schnorr signing |
| Oracle Service | `dpyc-oracle` | Community onboarding, governance, member lookup, citizenship verification |
| Community Registry | `lonniev/dpyc-community` | `members.json`, GOVERNANCE.md, tax rate, network status |
| Reference Operator | `lonniev/thebrain-mcp` | First Tollbooth-monetized MCP service (TheBrain knowledge graph API) |
| Reference Operator | `lonniev/excalibur-mcp` | Second Tollbooth-monetized MCP service (X/Twitter posting) |

The prior art GPG-signed tag `v1.0.0-prior-art` (dated February 16, 2026) on the
`lonniev/thebrain-mcp` repository establishes the earliest cryptographic proof of
the system's existence. The repository was made publicly accessible on February 17,
2026.

## Appendix B: Cryptographic Primitives

| Primitive | Usage | Specification |
|-----------|-------|--------------|
| secp256k1 Schnorr signatures | Certificate signing, Nostr event signing, citizenship verification | BIP-340, NIP-01 |
| SHA-256 | Certificate claim hashing, Merkle tree (git) | FIPS 180-4 |
| XChaCha20-Poly1305 | NIP-44 payload encryption (Secure Courier) | RFC 8439 (extended nonce variant) |
| HKDF-SHA256 | NIP-44 key derivation from ECDH shared secret | RFC 5869 |
| NIP-17 gift wrapping | Metadata-private message delivery | Nostr NIP-17 |
| bech32 encoding | Nostr npub/nsec representation | BIP-173, NIP-19 |
| Lightning Network BOLT-11 | Invoice generation and settlement | BOLT #11 |

## Appendix C: Constraint Engine Class Hierarchy

```
ToolConstraint (ABC)
├── TemporalWindowConstraint
├── FiniteSupplyConstraint
├── PeriodicRefreshConstraint
├── CouponConstraint
├── FreeTrialConstraint
├── LoyaltyDiscountConstraint
├── BulkBonusConstraint
├── HappyHourConstraint
└── JsonExpressionConstraint
```

**ConstraintEngine evaluation modes:**
- `ALL_MUST_PASS`: Conjunction — all constraints must allow
- `ANY_MUST_PASS`: Disjunction — at least one must allow
- `FIRST_MATCH`: Short-circuit — first definitive result wins

**PriceModifier composition rules:**
- Percentage discounts compound multiplicatively: 10% + 20% = 28% total discount
- Satoshi discounts add: 5 sats off + 3 sats off = 8 sats off
- Free propagates: if any modifier sets free=true, result is free
- Bonus multipliers compound multiplicatively: 1.1x * 1.25x = 1.375x

---

*End of Provisional Patent Application Specification Draft*

*Prepared by: Lonnie VanZandt (Inventor) with AI assistance (Claude, Anthropic)*
*Date: March 2026*
*Status: DRAFT — Requires review by registered patent attorney or agent*
