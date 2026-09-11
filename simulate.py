"""Monte Carlo check on whether the scanner's statistics can be trusted.

Drives the real Scanner / PaperBook / RunningStats against a synthetic
two-venue market whose true edge we control, then compares four ways of
measuring the same run:

  1. detected   - RunningStats fed the *displayed* spread of every
                  opportunity clearing the threshold (what the scanner did
                  before the paper book existed). Reports significant
                  profit in every scenario, including the one with no real
                  edge, because thresholding a noisy spread samples only
                  the right tail of the noise.
  2. all-pairs  - every evaluated pair, scored on the displayed spread.
                  Removes the selection bias but is not a usable fix: it
                  averages each pair's profitable direction with its
                  unprofitable mirror, so it sits near minus the
                  round-trip cost regardless of the true edge and rejects
                  real ones (scenario C).
  3. oracle     - ground truth, using the market's hidden fair value and
                  CAPTURE. Not computable outside a simulation; included
                  as the answer the other columns are trying to reach.
  4. paper book - what the shipped Scanner now reports: opportunities
                  repriced at the quotes prevailing `settle_after_polls`
                  later, one sample per route per `cooldown_polls`.

Columns 3 and 4 should agree in sign on all three scenarios. Column 4 is
the one the real code can compute without an oracle.

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

FEE = 0.001           # 0.1% taker fee per side
HALF_SPREAD = 0.0005  # 5bp half-spread -> 10bp to cross twice
NOISE = 0.0015        # 15bp transient per-venue quote noise (staleness/latency)
CAPTURE = 0.30        # fraction of an apparent dislocation that is really
                      # executable; the rest reverts before you fill
MIN_EDGE_PCT = 0.1    # scanner threshold, matches config.example.yaml
SETTLE_AFTER = 3      # polls a paper trade waits before being scored
COOLDOWN = 30         # polls a route is suppressed after producing a trade
POLLS = 20_000


class Market:
    """Two venues quoting one instrument off a common true mid.

    `bias` is a persistent, genuinely tradeable offset per venue. `noise` is
    transient quote noise carrying no edge — the thing a naive scanner
    mistakes for opportunity.
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

    def oracle_edge_pct(self, opp: Opportunity) -> float:
        """What the trade really returns once the noise reverts."""
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


def run_scenario(name: str, market: Market, polls: int = POLLS) -> None:
    sources = [MarketSource(market, v) for v in VENUES]
    scanner = Scanner(
        sources=sources,
        config=ScannerConfig(
            min_net_edge_pct=MIN_EDGE_PCT,
            report_every=0,
            settle_after_polls=SETTLE_AFTER,
            cooldown_polls=COOLDOWN,
        ),
    )

    all_pairs = RunningStats()
    oracle = RunningStats()
    evaluated = 0

    for _ in range(polls):
        market.step()

        # columns 2 and 3 are measured off the same market state the scanner sees
        quotes: list[Quote] = []
        for source in sources:
            quotes.extend(source.fetch_quotes())
        for opp in find_opportunities(quotes, min_net_edge_pct=float("-inf")):
            all_pairs.update(opp.net_edge_pct)
            evaluated += 1
        for opp in find_opportunities(quotes, min_net_edge_pct=MIN_EDGE_PCT):
            oracle.update(market.oracle_edge_pct(opp))

        scanner.poll_once()

    print(f"\n{'=' * 76}\n{name}\n{'=' * 76}")
    print(f"polls={polls:,}  pairs evaluated={evaluated:,}  "
          f"flagged={scanner.detected_stats.n:,}  "
          f"paper trades settled={scanner.stats.n:,} "
          f"(suppressed by cooldown={scanner.book.suppressed:,})")

    for label, stats in (
        ("1. detected   (filtered, displayed)", scanner.detected_stats),
        ("2. all-pairs  (unfiltered, displayed)", all_pairs),
        ("3. oracle     (hidden ground truth)", oracle),
        ("4. paper book (SHIPPED)", scanner.stats),
    ):
        if stats.n == 0:
            print(f"  {label:39s}  no samples")
            continue
        lo, hi = stats.confidence_interval()
        verdict = "TRADE" if stats.is_significantly_positive() else "stand down"
        print(f"  {label:39s}  n={stats.n:6,}  mean={stats.mean:+7.4f}%  "
              f"95%CI=({lo:+.4f}%, {hi:+.4f}%)  -> {verdict}")

    if scanner.stats.n and scanner.detected_stats.n:
        overstatement = scanner.detected_stats.mean - scanner.stats.mean
        print(f"  displayed spread overstates realized by {overstatement:+.4f}%/trade")


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
