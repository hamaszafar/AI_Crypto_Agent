from app.exchanges.binance_exchange import BinanceExchange
from app.exchanges.bitget_exchange import BitgetExchange
from app.exchanges.bybit_exchange import BybitExchange
from app.exchanges.coinbase_exchange import CoinbaseExchange
from app.exchanges.kraken_exchange import KrakenExchange
from app.exchanges.mock_exchange import MockExchange
from app.exchanges.okx_exchange import OKXExchange

from app.exchanges.factory import ExchangeFactory


ExchangeFactory.register("mock", MockExchange)
ExchangeFactory.register("binance", BinanceExchange)
ExchangeFactory.register("bybit", BybitExchange)
ExchangeFactory.register("bitget", BitgetExchange)
ExchangeFactory.register("okx", OKXExchange)
ExchangeFactory.register("kraken", KrakenExchange)
ExchangeFactory.register("coinbase", CoinbaseExchange)