---
name: nostr
description: koteitan's Nostr hub — relay discovery (bootstrap → kind:10002 → kind:3 → fallback), NIP-19 bech32 encode/decode (naddr/nevent/npub, DIY, no nostr-tools), CLI relay debugging with websocat/nak, the standard web-app stack (TypeScript + Vite + rx-nostr + React), and a pointer to the ~/code/nostr-research survey of how real clients/relays behave (bootstrap relays, limit/rate-limit, NIP-11 limits). Use for any nostr task — building/fixing a nostr web client, making an naddr URL, checking which relay holds an event, or asking what other implementations do.
---

# nostr

Everything for koteitan's nostr work. Read the reference file for the task at
hand; each is self-contained.

| Task | Reference |
|------|-----------|
| New/existing nostr web app: stack, NIP-07, follow list, note fetching | `references/project-stack.md` |
| Which relays to read/write for a pubkey; incremental rendering rule | `references/relay-discovery.md` |
| Build/parse `naddr` / `nevent` / `npub` / `note` / `nprofile` | `references/nip19.md` |
| "Does relay X have event/tag Y for pubkey Z?" (CLI debugging) | `references/relay-query.md` |
| **How do other clients/relays actually do it?** — bootstrap-relay choices per client, relay-software `limit`/rate-limit behavior, per-instance NIP-11 limits | `references/research-repo.md` → `~/code/nostr-research/` |

## Standing rules (apply to all nostr work)

1. **Do NOT use `nostr-tools`** (or other bech32 libs) for NIP-19 in project
   code — DIY the bech32, and keep decode symmetric with encode.
2. **Match the surrounding file's existing method.** If a bech32 helper or a
   relay-fetch pattern already exists in the file, reuse/extend it.
3. **Render as data arrives — never block on EOSE.**
4. Only use kind:10002 for the relay list; kind:3 is fallback only.
5. **Don't guess how other clients/relays behave, or what a relay's limits are —
   look it up in `~/code/nostr-research/`** (see `references/research-repo.md`).

## Relay sets (shared by all references)

Bootstrap / indexer relays:

```
wss://directory.yabu.me
wss://purplepag.es
wss://relay.nostr.band
wss://indexer.coracle.social
```

Fallback relays — if browser locale is `ja`:

```
wss://yabu.me                    wss://nostr.compile-error.net
wss://r.kojira.io                wss://relay-jp.nostr.wirednet.jp
wss://nrelay-jp.c-stellar.net    wss://nostream.ocha.one
wss://snowflare.cc
```

otherwise:

```
wss://relay.damus.io             wss://nostr-pub.wellorder.net
wss://offchain.pub               wss://relay.snort.social
```

Common kinds: `0` metadata, `1` note, `3` contacts, `10002` relay list,
`30030` emoji sets.

## Related (not part of this skill)

- `nostter-upstream-pr` — the PR workflow for contributing to SnowCait/nostter.
