---
name: check-usage
description: Report the Claude Code 5-hour and weekly (Max plan) rate-limit state — percent used, reset time, and the exhaustion forecast at the current pace. Use when the user asks how much of the limit is left, when it resets, or whether they will run out.
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
