[← Back](../../README.md) | [English](README.md) | [Japanese](README-ja.md)

# sessiondb

A Claude Code skill that indexes session JSONL logs into a SQLite + FTS5
database, enabling fast full-text search across all your past Claude Code
conversations — with proper Japanese morphological tokenization for mixed
Japanese / English content.

## What it does

Claude Code stores every conversation as JSONL in `~/.claude/projects/`. Over
time these accumulate to hundreds of megabytes, and `grep` becomes slow and
imprecise — especially for Japanese text where word boundaries are not
whitespace.

`sessiondb` builds an incremental SQLite + FTS5 index that lets you:

- Find a past session by keyword or topic in milliseconds.
- Resume that session via `claude --resume <session_id>`.
- Get statistics on usage by project, time, or session size.

## Database location

Default: `~/.claude/sessiondb/sessions.db`

The index lives next to the source data at `~/.claude/projects/` so that
backing up `~/.claude/` captures both originals and index. Override the path
with the `SESSIONDB_PATH` environment variable.

## Quick start

```bash
# Build the index (first run is a full scan; subsequent runs are incremental)
sessiondb index

# Search
sessiondb search "形態素解析"
sessiondb search "FTS5" --project -home-koteitan-my-skills

# Resume a found session
claude --resume <session_id>
```

## Files in this skill

| File | Purpose |
|------|---------|
| [SKILL.md](SKILL.md) | Agent-facing prompt: when to invoke and how to call |
| [how-to-create-db.md](how-to-create-db.md) | Schema, tokenizer, ingest, and build instructions |

## Status

Spec only at the moment — `bin/sessiondb` is not yet implemented.
Until the CLI exists, the skill lets Claude perform searches by issuing
SQLite queries directly.
