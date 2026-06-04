[← Back](../../README-ja.md) | [English](README.md) | [Japanese](README-ja.md)

# autonomy-stat

Claude Code エージェントの自走力 —— 1ターンあたりの**自走時間**（self-running
time）—— をセッションの JSONL ログから算出し、依存ライブラリなしの
インタラクティブな HTML レポートとして書き出す Claude Code スキルです。

## 使い方

```bash
skills/autonomy-stat/scripts/autonomy-stat.py stat <session-id|project-dir> <outfile.html> [--lang en|ja]
```

第1引数は次のいずれかを受け付けます。

- セッション UUID（`~/.claude/projects/*/` 全体から検索）
- `*.jsonl` へのフルパス
- `-home-user-dir` 形式のプロジェクトディレクトリ名（そのプロジェクトの**最新**
  セッションを採用）

`--lang` でレポート UI の言語を指定します（`en`＝デフォルト / `ja`）。翻訳されるのは
UI ラベルだけで、解析対象のデータ（入力 prompt 等）は翻訳されません。

例:

```bash
skills/autonomy-stat/scripts/autonomy-stat.py stat -home-user-myproject /tmp/myproject.html
skills/autonomy-stat/scripts/autonomy-stat.py stat -home-user-myproject /tmp/myproject.html --lang ja
```

生成された HTML をブラウザで開いてください。

## レポートの内容

縦に並んだ2つの折れ線グラフ（ダークモード・外部依存なし）と、ターンごとの表
で構成されます。

- **上のグラフ（青）** — tool待ち**を除いた**自走時間。エージェントが実際に
  考えて生成していた時間。
- **下のグラフ（橙）** — tool待ち**を含む**自走時間（モデル稼働 + ツール実行 +
  承認待ち）。

各グラフは自分のデータに合わせて縦軸を自動スケールし、横軸は1日単位（ローカル
時刻）です。点にカーソルを合わせるとターンごとの内訳が出ます。2本の差が
「tool待ち時間」で、長いツール実行や放置された承認待ちの発見に役立ちます。

## 仕組み

1. **履歴リプレイの除去。** `/compact` や resume は古いログを当時の
   タイムスタンプのまま再注入します。単調増加クロックから大きく後退した
   エントリはリプレイとみなして破棄します。
2. **本物の人間入力の判定**でターン境界を決めます。ツール結果・メタ行・
   サイドチェーン・harness 注入（タスク通知、スラッシュコマンド出力、
   システムリマインダ、compaction サマリ）は除外します。
3. **ターン分割**（連続入力は1境界にまとめる）。ターンの活動は、次の人間
   入力までの assistant 応答とツール結果です。
4. **イベント間ギャップの分類**:
   - **ツール結果**の直前 → tool待ち（全部カウント）
   - **assistant** 直前で5分以内 → 作業
   - **assistant** 直前で5分超 → 5分ぶんだけ作業、残りはスリープ/放置として
     **除外**
5. ターンごとに2系列を出力: `作業`（青）と `作業 + tool待ち`（橙）。
6. ターン間の待機（エージェント停止中・人間が不在）は自走に一切含めません。

## 調整できる定数

| 定数 | 既定値 | 意味 |
|------|--------|------|
| `IDLE_THRESHOLD_MS` | 5分 | assistant ギャップを作業とみなす上限。超過分はスリープ/放置扱い。最も効くつまみ。 |
| `REPLAY_TOLERANCE_MS` | 60秒 | `/compact` リプレイと判定するまでの、タイムスタンプ後退の許容量。 |

tool待ちのギャップにはあえて上限を掛けず、込み・抜きの2系列を両方見せること
で判断できるようにしています。

## インストール

```bash
ln -s "$PWD/skills/autonomy-stat" ~/.claude/skills/autonomy-stat
```
