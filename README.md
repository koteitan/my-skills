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
| [heart-beat](skills/heart-beat/) | Say `heart-beat X分`: work autonomously until the proof is complete, with a CronCreate heartbeat so the session never stays idle longer than X minutes |
| [autonomy-stat](skills/autonomy-stat/) | Measure an agent's per-turn self-running time from a session JSONL and render it as an interactive HTML chart (model-work vs tool-wait) |
| [check-usage](skills/check-usage/) | Report the 5-hour and weekly rate-limit state: percent used, reset time, and the exhaustion forecast at the current pace |
| [mermaid](skills/mermaid/) | Rules for drawing Mermaid diagrams: no node fills, no diamonds, short captions |
| [manim-tts](skills/manim-tts/) | Pitfalls of building narrated explainer videos with manim + VOICEVOX TTS: cache-dropped audio, mobjects that reappear, LaTeX failures on Japanese |
| [my-github-md-rule](skills/my-github-md-rule/) | Rules for generating bilingual (EN/JA) markdown documents on GitHub |
| [github-math-check](skills/github-math-check/) | Verify that Markdown math survives GitHub's own transformations, by rendering the exact string GitHub hands to the browser; also finds plain-text formulas whose `*` and `_` turn into italics |
| [nostr](skills/nostr/) | Nostr hub: relay discovery, DIY NIP-19 bech32 entities, CLI relay debugging, and the standard web-app stack |
| [webapp-defaults](skills/webapp-defaults/) | Defaults for a scratch-built vanilla page: dark mode on, top-right hamburger menu, UI state kept in localStorage |
| [sessiondb](skills/sessiondb/) | SQLite + FTS5 full-text search over Claude Code session JSONL logs |
| [use-bms](skills/use-bms/) | Build and drive the [yaBMS](https://github.com/koteitan/yaBMS) `c/bms` CLI: expand, compare, standard-check and loop-hunt Bashicu Matrices |
| [formalization-statement-fidelity-audit](skills/formalization-statement-fidelity-audit/) | Audit a formalization against the article it formalizes, one page per proposition, every difference classified X/Y/Z/W/S/R/U |

## Slash commands

| Command | Description |
|---------|-------------|
| [check-win-update](commands/check-win-update.md) | Check pending Windows Updates and report known issues from X |

## bin/ scripts

| Script | Description |
|--------|-------------|
| [claude-pushover](bin/claude-pushover) | Send Claude Code conversation summary via Pushover (intended as a Stop hook) |
| [pushover](bin/pushover) | Thin `curl` wrapper around the Pushover API |
| [live-server-sil](bin/live-server-sil) | Start `live-server` silently in the background and print a clickable URL that also works from other devices on the LAN |
| [live-server-list](bin/live-server-list) | List running `live-server` instances: PID, URL, serving directory |
| [live-server-kill](bin/live-server-kill) | Kill a running `live-server` (sole instance, or by port) |
| [wsl-port-open](bin/wsl-port-open) | Make a WSL port reachable from the LAN: add the Windows portproxy and firewall rule, one UAC prompt per port |
| [wsl-win-ip](bin/wsl-win-ip) | Print the Windows host's LAN IPv4 address, cached |
| [sessiondb](bin/sessiondb) | Build and query a SQLite + FTS5 index over Claude Code session JSONL logs |
| [sessionmv](bin/sessionmv) | Move a directory with its Claude Code sessions, or use `--codex` to rewrite Codex JSONL/state metadata |
| [newline](bin/newline) | Detect CR / LF / CRLF line endings in files |
| [nostrsocat](bin/nostrsocat) | `websocat` wrapper for querying Nostr relays |
| [codexps](bin/codexps) | List `codex:rescue` jobs and separate live ones from records whose process is gone |

## statusLine

[statusline-command.sh](statusline-command.sh) draws the two-line status line:
`host:dir` on top, then gauges for the context window and the 5-hour / weekly rate
limits, each with an exhaustion forecast, plus the model and effort level. It also
appends every rate-limit reading to `~/.claude/statusline-usage.log`, which is what
the [check-usage](skills/check-usage/) skill reads.

Register it in `~/.claude/settings.json`:

```json
"statusLine": {
  "type": "command",
  "command": "bash /home/<user>/.claude/statusline-command.sh"
}
```

## License

[MIT](LICENSE)
