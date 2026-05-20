---
name: get-context
description: Report the current Claude Code session's context-window usage percentage, computed locally from the session JSONL usage metadata
---

# get-context

Print how much of the context window the current session is using, as a
percentage.

## When to invoke

- User asks how full the context is ("今どれくらいコンテキスト使ってる?",
  "context 残量", "how much context is left").
- Before a long task, to decide whether compaction is near.

## How to get it

Run the bundled script and report its stdout:

```bash
skills/get-context/scripts/get-context
```

It prints e.g. `12.4%`. For the raw token count too:

```bash
GET_CONTEXT_RAW=1 skills/get-context/scripts/get-context   # -> 12.4% (123977/1000000 tokens)
```

## How it works

1. Locate the current session JSONL strictly via `$CLAUDE_CODE_SESSION_ID`
   (`~/.claude/projects/**/<session-id>.jsonl`). If the variable is unset,
   exit with an error instead of guessing — picking the wrong session would be
   worse than failing.
2. Read the **last** `usage` field — the token metadata auto-attached to each
   assistant message. The latest entry reflects the whole conversation because
   the prior context is re-read from cache every turn.
3. `context_tokens = input + cache_creation + cache_read + output`, then
   `pct = context_tokens / CONTEXT_WINDOW * 100`.

## Env overrides

- `CONTEXT_WINDOW` — context window size in tokens (default `1000000`).
- `GET_CONTEXT_RAW` — set to `1` to also print the raw token count.

## Note

This is a local estimate from the session log, not the value Claude itself
sees. It matches the `/context` figure closely (e.g. 11.9% computed vs 12%
shown). The exact `context_window.used_percentage` is only available to the
status line via Claude Code's stdin payload, not to a standalone script.
