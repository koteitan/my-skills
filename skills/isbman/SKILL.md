---
name: isbman
description: >-
  Build, run, and safely kill Isabelle/HOL (and Isabelle/ZF) proof sessions.
  ALWAYS use this instead of bare `isabelle build` and instead of
  `pkill -f poly` / `pkill -f isabelle`. Triggers whenever you would run
  `isabelle build`, when a build hangs / times out and must be killed, when
  checking for orphaned poly/Isabelle processes, or when several builds /
  sessions / agents may run concurrently. Each build gets a short isbman-id
  (an isbman-specific handle, not a PID); kill it by isbman-id from anywhere
  (no git/worktree/cwd knowledge needed).
---

# isbman — Isabelle build manager

`isbman` is a drop-in wrapper for `isabelle build` plus precise,
isbman-id-based process control. On PATH (`~/bin/isbman` →
`~/.claude/skills/isbman/scripts/isbman`).

Note: an **isbman-id** is isbman's own short handle for a build (e.g.
`04f31d`). It is NOT a system PID and NOT Isabelle's session id.

## Use it by default

- **Build**: replace `isabelle build <args>` with **`isbman build <args>`**
  (same args, e.g. `isbman build -d . -v BMS`). It streams output like
  `isabelle build` and prints a short **isbman-id** at the start, e.g.:

  ```
  isbman: build started — isbman-id: 04f31d  (in /home/koteitan/bms-paper)
  isbman: stop it with  ->  isbman kill 04f31d
  ```

- **Kill**: `isbman kill <isbman-id>` — works from ANY directory / later
  shell, including a build started elsewhere by the same user. Also:
  - `isbman kill --all` — kill every running isbman build.
  - `isbman kill` (no arg) — kill build(s) started from the current directory.
- **List**: `isbman ps` — every running build, globally, with its isbman-id,
  the directory it was started in, elapsed time, and build args. Use this to
  recover an isbman-id you didn't capture.

## Hard rules

- **Never** run `isabelle build` directly, and **never** use
  `pkill -f poly` / `pkill -9 -u "$USER" -f polyml` / `pkill -f isabelle`.
  Those blanket kills hit every concurrent build for the user and clobber
  another session's / agent's work. `isbman kill <isbman-id>` (or `--all`) is
  the only approved kill path.
- After `isbman build`/`isbman kill` you do NOT need the old
  `ps -ef | grep poly` orphan check — isbman reaps the build's own processes
  on exit, timeout, and Ctrl-C. To confirm, use `isbman ps`.
- Capture the isbman-id from the build's first lines. If you lose it, run
  `isbman ps` to recover it.
- Timeout defaults to 1800s; override with `ISBMAN_TIMEOUT=<sec> isbman build ...`.

## Why it works (mechanism)

- **isbman-id-based reaping (no knowledge required).** isbman injects
  `ISBMAN_ID`/`ISBMAN_DIR`/`ISBMAN_ARGS` into the build's environment. Every
  process Isabelle spawns — JVM, bash_process, the **detached** poly ML
  session, naproche — inherits them. `kill`/`ps` scan `/proc/<pid>/environ`
  for the exact `ISBMAN_ID` and act only on those PIDs. The process
  environment IS the registry: no state files, no directory/git dependence.
  (A process-group kill alone misses poly, which detaches into its own
  session — the environ match is the source of truth. Only same-OS-user
  processes are inspectable, so other users are never touched.)
- **Heap isolation (internal detail).** Isabelle ignores a direct
  `ISABELLE_HEAPS` env override but honors `USER_HOME`, from which
  `ISABELLE_HEAPS` cascades. isbman points `USER_HOME` at a per-directory dir
  under `$ISBMAN_HOME` (default `~/.cache/isbman`), so builds in different
  directories never fight over the same `<session>.db` (SQLite lock). HOL is
  read from the read-only distribution heaps; the isolated heaps are one-time
  seeded with a copy of the shared user heaps so prerequisites (ZF,
  ZF-Constructible, prior project images) are not rebuilt.

## Not required: git, git-worktree, subagents

isbman is a plain CLI. It needs none of these. git is used only
opportunistically to give the heaps dir a cwd-independent label (falls back
to `pwd`). Build management is entirely isbman-id-based and global. Real
requirements: Linux `/proc`, bash, coreutils, `setsid`, `timeout`, `isabelle`.

## Caveat

The isolated heaps are seeded once per directory. If you later rebuild a
prerequisite in the SHARED heaps and want a directory to pick it up, delete
its isolated home (`rm -rf "$ISBMAN_HOME/home/<slug>"`) to force a re-seed.
