# use-fandom (SKILL.md)

Fandom (MediaWiki) 上のページ・ファイルを編集するエージェント向け手順。巨大数研究 Wiki (googology.fandom.com, ja + en) で検証した具体的なノウハウも含む。

## 前提

- ボットパスワードは **wiki ごと** に発行される (Fandom 全体ではなく)。ja と en で別ユーザー名・別パスワード。環境変数の命名例:
  - `GWIKIJA_BOT_USER` / `GWIKIJA_BOT_PASSWORD` (日本語版)
  - `GWIKIEN_BOT_USER` / `GWIKIEN_BOT_PASSWORD` (英語版)
- `BASE` を wiki ごとに切り替える:
  - ja: `https://googology.fandom.com/ja/api.php`
  - en: `https://googology.fandom.com/api.php` (サブパスなし)
- クッキーファイルも wiki ごとに別ファイルを使う。
- 1 セッション内では同じ `COOKIES` を使い回す (ログイン・編集・アップロードで共有)。
- 全ての書き込みは `POST` + `format=json`。
- 書き込みの前に `csrftoken` を 1 回だけ取る。

**鉄則**:
- パスワードはチャットに書き出さない。コマンドの `--data-urlencode` 値には変数を使う。
- 投稿前に **必ずユーザーの承認を取る**。ブログ記事はログイン直後に全世界公開される。
- `prop=info|revisions` でページ存在 (`missing` キー) とサイズを先に確認する。

## ワークフロー

各ステップでユーザーの明示的な確認を取ってから次へ進む。

1. **ファイル名の確認**
   - 記事中の画像を抽出し、Fandom 上での名前 (1 文字目大文字化、既存ファイルとの衝突チェック) を一覧で提示する。
   - 既存ファイルは `prop=imageinfo` の `missing` キーで判定。
2. **ページ名の確認**
   - 本名前空間 / `ユーザーブログ:…` / `利用者:…` のどれか。
   - 既存ページは編集扱い、新規は作成扱い。
3. **ファイルのアップロード**
   - まず 1 枚だけ上げてユーザーに表示とライセンス表記を確認してもらう。残りは承認後にまとめて。
4. **ページ作成・編集**
   - `action=parse` で事前プレビュー → 本文が崩れていないか確認してから `action=edit`。
   - 英語版 Googology Wiki の User blog は **API での新規作成不可**。 先にユーザーが UI (`Special:CreateBlogPage`) で空ページを作る必要がある。
5. **最終確認**
   - レンダリング済み HTML を取得して検証。構造 (見出し / 表 / 画像) と error class を数える。
   - 画像パスは全部解決 (`missing` 要素なし) を確認。

## 1. ログイン

```sh
BASE='https://googology.fandom.com/ja/api.php'   # 英語は '/api.php'
COOKIES=/tmp/fandom-ja-cookies.txt

LOGIN_TOKEN=$(curl -s -b "$COOKIES" -c "$COOKIES" --get "$BASE" \
  --data-urlencode 'action=query' \
  --data-urlencode 'meta=tokens' \
  --data-urlencode 'type=login' \
  --data-urlencode 'format=json' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["query"]["tokens"]["logintoken"])')

curl -s -b "$COOKIES" -c "$COOKIES" "$BASE" \
  --data-urlencode "action=login" \
  --data-urlencode "lgname=$GWIKIJA_BOT_USER" \
  --data-urlencode "lgpassword=$GWIKIJA_BOT_PASSWORD" \
  --data-urlencode "lgtoken=$LOGIN_TOKEN" \
  --data-urlencode 'format=json'
```

- `action=login` を使う (`action=clientlogin` ではない)。ボットパスワード (`username@botname`) 用。
- 結果が `"Success"` 以外は中断。`lgname` 書式ミス、grant 不足などが原因。
- **ログイン直後に rights を検証**: `uiprop=rights` で `edit`, `createpage`, `upload` などが揃っているか確認。足りない場合はこの時点でユーザーに通知。

## 2. CSRF トークン取得

