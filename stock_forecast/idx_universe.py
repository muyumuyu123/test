"""The full Indonesia Stock Exchange (IDX) ticker universe.

Scrapes IDX's official "Daftar Saham" (stock list) page --
https://www.idx.co.id/id/data-pasar/data-saham/daftar-saham/ -- which lists
every company listed on the exchange (roughly 900+ tickers). The page itself
renders the table client-side from a JSON endpoint
(``/primary/StockData/GetSecuritiesStock``), so this fetches that endpoint
directly rather than parsing HTML.

IDX has changed the field names of that endpoint across past site redesigns,
so parsing here is deliberately defensive: it tries a short list of known
field-name variants and raises a clear, actionable error (naming the actual
keys it found) rather than silently returning wrong or empty data if IDX
changes the schema again.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

IDX_LIST_PAGE = "https://www.idx.co.id/id/data-pasar/data-saham/daftar-saham/"
IDX_API_URL = "https://www.idx.co.id/primary/StockData/GetSecuritiesStock"

CACHE_PATH = Path(__file__).with_name("idx_stock_list.csv")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": IDX_LIST_PAGE,
    "Accept": "application/json, text/plain, */*",
}

# Candidate field names IDX's internal API has used for these values.
_CODE_KEYS = ["Kode", "KodeEmiten", "Code", "StockCode", "SecuritiesCode"]
_NAME_KEYS = ["NamaEmiten", "NamaPerusahaan", "Name", "StockName", "SecuritiesName"]


class IdxListingError(RuntimeError):
    """Raised when the IDX response can't be parsed into a ticker list."""


def _extract_records(payload) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "Data", "results", "emiten"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    raise IdxListingError(
        "Unrecognized IDX API response shape: expected a list, or a dict "
        "with a 'data' list. Got top-level keys: "
        f"{sorted(payload) if isinstance(payload, dict) else type(payload).__name__}"
    )


def _pick_key(record: dict, candidates: list[str], role: str) -> str:
    for key in candidates:
        if key in record:
            return key
    raise IdxListingError(
        f"Could not find a {role} field in the IDX response. Tried {candidates}; "
        f"available fields on a sample record: {sorted(record)}"
    )


def fetch_idx_stock_list(timeout: float = 30.0) -> pd.DataFrame:
    """Download the full list of IDX-listed companies from idx.co.id.

    Returns a DataFrame with a ``ticker`` column (Yahoo Finance symbol, e.g.
    ``"BBCA.JK"``) and a ``name`` column, one row per listed company.
    """
    params = {"emitenType": "s", "start": 0, "length": 9999}
    response = requests.get(IDX_API_URL, params=params, headers=_HEADERS, timeout=timeout)
    response.raise_for_status()
    records = _extract_records(response.json())

    if not records:
        raise IdxListingError("IDX API returned zero records.")

    code_key = _pick_key(records[0], _CODE_KEYS, "ticker code")
    name_key = _pick_key(records[0], _NAME_KEYS, "company name")

    rows = [
        {"ticker": f"{str(rec[code_key]).strip().upper()}.JK", "name": str(rec[name_key]).strip()}
        for rec in records
        if rec.get(code_key)
    ]
    if not rows:
        raise IdxListingError("Parsed zero valid tickers out of the IDX API response.")

    return (
        pd.DataFrame(rows)
        .drop_duplicates(subset="ticker")
        .sort_values("ticker")
        .reset_index(drop=True)
    )


def load_idx_universe(refresh: bool = False) -> pd.DataFrame:
    """Load the full IDX ticker universe, caching it locally after the first fetch.

    Set ``refresh=True`` to bypass the cache and re-download the current list
    (IDX adds/removes listings over time, so refresh periodically for
    up-to-date coverage).
    """
    if not refresh and CACHE_PATH.exists():
        return pd.read_csv(CACHE_PATH)

    df = fetch_idx_stock_list()
    df.to_csv(CACHE_PATH, index=False)
    return df


if __name__ == "__main__":
    universe = load_idx_universe(refresh=True)
    print(f"Fetched {len(universe)} IDX-listed tickers -> {CACHE_PATH}")
