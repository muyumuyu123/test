import numpy as np
import pandas as pd
import pytest
import torch

from stock_forecast.forecast import ChronosStockForecaster, _next_business_days


class _FakePipeline:
    """Stands in for a Chronos pipeline without downloading real model weights."""

    def __init__(self, quantile_levels, prediction_length):
        self.quantile_levels = quantile_levels
        self.prediction_length = prediction_length
        self.received_context = None

    def predict_quantiles(self, context, prediction_length, quantile_levels):
        self.received_context = context
        assert prediction_length == self.prediction_length
        assert quantile_levels == self.quantile_levels

        base = context[-1].item()
        num_q = len(quantile_levels)
        # Increasing values across quantiles, flat across the horizon, so the
        # test can assert ordering without depending on real model output.
        values = torch.tensor(
            [[base + q * 10 for q in range(num_q)] for _ in range(prediction_length)],
            dtype=torch.float32,
        )
        quantiles = values.unsqueeze(0)  # (batch=1, prediction_length, num_quantiles)
        mean = values[:, num_q // 2].unsqueeze(0)
        return quantiles, mean


@pytest.fixture
def history():
    dates = pd.bdate_range("2024-01-01", periods=30)
    values = np.linspace(1000, 1029, num=30)
    return pd.Series(values, index=dates)


def _install_fake_pipeline(monkeypatch, prediction_length, quantile_low=0.1, quantile_high=0.9):
    expected_levels = sorted({quantile_low, 0.5, quantile_high})
    fake = _FakePipeline(expected_levels, prediction_length)
    monkeypatch.setattr(
        "stock_forecast.forecast.BaseChronosPipeline.from_pretrained",
        lambda *a, **kw: fake,
    )
    return fake


def test_forecast_returns_expected_shape_and_ordering(monkeypatch, history):
    fake = _install_fake_pipeline(monkeypatch, prediction_length=7)

    forecaster = ChronosStockForecaster()
    result = forecaster.forecast(history, prediction_length=7)

    assert len(result.dates) == 7
    assert len(result.median) == 7
    assert len(result.low) == 7
    assert len(result.high) == 7
    # low < median < high for every step, since the fake pipeline is monotone in quantile.
    assert np.all(result.low < result.median)
    assert np.all(result.median < result.high)
    # forecast should start after the last historical date.
    assert result.dates[0] > history.index[-1]
    assert torch.equal(fake.received_context, torch.tensor(history.to_numpy(), dtype=torch.float32))


def test_forecast_rejects_too_short_history(monkeypatch, history):
    _install_fake_pipeline(monkeypatch, prediction_length=7)
    forecaster = ChronosStockForecaster()

    with pytest.raises(ValueError, match="at least two"):
        forecaster.forecast(history.iloc[:1], prediction_length=7)


def test_forecast_rejects_bad_quantiles(monkeypatch, history):
    _install_fake_pipeline(monkeypatch, prediction_length=7, quantile_low=0.5, quantile_high=0.5)
    forecaster = ChronosStockForecaster()

    with pytest.raises(ValueError, match="quantile_low < 0.5 < quantile_high"):
        forecaster.forecast(history, prediction_length=7, quantile_low=0.5, quantile_high=0.5)


def test_next_business_days_skips_weekends():
    # 2024-01-05 is a Friday.
    result = _next_business_days(pd.Timestamp("2024-01-05"), 3)
    assert list(result.strftime("%Y-%m-%d")) == ["2024-01-08", "2024-01-09", "2024-01-10"]
