import pandas as pd
import pytest

from stock_forecast.data import fetch_ohlc, normalize_idx_ticker


def _fake_yf_frame():
    dates = pd.date_range("2024-01-01", periods=5, freq="B")
    return pd.DataFrame(
        {
            "Open": [100, 101, 102, 103, 104],
            "High": [101, 102, 103, 104, 105],
            "Low": [99, 100, 101, 102, 103],
            "Close": [100.5, 101.5, 102.5, 103.5, 104.5],
            "Volume": [1000, 1100, 1200, 1300, 1400],
        },
        index=dates,
    )


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("bbca", "BBCA.JK"),
        ("BBCA", "BBCA.JK"),
        (" bbca ", "BBCA.JK"),
        ("BBCA.JK", "BBCA.JK"),
        ("bbca.jk", "BBCA.JK"),
    ],
)
def test_normalize_idx_ticker(raw, expected):
    assert normalize_idx_ticker(raw) == expected


def test_fetch_ohlc_normalizes_columns_and_ticker(monkeypatch):
    captured = {}

    def fake_download(symbol, **kwargs):
        captured["symbol"] = symbol
        return _fake_yf_frame()

    monkeypatch.setattr("stock_forecast.data.yf.download", fake_download)

    df = fetch_ohlc("bbca", period="1y", interval="1d")

    assert captured["symbol"] == "BBCA.JK"
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert df.index.name == "date"
    assert df.index.is_monotonic_increasing
    assert len(df) == 5


def test_fetch_ohlc_raises_on_empty_response(monkeypatch):
    monkeypatch.setattr("stock_forecast.data.yf.download", lambda symbol, **kwargs: pd.DataFrame())

    with pytest.raises(ValueError, match="No data returned"):
        fetch_ohlc("NOSUCHTICKER")


def test_fetch_ohlc_flattens_multiindex_columns(monkeypatch):
    frame = _fake_yf_frame()
    frame.columns = pd.MultiIndex.from_product([frame.columns, ["BBCA.JK"]])
    monkeypatch.setattr("stock_forecast.data.yf.download", lambda symbol, **kwargs: frame)

    df = fetch_ohlc("BBCA")

    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
