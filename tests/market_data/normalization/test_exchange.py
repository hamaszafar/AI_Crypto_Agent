import pytest
from app.market_data.exceptions import InvalidExchangeError
from app.market_data.normalization.exchange import normalize_exchange_name


def test_normalize_exchange_name_valid():
    assert normalize_exchange_name("BINANCE") == "binance"
    assert normalize_exchange_name("Binance") == "binance"
    assert normalize_exchange_name("binance") == "binance"
    assert normalize_exchange_name(" Binance ") == "binance"
    assert normalize_exchange_name("BYBIT") == "bybit"
    assert normalize_exchange_name("OKX") == "okx"


def test_normalize_exchange_name_invalid():
    with pytest.raises(InvalidExchangeError):
        normalize_exchange_name("")

    with pytest.raises(InvalidExchangeError):
        normalize_exchange_name("   ")

    with pytest.raises(InvalidExchangeError):
        normalize_exchange_name(123)

    with pytest.raises(InvalidExchangeError):
        normalize_exchange_name(None)
