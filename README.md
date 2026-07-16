[English](README.md) | [Japanese](README-ja.md)

# my-skills

A collection of Claude Code skills, slash commands, and helper scripts, managed with version control.

## Structure

```
skills/<skill-name>/SKILL.md
commands/<command-name>.md
bin/<script-name>
statusline-command.sh
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

# statusLine command
ln -s "$PWD/statusline-command.sh" ~/.claude/statusline-command.sh
```

## Skills

| Skill | Description |
|-------|-------------|
| [compact-unfreeze](skills/compact-unfreeze/) | Work around the Remote Control + `/compact` frozen-input bug by arming a background Monitor to flush the stuck queue |
| [autonomy-stat](skills/autonomy-stat/) | Measure an agent's per-turn self-running time from a session JSONL and render it as an interactive HTML chart (model-work vs tool-wait) |
| [check-usage](skills/check-usage/) | Report the 5-hour and weekly rate-limit state: percent used, reset time, and the exhaustion forecast at the current pace |
| [mermaid](skills/mermaid/) | Rules for drawing Mermaid diagrams: no node fills, no diamonds, short captions |
| [my-github-md-rule](skills/my-github-md-rule/) | Rules for generating bilingual (EN/JA) markdown documents on GitHub |
| [sessiondb](skills/sessiondb/) | SQLite + FTS5 full-text search over Claude Code session JSONL logs |

## Slash commands

| Command | Description |
|---------|-------------|
| [check-win-update](commands/check-win-update.md) | Check pending Windows Updates and report known issues from X |

## bin/ scripts

| Script | Description |
|--------|-------------|
| [claude-pushover](bin/claude-pushover) | Send Claude Code conversation summary via Pushover (intended as a Stop hook) |
| [pushover](bin/pushover) | Thin `curl` wrapper around the Pushover API |
| [live-server-sil](bin/live-server-sil) | Start `live-server` silently in the background and print a clickable URL |
| [live-server-list](bin/live-server-list) | List running `live-server` instances: PID, URL, serving directory |
| [live-server-kill](bin/live-server-kill) | Kill a running `live-server` (sole instance, or by port) |
| [sessiondb](bin/sessiondb) | Build and query a SQLite + FTS5 index over Claude Code session JSONL logs |
| [sessionmv](bin/sessionmv) | Move a directory with all its `~/.claude/projects/` session dirs, rewriting `cwd` in JSONL |
| [newline](bin/newline) | Detect CR / LF / CRLF line endings in files |
| [nostrsocat](bin/nostrsocat) | `websocat` wrapper for querying Nostr relays |

## statusLine

[statusline-command.sh](statusline-command.sh) draws the two-line status line:
`host:dir` on top, then gauges for the context window and the 5-hour / weekly rate
limits, each with an exhaustion forecast, plus the model and effort level. It also
appends every rate-limit reading to `~/.claude/statusline-usage.log`, which is what
the [check-usage](skills/check-usage/) skill reads.

Point `statusLine.command` in `~/.claude/settings.json` at it:

```json
"statusLine": { "type": "command", "command": "bash /home/<user>/.claude/statusline-command.sh" }
```

## License

[MIT](LICENSE)
