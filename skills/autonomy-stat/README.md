[← Back](../../README.md) | [English](README.md) | [Japanese](README-ja.md)

# autonomy-stat

A Claude Code skill that measures an agent's autonomy — its *self-running time*
per turn — from a session JSONL log, and renders it as a self-contained,
interactive HTML report.

## Usage

```bash
skills/autonomy-stat/scripts/autonomy-stat.py stat <session-id|project-dir> <outfile.html> [--lang en|ja]
```

The first argument accepts any of:

- a session UUID (searched across all `~/.claude/projects/*/`)
- a full path to a `*.jsonl`
- a project-directory name in the `-home-user-dir` form (the latest session in
  that project is used)

`--lang` sets the report's UI language: `en` (default) or `ja`. Only the UI
labels are translated; the analyzed data (input prompts etc.) is never
translated.

Example:

```bash
skills/autonomy-stat/scripts/autonomy-stat.py stat -home-user-myproject /tmp/myproject.html
skills/autonomy-stat/scripts/autonomy-stat.py stat -home-user-myproject /tmp/myproject.html --lang ja
```

Then open the HTML in a browser.

## What the report shows

Two stacked time-series charts (dark mode, no external dependencies), plus a
per-turn table:

- **Top chart (blue)** — self-running time **excluding** tool-wait: the time
  the agent actually spent thinking/generating.
- **Bottom chart (orange)** — self-running time **including** tool-wait
  (model work + tool execution + approval waits).

Each chart auto-scales its own y-axis; the x-axis is per-day in local time.
Hover a point for a full per-turn breakdown. The gap between the two charts is
the tool-wait time — useful for spotting long tool runs or unattended approval
waits.

## How it works

1. **Drop replayed history.** `/compact` and resume re-inject old log lines
   with stale timestamps. Entries whose timestamp jumps far backward of a
   running monotonic clock are discarded as replays.
2. **Detect genuine human input** to mark turn boundaries — excluding tool
   results, meta lines, sidechains, and harness injections (task
   notifications, slash-command output, system reminders, compaction
   summaries).
3. **Split into turns** (queued inputs collapse into one boundary); a turn's
   activity is the assistant messages and tool results until the next human
   input.
4. **Classify each inter-event gap**:
   - before a **tool result** → tool-wait (counted in full),
   - before an **assistant** message within 5 min → work,
   - before an **assistant** message beyond 5 min → 5 min of work, the rest is
     sleep/idle and **excluded**.
5. Report two series per turn: `work` (blue) and `work + tool-wait` (orange).
6. Between-turn idle (agent stopped, human away) is never counted as
   self-running.

## Tunable constants

| Constant | Default | Meaning |
|----------|---------|---------|
| `IDLE_THRESHOLD_MS` | 5 min | Max assistant-gap counted as work; the excess is treated as sleep/idle. Most impactful knob. |
| `REPLAY_TOLERANCE_MS` | 60 s | Backward-timestamp tolerance before an entry is treated as a `/compact` replay. |

Tool-wait gaps are intentionally not capped; both series are shown instead so
you can judge.

## Installation

```bash
ln -s "$PWD/skills/autonomy-stat" ~/.claude/skills/autonomy-stat
```
