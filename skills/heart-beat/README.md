[← Back](../../README.md) | [English](README.md) | [Japanese](README-ja.md)

# heart-beat

A Claude Code skill that keeps the agent working on a proof until it is
complete, with a cron heartbeat that wakes the session when it goes idle.

## Usage

Say:

```
heart-beat 10分
```

The agent then acts as if told:

> Set a heartbeat with CronCreate every 10 minutes and work autonomously until
> the proof is complete. 10 minutes is not a work slice; it is the longest time
> the session may stay idle. Keep working continuously for as long as it takes.

## How it works

1. The agent removes any older heart-beat job and creates one recurring
   `CronCreate` job (e.g. `3-59/10 * * * *` for X = 10).
2. It starts working on the proof at once and keeps going.
3. Cron jobs fire only while the session is idle. So if a turn ends for any
   reason, the next heartbeat wakes the agent within X minutes, and it resumes
   from where it left off.
4. When the proof is complete (checker passes, no `sorry`), the agent deletes
   the job and gives a recap.

## Notes

- Jobs are session-only. They disappear when Claude Code exits.
- Recurring jobs auto-expire after 7 days.
- Say "stop the heart-beat" to cancel it.

See [SKILL.md](SKILL.md) for the exact cron table and heartbeat prompt.
