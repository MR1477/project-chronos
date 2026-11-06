
"""Unit tests for the Chronos Configuration Manager."""

import tempfile
import unittest
from pathlib import Path

from software.core.config import ConfigurationError, load_config


class TestChronosConfig(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.config_path = Path(self.temp_dir.name) / "test.toml"

    def write_config(self, content):
        self.config_path.write_text(content, encoding="utf-8")
        return self.config_path

    def test_valid_configuration(self):
        path = self.write_config(
            '[node]\nid = "chronos-node-001"\n'
        )
        config = load_config(path)
        self.assertEqual(config["node"]["id"], "chronos-node-001")

    def test_missing_file(self):
        with self.assertRaises(ConfigurationError):
            load_config(self.config_path)

    def test_invalid_toml(self):
        path = self.write_config("[node\nid = 123")
        with self.assertRaises(ConfigurationError):
            load_config(path)

    def test_missing_node_section(self):
        path = self.write_config('[core]\nversion = "0.1.0"')
        with self.assertRaises(ConfigurationError):
            load_config(path)

    def test_empty_node_id(self):
        path = self.write_config('[node]\nid = ""')
        with self.assertRaises(ConfigurationError):
            load_config(path)

    def test_whitespace_node_id(self):
        path = self.write_config('[node]\nid = "   "')
        with self.assertRaises(ConfigurationError):
            load_config(path)

    def test_numeric_node_id(self):
        path = self.write_config("[node]\nid = 123")
        with self.assertRaises(ConfigurationError):
            load_config(path)


if __name__ == "__main__":
    unittest.main()

