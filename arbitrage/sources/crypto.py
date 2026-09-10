"""Crypto exchange price source, built on ccxt's public order-book endpoints.

Only reads public market data — no API key or authentication needed to
*detect* opportunities. Placing orders is out of scope here; wire your own
authenticated ccxt client with your own keys, under each exchange's ToS
and rate limits, if you want to execute rather than just detect.
"""
from __future__ import annotations

from datetime import datetime, timezone

from arbitrage.core import Quote
from arbitrage.sources.base import PriceSource

try:
    import ccxt
except ImportError:  # pragma: no cover - optional dependency
    ccxt = None


class CcxtSource(PriceSource):
    """Wraps one ccxt exchange and polls the top of book for a fixed list
    of symbols (e.g. "BTC/USDT")."""

    def __init__(self, exchange_id: str, symbols: list[str], fee_rate: float | None = None):
        if ccxt is None:
            raise RuntimeError("pip install ccxt to use CcxtSource")
        if not hasattr(ccxt, exchange_id):
            raise ValueError(f"unknown ccxt exchange id: {exchange_id!r}")

        self.exchange_id = exchange_id
        self.symbols = symbols
        self.name = exchange_id
        self.exchange = getattr(ccxt, exchange_id)({"enableRateLimit": True})

        if fee_rate is not None:
            self.fee_rate = fee_rate
        else:
            try:
                self.fee_rate = self.exchange.fees.get("trading", {}).get("taker", 0.001)
            except Exception:
                self.fee_rate = 0.001

    def fetch_quotes(self) -> list[Quote]:
        quotes: list[Quote] = []
        now = datetime.now(timezone.utc)
        for symbol in self.symbols:
            try:
                order_book = self.exchange.fetch_order_book(symbol, limit=5)
                bids, asks = order_book.get("bids"), order_book.get("asks")
                if not bids or not asks:
                    continue
                quotes.append(Quote(
                    source=self.name,
                    instrument=symbol,
                    bid=bids[0][0],
                    ask=asks[0][0],
                    timestamp=now,
                    fee_rate=self.fee_rate,
                ))
            except Exception:
                # one symbol failing shouldn't kill the whole source
                continue
        return quotes
