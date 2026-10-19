import pandas as pd
import pytest

from investor.data_sources.technicals import summarize


def _price_history(closes, volumes=None):
    if volumes is None:
        volumes = [1_000_000] * len(closes)
    return pd.DataFrame({"Close": closes, "Volume": volumes})


def test_summarize_returns_expected_keys():
    closes = [100 + i * 0.5 for i in range(60)]
    result = summarize(_price_history(closes))

    assert set(result) == {
        "price",
        "sma_20",
        "sma_50",
        "rsi_14",
        "momentum_1mo_pct",
        "momentum_3mo_pct",
        "volatility",
        "risk_adjusted_momentum",
        "avg_dollar_volume",
    }
    assert result["price"] == closes[-1]


def test_summarize_momentum_3mo_pct_is_total_return():
    closes = [100 + i for i in range(60)]
    result = summarize(_price_history(closes))

    expected = (closes[-1] - closes[0]) / closes[0] * 100
    assert result["momentum_3mo_pct"] == pytest.approx(expected)


def test_summarize_volatility_higher_for_choppy_series():
    smooth = [100 + i for i in range(60)]
    choppy = [100 + i + (8 if i % 2 == 0 else -8) for i in range(60)]

    smooth_result = summarize(_price_history(smooth))
    choppy_result = summarize(_price_history(choppy))

    assert choppy_result["volatility"] > smooth_result["volatility"]


def test_summarize_risk_adjusted_momentum_is_momentum_over_volatility():
    closes = [100 + i for i in range(60)]
    result = summarize(_price_history(closes))

    assert result["volatility"] > 0
    assert result["risk_adjusted_momentum"] == pytest.approx(
        result["momentum_1mo_pct"] / result["volatility"]
    )


def test_summarize_risk_adjusted_momentum_handles_zero_volatility():
    closes = [100.0] * 60

    result = summarize(_price_history(closes))

    assert result["volatility"] == pytest.approx(0)
    assert result["risk_adjusted_momentum"] == pytest.approx(0)


def test_summarize_avg_dollar_volume():
    closes = [100 + i for i in range(60)]
    volumes = [1000 + i * 10 for i in range(60)]

    result = summarize(_price_history(closes, volumes))

    expected = sum(c * v for c, v in zip(closes, volumes)) / len(closes)
    assert result["avg_dollar_volume"] == pytest.approx(expected)


def test_summarize_rsi_high_for_steady_uptrend():
    closes = [100 + i for i in range(60)]
    result = summarize(_price_history(closes))

    assert result["rsi_14"] > 90


def test_summarize_rsi_low_for_steady_downtrend():
    closes = [200 - i for i in range(60)]
    result = summarize(_price_history(closes))

    assert result["rsi_14"] < 10


def test_summarize_rejects_insufficient_history():
    closes = [100 + i for i in range(10)]

    with pytest.raises(ValueError):
        summarize(_price_history(closes))
