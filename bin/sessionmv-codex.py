#!/usr/bin/env python3
"""Move a directory and rewrite the Codex sessions rooted below it."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import sys
import tempfile
from typing import Any, NoReturn
from urllib.parse import quote, unquote, urlsplit, urlunsplit
import uuid


def error(message: str) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def is_below(path: str, root: str) -> bool:
    return path == root or path.startswith(root + os.sep)


def replace_path(value: str, src: str, dst: str) -> str:
    """Replace src in an absolute path or a file:// URI, on path boundaries."""
    if is_below(value, src):
        return dst + value[len(src) :]

    parts = urlsplit(value)
    if parts.scheme != "file":
        return value

    uri_path = unquote(parts.path)
    if not is_below(uri_path, src):
        return value
    new_path = dst + uri_path[len(src) :]
    return urlunsplit(parts._replace(path=quote(new_path, safe="/:@")))


def rewrite_cwds(value: Any, src: str, dst: str) -> int:
    """Rewrite path-valued `cwd` fields recursively, returning the edit count."""
    edits = 0
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "cwd" and isinstance(child, str):
                replacement = replace_path(child, src, dst)
                if replacement != child:
                    value[key] = replacement
                    edits += 1
            else:
                edits += rewrite_cwds(child, src, dst)
    elif isinstance(value, list):
        for child in value:
            edits += rewrite_cwds(child, src, dst)
    return edits


def session_metadata(path: Path) -> tuple[str, str] | None:
    """Return (session id, cwd) from a rollout's first record."""
    try:
        with path.open(encoding="utf-8") as stream:
            first = stream.readline()
        record = json.loads(first)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None

    if record.get("type") != "session_meta":
        return None
    payload = record.get("payload")
    if not isinstance(payload, dict) or not isinstance(payload.get("cwd"), str):
        return None
    session_id = payload.get("id") or payload.get("session_id") or ""
    return str(session_id), payload["cwd"]


def discover_rollouts(codex_dir: Path, src: str) -> tuple[set[Path], set[str]]:
    rollouts: set[Path] = set()
    session_ids: set[str] = set()
    for directory_name in ("sessions", "archived_sessions"):
        directory = codex_dir / directory_name
        if not directory.is_dir():
            continue
        for path in directory.rglob("*.jsonl"):
            metadata = session_metadata(path)
            if metadata is None:
                continue
            session_id, cwd = metadata
            if is_below(cwd, src):
                rollouts.add(path)
                if session_id:
                    session_ids.add(session_id)
    return rollouts, session_ids


def state_rows(
    codex_dir: Path, src: str
) -> tuple[list[tuple[Path, list[tuple[str, str, str]]]], set[Path], set[str]]:
    """Find matching state DB rows and any rollout paths referenced by them."""
    databases: list[tuple[Path, list[tuple[str, str, str]]]] = []
    rollouts: set[Path] = set()
    session_ids: set[str] = set()

    for database in sorted(codex_dir.glob("state_*.sqlite")):
        try:
            connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(threads)")
            }
            if not {"id", "cwd", "rollout_path"}.issubset(columns):
                connection.close()
                continue
            rows = [
                (str(thread_id), str(cwd), str(rollout_path or ""))
                for thread_id, cwd, rollout_path in connection.execute(
                    "SELECT id, cwd, rollout_path FROM threads"
                )
                if isinstance(cwd, str) and is_below(cwd, src)
            ]
            connection.close()
        except sqlite3.Error as exc:
            error(f"cannot read Codex state database {database}: {exc}")

        if not rows:
            continue
        databases.append((database, rows))
        for session_id, _cwd, rollout_path in rows:
            session_ids.add(session_id)
            if rollout_path:
                path = Path(rollout_path)
                if not path.is_absolute():
                    path = codex_dir / path
                if path.is_file():
                    rollouts.add(path)

    return databases, rollouts, session_ids


def refuse_active_sessions(codex_dir: Path, session_ids: set[str]) -> None:
    lock_dir = codex_dir / "thread-writer-locks"
    active = sorted(
        session_id
        for session_id in session_ids
        if (lock_dir / f"{session_id}.lock").exists()
    )
    if active:
        shown = ", ".join(active[:3])
        if len(active) > 3:
            shown += f", ... ({len(active)} total)"
        error(
            "matching Codex session is currently open; close it and retry "
            f"(session: {shown})"
        )


def stage_rollout(path: Path, src: str, dst: str) -> tuple[Path, int]:
    """Create a fully validated, rewritten sibling temp file."""
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.sessionmv-", dir=path.parent
    )
    temp_path = Path(temp_name)
    edits = 0
    try:
        with (
            path.open(encoding="utf-8", newline="") as source,
            os.fdopen(descriptor, "w", encoding="utf-8", newline="") as target,
        ):
            for line_number, line in enumerate(source, start=1):
                ending = ""
                body = line
                if body.endswith("\n"):
                    ending = "\n"
                    body = body[:-1]
                    if body.endswith("\r"):
                        ending = "\r\n"
                        body = body[:-1]
                try:
                    record = json.loads(body)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"invalid JSON at {path}:{line_number}: {exc}"
                    ) from exc
                line_edits = rewrite_cwds(record, src, dst)
                if line_edits:
                    target.write(
                        json.dumps(record, ensure_ascii=False, separators=(",", ":"))
                        + ending
                    )
                    edits += line_edits
                else:
                    target.write(line)
        shutil.copystat(path, temp_path)
        os.chmod(temp_path, stat.S_IMODE(path.stat().st_mode))
        return temp_path, edits
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temp_path.unlink(missing_ok=True)
        raise


