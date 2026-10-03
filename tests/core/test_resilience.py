import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.api.app import app
from app.core.exceptions import TradingSignalException, DependencyError
from app.core.retry.retry import RetryPolicy

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

def test_startup_success(client):
    response = client.get("/health")
    assert response.status_code == 200

def test_startup_failure():
    # Patch SQLiteDatabase initialization to fail
    with patch("app.signals.persistence.SQLiteDatabase") as mock_db:
        mock_db.side_effect = Exception("DB Down")
        with pytest.raises(RuntimeError) as exc_info:
            with TestClient(app):
                pass
        assert "Startup dependency failure" in str(exc_info.value)

@patch("app.api.app.logger")
def test_shutdown_error_logged(mock_logger):
    # We patch SignalRepository.close instead of _repo instance
    with patch("app.signals.persistence.SignalRepository.close") as mock_close:
        mock_close.side_effect = Exception("Close error")
        with TestClient(app):
            pass  # startup succeeds
        # on exit from context manager, shutdown happens
        mock_logger.error.assert_called_with("Error closing SignalRepository on shutdown: Close error")

def test_exception_handler_500(client):
    with patch("app.signals.persistence.SignalRepository.get_latest", side_effect=TradingSignalException("Something went wrong")):
        response = client.get("/signals/BTCUSD/1h")
        assert response.status_code == 500
        assert response.json() == {"detail": "Something went wrong"}

def test_retry_jitter():
    policy = RetryPolicy(max_attempts=3, backoff_factor=10, jitter=True)
    delay1 = policy.get_backoff(1)
    delay2 = policy.get_backoff(1)
    assert delay1 > 0
    assert delay2 > 0
    assert 5 <= delay1 <= 15
    assert 5 <= delay2 <= 15
