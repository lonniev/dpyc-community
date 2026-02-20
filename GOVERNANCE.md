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

## Adding Members

### Process

1. **Applicant** generates a Nostr keypair and contacts a sponsoring Authority.
2. **Sponsoring Authority** submits a PR adding the applicant to `members.json` with:
   - `npub` — the applicant's Nostr public key
   - `role` — `operator` or `authority`
   - `status` — `active`
   - `member_since` — the current date
   - `upstream_authority_npub` — the sponsoring Authority's npub
   - `services` — list of MCP services (for operators)
3. **CI validation** runs automatically, checking schema, npub format, no duplicates, and that the upstream npub exists in the registry.
4. **An Authority with repo access** reviews and merges the PR.

### Who Can Approve

- The **Prime Authority** can approve any membership PR.
- **Authorities with repo access** can approve PRs for members in their downstream chain.
- Self-registration is not allowed — every new member needs a sponsor.

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
