"""Fetch OHLC(V) history for Indonesia Stock Exchange (IDX) tickers from Yahoo Finance."""

from __future__ import annotations

import pandas as pd
import yfinance as yf

IDX_SUFFIX = ".JK"

# A handful of well-known IDX blue chips, for convenience (ticker -> company name).
# Yahoo Finance addresses IDX-listed stocks with a ".JK" suffix.
POPULAR_IDX_TICKERS = {
    "BBCA": "Bank Central Asia",
    "BBRI": "Bank Rakyat Indonesia",
    "BMRI": "Bank Mandiri",
    "BBNI": "Bank Negara Indonesia",
    "TLKM": "Telkom Indonesia",
    "ASII": "Astra International",
    "UNVR": "Unilever Indonesia",
    "ICBP": "Indofood CBP",
    "ANTM": "Aneka Tambang",
    "GOTO": "GoTo Gojek Tokopedia",
}

OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]


def normalize_idx_ticker(ticker: str) -> str:
    """Append the IDX (".JK") suffix if the ticker doesn't already carry an exchange suffix."""
    symbol = ticker.strip().upper()
    if "." not in symbol:
        symbol += IDX_SUFFIX
    return symbol


def fetch_ohlc(ticker: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    """Download OHLCV history for an Indonesian stock from Yahoo Finance.

    ``ticker`` may be given with or without the ``.JK`` suffix Yahoo Finance
    uses for IDX-listed stocks (e.g. ``"BBCA"`` and ``"BBCA.JK"`` both resolve
    to Bank Central Asia).

    Returns a DataFrame indexed by date with lowercase ``open``/``high``/
    ``low``/``close``/``volume`` columns, sorted oldest to newest.
    """
    symbol = normalize_idx_ticker(ticker)
    raw = yf.download(
        symbol,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=True,
    )

    if raw is None or raw.empty:
        raise ValueError(
            f"No data returned for '{symbol}'. Check the ticker symbol "
            "(IDX tickers use the '.JK' suffix, e.g. 'BBCA.JK')."
        )

    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower)
    df.index.name = "date"
    df = df.sort_index()

    missing = [c for c in OHLCV_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Yahoo Finance response for '{symbol}' is missing columns: {missing}")

    return df[OHLCV_COLUMNS]
