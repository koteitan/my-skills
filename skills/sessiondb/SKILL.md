---
name: sessiondb
description: Index Claude Code session JSONL logs into a SQLite + FTS5 database with Japanese-aware tokenization, and search them
---

# sessiondb

Full-text search over past Claude Code sessions stored as JSONL in
`~/.claude/projects/`.

## When to invoke

- User wants to find a past session by topic or keyword
  ("あの話どこでしたっけ", "find the session about X").
- User asks to (re)build or update the session index.
- User asks aggregate stats about session history that would be slow with grep.

Do **not** invoke for lookups inside the current session — use `Read`/`Grep`.

## Database location

`~/.claude/sessiondb/sessions.db` (override with env var `SESSIONDB_PATH`).

## CLI

```
sessiondb index                       # incremental rebuild
sessiondb index --full                # drop and rebuild from scratch
sessiondb search "<query>" --format=jsonl [--project P] [--role R] [--limit N]
sessiondb search                      # query 省略 = セッション一覧 (新しい順)
sessiondb stats
sessiondb show <session_id> [--line L] [--context K]
```

**重要**: エージェントが呼ぶときは必ず `--format=jsonl` を付ける。CLI の
既定は `--format=table` (人間向け TSV) なので、明示しないと下記の
JSON Lines 形式は得られない。

If `bin/sessiondb` is not installed, fall back to invoking `sqlite3` directly:

```sql
SELECT m.session_id,
       snippet(messages_fts, 0, '<b>', '</b>', '…', 32) AS snippet,
       bm25(messages_fts) AS score,
       m.ts, m.role, m.source_path, m.line_no
  FROM messages_fts JOIN messages m ON m.id = messages_fts.rowid
  WHERE messages_fts MATCH :query
  ORDER BY score LIMIT 20;
```

## Response format (search)

JSON Lines, one hit per line, followed by a summary line:

```jsonl
{"session_id":"…","project":"…","ts":"…","role":"…","snippet":"…","score":-4.21,"source_path":"…","line_no":142,"resume":"claude --resume …"}
{"_summary":{"hits":17,"shown":10,"query":"…","ms":34}}
```

`--format=table` (CLI 既定) is TSV for human reading; do not parse from agent.

## Build / schema / ingest details

See [how-to-create-db.md](how-to-create-db.md). Read it only when you need to
implement, modify, or debug the indexer; not on every search.
