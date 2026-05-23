---
name: my-github-md-rule
description: When the user requests to generate markdown document on github
---

# Rules for GitHub Markdown Documents

- Each markdown consists of a pair of `*.md` in English and `*-ja.md` in Japanese.
  - Exception: `SKILL.md` does not need an EN/JA pair. It is read by the agent (English only) and is not user-facing documentation.
- Each markdown file must have the following link at the top of the file:

```
[← Back](../README-ja.md) | [English](*.md) | [Japanese](*-ja.md)
```

- "Back" link should point to the README.md in the parent directory.
- "English" and "Japanese" links should point each other.
- Use the following if the markdown file is README in the root directory:

```
[English](README.md) | [Japanese](README-ja.md)
```
