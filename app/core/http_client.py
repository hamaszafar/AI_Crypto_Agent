from __future__ import annotations

from typing import Any

import requests

from app.core.rate_limiter import RateLimiter
from app.core.retry.retry import RetryPolicy


class HTTPClient:
    """
    Shared HTTP client for external REST APIs.

    Responsibilities:
    - Apply rate limiting.
    - Apply retry policy.
    - Handle HTTP requests consistently.
    - Respect request timeout.
    """

    def __init__(
        self,
        rate_limiter: RateLimiter | None = None,
        retry_policy: RetryPolicy | None = None,
        timeout: float = 10.0,
        session: requests.Session | None = None,
    ) -> None:
        if timeout <= 0:
            raise ValueError(
                "timeout must be greater than zero"
            )

        self.rate_limiter = rate_limiter
        self.retry_policy = retry_policy
        self.timeout = timeout
        self.session = session

    def close(self) -> None:
        """Close the underlying HTTP session."""
        if self.session is not None:
            self.session.close()

    def __enter__(self) -> HTTPClient:
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> None:
        self.close()

    # ------------------------------------------------------------------
    # GET
    # ------------------------------------------------------------------

    def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> requests.Response:
        """
        Execute an HTTP GET request.

        Rate limiting is applied before the request.

        Retry behavior is delegated to RetryPolicy.
        """

        return self._request(
            method="GET",
            url=url,
            params=params,
            headers=headers,
        )

    # ------------------------------------------------------------------
    # Request
    # ------------------------------------------------------------------

    def _request(
        self,
        *,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> requests.Response:
        """
        Execute an HTTP request.

        GET requests intentionally use requests.get()
        so exchange-level tests and existing integrations
        can mock the GET transport directly.
        """

        def operation() -> requests.Response:
            if self.rate_limiter is not None:
                self.rate_limiter.acquire()

            if self.session is not None:
                if method.upper() == "GET":
                    return self.session.get(
                        url,
                        params=params,
                        headers=headers,
                        timeout=self.timeout,
                    )

                return self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                )
            else:
                if method.upper() == "GET":
                    return requests.get(
                        url,
                        params=params,
                        headers=headers,
                        timeout=self.timeout,
                    )

                return requests.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                )

        if self.retry_policy is None:
            return operation()

        return self.retry_policy.execute(
            operation
        )