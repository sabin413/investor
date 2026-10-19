# Stage 3 of the pipeline: researches each of the 50 screener candidates in
# depth (fundamentals + sentiment + technicals) and narrows to 10 final picks.

import json
import re

from anthropic import Anthropic, beta_tool

from investor.agents.macro_agent import EFFORT, MODEL
from investor.data_sources.fundamentals import get_fundamentals, get_price_history
from investor.data_sources.sentiment import get_sentiment
from investor.data_sources.technicals import summarize as summarize_technicals

SHORT_TERM = "short_term"
MEDIUM_TERM = "medium_term"

# FINAL_COUNT is derived from these so the two can't drift out of sync.
SHORT_TERM_COUNT = 5
MEDIUM_TERM_COUNT = 5
FINAL_COUNT = SHORT_TERM_COUNT + MEDIUM_TERM_COUNT

SYSTEM_PROMPT = f"""You are conducting deep-dive research for an
aggressive-but-sensible retail investor. You will be given today's macro
thesis and a shortlist of candidate tickers from an initial technical screen.
Call the research tool once for EACH candidate to pull fundamentals,
sentiment, and technicals, then pick your final {FINAL_COUNT}: exactly
{SHORT_TERM_COUNT} with high probability of an upturn in a "days to 1 month"
timeframe, and exactly {MEDIUM_TERM_COUNT} with high probability of an
upturn in a "1 month to a few months" timeframe. Ground every pick in the
actual data you pulled - don't invent numbers.

Respond with ONLY a JSON array (no other text) of exactly {FINAL_COUNT}
objects, each with keys "ticker", "timeframe" (either "{SHORT_TERM}" or
"{MEDIUM_TERM}"), and "reason"."""


def research_ticker(ticker: str) -> dict:
    # Shared by the deep-dive tool and portfolio_agent's snapshot of existing
    # holdings, so both stages score tickers on the same data. Each data
    # source fails independently so a single missing feed (e.g. no
    # StockTwits coverage) doesn't block the rest.
    result = {}
    try:
        result["fundamentals"] = get_fundamentals(ticker)
    except Exception as e:
        result["fundamentals_error"] = str(e)
    try:
        result["sentiment"] = get_sentiment(ticker)
    except Exception as e:
        result["sentiment_error"] = str(e)
    try:
        result["technicals"] = summarize_technicals(get_price_history(ticker))
    except Exception as e:
        result["technicals_error"] = str(e)
    return result


def _parse_picks(text: str) -> list[dict]:
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError(f"deep-dive agent did not return a JSON array: {text!r}")

    picks = json.loads(match.group())
    if len(picks) != FINAL_COUNT:
        raise ValueError(f"expected {FINAL_COUNT} picks, got {len(picks)}")

    for pick in picks:
        if "ticker" not in pick or "timeframe" not in pick or "reason" not in pick:
            raise ValueError(f"pick missing required keys: {pick!r}")
        if pick["timeframe"] not in (SHORT_TERM, MEDIUM_TERM):
            raise ValueError(f"invalid timeframe {pick['timeframe']!r} for {pick['ticker']!r}")

    # Enforce the exact short-term/medium-term split the prompt asks for.
    short_term = [p for p in picks if p["timeframe"] == SHORT_TERM]
    medium_term = [p for p in picks if p["timeframe"] == MEDIUM_TERM]
    if len(short_term) != SHORT_TERM_COUNT or len(medium_term) != MEDIUM_TERM_COUNT:
        raise ValueError(
            f"expected {SHORT_TERM_COUNT} short_term + {MEDIUM_TERM_COUNT} medium_term picks, got "
            f"{len(short_term)} short_term and {len(medium_term)} medium_term"
        )

    return picks


@beta_tool
def research_candidate(ticker: str) -> str:
    """Fetch fundamentals, sentiment, and technicals for one candidate stock.
    Fundamentals include price, market cap, PE/PEG ratios, 52-week range,
    analyst price targets and consensus rating, growth/profitability metrics
    (revenue/earnings growth, margins, ROE, debt/equity, free cash flow), and
    ownership/positioning data (insider/institutional holdings, short interest).

    Args:
        ticker: The stock ticker to research, e.g. AAPL.
    """
    return json.dumps(research_ticker(ticker))


def run_deep_dive_agent(macro_thesis: str, candidates: list[dict]) -> list[dict]:
    client = Anthropic()
    user_message = (
        f"Today's macro thesis:\n\n{macro_thesis}\n\n"
        f"Candidates from the screener:\n{json.dumps(candidates)}\n\n"
        "Research each with the tool, then pick your final list."
    )
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        # FINAL_COUNT (10) candidates with unconstrained reason length needs
        # more room than the old FINAL_COUNT=3 did.
        max_tokens=8000,
        output_config={"effort": EFFORT},
        system=SYSTEM_PROMPT,
        tools=[research_candidate],
        messages=[{"role": "user", "content": user_message}],
    )

    final_message = None
    for message in runner:
        final_message = message

    text = "".join(block.text for block in final_message.content if block.type == "text")
    return _parse_picks(text)
