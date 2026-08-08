# Relay discovery chain

How a client resolves which relays to read/write for a pubkey. Follow it exactly.

## Chain (in order, stop at the first hit)

1. From the bootstrap relays (SKILL.md), fetch **kind:10002** (NIP-65 relay
   list) for the target pubkey. If found → use those read/write relays.
   **Do not also use kind:3.**
2. If no kind:10002 → fetch **kind:3** (contact list) and read its legacy relay
   map in `content`.
3. If neither → use the fallback relay set (locale-dependent, see SKILL.md).
4. Then fetch the actual content (kind:1 etc.) from the resolved relays.

Always take the event with the newest `created_at`, and drop read-only relays
when you need write relays.

## Incremental / observable rendering

- **Render as data arrives — never block on EOSE.** As soon as a step finds
  something, move to the next step; merge later updates into the UI.
- Structure the pipeline as observable/reactive (rx-nostr streams or an event
  callback), not "await everything, then render".

## Timeouts

5 sec EOSE timeout, then retry at 30 sec, proceeding as soon as the first
kind:10002 event arrives. (See `project-stack.md` for the rx-nostr form.)
