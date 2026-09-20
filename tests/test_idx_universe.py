import pandas as pd
import pytest

from stock_forecast.idx_universe import (
    IdxListingError,
    fetch_idx_stock_list,
    load_idx_universe,
)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _fake_get(payload):
    return lambda url, params=None, headers=None, timeout=None: _FakeResponse(payload)


def test_fetch_idx_stock_list_parses_data_wrapped_records(monkeypatch):
    payload = {
        "data": [
            {"Kode": "bbca", "NamaEmiten": " Bank Central Asia Tbk. "},
            {"Kode": "TLKM", "NamaEmiten": "Telkom Indonesia Tbk."},
        ]
    }
    monkeypatch.setattr("stock_forecast.idx_universe.requests.get", _fake_get(payload))

    df = fetch_idx_stock_list()

    assert list(df.columns) == ["ticker", "name"]
    assert list(df["ticker"]) == ["BBCA.JK", "TLKM.JK"]
    assert df.loc[df["ticker"] == "BBCA.JK", "name"].iloc[0] == "Bank Central Asia Tbk."


def test_fetch_idx_stock_list_accepts_bare_list_payload(monkeypatch):
    payload = [{"StockCode": "ASII", "StockName": "Astra International Tbk."}]
    monkeypatch.setattr("stock_forecast.idx_universe.requests.get", _fake_get(payload))

    df = fetch_idx_stock_list()

    assert list(df["ticker"]) == ["ASII.JK"]


def test_fetch_idx_stock_list_deduplicates_and_sorts(monkeypatch):
    payload = {
        "data": [
            {"Kode": "TLKM", "NamaEmiten": "Telkom Indonesia Tbk."},
            {"Kode": "AALI", "NamaEmiten": "Astra Agro Lestari Tbk."},
            {"Kode": "TLKM", "NamaEmiten": "Telkom Indonesia Tbk. (dup)"},
        ]
    }
    monkeypatch.setattr("stock_forecast.idx_universe.requests.get", _fake_get(payload))

    df = fetch_idx_stock_list()

    assert list(df["ticker"]) == ["AALI.JK", "TLKM.JK"]


def test_fetch_idx_stock_list_raises_on_unrecognized_shape(monkeypatch):
    monkeypatch.setattr("stock_forecast.idx_universe.requests.get", _fake_get({"unexpected": True}))

    with pytest.raises(IdxListingError, match="Unrecognized IDX API response shape"):
        fetch_idx_stock_list()


def test_fetch_idx_stock_list_raises_when_fields_unknown(monkeypatch):
    payload = {"data": [{"weird_field": "AALI"}]}
    monkeypatch.setattr("stock_forecast.idx_universe.requests.get", _fake_get(payload))

    with pytest.raises(IdxListingError, match="Could not find a ticker code field"):
        fetch_idx_stock_list()


def test_load_idx_universe_uses_and_writes_cache(monkeypatch, tmp_path):
    cache_path = tmp_path / "idx_stock_list.csv"
    monkeypatch.setattr("stock_forecast.idx_universe.CACHE_PATH", cache_path)

    payload = {"data": [{"Kode": "BBRI", "NamaEmiten": "Bank Rakyat Indonesia Tbk."}]}
    monkeypatch.setattr("stock_forecast.idx_universe.requests.get", _fake_get(payload))

    assert not cache_path.exists()
    df = load_idx_universe()
    assert cache_path.exists()
    assert list(df["ticker"]) == ["BBRI.JK"]

    # Cached read should not touch the network: break requests.get to prove it.
    def _boom(*a, **kw):
        raise AssertionError("network should not be hit when cache exists")

    monkeypatch.setattr("stock_forecast.idx_universe.requests.get", _boom)
    cached_df = load_idx_universe()
    pd.testing.assert_frame_equal(cached_df, df)


def test_load_idx_universe_refresh_bypasses_cache(monkeypatch, tmp_path):
    cache_path = tmp_path / "idx_stock_list.csv"
    monkeypatch.setattr("stock_forecast.idx_universe.CACHE_PATH", cache_path)

    old_payload = {"data": [{"Kode": "BBRI", "NamaEmiten": "Old Name"}]}
    monkeypatch.setattr("stock_forecast.idx_universe.requests.get", _fake_get(old_payload))
    load_idx_universe()

    new_payload = {"data": [{"Kode": "BBRI", "NamaEmiten": "New Name"}]}
    monkeypatch.setattr("stock_forecast.idx_universe.requests.get", _fake_get(new_payload))
    df = load_idx_universe(refresh=True)

    assert df["name"].iloc[0] == "New Name"
