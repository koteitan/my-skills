[English](README.md) | [Japanese](README-ja.md)

# my-skills

Claude Code のスキル・スラッシュコマンド・ヘルパースクリプトのコレクションです。バージョン管理で管理しています。

## 構造

```
skills/<skill-name>/SKILL.md
commands/<command-name>.md
bin/<script-name>
```

## インストール

それぞれの設置先へシンボリックリンクを作成します：

```bash
# スキル
ln -s "$PWD/skills/<skill-name>" ~/.claude/skills/<skill-name>

# スラッシュコマンド
ln -s "$PWD/commands/<command-name>.md" ~/.claude/commands/<command-name>.md

# ヘルパースクリプト（$PATH の通ったディレクトリ）
ln -s "$PWD/bin/<script-name>" ~/bin/<script-name>
```

## スキル一覧

| スキル | 説明 |
|--------|------|
| [my-github-md-rule](skills/my-github-md-rule/) | GitHub 上で日英バイリンガルの markdown ドキュメントを生成するルール |

## スラッシュコマンド一覧

| コマンド | 説明 |
|---------|------|
| [check-win-update](commands/check-win-update.md) | Windows Update の保留中更新を取得し X で不具合報告を確認 |

## bin/ スクリプト一覧

| スクリプト | 説明 |
|-----------|------|
| [claude-pushover](bin/claude-pushover) | Claude Code の会話要約を Pushover で通知（Stop フック想定） |
| [pushover](bin/pushover) | Pushover API への薄い `curl` ラッパー |
| [live-server-list](bin/live-server-list) | 動作中の `live-server` のポート一覧を表示 |
| [mv-session](bin/mv-session) | ディレクトリと対応する `~/.claude/projects/` セッションを一緒に移動 |
| [newline](bin/newline) | ファイルの改行コード（CR / LF / CRLF）を判定 |

## ライセンス

[MIT](LICENSE)
