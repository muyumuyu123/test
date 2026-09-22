"""Forecast an Indonesia Stock Exchange (IDX) ticker's closing price with Chronos.

Example
-------
    python -m stock_forecast.cli --ticker BBCA --prediction-length 14 --plot forecast.png
    python -m stock_forecast.cli --ticker BBCA --end-date 2025-08-31 --prediction-length 10
"""

from __future__ import annotations

import argparse

import pandas as pd
from chronos import Chronos2Pipeline

from .data import fetch_ohlc, normalize_idx_ticker
from .forecast import DEFAULT_MODEL, ChronosStockForecaster


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--ticker", required=True, help="IDX ticker, e.g. BBCA or BBCA.JK")
    parser.add_argument("--period", default="2y", help="History window passed to yfinance (default: 2y)")
    parser.add_argument("--interval", default="1d", help="Bar interval passed to yfinance (default: 1d)")
    parser.add_argument(
        "--end-date",
        default=None,
        help="Cut off history at this date (YYYY-MM-DD) instead of today; the forecast then "
        "starts from the next trading day after it.",
    )
    parser.add_argument(
        "--prediction-length", type=int, default=14, help="Number of future bars to forecast (default: 14)"
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Chronos model id (default: {DEFAULT_MODEL})")
    parser.add_argument("--device", default="cpu", help="Torch device_map for the model (default: cpu)")
    parser.add_argument("--quantile-low", type=float, default=0.1, help="Lower forecast interval quantile")
    parser.add_argument("--quantile-high", type=float, default=0.9, help="Upper forecast interval quantile")
    parser.add_argument("--plot", default=None, help="Optional path to save a PNG chart of the forecast")
    parser.add_argument(
        "--use-volume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Feed traded volume to the model as a covariate (Chronos-2 only; default: on)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)

    symbol = normalize_idx_ticker(args.ticker)
    print(f"Fetching {symbol} OHLC from Yahoo Finance ({args.period}, {args.interval})...")
    df = fetch_ohlc(args.ticker, period=args.period, interval=args.interval)

    if args.end_date:
        df = df[df.index <= pd.Timestamp(args.end_date)]
        if df.empty:
            raise ValueError(f"No data on or before --end-date {args.end_date}.")
        print(f"Cut history at {df.index[-1].date()} (last trading day on/before {args.end_date}).")

    print(f"Loading Chronos model '{args.model}' on {args.device}...")
    forecaster = ChronosStockForecaster(model_id=args.model, device_map=args.device)

    past_covariates = None
    if args.use_volume:
        if isinstance(forecaster.pipeline, Chronos2Pipeline):
            past_covariates = {"volume": df["volume"]}
        else:
            print(f"Note: '{args.model}' is not Chronos-2, so volume can't be used as a covariate; ignoring it.")

    print(f"Forecasting {args.prediction_length} bars ahead...")
    result = forecaster.forecast(
        df["close"],
        prediction_length=args.prediction_length,
        quantile_low=args.quantile_low,
        quantile_high=args.quantile_high,
        past_covariates=past_covariates,
    )

    print(f"\n{symbol} forecast (median, [{args.quantile_low:.0%}-{args.quantile_high:.0%}] interval):")
    for date, low, median, high in zip(result.dates, result.low, result.median, result.high):
        print(f"  {date.date()}  {median:>14,.2f}   [{low:,.2f} - {high:,.2f}]")

    if args.plot:
        from .plotting import plot_forecast

        plot_forecast(df["close"], result, symbol, args.plot)
        print(f"\nSaved chart to {args.plot}")


if __name__ == "__main__":
    main()
