import numpy as np
import pandas as pd
import pytest
import torch
from chronos import Chronos2Pipeline

from stock_forecast.forecast import ChronosStockForecaster, _next_business_days


class _FakePipeline:
    """Stands in for a Chronos pipeline without downloading real model weights.

    ``shape_mode`` mimics the two ``predict_quantiles`` return shapes actually
    used by chronos-forecasting:
    - "classic": the Chronos/Chronos-Bolt pipelines return one
      ``(batch, prediction_length, num_quantiles)`` tensor.
    - "chronos2": Chronos-2 returns a list with one
      ``(n_variates, prediction_length, num_quantiles)`` tensor per input series.
    """

    def __init__(self, quantile_levels, prediction_length, shape_mode="classic"):
        self.quantile_levels = quantile_levels
        self.prediction_length = prediction_length
        self.shape_mode = shape_mode
        self.received_inputs = None

    def predict_quantiles(self, inputs, prediction_length, quantile_levels):
        self.received_inputs = inputs
        assert prediction_length == self.prediction_length
        assert quantile_levels == self.quantile_levels
        assert isinstance(inputs, list) and len(inputs) == 1

        context = inputs[0]
        base = context[-1].item()
        num_q = len(quantile_levels)
        # Increasing values across quantiles, flat across the horizon, so the
        # test can assert ordering without depending on real model output.
        values = torch.tensor(
            [[base + q * 10 for q in range(num_q)] for _ in range(prediction_length)],
            dtype=torch.float32,
        )

        if self.shape_mode == "classic":
            quantiles = values.unsqueeze(0)  # (batch=1, prediction_length, num_quantiles)
            mean = values[:, num_q // 2].unsqueeze(0)
        elif self.shape_mode == "chronos2":
            quantiles = [values.unsqueeze(0)]  # [(n_variates=1, prediction_length, num_quantiles)]
            mean = [values[:, num_q // 2].unsqueeze(0)]
        else:
            raise ValueError(self.shape_mode)

        return quantiles, mean


class _FakeChronos2Pipeline(Chronos2Pipeline):
    """A real ``Chronos2Pipeline`` subclass (so isinstance checks pass) that
    fakes ``predict_quantiles`` without needing real model weights."""

    def __init__(self, quantile_levels, prediction_length):
        # Deliberately skip Chronos2Pipeline.__init__: it just wants a real
        # Chronos2Model, which we don't need for a fake predict_quantiles.
        self.quantile_levels = quantile_levels
        self.prediction_length = prediction_length
        self.received_inputs = None

    def predict_quantiles(self, inputs, prediction_length, quantile_levels):
        self.received_inputs = inputs
        assert prediction_length == self.prediction_length
        assert quantile_levels == self.quantile_levels
        assert isinstance(inputs, list) and len(inputs) == 1

        item = inputs[0]
        context = item["target"] if isinstance(item, dict) else item
        base = context[-1].item()
        num_q = len(quantile_levels)
        values = torch.tensor(
            [[base + q * 10 for q in range(num_q)] for _ in range(prediction_length)],
            dtype=torch.float32,
        )
        quantiles = [values.unsqueeze(0)]  # [(n_variates=1, prediction_length, num_quantiles)]
        mean = [values[:, num_q // 2].unsqueeze(0)]
        return quantiles, mean


@pytest.fixture
def history():
    dates = pd.bdate_range("2024-01-01", periods=30)
    values = np.linspace(1000, 1029, num=30)
    return pd.Series(values, index=dates)


def _install_fake_pipeline(
    monkeypatch, prediction_length, quantile_low=0.1, quantile_high=0.9, shape_mode="classic"
):
    expected_levels = sorted({quantile_low, 0.5, quantile_high})
    fake = _FakePipeline(expected_levels, prediction_length, shape_mode=shape_mode)
    monkeypatch.setattr(
        "stock_forecast.forecast.BaseChronosPipeline.from_pretrained",
        lambda *a, **kw: fake,
    )
    return fake


def _install_fake_chronos2_pipeline(monkeypatch, prediction_length, quantile_low=0.1, quantile_high=0.9):
    expected_levels = sorted({quantile_low, 0.5, quantile_high})
    fake = _FakeChronos2Pipeline(expected_levels, prediction_length)
    monkeypatch.setattr(
        "stock_forecast.forecast.BaseChronosPipeline.from_pretrained",
        lambda *a, **kw: fake,
    )
    return fake


@pytest.mark.parametrize("shape_mode", ["classic", "chronos2"])
def test_forecast_returns_expected_shape_and_ordering(monkeypatch, history, shape_mode):
    fake = _install_fake_pipeline(monkeypatch, prediction_length=7, shape_mode=shape_mode)

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
    assert torch.equal(fake.received_inputs[0], torch.tensor(history.to_numpy(), dtype=torch.float32))


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


def test_forecast_with_past_covariates_on_chronos2(monkeypatch, history):
    fake = _install_fake_chronos2_pipeline(monkeypatch, prediction_length=5)
    volume = pd.Series(np.linspace(1_000_000, 1_029_000, num=len(history)), index=history.index)

    forecaster = ChronosStockForecaster()
    result = forecaster.forecast(history, prediction_length=5, past_covariates={"volume": volume})

    assert len(result.median) == 5
    sent = fake.received_inputs[0]
    assert isinstance(sent, dict)
    assert torch.equal(sent["target"], torch.tensor(history.to_numpy(), dtype=torch.float32))
    assert torch.equal(sent["past_covariates"]["volume"], torch.tensor(volume.to_numpy(), dtype=torch.float32))


def test_forecast_rejects_covariates_on_non_chronos2_model(monkeypatch, history):
    _install_fake_pipeline(monkeypatch, prediction_length=5, shape_mode="classic")
    volume = pd.Series(np.linspace(1_000_000, 1_029_000, num=len(history)), index=history.index)
    forecaster = ChronosStockForecaster()

    with pytest.raises(ValueError, match="requires a Chronos-2 model"):
        forecaster.forecast(history, prediction_length=5, past_covariates={"volume": volume})


def test_forecast_rejects_mismatched_covariate_length(monkeypatch, history):
    _install_fake_chronos2_pipeline(monkeypatch, prediction_length=5)
    short_volume = pd.Series(np.linspace(1_000_000, 1_010_000, num=len(history) - 1))
    forecaster = ChronosStockForecaster()

    with pytest.raises(ValueError, match="same length as history"):
        forecaster.forecast(history, prediction_length=5, past_covariates={"volume": short_volume})
