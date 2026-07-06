[← Back](../README.md) | [English](README.md) | [Japanese](README-ja.md)

# bin/

Standalone helper scripts. Add this directory to `PATH` (or symlink individual
scripts) to use them.

## Notification

- **pushover** — Thin `curl` wrapper: `pushover <message>` sends an iPhone
  Pushover notification. Requires env `PUSH_OVER_TOKEN` and `PUSH_OVER_USER`.
- **claude-pushover** — Claude Code hook that extracts the latest conversation
  message and sends it via Pushover (intended as a `Stop` hook).

## Live server

- **live-server-sil** `[port]` — Start `live-server` silently in the background
  serving the current directory, printing a single clickable URL (OSC 8).
- **live-server-list** — List running `live-server` instances: PID, URL,
  serving directory.
- **live-server-kill** `[port]` — Kill a running `live-server`. With no
  argument, kills the sole running instance; otherwise pass the port.

## Session / project directory

- **sessiondb** — SQLite + FTS5 full-text index over Claude Code session JSONL.
  Subcommands: `index`, `search`, `stats`, `size`, `show`, `help`. See
  [`skills/sessiondb/`](../skills/sessiondb/).
- **sessionmv** `<src> <dst>` — Move a directory and every corresponding
  `~/.claude/projects/` session directory (including subdirs), rewriting `cwd`
  paths inside session JSONL files.
- **mv-session** `<src> <dst>` — Older, simpler variant of `sessionmv`: moves a
  directory plus its single `~/.claude/projects/` session directory, without
  rewriting JSONL contents.

## Text / protocol

- **newline** — Detect the line-ending type (CR / LF / CRLF) of files.
- **nostrsocat** — `websocat` wrapper for Nostr relays:
  `nostrsocat <relay> <k1> <v1> <k2> <v2> …`. Requires `websocat`.
