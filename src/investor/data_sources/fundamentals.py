# Stock fundamentals and price history via yfinance (free, no API key needed).

import pandas as pd
import yfinance as yf


def get_fundamentals(ticker: str) -> dict:
    info = yf.Ticker(ticker).info
    # currentPrice is missing for some tickers (e.g. after-hours/delisted);
    # regularMarketPrice is the fallback.
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    if not info or price is None:
        raise ValueError(f"no fundamentals data for ticker {ticker!r}")

    return {
        "ticker": ticker,
        "price": price,
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        # Analyst consensus / price targets
        "target_mean_price": info.get("targetMeanPrice"),
        "target_median_price": info.get("targetMedianPrice"),
        "target_high_price": info.get("targetHighPrice"),
        "target_low_price": info.get("targetLowPrice"),
        "number_of_analyst_opinions": info.get("numberOfAnalystOpinions"),
        "recommendation_key": info.get("recommendationKey"),
        "recommendation_mean": info.get("recommendationMean"),
        # Growth / quality
        "peg_ratio": info.get("trailingPegRatio"),
        "debt_to_equity": info.get("debtToEquity"),
        "return_on_equity": info.get("returnOnEquity"),
        "profit_margins": info.get("profitMargins"),
        "operating_margins": info.get("operatingMargins"),
        "free_cashflow": info.get("freeCashflow"),
        "revenue_growth": info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
        "earnings_quarterly_growth": info.get("earningsQuarterlyGrowth"),
        # Ownership / positioning
        "held_percent_insiders": info.get("heldPercentInsiders"),
        "held_percent_institutions": info.get("heldPercentInstitutions"),
        "short_percent_of_float": info.get("shortPercentOfFloat"),
        "short_ratio": info.get("shortRatio"),
        "shares_short": info.get("sharesShort"),
        "shares_short_prior_month": info.get("sharesShortPriorMonth"),
    }


def get_price_history(ticker: str, period: str = "3mo") -> pd.DataFrame:
    history = yf.Ticker(ticker).history(period=period)
    if history.empty:
        raise ValueError(f"no price history for ticker {ticker!r}")
    return history
