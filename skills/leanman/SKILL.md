---
name: leanman
description: Check Lean 4 proof files safely from many agents at once, and kill runaway checks by handle. ALWAYS use this instead of bare `lake build`, bare `lean file.lean`, raw curl to kimina-lean-server, and instead of `pkill -f lean`. Triggers whenever you would verify a Lean file, when several agents check proofs concurrently, when a check hangs and must be killed, or when a worker runs inside the codex sandbox where kimina-lean-server is unreachable. Each job gets a short leanman-id (a leanman handle, not a PID); kill it by leanman-id from anywhere.
---

[← Back](../../README.md) | [English](README.md) | [Japanese](README-ja.md)

# leanman — Lean 4 proof-check manager

`leanman` is the single command for checking Lean 4 files under concurrency,
plus precise, leanman-id-based process control. It is the Lean counterpart of
[`isbman`](../isbman/SKILL.md) and follows the same model. On PATH
(`~/bin/leanman` → `~/my-skills/skills/leanman/scripts/leanman`).

A **leanman-id** is leanman's own short handle for a job (e.g. `04f31d`). It is
NOT a system PID.

## Roles

- **Manager** (Claude Code, full permissions): runs `leanman setup` once, owns
  every `leanman build`, kills stuck jobs with `leanman kill`.
- **Worker** (`codex:rescue` subagent, or another Claude Code): writes proof
  files in its own workspace and runs `leanman check` only. Workers never run
  `lake build` and never touch the project tree.

## Use it by default

- **Prepare (manager, once, serial)**: `leanman setup [-C PROJECT]` — runs
  `lake build`, caches `LEAN_PATH` + the `lean` binary, finds a matching
  kimina-lean-server, and records the project as the default so workers can
  just say `leanman check FILE.lean` from anywhere. `--no-build` skips the
  build when the library is already current; `--no-default` caches without
  claiming the shared default (see below); `--set-default` takes the default
  over on purpose.

  **`setup` is optional.** If every command passes `-C PROJECT`, you can skip
  it entirely: the first `check` resolves and caches `LEAN_PATH` itself
  (~1.9s), and later ones are ~1.4s. Use `setup` for the `lake build` and for
  recording a default — not because checks require it. `leanman build` leaves
  the cache refreshed, so a build never costs the next check anything.

- **Check (worker, parallel)**: `leanman check [-m MEMO] FILE.lean`. Add `-C
  PROJECT` if no default is recorded, `--json` for machine-readable output,
  `--backend kimina|lean` to override the automatic choice. `-m` labels the job
  in `leanman ps` — pass it when several agents run at once.

- **Build (manager only)**: `leanman build [-m MEMO] [lake-build-args...]` —
  wraps `lake build` under an exclusive lock.

- **List**: `leanman ps` — every running job, globally, with leanman-id, kind,
  directory, memo, elapsed time, and target file.

- **Kill**: `leanman kill <leanman-id>` from ANY directory. Also
  `leanman kill --all`, or `leanman kill` with no argument to kill the jobs
  started from the current project.

- **Diagnose**: `leanman doctor` — which backend would be used and why, whether
  this shell is sandboxed, and whether the `LEAN_PATH` cache is fresh.

## Read the exit code, never the output

```
0    green    no error, no sorry
1    sorry    compiles, but a sorry remains
2    error    Lean reported an error
3    infra    usage error, no project, no backend, refused default takeover
124  timeout  killed by LEANMAN_TIMEOUT — a runaway proof
143  killed   stopped by `leanman kill` (SIGTERM; 137 if it needed SIGKILL,
              130 on Ctrl-C) — reported as `killed`, not as a failed proof
```

Only 0 is green. Everything else means the file is not proved, but 124/143
additionally mean *nothing was decided* — the check never finished, so do not
report it as an error in the proof either.

This matters more than it looks. `lean` prints **nothing** on success, and a
tool call whose command was cut short also returns empty output. "No output"
therefore does not mean green, and an agent that reports success from silence
is reporting a proof it never verified. `leanman check` collapses that to one
number: only exit 0 is green.

### `#print axioms` output is void unless the exit code is 0 or 1

Lean fills a **failed elaboration** with `sorryAx`, and the partially
elaborated term can drag in further axioms with it. A declaration whose proof
errored therefore reports axioms it does not use — `sorryAx`, and
`Classical.choice` alongside it — even when the file contains no `sorry`:

```
$ grep -c sorry t-ax2.lean
0
$ leanman check --json t-ax2.lean
  verdict: error / exit 2
  error : Tactic `rfl` failed: ...
  info  : 'PSS.t_c' depends on axioms: [propext, sorryAx, Classical.choice, Quot.sound]
```

