from __future__ import annotations

from abc import ABC, abstractmethod

from arbitrage.core import Quote


class PriceSource(ABC):
    """A place to get current Quote(s) for one or more instruments from."""

    name: str

    @abstractmethod
    def fetch_quotes(self) -> list[Quote]:
        """Return current Quote objects. Should raise on failure rather than
        return stale/partial data silently; the scanner logs and skips."""
