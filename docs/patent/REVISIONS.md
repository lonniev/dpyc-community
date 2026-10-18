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

---

## Revision 2 — 2026-09-29 — npub-ownership proof for agentic callers and the poison nonce (§5.2, §5.3 step 5, §5.4)

**Affects:** §5.2 (Citizenship Verification), §5.3 step 5 (Anti-Replay / poison
nonce, element 614), §5.4 (Identity Credentials, element 624). Adds as-built
elements 634, 636, 638 to the reference numeral schedule; FIG. 5 is to be
redrawn for the non-provisional to show them.

**As filed**, the specification describes proof of npub control in two places
only: the Oracle citizenship challenge (§5.2 — a signed kind-1 event carrying an
issued nonce) and the operator deployment proof (§7.6 — a NIP-98 kind-27235
event, element 826). The poison nonce (§5.3 step 5) is described solely as an
anti-replay binding between a Secure Courier welcome message and its reply. The
specification does not describe how an **agentic caller that holds no private
key** (an AI assistant acting for a patron) proves, and later re-asserts, that it
acts for that patron's npub on paid tool calls.

**As built** (the `tollbooth-dpyc` SDK), that flow exists and is the dominant
one in production:

1. **npub-ownership challenge (element 634).** The agent calls
   `request_npub_proof(patron_npub)`. The Operator sends the patron a Secure
   Courier direct message (610) carrying a one-time poison nonce (614), an
   Operator-signed provenance attestation (kind 27235, binding the delivery key,
   the subject npub, the nonce, an optional stated reason and an optional
   `verify_at` venue — the OAuth 2.0 Device Grant `verification_uri`
   generalised), and a rendezvous relay. The patron confirms the source and the
   nonce in any conforming Nostr client and replies, optionally stating a
   duration; the reply is signed by the patron's private key. The agent then
   calls `receive_npub_proof(patron_npub, nonce)`; the Operator drains only the
   pinned relay, verifies the signed reply, and deletes it (NIP-09).
2. **Per-call proof of possession, keyed callers.** A caller that holds a
   private key (an Operator calling an Authority, an agent with its own keyring,
   the native pricing application) presents a freshly signed kind-27235 event
   on every paid call, bound to the invoked tool name, within a 60-second
   freshness window, with single-use replay rejection. This generalises §7.6
   from deployment to every paid tool.
3. **Divergence to be corrected — the nonce as credential.** From SDK 0.15.5
   (2026-04-26) through the current release, the Operator caches
   `sha256(nonce) : npub` on a successful receive and thereafter accepts the
   bare nonce, presented with the public npub, as the proof on every paid call
   for up to thirty days; the patron's signed reply is not retained. The nonce
   is drawn from a 51,840-value phrase space and was designed and documented as
   a non-secret matching token. **This is an implementation defect, not a
   design element**, and is being corrected (field report lonniev/goodearth-mcp#199, filed 2026-09-29,
   target lonniev/tollbooth-dpyc). It must not be carried into the
   non-provisional as an embodiment.

**Corrected design (to be carried forward as the primary embodiment):**

- **Proof grant (element 636).** On a verified reply the Operator mints an
  Operator-signed identity credential (kind 30080, element 624) binding the
  patron's public key, the hash of the nonce, the patron's own signature from
  the verified reply, and an expiration equal to the duration the patron
  stated. The agent holds this grant with the nonce and presents the grant with
  the npub on each paid call. The Operator verifies its own signature, the
  npub, the nonce hash, and expiry, with no server-side state on the hot path;
  revocation is a server-side tombstone. The nonce **selects** a grant and never
  authorizes on its own.
- **Proxy delegation (element 638).** When the agent holds its own key, the
  challenge names the agent's public key, the patron's signed reply covers it,
  and the grant carries an actor binding. That agent presents its own per-call
  kind-27235 proof together with the grant: sender-constrained delegation
  without a token-exchange service — the counterpart of the nested actor claim
  in OAuth 2.0 Token Exchange (RFC 8693), achieved with two Schnorr signatures
  and no authorization server.

