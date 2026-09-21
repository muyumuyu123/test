# Indonesian Stock Forecasting with Chronos

Forecasts closing prices for Indonesia Stock Exchange (IDX) tickers using
[Chronos-2](https://huggingface.co/autogluon/chronos-2), the current
generation model from Amazon's
[chronos-forecasting](https://github.com/amazon-science/chronos-forecasting)
library, a pretrained time series foundation model. OHLC data comes straight
from Yahoo Finance via `yfinance`; no historical training or fine-tuning is
needed since Chronos forecasts zero-shot from the raw price series.

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
- `--model` selects the Chronos checkpoint (default `autogluon/chronos-2`; try
  `autogluon/chronos-bolt-small` for a much smaller/faster model, at a cost in
  accuracy). The first run downloads the model from Hugging Face and caches
  it locally.
- `--plot forecast.png` saves a chart of recent history plus the forecast
  and its uncertainty band.

Some well-known IDX blue chips (see `stock_forecast.data.POPULAR_IDX_TICKERS`):
`BBCA`, `BBRI`, `BMRI`, `BBNI`, `TLKM`, `ASII`, `UNVR`, `ICBP`, `ANTM`, `GOTO`.

## The full IDX universe (~900+ tickers), not just the 10 blue chips above

`idx_universe.py` fetches the complete list of companies listed on IDX from
the official ["Daftar Saham"](https://www.idx.co.id/id/data-pasar/data-saham/daftar-saham/)
page (via the JSON API that page itself calls), and caches it to
`stock_forecast/idx_stock_list.csv` so later runs don't need to refetch it:

```bash
python -m stock_forecast.idx_universe   # fetches and caches the full list
```

```python
from stock_forecast.idx_universe import load_idx_universe

universe = load_idx_universe()  # DataFrame with `ticker` (e.g. "BBCA.JK") and `name`
print(len(universe), "tickers")
```

`batch.py` loads Chronos once and forecasts every ticker in that list,
skipping (and logging) any that fail to download rather than aborting the
whole run -- with ~900+ tickers spread across small-cap and thinly-traded
names, some Yahoo Finance misses are expected:

```bash
python -m stock_forecast.batch --output idx_forecasts.csv
# or, to try it on a handful first:
python -m stock_forecast.batch --output sample.csv --limit 20
```

This downloads ~900+ histories from Yahoo Finance and runs the model
~900+ times, so budget real wall-clock time for a full run (use `--device
cuda` if you have a GPU, and raise `--sleep` if Yahoo Finance starts
rate-limiting you).

**Caveat:** IDX's internal API (`/primary/StockData/GetSecuritiesStock`) is
undocumented and has changed field names across past site redesigns.
`fetch_idx_stock_list` tries several known field-name variants and raises a
clear `IdxListingError` naming the actual fields it found if none match, so a
future IDX change fails loudly instead of silently returning wrong data --
if you hit that error, update `_CODE_KEYS`/`_NAME_KEYS` in `idx_universe.py`
to match.

## Library usage

```python
from stock_forecast.data import fetch_ohlc
from stock_forecast.forecast import ChronosStockForecaster

df = fetch_ohlc("BBCA", period="2y", interval="1d")

forecaster = ChronosStockForecaster()  # loads autogluon/chronos-2
result = forecaster.forecast(df["close"], prediction_length=14)

print(result.to_frame())
```

## How it works

1. `data.py` downloads OHLCV history for the ticker and normalizes it into a
   date-indexed DataFrame with lowercase columns.
2. `forecast.py` feeds the closing-price series into a pretrained Chronos
   pipeline (`chronos.BaseChronosPipeline`, which auto-selects the right
   pipeline class for the checkpoint -- Chronos-2, classic Chronos, or
   Chronos-Bolt -- and normalizes their differing output shapes) and reads
   off the median and a low/high quantile band for the requested horizon.
3. `plotting.py` optionally renders the historical series against the
   forecast band as a PNG.

This is a statistical forecast of a noisy series, not investment advice --
treat the uncertainty band as a reminder of how wide the plausible outcomes
are, especially past a few trading days out.
