[English](README.md) | [Japanese](README-ja.md)

# my-skills

Claude Code のスキル・スラッシュコマンド・ヘルパースクリプトのコレクションです。バージョン管理で管理しています。

## 構造

```
skills/<skill-name>/SKILL.md
commands/<command-name>.md
bin/<script-name>
statusline-command.sh
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

# statusLine コマンド
ln -s "$PWD/statusline-command.sh" ~/.claude/statusline-command.sh
```

## スキル一覧

| スキル | 説明 |
|--------|------|
| [compact-unfreeze](skills/compact-unfreeze/) | Remote Control ＋ `/compact` の入力フリーズバグを、バックグラウンド Monitor の発火でキューをフラッシュして回避 |
| [autonomy-stat](skills/autonomy-stat/) | エージェントの1ターンあたりの自走時間をセッション JSONL から算出し、インタラクティブな HTML グラフ（モデル稼働 vs tool待ち）として描画 |
| [check-usage](skills/check-usage/) | 5時間枠と週次の rate limit の状態を報告：使用率・リセット時刻・現ペースでの上限到達予測 |
| [mermaid](skills/mermaid/) | Mermaid 図のルール：ノードに背景色を使わない・ひし形を使わない・キャプションは短く |
| [manim-tts](skills/manim-tts/) | manim + VOICEVOX で音声付き解説動画を作るときの罠：キャッシュで音声が落ちる・消したはずの図形が復活する・日本語で LaTeX が落ちる |
| [my-github-md-rule](skills/my-github-md-rule/) | GitHub 上で日英バイリンガルの markdown ドキュメントを生成するルール |
| [github-math-check](skills/github-math-check/) | Markdown の数式が GitHub 側の変換を経ても壊れないか、ブラウザに渡る文字列そのものを描画して検証 |
| [nostr](skills/nostr/) | Nostr 作業の集約：リレー探索・NIP-19 bech32 の自前実装・CLI でのリレー調査・Web アプリの標準構成 |
| [webapp-defaults](skills/webapp-defaults/) | 素の Web ページを作るときの既定：ダークモード ON・右上ハンバーガーメニュー・UI 状態を localStorage に保存 |
| [sessiondb](skills/sessiondb/) | Claude Code セッション JSONL ログを SQLite + FTS5 で全文検索 |
| [use-bms](skills/use-bms/) | [yaBMS](https://github.com/koteitan/yaBMS) の `c/bms` CLI をビルドして使う：バシク行列の展開・比較・標準判定・ループ検出 |

## スラッシュコマンド一覧

| コマンド | 説明 |
|---------|------|
| [check-win-update](commands/check-win-update.md) | Windows Update の保留中更新を取得し X で不具合報告を確認 |

## bin/ スクリプト一覧

| スクリプト | 説明 |
|-----------|------|
| [claude-pushover](bin/claude-pushover) | Claude Code の会話要約を Pushover で通知（Stop フック想定） |
| [pushover](bin/pushover) | Pushover API への薄い `curl` ラッパー |
| [live-server-sil](bin/live-server-sil) | `live-server` を静かにバックグラウンド起動しクリック可能な URL を表示 |
| [live-server-list](bin/live-server-list) | 動作中の `live-server` を PID・URL・配信ディレクトリで一覧表示 |
| [live-server-kill](bin/live-server-kill) | 動作中の `live-server` を停止（唯一のインスタンス、または port 指定） |
| [sessiondb](bin/sessiondb) | Claude Code セッション JSONL ログの SQLite + FTS5 インデックス構築と検索 |
| [sessionmv](bin/sessionmv) | ディレクトリを Claude Code セッションごと移動。`--codex` で Codex の JSONL・状態メタデータにも対応 |
| [newline](bin/newline) | ファイルの改行コード（CR / LF / CRLF）を判定 |
| [nostrsocat](bin/nostrsocat) | Nostr リレー照会用の `websocat` ラッパー |
| [codexps](bin/codexps) | `codex:rescue` ジョブを一覧し、生存中のものとプロセスが消えた記録を判別 |

## statusLine

[statusline-command.sh](statusline-command.sh) は2行のステータスラインを描画します。
1行目は `host:dir`、2行目はコンテキストウィンドウと 5時間枠 / 週次の rate limit の
ゲージ（それぞれ上限到達予測つき）、モデル名、effort です。あわせて rate limit の
読み取り値を `~/.claude/statusline-usage.log` に追記しており、これが
[check-usage](skills/check-usage/) スキルの読むデータになります。

`~/.claude/settings.json` の `statusLine.command` から参照します：

```json
"statusLine": { "type": "command", "command": "bash /home/<user>/.claude/statusline-command.sh" }
```

## ライセンス

[MIT](LICENSE)
