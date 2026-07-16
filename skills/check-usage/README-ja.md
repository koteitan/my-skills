[← Back](../../README-ja.md) | [English](README.md) | [Japanese](README-ja.md)

# check-usage

Claude Code の **5時間枠**と**週次**の rate limit（Max プランの利用上限）について、
「今どれだけ使ったか」「いつリセットされるか」「今のペースだと何時に上限に当たるか」
を1コマンドで表示する Claude Code スキルです。

## 出力例

```console
$ python3 ~/.claude/skills/check-usage/scripts/check-usage.py
5 hours limit:  90% used, will reset at 07/17 09:40, limited at 07/17 08:54 in the current pace
weekly limit :  51% used, will reset at 07/17 20:00, not projected to hit the limit before the reset
```

上の例は「5時間枠は 90% 消費済み。このペースだと 08:54 に上限に当たり、09:40 まで
解放されない」「週次は 51% 消費済みで、リセット（07/17 20:00）までに上限へは届かない
見込み」という意味です。

## 仕組み

Claude Code は statusLine コマンドに JSON を流し込んでおり、その中に**サーバー側**の
rate limit 状態が入っています。

- `.rate_limits.five_hour.{used_percentage, resets_at}`
- `.rate_limits.seven_day.{used_percentage, resets_at}`

`~/.claude/statusline-command.sh` はこの値をサンプルとして
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

## ローカルの JSONL から窓を再構成しないこと

`ccusage blocks` のようなツールは、ローカルの JSONL の最初のアクティビティを
時単位に切り捨ててウィンドウ境界を**推測**するため、実際のリセット時刻とずれます
（2026-07-17 の実測では ccusage が 09:00 リセットと表示した一方、本当の `resets_at`
は 09:40 でした）。本スキルが読む `rate_limits` はサーバーが返す値なので、そちらが
正です。

## 前提

- `~/.claude/statusline-command.sh` が statusLine として設定され、
  `~/.claude/statusline-usage.log` にサンプルを追記していること。
- ログの場所は環境変数 `STATUSLINE_USAGE_LOG` で変更できます。

## インストール

```bash
ln -s "$PWD/skills/check-usage" ~/.claude/skills/check-usage
```
