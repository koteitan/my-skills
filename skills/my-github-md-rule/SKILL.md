---
name: my-github-md-rule
description: Apply the user's selected README language and navigation-link convention. Use only when the user explicitly asks to use `my-github-md-rule` (including `$my-github-md-rule`) in the current request; do not trigger merely because the request concerns GitHub or Markdown documentation.
---

# GitHub Markdown Rules

Apply this skill only after the user explicitly invokes `my-github-md-rule`.

## Select a mode

Accept a mode by number or name. If the user explicitly invokes the skill without selecting a
mode, ask them to choose mode 1, 2, 3, or 4 before generating files.

| No. | Mode | `README.md` | `README-ja.md` | `README-en.md` | Back link |
| ---: | --- | --- | --- | --- | --- |
| 0 | default | Japanese | no | no | no |
| 1 | Japanese only | Japanese | no | no | yes |
| 2 | English only | English | no | no | yes |
| 3 | Japanese main | Japanese | no | English | yes |
| 4 | English main | English | Japanese | no | yes |

Mode 0 describes normal behavior when the user does not invoke this skill. Do not apply any
skill-specific file pairing, naming, or navigation-link rule in mode 0.

Only modes 1--4 are active invocations of this skill.

## Generate files

- In mode 1, generate only `README.md` in Japanese.
- In mode 2, generate only `README.md` in English.
- In mode 3, generate `README.md` in Japanese and `README-en.md` in English.
- In mode 4, generate `README.md` in English and `README-ja.md` in Japanese.
- Keep the contents of both files equivalent in modes 3 and 4.
- Treat `README.md` as the main file GitHub renders by default.
- For non-README documents, apply the same naming pattern: the main file is `<name>.md`, and
  the translation is `<name>-en.md` in mode 3 or `<name>-ja.md` in mode 4.

## Add navigation links

In modes 1--4, put a Back link at the top of every generated Markdown file. Point it to the
main README in the parent directory:

```markdown
[← Back](../README.md)
```

In bilingual modes, add the language links on the same line:

- Mode 3: `[← Back](../README.md) | [English](README-en.md) | [Japanese](README.md)`
- Mode 4: `[← Back](../README.md) | [English](README.md) | [Japanese](README-ja.md)`

For non-README documents, replace the language-link filenames with the corresponding
`<name>.md`, `<name>-en.md`, or `<name>-ja.md` filenames.

## Check for cross-language link mistakes

`scripts/check-link-lang.py` flags links where a file's language does not match the
language variant it points to -- for example a Japanese `README-ja.md` linking to a
subdirectory's English `README.md` when a `README-ja.md` sibling exists. Navigation and
language-switcher links are recognized by their text and skipped, and single-language
documents (no same-language sibling on disk) are never flagged.

Pass the mode so the checker knows which suffix maps to which language:

```sh
python3 scripts/check-link-lang.py --mode 4 <path...>   # mode 4: README.md = English
python3 scripts/check-link-lang.py --mode 3 <path...>   # mode 3: README.md = Japanese
```

Paths may be files or directories (recursed); the default is the current directory. The
checker exits 1 when it finds a mismatch and 0 otherwise. Modes 1 and 2 are single-language,
so there is nothing to cross-check.