**Relation to prior art (for the non-provisional's background).** The flow is
the structural counterpart of OpenID Connect Client-Initiated Backchannel
Authentication (CIBA): consumption device (the agent), authentication device
(the patron's Nostr client), a hint (the npub), a request handle (the nonce), a
binding message, a user-chosen expiry, and a grant. It differs in that there is
**no authorization server** — the Operator issues the challenge and the grant
under its own registered key; the binding message is **Operator-signed and bound
to the delivery key and the challenge** rather than relayed plaintext; the
transport is the untrusted public relay network; and the challenge transcript is
destroyed on receipt.

**Disposition (to confirm with counsel):** carry elements 634, 636 and 638 into
the non-provisional under Claim Family 4; describe item 3 above nowhere as an
embodiment. Add to the numeral schedule and FIG. 5 accordingly.

---

## Revision 3 — 2026-10-18 — identity on the connection; one acting npub per request (§5.2, §5.3, §5.4, §7.6)

**Affects:** §5.3 step 5 (poison nonce, element 614), §5.4 (Identity Credentials,
element 624), §7.6 (operator deployment proof, element 826), and Revision 2
(elements 634, 636, 638). Adds as-built elements 640–648 to the reference numeral
schedule; FIG. 5 is to be redrawn for the non-provisional to show them.

**As described in Revision 2**, proof of npub control travelled inside each
paid tool call as tool arguments: a keyed caller passed a freshly signed
kind-27235 event bound to the tool name, and a keyless agent passed the proof
grant (636) with its nonce. An agent's tool arguments are untrusted input, the
event was bound to the tool name and not to the arguments, and a client had to
store and replay grant material in its own context.

**As built** (`tollbooth-dpyc` 0.103.0, released 2026-10-18, live across the
network), identity travels on the HTTP connection that carries the call, and no
tool takes a proof argument. Every tool names the npub it acts for, and the
`Authorization` header proves it in one of two ways:

1. **Signed request (element 640).** A caller holding the npub's private key
   signs each HTTP request (NIP-98): a kind-27235 event whose tags name the
   method, the URL and the SHA-256 of the request body, plus a random nonce,
   carried as `Authorization: Nostr <base64 event>`. The Operator verifies the
   Schnorr signature, the method, the path and the body hash, a 60-second
   freshness window, and single-use replay rejection, before the request reaches
   any tool. The signature authorizes that request and nothing else, so it binds
   the tool arguments as well as the tool name. This generalises §7.6 (element
   826) from deployment to every request, and replaces the per-call argument
   proof of Revision 2 item 2.
2. **Holder connection and wallet (element 642).** A caller holding no private
   key (an AI assistant, a web page, a headless worker) connects by OAuth 2.1:
   dynamic client registration, an Authorization Code grant with PKCE that the
   Operator approves at once, short-lived access tokens and single-use rotating
   refresh tokens with reuse detection, all stored only as hashes. The
   connection has no identity of its own. Each npub it may act for is proven
   into its **wallet** one at a time by the npub-ownership challenge (634): the
   Operator stores the resulting proof grant (636) and its nonce against the
   holder, and on each call checks the grant the holder holds for the named npub
   (its own signature, the npub, the nonce hash, expiry, and revocation). The
   grant never leaves the Operator; the client holds only its OAuth tokens.
3. **Holder-bound challenge (element 644).** The challenge is bound to the
   holder that requested it, and `receive_npub_proof` answers only that holder.
   A reply can therefore prove an npub only into the connection that asked, and
   nothing is returned that a third party could replay.
4. **One acting npub per request (element 646).** A request proves exactly one
   npub. An action that needs the consent of two parties is a workflow of
   single-actor requests with a recorded approval. As built: an Operator asks an
   Authority to adopt it (`request_adoption`, a request signed with the
   Operator's key) and asks to change its registry entry (`update_operator`);
   both wait in the Authority's request queue until the Authority's owner
   approves or rejects them (`approve_operator_request`,
   `reject_operator_request`). Leaving the network (`deregister_operator`) is a
   single-party act by either the Operator or the Authority. The two-party
   `register_operator` call, which carried both parties' proofs in one request,
   is deleted.
5. **Authority-signed registry writes (element 648).** The community Oracle
   accepts a registry write (registering, updating or removing an Operator)
   only on a request signed by the key of the Authority it names; any other
   request reaches its free read tools as an anonymous caller.

**Changes to earlier elements.**

- **614.** The poison nonce is named `nonce` throughout the wire protocol. It
  remains a non-secret matching token that selects a challenge or a grant and
  never authorizes on its own.
- **636.** The proof grant is unchanged in form (Operator-signed kind 30080 over
  the patron's verified signature). It is held by the Operator in a holder's
  wallet (642) and is never presented by the client.
- **638.** Proxy delegation as described in Revision 2 (an actor binding inside
  the grant) was not built. Its purpose, letting an agent act for a patron
  without the patron's key, is met by the holder connection (642): the patron's
  signed reply proves the npub into the agent's connection. A keyed agent acting
  as itself signs its own requests (640).
- **The Revision 2 divergence (bare nonce as credential)** is fully removed. No
  path accepts a nonce, a grant or a signed event as a tool argument.

**Relation to prior art (for the non-provisional's background).** Element 640
is NIP-98 HTTP Auth applied to every request of a Model Context Protocol
session, with the body hash making it a per-request proof of possession in the
manner of OAuth 2.0 DPoP (RFC 9449) with no authorization server and no
separate key-binding step: the npub is the key. Element 642 uses the OAuth 2.1
Authorization Code flow with an empty consent step, because the connection
carries no identity until an npub is proven into it out of band (634); the
OAuth layer supplies only a revocable channel identity, and npub authority
comes from the patron's own signature.

**Disposition (to confirm with counsel):** carry 640–648 into the
non-provisional under Claim Family 4 as the primary embodiment of per-request
identity; retain the argument-borne proof of Revision 2 only as an alternative
embodiment if broader claim scope is wanted; describe 638 as superseded by 642.
Add to the numeral schedule and FIG. 5 accordingly.
