import json
import logging
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.app import app
from app.core.logging import JsonFormatter

client = TestClient(app)


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    # Check that prometheus format text is returned
    assert "api_requests_total" in response.text
    assert "api_request_latency_seconds" in response.text


@patch("redis.Redis.ping")
def test_readiness_probe_ok(mock_ping):
    mock_ping.return_value = True
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["dependencies"]["database"] == "ok"
    assert data["dependencies"]["redis"] == "ok"


@patch("redis.Redis.ping")
def test_readiness_probe_redis_fail(mock_ping):
    mock_ping.side_effect = Exception("Connection refused")
    response = client.get("/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["dependencies"]["redis"] == "down"
    assert data["dependencies"]["database"] == "ok"


def test_liveness_probe():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_json_formatter_filters_secrets():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="Test message", args=(), exc_info=None
    )
    record.token = "super_secret"
    record.api_key = "12345"
    record.public_data = "hello"
    
    formatted = formatter.format(record)
    data = json.loads(formatted)
    
    assert data["message"] == "Test message"
    assert data["public_data"] == "hello"
    assert data["token"] == "***REDACTED***"
    assert data["api_key"] == "***REDACTED***"
