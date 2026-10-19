# Computes technical indicators locally (via the `ta` library) from a price
# history DataFrame - no external API needed for this one.

import pandas as pd
from ta.momentum import ROCIndicator, RSIIndicator
from ta.trend import SMAIndicator

# Floor for volatility when dividing into risk_adjusted_momentum, so a
# flat/near-flat price series can't produce a divide-by-zero.
_VOLATILITY_EPSILON = 1e-6


def summarize(price_history: pd.DataFrame) -> dict:
    closes = price_history["Close"]
    if len(closes) <= 50:
        # SMA50 needs 50 data points; without more than that the latest
        # value would just be a partial/misleading average.
        raise ValueError(f"need more than 50 prices for a reliable summary, got {len(closes)}")

    momentum_1mo_pct = ROCIndicator(closes, window=21).roc().iloc[-1]  # ~21 trading days = 1 month

    # Simple total return over the whole fetched window (not a fixed-window
    # ROCIndicator) since the exact trading-day count behind "3mo" of history
    # varies slightly.
    momentum_3mo_pct = (closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0] * 100

    # Annualized, in percent, so it's on the same scale as the momentum
    # fields and risk_adjusted_momentum is a like-for-like ratio.
    daily_returns = closes.pct_change().dropna()
    volatility = daily_returns.std() * (252**0.5) * 100

    return {
        "price": closes.iloc[-1],
        "sma_20": SMAIndicator(closes, window=20).sma_indicator().iloc[-1],
        "sma_50": SMAIndicator(closes, window=50).sma_indicator().iloc[-1],
        "rsi_14": RSIIndicator(closes, window=14).rsi().iloc[-1],
        "momentum_1mo_pct": momentum_1mo_pct,
        "momentum_3mo_pct": momentum_3mo_pct,
        "volatility": volatility,
        "risk_adjusted_momentum": momentum_1mo_pct / max(volatility, _VOLATILITY_EPSILON),
        "avg_dollar_volume": (price_history["Volume"] * closes).mean(),
    }