Since `sorryAx > 0` is normally treated as an unconditional regression, reading
that line without checking the exit code first produces a false alarm — the
direction that teaches people to discount the check.

It is most convincing in a multi-theorem file: the declarations that *did*
elaborate print clean `[propext, Quot.sound]` lines a few rows above, so the
block reads as "this one theorem regressed and picked up choice as well". It
regressed in no way; it has simply not elaborated yet.

**Read the exit code first.** `check` tests for errors before anything else, so
exit 2 means Lean reported at least one error and **every** axiom figure in
that run is void — not only `sorryAx`. Only on exit 0 or 1 does
`#print axioms` describe the proof you actually wrote. There is no separate
error count in `--json` because the exit code already carries it; `raw` holds
the full message list if you need details.

## Several projects on one machine

`LEANMAN_HOME` holds **one** recorded default project, shared by every agent
and every session on the box. A worker that runs a bare
`leanman check FILE.lean` — no `-C`, not inside a project tree — resolves
through it. So on a machine proving more than one project at a time:

- **Pass `-C PROJECT` in every worker prompt.** It costs one flag and removes
  the whole class of "verified against the wrong project" mistakes.
- If you are the *second* project, run `leanman setup --no-default -C PROJECT`
  (or skip `setup` altogether). Plain `setup` now refuses to repoint an
  existing different default and tells you to choose `--set-default` or
  `--no-default`, so the accident cannot happen silently — but only the
  refusal is automatic; picking the right flag is yours.
- `leanman doctor -C PROJECT` prints which project currently owns the default
  and warns when it is not the one you asked about.

`leanman ps` shows the last two path components (`trio/lean`, `git/lean`),
because Lean projects are conventionally `<name>/lean` and a bare basename
makes every project on the machine look identical.

## Hard rules

- **Never** run `lake build` from a worker agent, and never run it from more
  than one place at a time. It writes into `.lake`; concurrent writers corrupt
  each other. `leanman build` / `leanman setup` serialise it behind an
  exclusive lock — that is the only approved path.
- **Never** use `pkill -f lean` / `pkill -f lake`. A blanket kill hits every
  concurrent agent. `leanman kill <leanman-id>` (or `--all`) is the only
  approved kill path.
- **Never** POST to kimina-lean-server by hand. `leanman check` picks it only
  when it is reachable AND serves this exact project; a hand-rolled curl can
  silently verify against a different project's environment.
- Workers do **not** edit library files that other agents import. They write
  their own proof files. When a library really must change, the manager stops
  the fan-out, runs `leanman build`, restarts kimina, and resumes.

## Backends

| | latency | needs network | timeout kills the work? |
|---|---|---|---|
| `kimina` | ~0.2s | yes | **no** — see below |
| `lean` | ~1.3s | no | yes |

`codex:rescue` runs its shell under seccomp that denies `socket()`, `connect()`
and `bind()` outright, so **no** HTTP client can reach kimina from there — not
curl, not a Unix socket, not a relay. The `lean` backend needs no network at
all, so a sandboxed worker runs the identical command and gets the identical
exit codes. Detection is free: the failed probe costs ~3ms under the sandbox.

### Choosing a backend

Default to `auto` — write plain `leanman check FILE.lean` and let it decide.
Override only for the reasons in the last table of this section.

| how | effect |
|---|---|
| `leanman check FILE.lean` | `auto` (default): kimina when usable, else `lean` |
| `leanman check --backend lean FILE.lean` | always `lean`; kimina is never consulted |
| `leanman check --backend kimina FILE.lean` | kimina required; **exits 3 if unreachable** instead of silently falling back |
| `LEANMAN_BACKEND=lean` | change the default for a whole agent / fan-out |
| `LEANMAN_KIMINA_URL=http://host:port/api/check` | point at a specific instance; skips the project match |

`auto` picks kimina only when **all** of these hold:

1. an endpoint is known — `LEANMAN_KIMINA_URL`, else the URL `leanman setup`
   recorded for this project, else the kimina `.env`;
2. if it came from the `.env`, that instance's `LEAN_SERVER_PROJECT_DIR` equals
   this project root — one kimina serves exactly one project, and checking
   against another project's environment yields confident, wrong answers;
3. the port answers a plain GET.

Otherwise it uses `lean`. To disable kimina for one project permanently,
delete `$LEANMAN_HOME/proj/<slug>/kimina.url` — but note a matching `.env`
lets it be rediscovered, so `LEANMAN_BACKEND=lean` is the reliable switch.

