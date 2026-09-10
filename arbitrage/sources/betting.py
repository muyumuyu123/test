"""Sportsbook odds source via The Odds API (https://the-odds-api.com), plus
surebet stake sizing.

Needs a free API key from the-odds-api.com. This computes classic
"arbitrage betting" / surebets: shopping the same event's outcomes across
different bookmakers for the best price on each, then sizing stakes so the
payout is equal (and positive) no matter which outcome happens. This is
legal in most jurisdictions — you're just price-shopping — but many
bookmakers limit or close accounts that do it repeatedly, and odds can move
between the quote and the bet being placed. Treat both as real costs, not
bugs in this code. This module only detects and sizes; it does not place
bets.
"""
from __future__ import annotations

from datetime import datetime, timezone

import requests

from arbitrage.core import Quote
from arbitrage.sources.base import PriceSource

ODDS_API_BASE = "https://api.the-odds-api.com/v4"


class OddsApiSource(PriceSource):
    """One Quote per (event, outcome, bookmaker). bid == ask == decimal odds;
    fee_rate is 0 because the bookmaker's margin is already baked into the
    odds rather than charged as a separate fee."""

    def __init__(self, api_key: str, sport: str, regions: str = "eu,us", markets: str = "h2h"):
        self.api_key = api_key
        self.sport = sport
        self.regions = regions
        self.markets = markets
        self.name = "the-odds-api"

    def fetch_quotes(self) -> list[Quote]:
        resp = requests.get(
            f"{ODDS_API_BASE}/sports/{self.sport}/odds",
            params={"apiKey": self.api_key, "regions": self.regions, "markets": self.markets},
            timeout=10,
        )
        resp.raise_for_status()
        now = datetime.now(timezone.utc)
        quotes: list[Quote] = []
        for event in resp.json():
            for bookmaker in event.get("bookmakers", []):
                for market in bookmaker.get("markets", []):
                    if market.get("key") != "h2h":
                        continue
                    for outcome in market.get("outcomes", []):
                        instrument = f"{event['id']}:{outcome['name']}"
                        quotes.append(Quote(
                            source=bookmaker["key"],
                            instrument=instrument,
                            bid=outcome["price"],
                            ask=outcome["price"],
                            timestamp=now,
                        ))
        return quotes


def best_odds_per_outcome(quotes: list[Quote], event_id: str) -> dict[str, tuple[float, str]]:
    """From raw Quotes for one event, return {outcome_name: (best_price, bookmaker)}."""
    best: dict[str, tuple[float, str]] = {}
    prefix = f"{event_id}:"
    for q in quotes:
        if not q.instrument.startswith(prefix):
            continue
        outcome = q.instrument[len(prefix):]
        if outcome not in best or q.bid > best[outcome][0]:
            best[outcome] = (q.bid, q.source)
    return best


def surebet_margin(best_odds: dict[str, float]) -> float:
    """sum(1/odds) across outcomes. < 1 means an arbitrage exists; the
    smaller it is, the bigger the guaranteed edge."""
    return sum(1 / o for o in best_odds.values())


def surebet_stakes(best_odds: dict[str, float], total_stake: float) -> dict[str, float]:
    """Stake per outcome that locks in equal profit regardless of which
    outcome happens, IF surebet_margin(best_odds) < 1."""
    inv_sum = surebet_margin(best_odds)
    if inv_sum >= 1:
        raise ValueError("no arbitrage: implied probabilities sum to >= 1")
    return {name: total_stake * (1 / o) / inv_sum for name, o in best_odds.items()}
