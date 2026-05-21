[← 戻る](../../README-ja.md) | [English](README.md) | [Japanese](README-ja.md)

# compact-unfreeze

Remote Control ＋ `/compact` の入力フリーズバグ
（[issue #51267](https://github.com/anthropics/claude-code/issues/51267)）を、
tmux もローカルのキー操作も使わずに回避する Claude Code スキル。

## バグの内容

**リモート（モバイル）クライアントから `/compact`** を実行すると、その直後の
リモート入力が固まる。`× <text>` と表示され、キューに入ったまま配信されない。
ローカル入力は常に通り、固まるのはリモート経路だけ。ローカルの TTY イベントが
入力ループを起こすまで解除されない。

## 回避策

compact の**前に**、ワンショットのバックグラウンド **Monitor**（`sleep`
タイマー）を仕掛けておく。Monitor タスクは `/compact` を跨いで生き残り、
タイマー発火時に agent が再起動される。このループ1回分の処理は——
**ツールを一切実行せず、テキストを一言返すだけでも**——固まったキューを
フラッシュする。これでリモート入力が自動で復活する。

クリーンな在席テストで確認済み：凍結プローブは Monitor 発火の5秒後に流れ、
agent はツールを1つも実行していなかった。

## 使い方

これは指示型スキルで、実行する CLI はない。agent が `SKILL.md` を読み、
リモートから `/compact` しようとしている場面で：

1. `Monitor` ツールを読み込む（`ToolSearch("select:Monitor")`）。
2. `sleep 240`（~1〜2分の compact ＋マージンをカバー）と `timeout_ms: 300000`
   でワンショット Monitor を仕掛ける。
3. ユーザーが `/compact` を実行。Monitor 発火時に agent が返信し、固まった
   キューがフラッシュされる。

正確なツール呼び出し、タイミングの注意点、セッション JSONL からの検証方法は
[SKILL.md](SKILL.md) を参照。

## 関連

- 手動の代替手段：任意のローカル入力、または `tmux send-keys -t <pane>
  Escape`。Monitor 経路はどちらも不要。
