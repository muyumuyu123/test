"""Monte Carlo check on whether the scanner's Law-of-Large-Numbers verdict
can be trusted.

Drives the real Scanner / RunningStats / find_opportunities against a
synthetic two-venue market whose true edge we control, then compares three
ways of measuring the same run:

  1. as-wired      - RunningStats fed only opportunities that cleared the
                     threshold, scored on the *detected* spread (what
                     scanner.py does today). Reports significant profit in
                     every scenario, including the one with no real edge.
  2. all-pairs     - RunningStats fed every evaluated pair, scored on the
                     detected spread. Removes the selection bias but is not
                     a usable fix: it averages each pair's profitable
                     direction with its unprofitable mirror, so it sits at
                     roughly minus the round-trip cost regardless of the
                     true edge, and rejects real ones (scenario C).
  3. realized      - RunningStats fed the *realized* P&L of every trade the
                     scanner would have acted on. The only column that gets
                     all three scenarios right.

Run: python simulate.py
"""
from __future__ import annotations

import logging
import math
import random
from datetime import datetime, timedelta, timezone

from arbitrage.core import Opportunity, Quote, find_opportunities
from arbitrage.scanner import Scanner, ScannerConfig
from arbitrage.sources.base import PriceSource
from arbitrage.stats import RunningStats

logging.getLogger("arbitrage.scanner").setLevel(logging.WARNING)

INSTRUMENT = "BTC/USDT"
VENUES = ("venue_a", "venue_b")

FEE = 0.001          # 0.1% taker fee per side
HALF_SPREAD = 0.0005  # 5bp half-spread -> 10bp to cross twice
NOISE = 0.0015       # 15bp transient per-venue quote noise (staleness/latency)
CAPTURE = 0.30       # fraction of an apparent dislocation that is really
                     # executable; the other 70% reverts before you fill
MIN_EDGE_PCT = 0.1   # scanner threshold, matches config.example.yaml
POLLS = 20_000


class Market:
    """Two venues quoting one instrument off a common true mid.

    `bias` is a *persistent, genuinely tradeable* offset per venue.
    `noise` is transient quote noise that carries no edge — it is the thing
    a naive scanner mistakes for opportunity.
    """

    def __init__(self, seed: int, bias: tuple[float, float] = (0.0, 0.0), noise: float = NOISE):
        self.rng = random.Random(seed)
        self.mid = 50_000.0
        self.bias = bias
        self.noise = noise
        self.displayed: dict[str, float] = {}
        self.fair: dict[str, float] = {}
        self.step()

    def step(self) -> None:
        self.mid *= math.exp(self.rng.gauss(0, 0.0005))
        for venue, bias in zip(VENUES, self.bias):
            eps = self.rng.gauss(0, self.noise) if self.noise else 0.0
            self.fair[venue] = self.mid * (1 + bias)
            self.displayed[venue] = self.mid * (1 + bias + eps)

    def quotes(self, now: datetime) -> list[Quote]:
        return [
            Quote(
                source=venue,
                instrument=INSTRUMENT,
                bid=self.displayed[venue] * (1 - HALF_SPREAD),
                ask=self.displayed[venue] * (1 + HALF_SPREAD),
                timestamp=now,
                fee_rate=FEE,
            )
            for venue in VENUES
        ]

    def realized_edge_pct(self, opp: Opportunity) -> float:
        """What the trade actually returns once the noise reverts."""
        def fill_ref(venue: str) -> float:
            return self.fair[venue] + CAPTURE * (self.displayed[venue] - self.fair[venue])

        cost = fill_ref(opp.buy_source) * (1 + HALF_SPREAD) * (1 + FEE)
        proceeds = fill_ref(opp.sell_source) * (1 - HALF_SPREAD) * (1 - FEE)
        return (proceeds - cost) / cost * 100


class MarketSource(PriceSource):
    def __init__(self, market: Market, venue: str):
        self.market = market
        self.venue = venue
        self.name = venue
        self._now = datetime.now(timezone.utc)

    def fetch_quotes(self) -> list[Quote]:
        self._now += timedelta(seconds=1)
        return [q for q in self.market.quotes(self._now) if q.source == self.venue]


def all_pair_edges(quotes: list[Quote]) -> list[float]:
    """Every ordered pair's net edge, threshold or not — the unbiased sample."""
    return [
        opp.net_edge_pct
        for opp in find_opportunities(quotes, min_net_edge_pct=float("-inf"))
    ]


def run_scenario(name: str, market: Market, polls: int = POLLS) -> None:
    sources = [MarketSource(market, v) for v in VENUES]
    scanner = Scanner(
        sources=sources,
        config=ScannerConfig(min_net_edge_pct=MIN_EDGE_PCT, report_every=0),
    )

    all_pairs = RunningStats()   # every pair evaluated, detected edge
    realized = RunningStats()    # only acted-on trades, realized P&L
    evaluated = 0

    for _ in range(polls):
        market.step()
        quotes = []
        for source in sources:
            quotes.extend(source.fetch_quotes())

        for edge in all_pair_edges(quotes):
            all_pairs.update(edge)
            evaluated += 1

        for opp in find_opportunities(quotes, min_net_edge_pct=MIN_EDGE_PCT):
            scanner.stats.update(opp.net_edge_pct)  # what scanner.py does
            realized.update(market.realized_edge_pct(opp))

    print(f"\n{'=' * 72}\n{name}\n{'=' * 72}")
    print(f"polls={polls:,}  pairs evaluated={evaluated:,}  "
          f"flagged as opportunities={scanner.stats.n:,} "
          f"({scanner.stats.n / max(evaluated, 1):.1%})")

    for label, stats in (
        ("1. as-wired  (filtered, detected)", scanner.stats),
        ("2. all-pairs (unfiltered, detected)", all_pairs),
        ("3. realized  (acted-on, true P&L)", realized),
    ):
        if stats.n == 0:
            print(f"  {label:38s}  no samples")
            continue
        lo, hi = stats.confidence_interval()
        verdict = "SIGNIFICANT PROFIT" if stats.is_significantly_positive() else "not significant"
        print(f"  {label:38s}  n={stats.n:6,}  mean={stats.mean:+7.4f}%  "
              f"95%CI=({lo:+.4f}%, {hi:+.4f}%)  -> {verdict}")

    if scanner.stats.n and realized.n:
        print(f"  scanner claims total   : {scanner.stats.expected_total_return_pct():+10.1f}%")
        print(f"  reality delivers total : {realized.expected_total_return_pct():+10.1f}%")


def main() -> None:
    run_scenario(
        "A. NO real edge — both venues fairly priced, only transient quote noise",
        Market(seed=7, bias=(0.0, 0.0), noise=NOISE),
    )
    run_scenario(
        "B. Persistent 0.5% dislocation, zero noise — one condition, resampled forever",
        Market(seed=7, bias=(0.0, 0.005), noise=0.0),
        polls=2_000,
    )
    run_scenario(
        "C. Real 0.4% edge buried in the same noise as scenario A",
        Market(seed=7, bias=(0.0, 0.004), noise=NOISE),
    )


if __name__ == "__main__":
    main()
