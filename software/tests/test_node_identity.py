
"""Automated tests for the Chronos Node Identity Manager."""

import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from software.core.node_identity import (
    NodeIdentityError,
    load_or_create_identity,
)


class TestNodeIdentity(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.identity_path = (
            Path(self.temp_dir.name) / "node" / "identity.json"
        )

    def test_identity_creation(self):
        identity = load_or_create_identity(self.identity_path)

        self.assertTrue(self.identity_path.exists())
        self.assertIn("node_id", identity)
        self.assertIn("created_at", identity)

    def test_valid_uuid(self):
        identity = load_or_create_identity(self.identity_path)

        parsed = uuid.UUID(identity["node_id"])
        self.assertEqual(str(parsed), identity["node_id"])
        self.assertEqual(parsed.version, 4)

    def test_identity_persistence(self):
        first = load_or_create_identity(self.identity_path)
        second = load_or_create_identity(self.identity_path)

        self.assertEqual(first, second)

    def test_unique_node_identities(self):
        first = load_or_create_identity(self.identity_path)

        second_path = (
            Path(self.temp_dir.name) / "other" / "identity.json"
        )
        second = load_or_create_identity(second_path)

        self.assertNotEqual(first["node_id"], second["node_id"])

    def test_corrupted_json(self):
        self.identity_path.parent.mkdir(parents=True)
        self.identity_path.write_text("{invalid json", encoding="utf-8")

        with self.assertRaises(NodeIdentityError):
            load_or_create_identity(self.identity_path)

    def test_missing_node_id(self):
        self.identity_path.parent.mkdir(parents=True)
        self.identity_path.write_text(
            json.dumps({"created_at": "2026-11-06T00:00:00+00:00"}),
            encoding="utf-8",
        )

        with self.assertRaises(NodeIdentityError):
            load_or_create_identity(self.identity_path)

    def test_invalid_timestamp(self):
        self.identity_path.parent.mkdir(parents=True)
        self.identity_path.write_text(
            json.dumps({
                "node_id": str(uuid.uuid4()),
                "created_at": "not-a-date",
            }),
            encoding="utf-8",
        )

        with self.assertRaises(NodeIdentityError):
            load_or_create_identity(self.identity_path)

    def test_write_failure(self):
        with patch(
            "pathlib.Path.write_text",
            side_effect=OSError("Disk unavailable"),
        ):
            with self.assertRaises(NodeIdentityError):
                load_or_create_identity(self.identity_path)


if __name__ == "__main__":
    unittest.main()


