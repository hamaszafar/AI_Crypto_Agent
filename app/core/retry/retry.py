from __future__ import annotations

import time
from typing import Callable, TypeVar

import requests


T = TypeVar("T")


class RetryError(Exception):
    """Raised when an operation fails after all retry attempts."""

    def __init__(
        self,
        message: str,
        *,
        last_exception: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.last_exception = last_exception


class RetryPolicy:
    """
    Reusable retry policy for HTTP/network operations.

    Retries:
    - requests.Timeout
    - requests.ConnectionError
    - HTTP 429
    - HTTP 5xx

    Does not retry other HTTP 4xx errors.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        backoff_factor: float = 1.0,
        max_backoff: float = 30.0,
        jitter: bool = True,
    ) -> None:
        if max_attempts < 1:
            raise ValueError(
                "max_attempts must be >= 1"
            )

        if backoff_factor < 0:
            raise ValueError(
                "backoff_factor must be >= 0"
            )

        if max_backoff < 0:
            raise ValueError(
                "max_backoff must be >= 0"
            )

        self.max_attempts = max_attempts
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        self.jitter = jitter

    def should_retry_exception(
        self,
        exc: Exception,
    ) -> bool:
        return isinstance(
            exc,
            (
                requests.Timeout,
                requests.ConnectionError,
            ),
        )

    def should_retry_response(
        self,
        response: requests.Response,
    ) -> bool:
        status_code = response.status_code

        return (
            status_code == 429
            or 500 <= status_code <= 599
        )

    def get_backoff(
        self,
        attempt: int,
    ) -> float:
        if attempt < 1:
            raise ValueError(
                "attempt must be >= 1"
            )

        delay = (
            self.backoff_factor
            * (2 ** (attempt - 1))
        )

        base_delay = min(
            delay,
            self.max_backoff,
        )
        
        if self.jitter:
            import random
            return random.uniform(base_delay * 0.5, base_delay * 1.5)
        return base_delay

    def get_retry_after(
        self,
        response: requests.Response,
    ) -> float | None:
        value = response.headers.get(
            "Retry-After"
        )

        if value is None:
            return None

        try:
            delay = float(value)
        except (TypeError, ValueError):
            return None

        if delay < 0:
            return None

        return min(
            delay,
            self.max_backoff,
        )

    def execute(
        self,
        operation: Callable[[], T],
    ) -> T:
        last_exception: Exception | None = None

        for attempt in range(
            1,
            self.max_attempts + 1,
        ):
            try:
                result = operation()

                if isinstance(
                    result,
                    requests.Response,
                ):
                    # Success
                    if result.ok:
                        return result

                    # Retryable HTTP status
                    if self.should_retry_response(
                        result
                    ):
                        if (
                            attempt
                            == self.max_attempts
                        ):
                            result.raise_for_status()

                        retry_after = (
                            self.get_retry_after(
                                result
                            )
                        )

                        delay = (
                            retry_after
                            if retry_after is not None
                            else self.get_backoff(
                                attempt
                            )
                        )

                        time.sleep(delay)
                        continue

                    # Non-retryable 4xx
                    result.raise_for_status()

                return result

            except (
                requests.Timeout,
                requests.ConnectionError,
            ) as exc:
                last_exception = exc

                if (
                    attempt
                    == self.max_attempts
                ):
                    break

                time.sleep(
                    self.get_backoff(attempt)
                )

        raise RetryError(
            "Operation failed after maximum retry attempts.",
            last_exception=last_exception,
        )