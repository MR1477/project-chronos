
"""Integration tests for Chronos Core startup."""

import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from software.core.main import main


class TestChronosStartup(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.config_path = Path(self.temp_dir.name) / "chronos.toml"

    def tearDown(self):
        logger = logging.getLogger("chronos")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()

    def write_config(self, content):
        self.config_path.write_text(content, encoding="utf-8")
        return self.config_path

    def test_successful_startup(self):
        self.write_config(
            '[node]\nid = "test-node-001"\n'
            '[core]\nlog_level = "INFO"\n'
        )

        with patch("software.core.main.setup_logging") as mock_logging:
            result = main(self.config_path)

        self.assertEqual(result, 0)
        mock_logging.assert_called_once()
        mock_logging.return_value.info.assert_any_call(
            "Node ID: %s", "test-node-001"
        )

    def test_missing_configuration(self):
        with patch("software.core.main.setup_logging") as mock_logging:
            result = main(self.config_path)

        self.assertEqual(result, 1)
        mock_logging.assert_not_called()

    def test_invalid_configuration(self):
        self.write_config('[node]\nid = ""')

        with patch("software.core.main.setup_logging") as mock_logging:
            result = main(self.config_path)

        self.assertEqual(result, 1)
        mock_logging.assert_not_called()

    def test_invalid_log_level(self):
        self.write_config(
            '[node]\nid = "test-node-001"\n'
            '[core]\nlog_level = "INVALID"\n'
        )

        result = main(self.config_path)
        self.assertEqual(result, 1)

    def test_logging_failure(self):
        self.write_config('[node]\nid = "test-node-001"')

        with patch(
            "software.core.main.setup_logging",
            side_effect=OSError("Disk unavailable"),
        ):
            result = main(self.config_path)

        self.assertEqual(result, 1)

    def test_default_log_level(self):
        self.write_config('[node]\nid = "test-node-001"')

        with patch("software.core.main.setup_logging") as mock_logging:
            result = main(self.config_path)

        self.assertEqual(result, 0)
        self.assertEqual(
            mock_logging.call_args.kwargs["log_level"],
            "INFO",
        )


if __name__ == "__main__":
    unittest.main()

