"""Tests for the Chronos continuous runtime."""

import unittest
from threading import Event, Thread
from unittest.mock import Mock

from software.core.runtime import ChronosRuntime


class TestChronosRuntime(unittest.TestCase):

    def test_heartbeat_and_clean_shutdown(self):
        """Runtime executes a heartbeat and stops when requested."""
        stop_event = Event()
        heartbeat = Mock(side_effect=stop_event.set)

        runtime = ChronosRuntime(
            heartbeat=heartbeat,
            interval_seconds=60,
            stop_event=stop_event,
        )

        runtime.run()

        heartbeat.assert_called_once_with()
        self.assertTrue(stop_event.is_set())

    def test_repeated_heartbeats(self):
        """Runtime repeats heartbeats until shutdown."""
        stop_event = Event()
        heartbeat = Mock()

        def on_heartbeat():
            if heartbeat.call_count == 3:
                stop_event.set()

        heartbeat.side_effect = on_heartbeat

        runtime = ChronosRuntime(
            heartbeat=heartbeat,
            interval_seconds=0.001,
            stop_event=stop_event,
        )

        runtime.run()

        self.assertEqual(heartbeat.call_count, 3)
        self.assertTrue(stop_event.is_set())



    def test_invalid_intervals(self):
        """Runtime rejects invalid heartbeat intervals."""
        for interval in (0, -1, float("inf"), float("nan"), True, "60"):
            with self.subTest(interval=interval):
                with self.assertRaises(ValueError):
                    ChronosRuntime(
                        heartbeat=Mock(),
                        interval_seconds=interval,
                    )



    def test_external_shutdown(self):
        """An external stop request interrupts the waiting interval."""
        stop_event = Event()
        heartbeat_started = Event()
        heartbeat = Mock(side_effect=heartbeat_started.set)

        runtime = ChronosRuntime(
            heartbeat=heartbeat,
            interval_seconds=3600,
            stop_event=stop_event,
        )

        worker = Thread(target=runtime.run, daemon=True)
        worker.start()

        try:
            self.assertTrue(heartbeat_started.wait(timeout=2))
            runtime.stop()
            worker.join(timeout=2)
            self.assertFalse(worker.is_alive())
            heartbeat.assert_called_once_with()
        finally:
            runtime.stop()
            worker.join(timeout=2)



    def test_shutdown_signal_handler(self):
        """Shutdown handler requests runtime termination."""
        from signal import SIGTERM
        from software.core.runtime import create_shutdown_handler

        runtime = Mock()
        handler = create_shutdown_handler(runtime)

        handler(SIGTERM, None)

        runtime.stop.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
