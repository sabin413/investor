import pandas as pd
import pytest

from investor.data_sources import fundamentals


class FakeTicker:
    def __init__(self, info=None, history_df=None):
        self.info = info if info is not None else {}
        self._history_df = history_df if history_df is not None else pd.DataFrame()

    def history(self, period):
        return self._history_df


def test_get_fundamentals(monkeypatch):
    info = {
        "currentPrice": 150.0,
        "marketCap": 1_000_000,
        "trailingPE": 25.0,
        "fiftyTwoWeekHigh": 200.0,
        "fiftyTwoWeekLow": 100.0,
    }
    monkeypatch.setattr(fundamentals.yf, "Ticker", lambda ticker: FakeTicker(info=info))

    result = fundamentals.get_fundamentals("AAPL")

    assert result["ticker"] == "AAPL"
    assert result["price"] == 150.0
    assert result["market_cap"] == 1_000_000


def test_get_fundamentals_includes_analyst_growth_and_ownership_fields(monkeypatch):
    info = {
        "currentPrice": 150.0,
        "marketCap": 1_000_000,
        "trailingPE": 25.0,
        "fiftyTwoWeekHigh": 200.0,
        "fiftyTwoWeekLow": 100.0,
        "targetMeanPrice": 180.0,
        "targetMedianPrice": 175.0,
        "targetHighPrice": 220.0,
        "targetLowPrice": 140.0,
        "numberOfAnalystOpinions": 30,
        "recommendationKey": "buy",
        "recommendationMean": 2.1,
        "trailingPegRatio": 1.8,
        "debtToEquity": 45.0,
        "returnOnEquity": 0.35,
        "profitMargins": 0.25,
        "operatingMargins": 0.3,
        "freeCashflow": 5_000_000,
        "revenueGrowth": 0.12,
        "earningsGrowth": 0.2,
        "earningsQuarterlyGrowth": 0.18,
        "heldPercentInsiders": 0.02,
        "heldPercentInstitutions": 0.7,
        "shortPercentOfFloat": 0.01,
        "shortRatio": 1.5,
        "sharesShort": 1_000_000,
        "sharesShortPriorMonth": 1_200_000,
    }
    monkeypatch.setattr(fundamentals.yf, "Ticker", lambda ticker: FakeTicker(info=info))

    result = fundamentals.get_fundamentals("AAPL")

    assert result["target_mean_price"] == 180.0
    assert result["target_median_price"] == 175.0
    assert result["target_high_price"] == 220.0
    assert result["target_low_price"] == 140.0
    assert result["number_of_analyst_opinions"] == 30
    assert result["recommendation_key"] == "buy"
    assert result["recommendation_mean"] == 2.1
    assert result["peg_ratio"] == 1.8
    assert result["debt_to_equity"] == 45.0
    assert result["return_on_equity"] == 0.35
    assert result["profit_margins"] == 0.25
    assert result["operating_margins"] == 0.3
    assert result["free_cashflow"] == 5_000_000
    assert result["revenue_growth"] == 0.12
    assert result["earnings_growth"] == 0.2
    assert result["earnings_quarterly_growth"] == 0.18
    assert result["held_percent_insiders"] == 0.02
    assert result["held_percent_institutions"] == 0.7
    assert result["short_percent_of_float"] == 0.01
    assert result["short_ratio"] == 1.5
    assert result["shares_short"] == 1_000_000
    assert result["shares_short_prior_month"] == 1_200_000


def test_get_fundamentals_defaults_missing_optional_fields_to_none(monkeypatch):
    info = {"currentPrice": 150.0}
    monkeypatch.setattr(fundamentals.yf, "Ticker", lambda ticker: FakeTicker(info=info))

    result = fundamentals.get_fundamentals("AAPL")

    assert result["target_mean_price"] is None
    assert result["peg_ratio"] is None
    assert result["held_percent_institutions"] is None


def test_get_fundamentals_rejects_empty_info(monkeypatch):
    monkeypatch.setattr(fundamentals.yf, "Ticker", lambda ticker: FakeTicker(info={}))

    with pytest.raises(ValueError):
        fundamentals.get_fundamentals("BADTICKER")


def test_get_price_history(monkeypatch):
    df = pd.DataFrame({"Close": [1.0, 2.0, 3.0]})
    monkeypatch.setattr(fundamentals.yf, "Ticker", lambda ticker: FakeTicker(history_df=df))

    result = fundamentals.get_price_history("AAPL")

    assert list(result["Close"]) == [1.0, 2.0, 3.0]


def test_get_price_history_rejects_empty(monkeypatch):
    monkeypatch.setattr(fundamentals.yf, "Ticker", lambda ticker: FakeTicker(history_df=pd.DataFrame()))

    with pytest.raises(ValueError):
        fundamentals.get_price_history("BADTICKER")
