[← Back](README.md) | [English](how-to-create-db.md) | [Japanese](how-to-create-db-ja.md)

# How to create the sessiondb database

Schema, tokenizer choices, ingest logic, and build instructions for the
`sessiondb` SQLite index. Read this when implementing or debugging
`bin/sessiondb`, not on every search.

## Schema

Two regular tables plus an FTS5 virtual table.

```sql
-- Per-session aggregate metadata (denormalized from messages for fast listing).
CREATE TABLE sessions (
  session_id  TEXT PRIMARY KEY,
  project     TEXT NOT NULL,           -- e.g. "-home-koteitan-my-skills"
  cwd         TEXT,
  source_path TEXT NOT NULL UNIQUE,    -- absolute path to the .jsonl
  started_at  TEXT,
  ended_at    TEXT,
  msg_count   INTEGER NOT NULL DEFAULT 0,
  total_bytes INTEGER NOT NULL DEFAULT 0
);

-- One row per JSONL line.
CREATE TABLE messages (
  id          INTEGER PRIMARY KEY,
  session_id  TEXT NOT NULL REFERENCES sessions(session_id),
  line_no     INTEGER NOT NULL,        -- 1-based line in the source JSONL
  ts          TEXT,
  role        TEXT,                    -- user / assistant / system
  kind        TEXT,                    -- text / tool_use / tool_result / thinking
  tool        TEXT,                    -- tool name for tool_use kinds
  content     TEXT NOT NULL,           -- flattened searchable text
  raw_len     INTEGER,                 -- original byte length
  UNIQUE (session_id, line_no)
);
CREATE INDEX idx_messages_session ON messages(session_id);
CREATE INDEX idx_messages_ts      ON messages(ts);

-- FTS5 mirror of messages.content with Japanese-aware tokenizer.
CREATE VIRTUAL TABLE messages_fts USING fts5(
  content,
  content='messages',
  content_rowid='id',
  tokenize='vaporetto'   -- fallback: 'trigram' if extension unavailable
);

-- Bookkeeping for incremental ingest.
CREATE TABLE files (
  source_path    TEXT PRIMARY KEY,
  size           INTEGER NOT NULL,     -- size at last ingest
  mtime          REAL NOT NULL,
  indexed_lines  INTEGER NOT NULL,     -- lines already in `messages`
  indexed_at     TEXT NOT NULL
);
```

The raw JSONL is **not** copied into the DB. `(source_path, line_no)` is enough
to re-read original context on demand.

## Tokenizer selection

Mixed Japanese / English content is handled by the FTS5 tokenizer, not by
pre-tokenizing in the indexer. Preference order:

1. **[sqlite-vaporetto](https://github.com/hotchpotch/sqlite-vaporetto)** —
   fast, lightweight Japanese morphological tokenizer; leaves ASCII as-is.
2. **[lindera-sqlite](https://github.com/lindera/lindera-sqlite)** —
   broader CJK support, heavier dependency.
3. **`trigram`** (built into SQLite ≥ 3.34) — zero-dependency fallback;
   coarser recall but works out of the box.
4. **`unicode61`** — last resort; Japanese recall will be poor.

Switch tokenizers only via `sessiondb index --full`, since the FTS5 index is
tokenizer-specific.

## Content flattening rules

For each JSONL line, the indexer flattens its content into the `messages.content`
text blob:

- text block → text as-is
- `tool_use` → `"[{tool_name}] " + JSON.stringify(input)`
- `tool_result` → text output; if larger than 64 KB, truncate and append `[truncated]`
- `thinking` → not indexed by default (noise). Add `--include-thinking` to enable.

Keep the original `raw_len` so callers can spot truncated rows.

## Ingest rules (incremental)

JSONL files are append-only during a session. The `files` table records the last
ingested `(size, mtime, indexed_lines)` per file. On each `sessiondb index`:

1. Walk every `*.jsonl` under `~/.claude/projects/`.
2. For each file, compare against the `files` row:

   | Current state                  | Action                                             |
   |--------------------------------|----------------------------------------------------|
   | not in `files`                 | new session — ingest from line 1                   |
   | same `size` as recorded        | skip                                               |
   | `size` grew                    | append-only — ingest from `indexed_lines + 1`      |
   | `size` shrunk                  | abnormal — purge this `source_path` and re-ingest  |
   | file no longer exists          | delete `sessions` / `messages` / `files` rows      |

3. Wrap each file's ingest in a single transaction for speed.
4. Update the `files` row with new `(size, mtime, indexed_lines, indexed_at)`.

The current live session JSONL is handled by the same logic — it just keeps
growing in size and each index run appends the new lines.

`sessiondb index --full` drops and recreates `messages`, `messages_fts`,
and `files`, then ingests from scratch. Use this when the schema or tokenizer
changes.

## Build / install (Python reference implementation)

Minimal stack: Python 3 stdlib only, plus the chosen tokenizer extension.

```bash
# 1. Build the tokenizer extension (vaporetto example; requires Rust)
git clone https://github.com/hotchpotch/sqlite-vaporetto
cd sqlite-vaporetto
cargo build --release
# → target/release/libsqlite_vaporetto.so

# 2. Load it in the indexer
python3 -c "
import sqlite3
conn = sqlite3.connect('/home/koteitan/.claude/sessiondb/sessions.db')
conn.enable_load_extension(True)
conn.load_extension('/path/to/libsqlite_vaporetto.so')
"
```

When the extension is unavailable, the indexer should fall back to
`tokenize='trigram'` and print a warning.

## Constraints

- **Read-only** access to `~/.claude/projects/`. Never write there.
- The indexer must be **idempotent** — running it twice with no source changes
  must be a no-op.
- All user-facing CLI messages in Japanese (per user preference).

## Related skills

- [history](../../skills/history/) — lists / inspects raw session files.
  `sessiondb` adds search on top.
