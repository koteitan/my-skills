---
name: my-github-md-rule
description: When the user requests to generate markdown document on github
---

# Rules for GitHub Markdown Documents

- Each markdown consists of a pair of `*.md` in English and `*-ja.md` in Japanese.
  - Exception: `SKILL.md` does not need an EN/JA pair. It is read by the agent (English only) and is not user-facing documentation.
- Each markdown file must have the following link at the top of the file:

```
[← Back](../README.md) | [English](*.md) | [Japanese](*-ja.md)
```

- "Back" link should point to the README.md in the parent directory.
- "English" and "Japanese" links should point each other.
- Use the following if the markdown file is README in the root directory:

```
[English](README.md) | [Japanese](README-ja.md)
```

## Language modes

The pair always has a **main** file — the one GitHub renders by default (`README.md` or
`<name>.md`) — plus a **secondary** translation. The invocation mode sets which language
is the main:

- **English main** (default): main = English `*.md`; secondary = Japanese `*-ja.md`.
  - header: `[← Back](../README.md) | [English](*.md) | [Japanese](*-ja.md)`
  - root README: `[English](README.md) | [Japanese](README-ja.md)`
- **Japanese main**: main = Japanese `*.md`; secondary = English `*-en.md`.
  - header: `[← Back](../README.md) | [English](*-en.md) | [Japanese](*.md)`
  - root README: `[English](README-en.md) | [Japanese](README.md)`

"**both**" (as in "Japanese main both") just means: emit both language files of the pair
(the usual case).

The **Back** link always points to the parent directory's main README (`../README.md`) in
either mode.
