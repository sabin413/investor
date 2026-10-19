import json

import pytest

from investor.agents import portfolio_agent
from investor.portfolio.models import Portfolio, Position


def test_portfolio_snapshot_computes_pct_of_total(monkeypatch):
    monkeypatch.setattr(portfolio_agent, "get_fundamentals", lambda t: {"price": 100.0})
    monkeypatch.setattr(portfolio_agent, "get_crypto_price", lambda t: 50_000.0)
    monkeypatch.setattr(portfolio_agent, "research_ticker", lambda t: {})

    portfolio = Portfolio(
        positions=[
            Position(ticker="AAPL", quantity=10, asset_class="equity"),
            Position(ticker="BTC", quantity=0.02, asset_class="crypto"),
        ]
    )

    snapshot = portfolio_agent.portfolio_snapshot(portfolio)

    assert snapshot["AAPL"]["value"] == 1000.0
    assert snapshot["BTC"]["value"] == 1000.0
    assert snapshot["AAPL"]["pct_of_portfolio"] == pytest.approx(0.5)
    assert snapshot["BTC"]["pct_of_portfolio"] == pytest.approx(0.5)


def test_portfolio_snapshot_enriches_equity_holdings_with_research(monkeypatch):
    monkeypatch.setattr(portfolio_agent, "get_fundamentals", lambda t: {"price": 100.0})
    monkeypatch.setattr(
        portfolio_agent,
        "research_ticker",
        lambda t: {"technicals": {"rsi_14": 55.0}, "sentiment": {"bullish": 5, "bearish": 1}},
    )

    portfolio = Portfolio(positions=[Position(ticker="AAPL", quantity=10, asset_class="equity")])

    snapshot = portfolio_agent.portfolio_snapshot(portfolio)

    assert snapshot["AAPL"]["technicals"] == {"rsi_14": 55.0}
    assert snapshot["AAPL"]["sentiment"] == {"bullish": 5, "bearish": 1}


def test_portfolio_snapshot_skips_research_for_crypto(monkeypatch):
    monkeypatch.setattr(portfolio_agent, "get_crypto_price", lambda t: 50_000.0)
    calls = []
    monkeypatch.setattr(portfolio_agent, "research_ticker", lambda t: calls.append(t) or {})

    portfolio = Portfolio(positions=[Position(ticker="BTC", quantity=0.02, asset_class="crypto")])

    snapshot = portfolio_agent.portfolio_snapshot(portfolio)

    assert calls == []
    assert "technicals" not in snapshot["BTC"]


def test_portfolio_snapshot_records_price_lookup_failure(monkeypatch):
    monkeypatch.setattr(
        portfolio_agent,
        "get_fundamentals",
        lambda t: (_ for _ in ()).throw(ValueError("no data")),
    )

    portfolio = Portfolio(positions=[Position(ticker="BADTICKER", quantity=1, asset_class="equity")])

    snapshot = portfolio_agent.portfolio_snapshot(portfolio)

    assert "error" in snapshot["BADTICKER"]


def test_enrich_candidates_attaches_research(monkeypatch):
    monkeypatch.setattr(
        portfolio_agent,
        "research_ticker",
        lambda t: {"technicals": {"rsi_14": 60.0}, "fundamentals": {"pe_ratio": 20.0}},
    )
    candidates = [{"ticker": "SMCI", "timeframe": "short_term", "reason": "momentum"}]

    enriched = portfolio_agent._enrich_candidates(candidates)

    assert enriched[0]["ticker"] == "SMCI"
    assert enriched[0]["timeframe"] == "short_term"
    assert enriched[0]["reason"] == "momentum"
    assert enriched[0]["technicals"] == {"rsi_14": 60.0}
    assert enriched[0]["fundamentals"] == {"pe_ratio": 20.0}


def test_enrich_candidates_researches_each_ticker_independently(monkeypatch):
    calls = []
    monkeypatch.setattr(
        portfolio_agent,
        "research_ticker",
        lambda t: calls.append(t) or {"fundamentals": {"pe_ratio": 1.0}},
    )
    candidates = [
        {"ticker": "AAA", "timeframe": "short_term", "reason": "x"},
        {"ticker": "BBB", "timeframe": "medium_term", "reason": "y"},
    ]

    portfolio_agent._enrich_candidates(candidates)

    assert calls == ["AAA", "BBB"]


def test_apply_risk_guardrail_blocks_oversized_buy(monkeypatch):
    monkeypatch.setattr(portfolio_agent, "MAX_SINGLE_POSITION_PCT", 0.20)
    snapshot = {"AAPL": {"pct_of_portfolio": 0.25}}
    actions = [{"ticker": "AAPL", "action": "buy", "reason": "strong momentum"}]

    checked = portfolio_agent.apply_risk_guardrail(actions, snapshot)

    assert checked[0]["action"] == "hold"
    assert "risk guardrail" in checked[0]["reason"]
    assert "strong momentum" in checked[0]["reason"]


