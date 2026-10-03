from unittest.mock import Mock, patch

import pytest
import requests

from app.core.retry.retry import RetryError, RetryPolicy


def make_response(status_code: int) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response.url = "https://example.com"
    return response


def test_successful_request_returns_response():
    policy = RetryPolicy()

    response = make_response(200)

    operation = Mock(return_value=response)

    result = policy.execute(operation)

    assert result is response
    assert operation.call_count == 1


@patch("app.core.retry.retry.time.sleep")
def test_timeout_is_retried(mock_sleep):
    policy = RetryPolicy(
        max_attempts=3,
        backoff_factor=1,
        jitter=False,
    )

    operation = Mock(
        side_effect=[
            requests.Timeout(),
            requests.Timeout(),
            make_response(200),
        ]
    )

    result = policy.execute(operation)

    assert result.status_code == 200
    assert operation.call_count == 3

    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(1)
    mock_sleep.assert_any_call(2)


@patch("app.core.retry.retry.time.sleep")
def test_connection_error_is_retried(mock_sleep):
    policy = RetryPolicy(
        max_attempts=3,
        backoff_factor=1,
        jitter=False,
    )

    operation = Mock(
        side_effect=[
            requests.ConnectionError(),
            make_response(200),
        ]
    )

    result = policy.execute(operation)

    assert result.status_code == 200
    assert operation.call_count == 2
    mock_sleep.assert_called_once_with(1)


@patch("app.core.retry.retry.time.sleep")
def test_http_500_is_retried(mock_sleep):
    policy = RetryPolicy(
        max_attempts=3,
        backoff_factor=1,
        jitter=False,
    )

    operation = Mock(
        side_effect=[
            make_response(500),
            make_response(200),
        ]
    )

    result = policy.execute(operation)

    assert result.status_code == 200
    assert operation.call_count == 2
    mock_sleep.assert_called_once_with(1)


@patch("app.core.retry.retry.time.sleep")
def test_http_503_is_retried(mock_sleep):
    policy = RetryPolicy(
        max_attempts=3,
        backoff_factor=1,
        jitter=False,
    )

    operation = Mock(
        side_effect=[
            make_response(503),
            make_response(200),
        ]
    )

    result = policy.execute(operation)

    assert result.status_code == 200
    assert operation.call_count == 2


@patch("app.core.retry.retry.time.sleep")
def test_http_429_respects_retry_after(mock_sleep):
    policy = RetryPolicy(
        max_attempts=3,
        backoff_factor=1,
        jitter=False,
    )

    rate_limited = make_response(429)
    rate_limited.headers["Retry-After"] = "5"

    operation = Mock(
        side_effect=[
            rate_limited,
            make_response(200),
        ]
    )

    result = policy.execute(operation)

    assert result.status_code == 200
    assert operation.call_count == 2
    mock_sleep.assert_called_once_with(5)


@patch("app.core.retry.retry.time.sleep")
def test_non_retryable_4xx_fails_immediately(mock_sleep):
    policy = RetryPolicy(
        max_attempts=3,
        backoff_factor=1,
        jitter=False,
    )

    response = make_response(400)

    operation = Mock(return_value=response)

    with pytest.raises(requests.HTTPError):
        policy.execute(operation)

    assert operation.call_count == 1
    mock_sleep.assert_not_called()


@patch("app.core.retry.retry.time.sleep")
def test_retries_stop_after_max_attempts(mock_sleep):
    policy = RetryPolicy(
        max_attempts=3,
        backoff_factor=1,
        jitter=False,
    )

    operation = Mock(
        side_effect=requests.Timeout()
    )

    with pytest.raises(RetryError):
        policy.execute(operation)

    assert operation.call_count == 3
    assert mock_sleep.call_count == 2


@patch("app.core.retry.retry.time.sleep")
def test_http_500_fails_after_max_attempts(mock_sleep):
    policy = RetryPolicy(
        max_attempts=3,
        backoff_factor=1,
        jitter=False,
    )

    operation = Mock(
        return_value=make_response(500)
    )

    with pytest.raises(requests.HTTPError):
        policy.execute(operation)

    assert operation.call_count == 3
    assert mock_sleep.call_count == 2


def test_backoff_is_exponential():
    policy = RetryPolicy(
        max_attempts=5,
        backoff_factor=1,
        jitter=False,
    )

    assert policy.get_backoff(1) == 1
    assert policy.get_backoff(2) == 2
    assert policy.get_backoff(3) == 4
    assert policy.get_backoff(4) == 8


def test_backoff_is_capped():
    policy = RetryPolicy(
        max_attempts=5,
        backoff_factor=2,
        max_backoff=5,
        jitter=False,
    )

    assert policy.get_backoff(1) == 2
    assert policy.get_backoff(2) == 4
    assert policy.get_backoff(3) == 5


def test_invalid_max_attempts():
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=0)


def test_invalid_backoff_factor():
    with pytest.raises(ValueError):
        RetryPolicy(backoff_factor=-1)