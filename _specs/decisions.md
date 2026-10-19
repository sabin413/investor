# Design decisions (v1)

Companion to `investor.md`, capturing the decisions made when scoping v1.

## Execution model

Recommendations only — the app never places trades automatically. Every
buy/sell/hold suggestion is surfaced to the user for manual action. Auto-
execution via a brokerage API is a possible future phase, not part of v1.

## Portfolio tracking

Manually maintained in `portfolio.md` at the project root, in a minimal
`TICKER QUANTITY` per line format. No brokerage or aggregator integration in
v1. No cost basis is tracked — position sizing is computed from current
market value (price × quantity).

## Data sources (v1 — free only)

| Purpose | Source |
|---|---|
| Macro / news | FRED API, a free news/headline pull |
| Stock fundamentals & price | `yfinance` |
| Crypto | CoinGecko API |
| Gold | GLD/IAU ETF price via `yfinance` (proxy) |
| Sentiment | StockTwits public API |
| Technicals | computed locally via the `ta` library, no external API |
| Candidate universe | S&P 500 (Wikipedia) + top 500 small caps by market cap (stockanalysis.com) |

Real-time whole-market screening isn't available for free, so v1 screens a
static universe rather than the entire market (~1000 tickers total).

`pandas-ta` turned out to be broken on PyPI (only pre-release versions
requiring Python 3.12+); switched to the `ta` library instead, which is
actively maintained and works on 3.11.

Official Russell 2000 constituent files (iShares, Vanguard) are blocked by
bot-protection for plain HTTP requests, so the small-cap slice uses
stockanalysis.com's small-cap screener (same $300M-$2B market-cap band
Russell 2000 targets) as a proxy, taking the top 500 by market cap — not
literal Russell 2000 membership, but the largest/most liquid names in that
band.

**Planned first paid add-on:** Unusual Whales (options flow), once v1's
output quality is validated. Considered and deprioritized for now: Ortex,
Quiver Quant, Benzinga Pro, Polygon.io options data.

**Anthropic `@beta_tool` gotcha:** a tool function's return value must be
`str` or an iterable of content blocks — not a raw dict/list. Returning a
raw dict/list produces a malformed API request (`content.0: Input should be
an object`) only on the success path, so it can pass local testing and still
break live. All tool functions in `agents/` return `json.dumps(...)`.

**Portfolio agent `max_tokens` gotcha:** with a full portfolio (8 holdings)
plus 3 researched candidates, the portfolio agent's response is long enough
(11 detailed per-ticker decisions) that `max_tokens=2000` truncated it
mid-response, which correctly failed JSON parsing rather than silently
returning garbage. Fixed by raising to `max_tokens=6000` and asking for
2-3 sentence reasons instead of open-ended paragraphs.

*Update:* when the deep-dive output grew from 3 picks to 10 (5 short-term +
5 medium-term), the portfolio agent's `max_tokens` was raised again to
8000, since it now addresses the full portfolio plus up to 10 researched
candidates in one response.

## Output

A markdown report per run, written to `reports/YYYY-MM-DD.md`, with:
- Macro summary
- Top candidates (ticker, timeframe, rationale)
- Portfolio actions (hold/sell/buy per position, rationale)

The dated report files are themselves the historical record — no database.
If outcome tracking is wanted later, it's built by parsing these files
rather than maintaining a separate log from the start.

## Risk management

Deliberately minimal: one or two hardcoded guardrail constants (e.g. a max
percentage of portfolio in a single new position), not a rules engine or
config file. Enough to block an obviously reckless suggestion; tuned after
seeing real output.

## Tech stack

Python. Claude API (with tool use) drives four sequential pipeline stages —
macro agent → screener agent → deep-dive agent → portfolio agent — each
stage narrowing scope for the next. No agent framework (LangChain/CrewAI):
the pipeline is linear enough that a thin hand-rolled orchestrator is
simpler to reason about.

## Deferred (explicitly out of scope for v1)

- Auto-execution / brokerage integration
- Paid data sources
- Email delivery or a web dashboard
- Scheduling/cron automation (v1 is run manually)
- Backtesting / outcome evaluation
- Any database

## Build approach

Implemented in small slices, each reviewed and approved before the next
begins:

1. Project scaffold + portfolio parsing
2. Free data source modules (fundamentals, macro, crypto, sentiment,
   technicals, candidate universe)
3. Macro + screener agents
4. Deep-dive + portfolio agents
5. Report generation + orchestrator wiring

## Model

Upgraded from `claude-opus-5` to `claude-opus-5-5` (cheaper per token,
stronger on knowledge-work/finance benchmarks; no evidence it picks better
stocks — measure via the dated reports). Opus 5.5 defaults to `medium`
effort where Opus 5 defaulted to `high`, so `EFFORT = "high"` is pinned
in `macro_agent.py` and passed as `output_config` on every Claude call to
keep analysis depth unchanged.
