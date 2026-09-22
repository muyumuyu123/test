"""Chart a stock's historical close price against its Chronos forecast."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from .forecast import ForecastResult  # noqa: E402


def plot_forecast(
    history: pd.Series,
    result: ForecastResult,
    ticker: str,
    output_path: str,
    history_bars: int = 120,
) -> None:
    """Save a PNG chart with recent history, the median forecast, and its interval band."""
    fig, ax = plt.subplots(figsize=(11, 5))

    tail = history.tail(history_bars)
    ax.plot(tail.index, tail.to_numpy(), label="Historical close", color="#1f77b4")
    ax.plot(result.dates, result.median, label="Chronos median forecast", color="#d62728")
    ax.fill_between(
        result.dates,
        result.low,
        result.high,
        color="#d62728",
        alpha=0.2,
        label=f"{result.quantile_low:.0%}-{result.quantile_high:.0%} interval",
    )

    ax.set_title(f"{ticker} closing price forecast (Chronos)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price (IDR)")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
