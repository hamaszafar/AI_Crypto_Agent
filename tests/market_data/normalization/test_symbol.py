import pytest
from app.market_data.exceptions import InvalidSymbolError
from app.market_data.normalization.symbol import normalize_symbol


def test_normalize_symbol_valid():
    assert normalize_symbol("BTCUSDT") == "BTC/USDT"
    assert normalize_symbol("BTC-USDT") == "BTC/USDT"
    assert normalize_symbol("BTC_USDT") == "BTC/USDT"
    assert normalize_symbol("btc/usdt") == "BTC/USDT"
    assert normalize_symbol(" BTC/USDT ") == "BTC/USDT"
    assert normalize_symbol("BTC-USD") == "BTC/USD"
    assert normalize_symbol("XBT/USD") == "BTC/USD"
    assert normalize_symbol("ETHUSDT") == "ETH/USDT"


def test_normalize_symbol_invalid():
    with pytest.raises(InvalidSymbolError):
        normalize_symbol("")

    with pytest.raises(InvalidSymbolError):
        normalize_symbol("   ")

    with pytest.raises(InvalidSymbolError):
        normalize_symbol("INVALID_FORMAT_PARTS_3_X_Y")

    with pytest.raises(InvalidSymbolError):
        normalize_symbol(12345)

    with pytest.raises(InvalidSymbolError):
        normalize_symbol(None)
