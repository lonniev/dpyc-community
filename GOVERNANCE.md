# DPYC Honor Chain Governance

This document describes how the DPYC community manages membership, resolves disputes, and maintains the integrity of the Honor Chain registry.

## Membership Tiers

### Prime Authority

The founding root of the Honor Chain. The Prime Authority:

- Mints cert-sats (all downstream supply originates here)
- Has no upstream authority (`upstream_authority_npub: null`)
- Can approve membership PRs for any role
- Acts as tiebreaker on disputed governance decisions
- Cannot be banned through the normal process

**Current Prime Authority:** Lonnie VanZandt (`npub1l94pd4qu4eszrl6ek032ftcnsu3tt9a7xvq2zp7eaxeklp6mrpzssmq8pf`)

### Authority

An intermediate node in the Honor Chain that:

- Purchases cert-sats from its upstream Authority
- Certifies purchase orders for its downstream Operators
- Collects tax on each certification
- Can sponsor new Operators and sub-Authorities
- Has repo write access to approve membership PRs for their downstream members

### Operator

A leaf node that runs one or more MCP services monetized through the Tollbooth:

- Purchases tax credits from their sponsoring Authority
- Serves end users via MCP tools
- Must maintain active standing to have purchases certified

### Citizen

A community member who has proven ownership of a Nostr keypair but does not operate services or certify purchases:

- Has no Tollbooth obligations or privileges
- Identified by their `npub` — the same Nostr keypair used by all tiers
- May participate in governance (ban discussions, appeals)
- May upgrade to Operator or Authority by finding a sponsoring Authority and submitting a role-change PR
- Sponsored by the Prime Authority by default (automated onboarding via the DPYC Oracle)

Citizens are admitted through a Nostr signature challenge: the applicant signs a nonce with their private key, proving they control the `npub` without revealing the `nsec`. The Oracle verifies the signature and commits the membership directly — no waiting for PR review.

## Adding Members

### Self-Service Citizen Onboarding

1. **Applicant** generates a Nostr keypair (e.g., `nak key generate`).
2. **Applicant** calls the DPYC Oracle's `request_citizenship(npub, display_name)` tool, which returns a challenge nonce.
3. **Applicant** signs the challenge message `DPYC-CITIZENSHIP:<nonce>` with their Nostr private key and calls `confirm_citizenship(npub, challenge_id, signed_event_json)`.
4. **Oracle** verifies the Schnorr signature, confirms the signing pubkey matches the claimed npub, and commits the applicant directly to `members.json` as a Citizen with `upstream_authority_npub` set to the Prime Authority. Membership is effective immediately.

### Sponsored Member Onboarding

1. **Applicant** generates a Nostr keypair and contacts a sponsoring Authority.
2. **Sponsoring Authority** submits a PR adding the applicant to `members.json` with:
   - `npub` — the applicant's Nostr public key
   - `role` — `operator`, `authority`, or `citizen`
   - `status` — `active`
   - `member_since` — the current date
   - `upstream_authority_npub` — the sponsoring Authority's npub
   - `services` — list of MCP services (for operators)
3. **CI validation** runs automatically, checking schema, npub format, no duplicates, and that the upstream npub exists in the registry.
4. **An Authority with repo access** reviews and merges the PR.

### Who Can Approve

- The **Prime Authority** can approve any membership PR.
- **Authorities with repo access** can approve PRs for members in their downstream chain.
- Self-registration is not allowed — every new member needs a sponsor (Citizens are sponsored automatically by the Prime Authority via the Oracle).

## Ban Proposals

### Grounds for Banning

- Collecting payments without proper Authority certification
- Storing customer PII in violation of the DPYC philosophy
- Misrepresenting upstream Authority affiliation
- Operating a cloned Tollbooth without Honor Chain membership
- Fraud, abuse, or conduct harmful to the community

### Process

1. **Open an Issue** on this repository with:
   - The `npub` of the member in question
   - Evidence of the violation (screenshots, logs, transaction records)
   - Which community principle was violated
2. **72-hour discussion period** — Authorities weigh in on the Issue.
3. **Ban PR** — If consensus supports banning, a PR is submitted that:
   - Changes the member's `status` to `"banned"`
   - Adds `ban_reason` with a link to the Issue
   - Adds `banned_at` with the current date
4. **PR reviewed and merged** by an Authority with repo access.

### Effects of a Ban

- The member's `certify_purchase` requests will be refused by all Authorities that check this registry.
- The member's record remains in `members.json` for transparency and auditability.
- Downstream members of a banned Authority must find a new upstream sponsor or face service interruption.

## Appeals

1. **Open a new Issue** referencing the original ban Issue.
2. **Present new evidence** or argue that the ban was unjust.
3. **Community review** — same 72-hour discussion period.
4. **If upheld**: a PR restoring `status` to `"active"` and removing `ban_reason` / `banned_at`.
5. **If denied**: the ban stands. Further appeals require substantial new evidence.

## Registry Integrity

- **Branch protection** is enabled on `main`:
  - All changes require a PR
  - At least 1 approving review from an Authority
  - CI status checks must pass
  - No force-pushes
  - No branch deletions
- **Git history** provides a tamper-evident audit trail — every membership change is a signed, hashed commit in a Merkle tree.
- **CI validation** enforces schema compliance, npub format, uniqueness, and upstream reference integrity on every PR.

## Amendments

This governance document can be updated via the same PR process. Changes to governance require approval from the Prime Authority.
