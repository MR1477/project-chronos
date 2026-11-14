"""Experiment 002's socket-free simulated receiver."""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread


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
CREATE TABLE IF NOT EXISTS poll_timing (
    observation_id INTEGER PRIMARY KEY REFERENCES raw_observations(id),
    scheduled_ns INTEGER NOT NULL,
    started_ns INTEGER NOT NULL,
    ended_ns INTEGER NOT NULL,
    lateness_ns INTEGER NOT NULL,
    missed_ticks INTEGER NOT NULL
);
CREATE VIEW IF NOT EXISTS timing_diagnostics AS
SELECT raw.run_id, COUNT(*) AS polls,
       SUM(raw.error IS NOT NULL) AS poll_errors,
       SUM(timing.lateness_ns > 0) AS late_polls,
       SUM(timing.missed_ticks) AS missed_ticks,
       MAX(timing.lateness_ns) AS max_lateness_ns,
       MAX(timing.ended_ns - timing.started_ns) AS max_poll_ns
FROM poll_timing AS timing
JOIN raw_observations AS raw ON raw.id = timing.observation_id
GROUP BY raw.run_id;
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
                 monotonic_ns=time.monotonic_ns, utc_now=None, sleep=time.sleep,
                 synchronous=None, diagnostics=None):
        self.archive = Path(archive)
        self.endpoint = endpoint
        self.monotonic_ns = monotonic_ns
        self.utc_now = utc_now if utc_now is not None else lambda: datetime.now(timezone.utc)
        self.sleep = sleep
        if synchronous not in (None, "FULL", "NORMAL"):
            raise ValueError("synchronous must be FULL or NORMAL")
        self.synchronous = synchronous
        self.diagnostics = diagnostics

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
            if self.synchronous is not None:
                self.connection.execute(f"PRAGMA synchronous={self.synchronous}")
            self.connection.executescript(SCHEMA)
        except BaseException:
            self.connection.close()
            raise
        return self

    def __exit__(self, *exc):
        self.connection.close()

    def poll(self, *, scheduled_ns=None, missed_ticks=0):
        self._write(self._acquire(scheduled_ns, missed_ticks))

    def _acquire(self, scheduled_ns, missed_ticks):
        started_ns = self.monotonic_ns()
        if scheduled_ns is None:
            scheduled_ns = started_ns
        error = None
        try:
            payload, control_id = self.endpoint()
        except (ConnectionError, TimeoutError) as exc:
            payload = control_id = None
            error = str(exc)
        monotonic_ns = self.monotonic_ns()
        observed_utc = self.utc_now().astimezone(timezone.utc).isoformat(timespec="microseconds")
        sha256 = hashlib.sha256(payload).hexdigest() if payload is not None else None
        return (scheduled_ns, started_ns, monotonic_ns, missed_ticks,
                observed_utc, payload, sha256, control_id, error)

    def _event(self, status, observation, sequence, **details):
        if self.diagnostics is not None:
            scheduled, started, acquired, missed = observation[:4]
            self.diagnostics(dict(status=status, run_id=self.run_id, sequence=sequence,
                                  scheduled_ns=scheduled, started_ns=started,
                                  acquired_ns=acquired, lateness_ns=started - scheduled,
                                  missed_ticks=missed, **details))

    def _write(self, acquired, sequence=None):
        (scheduled_ns, started_ns, monotonic_ns, missed_ticks,
         observed_utc, payload, sha256, control_id, error) = acquired
        transaction_started_ns = self.monotonic_ns() if self.diagnostics is not None else None
        with self.connection:
            observation = self.connection.execute(
                """INSERT INTO raw_observations
                   (run_id, observed_utc, monotonic_ns, payload, sha256, control_id, error)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (self.run_id, observed_utc, monotonic_ns, payload, sha256, control_id, error),
            )
            ended_ns = self.monotonic_ns()
            self.connection.execute(
                """INSERT INTO poll_timing
                   (observation_id, scheduled_ns, started_ns, ended_ns,
                    lateness_ns, missed_ticks)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (observation.lastrowid, scheduled_ns, started_ns, ended_ns,
                 started_ns - scheduled_ns, missed_ticks),
            )

        if transaction_started_ns is not None:
            committed_ns = self.monotonic_ns()
            self._event("committed", acquired, sequence, observation_id=observation.lastrowid,
                        transaction_started_ns=transaction_started_ns, committed_ns=committed_ns,
                        transaction_ns=committed_ns - transaction_started_ns,
                        queue_delay_ns=transaction_started_ns - monotonic_ns)

    def run(self, polls: int | None = None):
        """Poll immediately, then on one-second deadlines. Skip missed ticks."""
        deadline = self.monotonic_ns()
        completed = 0
        missed = 0
        while polls is None or completed < polls:
            remaining = deadline - self.monotonic_ns()
            while remaining > 0:
                self.sleep(remaining / SECOND_NS)
                remaining = deadline - self.monotonic_ns()
            self.poll(scheduled_ns=deadline, missed_ticks=missed)
            completed += 1
            deadline += SECOND_NS
            now = self.monotonic_ns()
            missed = max(0, (now - deadline + SECOND_NS - 1) // SECOND_NS)
            deadline += missed * SECOND_NS


class BufferedReceiver(Receiver):
    """Experimental FIFO acquisition with a single connection-owning writer."""

    def __init__(self, *args, queue_capacity=16, **kwargs):
        super().__init__(*args, **kwargs)
        if queue_capacity < 1 or self.diagnostics is None:
            raise ValueError("buffering requires a positive capacity and diagnostics")
        self.queue_capacity = queue_capacity

    def poll(self, *, scheduled_ns=None, missed_ticks=0):
        observation = self._acquire(scheduled_ns, missed_ticks)
        with self._event_lock:
            self._sequence += 1
            if self._failure is not None:
                self._event("dropped", observation, self._sequence, reason="writer_failed")
                raise RuntimeError("CTSI writer failed") from self._failure
            try:
                self._queue.put_nowait((self._sequence, observation))
            except Full:
                self._event("dropped", observation, self._sequence, reason="queue_full")
            else:
                self._event("queued", observation, self._sequence)

    def run(self, polls=None):
        self._queue = Queue(self.queue_capacity)
        self._event_lock = Lock()
        self._sequence = 0
        self._failure = None
        finished = Event()
        ready = Event()

        def writer():
            try:
                with self:
                    ready.set()
                    while not finished.is_set() or not self._queue.empty():
                        try:
                            sequence, observation = self._queue.get(timeout=0.1)
                        except Empty:
                            continue
                        # Publish admission before starting the write.
                        with self._event_lock:
                            pass
                        try:
                            self._write(observation, sequence)
                        except sqlite3.Error:
                            self._event("write_failed", observation, sequence)
                            raise
            except BaseException as exc:
                with self._event_lock:
                    self._failure = exc
            finally:
                ready.set()

        worker = Thread(target=writer, name="ctsi-writer")
        worker.start()
        try:
            ready.wait()
            if self._failure is None:
                super().run(polls)
        finally:
            finished.set()
            worker.join()
            while not self._queue.empty():
                sequence, observation = self._queue.get_nowait()
                self._event("dropped", observation, sequence, reason="writer_failed")
            if self._failure is not None:
                raise RuntimeError("CTSI writer failed") from self._failure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path("data/ctsi/observations.sqlite3"))
    parser.add_argument("--polls", type=int, help="Stop after this many polls")
    parser.add_argument("--signal-file", type=Path, help="Inject this local file's bytes at startup")
    parser.add_argument("--control-id", help="Label the injected signal as a known control")
    parser.add_argument("--fail-first", action="store_true", help="Simulate an initial timeout")
    parser.add_argument("--synchronous", choices=("FULL", "NORMAL"),
                        help="Override SQLite synchronous for this connection")
    parser.add_argument("--diagnostics", action="store_true", help="Emit JSON timing events to stderr")
    parser.add_argument("--buffered", type=int, metavar="CAPACITY", help="Use an experimental FIFO writer")
    args = parser.parse_args()
    if args.buffered is not None and (args.buffered < 1 or not args.diagnostics):
        parser.error("--buffered requires a positive capacity and --diagnostics")
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
        def report(event):
            print(json.dumps(event), file=sys.stderr, flush=True)

        options = dict(synchronous=args.synchronous, diagnostics=report if args.diagnostics else None)
        if args.buffered is None:
            with Receiver(args.archive, endpoint, **options) as receiver:
                receiver.run(args.polls)
        else:
            BufferedReceiver(args.archive, endpoint, queue_capacity=args.buffered,
                             **options).run(args.polls)
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