```sh
CSRF=$(curl -s -b "$COOKIES" -c "$COOKIES" --get "$BASE" \
  --data-urlencode 'action=query' \
  --data-urlencode 'meta=tokens' \
  --data-urlencode 'format=json' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["query"]["tokens"]["csrftoken"])')
```

- **ログイン後** に取ること。ログイン前は匿名用の `+\\` が返り、編集に使えない。
- `action=edit`, `action=upload`, `action=move` などで `token=$CSRF` を使う。

## 3. 名前空間マップ (ja ↔ en)

| 番号 | ja | en |
|---|---|---|
| 0 | (本名前空間) | (main) |
| 2 | 利用者 | User |
| 6 | ファイル | File |
| 14 | カテゴリ | Category |
| 500 | ユーザーブログ | User blog |
| 501 | ユーザーブログ・コメント | User blog comment |

言語版の記事を書き分ける際は、画像・内部リンク・カテゴリタグをこのマップで変換する。

## 4. ページ存在チェック

```sh
curl -s -b "$COOKIES" -c "$COOKIES" --get "$BASE" \
  --data-urlencode 'action=query' \
  --data-urlencode 'format=json' \
  --data-urlencode 'prop=info|revisions' \
  --data-urlencode 'rvprop=content' \
  --data-urlencode 'rvslots=main' \
  --data-urlencode "titles=ユーザーブログ:Koteitan/タイトル"
```

- `"missing":""` キーがあれば未作成
- `revisions[0].slots.main["*"]` が本文
- 編集前に `intestactions=edit|create` でその動作が通るかを事前判定できる。失敗する場合は permissiondenied が明示される。

## 5. ページ編集 / 作成

```sh
curl -s -b "$COOKIES" -c "$COOKIES" "$BASE" \
  --data-urlencode 'action=edit' \
  --data-urlencode 'format=json' \
  --data-urlencode "title=ユーザーブログ:Koteitan/タイトル" \
  --data-urlencode "text@body.wiki" \
  --data-urlencode "summary=初版" \
  --data-urlencode "token=$CSRF" \
  --data-urlencode 'bot=1'
```

- `bot=1` を付けると最近の更新で「ボット」フラグがつく (推奨)。
- 既存ページを更新するときは `basetimestamp` と `starttimestamp` を渡すと衝突検出できる。
- 大きな本文は `--data-urlencode "text@body.wiki"` でファイルから読める (推奨)。

## 6. 画像アップロード

```sh
curl -s -b "$COOKIES" -c "$COOKIES" "$BASE" \
  -F 'action=upload' \
  -F 'format=json' \
  -F "filename=Kot-foo.png" \
  -F "comment=記事「…」用" \
  -F $'text=== ライセンス ==\n{{Selfcc}}' \
  -F "token=$CSRF" \
  -F "file=@/path/to/foo.png" \
  -F 'ignorewarnings=1'
```

- ファイル名の 1 文字目は **自動で大文字化**。`kot-foo.png` → `Kot-foo.png`。
- 同名ファイルがあると `fileexists-forbidden` が返る。差し替えは "Upload, replace, and move files" grant が必要。
- 新規は "Upload new files" で足りるが、**同時に "Create, edit, and move pages" が必要** (ファイル説明ページを新規作成するため)。無いと `cantcreate` エラーで `filekey` だけが返る。
- `text` のライセンス節は wiki・著者ごとに決まったテンプレートを使う:
  - 巨大数研究 Wiki (ja): `== ライセンス ==\n{{Selfcc}}`
  - 巨大数研究 Wiki (en): `== Licensing ==\n{{Selfcc}}`
  - 他 wiki でも、既にアップされている類似ファイルの `prop=revisions` で使用テンプレートを調べ、それに合わせる。

## 7. 名前の衝突チェック

アップロード前に:

```sh
curl -s --get "$BASE" \
  --data-urlencode 'action=query' \
  --data-urlencode 'format=json' \
  --data-urlencode 'prop=imageinfo' \
  --data-urlencode 'iiprop=url|size|user|timestamp' \
  --data-urlencode 'titles=File:A.png|File:B.png|File:C.png'
```

