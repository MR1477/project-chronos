"""Regression tests for the documented Chronos command-line entry point."""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestChronosCLI(unittest.TestCase):
    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.project_root = Path(temp_dir.name)
        source = Path(__file__).resolve().parents[1]
        software = self.project_root / "software"
        shutil.copytree(
            source / "core", software / "core", ignore=shutil.ignore_patterns("__pycache__")
        )
        (software / "config").mkdir()
        shutil.copyfile(
            source / "config" / "chronos.example.toml",
            software / "config" / "chronos.example.toml",
        )

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "software.core.main", *args],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_default_startup_initializes_and_exits(self):
        result = self.run_cli()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Chronos Core initialized successfully", result.stderr)
        self.assertTrue((self.project_root / "data/node/identity.json").is_file())

    def test_help_prints_usage_without_starting_core(self):
        result = self.run_cli("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout)
        self.assertIn("Project Chronos Core", result.stdout)
        self.assertIn("--continuous", result.stdout)
        self.assertEqual(result.stderr, "")
        self.assertFalse((self.project_root / "logs").exists())
        self.assertFalse((self.project_root / "data").exists())

    def test_unknown_option_reports_usage_without_starting_core(self):
        result = self.run_cli("--unknown-option")

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("usage:", result.stderr)
        self.assertIn("unrecognized arguments: --unknown-option", result.stderr)
        self.assertFalse((self.project_root / "logs").exists())
        self.assertFalse((self.project_root / "data").exists())
