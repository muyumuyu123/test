"""E-commerce product price source.

Scraping real marketplaces (Tokopedia, Shopee, Amazon, ...) generally
violates their Terms of Service, and their anti-bot defenses will break a
naive scraper anyway. Prefer an official seller/affiliate/partner API
wherever one exists — most large marketplaces have one. This module gives
you the adapter shape (`HtmlProductSource` + a `parse` callable you supply)
plus one fully working example against books.toscrape.com, a public
sandbox site built specifically for scraping practice, so the mechanics
are demonstrated without touching a real site's ToS. Point `HtmlProductSource`
only at pages whose robots.txt/ToS permit automated access, and keep
request rates low and a real contact User-Agent.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

import requests
from bs4 import BeautifulSoup

from arbitrage.core import Quote
from arbitrage.sources.base import PriceSource


class HtmlProductSource(PriceSource):
    """Fetches one product page and extracts a single price via `parse`."""

    def __init__(
        self,
        name: str,
        instrument: str,
        url: str,
        parse: Callable[[str], float],
        fee_rate: float = 0.0,
        headers: dict | None = None,
    ):
        self.name = name
        self.instrument = instrument
        self.url = url
        self.parse = parse
        self.fee_rate = fee_rate
        self.headers = headers or {"User-Agent": "arbitrage-scanner/1.0 (contact: you@example.com)"}

    def fetch_quotes(self) -> list[Quote]:
        resp = requests.get(self.url, headers=self.headers, timeout=10)
        resp.raise_for_status()
        price = self.parse(resp.text)
        now = datetime.now(timezone.utc)
        return [Quote(
            source=self.name,
            instrument=self.instrument,
            bid=price,
            ask=price,
            timestamp=now,
            fee_rate=self.fee_rate,
        )]


def books_toscrape_price(html: str) -> float:
    """Example parser for a https://books.toscrape.com product page."""
    soup = BeautifulSoup(html, "html.parser")
    price_el = soup.select_one("p.price_color")
    if price_el is None:
        raise ValueError("price element not found")
    return float(price_el.text.replace("£", "").strip())
