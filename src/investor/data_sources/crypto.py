# Crypto spot prices via CoinGecko's free public API.

import requests

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

# CoinGecko needs its own slug ids, not tickers - only the handful of coins
# actually supported in portfolio.md are mapped here.
TICKER_TO_COINGECKO_ID = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "DOGE": "dogecoin",
    "XRP": "ripple",
    "ADA": "cardano",
}


def get_crypto_price(ticker: str, vs_currency: str = "usd") -> float:
    coin_id = TICKER_TO_COINGECKO_ID.get(ticker.upper())
    if coin_id is None:
        raise ValueError(f"no CoinGecko id mapping for ticker {ticker!r}")

    resp = requests.get(
        COINGECKO_URL,
        params={"ids": coin_id, "vs_currencies": vs_currency},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    if coin_id not in data or vs_currency not in data[coin_id]:
        raise ValueError(f"no price data returned for {ticker!r}")

    return data[coin_id][vs_currency]
