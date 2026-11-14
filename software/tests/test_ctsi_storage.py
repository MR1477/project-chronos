import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from threading import Event
from unittest.mock import patch

from software.ctsi.receiver import BufferedReceiver, Receiver, SimulatedEndpoint


class StorageTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.archive = Path(directory.name) / "archive.sqlite3"
        self.events = []
        self.endpoint = SimulatedEndpoint()
        self.endpoint.inject(b"\x00\xff", control_id="binary")

    def test_transaction_timing_and_explicit_synchronous(self):
        with Receiver(self.archive, self.endpoint, synchronous="NORMAL",
                      diagnostics=self.events.append) as receiver:
            self.assertEqual(receiver.connection.execute("PRAGMA synchronous").fetchone(), (1,))
            receiver.poll()
        event, = self.events
        self.assertLessEqual(event["started_ns"], event["acquired_ns"])
        self.assertLessEqual(event["acquired_ns"], event["transaction_started_ns"])
        self.assertEqual(event["transaction_ns"],
                         event["committed_ns"] - event["transaction_started_ns"])
        self.assertEqual(event["status"], "committed")

    def test_buffer_drains_fifo_and_preserves_payload_hashes(self):
        values = iter([b"\xff", b"\x00", b"\x80"])
        receiver = BufferedReceiver(self.archive, lambda: (next(values), None),
                                    queue_capacity=3, diagnostics=self.events.append,
                                    monotonic_ns=lambda: 0, sleep=lambda _: None)
        # Use a fake scheduler clock to avoid a multi-second unit test.
        now = 0

        def sleep(seconds):
            nonlocal now
            now += round(seconds * 1e9)

        receiver.monotonic_ns = lambda: now
        receiver.sleep = sleep
        receiver.run(3)
        with closing(sqlite3.connect(self.archive)) as db:
            rows = db.execute("SELECT payload, sha256 FROM raw_observations ORDER BY id").fetchall()
        from hashlib import sha256
        self.assertEqual(rows, [(value, sha256(value).hexdigest())
                                for value in [b"\xff", b"\x00", b"\x80"]])
        self.assertEqual([e["sequence"] for e in self.events if e["status"] == "committed"],
                         [1, 2, 3])

    def test_full_queue_drops_newest_and_drains_existing(self):
        release = Event()
        dropped = Event()
        original = Receiver._write

        def blocked_write(receiver, observation, sequence=None):
            if not release.wait(5):
                raise RuntimeError("test did not release writer")
            return original(receiver, observation, sequence)

        def record(event):
            self.events.append(event)
            if event["status"] == "dropped":
                dropped.set()
                release.set()

        receiver = BufferedReceiver(self.archive, self.endpoint,
                                    queue_capacity=1, diagnostics=record)
        with patch.object(Receiver, "_write", blocked_write):
            receiver.run(3)
        self.assertTrue(dropped.is_set())
        self.assertEqual([e["sequence"] for e in self.events if e["status"] == "dropped"], [3])
        self.assertEqual([e["sequence"] for e in self.events if e["status"] == "committed"], [1, 2])

    def test_writer_failure_surfaces_and_accounts_for_failed_write(self):
        receiver = BufferedReceiver(self.archive, self.endpoint,
                                    diagnostics=self.events.append)
        with patch.object(Receiver, "_write", side_effect=sqlite3.OperationalError("disk full")):
            with self.assertRaisesRegex(RuntimeError, "CTSI writer failed"):
                receiver.run(1)
        self.assertEqual([e["status"] for e in self.events], ["queued", "write_failed"])
