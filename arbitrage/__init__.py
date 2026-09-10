"""Cross-source price arbitrage scanner.

Finds price differences for the same instrument across multiple sources
(crypto exchanges, sportsbook odds, e-commerce listings) and tracks the
statistics of the edge those differences imply, using the Law of Large
Numbers: a single opportunity's net edge is small and noisy, but the
running average over many independent opportunities converges to the
true expected edge, and the total expected P&L (n * mean) becomes
predictable with a shrinking confidence interval as n grows.

This package only *detects* opportunities from public market data. It
does not place trades or bets — wire your own authenticated execution
against each source's API under its own ToS if you want that.
"""
