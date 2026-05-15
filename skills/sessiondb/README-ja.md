[← Back](../../README-ja.md) | [English](README.md) | [Japanese](README-ja.md)

# sessiondb

Claude Code のセッションログ（JSONL）を SQLite + FTS5 でインデックス化し、
過去の会話を全文検索できるようにする Claude Code スキル。日本語の形態素解析と
英数字をそのまま扱うトークナイザーを組み合わせ、日英混在テキストでも精度良く
ヒットします。

## 何ができるか

Claude Code は会話を `~/.claude/projects/` 配下に JSONL で保存します。利用が
進むと数百 MB 〜 GB に積み上がり、`grep` では遅く・不正確（特に日本語は
空白で語が区切られないため）になります。

`sessiondb` は SQLite + FTS5 の差分インデックスを構築し、以下を可能にします：

- 過去セッションをキーワードやトピックでミリ秒検索
- 見つけたセッションを `claude --resume <session_id>` で再開
- プロジェクト別・時系列・セッションサイズなどの統計取得

## データベースの場所

既定: `~/.claude/sessiondb/sessions.db`

元データの `~/.claude/projects/` の隣に置くことで、`~/.claude/` を丸ごと
バックアップすれば索引も一緒に保全されます。環境変数 `SESSIONDB_PATH` で
上書き可能。

## クイックスタート

```bash
# インデックス構築（初回はフル、以降は差分更新）
sessiondb index

# 検索
sessiondb search "形態素解析"
sessiondb search "FTS5" --project -home-koteitan-my-skills

# 見つけたセッションを再開
claude --resume <session_id>
```

## このスキルのファイル

| ファイル | 役割 |
|---------|------|
| [SKILL.md](SKILL.md) | エージェント向けプロンプト（起動条件・呼び出し方） |
| [how-to-create-db-ja.md](how-to-create-db-ja.md) | スキーマ・トークナイザー・取り込みロジック・構築手順 |

## ステータス

現状は仕様のみ。`bin/sessiondb` は未実装。CLI ができるまでは、SKILL.md の
記述により Claude が直接 SQLite クエリを発行して検索を代行します。