`--backend kimina` fails loudly on purpose. Silently degrading to `lean` would
hide the case where you believed you were checking against the resident REPL
and were not.

### When to override

| situation | use |
|---|---|
| ordinary proof iteration | `auto` (nothing to pass) |
| the proof might not terminate — unbounded `decide`, deep `simp`, recursion with no visible fuel | `--backend lean` |
| right after `leanman build`, before the manager has restarted kimina | `--backend lean` — the REPL still holds the previous oleans |
| a bulk run where the ~1.1s difference actually matters and a wrong backend must not pass unnoticed | `--backend kimina` |
| worker running inside the codex sandbox | nothing — `auto` already resolves to `lean` |

## The one thing a timeout cannot do on the kimina backend

`LEANMAN_TIMEOUT` and `leanman kill` reap the **client**. On the `lean` backend
that is the whole computation, so a runaway proof dies. On the `kimina` backend
the elaboration is happening inside the server's resident REPL, and dropping
the HTTP connection does not stop it — the snippet runs to completion in the
server, and while it does, every other agent's checks slow down roughly 10x
(measured: 210ms → 2833ms, recovering once the REPL is free).

So when a proof might not terminate — an unbounded `decide`, a deep `simp`, a
recursion with no obvious fuel — run it with **`--backend lean`**. You pay
~1.1s more per check and get a timeout that actually kills the work. Reserve
the kimina backend for proofs you expect to converge.

## Driving `codex:rescue` as a worker

Measured on codex-cli 0.147.0 with the Codex Companion plugin 1.0.6.

### Launch it from the Agent tool, not the slash command

Spawn `subagent_type: "codex:codex-rescue"` with the `Agent` tool. That
subagent declares `tools: Bash`, so it *cannot* prompt the user. The
`/codex:rescue` slash command is a different path — it holds `AskUserQuestion`
and asks "continue the existing Codex thread or start a new one?" once per
invocation whenever a resumable thread exists, so twenty rescues mean nineteen
prompts. Either way, passing `--fresh` (or `--resume`) suppresses the question,
and `--wait` / `--background` chooses whether the manager blocks.

Leave `--model` and `--effort` unset; they come from `~/.codex/config.toml`.

### What its sandbox allows

| | |
|---|---|
| `socket()` / `connect()` / `bind()` | **denied, EPERM** — kimina is unreachable by any means: no curl, no Unix socket, no relay process |
| the Lean project tree | **read-only** — the worker cannot edit it or build it |
| its cwd and `/tmp` | writable (with `--write`; read-only otherwise, cwd included) |
| `/proc/<pid>/environ`, `kill`, `setsid`, `timeout`, `flock` | allowed |
| `leanman` on `PATH` | yes — `~/bin` is on the sandbox PATH |

So a codex worker runs `leanman check` unchanged: `auto` resolves to `lean`,
and the exit codes match a host run exactly (verified 0/1/2 on both sides).
`LEANMAN_HOME` defaults into `/tmp` precisely so this works.

### Prompt template

```
Work in <WORKDIR>. The Lean project is <PROJECT> and is READ-ONLY to you:
never edit a file inside it. Do not run `lake build`, `lake env lean`, or
`lean` directly — `leanman check` is your ONLY way to verify anything.

Write your proof file as <WORKDIR>/<name>.lean and verify it with exactly:

    leanman check -m <agent-label> -C <PROJECT> <name>.lean; echo "exit=$?"

Judge the result by the EXIT CODE, never by the output:
    0 = green (no error, no sorry)   1 = a sorry remains
    2 = Lean error                   124 = runaway, killed
`lean` prints nothing on success, so empty output on its own proves nothing.

Iterate until exit 0. Report the final file contents and the last exit code.
If you cannot reach exit 0, say so plainly — do not claim success.
```

### Behaviour to expect

- **It will reach for `lake env lean` on its own** if the instructions leave
  room. Observed: told to verify via kimina and finding the socket blocked, it
  fell back to `lake env lean` even though the prompt forbade `lake`. Forbid
  `lake` explicitly and give it `leanman check` as the only sanctioned command,
  or its work escapes `leanman ps` and the build lock.
- **The 30s shell limit is a yield, not a kill.** A command that runs longer
  keeps running in the model's process session and it polls for the rest
  (verified: a 45s command returned its output after one poll). A ~1.3s check
  never touches this, and a long job is not truncated — but the first return
  arrives with empty stdout, which is one more reason the exit-code contract
  matters.