def restore_database(
    database: Path, rows: list[tuple[str, str, str]], src: str, dst: str
) -> None:
    """Best-effort reversal after a database commit succeeded."""
    connection = sqlite3.connect(database, timeout=5)
    try:
        with connection:
            for session_id, old_cwd, _rollout_path in rows:
                new_cwd = dst + old_cwd[len(src) :]
                connection.execute(
                    "UPDATE threads SET cwd = ? WHERE id = ? AND cwd = ?",
                    (old_cwd, session_id, new_cwd),
                )
    finally:
        connection.close()


def move_codex(src_arg: str, dst_arg: str) -> None:
    source = Path(src_arg).resolve()
    if not source.is_dir():
        error(f"source directory not found: {src_arg}")

    destination = Path(dst_arg).resolve(strict=False)
    if destination.is_dir():
        destination = destination / source.name
    if destination.exists():
        error(f"destination already exists: {destination}")
    if source == destination:
        error("source and destination are the same")
    try:
        destination.relative_to(source)
    except ValueError:
        pass
    else:
        error("destination is inside source")
    if not destination.parent.is_dir():
        error(f"destination parent directory not found: {destination.parent}")

    source_string = str(source)
    destination_string = str(destination)
    codex_dir = Path(
        os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))
    ).expanduser()

    rollouts, session_ids = discover_rollouts(codex_dir, source_string)
    databases, database_rollouts, database_ids = state_rows(codex_dir, source_string)
    rollouts.update(database_rollouts)
    session_ids.update(database_ids)
    if not rollouts and not any(rows for _database, rows in databases):
        error(f"no Codex session found for {source_string} (nothing moved)")

    refuse_active_sessions(codex_dir, session_ids)

    staged: dict[Path, Path] = {}
    edit_count = 0
    try:
        for rollout in sorted(rollouts):
            temp_path, edits = stage_rollout(rollout, source_string, destination_string)
            staged[rollout] = temp_path
            edit_count += edits
    except (OSError, UnicodeError, ValueError) as exc:
        for temp_path in staged.values():
            temp_path.unlink(missing_ok=True)
        error(str(exc))

    connections: list[tuple[Path, list[tuple[str, str, str]], sqlite3.Connection]] = []
    backups: dict[Path, Path] = {}
    moved = False
    committed: list[tuple[Path, list[tuple[str, str, str]]]] = []
    try:
        shutil.move(str(source), str(destination))
        moved = True

        for database, rows in databases:
            connection = sqlite3.connect(database, timeout=5)
            connections.append((database, rows, connection))
            connection.execute("BEGIN IMMEDIATE")
            for session_id, old_cwd, _rollout_path in rows:
                new_cwd = destination_string + old_cwd[len(source_string) :]
                connection.execute(
                    "UPDATE threads SET cwd = ? WHERE id = ? AND cwd = ?",
                    (new_cwd, session_id, old_cwd),
                )

        for rollout, temp_path in staged.items():
            backup = rollout.with_name(
                f".{rollout.name}.sessionmv-backup-{uuid.uuid4().hex}"
            )
            os.replace(rollout, backup)
            backups[rollout] = backup
            os.replace(temp_path, rollout)

        for database, rows, connection in connections:
            connection.commit()
            committed.append((database, rows))

    except (OSError, sqlite3.Error) as exc:
        for _database, _rows, connection in connections:
            try:
                connection.rollback()
            except sqlite3.Error:
                pass
        for database, rows in reversed(committed):
            try:
                restore_database(database, rows, source_string, destination_string)
            except sqlite3.Error as restore_error:
                print(
                    f"warning: could not roll back {database}: {restore_error}",
                    file=sys.stderr,
                )
        for rollout, backup in backups.items():
            if backup.exists():
                try:
                    os.replace(backup, rollout)
                except OSError as restore_error:
                    print(
                        f"warning: could not restore {rollout}: {restore_error}",
                        file=sys.stderr,
                    )
        if moved:
            try:
                shutil.move(str(destination), str(source))
            except OSError as restore_error:
                print(
                    f"warning: could not move directory back to {source}: {restore_error}",
                    file=sys.stderr,
                )
        for temp_path in staged.values():
            temp_path.unlink(missing_ok=True)
        error(f"move failed: {exc}")
    finally:
        for _database, _rows, connection in connections:
            connection.close()

    for backup in backups.values():
        try:
            backup.unlink()
        except OSError as exc:
            print(f"warning: could not remove backup {backup}: {exc}", file=sys.stderr)

    database_row_count = sum(len(rows) for _database, rows in databases)
    print(f"moved: {source_string} -> {destination_string}")
    print(
        "updated Codex sessions: "
        f"{len(rollouts)} JSONL file(s), {database_row_count} state row(s), "
        f"{edit_count} cwd field(s)"
    )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: sessionmv --codex <a> <b>", file=sys.stderr)
        raise SystemExit(1)
    move_codex(sys.argv[1], sys.argv[2])