- `missing` キーあり → 新規として上げられる
- `imageinfo` あり → 既存。差し替えは "Upload, replace, and move files" grant と `ignorewarnings=1` が必要。

## 8. Markdown → Fandom wikitext 変換ルール

実際に `article/main.md → article/fandom.txt` の変換で検証したルール。巨大数研究 Wiki (googology.fandom.com) で `action=parse` レンダリングエラー 0 を確認した設定。

### 8.1 変換表

| Markdown | Fandom wikitext | 補足 |
|---|---|---|
| `# H1` (冒頭) | 削除 | ページタイトルが見出しの役目を果たす |
| `## X`〜`#### X` | `== X ==`〜`==== X ====` | |
| `**X**` | `'''X'''` | |
| `*X*` | `''X''` | |
| `` `X` `` | `X` (バッククォート削除) | `<code>` は視覚的に邪魔なのでプレーンに |
| `$x$` | `\( x \)` | Googology は client-side MathJax。 `<math>` は使わない |
| `\begin{eqnarray}…\end{eqnarray}` | `\begin{eqnarray*}…\end{eqnarray*}` | `*` 付きで番号を抑制 |
| `![alt](x.png)` | `<div style="max-width:100%; overflow-x:auto; text-align:center;">\n[[ファイル:x.png\|center]]\n</div>` | モバイルでの横オーバーフロー対応 |
| `[text](url)` | `[url text]` | 外部リンク |
| `[text](https://googology.fandom.com/<lang>/wiki/<page>)` | `[[<page>\|text]]` | 内部リンク |
| `[x](../path)` | `[https://github.com/<user>/<repo>/blob/main/<path> x]` | リポジトリ相対パスは絶対 URL 化 |
| Markdown pipe table | `{\| class="wikitable"` ブロック | |
| `- X` / `   - X` | `* X` / `** X` | ネストは 3 スペースで 1 階層 |
| `1. X` | `# X` | ネスト時: `#*` は「順序の下にビュレット」(フルパス表記) |
| `> X` 連続行 | `<blockquote>…</blockquote>` | |
| `---` | `----` | 水平線 |
| ` ```lang \n body \n ``` ` | `<syntaxhighlight lang="lang">body</syntaxhighlight>` | |
| ` ``` \n body \n ``` ` (無指定) | `<pre>body</pre>` | |
| `[^n]` + `[^n]: body` | `<ref name="n">body</ref>` + `<references/>` | orphan は削除 |

### 8.2 落とし穴

- **`<math>` タグは使わない** (Googology の場合)。 サーバー側 texvc で汚い SVG になり、`@`, `eqnarray`, 一部のコマンドが通らない。 client-side MathJax (`\( ... \)` と `$$...$$`、`\begin{eqnarray*}`) を使う。 wiki に MathJax 設定がない場合は `<math>` にフォールバック必要なので事前テスト。
- **見出しに数式を入れない**。 `## 5.2.1 \( x *= p_i \)` などは目次に `UNIQ-...-QINU` プレースホルダがそのまま漏れる。 Unicode (`Σ`, `Θ`, `Ω`, `↑↑↑`) で書き直す。
- **保護順序**: md→wiki 変換では、 コードブロックと `\begin{eqnarray}` ブロックをまずプレースホルダに退避、 `$…$` も退避する。 italic 変換 `*…*` が math 内の `*` を誤爆する。
- **list 変換のタイミング (wiki→md 時)**: 見出し `== X ==` → `## X` と、 wiki の `##` (ネスト順序リスト) が衝突する。 wiki→md では **list を先に** 変換する。 md→wiki では heading を先にして問題ない。
- **list のネスト種別**: wiki はフルパス表記 (`#*` = 順序の下にビュレット、`**` = ビュレットの下にビュレット)。 スクリプトでは親の種別を stack で追跡する。
- **インデントされた display math**: Markdown の `- …\n  \begin{eqnarray}…` のように数式の行が空白で始まると、 restore 後に MediaWiki が `<pre>` でくるんで枠付きになる。 restore 前に先頭の空白を strip する。
- **mermaid**: Fandom では描画されない。 `npx -y @mermaid-js/mermaid-cli -i x.mmd -o x.png -s 2 -b transparent` で PNG 化してアップロード、 `[[ファイル:x.png\|center]]` に差し替え。
- **モバイル画像オーバーフロー**: `<img width="N">` は固定幅。 CSS を注入する手段がないので `<div style="overflow-x:auto">` で横スクロール可能にする。
- **バックティックは全部 `<code>` or プレーン化**: MediaWiki は Markdown のバッククォートを解釈しないので放置するとそのまま文字として表示される。

