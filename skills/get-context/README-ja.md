[← Back](../../README-ja.md) | [English](README.md) | [Japanese](README-ja.md)

# get-context

現在のセッションのコンテキストウィンドウ使用率を、セッション JSONL の
`usage` メタデータからローカルに算出して提示する Claude Code スキルです。

## 使い方

```bash
skills/get-context/scripts/get-context        # -> 12.4%
GET_CONTEXT_RAW=1 skills/get-context/scripts/get-context   # -> 12.4% (123977/1000000 tokens)
```

## 仕組み

1. `$CLAUDE_CODE_SESSION_ID` のみで現在のセッション JSONL を特定
   （`~/.claude/projects/**/<session-id>.jsonl`）。変数が未設定なら推測せず
   エラー終了する（間違ったセッションを拾うより失敗する方が安全なため）。
2. 各アシスタントメッセージに自動付与される **最後の** `usage` フィールドを読む。
   直前までのコンテキストは毎ターン cache から再読込されるため、最新エントリが
   会話全体を反映する。
3. `context_tokens = input + cache_creation + cache_read + output` を求め、
   `pct = context_tokens / CONTEXT_WINDOW * 100`。

## 環境変数

| 変数 | 既定値 | 意味 |
|------|--------|------|
| `CONTEXT_WINDOW` | `1000000` | コンテキストウィンドウのトークン数 |
| `GET_CONTEXT_RAW` | (未設定) | `1` にすると生のトークン数も表示 |

## 注意

これは Claude 本体が見ている正確な値ではなくローカル推定値ですが、`/context`
の数値とほぼ一致します（算出 11.9% に対し表示 12% など）。正確な
`context_window.used_percentage` は Claude Code が status line に渡す stdin
ペイロードにのみ含まれ、スタンドアロンのスクリプトからは取得できません。

## インストール

```bash
ln -s "$PWD/skills/get-context" ~/.claude/skills/get-context
```