def test_apply_risk_guardrail_allows_buy_under_cap(monkeypatch):
    monkeypatch.setattr(portfolio_agent, "MAX_SINGLE_POSITION_PCT", 0.20)
    snapshot = {"AAPL": {"pct_of_portfolio": 0.05}}
    actions = [{"ticker": "AAPL", "action": "buy", "reason": "strong momentum"}]

    checked = portfolio_agent.apply_risk_guardrail(actions, snapshot)

    assert checked[0]["action"] == "buy"


def test_apply_risk_guardrail_allows_first_buy_of_new_ticker(monkeypatch):
    monkeypatch.setattr(portfolio_agent, "MAX_SINGLE_POSITION_PCT", 0.20)
    actions = [{"ticker": "NEWCO", "action": "buy", "reason": "new candidate"}]

    checked = portfolio_agent.apply_risk_guardrail(actions, snapshot={})

    assert checked[0]["action"] == "buy"


def test_apply_risk_guardrail_leaves_non_buy_actions_untouched(monkeypatch):
    monkeypatch.setattr(portfolio_agent, "MAX_SINGLE_POSITION_PCT", 0.20)
    snapshot = {"AAPL": {"pct_of_portfolio": 0.90}}
    actions = [{"ticker": "AAPL", "action": "sell", "reason": "overweight"}]

    checked = portfolio_agent.apply_risk_guardrail(actions, snapshot)

    assert checked[0]["action"] == "sell"


def test_parse_actions_happy_path():
    text = json.dumps([{"ticker": "AAPL", "action": "hold", "reason": "steady"}])

    actions = portfolio_agent._parse_actions(text)

    assert actions == [{"ticker": "AAPL", "action": "hold", "reason": "steady"}]


def test_parse_actions_rejects_invalid_action():
    text = json.dumps([{"ticker": "AAPL", "action": "yolo", "reason": "steady"}])

    with pytest.raises(ValueError):
        portfolio_agent._parse_actions(text)


def test_parse_actions_rejects_missing_keys():
    text = json.dumps([{"ticker": "AAPL", "action": "hold"}])

    with pytest.raises(ValueError):
        portfolio_agent._parse_actions(text)


def test_parse_actions_rejects_non_json():
    with pytest.raises(ValueError):
        portfolio_agent._parse_actions("no json here")


def test_validate_against_membership_rejects_sell_on_non_holding():
    snapshot = {"AAPL": {"pct_of_portfolio": 0.5}}
    candidates = [{"ticker": "SMCI"}]
    actions = [
        {"ticker": "AAPL", "action": "hold", "reason": "steady"},
        {"ticker": "SMCI", "action": "sell", "reason": "hallucinated holding"},
    ]

    with pytest.raises(ValueError, match="not a current holding"):
        portfolio_agent._validate_against_membership(actions, snapshot, candidates)


def test_validate_against_membership_rejects_buy_on_existing_holding():
    snapshot = {"AAPL": {"pct_of_portfolio": 0.5}}
    actions = [{"ticker": "AAPL", "action": "buy", "reason": "add more"}]

    with pytest.raises(ValueError, match="current holding"):
        portfolio_agent._validate_against_membership(actions, snapshot, [])


def test_validate_against_membership_rejects_missing_holding_decision():
    snapshot = {"AAPL": {"pct_of_portfolio": 0.5}, "BBAI": {"pct_of_portfolio": 0.01}}
    actions = [{"ticker": "AAPL", "action": "hold", "reason": "steady"}]

    with pytest.raises(ValueError, match="BBAI"):
        portfolio_agent._validate_against_membership(actions, snapshot, [])


def test_validate_against_membership_rejects_unknown_ticker():
    actions = [{"ticker": "GHOST", "action": "buy", "reason": "made up"}]

    with pytest.raises(ValueError, match="neither a current holding nor a researched candidate"):
        portfolio_agent._validate_against_membership(actions, {}, [])


def test_validate_against_membership_allows_correct_decisions():
    snapshot = {"AAPL": {"pct_of_portfolio": 0.5}}
    candidates = [{"ticker": "SMCI"}]
    actions = [
        {"ticker": "AAPL", "action": "sell", "reason": "overweight"},
        {"ticker": "SMCI", "action": "buy", "reason": "strong momentum"},
    ]

    portfolio_agent._validate_against_membership(actions, snapshot, candidates)
