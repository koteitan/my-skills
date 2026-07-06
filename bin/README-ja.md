[← 戻る](../README-ja.md) | [English](README.md) | [Japanese](README-ja.md)

# bin/

単体で動く補助スクリプト集。このディレクトリを `PATH` に追加するか、
個別に symlink を張って使う。

## 通知

- **pushover** — `curl` の薄いラッパ。`pushover <message>` で iPhone Pushover
  通知を送る。環境変数 `PUSH_OVER_TOKEN` と `PUSH_OVER_USER` が必要。
- **claude-pushover** — Claude Code のフック用。直近の会話メッセージを抽出して
  Pushover 経由で送信（`Stop` フックとして使う想定）。

## live-server

- **live-server-sil** `[port]` — カレントディレクトリを配信する `live-server`
  をバックグラウンドで静かに起動し、クリック可能な URL（OSC 8）を1行だけ表示。
- **live-server-list** — 動作中の `live-server` を PID・URL・配信ディレクトリで一覧表示。
- **live-server-kill** `[port]` — 動作中の `live-server` を停止。無引数のときは
  唯一の実行中インスタンスを、複数ある場合は port を指定して kill。

## セッション／プロジェクトディレクトリ

- **sessiondb** — Claude Code セッション JSONL の SQLite + FTS5 全文索引。
  サブコマンド：`index` / `search` / `stats` / `size` / `show` / `help`。
  詳細は [`skills/sessiondb/`](../skills/sessiondb/)。
- **sessionmv** `<src> <dst>` — ディレクトリを移動しつつ、対応する
  `~/.claude/projects/` 配下のセッションディレクトリ（サブディレクトリ分も含む）
  も同時に移動し、セッション JSONL 内の `cwd` パスも書き換える。
- **mv-session** `<src> <dst>` — `sessionmv` の旧・簡易版。ディレクトリと単一の
  `~/.claude/projects/` セッションディレクトリを移動するだけで、JSONL の中身は
  書き換えない。

## テキスト／プロトコル

- **newline** — ファイルの改行コード種別（CR / LF / CRLF）を判定。
- **nostrsocat** — Nostr リレー用の `websocat` ラッパ：
  `nostrsocat <relay> <k1> <v1> <k2> <v2> …`。`websocat` が必要。
