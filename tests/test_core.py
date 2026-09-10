from datetime import datetime, timezone

from arbitrage.core import Quote, find_opportunities


def make_quote(source, instrument, price, fee_rate=0.0):
    return Quote(
        source=source,
        instrument=instrument,
        bid=price,
        ask=price,
        timestamp=datetime.now(timezone.utc),
        fee_rate=fee_rate,
    )


def test_finds_profitable_pair():
    quotes = [
        make_quote("exchange_a", "BTC/USDT", 100.0),
        make_quote("exchange_b", "BTC/USDT", 110.0),
    ]
    opps = find_opportunities(quotes, min_net_edge_pct=0.0)
    assert len(opps) == 1
    opp = opps[0]
    assert opp.buy_source == "exchange_a"
    assert opp.sell_source == "exchange_b"
    assert opp.net_edge_pct == 10.0


def test_fees_can_erase_edge():
    quotes = [
        make_quote("exchange_a", "BTC/USDT", 100.0, fee_rate=0.05),
        make_quote("exchange_b", "BTC/USDT", 101.0, fee_rate=0.05),
    ]
    opps = find_opportunities(quotes, min_net_edge_pct=0.0)
    assert opps == []


def test_no_opportunity_for_single_source():
    quotes = [make_quote("only_one", "BTC/USDT", 100.0)]
    assert find_opportunities(quotes) == []


def test_different_instruments_not_compared():
    quotes = [
        make_quote("exchange_a", "BTC/USDT", 100.0),
        make_quote("exchange_b", "ETH/USDT", 110.0),
    ]
    assert find_opportunities(quotes) == []
