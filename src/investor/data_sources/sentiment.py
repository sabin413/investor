# Public sentiment via StockTwits' public API (no key required): counts
# bullish/bearish tags on recent messages for a ticker.

import requests

STOCKTWITS_URL = "https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_sentiment(ticker: str) -> dict:
    resp = requests.get(STOCKTWITS_URL.format(ticker=ticker), headers=HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    messages = data.get("messages")
    if messages is None:
        raise ValueError(f"unexpected StockTwits response for {ticker!r}: {data!r}")

    bullish = 0
    bearish = 0
    for message in messages:
        # Sentiment tag is optional per message - untagged messages count
        # toward message_count but not toward bullish/bearish.
        sentiment = (message.get("entities") or {}).get("sentiment") or {}
        basic = sentiment.get("basic")
        if basic == "Bullish":
            bullish += 1
        elif basic == "Bearish":
            bearish += 1

    return {
        "ticker": ticker,
        "message_count": len(messages),
        "bullish": bullish,
        "bearish": bearish,
    }
