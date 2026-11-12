"""Experiment 002's socket-free simulated receiver."""

import argparse
import hashlib
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


SECOND_NS = 1_000_000_000
SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_observations (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    observed_utc TEXT NOT NULL,
    monotonic_ns INTEGER NOT NULL,
    payload BLOB,
    sha256 TEXT,
    control_id TEXT,
    error TEXT
);
CREATE INDEX IF NOT EXISTS successful_observations ON raw_observations(id)
    WHERE sha256 IS NOT NULL;
CREATE TRIGGER IF NOT EXISTS reject_observation_update
BEFORE UPDATE ON raw_observations BEGIN
    SELECT RAISE(ABORT, 'raw observations are append-only');
END;
CREATE TRIGGER IF NOT EXISTS reject_observation_delete
BEFORE DELETE ON raw_observations BEGIN
    SELECT RAISE(ABORT, 'raw observations are append-only');
END;
CREATE TRIGGER IF NOT EXISTS reject_observation_replace
BEFORE INSERT ON raw_observations
WHEN EXISTS (SELECT 1 FROM raw_observations WHERE id = NEW.id) BEGIN
    SELECT RAISE(ABORT, 'raw observations are append-only');
END;
CREATE VIEW IF NOT EXISTS observations AS
SELECT current.*,
    CASE
        WHEN current.error IS NOT NULL THEN 'network_error'
        WHEN previous.id IS NULL THEN 'initial'
        WHEN current.sha256 = previous.sha256 THEN 'duplicate'
        ELSE 'change'
    END AS classification
FROM raw_observations AS current
LEFT JOIN raw_observations AS previous ON previous.id = (
    SELECT id FROM raw_observations
    WHERE sha256 IS NOT NULL AND id < current.id
    ORDER BY id DESC LIMIT 1
);
"""


class SimulatedEndpoint:
    """Hold a binary signal and optionally fail the next poll."""

    def __init__(self):
        self.signal = (b"", None)
        self.error = None

    def inject(self, payload: bytes, *, control_id: str | None = None):
        self.signal = (bytes(payload), control_id)

    def fail_next(self, reason: str):
        self.error = reason

    def __call__(self):
        if self.error is not None:
            reason, self.error = self.error, None
            raise ConnectionError(reason)
        return self.signal


class Receiver:
    def __init__(self, archive, endpoint: SimulatedEndpoint, *,
                 monotonic_ns=time.monotonic_ns, utc_now=None, sleep=time.sleep):
        self.archive = Path(archive)
        self.endpoint = endpoint
        self.monotonic_ns = monotonic_ns
        self.utc_now = utc_now if utc_now is not None else lambda: datetime.now(timezone.utc)
        self.sleep = sleep

    def __enter__(self):
        self.run_id = str(uuid.uuid4())
        self.archive.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            descriptor = os.open(self.archive, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(descriptor)
        self.connection = sqlite3.connect(self.archive)
        try:
            self.connection.executescript(SCHEMA)
        except BaseException:
            self.connection.close()
            raise
        return self

    def __exit__(self, *exc):
        self.connection.close()

    def poll(self):
        error = None
        try:
            payload, control_id = self.endpoint()
        except (ConnectionError, TimeoutError) as exc:
            payload = control_id = None
            error = str(exc)
        monotonic_ns = self.monotonic_ns()
        observed_utc = self.utc_now().astimezone(timezone.utc).isoformat(timespec="microseconds")
        sha256 = hashlib.sha256(payload).hexdigest() if payload is not None else None
        with self.connection:
            self.connection.execute(
                """INSERT INTO raw_observations
                   (run_id, observed_utc, monotonic_ns, payload, sha256, control_id, error)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (self.run_id, observed_utc, monotonic_ns, payload, sha256, control_id, error),
            )

    def run(self, polls: int | None = None):
        """Poll immediately, then on one-second deadlines. Skip missed ticks."""
        deadline = self.monotonic_ns()
        completed = 0
        while polls is None or completed < polls:
            remaining = deadline - self.monotonic_ns()
            while remaining > 0:
                self.sleep(remaining / SECOND_NS)
                remaining = deadline - self.monotonic_ns()
            self.poll()
            completed += 1
            deadline += SECOND_NS
            now = self.monotonic_ns()
            if now > deadline:
                missed = (now - deadline + SECOND_NS - 1) // SECOND_NS
                deadline += missed * SECOND_NS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path("data/ctsi/observations.sqlite3"))
    parser.add_argument("--polls", type=int, help="Stop after this many polls")
    parser.add_argument("--signal-file", type=Path, help="Inject this local file's bytes at startup")
    parser.add_argument("--control-id", help="Label the injected signal as a known control")
    parser.add_argument("--fail-first", action="store_true", help="Simulate an initial timeout")
    args = parser.parse_args()
    if args.polls is not None and args.polls < 1:
        parser.error("--polls must be positive")
    if args.control_id is not None and args.signal_file is None:
        parser.error("--control-id requires --signal-file")

    endpoint = SimulatedEndpoint()
    if args.signal_file is not None:
        endpoint.inject(args.signal_file.read_bytes(), control_id=args.control_id)
    if args.fail_first:
        endpoint.fail_next("simulated timeout")
    try:
        with Receiver(args.archive, endpoint) as receiver:
            receiver.run(args.polls)
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
