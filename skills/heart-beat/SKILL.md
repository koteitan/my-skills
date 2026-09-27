---
name: heart-beat
description: Keep working autonomously until the proof is complete, with a CronCreate heartbeat that wakes the session whenever it has been idle for X minutes. Use when the user says "heart-beat X分" / "heart-beat Xm" (X is a number of minutes).
---

# heart-beat

The user says `heart-beat X分` (or `heart-beat Xm`). Treat it as this instruction:

> Set a heartbeat with CronCreate every X minutes and work autonomously until the
> proof is complete. X is not a work slice. X is the longest time the session may
> stay idle. Keep working continuously for as long as the work takes.

## Meaning of X

- X = the maximum idle time. It is **not** "work X minutes, then stop".
- Cron jobs fire only while the REPL is idle. So the heartbeat never interrupts
  work. It only wakes the session after a turn has ended.
- Do not end a turn at an X-minute boundary. Do not split the work into
  X-minute pieces. Keep working until the proof is complete.

## Steps

1. `ToolSearch("select:CronCreate,CronList,CronDelete")` to load the cron tools.
2. `CronList`. Delete any earlier job whose prompt starts with `[heart-beat]`, so
   only one heartbeat exists.
3. `CronCreate` with `recurring: true`, the cron below, and the prompt below.
   Remember the returned job ID.
4. Say in one line: the job ID, the interval, and that recurring jobs expire
   after 7 days.
5. Start (or resume) the work on the proof right away, in the same turn.

## Cron expression

Use the offset minute `M = min(3, 59 mod X)`. It avoids the :00 rush, and it
keeps every gap ≤ X, also across the hour boundary (the gap there is
`60 - X·floor((59-M)/X)`, which is ≤ X only when `M ≤ 59 mod X`).

| X | cron | note |
|---|------|------|
| 1 | `* * * * *` | |
| 2–59 | `M-59/X * * * *` | |
| 60 | `3 * * * *` | |
| multiple of 60, = 60·H | `3 */H * * *` | |
| other X > 60 | round down to a multiple of 60 | say so to the user |

Example: X = 10 → `3-59/10 * * * *` (fires at :03, :13, …, :53).

## Heartbeat prompt

Pass this as `prompt` (fill in X):

```
[heart-beat] Heartbeat (X min). You have been idle. Resume autonomous work
toward completing the proof: check where you left off (todo list, files,
build/check results, background agents) and continue. Work continuously; X is
the maximum idle time, not a work slice. When the proof is complete, delete
this heart-beat job with CronDelete and give a final recap.
```

## When a heartbeat fires

- Find the current state and continue the work. Do not only reply "still
  working".
- If the only thing left is waiting for background agents or builds you
  started, check their status, do any other useful work, and end the turn with
  one short line. The next heartbeat will check again.
- If you are blocked on input only the user can give, say the blocker in one
  sentence and `CronDelete` the heartbeat, so it does not fire in vain.

## When the proof is complete

1. Verify it (the project's proof checker passes, no `sorry` / `oops` / admitted
   steps remain).
2. `CronDelete` the heartbeat job.
3. Give a recap: what was proved, what changed, what is next.

## Stopping early

If the user says to stop the heart-beat, `CronDelete` the job and say so in one
line.
