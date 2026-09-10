"""Polls PriceSources, finds opportunities, and tracks the running edge
statistics (see arbitrage.stats for the Law-of-Large-Numbers rationale).

This module only finds and logs opportunities. It never places a trade or
a bet — that's a deliberate boundary, not a missing feature: execution
needs your own authenticated, ToS-compliant client per source.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from arbitrage.core import Opportunity, find_opportunities
from arbitrage.sources.base import PriceSource
from arbitrage.stats import RunningStats

logger = logging.getLogger("arbitrage.scanner")


@dataclass
class ScannerConfig:
    poll_interval_s: float = 5.0
    min_net_edge_pct: float = 0.1  # ignore opportunities smaller than this
    max_iterations: int | None = None  # None = run until interrupted
    report_every: int = 20  # log LLN stats every N opportunities found


@dataclass
class Scanner:
    sources: list[PriceSource]
    config: ScannerConfig = field(default_factory=ScannerConfig)
    stats: RunningStats = field(default_factory=RunningStats)
    opportunities_log: list[Opportunity] = field(default_factory=list)

    def poll_once(self) -> list[Opportunity]:
        quotes = []
        for source in self.sources:
            try:
                quotes.extend(source.fetch_quotes())
            except Exception:
                logger.exception("source %s failed to fetch quotes", source.name)

        opps = find_opportunities(quotes, min_net_edge_pct=self.config.min_net_edge_pct)
        for opp in opps:
            self.stats.update(opp.net_edge_pct)
            self.opportunities_log.append(opp)
            logger.info(
                "opportunity: %s buy@%s(%.6g) sell@%s(%.6g) net_edge=%.3f%%",
                opp.instrument, opp.buy_source, opp.buy_price,
                opp.sell_source, opp.sell_price, opp.net_edge_pct,
            )
            if self.config.report_every and self.stats.n % self.config.report_every == 0:
                self._report()
        return opps

    def _report(self) -> None:
        lo, hi = self.stats.confidence_interval()
        logger.info(
            "LLN stats: n=%d mean_edge=%.4f%% 95%%CI=(%.4f%%, %.4f%%) "
            "expected_total=%.2f%% significant=%s",
            self.stats.n, self.stats.mean, lo, hi,
            self.stats.expected_total_return_pct(),
            self.stats.is_significantly_positive(),
        )

    def run(self) -> None:
        iteration = 0
        while self.config.max_iterations is None or iteration < self.config.max_iterations:
            self.poll_once()
            iteration += 1
            time.sleep(self.config.poll_interval_s)
