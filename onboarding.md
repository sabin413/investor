# Onboarding

## What this is
A daily research agent that mimics an experienced retail investor's morning routine: read macro conditions → screen the market → deep-dive top candidates → reconcile against your portfolio → write a markdown report. Recommendations only — it never trades. Pure Python, driven by four sequential Claude API stages (no agent framework). See `_specs/investor.md` (original spec) and `_specs/decisions.md` (design decisions/gotchas) for background.

Funnel at a glance: ~1000 tickers → 200 (mechanical technical prescreen) → 50 (screener agent) → 10 picks, 5 short-term + 5 medium-term (deep-dive agent) → buy/sell/hold/pass actions (portfolio agent).

## Entry point
- **`scripts/run_daily.py`** — the orchestrator. Runs the four agents in sequence (macro → screener → deep-dive → portfolio), then generates and writes `reports/YYYY-MM-DD.md`. This is what you actually execute (`python scripts/run_daily.py`).

## `src/investor/config.py`
Loads `.env` (via `dotenv`), exposes `ANTHROPIC_API_KEY` / `FRED_API_KEY`, and defines the one risk constant: `MAX_SINGLE_POSITION_PCT = 0.20`.

## `src/investor/agents/` — the four pipeline stages (all use Claude Opus 5.5 at `high` effort; model string and effort in `macro_agent.MODEL` / `macro_agent.EFFORT`)
- **`macro_agent.py`** — gives Claude two tools (`fetch_macro_snapshot`, `fetch_headlines`) and asks it to write a 150-250 word macro thesis. Output: plain text string, passed to every downstream stage.
- **`screener_agent.py`** — two steps:
  1. Mechanical prescreen (pure Python, no Claude): bulk-downloads 3mo price history for the whole tradeable universe via `yfinance`, keeps only tickers trading above their 50-day SMA (`_in_uptrend`), and ranks survivors by risk-adjusted momentum — 1-month momentum ÷ annualized volatility (`_score_universe`). The top `PRESCREEN_COUNT` (200) are exposed to Claude via the `prescreen_candidates` tool.
  2. Claude's judgment: given the macro thesis and the 200 candidates' full technical fields, Claude picks `FINAL_COUNT` (50), weighing momentum, trend strength, RSI (avoid extreme overbought), liquidity, and the macro backdrop, with a one-line reason each. Output: JSON array parsed/validated by `_parse_candidates`.
- **`deep_dive_agent.py`** — for each of the 50 candidates, exposes a `research_candidate` tool that pulls fundamentals + sentiment + technicals (`research_ticker` — reused by `portfolio_agent.py` too; each data source fails independently so one missing feed doesn't block the rest). Claude researches all 50 and narrows to 10 final picks: exactly `SHORT_TERM_COUNT` (5) short-term (days–1mo) and `MEDIUM_TERM_COUNT` (5) medium-term (1mo–few months). `_parse_picks` validates the count and the exact 5/5 split.
- **`portfolio_agent.py`** — takes the current portfolio (loaded from `portfolio.md`), fetches a full snapshot (`portfolio_snapshot`: current price, value, % of portfolio, plus full research for equities via `research_ticker`), and enriches the 10 picks with the same research (`_enrich_candidates`) so buy/pass decisions get the same data as hold/sell decisions. Then asks Claude (single call, no tools) to decide hold/sell for each holding and buy/pass for each candidate. `_validate_against_membership` enforces that holdings only get hold/sell and candidates only get buy/pass, and that every holding gets a decision. `apply_risk_guardrail` then downgrades any `buy` to `hold` if that ticker is already at or above `MAX_SINGLE_POSITION_PCT` of the portfolio, keeping the original reason in the report.

## `src/investor/data_sources/` — thin wrappers around free external data, no local caching/DB
- **`macro.py`** — FRED API (fed funds rate, CPI, unemployment) + CNBC RSS headlines.
- **`fundamentals.py`** — `yfinance` wrapper returning price, market cap, P/E, PEG, 52-week range, analyst price targets and consensus rating, growth/profitability metrics (revenue/earnings growth, margins, ROE, debt/equity, free cash flow), and ownership/positioning data (insider/institutional holdings, short interest). Also returns raw price history.
- **`technicals.py`** — computes, via the `ta` library, from a price-history DataFrame (needs >50 prices): price, SMA20/50, RSI14, 1-month and 3-month momentum, annualized volatility, risk-adjusted momentum, and average dollar volume.
- **`sentiment.py`** — StockTwits public API; counts bullish/bearish message tags for a ticker.
- **`crypto.py`** — CoinGecko price lookup, with a small hardcoded ticker→CoinGecko-id map (BTC, ETH, SOL, DOGE, XRP, ADA).
- **`universe.py`** — builds the "tradeable universe" by scraping S&P 500 tickers (Wikipedia) union top-500 small caps (stockanalysis.com, used as a Russell 2000 proxy since official sources block scraping).

## `src/investor/portfolio/`
- **`models.py`** — two frozen dataclasses: `Position` (ticker, quantity, asset_class) and `Portfolio` (list of positions).
- **`store.py`** — `load_portfolio()` parses `portfolio.md`'s `TICKER QUANTITY` lines (blank lines and `#` comments are skipped), auto-classifying `asset_class` as crypto (from a hardcoded set) or equity.

## `src/investor/reports/generator.py`
`generate_report()` assembles the macro thesis + picks + actions into a markdown string; `write_report()` writes it to `reports/YYYY-MM-DD.md`.

## Root files
- **`portfolio.md`** — your actual holdings, one `TICKER QUANTITY` line each (currently BTC + 9 equities/ETFs).
- **`reports/`** — dated output reports, one per run; these are the historical record.
- **`.env.example` / `.env`** — API key config (`ANTHROPIC_API_KEY`, `FRED_API_KEY`).
- **`pyproject.toml`** — setuptools package (`src/` layout), deps: `yfinance`, `pandas`, `requests`, `ta`, `anthropic`, etc.; tests via `pytest`.

## `tests/`
One test file per data source/agent/component (`test_macro.py`, `test_crypto.py`, `test_screener_agent.py`, etc.) plus `conftest.py` for shared fixtures — mirrors the `src/investor/` structure 1:1.

## Notable gotchas (from `decisions.md`)
- `@beta_tool` functions must return `str`/content blocks, not raw dict/list — hence every tool wraps output in `json.dumps(...)`.
- Output size drives `max_tokens`: too low truncates the response mid-JSON, which fails parsing. Current values are 2000 (macro), 10000 (screener, 50 candidates), and 8000 (deep-dive and portfolio, 10 picks plus a full portfolio).
- No database — dated report files *are* the historical record. Auto-execution, scheduling, and paid data (Unusual Whales planned next) are explicitly deferred.
