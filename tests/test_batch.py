import numpy as np
import pandas as pd
import pytest

from stock_forecast.batch import run_batch
from stock_forecast.forecast import ForecastResult


class _FakeForecaster:
    def __init__(self, fail_tickers=()):
        self.fail_tickers = set(fail_tickers)
        self.calls = []

    def forecast(self, history, prediction_length):
        self.calls.append(len(history))
        last = history.iloc[-1]
        dates = pd.bdate_range(history.index[-1], periods=prediction_length + 1)[1:]
        return ForecastResult(
            dates=dates,
            median=np.full(prediction_length, last),
            low=np.full(prediction_length, last - 10),
            high=np.full(prediction_length, last + 10),
            quantile_low=0.1,
            quantile_high=0.9,
        )


@pytest.fixture
def universe():
    return pd.DataFrame(
        {
            "ticker": ["AAAA.JK", "BBBB.JK", "CCCC.JK"],
            "name": ["Company A", "Company B", "Company C"],
        }
    )


def _fake_ohlc_for(fail_tickers):
    def _fetch(ticker, period, interval):
        if ticker in fail_tickers:
            raise ValueError(f"No data returned for '{ticker}'.")
        dates = pd.bdate_range("2024-01-01", periods=10)
        return pd.DataFrame({"close": np.linspace(100, 109, 10)}, index=dates)

    return _fetch


def test_run_batch_skips_failing_tickers_without_aborting(monkeypatch, universe):
    monkeypatch.setattr("stock_forecast.batch.fetch_ohlc", _fake_ohlc_for(fail_tickers={"BBBB.JK"}))
    forecaster = _FakeForecaster()

    out = run_batch(forecaster, universe, period="1y", interval="1d", prediction_length=5, sleep_seconds=0)

    assert list(out["ticker"]) == ["AAAA.JK", "CCCC.JK"]
    assert set(out.columns) == {
        "ticker",
        "name",
        "as_of",
        "last_close",
        "forecast_date",
        "median",
        "low",
        "high",
    }
    assert len(forecaster.calls) == 2


def test_run_batch_returns_empty_frame_when_all_fail(monkeypatch, universe):
    monkeypatch.setattr(
        "stock_forecast.batch.fetch_ohlc",
        _fake_ohlc_for(fail_tickers={"AAAA.JK", "BBBB.JK", "CCCC.JK"}),
    )
    forecaster = _FakeForecaster()

    out = run_batch(forecaster, universe, period="1y", interval="1d", prediction_length=5, sleep_seconds=0)

    assert out.empty
