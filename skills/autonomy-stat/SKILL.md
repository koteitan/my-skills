---
name: autonomy-stat
description: Measure a Claude Code agent's autonomy (self-running time) from a session JSONL and render it as an interactive HTML chart. Splits each turn into model-work time vs tool-wait time, and excludes idle/sleep/replay so the numbers reflect time the agent was actually working on its own.
---

# autonomy-stat

Analyze how long a Claude Code agent ran on its own per turn, from a session
JSONL log, and write an interactive HTML report (two time-series charts +
a per-turn table).

## When to invoke

- User wants to evaluate agent autonomy / self-running time.
- User asks how long the agent worked per turn, or to chart a session over time.
- User points at a project (`~/foo`) or a session id and asks to "analyze" it
  in this autonomy sense.

## Usage

```bash
skills/autonomy-stat/scripts/autonomy-stat.py stat <session-id|project-dir> <outfile.html> [--lang en|ja]
```

The first argument accepts any of:

- a session UUID — e.g. `66af0915-9b59-4b1e-88a3-ff312e0c2ed3`
  (searched across all `~/.claude/projects/*/`)
- a full path to a `*.jsonl`
- a project-directory name in the `-home-user-dir` form — e.g.
  `-home-user-myproject`. The **latest** session in that project is used.

`--lang` sets the report's UI language: `en` (default) or `ja`. Only the UI
labels are translated; the analyzed data (input prompts etc.) is never
translated.

Example:

```bash
skills/autonomy-stat/scripts/autonomy-stat.py stat -home-user-myproject /tmp/myproject.html
skills/autonomy-stat/scripts/autonomy-stat.py stat -home-user-myproject /tmp/myproject.html --lang ja
```

Open the resulting HTML in a browser. The user runs their own HTTP server — do
not launch one.

## Output

A self-contained dark-mode HTML (no external dependencies) with:

- **Top chart (blue)** — self-running time *excluding* tool-wait: pure model
  thinking/generation time per turn.
- **Bottom chart (orange)** — self-running time *including* tool-wait
  (model work + tool execution + approval waits).
- Each chart auto-scales its own y-axis (nice steps: `1m/2m/5m/.../1h/2h/...`);
  x-axis is per-day, local time.
- Hover any point for a per-turn breakdown; a full table follows below.

The gap between the two charts is the tool-wait time. Read the **blue** chart
for "time the agent actually spent reasoning"; the orange/blue gap reveals long
tool executions or unattended approval waits.

## How it works (algorithm)

1. **Drop replayed history** (`drop_replayed`): `/compact` and resume
   re-inject old log lines with their original (stale) timestamps. Any entry
   whose timestamp jumps backward more than `REPLAY_TOLERANCE_MS` below a
   running monotonic clock is discarded as a replay.
2. **Detect genuine human input** (`is_genuine_user`): a `user` entry that is
   not a tool result (`toolUseResult`), not meta, not a sidechain, not a
   harness injection (`origin.kind`, `<task-notification>`, `<command-*>`,
   `<system-reminder>`, the compaction continuation summary). These mark turn
   boundaries.
3. **Split into turns**: consecutive human inputs (queued) collapse into one
   boundary (start = last of them). A turn's activity = `assistant` messages
   and tool results until the next genuine input. system/queue/command events
   never extend a turn's end.
4. **Classify the gap before each activity event** into three buckets:
   - next event is a **tool result** → `toolwait` (a tool was running / awaiting
     approval); counted in full.
   - next event is an **assistant** message and gap ≤ `IDLE_THRESHOLD_MS` →
     `work` (normal generation/thinking).
   - next event is an **assistant** message and gap > `IDLE_THRESHOLD_MS` →
     `work` capped at the threshold, the excess is `sleep` (e.g. `/loop`
     sleeps, unattended idle) and is **excluded**.
   Rationale: a long gap *before an assistant message* has no running tool to
   justify it, so it is idle, not work. A long gap before a *tool result* is a
   real (possibly slow) tool, so it counts.
5. **Two series per turn**:
   - `active_excl = work` (tool-wait excluded) → blue
   - `active_incl = work + toolwait` (tool-wait included) → orange
6. **Between-turn idle** (`idle_before_sec`) = next turn's start − this turn's
   end. This is the agent sitting stopped while the human is away; never
   counted as self-running (shown for reference only).

## Tunable constants (top of the script)

| Constant | Default | Meaning |
|----------|---------|---------|
| `IDLE_THRESHOLD_MS` | 5 min | Max assistant-gap counted as work; excess is sleep/idle. The single most impactful knob. |
| `REPLAY_TOLERANCE_MS` | 60 s | Backward-timestamp tolerance before an entry is treated as `/compact` replay. |

Tool-wait gaps are intentionally **not** capped — instead both the
with-tool-wait and without-tool-wait series are shown so the user can judge.

## Notes / caveats

- Timestamps are UTC in the log; the HTML renders them in the browser's local
  time zone.
- Sessions heavily compacted/resumed can be majority replay; step 1 is what
  makes the per-turn durations trustworthy.
