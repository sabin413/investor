import json

import pytest

from investor.agents import deep_dive_agent


def _picks(short_term_count, medium_term_count):
    picks = []
    for i in range(short_term_count):
        picks.append({"ticker": f"S{i}", "timeframe": "short_term", "reason": "because"})
    for i in range(medium_term_count):
        picks.append({"ticker": f"M{i}", "timeframe": "medium_term", "reason": "because"})
    return json.dumps(picks)


def test_parse_picks_happy_path():
    short_count = deep_dive_agent.SHORT_TERM_COUNT
    medium_count = deep_dive_agent.MEDIUM_TERM_COUNT

    picks = deep_dive_agent._parse_picks(_picks(short_count, medium_count))

    assert len(picks) == deep_dive_agent.FINAL_COUNT
    assert sum(p["timeframe"] == "short_term" for p in picks) == short_count
    assert sum(p["timeframe"] == "medium_term" for p in picks) == medium_count


def test_parse_picks_extracts_json_from_surrounding_text():
    text = f"Here are my picks:\n{_picks(deep_dive_agent.SHORT_TERM_COUNT, deep_dive_agent.MEDIUM_TERM_COUNT)}\nDone."

    assert len(deep_dive_agent._parse_picks(text)) == deep_dive_agent.FINAL_COUNT


def test_parse_picks_rejects_wrong_timeframe_split():
    # Right total count, wrong composition (all short-term, none medium-term).
    with pytest.raises(ValueError):
        deep_dive_agent._parse_picks(_picks(deep_dive_agent.FINAL_COUNT, 0))


def test_parse_picks_rejects_wrong_count():
    with pytest.raises(ValueError):
        deep_dive_agent._parse_picks(_picks(1, 1))


def test_parse_picks_rejects_invalid_timeframe():
    # Exactly FINAL_COUNT entries so it clears the count check, but the last
    # one has an invalid timeframe value.
    picks = [
        {"ticker": f"S{i}", "timeframe": "short_term", "reason": "x"}
        for i in range(deep_dive_agent.SHORT_TERM_COUNT - 1)
    ]
    picks += [
        {"ticker": f"M{i}", "timeframe": "medium_term", "reason": "x"}
        for i in range(deep_dive_agent.MEDIUM_TERM_COUNT)
    ]
    picks.append({"ticker": "BAD", "timeframe": "long_term", "reason": "x"})
    text = json.dumps(picks)

    with pytest.raises(ValueError):
        deep_dive_agent._parse_picks(text)


def test_research_ticker_survives_partial_source_failure(monkeypatch):
    monkeypatch.setattr(deep_dive_agent, "get_fundamentals", lambda t: {"price": 100})
    monkeypatch.setattr(
        deep_dive_agent,
        "get_sentiment",
        lambda t: (_ for _ in ()).throw(RuntimeError("stocktwits down")),
    )
    monkeypatch.setattr(deep_dive_agent, "get_price_history", lambda t: object())
    monkeypatch.setattr(deep_dive_agent, "summarize_technicals", lambda h: {"rsi_14": 50})

    result = deep_dive_agent.research_ticker("AAPL")

    assert result["fundamentals"] == {"price": 100}
    assert "sentiment_error" in result
    assert result["technicals"] == {"rsi_14": 50}
