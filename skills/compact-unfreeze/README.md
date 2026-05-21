[← Back](../../README.md) | [English](README.md) | [Japanese](README-ja.md)

# compact-unfreeze

A Claude Code skill that works around the Remote Control + `/compact`
frozen-input bug ([issue #51267](https://github.com/anthropics/claude-code/issues/51267))
without tmux or any local keystroke.

## The bug

When you run `/compact` **from the remote (mobile) client**, the next remote
input freezes: it shows as `× <text>`, queued but never delivered. Local input
always works; only the remote path stalls — it stays stuck until a local TTY
event wakes the input loop.

## The workaround

Arm a one-shot background **Monitor** (a `sleep` timer) *before* compacting.
The Monitor task survives `/compact`, and when its timer fires the agent is
re-invoked. That single loop iteration — **even a text-only reply, no tools** —
drains the stuck queue. Remote input works again, hands-free.

This was confirmed with a clean in-seat test: the frozen probe drained 5
seconds after the Monitor fired, with the agent running zero tools.

## Usage

This is an instruction-only skill — there is no CLI to run. The agent reads
`SKILL.md` and, when you are about to `/compact` from the remote client:

1. Loads the `Monitor` tool (`ToolSearch("select:Monitor")`).
2. Arms a one-shot Monitor with `sleep 240` (covers a ~1–2 min compact plus
   margin) and `timeout_ms: 300000`.
3. You run `/compact`; when the Monitor fires, the agent replies and the frozen
   queue flushes.

See [SKILL.md](SKILL.md) for the exact tool call, timing notes, and how to
verify it worked from the session JSONL.

## See also

- Manual alternatives: any local input, or `tmux send-keys -t <pane> Escape`.
  The Monitor route needs neither.