- **The manager can kill a sandboxed worker's runaway check.** environ scanning
  is global per user, so a job started inside the sandbox shows up in the
  manager's `leanman ps` and dies to `leanman kill <id>` (verified end to end).
- **Threads are scoped per cwd.** Codex records its thread against the
  workspace root it ran in, so `--resume` from a different directory finds
  nothing. Fix the worker's cwd across a task if you intend to resume it.
  `--resume` genuinely restores the conversation — not a summary — but state
  lives in `/tmp/codex-companion/` and is lost on reboot.
- **A stale job blocks resume.** A rescue that was interrupted leaves its
  record at `status: running`, and the next `--resume` in that workspace throws
  `Task <id> is still running`. Clear it with `/codex:cancel <id>`.

## Why parallel checks are safe

A Lean *check* writes nothing — it succeeds with the project tree mounted
read-only. Only `lake build` writes. So `check` takes a **shared** lock and
`build`/`setup` take an **exclusive** one: N checks run at full speed together,
and no check can ever observe half-written oleans. Measured: 8 concurrent
checks finish in the wall time of one.

**A build that takes minutes at near-zero CPU is lock-blocked, not slow.**
`user 0m0.5s` / `sys 0m6.9s` against 9 minutes of wall clock means the process
is waiting on lake's lock while something else holds it. Run `leanman ps`
before killing anything: SIGTERM-ing the waiter only adds contenders, and the
same work under `leanman build`'s exclusive lock finishes in seconds.

Memory is the practical ceiling, and it is mild. Each `lean` process shows
~3.3 GB RSS, but that is the mmap'd Mathlib olean set counted once per process;
the marginal cost is **~330 MB per concurrent check**, linear. On a 28-core /
31 GB box, CPU binds long before memory.

## Mechanism

- **leanman-id reaping.** leanman injects `LEANMAN_ID` / `LEANMAN_KIND` /
  `LEANMAN_DIR` / `LEANMAN_TARGET` / `LEANMAN_MEMO` into the job's environment;
  every child inherits them. `ps`/`kill` scan `/proc/<pid>/environ` for the
  exact `LEANMAN_ID` and act only on those PIDs. The process environment IS the
  registry — no daemon, no PID files to go stale. Only same-OS-user processes
  are inspectable, so other users are never touched. This works from inside the
  codex sandbox too (`/proc` reads and `kill` are permitted there).
- **`LEAN_PATH` caching.** Going through `lake` costs ~1.2s, most of a check's
  wall time. leanman resolves `LEAN_PATH` and the `lean` binary in a **single**
  `lake env` call (two `printenv` calls cost twice as much — 868ms vs 433ms),
  caches both per project keyed on the mtimes of `lakefile.*`,
  `lean-toolchain` and `lake-manifest.json`, and bypasses `lake` entirely
  afterwards: 1.8s → 1.4s per check. `leanman build` re-derives the cache on
  success, so the entry after a build is fresh rather than merely invalidated.
- **State in `/tmp`.** `LEANMAN_HOME` defaults to `/tmp/leanman-<uid>` because
  the codex sandbox can write `/tmp` but not `~/.cache`. Everything there is
  regenerable; losing it costs one `leanman setup`.

## After a library rebuild

A running kimina-lean-server holds the **old** oleans in its resident REPL.
Restart it before checking against it, or snippets fail with
`Unknown identifier` — or worse, pass against stale definitions. Until it is
restarted, check with `--backend lean`, which reads oleans from disk every
time and is therefore never stale.

`leanman build` prints this reminder **only when a kimina actually serves the
project it just built**, and names that server's URL. On a machine running
several projects an unconditional reminder is worse than none: the only kimina
in sight usually belongs to somebody else's project, and restarting it breaks
their agents.

## Env overrides

```
LEANMAN_HOME            state dir            (default /tmp/leanman-<uid>)
LEANMAN_TIMEOUT         check timeout, secs  (default 300)
LEANMAN_BUILD_TIMEOUT   build timeout, secs  (default 3600)
LEANMAN_BACKEND         auto | kimina | lean (default auto)
LEANMAN_PROJECT         project root, overrides the recorded default
LEANMAN_KIMINA_URL      force this endpoint, skipping the project match
LEANMAN_KIMINA_ENV      kimina .env to read  (default ~/proofs/pss-proof/kimina-lean-server/.env)
LEANMAN_MEMO            default memo for -m
```

## Requirements

Linux `/proc`, bash, coreutils, `setsid`, `timeout`, `flock`, `md5sum`,
`python3`, and `lake`/`lean` on PATH. Nothing project-specific is hardcoded;
the project is found by walking up to a `lakefile.lean` / `lakefile.toml`.
