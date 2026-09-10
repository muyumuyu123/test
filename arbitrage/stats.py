"""Law-of-Large-Numbers bookkeeping for a stream of opportunity edges.

The point of this module: a single arbitrage opportunity's net edge is a
noisy random variable (stale quotes, slippage, latency all eat into it,
and sometimes it's flat-out negative once reality catches up with the
snapshot). Nobody should bet the farm on one of them. But if you size
each trade so no single loss is fatal, and repeat the process many times
across many instruments/sources, two classical results kick in:

- Law of Large Numbers: the sample mean of realized edges converges to
  the true expected edge as n grows, regardless of how noisy any single
  observation is.
- Central Limit Theorem: the *uncertainty* around that sample mean
  shrinks proportionally to 1/sqrt(n), so a confidence interval you can
  actually act on emerges after enough repetitions.

Together: a small, even barely-detectable per-trade edge becomes an
almost-certain aggregate profit once n is large enough — provided the
edge is real (not an artifact of stale data) and trades are close to
independent. This module tracks the running mean/variance so you can see
when that confidence interval has clearly separated from zero.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class RunningStats:
    """Welford's online algorithm for mean/variance of a value stream."""
    n: int = 0
    mean: float = 0.0
    _m2: float = 0.0

    def update(self, x: float) -> None:
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        delta2 = x - self.mean
        self._m2 += delta * delta2

    @property
    def variance(self) -> float:
        return self._m2 / (self.n - 1) if self.n > 1 else 0.0

    @property
    def stderr(self) -> float:
        return math.sqrt(self.variance / self.n) if self.n > 0 else float("inf")

    def confidence_interval(self, z: float = 1.96) -> tuple[float, float]:
        """Approximate confidence interval for the true mean edge (default ~95%)."""
        margin = z * self.stderr
        return (self.mean - margin, self.mean + margin)

    def expected_total_return_pct(self) -> float:
        """Sum of per-trade edges ~= n * mean, by linearity of expectation."""
        return self.n * self.mean

    def is_significantly_positive(self, z: float = 1.96) -> bool:
        """True once the lower confidence bound has cleared zero.

        This is the practical payoff of the Law of Large Numbers here:
        even a tiny, hard-to-trust-by-eye per-trade edge becomes a
        statistically solid aggregate edge once enough independent
        observations have come in.
        """
        if self.n <= 1:
            return False
        lo, _ = self.confidence_interval(z)
        return lo > 0
