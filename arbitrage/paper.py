"""Paper-trading layer: score opportunities by what they would actually have
returned, not by the spread that was displayed when they were spotted.

The scanner used to feed RunningStats the *detected* edge of every
opportunity clearing the threshold. simulate.py shows why that is
unusable: on a market with no real edge it still reports a significant
profit, because thresholding a noisy spread samples only the right tail of
the noise.

A PaperBook fixes the measurement in two ways:

- An opportunity is recorded, not scored. It is scored `settle_after` polls
  later against the prices prevailing *then* — which is what a real order
  would fill at, having been decided on data that was already stale by the
  time it was acted on. The gap between the two is the slippage that
  detected-edge accounting silently books as profit.
- A route (instrument + buy venue + sell venue) that just produced a trade
  is suppressed for `cooldown_polls`. A spread that persists for an hour is
  one observation, not one per poll, and feeding it repeatedly to
  RunningStats collapses the confidence interval around what is really a
  single data point.

Nothing here places an order. It estimates fills from quotes the scanner
already polls.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from arbitrage.core import Opportunity, Quote

RouteKey = tuple[str, str, str]


def route_of(opp: Opportunity) -> RouteKey:
    return (opp.instrument, opp.buy_source, opp.sell_source)


@dataclass(frozen=True)
class PaperTrade:
    """An opportunity recorded at detection time, awaiting settlement."""
    opportunity: Opportunity
    opened_at_poll: int

    @property
    def detected_edge_pct(self) -> float:
        return self.opportunity.net_edge_pct


@dataclass(frozen=True)
class SettledTrade:
    """A paper trade scored against the prices that prevailed at settlement."""
    trade: PaperTrade
    settled_at_poll: int
    filled: Opportunity  # same route, repriced at settlement

    @property
    def realized_edge_pct(self) -> float:
        return self.filled.net_edge_pct

    @property
    def slippage_pct(self) -> float:
        """Detected edge minus realized edge: what the stale quote overstated."""
        return self.trade.detected_edge_pct - self.realized_edge_pct


@dataclass
class PaperBook:
    """Holds open paper trades and settles them against later quotes."""

    settle_after: int = 3      # polls to wait before scoring a trade
    cooldown_polls: int = 60   # per-route suppression, for sample independence
    unpriced: int = 0          # trades dropped because settle quotes were missing
    suppressed: int = 0        # opportunities skipped by cooldown

    _open: list[PaperTrade] = field(default_factory=list)
    _last_opened: dict[RouteKey, int] = field(default_factory=dict)

    @property
    def open_count(self) -> int:
        return len(self._open)

    def record(self, opp: Opportunity, poll: int) -> PaperTrade | None:
        """Open a paper trade, unless this route is still in cooldown."""
        key = route_of(opp)
        last = self._last_opened.get(key)
        if last is not None and poll - last < self.cooldown_polls:
            self.suppressed += 1
            return None

        trade = PaperTrade(opportunity=opp, opened_at_poll=poll)
        self._open.append(trade)
        self._last_opened[key] = poll
        return trade

    def settle(self, quotes: list[Quote], poll: int) -> list[SettledTrade]:
        """Score every open trade whose settle deadline has passed.

        A trade whose venues are not both quoting at settlement cannot be
        priced, so it is dropped and counted in `unpriced` rather than
        scored on a guess.
        """
        book = {(q.source, q.instrument): q for q in quotes}
        settled: list[SettledTrade] = []
        still_open: list[PaperTrade] = []

        for trade in self._open:
            if poll - trade.opened_at_poll < self.settle_after:
                still_open.append(trade)
                continue

            opp = trade.opportunity
            buy_q = book.get((opp.buy_source, opp.instrument))
            sell_q = book.get((opp.sell_source, opp.instrument))
            if buy_q is None or sell_q is None:
                self.unpriced += 1
                continue

            filled = replace(
                opp,
                buy_price=buy_q.ask,
                sell_price=sell_q.bid,
                timestamp=max(buy_q.timestamp, sell_q.timestamp),
            )
            settled.append(SettledTrade(trade=trade, settled_at_poll=poll, filled=filled))

        self._open = still_open
        return settled
