[English](README-en.md) | [Japanese](README.md)

# use-fandom

Fandom (MediaWiki) 上のページとファイルを閲覧・編集するためのスキル。

主な用途:
- ブログ記事やユーザーページの新規作成・更新
- 画像ファイルのアップロード
- 既存ページの読み取り

API のベースは `https://<wiki>.fandom.com/<lang>/api.php` (例: `https://googology.fandom.com/ja/api.php`)。

## ボットパスワードの作り方

Fandom のボットパスワードは **wiki ごとに独立** して発行される (Fandom 全体で共通ではない)。 複数言語版 (ja / en) に投稿する場合は、 **両方の wiki で別々に作成** する必要がある。

1. Fandom に自分のアカウントでログインする。
2. `Special:BotPasswords` を開く:
   - 日本語版: `https://googology.fandom.com/ja/wiki/Special:BotPasswords`
   - 英語版: `https://googology.fandom.com/wiki/Special:BotPasswords`
3. ボット名を決めて作成する (例: `claude`)。 実際のログイン ID は `ユーザー名@ボット名` の形式 (例: `Koteitan@claude`)。
4. 権限 (grants) は最小限に:
   - **Basic rights**
   - **Edit existing pages**
   - **Create, edit, and move pages** ← ファイルアップロード時にも必要 (ファイル説明ページの新規作成のため)
   - **Upload new files** (画像をアップするとき)
   - **Upload, replace, and move files** (既存画像を差し替えるとき)

   それ以外の権限は付けない (削除・ブロック・保護などは漏洩時の被害を大きくする)。
5. **Allowed pages for editing** は空のまま。 限定するとファイルページも触れなくなり、アップロードが止まる。
6. **IP ranges** は空のまま。
7. 作成直後に表示されるパスワードは **一度しか見られない**。 すぐ環境変数などに保存する。

**ja と en で同じ名前のボットを作っても、パスワード文字列は別物になる**。 両方保存すること。

## エージェントへの渡し方

### 推奨: 環境変数

Claude Code を起動する前のシェルで (`wiki` ごとに分けておく):

```sh
# 日本語版
export GWIKIJA_BOT_USER='Koteitan@claude'
export GWIKIJA_BOT_PASSWORD='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

# 英語版
export GWIKIEN_BOT_USER='Koteitan@claude'
export GWIKIEN_BOT_PASSWORD='yyyyyyyyyyyyyyyyyyyyyyyyyyyyyy'
```

永続化したい場合は `~/.bashrc` に書く (ファイルのパーミッションは `chmod 600 ~/.bashrc` 相当にしておく)。

**注意**: 環境変数は同じユーザーで動く別プロセスから `/proc/<pid>/environ` で読める。 chmod 600 ファイルより特別に安全ではない。

### 代替: ファイル

```sh
cat > ~/.fandom-bot <<'EOF'
GWIKIJA_BOT_USER=Koteitan@claude
GWIKIJA_BOT_PASSWORD=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GWIKIEN_BOT_USER=Koteitan@claude
GWIKIEN_BOT_PASSWORD=yyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
EOF
chmod 600 ~/.fandom-bot
```

## ワークフロー

Fandom へ記事を投稿するときの標準手順。 各ステップでユーザーの明示的な確認を取る。

1. **ユーザーによるアップロードするファイルのファイル名の確認**
2. **ユーザーによる作成するページ名の確認**
3. **ファイルのアップロード**
4. **ユーザーによるファイルのアップロードの確認**
5. **ページ作成・編集**
6. **ユーザーによる最終確認**

複数言語版を書く場合は、原稿 (`main.md`) → wiki 用 (`fandom.txt`) → 翻訳 (`fandom-en.txt`) の順に段階的に作る。 各段階で `action=parse` のプレビューと目視確認を取る。 詳細な変換ルール (`$...$` → `\( ... \)`、 `|` 表 → `{| class="wikitable" |}` など) は `SKILL.md` を参照。

## 英語版 Googology Wiki の落とし穴

- **ボットパスワードは wiki ごとに独立**: 日本語版で作ったパスワードは英語版では認証されない。
- **User blog の API 新規作成が封じられている** (英語版のみ): `action=edit` では permissiondenied。 ユーザーに `Special:CreateBlogPage` で空ページ (タイトルだけ、本文は "Draft" でよい) を作ってもらってから、 ボットで本文を上書きする。 日本語版は API で新規作成可能。
- **同じアカウントでも wiki ごとに所属グループが違う**: ja で sysop (管理者) でも en では通常ユーザー扱いということがある。 ログイン後に `uiprop=groups|rights` で必ず検証する。

詳細はエージェント向け手順書 `SKILL.md` の §9.5 を参照。

## 動作確認

```sh
curl -s --max-time 20 'https://googology.fandom.com/ja/api.php?action=query&meta=userinfo&format=json' \
  --cookie-jar /tmp/fandom-cookies.txt \
  --cookie /tmp/fandom-cookies.txt
```

ログインしていないときは `"id":0,"name":"<IP>"` 相当が返る。
