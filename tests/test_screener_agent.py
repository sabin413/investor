import json

import pandas as pd
import pytest

from investor.agents import screener_agent


def _bulk_data(prices_by_ticker, volumes_by_ticker=None):
    volumes_by_ticker = volumes_by_ticker or {}
    frames = {}
    for ticker, closes in prices_by_ticker.items():
        volumes = volumes_by_ticker.get(ticker, [1_000_000] * len(closes))
        frames[ticker] = pd.DataFrame({"Close": closes, "Volume": volumes})
    return pd.concat(frames, axis=1)


def test_score_universe_filters_out_tickers_below_sma50(monkeypatch):
    rising = [100 + i for i in range(60)]
    falling = [200 - i for i in range(60)]

    monkeypatch.setattr(
        screener_agent.yf,
        "download",
        lambda tickers, **kwargs: _bulk_data({"UP": rising, "DOWN": falling}),
    )

    scored = screener_agent._score_universe(["UP", "DOWN"])

    # DOWN is excluded entirely (below its own SMA50), not just ranked lower.
    assert [s["ticker"] for s in scored] == ["UP"]


def test_score_universe_ranks_survivors_by_risk_adjusted_momentum_descending(monkeypatch):
    # Both series end above their own SMA50 (pass the trend gate). VOLATILE
    # has slightly higher raw 1-month momentum than STEADY, but its
    # alternating swings give it much higher volatility - so ranking by
    # risk-adjusted momentum (not raw momentum) puts STEADY first.
    steady = [100 + i for i in range(60)]
    volatile = [100 + 3.0 * i + (12 if i % 2 == 0 else -12) for i in range(60)]

    monkeypatch.setattr(
        screener_agent.yf,
        "download",
        lambda tickers, **kwargs: _bulk_data({"STEADY": steady, "VOLATILE": volatile}),
    )

    scored = screener_agent._score_universe(["STEADY", "VOLATILE"])

    assert [s["ticker"] for s in scored] == ["STEADY", "VOLATILE"]
    # Raw momentum does NOT favor STEADY - proves this isn't just re-deriving
    # the old momentum-only ordering.
    steady_stats, volatile_stats = scored[0], scored[1]
    assert steady_stats["momentum_1mo_pct"] <= volatile_stats["momentum_1mo_pct"]
    assert steady_stats["risk_adjusted_momentum"] > volatile_stats["risk_adjusted_momentum"]


def test_score_universe_returns_empty_list_when_all_below_sma50(monkeypatch):
    falling_a = [200 - i for i in range(60)]
    falling_b = [150 - 0.5 * i for i in range(60)]

    monkeypatch.setattr(
        screener_agent.yf,
        "download",
        lambda tickers, **kwargs: _bulk_data({"A": falling_a, "B": falling_b}),
    )

    scored = screener_agent._score_universe(["A", "B"])

    assert scored == []


def test_score_universe_skips_tickers_with_missing_data(monkeypatch):
    rising = [100 + i for i in range(60)]

    monkeypatch.setattr(
        screener_agent.yf,
        "download",
        lambda tickers, **kwargs: _bulk_data({"GOOD": rising}),
    )

    scored = screener_agent._score_universe(["GOOD", "MISSING"])

    assert [s["ticker"] for s in scored] == ["GOOD"]


def test_prescreen_count_is_200():
    assert screener_agent.PRESCREEN_COUNT == 200


def _candidate_json(count):
    return json.dumps([{"ticker": f"T{i}", "reason": "because"} for i in range(count)])


def test_parse_candidates_happy_path():
    text = _candidate_json(screener_agent.FINAL_COUNT)

    candidates = screener_agent._parse_candidates(text)

    assert len(candidates) == screener_agent.FINAL_COUNT
    assert candidates[0] == {"ticker": "T0", "reason": "because"}


def test_parse_candidates_extracts_json_from_surrounding_text():
    text = f"Here you go:\n{_candidate_json(screener_agent.FINAL_COUNT)}\nHope that helps."

    candidates = screener_agent._parse_candidates(text)

    assert len(candidates) == screener_agent.FINAL_COUNT


def test_parse_candidates_rejects_wrong_count():
    with pytest.raises(ValueError):
        screener_agent._parse_candidates(_candidate_json(screener_agent.FINAL_COUNT - 1))


def test_parse_candidates_rejects_missing_keys():
    text = json.dumps([{"ticker": "T0"}] * screener_agent.FINAL_COUNT)

    with pytest.raises(ValueError):
        screener_agent._parse_candidates(text)


def test_parse_candidates_rejects_non_json():
    with pytest.raises(ValueError):
        screener_agent._parse_candidates("no json here")
