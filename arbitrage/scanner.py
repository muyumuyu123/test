"""Polls PriceSources, finds opportunities, and scores them through a paper
book so the reported statistics reflect realized returns.

`stats` is fed only settled paper trades — an opportunity repriced at the
quotes prevailing a few polls after it was spotted. `detected_stats` keeps
the raw displayed spread for comparison; the gap between the two is the
slippage that detected-edge accounting mistakes for profit. See
arbitrage.paper for why, and simulate.py for the run that demonstrates it.

This module never places a trade or a bet — execution needs your own
authenticated, ToS-compliant client per source.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from arbitrage.core import Opportunity, Quote, find_opportunities
from arbitrage.paper import PaperBook, SettledTrade
from arbitrage.sources.base import PriceSource
from arbitrage.stats import RunningStats

logger = logging.getLogger("arbitrage.scanner")


@dataclass
class ScannerConfig:
    poll_interval_s: float = 5.0
    min_net_edge_pct: float = 0.1  # ignore opportunities smaller than this
    max_iterations: int | None = None  # None = run until interrupted
    report_every: int = 20  # log stats every N settled trades
    settle_after_polls: int = 3  # how long a paper trade waits before scoring
    cooldown_polls: int = 60  # per-route suppression, for sample independence


@dataclass
class Scanner:
    sources: list[PriceSource]
    config: ScannerConfig = field(default_factory=ScannerConfig)
    stats: RunningStats = field(default_factory=RunningStats)  # realized
    detected_stats: RunningStats = field(default_factory=RunningStats)
    opportunities_log: list[Opportunity] = field(default_factory=list)
    settled_log: list[SettledTrade] = field(default_factory=list)
    poll_count: int = 0
    book: PaperBook = field(init=False)

    def __post_init__(self) -> None:
        self.book = PaperBook(
            settle_after=self.config.settle_after_polls,
            cooldown_polls=self.config.cooldown_polls,
        )

    def _fetch_all(self) -> list[Quote]:
        quotes: list[Quote] = []
        for source in self.sources:
            try:
                quotes.extend(source.fetch_quotes())
            except Exception:
                logger.exception("source %s failed to fetch quotes", source.name)
        return quotes

    def poll_once(self) -> list[Opportunity]:
        self.poll_count += 1
        quotes = self._fetch_all()

        for settled in self.book.settle(quotes, self.poll_count):
            self.stats.update(settled.realized_edge_pct)
            self.settled_log.append(settled)
            logger.info(
                "settled: %s %s->%s detected=%+.3f%% realized=%+.3f%% slippage=%+.3f%%",
                settled.filled.instrument,
                settled.filled.buy_source,
                settled.filled.sell_source,
                settled.trade.detected_edge_pct,
                settled.realized_edge_pct,
                settled.slippage_pct,
            )
            if self.config.report_every and self.stats.n % self.config.report_every == 0:
                self._report()

        opps = find_opportunities(quotes, min_net_edge_pct=self.config.min_net_edge_pct)
        for opp in opps:
            self.detected_stats.update(opp.net_edge_pct)
            self.opportunities_log.append(opp)
            if self.book.record(opp, self.poll_count) is not None:
                logger.info(
                    "opened: %s buy@%s(%.6g) sell@%s(%.6g) detected=%+.3f%%",
                    opp.instrument, opp.buy_source, opp.buy_price,
                    opp.sell_source, opp.sell_price, opp.net_edge_pct,
                )
        return opps

    def _report(self) -> None:
        lo, hi = self.stats.confidence_interval()
        logger.info(
            "realized: n=%d mean=%+.4f%% 95%%CI=(%+.4f%%, %+.4f%%) total=%+.2f%% significant=%s",
            self.stats.n, self.stats.mean, lo, hi,
            self.stats.expected_total_return_pct(),
            self.stats.is_significantly_positive(),
        )
        if self.detected_stats.n:
            logger.info(
                "detected: n=%d mean=%+.4f%% (overstates realized by %+.4f%%/trade) "
                "| open=%d suppressed=%d unpriced=%d",
                self.detected_stats.n, self.detected_stats.mean,
                self.detected_stats.mean - self.stats.mean,
                self.book.open_count, self.book.suppressed, self.book.unpriced,
            )

    def run(self) -> None:
        iteration = 0
        while self.config.max_iterations is None or iteration < self.config.max_iterations:
            self.poll_once()
            iteration += 1
            time.sleep(self.config.poll_interval_s)
