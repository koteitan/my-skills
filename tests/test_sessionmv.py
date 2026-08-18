from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest


REPOSITORY = Path(__file__).resolve().parents[1]
SESSIONMV = REPOSITORY / "bin" / "sessionmv"


def encode_claude_path(path: Path) -> str:
    return "".join(character if character.isalnum() else "-" for character in str(path))


class SessionmvTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_directory.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.environment = os.environ.copy()
        self.environment["HOME"] = str(self.home)

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def run_sessionmv(self, *arguments: object) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(SESSIONMV), *(str(argument) for argument in arguments)],
            env=self.environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def make_codex_database(
        self, codex_home: Path, rows: list[tuple[str, Path, Path]]
    ) -> Path:
        database = codex_home / "state_5.sqlite"
        connection = sqlite3.connect(database)
        connection.execute(
            "CREATE TABLE threads (id TEXT PRIMARY KEY, rollout_path TEXT, cwd TEXT)"
        )
        connection.executemany(
            "INSERT INTO threads (id, rollout_path, cwd) VALUES (?, ?, ?)",
            [(session_id, str(rollout), str(cwd)) for session_id, rollout, cwd in rows],
        )
        connection.commit()
        connection.close()
        return database

    def write_rollout(self, path: Path, records: list[dict[str, object]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(
                json.dumps(record, separators=(",", ":")) + "\n" for record in records
            ),
            encoding="utf-8",
        )

    def test_codex_moves_directory_and_rewrites_session_metadata(self) -> None:
        source = self.root / "old project"
        source.mkdir()
        (source / "tracked.txt").write_text("content", encoding="utf-8")
        destination = self.root / "new project"
        sibling = self.root / "old project-other"

        codex_home = self.home / ".codex"
        self.environment["CODEX_HOME"] = str(codex_home)
        rollout = codex_home / "sessions" / "2026" / "08" / "13" / "rollout-a.jsonl"
        other_rollout = (
            codex_home / "sessions" / "2026" / "08" / "13" / "rollout-b.jsonl"
        )
        records = [
            {
                "type": "session_meta",
                "payload": {"id": "session-a", "cwd": str(source)},
            },
            {"type": "turn_context", "payload": {"cwd": str(source / "subdir")}},
            {"type": "event_msg", "payload": {"item": {"cwd": source.as_uri()}}},
            {
                "type": "event_msg",
                "payload": {"stdout": f"{source}\nkeep history unchanged"},
            },
        ]
        other_records = [
            {
                "type": "session_meta",
                "payload": {"id": "session-b", "cwd": str(sibling)},
            }
        ]
        self.write_rollout(rollout, records)
        self.write_rollout(other_rollout, other_records)
        database = self.make_codex_database(
            codex_home,
            [
                ("session-a", rollout, source),
                ("session-b", other_rollout, sibling),
            ],
        )

        result = self.run_sessionmv("--codex", source, destination)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(source.exists())
        self.assertEqual((destination / "tracked.txt").read_text(), "content")
        updated = [json.loads(line) for line in rollout.read_text().splitlines()]
        self.assertEqual(updated[0]["payload"]["cwd"], str(destination))
        self.assertEqual(updated[1]["payload"]["cwd"], str(destination / "subdir"))
        self.assertEqual(updated[2]["payload"]["item"]["cwd"], destination.as_uri())
        self.assertEqual(updated[3], records[3])
        self.assertEqual(
            [json.loads(line) for line in other_rollout.read_text().splitlines()],
            other_records,
        )
        connection = sqlite3.connect(database)
        rows = dict(connection.execute("SELECT id, cwd FROM threads"))
        connection.close()
        self.assertEqual(rows["session-a"], str(destination))
        self.assertEqual(rows["session-b"], str(sibling))
        self.assertIn("1 JSONL file(s), 1 state row(s), 3 cwd field(s)", result.stdout)

    def test_codex_refuses_an_open_matching_session(self) -> None:
        source = self.root / "source"
        source.mkdir()
        destination = self.root / "destination"
        codex_home = self.home / ".codex"
        self.environment["CODEX_HOME"] = str(codex_home)
        rollout = codex_home / "sessions" / "2026" / "08" / "13" / "rollout.jsonl"
        self.write_rollout(
            rollout,
            [{"type": "session_meta", "payload": {"id": "active", "cwd": str(source)}}],
        )
        self.make_codex_database(codex_home, [("active", rollout, source)])
        locks = codex_home / "thread-writer-locks"
        locks.mkdir()
        (locks / "active.lock").touch()

        result = self.run_sessionmv("--codex", source, destination)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("currently open", result.stderr)
        self.assertTrue(source.is_dir())
        self.assertFalse(destination.exists())

    def test_codex_requires_a_matching_session(self) -> None:
        source = self.root / "source"
        source.mkdir()
        destination = self.root / "destination"
        codex_home = self.home / ".codex"
        codex_home.mkdir()
        self.environment["CODEX_HOME"] = str(codex_home)

        result = self.run_sessionmv("--codex", source, destination)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no Codex session found", result.stderr)
        self.assertTrue(source.is_dir())
        self.assertFalse(destination.exists())

    def test_codex_validates_json_before_moving(self) -> None:
        source = self.root / "source"
        source.mkdir()
        destination = self.root / "destination"
        codex_home = self.home / ".codex"
        self.environment["CODEX_HOME"] = str(codex_home)
        rollout = codex_home / "sessions" / "2026" / "08" / "13" / "rollout.jsonl"
        self.write_rollout(
            rollout,
            [{"type": "session_meta", "payload": {"id": "broken", "cwd": str(source)}}],
        )
        with rollout.open("a", encoding="utf-8") as stream:
            stream.write("not JSON\n")
        self.make_codex_database(codex_home, [("broken", rollout, source)])

        result = self.run_sessionmv("--codex", source, destination)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid JSON", result.stderr)
        self.assertTrue(source.is_dir())
        self.assertFalse(destination.exists())

    def test_codex_rolls_directory_back_when_state_update_fails(self) -> None:
        source = self.root / "source"
        source.mkdir()
        (source / "file.txt").write_text("unchanged", encoding="utf-8")
        destination = self.root / "destination"
        codex_home = self.home / ".codex"
        self.environment["CODEX_HOME"] = str(codex_home)
        rollout = codex_home / "sessions" / "2026" / "08" / "13" / "rollout.jsonl"
        original_record = {
            "type": "session_meta",
            "payload": {"id": "read-only", "cwd": str(source)},
        }
        self.write_rollout(rollout, [original_record])
        database = self.make_codex_database(
            codex_home, [("read-only", rollout, source)]
        )
        database.chmod(0o444)

        result = self.run_sessionmv("--codex", source, destination)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("move failed", result.stderr)
        self.assertEqual((source / "file.txt").read_text(), "unchanged")
        self.assertFalse(destination.exists())
        self.assertEqual(json.loads(rollout.read_text()), original_record)

    def test_default_mode_keeps_claude_code_behavior(self) -> None:
        source = self.root / "source"
        source.mkdir()
        destination = self.root / "destination"
        projects = self.home / ".claude" / "projects"
        old_project = projects / encode_claude_path(source)
        old_project.mkdir(parents=True)
        session = old_project / "session.jsonl"
        session.write_text(
            json.dumps({"cwd": str(source)}, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

        result = self.run_sessionmv(source, destination)

        self.assertEqual(result.returncode, 0, result.stderr)
        new_project = projects / encode_claude_path(destination)
        self.assertTrue(destination.is_dir())
        self.assertFalse(old_project.exists())
        self.assertEqual(
            json.loads((new_project / "session.jsonl").read_text())["cwd"],
            str(destination),
        )


if __name__ == "__main__":
    unittest.main()
