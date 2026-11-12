"""Exercise Experiment 001 through its command line and SSH boundary."""

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

from software.learning.experiment001 import check_connection


class TestNotebook(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.source = self.root / "source.json"
        self.database = self.root / "notebook.sqlite3"
        self.manifest = {
            "edition": "Synthetic test fixture",
            "provenance": "Original text written for the test suite",
            "chapters": [
                {
                    "title": "Observations",
                    "passages": [
                        {
                            "locator": "p. 12",
                            "text": "A violet lamp flashes twice. The timer counts the flashes.",
                        },
                    ],
                },
                {
                    "title": "Measurements",
                    "passages": [
                        {"locator": "p. 15", "text": "A copper rod measures one metre."},
                    ],
                },
            ],
        }

    def run_cli(self, *args):
        return subprocess.run(
            [
                sys.executable, "-m", "software.learning.experiment001",
                "--db", str(self.database), *args,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def ingest(self):
        self.source.write_text(json.dumps(self.manifest), encoding="utf-8")
        result = self.run_cli("ingest", str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_grounded_notes_are_retrievable_after_restart_without_source_file(self):
        notebook = self.ingest()
        self.assertEqual(notebook["source"]["title"], "A Brief History of Time")
        self.assertEqual(notebook["source"]["author"], "Stephen Hawking")
        self.assertEqual(notebook["source"]["edition"], self.manifest["edition"])
        self.assertEqual(notebook["source"]["provenance"], self.manifest["provenance"])
        self.assertEqual(
            datetime.fromisoformat(notebook["created_at"]).utcoffset(),
            timezone.utc.utcoffset(None),
        )
        chapter = notebook["chapters"][0]
        self.assertEqual(chapter["title"], "Observations")
        note = chapter["notes"][0]
        self.assertEqual(note["excerpt"], "A violet lamp flashes twice.")
        self.assertIn("?", note["question"])
        self.assertEqual(note["locator"], "p. 12")
        self.assertEqual(self.ingest(), notebook)

        self.source.unlink()
        result = self.run_cli("show", notebook["id"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), notebook)

        result = self.run_cli("search", notebook["id"], "timer")
        self.assertEqual(result.returncode, 0, result.stderr)
        matches = json.loads(result.stdout)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["locator"], "p. 12")
        self.assertIn("The timer counts the flashes.", matches[0]["text"])

        result = self.run_cli("search", notebook["id"], "unmentioned")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [])

    def test_missing_or_uncited_source_does_not_create_notebook(self):
        missing = self.run_cli("ingest", str(self.source))
        self.assertNotEqual(missing.returncode, 0)
        self.manifest["chapters"][0]["passages"][0]["locator"] = " "
        self.source.write_text(json.dumps(self.manifest), encoding="utf-8")
        uncited = self.run_cli("ingest", str(self.source))
        self.assertNotEqual(uncited.returncode, 0)
        self.assertIn("locator", uncited.stderr)
        self.assertFalse(self.database.exists())

    def test_revised_source_preserves_original_notebook(self):
        original = self.ingest()
        self.manifest["chapters"][0]["passages"][0]["text"] = "The lamp flashes once."
        revised = self.ingest()
        self.assertNotEqual(original["id"], revised["id"])
        result = self.run_cli("show", original["id"])
        self.assertEqual(json.loads(result.stdout), original)


class TestConnection(unittest.TestCase):
    def test_simulated_unreachable_node_reconnects_with_bounded_ssh_attempts(self):
        run = Mock(side_effect=[
            subprocess.CompletedProcess([], 255, "", "ssh: No route to host"),
            subprocess.CompletedProcess([], 0, "", ""),
        ])
        pause = Mock()
        report = Mock()

        self.assertTrue(check_connection(attempts=2, run=run, pause=pause, report=report))
        self.assertEqual(run.call_count, 2)
        args, kwargs = run.call_args
        self.assertIn("StrictHostKeyChecking=yes", args[0])
        self.assertIn("BatchMode=yes", args[0])
        self.assertIn("pi@pi.local", args[0])
        self.assertLessEqual(kwargs["timeout"], 10)
        pause.assert_called_once()
        self.assertIn("unreachable", report.call_args_list[0].args[0])
        self.assertIn("connected", report.call_args_list[1].args[0])

    def test_resolution_and_authentication_failures_do_not_trigger_retry(self):
        for reason in ("Could not resolve hostname", "Permission denied (publickey)",
                       "Host key verification failed"):
            with self.subTest(reason=reason):
                run = Mock(return_value=subprocess.CompletedProcess([], 255, "", reason))
                pause = Mock()
                report = Mock()
                self.assertFalse(
                    check_connection(attempts=3, run=run, pause=pause, report=report)
                )
                run.assert_called_once()
                pause.assert_not_called()
                self.assertIn(reason, report.call_args.args[0])

    def test_connection_timeout_retries_then_stops(self):
        run = Mock(side_effect=subprocess.TimeoutExpired("ssh", 10))
        pause = Mock()
        self.assertFalse(
            check_connection(attempts=2, run=run, pause=pause, report=Mock())
        )
        self.assertEqual(run.call_count, 2)
        pause.assert_called_once()
