"""Command-line entry point: build sources from a YAML config and run the
scanner. See config.example.yaml for the format.

Usage:
    python -m arbitrage.cli --config config.yaml
    python -m arbitrage.cli --config config.yaml --once   # single poll, print, exit
"""
from __future__ import annotations

import argparse
import logging
import os

import yaml

from arbitrage.scanner import Scanner, ScannerConfig
from arbitrage.sources.base import PriceSource


def _build_source(spec: dict) -> PriceSource:
    kind = spec["type"]
    if kind == "crypto_ccxt":
        from arbitrage.sources.crypto import CcxtSource
        return CcxtSource(
            exchange_id=spec["exchange"],
            symbols=spec["symbols"],
            fee_rate=spec.get("fee_rate"),
        )
    if kind == "odds_api":
        from arbitrage.sources.betting import OddsApiSource
        api_key = spec.get("api_key") or os.environ.get("ODDS_API_KEY", "")
        if not api_key:
            raise ValueError("odds_api source needs api_key (config or ODDS_API_KEY env var)")
        return OddsApiSource(
            api_key=api_key,
            sport=spec["sport"],
            regions=spec.get("regions", "eu,us"),
            markets=spec.get("markets", "h2h"),
        )
    if kind == "html_product":
        from arbitrage.sources.ecommerce import HtmlProductSource, books_toscrape_price
        parsers = {"books_toscrape": books_toscrape_price}
        parser = parsers.get(spec.get("parser", ""))
        if parser is None:
            raise ValueError(f"unknown parser {spec.get('parser')!r} for html_product source")
        return HtmlProductSource(
            name=spec["name"],
            instrument=spec["instrument"],
            url=spec["url"],
            parse=parser,
            fee_rate=spec.get("fee_rate", 0.0),
        )
    raise ValueError(f"unknown source type: {kind!r}")


def load_config(path: str) -> tuple[list[PriceSource], ScannerConfig]:
    with open(path) as f:
        raw = yaml.safe_load(f)

    sources = [_build_source(spec) for spec in raw.get("sources", [])]
    scanner_cfg = ScannerConfig(**raw.get("scanner", {}))
    return sources, scanner_cfg


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-source price arbitrage scanner")
    parser.add_argument("--config", required=True, help="path to YAML config")
    parser.add_argument("--once", action="store_true", help="poll a single time and exit")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    sources, scanner_cfg = load_config(args.config)
    scanner = Scanner(sources=sources, config=scanner_cfg)

    if args.once:
        opps = scanner.poll_once()
        print(f"found {len(opps)} opportunities this poll")
        for opp in opps:
            print(f"  {opp.instrument}: buy {opp.buy_source} -> sell {opp.sell_source}, net_edge={opp.net_edge_pct:.3f}%")
    else:
        scanner.run()


if __name__ == "__main__":
    main()
