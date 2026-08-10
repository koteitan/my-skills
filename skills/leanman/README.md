[← Back](../../README.md) | [English](README.md) | [Japanese](README-ja.md)

# leanman

A Lean 4 proof-check manager for multi-agent work: one command that checks a
Lean file, picks a backend that works even inside a restricted sandbox, and
gives every job a short handle you can kill it by.

The skill itself lives in [SKILL.md](SKILL.md); the tool is
[scripts/leanman](scripts/leanman). This file explains what it is and why it
looks the way it does.

## The problem

Several agents proving Lean lemmas at the same time hit four distinct walls.

1. **`lake build` is not concurrent.** It writes into `.lake`; two of them
   racing corrupt each other. But *checking* a file writes nothing, so the two
   need different treatment rather than a blanket "don't run Lean in parallel".
2. **Silence is ambiguous.** `lean` prints nothing when a file is fine. A tool
   call whose command was cut short also returns nothing. An agent that reads
   "no output" as "proved it" reports a proof it never verified.
3. **The fast checker is unreachable from a sandbox.** `codex:rescue` runs its
   shell under seccomp that denies `socket()`, `connect()` and `bind()`, so
   nothing at all can talk to kimina-lean-server from there — not curl, not a
   Unix-domain socket, not a relay process.
4. **Killing a stuck check is dangerous.** `pkill -f lean` takes out every
   other agent's work along with the one you meant.

## What leanman does

- `leanman setup` is the one serial step: build the library, cache `LEAN_PATH`,
  locate a matching kimina server, record the project as the default.
- `leanman check FILE.lean` is what workers run, in parallel, from anywhere.
  It returns **0 green / 1 sorry / 2 error / 124 timeout** — a number, not a
  silence to interpret.
- It chooses **kimina** (~0.2s) when that server is reachable *and* serves this
  exact project, otherwise a direct **`lean`** invocation (~1.3s) that needs no
  network. A sandboxed worker runs the same command and gets the same codes.
- `check` takes a shared lock, `build`/`setup` an exclusive one, so N checks
  run at full speed and none can see half-written oleans.
- Every job carries a **leanman-id**; `leanman ps` lists them and
  `leanman kill <id>` kills exactly one, from any directory.

## Design notes

**Why the environment is the registry.** Like `isbman`, leanman injects
`LEANMAN_*` variables into each job and finds its processes by scanning
`/proc/<pid>/environ`. No daemon, no PID file that can go stale, and it works
from inside the sandbox because `/proc` reads and `kill` are permitted there.

**Why `/tmp` and not `~/.cache`.** The codex sandbox grants write access to the
workspace and `/tmp` only. Putting state in `~/.cache` would make every
sandboxed worker fail. Nothing in `LEANMAN_HOME` is precious.

**Why the `LEAN_PATH` cache exists.** `lake` costs ~1.2s of startup, and the
actual elaboration of a small proof file is ~0.09s. Caching `LEAN_PATH` and
calling `lean` directly removes most of the per-check wall time.

**Why kimina is matched against the project.** One kimina instance serves
exactly one `LEAN_SERVER_PROJECT_DIR`. Checking against the wrong project's
environment produces confident, wrong answers, so leanman uses kimina only when
the directories match, and silently prefers the slower, always-correct path
otherwise.

## Measurements

Taken on the pss-proof Lean project (Lean 4.30 + Mathlib), 28 cores / 31 GB:

| | |
|---|---|
| `lake env lean` (cold, via lake) | 1.81s |
| `lean` with cached `LEAN_PATH` | 1.29s |
| kimina (resident REPL) | 0.07s |
| pure elaboration of the file | 0.09s |
| 8 concurrent checks, total | 1.79s |
| marginal memory per concurrent check | ~330 MB |
| kimina probe failure inside the sandbox | 3ms |

## Relationship to isbman

[`isbman`](https://github.com/koteitan/isbman) is the same idea for
Isabelle/HOL, and leanman borrows its id-based reaping wholesale. The
differences come from Lean: no heap isolation is needed (a check writes
nothing, so there is no store to isolate and no `gc` subcommand), and there are
two backends instead of one because a resident REPL exists and is sometimes
reachable.
