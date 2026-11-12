import hashlib
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from software.ctsi.receiver import Receiver, SimulatedEndpoint


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "observations.sqlite3"
        self.endpoint = SimulatedEndpoint()
        self.now = 0
        self.wall = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def receiver(self):
        return Receiver(self.path, self.endpoint, monotonic_ns=lambda: self.now,
                        utc_now=lambda: self.wall, sleep=self.sleep)

    def sleep(self, seconds):
        self.now += round(seconds * 1_000_000_000)

    def observations(self):
        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute("SELECT * FROM observations ORDER BY id").fetchall()

    def test_binary_injection_and_unexpected_change(self):
        with self.receiver() as receiver:
            receiver.poll()
            self.endpoint.inject(b"\x00\xff", control_id="control-1")
            receiver.poll()
            receiver.poll()
            self.endpoint.inject(b"unknown")
            receiver.poll()
        first, changed, duplicate, unexpected = self.observations()
        self.assertEqual([row["classification"] for row in self.observations()],
                         ["initial", "change", "duplicate", "change"])
        self.assertEqual(first["payload"], b"")
        self.assertEqual(changed["payload"], b"\x00\xff")
        self.assertEqual(changed["sha256"], hashlib.sha256(b"\x00\xff").hexdigest())
        self.assertEqual(changed["control_id"], "control-1")
        self.assertEqual(duplicate["control_id"], "control-1")
        self.assertIsNone(unexpected["control_id"])

    def test_restart_and_simulated_network_failure(self):
        self.endpoint.inject(b"signal")
        with self.receiver() as receiver:
            receiver.poll()
        self.endpoint.fail_next("timeout")
        with self.receiver() as receiver:
            receiver.run(2)
        first, error, last = self.observations()
        self.assertNotEqual(first["run_id"], last["run_id"])
        self.assertEqual(error["classification"], "network_error")
        self.assertEqual(error["error"], "timeout")
        self.assertIsNone(error["payload"])
        self.assertIsNone(error["sha256"])
        self.assertEqual(last["classification"], "duplicate")
        self.assertEqual([first["id"], error["id"], last["id"]], [1, 2, 3])

    def test_wall_clock_jumps_and_poll_work_do_not_shift_deadlines(self):
        starts = []

        def endpoint():
            starts.append(self.now)
            self.now += 250_000_000
            self.wall += timedelta(hours=[0, -2, 4][len(starts) - 1])
            return self.endpoint()

        with Receiver(self.path, endpoint, monotonic_ns=lambda: self.now,
                      utc_now=lambda: self.wall, sleep=self.sleep) as receiver:
            receiver.run(3)
        self.assertEqual(starts, [0, 1_000_000_000, 2_000_000_000])
        first, second, third = self.observations()
        self.assertEqual(second["monotonic_ns"], 1_250_000_000)
        self.assertLess(second["observed_utc"], first["observed_utc"])
        self.assertGreater(third["observed_utc"], first["observed_utc"])

    def test_raw_observations_reject_update_and_delete(self):
        with self.receiver() as receiver:
            receiver.poll()
        with sqlite3.connect(self.path) as connection:
            for statement in ("UPDATE raw_observations SET payload = NULL",
                              "DELETE FROM raw_observations"):
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(statement)
