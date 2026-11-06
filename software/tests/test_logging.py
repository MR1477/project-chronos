
"""Automated tests for the Chronos Logging Manager."""

import logging
import tempfile
import unittest
from pathlib import Path

from software.core.logging_setup import setup_logging


class TestChronosLogging(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.log_dir = Path(self.temp_dir.name) / "logs"

    def tearDown(self):
        logger = logging.getLogger("chronos")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()

    def test_log_file_creation(self):
        logger = setup_logging(self.log_dir)
        logger.info("Test message")

        log_file = self.log_dir / "chronos.log"
        self.assertTrue(log_file.exists())
        self.assertIn(
            "Test message",
            log_file.read_text(encoding="utf-8"),
        )

    def test_info_level(self):
        logger = setup_logging(self.log_dir, log_level="INFO")
        logger.debug("Hidden debug message")
        logger.info("Visible info message")

        content = (self.log_dir / "chronos.log").read_text(
            encoding="utf-8"
        )

        self.assertIn("Visible info message", content)
        self.assertNotIn("Hidden debug message", content)

    def test_debug_level(self):
        logger = setup_logging(self.log_dir, log_level="DEBUG")
        logger.debug("Debug test message")

        content = (self.log_dir / "chronos.log").read_text(
            encoding="utf-8"
        )

        self.assertIn("Debug test message", content)

    def test_invalid_level(self):
        with self.assertRaises(ValueError):
            setup_logging(self.log_dir, log_level="INVALID")

    def test_invalid_max_bytes(self):
        with self.assertRaises(ValueError):
            setup_logging(self.log_dir, max_bytes=0)

    def test_invalid_backup_count(self):
        with self.assertRaises(ValueError):
            setup_logging(self.log_dir, backup_count=0)

    def test_log_rotation(self):
        logger = setup_logging(
            self.log_dir,
            max_bytes=200,
            backup_count=2,
        )

        for index in range(30):
            logger.info("Rotation test message %d", index)

        self.assertTrue(
            (self.log_dir / "chronos.log.1").exists()
        )

    def test_reconfiguration(self):
        logger = setup_logging(self.log_dir)
        initial_handler_count = len(logger.handlers)

        logger = setup_logging(self.log_dir)

        self.assertEqual(
            len(logger.handlers),
            initial_handler_count,
        )
        self.assertEqual(len(logger.handlers), 2)


if __name__ == "__main__":
    unittest.main()


