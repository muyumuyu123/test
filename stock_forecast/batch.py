"""Forecast every stock in the IDX universe with Chronos, not just a handful.

Loads Chronos once, then iterates the full IDX ticker list (see
``idx_universe.load_idx_universe``), forecasting each ticker's closing price
and appending one result row per ticker to a CSV. A ticker that fails to
download or forecast (delisted, no recent trades, a transient Yahoo Finance
error) is skipped and logged rather than aborting the whole run -- with ~900+
tickers, some failures are expected.

Example
-------
    python -m stock_forecast.batch --output idx_forecasts.csv --limit 50
"""

from __future__ import annotations

import argparse
import time

import pandas as pd

from .data import fetch_ohlc
from .forecast import DEFAULT_MODEL, ChronosStockForecaster
from .idx_universe import load_idx_universe


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--output", default="idx_forecasts.csv", help="CSV path to write results to")
    parser.add_argument("--period", default="1y", help="History window passed to yfinance (default: 1y)")
    parser.add_argument("--interval", default="1d", help="Bar interval passed to yfinance (default: 1d)")
    parser.add_argument("--prediction-length", type=int, default=14)
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Chronos model id (default: {DEFAULT_MODEL})")
    parser.add_argument("--device", default="cpu", help="Torch device_map for the model (default: cpu)")
    parser.add_argument("--limit", type=int, default=None, help="Only forecast the first N tickers (for testing)")
    parser.add_argument("--sleep", type=float, default=0.5, help="Seconds to sleep between Yahoo Finance requests")
    parser.add_argument(
        "--refresh-universe", action="store_true", help="Re-download the IDX ticker list before running"
    )
    return parser


def run_batch(
    forecaster: ChronosStockForecaster,
    universe: pd.DataFrame,
    period: str,
    interval: str,
    prediction_length: int,
    sleep_seconds: float,
) -> pd.DataFrame:
    """Forecast every ticker in ``universe``, skipping and logging failures."""
    rows = []
    for i, record in enumerate(universe.itertuples(), start=1):
        print(f"[{i}/{len(universe)}] {record.ticker} ({record.name})...", end=" ", flush=True)
        try:
            df = fetch_ohlc(record.ticker, period=period, interval=interval)
            result = forecaster.forecast(df["close"], prediction_length=prediction_length)
        except Exception as exc:  # noqa: BLE001 - one bad ticker must not abort the batch
            print(f"skipped ({exc})")
            continue

        rows.append(
            {
                "ticker": record.ticker,
                "name": record.name,
                "as_of": df.index[-1].date(),
                "last_close": df["close"].iloc[-1],
                "forecast_date": result.dates[-1].date(),
                "median": result.median[-1],
                "low": result.low[-1],
                "high": result.high[-1],
            }
        )
        print("ok")
        if sleep_seconds:
            time.sleep(sleep_seconds)

    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)

    universe = load_idx_universe(refresh=args.refresh_universe)
    if args.limit:
        universe = universe.head(args.limit)
    print(f"Loaded {len(universe)} IDX tickers.")

    print(f"Loading Chronos model '{args.model}' on {args.device}...")
    forecaster = ChronosStockForecaster(model_id=args.model, device_map=args.device)

    out = run_batch(
        forecaster,
        universe,
        period=args.period,
        interval=args.interval,
        prediction_length=args.prediction_length,
        sleep_seconds=args.sleep,
    )
    out.to_csv(args.output, index=False)
    print(f"\nWrote {len(out)}/{len(universe)} forecasts to {args.output}")


if __name__ == "__main__":
    main()
