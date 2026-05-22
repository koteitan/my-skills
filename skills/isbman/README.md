# isbman — Isabelle build manager (human guide)

A thin wrapper around `isabelle build` that (1) makes it **safe to run
multiple Isabelle builds at once** and (2) gives every build a short
**isbman-id** so you can manage it **without knowing anything about git,
worktrees, or the current directory**.

An **isbman-id** (e.g. `04f31d`) is isbman's own handle for a build — not a
system PID and not Isabelle's session id.

Installed at `~/.claude/skills/isbman/scripts/isbman`, symlinked to
`~/bin/isbman` (on PATH), so you can just type `isbman`.

## Commands

```sh
isbman build -d . -v BMS      # same args as `isabelle build`; prints an isbman-id
isbman kill <isbman-id>       # kill that build — from ANY directory / later shell
isbman kill --all             # kill every running isbman build
isbman kill                   # kill build(s) started from the current directory
isbman ps                     # list every running build (isbman-id, dir, elapsed, args)
```

A build announces its isbman-id up front:

```
isbman: build started — isbman-id: 04f31d  (in /home/koteitan/bms-paper)
isbman: stop it with  ->  isbman kill 04f31d
```

Lost the isbman-id? `isbman ps` shows them all:

```
ISBMAN-ID  NPROC  ELAPSED   DIR                    BUILD-ARGS
04f31d     9      12s       bms-paper              -d . -v BMS
```

Override the timeout (default 1800s):

```sh
ISBMAN_TIMEOUT=600 isbman build -d . -v BMS
```

## Why it exists

When more than one Isabelle build runs at once (parallel agents, or you
starting an unrelated proof in another window), two problems appear:

1. **Heap DB lock contention.** Isabelle stores each session's compiled image
   as a SQLite file `…/heaps/polyml-*/log/<session>.db`. Two builds touching
   the same file collide.
2. **Imprecise kills.** A hung build often orphans the `poly` ML process at
   100% CPU. The old fix, `pkill -f polyml`, kills *every* poly for the user —
   including a healthy build elsewhere.

## How it works

### Build management is purely isbman-id-based

`isbman build` generates a short isbman-id and injects `ISBMAN_ID` (plus
`ISBMAN_DIR`, `ISBMAN_ARGS`) into the build's environment. Every process
Isabelle spawns — the JVM, `bash_process`, the **detached** `poly` session,
naproche — inherits these. `isbman kill <isbman-id>` / `isbman ps` scan
`/proc/<pid>/environ` for that exact isbman-id and act only on the matching
PIDs.

Consequences:
- **No directory/git/worktree knowledge needed.** The isbman-id is a global
  handle. You can `cd` anywhere, open a new shell, or kill a build a teammate
  started (same OS user) — `isbman kill <isbman-id>` just works.
- **No state files.** The running processes' own environment is the registry.
- **Precise.** A process-group kill alone would miss `poly` (it starts its own
  session); matching `ISBMAN_ID` in the environment catches it. Other OS
  users' processes aren't readable, so they're never touched.

### Heap isolation is an internal detail

You never have to think about this. Isabelle ignores `ISABELLE_HEAPS` set in
the environment (it recomputes it from `etc/settings`) but honors
`USER_HOME`. isbman points `USER_HOME` at a per-directory dir
(`~/.cache/isbman/home/<slug>`), so `ISABELLE_HEAPS` cascades to a private
location and builds in different directories write different `<session>.db`
files.

To avoid rebuilding HOL/ZF/etc. in that private location, HOL/Pure are read
from the read-only distribution heaps (`ISABELLE_HEAPS_SYSTEM`, untouched),
and the private heaps are **seeded once with a copy** (`cp -a`, ~32 MB) of the
shared user heaps. Real copies, not symlinks, so a local rebuild never
clobbers the shared originals.

## Not required: git, git-worktree, subagents

isbman is a plain CLI and needs none of these.
- **git**: used only to give the heaps dir a stable, cwd-independent label
  (so any subdir of a repo shares one heaps dir). Without git it falls back to
  `pwd`. Build management doesn't use git at all.
- **git-worktree**: irrelevant; if you do use worktrees, each maps to a
  different dir and is isolated automatically.
- **subagents**: completely unrelated; this is an OS-level CLI tool. A single
  build in a single shell works exactly the same.

Real requirements: Linux `/proc`, `bash`, coreutils (`md5sum`, `cp`, `tr`,
`od`, `sed`, `awk`), `setsid`, `timeout`, and `isabelle`.

## Layout & re-seeding

```
~/.cache/isbman/home/<slug>/.isabelle/<Isabelle-id>/heaps/…   # per-directory heaps
```

`<slug>` = `<basename>-<md5(abspath)[:8]>` of the git toplevel (or `pwd`).
Override the base dir with `ISBMAN_HOME`. To force fresh prerequisites:

```sh
rm -rf ~/.cache/isbman/home/<slug>
```

Nothing project-specific is baked in: all paths come from `isabelle getenv`,
session names are whatever you pass. Works for `BMS`, `BMS_ZF`, or any
unrelated proof.
