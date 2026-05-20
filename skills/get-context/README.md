[← Back](../../README.md) | [English](README.md) | [Japanese](README-ja.md)

# get-context

A Claude Code skill that reports the current session's context-window usage as
a percentage, computed locally from the session JSONL `usage` metadata.

## Usage

```bash
skills/get-context/scripts/get-context        # -> 12.4%
GET_CONTEXT_RAW=1 skills/get-context/scripts/get-context   # -> 12.4% (123977/1000000 tokens)
```

## How it works

1. Locate the current session JSONL strictly via `$CLAUDE_CODE_SESSION_ID`
   (`~/.claude/projects/**/<session-id>.jsonl`). If the variable is unset, the
   script exits with an error instead of guessing — picking the wrong session
   would be worse than failing.
2. Read the **last** `usage` field auto-attached to each assistant message.
   The latest entry reflects the whole conversation, because the prior context
   is re-read from cache every turn.
3. `context_tokens = input + cache_creation + cache_read + output`, then
   `pct = context_tokens / CONTEXT_WINDOW * 100`.

## Environment variables

| Variable | Default | Meaning |
|----------|---------|---------|
| `CONTEXT_WINDOW` | `1000000` | Context window size in tokens |
| `GET_CONTEXT_RAW` | (unset) | Set to `1` to also print the raw token count |

## Note

This is a local estimate, not the exact value Claude sees, but it matches the
`/context` figure closely (e.g. 11.9% computed vs 12% shown). The precise
`context_window.used_percentage` is only delivered to the status line through
Claude Code's stdin payload, which a standalone script cannot read.

## Installation

```bash
ln -s "$PWD/skills/get-context" ~/.claude/skills/get-context
```
