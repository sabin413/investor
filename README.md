# Investor Agent

Daily research agent that reads macro conditions, screens the market, and
reconciles suggestions against your portfolio. See `_specs/investor.md` and
`_specs/decisions.md` for background and design decisions.

## Setup

    python -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"
    cp .env.example .env   # fill in ANTHROPIC_API_KEY, FRED_API_KEY

## Portfolio

Maintain your holdings in `portfolio.md` at the project root, one line per
position:

    TICKER QUANTITY

## Run

    python scripts/run_daily.py

Runs the full pipeline (macro → screener → deep-dive → portfolio) and writes
`reports/YYYY-MM-DD.md`.

## Tests

    pytest

## Status

v1 complete: portfolio parsing, free data sources, and all four pipeline
agents (macro, screener, deep-dive, portfolio) are built and verified
end-to-end. See `_specs/decisions.md` for the paid-data roadmap (Unusual
Whales next) and other deferred items (auto-execution, scheduling, a
database, etc.).
