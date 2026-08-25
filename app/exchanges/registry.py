from app.exchanges.binance_exchange import BinanceExchange
from app.exchanges.factory import ExchangeFactory
from app.exchanges.mock_exchange import MockExchange


ExchangeFactory.register("mock", MockExchange)
ExchangeFactory.register("binance", BinanceExchange)