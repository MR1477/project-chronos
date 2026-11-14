"""Exercise the persistent memory workflow in separate CLI processes."""

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path


CITATION_URL = "https://example.org/study"
STUDY_NOTES = """# Sample study notes

**Source** — Original astronomy fixture.

## Chapter 1 · Orbital motion

3. **Galileo and Kepler.** Galileo saw moons orbiting Jupiter. Kepler described elliptical paths. [Orbital observations](https://example.org/study)
4. **Newton.** Newton explained orbital motion using gravity. [Universal gravitation](https://example.org/study)

## Review questions

1. **Question.** What did they discover?
"""
QUESTION = "What did Galileo, Kepler, and Newton contribute to our understanding of orbital motion?"


class TestPersistentMemory(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        root = Path(workspace.name)
        self.database = root / "memory.sqlite3"
        self.source = root / "study.md"
        self.source.write_text(STUDY_NOTES, encoding="utf-8")

    def run_cli(self, *args):
        return subprocess.run(
            [
                sys.executable, "-m", "software.memory.cli",
                "--db", str(self.database), *args,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def successful_result(self, *args):
        result = self.run_cli(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_ingest_and_retrieve_original_note_identifiers_and_citations(self):
        imported = self.successful_result("ingest", str(self.source))
        self.assertEqual(imported["notes"], 2)
        self.assertEqual(self.successful_result("ingest", str(self.source)), imported)
        with closing(sqlite3.connect(self.database)) as connection:
            self.assertEqual(connection.execute("PRAGMA quick_check").fetchone(), ("ok",))

        results = self.successful_result("search", "Jupiter")
        self.assertEqual(len(results), 1)
        note = results[0]
        self.assertEqual(note["note_id"], 3)
        self.assertEqual(note["document_id"], imported["document_id"])
        self.assertEqual(note["chapter"], "Chapter 1 · Orbital motion")
        self.assertEqual(note["source"], "Original astronomy fixture.")
        self.assertEqual(note["citation"], {"label": "Orbital observations", "url": CITATION_URL})

    def test_orbital_motion_answer_survives_restart_and_source_removal(self):
        self.successful_result("ingest", str(self.source))
        before = self.successful_result("ask", QUESTION)
        self.assertEqual(before["status"], "supported")
        self.assertEqual({note["note_id"] for note in before["evidence"]}, {3, 4})
        self.assertIn("**Galileo and Kepler.**", before["answer"])
        self.assertIn("Galileo saw moons orbiting Jupiter.", before["answer"])
        self.assertIn("Newton explained orbital motion using gravity.", before["answer"])
        self.assertIn(f"[Universal gravitation]({CITATION_URL})", before["answer"])

        self.source.unlink()
        self.assertEqual(self.successful_result("ask", QUESTION), before)

    def test_missing_and_malformed_ingests_leave_existing_memory_intact(self):
        self.successful_result("ingest", str(self.source))
        missing = self.run_cli("ingest", str(self.source.with_name("missing.md")))
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("missing.md", missing.stderr)

        for invalid in (
            STUDY_NOTES.replace(f"[Universal gravitation]({CITATION_URL})", ""),
            STUDY_NOTES.replace("4. **Newton.", "3. **Newton."),
            "# No cited notes",
        ):
            with self.subTest(invalid=invalid):
                self.source.write_text(invalid, encoding="utf-8")
                result = self.run_cli("ingest", str(self.source))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Memory:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

        self.assertEqual(len(self.successful_result("search", "Jupiter")), 1)

    def test_empty_and_unsupported_questions(self):
        self.successful_result("ingest", str(self.source))
        for command in ("search", "ask"):
            result = self.run_cli(command, "  ")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("query", result.stderr)
        for question in ("What is photosynthesis?", "Did Galileo explain photosynthesis?"):
            result = self.successful_result("ask", question)
            self.assertEqual(result["status"], "insufficient_evidence")
            self.assertEqual(result["evidence"], [])
            self.assertNotIn("Jupiter", result["answer"])
        self.assertEqual(self.successful_result("search", "photosynthesis"), [])
