# Provisional Specification — Revision & Errata Log

This log records **as-built corrections** to the filed provisional specification
(`PROVISIONAL-SPEC-DRAFT.md`), for incorporation into the non-provisional
(utility) application. A filed provisional application cannot be amended in
place — its filing date attaches to the text as submitted — so these revisions
are intended to be carried into the non-provisional (or a follow-on provisional)
before the priority window closes.

> **Not legal advice.** This is a technical as-built record prepared by the
> inventor with AI assistance (Claude, Anthropic). Confirm all filing mechanics
> with a registered patent attorney or agent. Claude is not a lawyer.

- **Provisional application** (per inventor's records): No. 64/045,999, filed
  2026-04-21.
- **Non-provisional deadline**: 2027-04-21.

---

## Revision 1 — 2026-06-24 — Upstream certification mechanism (§4.1, §4.3)

**Affects:** §4.1 (Self-Similar Pattern) and §4.3 (Chain Topology).

**As filed**, the specification describes upstream (Authority-to-Authority)
certification as a *real-time cascade*: a non-Prime Authority's `certify_credits`,
when invoked by a downstream Operator, "simultaneously calls its upstream
Authority's `certify_credits` … a cascading chain of real-time certifications …
no tier requires pre-purchased certificate inventories — each certification
request cascades upstream in real-time."

**As built** (the `tollbooth-dpyc` SDK), the mechanism differs — there is **no
real-time cascade** inside `certify_credits`:

1. `certify_credits` (the Authority's revenue tool) debits the **calling
   actor's** pre-funded api_sat balance held *at that Authority* by the
   ad-valorem fee, verifies registry standing, signs the Schnorr certificate
   (Nostr event kind 30079) locally, and returns. It does **not** invoke any
   upstream Authority — the `AuthorityCertifier` client is never called from the
   certification path.
2. Each non-Prime Authority instead maintains a **pre-funded api_sat balance at
   its parent Authority** — its certification capacity. That balance is consumed
   as the Authority certifies its own downstream purchases up the chain, and is
   **replenished by the Authority's own `purchase_credits` call** (in "certified"
   mode). That purchase is the moment — and the only moment — at which upstream
   certification actually occurs.
3. Fees still accrue at **every tier** (the model remains a cascading /
   compounding ad-valorem tax in aggregate), and — consistent with the
   pre-funded-balance claims elsewhere in the specification — **all such fees are
   collected at credit-purchase / certification time, never during a consumer's
   tool call.** A consumer's tool invocation debits only the consumer's own local
   ledger; it triggers no upstream fee.

**Net effect:** the implemented mechanism is **pre-funded certification capacity
(inventory) replenished by each tier's own purchase** — the opposite of the
"no pre-purchased inventories / real-time cascade" language as filed. The
real-time upstream cascade remains a **contemplated alternative embodiment**; it
is not the current implementation.

**Disposition (to confirm with counsel):** carry the pre-funded-balance
mechanism into the non-provisional as the primary embodiment, optionally
retaining the real-time cascade as an alternative embodiment to preserve broader
claim scope.
