[English](README.md) | [Japanese](README-ja.md)

# my-skills

Claude Code スキルのコレクションです。バージョン管理で管理しています。

## 構造

```
<skill-name>/SKILL.md
```

各スキルは `SKILL.md` ファイルを含むディレクトリです。

## インストール

スキルディレクトリから `~/.claude/skills/` へシンボリックリンクを作成します：

```bash
ln -s /path/to/my-skills/<skill-name> ~/.claude/skills/<skill-name>
```

## スキル一覧

| スキル | 説明 |
|--------|------|
| [my-github-md-rule](my-github-md-rule/) | GitHub 上で日英バイリンガルの markdown ドキュメントを生成するルール |

## ライセンス

[MIT](LICENSE)
