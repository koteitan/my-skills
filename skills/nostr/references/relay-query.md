# Ad-hoc relay query (CLI debugging)

Fetch a pubkey's events from a specific relay, check tags, compare across relays.

Triggers: "wss://… に pubkey … のイベントがあるか見て" / "kind:3 に \"p\":\"…\"
というタグはある?" / "リレーを wss://… にしてみて。こっちにはあった"

## websocat (installed — prefer it)

```bash
echo '["REQ","x",{"authors":["<pubkey-hex>"],"kinds":[10002],"limit":5}]' \
  | websocat -n1 wss://relay.example.net
```

- `-n1` closes after the first response batch. For a full set, drop `-n1` and
  Ctrl-C after EOSE, or pipe through a short timeout.
- Parse the `["EVENT",...]` lines with `jq` to read `.tags` / `.content`.
- Compare relays by running the same REQ against each URL and diffing.

## nak (if available — terser)

```bash
nak req -k 10002 -a <pubkey-hex> wss://relay.example.net
nak req -k 3 -a <pubkey-hex> wss://relay.example.net | jq '.tags'
```

## Finding *which* relay has something

Start from the bootstrap/indexer relays in SKILL.md (plus
`wss://user.kindpag.es`).

## Reporting

Answer the concrete question directly: "yes, relay X returns a kind:3 with a
`p` tag = `<val>`" or "no event found on X, but Y has it." Show the relevant
tag/JSON snippet, not the whole event dump.
