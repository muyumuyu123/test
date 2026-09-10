import random

from arbitrage.stats import RunningStats


def test_matches_naive_mean():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    stats = RunningStats()
    for v in values:
        stats.update(v)
    assert stats.n == 5
    assert stats.mean == sum(values) / len(values)


def test_confidence_interval_narrows_with_n():
    random.seed(0)
    stats = RunningStats()
    # true mean edge is +0.2%, noisy per-trade (std dev 2%)
    for _ in range(10):
        stats.update(random.gauss(0.2, 2.0))
    width_10 = stats.confidence_interval()[1] - stats.confidence_interval()[0]

    for _ in range(990):  # total n = 1000
        stats.update(random.gauss(0.2, 2.0))
    width_1000 = stats.confidence_interval()[1] - stats.confidence_interval()[0]

    assert width_1000 < width_10


def test_law_of_large_numbers_reveals_small_positive_edge():
    random.seed(1)
    stats = RunningStats()
    # a small, individually-unconvincing edge (+0.05%) buried in noise (std dev 1%)
    for _ in range(20):
        stats.update(random.gauss(0.05, 1.0))
    assert not stats.is_significantly_positive()  # too few samples to trust yet

    for _ in range(50_000):
        stats.update(random.gauss(0.05, 1.0))
    assert stats.is_significantly_positive()  # LLN: mean has converged, CI cleared zero
    assert stats.expected_total_return_pct() > 0


def test_zero_or_negative_true_edge_never_becomes_significant():
    random.seed(2)
    stats = RunningStats()
    for _ in range(50_000):
        stats.update(random.gauss(-0.05, 1.0))
    assert not stats.is_significantly_positive()
