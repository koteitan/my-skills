[English](README.md) | [Japanese](README-ja.md)

# my-skills

A collection of Claude Code skills, managed with version control.

## Structure

```
<skill-name>/SKILL.md
```

Each skill is a directory containing a `SKILL.md` file.

## Installation

Create a symbolic link from the skill directory to `~/.claude/skills/`:

```bash
ln -s /path/to/my-skills/<skill-name> ~/.claude/skills/<skill-name>
```

## Skills

| Skill | Description |
|-------|-------------|
| [my-github-md-rule](my-github-md-rule/) | Rules for generating bilingual (EN/JA) markdown documents on GitHub |

## License

[MIT](LICENSE)
