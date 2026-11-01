"""Thread-safe Lamport logical clock."""
from threading import Lock


class LamportClock:
    def __init__(self):
        self._value = 0
        self._lock = Lock()

    @property
    def value(self):
        with self._lock:
            return self._value

    def tick(self):
        """Advance the local clock before emitting an event or message."""
        with self._lock:
            self._value += 1
            return self._value

    def receive(self, remote):
        """Merge a received timestamp using Lamport's max(local, remote) + 1 rule."""
        with self._lock:
            self._value = max(self._value, int(remote)) + 1
            return self._value
