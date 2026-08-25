from __future__ import annotations

import time
from threading import Lock


class RateLimiter:
    """
    Simple thread-safe token-bucket-style rate limiter.

    Example:
        RateLimiter(max_requests=10, window_seconds=1)

    allows at most 10 requests during a 1-second window.
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: float = 1.0,
    ) -> None:
        if max_requests < 1:
            raise ValueError(
                "max_requests must be greater than zero"
            )

        if window_seconds <= 0:
            raise ValueError(
                "window_seconds must be greater than zero"
            )

        self.max_requests = max_requests
        self.window_seconds = window_seconds

        self._requests: list[float] = []
        self._lock = Lock()

    def acquire(self) -> None:
        """
        Wait until a request is allowed.
        """

        while True:
            with self._lock:
                now = time.monotonic()

                self._remove_expired(now)

                if len(self._requests) < self.max_requests:
                    self._requests.append(now)
                    return

                oldest = self._requests[0]
                wait_time = (
                    self.window_seconds
                    - (now - oldest)
                )

            if wait_time > 0:
                time.sleep(wait_time)

    def _remove_expired(self, now: float) -> None:
        cutoff = now - self.window_seconds

        while (
            self._requests
            and self._requests[0] <= cutoff
        ):
            self._requests.pop(0)

    def reset(self) -> None:
        """
        Clear the current request history.
        """

        with self._lock:
            self._requests.clear()

    @property
    def current_requests(self) -> int:
        """
        Return the number of requests currently
        inside the active rate-limit window.
        """

        with self._lock:
            now = time.monotonic()

            self._remove_expired(now)

            return len(self._requests)