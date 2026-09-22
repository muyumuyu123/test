"""Zero-shot time series forecasting of stock closing prices with Chronos.

Chronos (https://github.com/amazon-science/chronos-forecasting) treats a
numeric series as a token sequence and is pretrained on a large corpus of
time series, so it can forecast a new series -- like a stock's closing
price -- with no task-specific training.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import torch
from chronos import BaseChronosPipeline, Chronos2Pipeline

# Chronos-2 (https://huggingface.co/autogluon/chronos-2) is the current
# generation forecasting model from the Chronos/AutoGluon team: a single
# checkpoint that handles univariate, multivariate and covariate-aware
# forecasting. Chronos-2 and Chronos-Bolt checkpoints are published under the
# "autogluon" Hugging Face org (not "amazon"); only the classic Chronos-T5
# checkpoints live under "amazon/chronos-t5-*". Swap for
# "autogluon/chronos-bolt-small" for a much smaller/faster model.
DEFAULT_MODEL = "autogluon/chronos-2"


@dataclass
class ForecastResult:
    """A Chronos forecast: a median path plus a low/high uncertainty band."""

    dates: pd.DatetimeIndex
    median: np.ndarray
    low: np.ndarray
    high: np.ndarray
    quantile_low: float
    quantile_high: float

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            {"median": self.median, "low": self.low, "high": self.high},
            index=self.dates,
        )


class ChronosStockForecaster:
    """Wraps a pretrained Chronos pipeline to forecast a univariate price series."""

    def __init__(self, model_id: str = DEFAULT_MODEL, device_map: str = "cpu"):
        self.model_id = model_id
        self.pipeline = BaseChronosPipeline.from_pretrained(
            model_id,
            device_map=device_map,
            dtype=torch.float32,
        )

    def forecast(
        self,
        history: pd.Series,
        prediction_length: int = 14,
        quantile_low: float = 0.1,
        quantile_high: float = 0.9,
        past_covariates: dict[str, pd.Series] | None = None,
    ) -> ForecastResult:
        """Forecast ``prediction_length`` future bars from a price series.

        ``history`` must be indexed by date and sorted oldest to newest
        (e.g. the ``close`` column returned by ``data.fetch_ohlc``).

        ``past_covariates`` (Chronos-2 only) are extra historical series --
        e.g. ``{"volume": df["volume"]}`` -- that inform the forecast without
        being forecast themselves. Each must have the same length as
        ``history``. Ignored/rejected on classic Chronos or Chronos-Bolt
        models, which only accept the target series.
        """
        if len(history) < 2:
            raise ValueError("Need at least two historical observations to forecast.")
        if not 0 <= quantile_low < 0.5 < quantile_high <= 1:
            raise ValueError("Expected quantile_low < 0.5 < quantile_high, within [0, 1].")

        context = torch.tensor(history.to_numpy(), dtype=torch.float32)
        quantile_levels = sorted({quantile_low, 0.5, quantile_high})

        if past_covariates:
            if not isinstance(self.pipeline, Chronos2Pipeline):
                raise ValueError(
                    f"past_covariates requires a Chronos-2 model; '{self.model_id}' "
                    "only accepts a plain target series."
                )
            for name, series in past_covariates.items():
                if len(series) != len(history):
                    raise ValueError(
                        f"Covariate '{name}' has {len(series)} points, expected "
                        f"{len(history)} (same length as history)."
                    )
            inputs = [
                {
                    "target": context,
                    "past_covariates": {
                        name: torch.tensor(series.to_numpy(), dtype=torch.float32)
                        for name, series in past_covariates.items()
                    },
                }
            ]
        else:
            # A one-element list is the input form both the classic/Bolt pipelines
            # (which stack it into a (1, length) batch) and Chronos-2 (which keeps
            # it as a one-item list, univariate) accept identically.
            inputs = [context]

        quantiles, _mean = self.pipeline.predict_quantiles(
            inputs,
            prediction_length=prediction_length,
            quantile_levels=quantile_levels,
        )
        quantiles = _first_series_quantiles(quantiles)

        low_idx = quantile_levels.index(quantile_low)
        median_idx = quantile_levels.index(0.5)
        high_idx = quantile_levels.index(quantile_high)

        future_dates = _next_business_days(history.index[-1], prediction_length)

        return ForecastResult(
            dates=future_dates,
            median=quantiles[:, median_idx],
            low=quantiles[:, low_idx],
            high=quantiles[:, high_idx],
            quantile_low=quantile_low,
            quantile_high=quantile_high,
        )


def _next_business_days(last_date, n: int) -> pd.DatetimeIndex:
    """The ``n`` business days following ``last_date`` (exclusive of it)."""
    return pd.bdate_range(start=last_date, periods=n + 1, freq="B")[1:]


def _first_series_quantiles(quantiles) -> np.ndarray:
    """Normalize a single-series ``predict_quantiles`` result to (prediction_length, num_quantiles).

    The classic/Bolt pipelines return one ``(batch, prediction_length, num_quantiles)``
    tensor; Chronos-2 returns a list with one ``(n_variates, prediction_length,
    num_quantiles)`` tensor per input series. Both were called with a single
    univariate series, so either shape reduces to the same 2D array.
    """
    first = quantiles[0]
    if first.ndim == 3:
        first = first[0]
    return first.numpy()
