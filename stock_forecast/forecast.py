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
from chronos import BaseChronosPipeline

# A small, CPU-friendly Chronos-Bolt model. Swap for "amazon/chronos-bolt-base"
# or a classic "amazon/chronos-t5-*" checkpoint for higher accuracy at the
# cost of more compute.
DEFAULT_MODEL = "amazon/chronos-bolt-small"


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
    ) -> ForecastResult:
        """Forecast ``prediction_length`` future bars from a price series.

        ``history`` must be indexed by date and sorted oldest to newest
        (e.g. the ``close`` column returned by ``data.fetch_ohlc``).
        """
        if len(history) < 2:
            raise ValueError("Need at least two historical observations to forecast.")
        if not 0 <= quantile_low < 0.5 < quantile_high <= 1:
            raise ValueError("Expected quantile_low < 0.5 < quantile_high, within [0, 1].")

        context = torch.tensor(history.to_numpy(), dtype=torch.float32)
        quantile_levels = sorted({quantile_low, 0.5, quantile_high})

        quantiles, _mean = self.pipeline.predict_quantiles(
            context,
            prediction_length=prediction_length,
            quantile_levels=quantile_levels,
        )
        # quantiles: (batch=1, prediction_length, num_quantiles)
        quantiles = quantiles[0].numpy()

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
