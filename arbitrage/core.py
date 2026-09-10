"""Core data model: a Quote from one source, and an Opportunity between two."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Quote:
    """A single price observation for one instrument at one source.

    bid/ask: what you could sell/buy at right now. For instruments that
    only have a single price (an odds price, a listed product price),
    set both to the same value.
    fee_rate: taker/transaction fee as a fraction of notional (0.001 = 0.1%).
    """
    source: str
    instrument: str
    bid: float
    ask: float
    timestamp: datetime
    fee_rate: float = 0.0


@dataclass(frozen=True)
class Opportunity:
    """Buy `instrument` at `buy_source`, sell it at `sell_source`."""
    instrument: str
    buy_source: str
    sell_source: str
    buy_price: float
    sell_price: float
    buy_fee_rate: float
    sell_fee_rate: float
    timestamp: datetime

    @property
    def gross_spread_pct(self) -> float:
        return (self.sell_price - self.buy_price) / self.buy_price * 100

    @property
    def net_edge_pct(self) -> float:
        """Expected return per unit of capital after both sides' fees."""
        cost = self.buy_price * (1 + self.buy_fee_rate)
        proceeds = self.sell_price * (1 - self.sell_fee_rate)
        return (proceeds - cost) / cost * 100

    def is_profitable(self, min_net_edge_pct: float = 0.0) -> bool:
        return self.net_edge_pct > min_net_edge_pct


def find_opportunities(quotes: list[Quote], min_net_edge_pct: float = 0.0) -> list[Opportunity]:
    """Compare every pair of sources quoting the same instrument and return
    every direction that clears `min_net_edge_pct` after fees."""
    by_instrument: dict[str, list[Quote]] = {}
    for q in quotes:
        by_instrument.setdefault(q.instrument, []).append(q)

    opportunities: list[Opportunity] = []
    for instrument, qs in by_instrument.items():
        for buy_q in qs:
            for sell_q in qs:
                if buy_q.source == sell_q.source:
                    continue
                opp = Opportunity(
                    instrument=instrument,
                    buy_source=buy_q.source,
                    sell_source=sell_q.source,
                    buy_price=buy_q.ask,
                    sell_price=sell_q.bid,
                    buy_fee_rate=buy_q.fee_rate,
                    sell_fee_rate=sell_q.fee_rate,
                    timestamp=max(buy_q.timestamp, sell_q.timestamp),
                )
                if opp.is_profitable(min_net_edge_pct):
                    opportunities.append(opp)
    return opportunities