### 8.3 プレビューで検証

```sh
curl -s --max-time 60 -X POST "$BASE" \
  --data-urlencode 'action=parse' \
  --data-urlencode 'format=json' \
  --data-urlencode 'contentmodel=wikitext' \
  --data-urlencode 'prop=text' \
  --data-urlencode "text@body.wiki" \
  -o /tmp/preview.json
python3 -c '
import json, re
h = json.load(open("/tmp/preview.json"))["parse"]["text"]["*"]
print("math errors   :", len(re.findall(r"構文解析に失敗|[Ff]ailed to parse", h)))
print("error elements:", len(re.findall(r"class=\"[^\"]*error[^\"]*\"", h)))
print("H2/H3/H4      :", len(re.findall(r"<h2", h)), len(re.findall(r"<h3", h)), len(re.findall(r"<h4", h)))
print("tables        :", len(re.findall(r"<table", h)))
print("<math> SVGs   :", len(re.findall(r"mwe-math-element", h)))  # Googology では 0 が望ましい
'
```

- **math errors 0, error 要素 0 を目標**。
- `<math>` SVG が出ているなら `\( ... \)` に移行していない。
- 投稿後も `page=…` で同じ検証をする (MathJax は client-side なので投稿 HTML には SVG として現れない)。

## 9. 言語版の作り方 (ja → en の例)

### 9.1 翻訳の方針

- 画像は共通のファイル名で両 wiki にアップロード (`Kot-hs2maze-*.png`)。
- 内部リンクは言語版別のタイトルに翻訳。 既存の相手言語ページがあればそれを調べて正確な綴り (大文字化・空白) に合わせる。
- Wikipedia リンクはターゲット読者の言語版 (`en.wikipedia.org` / `ja.wikipedia.org`) に差し替える。
- GitHub README は `README.md` (英語) / `README-ja.md` (日本語) など、 相手言語版のファイル名に差し替える。
- 技術用語は Googology 標準用語に合わせる:
  - 巨大関数 → **fast-growing function**
  - 巨大数 → **large number**
  - 繰り返し迷路 → **repeated maze**
  - ゲーデル符号化 → **Gödel encoding / numbering**

### 9.2 言語ごとの差し替え項目

| 要素 | ja | en |
|---|---|---|
| 名前空間 | `ユーザーブログ:` | `User blog:` |
| ファイル | `[[ファイル:X]]` | `[[File:X]]` |
| カテゴリタグ | `[[カテゴリ:ブログ記事]]` | `[[Category:Blog posts]]` |
| 編集要約 | 日本語 | 英語 |
| ライセンス節 | `== ライセンス ==` | `== Licensing ==` |

### 9.3 mermaid 図

言語ごとに別の PNG を作る (`Kot-foo-pipeline.png` と `Kot-foo-pipeline-en.png`)。 ソース `.mmd` もそれぞれ別ファイルで管理する。 wikitext 側で参照先を変える。

### 9.4 英訳の実行

- 長文は subagent (general-purpose) に投げるとよい。 以下をプロンプトに含める:
  - 固定グロッサリ (日本語 → 英語の対応表)
  - 「wikitext 書式は変更しない」原則
  - 画像参照は `[[ファイル:` → `[[File:` だけ差し替え、ファイル名は保持
  - 内部リンクのタイトル翻訳 (`ユーザーブログ:Koteitan/…` → `User blog:Koteitan/…`、記事タイトル自体も英訳)
  - 作者名はラテン文字のまま
