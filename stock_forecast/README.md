# Indonesian Stock Forecasting with Chronos

Forecasts closing prices for Indonesia Stock Exchange (IDX) tickers using
[Chronos](https://github.com/amazon-science/chronos-forecasting), Amazon's
pretrained time series foundation model. OHLC data comes straight from Yahoo
Finance via `yfinance`; no historical training or fine-tuning is needed since
Chronos forecasts zero-shot from the raw price series.

## Install

```bash
pip install -r requirements.txt
```

## Usage

```bash
python -m stock_forecast.cli --ticker BBCA --prediction-length 14 --plot forecast.png
```

- `--ticker` accepts a bare code (`BBCA`) or the full Yahoo Finance symbol
  (`BBCA.JK`) -- IDX tickers are auto-suffixed with `.JK`.
- `--period` / `--interval` are passed straight to `yfinance.download`
  (default: 2 years of daily bars).
- `--prediction-length` is how many future trading days to forecast.
- `--model` selects the Chronos checkpoint (default `amazon/chronos-bolt-small`;
  try `amazon/chronos-bolt-base` or `amazon/chronos-t5-small` for a different
  accuracy/speed trade-off). The first run downloads the model from Hugging
  Face and caches it locally.
- `--plot forecast.png` saves a chart of recent history plus the forecast
  and its uncertainty band.

Some well-known IDX blue chips (see `stock_forecast.data.POPULAR_IDX_TICKERS`):
`BBCA`, `BBRI`, `BMRI`, `BBNI`, `TLKM`, `ASII`, `UNVR`, `ICBP`, `ANTM`, `GOTO`.

## Library usage

```python
from stock_forecast.data import fetch_ohlc
from stock_forecast.forecast import ChronosStockForecaster

df = fetch_ohlc("BBCA", period="2y", interval="1d")

forecaster = ChronosStockForecaster()  # loads amazon/chronos-bolt-small
result = forecaster.forecast(df["close"], prediction_length=14)

print(result.to_frame())
```

## How it works

1. `data.py` downloads OHLCV history for the ticker and normalizes it into a
   date-indexed DataFrame with lowercase columns.
2. `forecast.py` feeds the closing-price series into a pretrained Chronos
   pipeline (`chronos.BaseChronosPipeline`, which auto-selects the right
   pipeline for classic Chronos or Chronos-Bolt checkpoints) and reads off
   the median and a low/high quantile band for the requested horizon.
3. `plotting.py` optionally renders the historical series against the
   forecast band as a PNG.

This is a statistical forecast of a noisy series, not investment advice --
treat the uncertainty band as a reminder of how wide the plausible outcomes
are, especially past a few trading days out.
