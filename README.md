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
| [my-github-md-rule](skills/my-github-md-rule/) | Rules for generating bilingual (EN/JA) markdown documents on GitHub |

## Slash commands

| Command | Description |
|---------|-------------|
| [check-win-update](commands/check-win-update.md) | Check pending Windows Updates and report known issues from X |

## bin/ scripts

| Script | Description |
|--------|-------------|
| [claude-pushover](bin/claude-pushover) | Send Claude Code conversation summary via Pushover (intended as a Stop hook) |
| [pushover](bin/pushover) | Thin `curl` wrapper around the Pushover API |
| [live-server-list](bin/live-server-list) | List ports of running `live-server` instances |
| [mv-session](bin/mv-session) | Move a directory together with its `~/.claude/projects/` session dir |
| [newline](bin/newline) | Detect CR / LF / CRLF line endings in files |

## License

[MIT](LICENSE)
