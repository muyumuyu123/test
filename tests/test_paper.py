from datetime import datetime, timezone

from arbitrage.core import Quote, find_opportunities
from arbitrage.paper import PaperBook


def quote(source, price, instrument="BTC/USDT", fee_rate=0.0):
    return Quote(
        source=source,
        instrument=instrument,
        bid=price,
        ask=price,
        timestamp=datetime.now(timezone.utc),
        fee_rate=fee_rate,
    )


def one_opportunity(cheap=100.0, rich=110.0):
    opps = find_opportunities([quote("venue_a", cheap), quote("venue_b", rich)])
    assert len(opps) == 1
    return opps[0]


def test_not_settled_before_deadline():
    book = PaperBook(settle_after=3, cooldown_polls=0)
    book.record(one_opportunity(), poll=1)

    quotes = [quote("venue_a", 100.0), quote("venue_b", 110.0)]
    assert book.settle(quotes, poll=2) == []
    assert book.settle(quotes, poll=3) == []
    assert len(book.settle(quotes, poll=4)) == 1
    assert book.open_count == 0


def test_realized_uses_settlement_prices_not_detection_prices():
    book = PaperBook(settle_after=1, cooldown_polls=0)
    book.record(one_opportunity(cheap=100.0, rich=110.0), poll=1)

    # by settlement the spread has closed entirely
    settled = book.settle([quote("venue_a", 105.0), quote("venue_b", 105.0)], poll=2)
    assert len(settled) == 1
    assert settled[0].trade.detected_edge_pct == 10.0
    assert settled[0].realized_edge_pct == 0.0
    assert settled[0].slippage_pct == 10.0


def test_realized_can_be_negative_when_price_moves_against_you():
    book = PaperBook(settle_after=1, cooldown_polls=0)
    book.record(one_opportunity(cheap=100.0, rich=110.0), poll=1)

    # the spread inverted while the order was in flight
    settled = book.settle([quote("venue_a", 110.0), quote("venue_b", 100.0)], poll=2)
    assert settled[0].realized_edge_pct < 0


def test_fees_are_carried_into_settlement():
    opps = find_opportunities([
        quote("venue_a", 100.0, fee_rate=0.01),
        quote("venue_b", 110.0, fee_rate=0.01),
    ])
    book = PaperBook(settle_after=1, cooldown_polls=0)
    book.record(opps[0], poll=1)

    settled = book.settle([quote("venue_a", 100.0), quote("venue_b", 110.0)], poll=2)
    # 110*(1-0.01) / (100*(1+0.01)) - 1 = 7.82%, not the 10% gross spread
    assert round(settled[0].realized_edge_pct, 2) == 7.82


def test_cooldown_suppresses_the_same_route():
    book = PaperBook(settle_after=1, cooldown_polls=10)
    opp = one_opportunity()

    assert book.record(opp, poll=1) is not None
    assert book.record(opp, poll=5) is None      # still in cooldown
    assert book.record(opp, poll=10) is None     # boundary: 10-1 < 10
    assert book.record(opp, poll=11) is not None  # cooldown elapsed
    assert book.suppressed == 2


def test_cooldown_is_per_route():
    book = PaperBook(settle_after=1, cooldown_polls=10)
    a_to_b = one_opportunity()
    other = find_opportunities([
        quote("venue_c", 100.0, instrument="ETH/USDT"),
        quote("venue_d", 110.0, instrument="ETH/USDT"),
    ])[0]

    assert book.record(a_to_b, poll=1) is not None
    assert book.record(other, poll=1) is not None  # different route, not suppressed
    assert book.suppressed == 0


def test_unpriceable_trade_is_dropped_and_counted():
    book = PaperBook(settle_after=1, cooldown_polls=0)
    book.record(one_opportunity(), poll=1)

    # venue_b stopped quoting, so the fill cannot be priced
    settled = book.settle([quote("venue_a", 100.0)], poll=2)
    assert settled == []
    assert book.unpriced == 1
    assert book.open_count == 0
