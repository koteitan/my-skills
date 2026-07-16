[← Back](../../README.md) | [English](README.md) | [Japanese](README-ja.md)

# check-usage

A Claude Code skill that lets the agent find out the state of the **5-hour** and
**weekly** rate limits (the Max plan's usage ceilings): how much is used, when the
window resets, and when you would hit the limit at the current pace.

Ask "how much of this week is left?", "when do I get it back?", or "will I run out
at this rate?" and the agent runs this skill's script to answer.

## Example output

```console
$ python3 ~/.claude/skills/check-usage/scripts/check-usage.py
5 hours limit:  90% used, will reset at 07/17 09:40, limited at 07/17 08:54 in the current pace
weekly limit :  51% used, will reset at 07/17 20:00, not projected to hit the limit before the reset
```

Read as: the 5-hour window is 90% spent and, at this pace, runs out at 08:54 —
46 minutes before it resets at 09:40. The weekly window is 51% spent and is not
on track to run out before its reset at 20:00.

## How it works

Claude Code pipes a JSON blob into the statusLine command, and that blob carries
**server-side** rate-limit state:

- `.rate_limits.five_hour.{used_percentage, resets_at}`
- `.rate_limits.seven_day.{used_percentage, resets_at}`

`~/.claude/statusline-command.sh` appends each reading as a sample to
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

## Do not reconstruct the windows from local JSONL

Tools like `ccusage blocks` **infer** window boundaries by flooring the first
activity in the local JSONL to the hour, so they drift from the real reset
(measured 2026-07-17: ccusage reported a 09:00 reset while the true `resets_at`
was 09:40). The `rate_limits` values this skill reads come from the server and
are authoritative.

## Requirements

- `~/.claude/statusline-command.sh` configured as the statusLine command, so that
  it appends samples to `~/.claude/statusline-usage.log`.
- The log location can be overridden with the `STATUSLINE_USAGE_LOG` environment
  variable.

## Installation

```bash
ln -s "$PWD/skills/check-usage" ~/.claude/skills/check-usage
```
