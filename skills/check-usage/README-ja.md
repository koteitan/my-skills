[← Back](../../README-ja.md) | [English](README.md) | [Japanese](README-ja.md)

# check-usage

Claude Code の **5時間枠**と**週次**の rate limit（Max プランの利用上限）について、
「今どれだけ使ったか」「いつリセットされるか」「今のペースだと何時に上限に当たるか」を
**エージェント自身が**知ることができるスキルです。

人間はステータスラインを見れば残量が分かりますが、エージェントには見えていません。
その状態で長い作業を始めると、上限に当たった瞬間に途中で力尽きます。このスキルを入れると、
エージェントは着手前や作業の合間に残量と上限到達予測を確認できるので、

- 残りが乏しければ、大きな workflow に着手せず先に区切りをつける
- サブエージェントを何十個も並列に投げるか、少数で回すかを決める
- リセット時刻をまたぐように作業を割る

といったペース配分ができ、長い作業が中途で死ぬのを避けられます。

## なぜ fanout の前に見る価値があるか

公式ドキュメントも
[「large workflow fanout のような一気の高負荷は、5時間枠がリセットされる前に週次を
使い切りうる」](https://code.claude.com/docs/en/errors.md)と警告しています。問題は、
そこで死んだときの損失が大きいことです。

**rate limit でサブエージェントが死ぬと、そのコンテキストは全損します。** 死んだ
`agent()` は journal に `{"type":"result","value":null}` としか残らず、
`resumeFromRunId` で再開しても素のプロンプトから新しい agent がやり直すだけです
（完了済みの agent はキャッシュ再生されます）。生き残るのは**ディスクに書いたファイル
だけ**で、復旧経路はディスクの成果物か session jsonl の掘り起こしの2つしかありません。
10分ぶんの作業を全部インメモリに持っている agent は、丸ごと消えます。

だから manager 役のエージェントは、fanout に着手する前と各フェーズの合間にこのスキルを
叩いて、規模を決めたり、リセットをまたぐ形に割り直したりできます。

### 予測は「非対称に」読む

ここが肝心です。**予測は過去のペースからの外挿なので、fanout の直前が最も当てになりません。**
これから並列16本を投げようという瞬間の予測は、必ず過小評価です。したがって:

- **予測が出ている**（リセット前に 100% に当たる）→ 強いシグナル。信じて着手しない。
- **予測が出ていない** → **余裕がある証明ではない**。「ペースが変わらなければ」という
  条件付きにすぎず、fanout はそのペースを壊す行為そのものです。

fanout の規模を見積もるなら、予測よりも `~/.claude/statusline-usage.log` を直接見て
**前回の同規模の Wave で実際に何%動いたか**を読む方が確実です。

### ディスク規律は無条件で

「上限が近づいたら保存させる」という条件付きの運用にはしないでください。コンテキストは
rate limit 以外（API エラー、compaction、中断）でも失われますし、予測が外れるのは
「まだ余裕がある」と判断したときだからです。1 agent = 1 ファイル、早めに `.draft` を
書かせる、インメモリ蓄積をさせない、を常時のルールにしたうえで、このスキルは
**着手判断**に使うのが正しい役割分担です。

## 出力例

```console
$ python3 ~/.claude/skills/check-usage/scripts/check-usage.py
5 hours limit:  90% used, will reset at 07/17 09:40, limited at 07/17 08:54 in the current pace
weekly limit :  51% used, will reset at 07/17 20:00, not projected to hit the limit before the reset
```

上の例は「5時間枠は 90% 消費済み。このペースだと 08:54 に上限に当たり、09:40 まで
解放されない」「週次は 51% 消費済みで、リセット（07/17 20:00）までに上限へは届かない
見込み」という意味です。

## インストール

このスキルは、リポジトリ直下の
[statusline-command.sh](../../statusline-command.sh) が書き出すログを読みます。
**Claude Code の標準状態ではこのログは存在しません**。素の Claude Code は rate limit
の値を statusLine に渡すだけで、どこにも記録しないからです。したがって、スキル本体と
statusline-command.sh の**両方**を入れる必要があります。

```bash
# 1. スキル本体
ln -s "$PWD/skills/check-usage" ~/.claude/skills/check-usage

# 2. ログを書き出す statusLine スクリプト
ln -s "$PWD/statusline-command.sh" ~/.claude/statusline-command.sh
```

次に `~/.claude/settings.json` で statusLine として設定します：

```json
"statusLine": { "type": "command", "command": "bash /home/<user>/.claude/statusline-command.sh" }
```

以降、statusLine が描画されるたびに `~/.claude/statusline-usage.log` にサンプルが
追記されます。**予測にはサンプルが2点以上必要**なので、入れた直後は使用率とリセット
時刻だけが出て、予測は少し使ってから出るようになります。ログの場所は環境変数
`STATUSLINE_USAGE_LOG` で変更できます。

## 仕組み

Claude Code は statusLine コマンドに JSON を流し込んでおり、その中に**サーバー側**の
rate limit 状態が入っています。

- `.rate_limits.five_hour.{used_percentage, resets_at}`
- `.rate_limits.seven_day.{used_percentage, resets_at}`

statusline-command.sh はこの値をサンプルとして
`~/.claude/statusline-usage.log` に追記します。1行1サンプルで、値が無いときは `-` です。

```
<epoch> <5時間%> <週次%> <5時間のresets_at> <週次のresets_at>
```

本スクリプトはこのログを読み、

1. 最新行から現在の使用率とリセット時刻を取り、
2. **同じ `resets_at` を持つ行**＝現在のウィンドウのサンプル列に対して
   最初の点と最新の点を結ぶ傾き（%/秒、実時間ベース）を取り、
3. その傾きを 100% まで外挿して上限到達時刻を予測します。

## 予測についての注意

- 予測はリセットより**前**に 100% へ到達する場合だけ表示します。そうでなければ
  リセットが先に来るので警告する意味がありません。
- 傾きは実時間（wall-clock）ベースなので、アイドル時間も含めて平均化されます。
  「席を外していた時間」も分母に入る、意図的な設計です。
- ウィンドウの序盤は使用率がまだ動いておらず（元データの分解能が 1%）、予測が出ません。
  ただしそれは残量に余裕がある時間帯でもあります。
- ログにサンプルが溜まるのは statusLine が描画されたときだけなので、
  Claude Code をしばらく使っていない期間はサンプルが飛びます。
