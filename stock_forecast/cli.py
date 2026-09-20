"""Forecast an Indonesia Stock Exchange (IDX) ticker's closing price with Chronos.

Example
-------
    python -m stock_forecast.cli --ticker BBCA --prediction-length 14 --plot forecast.png
"""

from __future__ import annotations

import argparse

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
        "--prediction-length", type=int, default=14, help="Number of future bars to forecast (default: 14)"
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Chronos model id (default: {DEFAULT_MODEL})")
    parser.add_argument("--device", default="cpu", help="Torch device_map for the model (default: cpu)")
    parser.add_argument("--quantile-low", type=float, default=0.1, help="Lower forecast interval quantile")
    parser.add_argument("--quantile-high", type=float, default=0.9, help="Upper forecast interval quantile")
    parser.add_argument("--plot", default=None, help="Optional path to save a PNG chart of the forecast")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)

    symbol = normalize_idx_ticker(args.ticker)
    print(f"Fetching {symbol} OHLC from Yahoo Finance ({args.period}, {args.interval})...")
    df = fetch_ohlc(args.ticker, period=args.period, interval=args.interval)

    print(f"Loading Chronos model '{args.model}' on {args.device}...")
    forecaster = ChronosStockForecaster(model_id=args.model, device_map=args.device)

    print(f"Forecasting {args.prediction_length} bars ahead...")
    result = forecaster.forecast(
        df["close"],
        prediction_length=args.prediction_length,
        quantile_low=args.quantile_low,
        quantile_high=args.quantile_high,
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
