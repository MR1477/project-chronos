
"""Automated tests for Project Chronos Core."""

import importlib.util
import platform
import unittest
from pathlib import Path


CORE_PATH = Path(__file__).resolve().parents[1] / "core" / "main.py"

spec = importlib.util.spec_from_file_location("chronos_core", CORE_PATH)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


class TestChronosCore(unittest.TestCase):

    def test_version(self):
        """Chronos should report the correct version."""
        self.assertEqual(core.CHRONOS_VERSION, "0.1.0")

    def test_system_information(self):
        """System information should contain the required fields."""
        info = core.get_system_info()

        required_fields = [
            "chronos_version",
            "python_version",
            "operating_system",
            "architecture",
        ]

        for field in required_fields:
            with self.subTest(field=field):
                self.assertIn(field, info)

    def test_python_version(self):
        """Reported Python version should match the runtime."""
        info = core.get_system_info()
        self.assertEqual(
            info["python_version"],
            platform.python_version()
        )

    def test_operating_system(self):
        """Reported operating system should match the runtime."""
        info = core.get_system_info()
        self.assertEqual(
            info["operating_system"],
            platform.system()
        )


if __name__ == "__main__":
    unittest.main()

