---
name: check-usage
description: Report the Claude Code 5-hour and weekly (Max plan) rate-limit state — percent used, reset time, and the exhaustion forecast at the current pace. Use when the user asks how much of the limit is left or when it resets, and before committing to a large workflow fanout that could die mid-run.
---

# check-usage

Run the script and report its output:

```bash
python3 ~/.claude/skills/check-usage/scripts/check-usage.py
```

It prints, for both windows:

```
5 hours limit:  90% used, will reset at 07/17 08:00, limited at 07/17 07:12 in the current pace
weekly limit :  51% used, will reset at 07/18 05:00, not projected to hit the limit before the reset
```

## Pacing a workflow

A rate-limit death mid-fanout destroys every in-flight subagent's context: the
`agent()` call is journaled as `{"type":"result","value":null}`, and a
`resumeFromRunId` restarts it from the bare prompt. Only files on disk survive.
So:

- Run this before committing to a large fanout, and again between phases. Prefer
  several smaller workflows in sequence, checking here in the main loop between
  them — a workflow script cannot read the log itself (no filesystem access), so
  self-pacing inside a script costs a sentinel agent per round.
- **Read the forecast asymmetrically.** If it names a time, believe it and don't
  start the fanout. If it doesn't, that is not proof of headroom: the slope is
  extrapolated from past pace, and a fanout is precisely what breaks that pace.
- To size a fanout, read `~/.claude/statusline-usage.log` directly: how much the
  percentage moved during the last comparable wave is a better cost estimate than
  the forecast.
- Weekly and 5-hour are asymmetric — burning the weekly costs days, the 5-hour at
  most five hours. Degrade harder when the weekly is thin.
- Never make disk discipline conditional on this reading (1 agent = 1 file, draft
  early, no in-memory accumulation). Context is also lost to API errors, compaction
  and interrupts, and the forecast is least reliable exactly when it says you are
  fine.

## Notes

- Data comes from `~/.claude/statusline-usage.log`, which `statusline-command.sh`
  appends from the **server-side** `rate_limits` fields Claude Code feeds the
  statusline. This is authoritative — do not reconstruct windows from local JSONL
  (e.g. `ccusage blocks` infers boundaries and drifts from the real reset).
- The forecast is a wall-clock slope extrapolation over the current window's
  samples, so idle time counts. It is only shown when 100% would be reached
  before the reset; otherwise the reset wins and there is nothing to warn about.
- Early in a window the percentage may not have moved yet (1% resolution), so no
  forecast appears — which is also when plenty remains.