- subagent 完了後、 残作業:
  - 用語ゆれチェック (`huge function` → `fast-growing function` 全置換、など)
  - 既存の相手言語ページがあれば実在する綴りに差し替え
  - Wikipedia / GitHub リンクを英語版に差し替え

### 9.5 英語版 Googology Wiki の権限差 (実測)

ja wiki と en wiki は見かけ上同じ Fandom サイトだが、API 権限の挙動が明確に違う。 2026-10 に実測した結果:

#### (a) ユーザーの所属グループが違う

| wiki | 自分 (Koteitan) のグループ |
|---|---|
| ja | `['rollback', 'sysop', '*', 'user', 'autoconfirmed', 'emailconfirmed']` |
| en | `['*', 'user', 'autoconfirmed', 'emailconfirmed']` |

ja では sysop (管理者) で全権限、en では通常ユーザー扱い。 **同じアカウントでも wiki ごとに権限が全然違う**。 ログイン後の `uiprop=groups|rights` で必ず確認。

#### (b) ボットパスワードは wiki ごと

Fandom のボットパスワードは **各 wiki で独立して管理** される (`Special:BotPasswords`)。 ja で grant 設定しても en には適用されない。 両 wiki でそれぞれ grant を揃える必要がある。 環境変数も分けておく:

```sh
export GWIKIJA_BOT_USER='Koteitan@claude'
export GWIKIJA_BOT_PASSWORD='...'
export GWIKIEN_BOT_USER='Koteitan@claude-en'
export GWIKIEN_BOT_PASSWORD='...'
```

**同じボット名 `claude` でも、ja と en のパスワード文字列は違う**。 片方の wiki で作ったパスワードはもう一方では認証されない。

#### (c) User blog の API 新規作成が en では封じられている

| 操作 | ja wiki | en wiki |
|---|---|---|
| `User blog:X/新タイトル` の `action=edit` 新規作成 | ○ Success | **× permissiondenied** |
| `User blog:X/既存タイトル` の `action=edit` 編集 | ○ Success | ○ Success |
| 既存 User blog の `intestactions=edit` 結果 | `"edit": []` (OK) | `"edit": []` (OK) |
| 未作成 User blog の `intestactions=edit\|create` 結果 | 両方 OK | 両方 `permissiondenied` |

en wiki は User blog 名前空間 (ns 500) の **新規作成を UI 経由に限定** している (推定: 特別ページ `Special:CreateBlogPage` でメタデータや分類処理を行う前提)。 API での `action=edit` 新規作成はブロック。 一方、 UI で空ページを作れば既存ページ扱いになるので、 API `action=edit` で上書き可能。

**対処**: ユーザーに `Special:CreateBlogPage` でタイトルを入れて "Publish" してもらう。 本文は空か "Draft" でよい。 その後、 ボットで本文をまとめて差し替える。 ja wiki でも同じフローを使えば汎用的で安全。

#### (d) 事前判定: intestactions の活用

書き込みを試す前に `intestactions` で判定できる:

```sh
curl -s --max-time 20 -b "$COOKIES" --get "$BASE" \
  --data-urlencode 'action=query' \
  --data-urlencode 'format=json' \
  --data-urlencode "titles=User blog:X/タイトル" \
  --data-urlencode 'prop=info' \
  --data-urlencode 'intestactions=edit|create' \
  --data-urlencode 'intestactionsdetail=full'
# "edit": [] → OK
# "edit": [{"code":"permissiondenied",...}] → NG
```

User blog の新規投稿前に必ず実行。 permissiondenied が返ったら UI 経由作成を依頼する。

#### (e) 既存ブログの大小文字

相手言語版の既存ページ名は、 subagent が自動生成する直訳と微妙に違うことがある:

| subagent の生成 (直訳) | 実在の en ページ名 |
|---|---|
| `History of repeated mazes` | `A history of Repeating Mazes` |
| `Pentation maze` | `Pentation Maze` (大文字 M) |

