# NIP-19 bech32 entities

Build and parse `npub`, `note`, `nprofile`, `nevent`, `naddr`.

## Policy

1. **Do NOT use `nostr-tools`** (or other bech32 libs) in project code. Write
   the bech32 encode/decode DIY.
2. **decode must be symmetric with encode** — same DIY implementation both ways,
   round-trippable.
3. **Match the method the surrounding file already uses.** If a file already has
   a bech32 helper, reuse/extend it; don't introduce a second style.
4. When generating a test `naddr` URL, **ask which relay hints to embed** — the
   user often wants a specific hint (e.g. `wss://nos.lol` even though it isn't
   in their kind:10002) to test relay-hint behavior.

## naddr TLV structure

`naddr` bech32-encodes a TLV payload (`nostr:naddr1…`):

| type | meaning | encoding |
|------|---------|----------|
| `0` special | the `d` identifier (kind:30xxx) | UTF-8 bytes of the identifier |
| `1` relay | relay hint (repeatable) | ASCII bytes of the relay URL |
| `2` author | pubkey | 32 raw bytes (hex → bytes) |
| `3` kind | event kind | 4-byte big-endian uint32 |

`nevent` uses the same TLV but type `0` = 32-byte event id. `nprofile` = type `0`
pubkey + type `1` relays. `npub`/`note` are plain bech32 of the 32-byte value
(no TLV).

Bech32: HRP is the prefix (`naddr`, `nevent`, `npub`…); data is the 5-bit
regrouped payload plus a 6-byte checksum.

## Typical request

> `https://…/pack/<pubkey>/<name>` を naddr にして URL を教えて

→ kind = 30030 (emoji sets) or whatever the app uses, author = `<pubkey>`,
d-identifier = `<name>`, relays = the hint(s) the user specifies. Emit
`nostr:naddr1…` and/or the app URL form.
