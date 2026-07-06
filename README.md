[English](README.md) | [Japanese](README-ja.md)

# my-skills

A collection of Claude Code skills, slash commands, and helper scripts, managed with version control.

## Structure

```
skills/<skill-name>/SKILL.md
commands/<command-name>.md
bin/<script-name>
```

## Installation

Create symbolic links to the appropriate locations:

```bash
# Skills
ln -s "$PWD/skills/<skill-name>" ~/.claude/skills/<skill-name>

# Slash commands
ln -s "$PWD/commands/<command-name>.md" ~/.claude/commands/<command-name>.md

# Helper scripts (any directory on $PATH)
ln -s "$PWD/bin/<script-name>" ~/bin/<script-name>
```

## Skills

| Skill | Description |
|-------|-------------|
| [compact-unfreeze](skills/compact-unfreeze/) | Work around the Remote Control + `/compact` frozen-input bug by arming a background Monitor to flush the stuck queue |
| [autonomy-stat](skills/autonomy-stat/) | Measure an agent's per-turn self-running time from a session JSONL and render it as an interactive HTML chart (model-work vs tool-wait) |
| [my-github-md-rule](skills/my-github-md-rule/) | Rules for generating bilingual (EN/JA) markdown documents on GitHub |
| [sessiondb](skills/sessiondb/) | SQLite + FTS5 full-text search over Claude Code session JSONL logs |

## Slash commands

| Command | Description |
|---------|-------------|
| [check-win-update](commands/check-win-update.md) | Check pending Windows Updates and report known issues from X |

## bin/ scripts

See [`bin/README.md`](bin/README.md) for the list of helper scripts and their descriptions.

## License

[MIT](LICENSE)