内部リンクを `[[User blog:Koteitan/X|…]]` で書く前に `allpages apnamespace=500 apprefix=User` で実在するタイトルを確認し、綴り (大小文字・冠詞・ハイフン) を実際のページに合わせる。 間違えると red link のまま投稿してしまう。

## 10. wikitext → Markdown 逆変換 (任意)

GitHub 用に `fandom-en.txt → main-en.md` を作る場合の要点。 §8 の逆:

- `== X ==` → `## X`、以下階層シフト。 **冒頭に H1 (ページタイトル) を追加**。
- `\( x \)` → `$x$`
- `\begin{eqnarray*}` → `\begin{eqnarray}` (GitHub の MathJax は `*` 無しの方が無難)
- `[URL text]` → `[text](URL)`
- `[[Page|label]]` → `[label](https://<wiki>/wiki/<url-encoded Page>)`
- `{|class="wikitable"` → Markdown pipe table
- `'''X'''` → `**X**`、`''X''` → `*X*`
- `<syntaxhighlight lang="L">` → ` ```L ... ``` `
- `<pre>` → ` ``` ... ``` `
- `* X` → `- X`、 `# X` → `1. X` (ネスト対応)
- `<blockquote>...</blockquote>` → `> …`
- `----` → `---`
- 画像ラッパー `<div …>\n[[ファイル:X|…]]\n</div>` → `![X](X)`
- mermaid 用に差し替えた PNG 参照 (`Kot-foo-pipeline-en.png`) → 元の mermaid コードブロックに戻す

**順序の注意**: wiki→md では **list を先に** 変換する (見出し `== X ==` → `## X` と wiki の `##` が衝突するため)。

## 11. 失敗時の対処

| 症状 | 原因 | 対処 |
|---|---|---|
| `"login":{"result":"Failed"}` | ユーザー名の `@ボット名` が抜けている | `*_BOT_USER` に `@` を含めて再設定 |
| `"login":{"result":"WrongPass"}` | パスワード違い / grant 不足 | `Special:BotPasswords` で grant を確認 |
| `"upload":{"error":{"code":"cantcreate"}}` | `createpage` 権限なし (ファイル説明ページ作成不可) | ボットパスワードの "Create, edit, and move pages" grant を追加 |
| `"upload":{"error":{"code":"fileexists-forbidden"}}` | 既存ファイル差し替え権限なし | "Upload, replace, and move files" grant を追加 |
| `"edit":{"error":{"code":"permissiondenied"}}` | 名前空間制限、または wiki 側で API 新規作成不可 | `intestactions` で `edit`/`create` を事前判定。 User blog は UI 作成必須の wiki あり |
| `"error":{"code":"abusefilter-..."}` | 編集フィルター | 本文を見直す |
| `"error":{"code":"readonly"}` | wiki 保守中 | 時間を置く |
| `"error":{"code":"assertuserfailed"}` | セッション切れ | 再ログイン |
| 投稿後に `UNIQ--postMath-...-QINU` が TOC に残る | 見出しに `<math>` or `\( \)` が含まれる | 見出しの数式を Unicode に書き換え |
| 投稿後にモバイルで画像がはみ出す | 固定幅画像でレスポンシブ CSS 未適用 | `<div style="overflow-x:auto">` で囲む |
| 数式が汚い SVG | `<math>` が texvc で処理されている | `\( ... \)` に変更して client-side MathJax に任せる |

## 12. 編集の原則

- **投稿前にユーザー承認**。公開ブログ記事は検索エンジンにも拾われる。
- **プレビュー必須**。 `action=parse` で事前確認、投稿後に `page=…` で再確認。
- **要約を書く**: `summary=` には変更内容を書く (「初版」「数式修正」など)。履歴に残る。
- **衝突時の対処**: 既存ページを更新する場合、`basetimestamp` + `starttimestamp` で衝突検出。
- **ボットパスワードはログインごとに新規コッキーを取る必要はない**。 1 セッション内では使い回す。
