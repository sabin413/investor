# Stage 4 of the pipeline: reconciles the deep-dive picks against the user's
# actual holdings and decides hold/sell/buy/pass for each ticker involved.

import json
import re

from anthropic import Anthropic

from investor.agents.deep_dive_agent import research_ticker
from investor.agents.macro_agent import EFFORT, MODEL
from investor.config import MAX_SINGLE_POSITION_PCT
from investor.data_sources.crypto import get_crypto_price
from investor.data_sources.fundamentals import get_fundamentals
from investor.portfolio.models import Portfolio

VALID_ACTIONS = {"buy", "sell", "hold", "pass"}

SYSTEM_PROMPT = """You are a portfolio manager for an aggressive-but-sensible
retail investor. You will be given the current portfolio, today's macro
thesis, and researched candidate stocks. Every equity holding and candidate
comes with the same fundamentals/sentiment/technicals data (P/E, market cap,
52-week range, SMA20/50, RSI14, 1-month momentum, StockTwits bull/bear
counts) - crypto holdings only have a price, since that data isn't
available for them. For each existing holding, decide "hold" or "sell". For
each candidate not currently held, decide "buy" or "pass". Do full technical
and fundamental analysis on every holding before deciding, the way an
experienced investor would - don't just re-state the macro thesis, engage
with that ticker's own P/E, RSI, moving averages, momentum, and sentiment
before calling for a sell or a hold. Keep each reason to 2-3 sentences.
Ground every decision in the data you were given - don't invent numbers.

Respond with ONLY a JSON array (no other text), one object per ticker you
address, each with keys "ticker", "action" (one of "buy", "sell", "hold",
"pass"), and "reason"."""


def _current_price(ticker: str, asset_class: str) -> float:
    if asset_class == "crypto":
        return get_crypto_price(ticker)
    return get_fundamentals(ticker)["price"]


def portfolio_snapshot(portfolio: Portfolio) -> dict:
    """Fetch current prices, full research (for equities), and each
    position's % of total portfolio value."""
    values = {}
    for position in portfolio.positions:
        try:
            price = _current_price(position.ticker, position.asset_class)
        except Exception as e:
            values[position.ticker] = {"error": str(e)}
            continue
        entry = {
            "price": price,
            "quantity": position.quantity,
            "value": price * position.quantity,
        }
        if position.asset_class == "equity":
            # Crypto skips this: no fundamentals/sentiment/technicals data available.
            entry.update(research_ticker(position.ticker))
        values[position.ticker] = entry

    total = sum(v["value"] for v in values.values() if "value" in v)
    for value in values.values():
        if "value" in value:
            value["pct_of_portfolio"] = value["value"] / total if total else 0.0

    return values


def _enrich_candidates(candidates: list[dict]) -> list[dict]:
    """Attach full fundamentals/sentiment/technicals research to each
    deep-dive candidate, mirroring what portfolio_snapshot() already attaches
    to existing equity holdings - otherwise buy/pass decisions would be made
    on far less data than hold/sell decisions."""
    enriched = []
    for candidate in candidates:
        entry = {**candidate, **research_ticker(candidate["ticker"])}
        enriched.append(entry)
    return enriched


def _parse_actions(text: str) -> list[dict]:
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError(f"portfolio agent did not return a JSON array: {text!r}")

    actions = json.loads(match.group())
    for action in actions:
        if "ticker" not in action or "action" not in action or "reason" not in action:
            raise ValueError(f"action missing required keys: {action!r}")
        if action["action"] not in VALID_ACTIONS:
            raise ValueError(f"invalid action {action['action']!r} for {action['ticker']!r}")

    return actions


def _validate_against_membership(actions: list[dict], snapshot: dict, candidates: list[dict]) -> None:
    """Ensure hold/sell only target current holdings and buy/pass only target
    researched candidates, and that every current holding got a decision."""
    snapshot_tickers = {t.upper() for t in snapshot}
    candidate_tickers = {c["ticker"].upper() for c in candidates}

    seen = set()
    for action in actions:
        ticker = action["ticker"].upper()
        seen.add(ticker)
        if ticker in snapshot_tickers:
            if action["action"] not in ("hold", "sell"):
                raise ValueError(
                    f"{ticker} is a current holding; action must be hold/sell, "
                    f"got {action['action']!r}"
                )
        elif ticker in candidate_tickers:
            if action["action"] not in ("buy", "pass"):
                raise ValueError(
                    f"{ticker} is a candidate, not a current holding; action must "
                    f"be buy/pass, got {action['action']!r}"
                )
        else:
            raise ValueError(
                f"{ticker} is neither a current holding nor a researched candidate"
            )

    missing = snapshot_tickers - seen
    if missing:
        raise ValueError(f"missing hold/sell decision for current holdings: {sorted(missing)}")


def apply_risk_guardrail(actions: list[dict], snapshot: dict) -> list[dict]:
    """Block a 'buy' for any ticker already at/above MAX_SINGLE_POSITION_PCT."""
    checked = []
    for action in actions:
        pct = snapshot.get(action["ticker"], {}).get("pct_of_portfolio", 0.0)
        if action["action"] == "buy" and pct >= MAX_SINGLE_POSITION_PCT:
            # Downgrade rather than drop the action, so the report still
            # explains why a candidate the model wanted to buy was blocked.
            action = {
                **action,
                "action": "hold",
                "reason": (
                    f"Blocked by risk guardrail: {action['ticker']} is already "
                    f"{pct:.0%} of the portfolio (cap {MAX_SINGLE_POSITION_PCT:.0%}). "
                    f"Original suggestion: {action['reason']}"
                ),
            }
        checked.append(action)
    return checked


def run_portfolio_agent(macro_thesis: str, candidates: list[dict], portfolio: Portfolio) -> list[dict]:
    snapshot = portfolio_snapshot(portfolio)
    researched_candidates = _enrich_candidates(candidates)

    user_message = (
        f"Today's macro thesis:\n\n{macro_thesis}\n\n"
        f"Current portfolio:\n{json.dumps(snapshot, default=str)}\n\n"
        f"Researched candidates:\n{json.dumps(researched_candidates, default=str)}\n\n"
        "Decide actions."
    )

    client = Anthropic()
    # No tools here (unlike the other stages): all research is fetched
    # up-front into the prompt, so this is a single non-agentic call.
    response = client.messages.create(
        model=MODEL,
        # Higher than the other stages' max_tokens: a full portfolio plus up
        # to 10 researched candidates means many detailed per-ticker
        # decisions in one response.
        max_tokens=8000,
        output_config={"effort": EFFORT},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    text = "".join(block.text for block in response.content if block.type == "text")
    actions = _parse_actions(text)
    _validate_against_membership(actions, snapshot, candidates)
    return apply_risk_guardrail(actions, snapshot)
