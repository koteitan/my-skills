# nostr web project — stack & standard flows

The platforms and fetch procedures koteitan re-specifies in every nostr project.
(If the project already picked something else, match the project.)

## Platform

- language: TypeScript
- build: Vite
- nostr: rx-nostr — https://github.com/penpenpng/rx-nostr
- UI: React
- UI translation: react-i18next — https://github.com/i18next/react-i18next

## Get the app user's pubkey

Read it from the NIP-07 browser extension
(https://github.com/nostr-protocol/nips/blob/master/07.md).

## Fetch the relay list

- from the bootstrap relays (see SKILL.md)
- rx-nostr **backward** strategy
- filter: `kinds:[10002,3]`, `limit:2`, `authors:[pubkey]`
- 5 sec EOSE timeout; retry with:
  - 30 sec EOSE timeout
  - proceed to the next step as soon as the first kind:10002 event arrives
- Basically use **only** kind:10002. If none, fall back to kind:3's relay list;
  if neither, use the fallback relays.
- Use the list with the newest `created_at`.
- Remove relays marked read-only.

See `relay-discovery.md` for the same chain stated as a general client rule.

## Read the user's profile (name / display_name / icon)

After NIP-07: fetch `kinds:[0]`, `limit:1`, `authors:[pubkey]`, take the newest
`created_at`, then read `content.picture`, `content.name`, `content.display_name`.

## Fetch the follow list

- from relay list + bootstrap relays
- rx-nostr backward strategy
- filter: `kinds:[3]`, `limit:1`, `authors:[pubkey]`
- 5 sec EOSE timeout; retry with 30 sec, proceeding on the first hit
- use the follow list with the newest `created_at`

## Subscribe to kind:1 notes (forward)

- from the relay list, rx-nostr strategy
- filter: `kinds:[1]`, `authors: <follow-list pubkeys>`, `limit:0`
- If over 1000 followings, split into multiple subscriptions of 1000 authors each.

## Fetch followees' kind:0 profiles

- from the relay list
- filter: `kinds:[0]`, `authors:` 200 pubkeys per batch, `limit:200`

## Main project

The above is only the shared part. **Ask the user what the main project is.**
