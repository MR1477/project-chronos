"""Continuous execution runtime for Project Chronos."""

from threading import Event


class ChronosRuntime:
    """Run periodic Chronos tasks until shutdown is requested."""

    def __init__(self, heartbeat, interval_seconds=60, stop_event=None):
        if not callable(heartbeat):
            raise TypeError("heartbeat must be callable")

        if isinstance(interval_seconds, bool) or not isinstance(
            interval_seconds, (int, float)
        ) or not 0 < interval_seconds < float("inf"):
            raise ValueError("interval_seconds must be a positive finite number")

        self.heartbeat = heartbeat
        self.interval_seconds = interval_seconds
        self.stop_event = stop_event if stop_event is not None else Event()

    def run(self):
        """Execute heartbeats until a shutdown is requested."""
        while not self.stop_event.is_set():
            self.heartbeat()
            self.stop_event.wait(self.interval_seconds)

    def stop(self):
        """Request graceful shutdown."""
        self.stop_event.set()


def create_shutdown_handler(runtime):
    """Create a signal handler that requests graceful shutdown."""

    def handle_shutdown(signum, frame):
        runtime.stop()

    return handle_shutdown
