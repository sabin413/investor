# Stage 2 of the pipeline: narrows the whole tradeable universe (~1000
# tickers) down to 50 candidates worth researching in depth.
#
# Two steps:
#   1. Mechanical technical shortlist (1000 -> PRESCREEN_COUNT): pure Python,
#      trend-confirmed (price above SMA50) and ranked by risk-adjusted
#      momentum. No Claude judgment involved yet.
#   2. Claude's judgment (PRESCREEN_COUNT -> FINAL_COUNT): Claude sees the
#      full technical field set for the shortlist and picks the FINAL_COUNT
#      it judges best, weighing multiple factors rather than any single one.

import json
import re

import yfinance as yf
from anthropic import Anthropic, beta_tool

from investor.agents.macro_agent import EFFORT, MODEL
from investor.data_sources.technicals import summarize as summarize_technicals
from investor.data_sources.universe import get_universe

PRESCREEN_COUNT = 200
FINAL_COUNT = 50

SYSTEM_PROMPT = f"""You are a stock screener for an aggressive-but-sensible
retail investor. You will be given today's macro thesis and a tool that
returns a technically-shortlisted pool of {PRESCREEN_COUNT} candidate stocks:
tickers already confirmed to be trading above their 50-day SMA and ranked by
risk-adjusted momentum (1-month momentum divided by annualized volatility).
For each candidate you'll see price, SMA20, SMA50, RSI14, 1-month momentum,
3-month momentum, volatility, risk-adjusted momentum, and average dollar
volume.

Pick the {FINAL_COUNT} most interesting candidates for further research.
This is your own judgment call, not a request to re-sort by any single field
you're given - weigh momentum (1-month and 3-month) together with trend
strength (how price relates to SMA20/SMA50), RSI (avoid chasing names that
are extremely overbought), liquidity (avg_dollar_volume - avoid illiquid
names), and the macro backdrop. For each, give a one-line reason grounded
only in the data you were given - don't invent data.

Respond with ONLY a JSON array (no other text) of exactly {FINAL_COUNT}
objects, each with keys "ticker" and "reason"."""


def _in_uptrend(stats: dict) -> bool:
    """True if price is above its 50-day SMA (confirmed uptrend, not just a
    recent spike against the broader trend)."""
    return stats["price"] > stats["sma_50"]


def _score_universe(tickers: list[str]) -> list[dict]:
    """Bulk-fetch price history, keep only tickers in a confirmed uptrend,
    and rank survivors by risk-adjusted momentum."""
    # Bulk download (not one call per ticker) to keep this fast across ~1000 tickers.
    data = yf.download(tickers, period="3mo", group_by="ticker", threads=True, progress=False)

    scored = []
    for ticker in tickers:
        try:
            history = data[ticker].dropna()
            stats = summarize_technicals(history)
        except Exception:
            # Missing/incomplete history for a ticker just drops it from screening.
            continue
        scored.append({"ticker": ticker, **stats})

    # Trend-confirmation gate: excludes tickers trading below their own
    # 50-day SMA. If a broad downturn filters everyone out, this returns []
    # and _parse_candidates raises downstream (wrong candidate count) rather
    # than silently proceeding with no real data.
    scored = [s for s in scored if _in_uptrend(s)]
    scored.sort(key=lambda s: s["risk_adjusted_momentum"], reverse=True)
    return scored


def _prescreen_shortlist(limit: int = PRESCREEN_COUNT) -> list[dict]:
    """Trend-confirmed candidates ranked by risk-adjusted momentum, truncated to `limit`."""
    return _score_universe(get_universe())[:limit]


def _parse_candidates(text: str) -> list[dict]:
    # Claude is asked for JSON-only, but defensively extract the array in
    # case it wraps the response in prose or markdown fences.
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError(f"screener agent did not return a JSON array: {text!r}")

    candidates = json.loads(match.group())
    if len(candidates) != FINAL_COUNT:
        raise ValueError(f"expected {FINAL_COUNT} candidates, got {len(candidates)}")
    for candidate in candidates:
        if "ticker" not in candidate or "reason" not in candidate:
            raise ValueError(f"candidate missing ticker/reason: {candidate!r}")

    return candidates


@beta_tool
def prescreen_candidates() -> str:
    """Fetch a technically-shortlisted pool of candidate stocks from the
    tradeable universe (S&P 500 + top small caps). Tickers are first filtered
    to those in a confirmed uptrend (price above their 50-day SMA), then
    ranked by risk-adjusted momentum (1-month momentum divided by annualized
    volatility). Returns price, SMA20, SMA50, RSI14, 1-month momentum,
    3-month momentum, volatility, risk-adjusted momentum, and average dollar
    volume for each candidate.
    """
    return json.dumps(_prescreen_shortlist())


def run_screener_agent(macro_thesis: str) -> list[dict]:
    client = Anthropic()
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        # FINAL_COUNT (50) candidates each with a one-line reason needs more
        # room than the old FINAL_COUNT=10 did.
        max_tokens=10000,
        output_config={"effort": EFFORT},
        system=SYSTEM_PROMPT,
        tools=[prescreen_candidates],
        messages=[
            {
                "role": "user",
                "content": f"Today's macro thesis:\n\n{macro_thesis}\n\nPick candidates.",
            }
        ],
    )

    final_message = None
    for message in runner:
        final_message = message

    text = "".join(block.text for block in final_message.content if block.type == "text")
    return _parse_candidates(text)
