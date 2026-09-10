# Price Arbitrage Scanner

Finds price differences for the same instrument across multiple sources
(crypto exchanges, sportsbook odds, e-commerce listings) and tracks the
statistics of the edge those differences imply.

## The idea (Law of Large Numbers)

A single opportunity's net edge (spread minus both sides' fees) is small
and noisy — quotes go stale, slippage happens, latency eats into it, and
individually it's easy to talk yourself out of. But if you size each trade
so no single loss is fatal, and repeat the process many times across many
instruments and sources:

- **Law of Large Numbers**: the running average of realized edges converges
  to the true expected edge, however noisy any one observation is.
- **Central Limit Theorem**: the uncertainty around that average shrinks
  like `1/sqrt(n)`, so a confidence interval you can act on emerges after
  enough repetitions.

`arbitrage/stats.py` implements this with Welford's online mean/variance
and reports a confidence interval and a "statistically significant" flag
once the lower bound clears zero. This only works if the edge is *real*
(not a stale-quote artifact) and opportunities are close to independent —
it can't turn a genuinely negative-EV strategy positive, it just tells you
honestly when a real small edge has accumulated enough samples to trust.

## What this does and doesn't do

This is a **scanner/detector**, not an auto-trader. It reads public market
data and logs opportunities with their net edge. It does **not** place
trades, place bets, or store credentials — wiring up execution is left to
you, using your own authenticated API client per source, under that
source's Terms of Service, rate limits, and (for betting) your
jurisdiction's laws.

## Sources

| type            | market          | notes |
|-----------------|-----------------|-------|
| `crypto_ccxt`   | crypto exchanges| public order-book data via [ccxt](https://github.com/ccxt/ccxt), no API key needed |
| `odds_api`      | sports betting  | via [the-odds-api.com](https://the-odds-api.com), needs a free API key; see `arbitrage/sources/betting.py` for surebet stake sizing |
| `html_product`  | e-commerce      | generic scraper adapter; ships one working example against books.toscrape.com (a public scraping-practice sandbox). **Do not point this at a real marketplace's ToS-protected pages** — use an official seller/affiliate API instead |

## Setup

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml
# edit config.yaml: pick sources, symbols, thresholds
```

## Run

```bash
# one poll, print results, exit
python -m arbitrage.cli --config config.yaml --once

# run continuously, polling every `poll_interval_s`
python -m arbitrage.cli --config config.yaml
```

## Tests

```bash
pytest
```

## Important caveats

- **Fees and slippage are what make or break this.** `net_edge_pct` already
  subtracts both sides' fee rates — set them accurately per source, or the
  "opportunities" you see are fiction.
- **Quotes go stale.** Between fetching a quote and acting on it, price can
  move enough to erase the edge. This is exactly the noise the LLN section
  above is meant to average out over many trades, not eliminate on any one.
- **Betting arbitrage risk**: bookmakers actively detect and limit/ban
  accounts that surebet repeatedly. That's an account/bankroll risk, not
  something the code can fix.
- **Respect ToS and robots.txt.** The e-commerce adapter is generic on
  purpose — point it only at sources that permit automated access (an
  official API, or a sandbox like books.toscrape.com), not at a real
  marketplace's protected pages.
