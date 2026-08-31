from unittest.mock import Mock, patch

import pytest
import requests

from app.core.http_client import HTTPClient
from app.core.rate_limiter import RateLimiter
from app.core.retry.retry import RetryPolicy


def make_response(status_code: int) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response.url = "https://example.com"
    return response


def create_client(
    *,
    rate_limiter: RateLimiter | None = None,
    retry_policy: RetryPolicy | None = None,
    session: requests.Session | None = None,
) -> HTTPClient:
    return HTTPClient(
        rate_limiter=rate_limiter
        or RateLimiter(
            max_requests=10,
            window_seconds=1,
        ),
        retry_policy=retry_policy
        or RetryPolicy(
            max_attempts=3,
            backoff_factor=0,
        ),
        session=session,
    )


def test_get_returns_successful_response():
    session = Mock()
    session.get.return_value = make_response(200)

    client = create_client(session=session)

    response = client.get(
        "https://example.com/api",
    )

    assert response.status_code == 200

    session.get.assert_called_once_with(
        "https://example.com/api",
        params=None,
        headers=None,
        timeout=10.0,
    )


def test_get_passes_params_and_headers():
    session = Mock()
    session.get.return_value = make_response(200)

    client = create_client(session=session)

    response = client.get(
        "https://example.com/api",
        params={"symbol": "BTCUSDT"},
        headers={"X-Test": "value"},
    )

    assert response.status_code == 200

    session.get.assert_called_once_with(
        "https://example.com/api",
        params={"symbol": "BTCUSDT"},
        headers={"X-Test": "value"},
        timeout=10.0,
    )


def test_rate_limiter_is_called_before_request():
    session = Mock()
    session.get.return_value = make_response(200)

    rate_limiter = Mock()

    client = create_client(
        rate_limiter=rate_limiter,
        session=session,
    )

    client.get("https://example.com")

    rate_limiter.acquire.assert_called_once()

    assert rate_limiter.acquire.call_count == 1
    assert session.get.call_count == 1


@patch("app.core.http_client.RetryPolicy")
def test_custom_retry_policy_is_used(mock_retry_policy_cls):
    session = Mock()
    session.get.return_value = make_response(200)

    retry_policy = Mock()

    retry_policy.execute.side_effect = (
        lambda operation: operation()
    )

    client = HTTPClient(
        rate_limiter=RateLimiter(
            max_requests=10,
            window_seconds=1,
        ),
        retry_policy=retry_policy,
        session=session,
    )

    response = client.get("https://example.com")

    assert response.status_code == 200
    retry_policy.execute.assert_called_once()



def test_timeout_is_passed_to_request():
    session = Mock()
    session.get.return_value = make_response(200)

    client = HTTPClient(
        rate_limiter=RateLimiter(
            max_requests=10,
            window_seconds=1,
        ),
        timeout=5.5,
        session=session,
    )

    client.get("https://example.com")

    session.get.assert_called_once_with(
        "https://example.com",
        params=None,
        headers=None,
        timeout=5.5,
    )


def test_invalid_timeout():
    with pytest.raises(ValueError):
        HTTPClient(
            rate_limiter=RateLimiter(
                max_requests=10,
                window_seconds=1,
            ),
            timeout=0,
        )


def test_negative_timeout():
    with pytest.raises(ValueError):
        HTTPClient(
            rate_limiter=RateLimiter(
                max_requests=10,
                window_seconds=1,
            ),
            timeout=-1,
        )


def test_timeout_exception_is_retried():
    session = Mock()

    session.get.side_effect = [
        requests.Timeout(),
        make_response(200),
    ]

    retry_policy = RetryPolicy(
        max_attempts=2,
        backoff_factor=0,
    )

    rate_limiter = Mock()

    client = HTTPClient(
        rate_limiter=rate_limiter,
        retry_policy=retry_policy,
        session=session,
    )

    response = client.get("https://example.com")

    assert response.status_code == 200
    assert session.get.call_count == 2
    assert rate_limiter.acquire.call_count == 2


def test_connection_error_is_retried():
    session = Mock()

    session.get.side_effect = [
        requests.ConnectionError(),
        make_response(200),
    ]

    retry_policy = RetryPolicy(
        max_attempts=2,
        backoff_factor=0,
    )

    rate_limiter = Mock()

    client = HTTPClient(
        rate_limiter=rate_limiter,
        retry_policy=retry_policy,
        session=session,
    )

    response = client.get("https://example.com")

    assert response.status_code == 200
    assert session.get.call_count == 2
    assert rate_limiter.acquire.call_count == 2


def test_http_500_is_retried():
    session = Mock()

    session.get.side_effect = [
        make_response(500),
        make_response(200),
    ]

    retry_policy = RetryPolicy(
        max_attempts=2,
        backoff_factor=0,
    )

    rate_limiter = Mock()

    client = HTTPClient(
        rate_limiter=rate_limiter,
        retry_policy=retry_policy,
        session=session,
    )

    response = client.get("https://example.com")

    assert response.status_code == 200
    assert session.get.call_count == 2
    assert rate_limiter.acquire.call_count == 2


def test_http_400_is_not_retried():
    session = Mock()

    session.get.return_value = make_response(400)

    retry_policy = RetryPolicy(
        max_attempts=3,
        backoff_factor=0,
    )

    rate_limiter = Mock()

    client = HTTPClient(
        rate_limiter=rate_limiter,
        retry_policy=retry_policy,
        session=session,
    )

    with pytest.raises(requests.HTTPError):
        client.get("https://example.com")

    assert session.get.call_count == 1
    assert rate_limiter.acquire.call_count == 1


def test_http_429_is_retried():
    rate_limited = make_response(429)
    rate_limited.headers["Retry-After"] = "0"

    session = Mock()

    session.get.side_effect = [
        rate_limited,
        make_response(200),
    ]

    retry_policy = RetryPolicy(
        max_attempts=2,
        backoff_factor=0,
    )

    rate_limiter = Mock()

    client = HTTPClient(
        rate_limiter=rate_limiter,
        retry_policy=retry_policy,
        session=session,
    )

    response = client.get("https://example.com")

    assert response.status_code == 200
    assert session.get.call_count == 2
    assert rate_limiter.acquire.call_count == 2


def test_context_manager_closes_session():
    session = Mock()

    client = create_client(session=session)

    client.close()

    session.close.assert_called_once()


def test_context_manager():
    session = Mock()

    with create_client(session=session):
        pass

    session.close.assert_called_once()