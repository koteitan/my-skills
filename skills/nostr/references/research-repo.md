# ~/code/nostr-research — 既存実装の調査資料

koteitan 自身の調査リポジトリ (github: koteitan/nostr-research)。
「他のクライアント/リレーは実際どうしているか」を知りたくなったら**推測せずここを読む**。
各ページは英語版 `README-en.md` と日本語版 `README-ja.md` の対で存在する
(トップだけ `README.md` / `README-ja.md`)。

## どの情報が要るとき、どれを見るか

| 知りたいこと | 見るファイル |
|---|---|
| 各クライアントの bootstrap relay の選び方 / リレー取得方法 / search relay / リアクション取得 / 画像アップロード / フレームワーク | `client/README-en.md` (概要表) |
| 上記の**クライアント個別の根拠** (該当コードの引用付き) | `client/evidences/<topic>/<client>.md` — topic = `bootstrap-relay`, `relay`, `search-relay`, `reaction-for-events`, `image-upload`。client = nostter, rabbit, lumilumi, nos-haiku, nostrudel, coracle, damus, amethyst, primal, iris, yakihonne, algia, kakoi, nosame, nullnull, flowgazer |
| リレー実装 (strfry / nostr-rs-relay / khatru / nostream / haven …) のシェア、`limit` の挙動、レート制限、フィルタ値・メッセージサイズ上限、時刻ベース制限 | `relay/README-en.md`、根拠は `relay/evidences/` |
| 実在リレーインスタンスの NIP-11 制限値 (max_message_length, max_subscriptions, max_limit, max_filters, max_event_tags, max_content_length …) | `relay-instances/README-en.md` |

## 使い方の指針

- 「limit はいくつまで送っていい?」「このリレーは購読を何本張れる?」→
  `relay-instances/README-en.md` の表を引く (推測しない)。
- 「うちのクライアントの bootstrap relay はこれでいいか?」→
  `client/README-en.md` の bootstrap 表で他クライアントと比較する。
- 記載が古い可能性がある場合は各ページ冒頭の *Last updated* / *Last Checked*
  を見る。更新が必要なら、リポジトリ内の
  `skills/nostr-research-update-client` / `skills/nostr-research-update-relay`
  が更新手順。
- 表に無いクライアント/リレーを調べたときは、この資料への追記を提案してよい。
