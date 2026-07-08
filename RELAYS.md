# DPYC Supported Nostr Relays

`relays.json` in this repository is the **single source of truth** for which Nostr
relays the DPYC federation uses. Every Tollbooth server (via the `tollbooth-dpyc`
wheel) and every front-end (the Pricing Studio iOS app) fetches this list over
GitHub raw HTTPS. There is no hardcoded relay list anywhere else — change the set
here and the whole federation follows.

Raw URL clients fetch:

```
https://raw.githubusercontent.com/lonniev/dpyc-community/main/relays.json
```

## Curation criteria

A relay belongs on this list only if it is **both**:

1. **Reliable** — high, proven uptime.
2. **Open for writes** — accepts events from arbitrary npubs with no payment or
   allow-list gate.

The open-write requirement is not optional: the Secure Courier delivers
credential DMs from *arbitrary patron npubs* to operators. A paywalled or
metadata-only relay (however well-run) would silently reject those writes and
strand the flow, so such relays are excluded even when they are individually
excellent (e.g. `nostr.wine`, which is paid; profile-only relays like
`purplepag.es`).

## Client behavior

Clients cache the fetched list and refresh only when their **cache is older than
3 days**. There is no baked-in fallback list:

- **Fresh cache (< 3 days)** → used directly, no fetch.
- **Stale or absent cache** → refetch from GitHub raw.
- **Refresh fails but a previously-fetched copy exists** → keep serving that
  last-known-good copy (stale-if-error) rather than going dark.
- **Cold start with no cache and an unreachable GitHub** → relay-dependent
  operations fail closed. This is the same trust model the members registry
  already uses (`members/read-only-lookup-cache.json`).

## Usage protocol — how the federation uses the set

The relays in `relays.json` form one shared pool. Different subsystems draw on it
differently:

| Subsystem | Strategy |
|---|---|
| **Secure Courier DMs** (credentials) | Try relays in order; **pin the first relay that accepts the publish** as the per-conversation rendezvous (the chosen relay is embedded in the DM so the responder replies there). |
| **Identity proof** (`request/receive_npub_proof`) | Drain **only** the pinned rendezvous relay from the courier exchange. |
| **Audit trail** (ledger events) | **Broadcast to all** relays, fire-and-forget. |
| **Bootstrap config** (kind-30078, NIP-33) | Publish/poll across the whole set. |
| **Profile** (kind-0 read/publish) | Fan out across the whole set. |

Array order is preference order. The entry flagged `primary: true` (or, absent
that flag, the first entry) is the courier's first rendezvous try.

## Editing the set

1. Edit `relays.json` — add/remove relays, bump `version`, update `updated_at`.
2. Open a PR. CI (`validate-relays.yml`) validates it against
   `schemas/relays.schema.json`.
3. On merge to `main`, clients pick up the change on their next cache refresh
   (within 3 days; sooner on a cold start).
