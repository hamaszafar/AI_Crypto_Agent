import time

import pytest

from app.core.rate_limiter import RateLimiter


def test_invalid_max_requests():
    with pytest.raises(ValueError):
        RateLimiter(
            max_requests=0,
            window_seconds=1,
        )


def test_invalid_window():
    with pytest.raises(ValueError):
        RateLimiter(
            max_requests=1,
            window_seconds=0,
        )


def test_first_request_is_immediate(monkeypatch):
    limiter = RateLimiter(
        max_requests=1,
        window_seconds=1,
    )

    sleep_calls = []

    monkeypatch.setattr(
        time,
        "sleep",
        lambda seconds: sleep_calls.append(seconds),
    )

    limiter.acquire()

    assert sleep_calls == []
    assert limiter.current_requests == 1


def test_requests_are_tracked():
    limiter = RateLimiter(
        max_requests=3,
        window_seconds=10,
    )

    limiter.acquire()
    limiter.acquire()

    assert limiter.current_requests == 2


def test_limit_waits_for_window(monkeypatch):
    limiter = RateLimiter(
        max_requests=1,
        window_seconds=1,
    )

    fake_time = [100.0]

    def fake_monotonic():
        return fake_time[0]

    monkeypatch.setattr(
        time,
        "monotonic",
        fake_monotonic,
    )

    sleep_calls = []

    def fake_sleep(seconds):
        sleep_calls.append(seconds)
        fake_time[0] += seconds

    monkeypatch.setattr(
        time,
        "sleep",
        fake_sleep,
    )

    limiter.acquire()

    assert limiter.current_requests == 1

    limiter.acquire()

    assert len(sleep_calls) == 1
    assert sleep_calls[0] == pytest.approx(1.0)

    assert limiter.current_requests == 1


def test_expired_requests_are_removed(monkeypatch):
    limiter = RateLimiter(
        max_requests=2,
        window_seconds=10,
    )

    fake_time = [100.0]

    monkeypatch.setattr(
        time,
        "monotonic",
        lambda: fake_time[0],
    )

    limiter.acquire()
    limiter.acquire()

    assert limiter.current_requests == 2

    fake_time[0] = 111.0

    assert limiter.current_requests == 0


def test_reset():
    limiter = RateLimiter(
        max_requests=5,
        window_seconds=10,
    )

    limiter.acquire()
    limiter.acquire()

    assert limiter.current_requests == 2

    limiter.reset()

    assert limiter.current_requests == 0


def test_multiple_requests_within_limit():
    limiter = RateLimiter(
        max_requests=5,
        window_seconds=10,
    )

    for _ in range(5):
        limiter.acquire()

    assert limiter.current_requests == 5