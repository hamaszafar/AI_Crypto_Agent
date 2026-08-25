from app.exchanges.types import Symbol, Timeframe

def test_timeframe():
    assert Timeframe.FIFTEEN_MINUTES.value == "15m"
    assert Timeframe.ONE_HOUR.value == "1h"
    assert Timeframe.FOUR_HOURS.value == "4h"
    assert Timeframe.ONE_DAY.value == "1d"

def test_symbol():
    assert Symbol.BTC_USDT.value == "BTC/USDT"
    assert Symbol.ETH_USDT.value == "ETH/USDT"
    assert Symbol.XRP_USDT.value == "XRP/USDT"
    assert Symbol.LTC_USDT.value == "LTC/USDT"
    assert Symbol.SOL_USDT.value == "SOL/USDT"