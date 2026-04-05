# purpose
- versioning of the agent skills

# structure
<skill A>/SKILL.md
<skill B>/SKILL.md
...

# usage
ln -s <skill A> ~/.claude/skills/<skill A>
ln -s <skill B> ~/.claude/skills/<skill B>

# skills
## my github md rule
### directory
my-github-md-rule/

### trigger
- When the user requests to generate markdown document on github

### rule
- Each markdown consists of a pair of *.md in English and *-ja.md in Japanese.
- Each markdown files must have a following link at the top of the file:
```
[← Back](../README-ja.md) | [English](*.md) | [Japanese](*-ja.md)
```
- "Back" link should point to the README.md in the parent directory.
- "English" and "Japanese" links should point each other.
- Use following if the markdown file is README in the root directory:
```
[English](README.md) | [Japanese](README-ja.md)
```

