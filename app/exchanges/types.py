from enum import Enum 

class Timeframe(str, Enum):
    FIFTEEN_MINUTES = "15m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"

class Symbol(str, Enum):
    BTC_USDT = "BTC/USDT"
    ETH_USDT = "ETH/USDT"
    XRP_USDT = "XRP/USDT"
    LTC_USDT = "LTC/USDT"
    SOL_USDT = "SOL/USDT"