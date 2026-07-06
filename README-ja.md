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
| [compact-unfreeze](skills/compact-unfreeze/) | Remote Control ＋ `/compact` の入力フリーズバグを、バックグラウンド Monitor の発火でキューをフラッシュして回避 |
| [autonomy-stat](skills/autonomy-stat/) | エージェントの1ターンあたりの自走時間をセッション JSONL から算出し、インタラクティブな HTML グラフ（モデル稼働 vs tool待ち）として描画 |
| [my-github-md-rule](skills/my-github-md-rule/) | GitHub 上で日英バイリンガルの markdown ドキュメントを生成するルール |
| [sessiondb](skills/sessiondb/) | Claude Code セッション JSONL ログを SQLite + FTS5 で全文検索 |

## スラッシュコマンド一覧

| コマンド | 説明 |
|---------|------|
| [check-win-update](commands/check-win-update.md) | Windows Update の保留中更新を取得し X で不具合報告を確認 |

## bin/ スクリプト一覧

ヘルパースクリプトの一覧と説明は [`bin/README-ja.md`](bin/README-ja.md) を参照。

## ライセンス

[MIT](LICENSE)
