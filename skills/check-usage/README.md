[← Back](../../README.md) | [English](README.md) | [Japanese](README-ja.md)

# check-usage

A Claude Code skill that lets **the agent itself** find out the state of the
**5-hour** and **weekly** rate limits (the Max plan's usage ceilings): how much is
used, when the window resets, and when it would hit the limit at the current pace.

You can see what is left by glancing at the status line; the agent cannot. Starting
a long job blind, it simply dies mid-task the moment the limit is reached. With this
skill the agent can check the remaining budget and the exhaustion forecast before it
commits to work, so it can:

- wrap up at a checkpoint instead of starting a large workflow on a thin budget;
- decide whether to fan out dozens of subagents or run a small pool;
- split the work around the reset time.

That pacing is what keeps a long job from being cut in half.

## Why it is worth checking before a fanout

The docs themselves warn that
[a single burst of heavy activity, such as a large workflow fanout, can exhaust the
weekly allowance before the session window resets](https://code.claude.com/docs/en/errors.md).
What they don't say is how much you lose when it happens.

**A rate-limit death destroys an in-flight subagent's context entirely.** The dead
`agent()` call is journaled as nothing but `{"type":"result","value":null}`, and a
`resumeFromRunId` restarts it from the bare prompt with a fresh context (completed
agents do replay from cache). Only files written to disk survive; the sole recovery
routes are those artifacts and digging through the session jsonl. An agent holding
ten minutes of work in memory loses all of it.

So a manager agent can run this skill before committing to a fanout and again
between phases — to size the pool, or to re-cut the work around the reset.

### Read the forecast asymmetrically

This is the crux. **The forecast extrapolates from past pace, which makes it least
trustworthy exactly when you are about to change that pace.** The forecast you read
one second before launching sixteen parallel agents is guaranteed to be optimistic.
So:

- **A forecast that names a time** is a strong signal: believe it, don't start.
- **No forecast is not proof of headroom.** It only means "at the current pace" —
  and a fanout is precisely what breaks the current pace.

To size a fanout, read `~/.claude/statusline-usage.log` directly and see how many
points the last comparable wave actually moved. That measurement beats the forecast.

### Keep disk discipline unconditional

Do not make "save your work" conditional on this reading. Context is lost to API
errors, compaction and interrupts too, and the forecast fails you precisely when it
says you are fine. Make 1 agent = 1 file, draft early, and no in-memory accumulation
standing rules; use this skill for the *decision to start*, which is the one thing
disk discipline cannot cover.

## Example output

```console
$ python3 ~/.claude/skills/check-usage/scripts/check-usage.py
5 hours limit:  90% used, will reset at 07/17 09:40, limited at 07/17 08:54 in the current pace
weekly limit :  51% used, will reset at 07/17 20:00, not projected to hit the limit before the reset
```

Read as: the 5-hour window is 90% spent and, at this pace, runs out at 08:54 —
46 minutes before it resets at 09:40. The weekly window is 51% spent and is not
on track to run out before its reset at 20:00.

## Installation

This skill reads a log written by [statusline-command.sh](../../statusline-command.sh)
at the root of this repository. **A stock Claude Code has no such log**: it hands the
rate-limit values to the statusLine and records them nowhere. So you need to install
**both** the skill and that statusLine script.

```bash
# 1. the skill itself
ln -s "$PWD/skills/check-usage" ~/.claude/skills/check-usage

# 2. the statusLine script that writes the log
ln -s "$PWD/statusline-command.sh" ~/.claude/statusline-command.sh
```

Then wire it up as the statusLine in `~/.claude/settings.json`:

```json
"statusLine": { "type": "command", "command": "bash /home/<user>/.claude/statusline-command.sh" }
```

From then on, every statusLine render appends a sample to
`~/.claude/statusline-usage.log`. **The forecast needs at least two samples**, so right
after installing you get the percentage and reset time only; the forecast appears once
you have been using Claude Code for a while. Override the log location with the
`STATUSLINE_USAGE_LOG` environment variable.

## How it works

Claude Code pipes a JSON blob into the statusLine command, and that blob carries
**server-side** rate-limit state:

- `.rate_limits.five_hour.{used_percentage, resets_at}`
- `.rate_limits.seven_day.{used_percentage, resets_at}`

statusline-command.sh appends each reading as a sample to
`~/.claude/statusline-usage.log` — one sample per line, `-` where a value is absent:

```
<epoch> <five%> <week%> <five_resets_at> <week_resets_at>
```

This script reads that log and:

1. takes the current percentage and reset time from the last row;
2. selects the rows sharing the same `resets_at` — i.e. the samples of the
   current window — and measures the slope (%/sec, wall-clock) from the first to
   the latest of them;
3. extrapolates that slope to 100% to get the exhaustion time.

## Caveats on the forecast

- The forecast is only shown when 100% would be reached **before** the reset.
  Otherwise the reset wins and there is nothing to warn about.
- The slope is wall-clock based, so idle time is averaged in. Time spent away
  from the keyboard counts toward the denominator — this is deliberate.
- Early in a window the percentage may not have moved yet (the source resolution
  is 1%), so no forecast appears. That is also when plenty remains.
- Samples only accumulate when the statusLine renders, so gaps appear across
  stretches where Claude Code was not in use.
