[← Back](README-ja.md) | [English](how-to-create-db.md) | [Japanese](how-to-create-db-ja.md)

# sessiondb データベースの作り方

`sessiondb` の SQLite インデックスのスキーマ、トークナイザー選定、取り込み
ロジック、構築手順をまとめたドキュメント。`bin/sessiondb` を実装・修正・
デバッグするときに読むためのもので、毎回の検索時に読む必要はありません。

## スキーマ

通常テーブル 2 つ + FTS5 仮想テーブル 1 つ。

```sql
-- セッション単位のメタデータ（messages から派生・非正規化）
CREATE TABLE sessions (
  session_id  TEXT PRIMARY KEY,
  project     TEXT NOT NULL,           -- 例: "-home-koteitan-my-skills"
  cwd         TEXT,
  source_path TEXT NOT NULL UNIQUE,    -- 元 .jsonl への絶対パス
  started_at  TEXT,
  ended_at    TEXT,
  msg_count   INTEGER NOT NULL DEFAULT 0,
  total_bytes INTEGER NOT NULL DEFAULT 0
);

-- JSONL の 1 行 = 1 メッセージ
CREATE TABLE messages (
  id          INTEGER PRIMARY KEY,
  session_id  TEXT NOT NULL REFERENCES sessions(session_id),
  line_no     INTEGER NOT NULL,        -- JSONL の 1-based 行番号
  ts          TEXT,
  role        TEXT,                    -- user / assistant / system
  kind        TEXT,                    -- text / tool_use / tool_result / thinking
  tool        TEXT,                    -- tool_use のみ
  content     TEXT NOT NULL,           -- 検索対象に平坦化したテキスト
  raw_len     INTEGER,                 -- 元の byte 数
  UNIQUE (session_id, line_no)
);
CREATE INDEX idx_messages_session ON messages(session_id);
CREATE INDEX idx_messages_ts      ON messages(ts);

-- 日本語対応トークナイザーで `content` をミラーする FTS5 仮想表
CREATE VIRTUAL TABLE messages_fts USING fts5(
  content,
  content='messages',
  content_rowid='id',
  tokenize='vaporetto'   -- 拡張が無ければ 'trigram' にフォールバック
);

-- 増分取り込みのブックキーピング
CREATE TABLE files (
  source_path    TEXT PRIMARY KEY,
  size           INTEGER NOT NULL,     -- 最後にインデックスした時点の byte 数
  mtime          REAL NOT NULL,
  indexed_lines  INTEGER NOT NULL,     -- すでに `messages` に入った行数
  indexed_at     TEXT NOT NULL
);
```

生の JSONL は DB に**入れません**。`(source_path, line_no)` を覚えておけば
必要なときに元ファイルから前後文脈を読み直せます。

## トークナイザー選定

日英混在テキストは FTS5 のトークナイザー側で処理し、インデクサ側で
事前トークナイズはしません。優先順位：

1. **[sqlite-vaporetto](https://github.com/hotchpotch/sqlite-vaporetto)** —
   高速・軽量、日本語を形態素分割、ASCII はそのまま。
2. **[lindera-sqlite](https://github.com/lindera/lindera-sqlite)** —
   CJK 全般に対応、依存が重め。
3. **`trigram`**（SQLite 3.34 以降に内蔵）— 依存ゼロのフォールバック。
   再現率は粗いがそのまま動く。
4. **`unicode61`** — 最終手段。日本語の再現率はかなり落ちる。

トークナイザーの変更は `sessiondb index --full` 経由で。FTS5 のインデックスは
トークナイザー固有なので。

## content の平坦化ルール

JSONL の各行について、`messages.content` に格納する文字列の作り方：

- text ブロック → そのまま
- `tool_use` → `"[{tool_name}] " + JSON.stringify(input)`
- `tool_result` → 出力テキスト。64 KB を超えたら切り詰めて末尾に `[truncated]`
- `thinking` → 既定では取り込まない（ノイズ）。`--include-thinking` で有効化

切り詰めの有無は呼び出し側で判別できるよう、`raw_len` を必ず残します。

## 増分取り込みロジック

JSONL はセッション中ずっと append-only。`files` テーブルに各ファイルの
最終取り込み状態 `(size, mtime, indexed_lines)` を持ち、`sessiondb index`
実行時に以下のように分岐します。

1. `~/.claude/projects/` 配下の `*.jsonl` を全件走査
2. 各ファイルについて `files` レコードと比較：

   | 現在の状態                  | 動作                                           |
   |----------------------------|------------------------------------------------|
   | `files` に無い              | 新規セッション → 1 行目から全部取り込む          |
   | 記録と同じ `size`           | スキップ                                       |
   | `size` が増えた             | 追記された → `indexed_lines + 1` 行目以降のみ   |
   | `size` が減った             | 異常 → 該当 `source_path` を全削除して再構築    |
   | ファイルが消えた            | `sessions` / `messages` / `files` の該当行を削除|

3. 1 ファイル分の取り込みは 1 トランザクションでまとめる
4. 取り込み後 `files` を `(size, mtime, indexed_lines, indexed_at)` で更新

現在進行中のセッションも同じロジックで自然に扱えます（size が増えていく
だけなので、差分追記だけが繰り返される）。

`sessiondb index --full` は `messages` / `messages_fts` / `files` を drop して
ゼロから再構築します。スキーマやトークナイザーを変えたときに使用。

## 構築・導入手順（Python 参照実装）

最小構成：Python 3 標準ライブラリのみ + 選んだトークナイザー拡張。

```bash
# 1. トークナイザー拡張をビルド（vaporetto の例。Rust が必要）
git clone https://github.com/hotchpotch/sqlite-vaporetto
cd sqlite-vaporetto
cargo build --release
# → target/release/libsqlite_vaporetto.so

# 2. インデクサからロード
python3 -c "
import sqlite3
conn = sqlite3.connect('/home/koteitan/.claude/sessiondb/sessions.db')
conn.enable_load_extension(True)
conn.load_extension('/path/to/libsqlite_vaporetto.so')
"
```

拡張が無いときは `tokenize='trigram'` にフォールバックして警告を出す。

## 制約

- `~/.claude/projects/` は **読み取り専用**。絶対に書き込まない。
- インデクサは**冪等**。元データに変化が無ければ 2 度目以降は no-op。
- ユーザー向け CLI メッセージは日本語（ユーザー設定に合わせる）。

## 関連スキル

- [history](../../skills/history/) — 生のセッションファイルを列挙・閲覧する
  スキル。`sessiondb` はその上に検索機能を追加するもの。
