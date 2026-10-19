# Builds the "tradeable universe" the screener scans: S&P 500 (large cap)
# unioned with the top 500 small caps by market cap.

from io import StringIO

import pandas as pd
import requests

SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
# Official Russell 2000 constituent files (iShares/Vanguard) block plain HTTP
# requests with bot-protection. This is a proxy: stockanalysis.com's small-cap
# screener (same $300M-$2B market-cap band Russell 2000 targets), sorted by
# market cap descending, so "top N" means the largest/most liquid small caps.
SMALLCAP_URL = "https://stockanalysis.com/list/small-cap-stocks/"
SMALLCAP_COUNT = 500
# stockanalysis.com returns 403 for the bare "Mozilla/5.0" UA; a full
# browser UA string is accepted.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    )
}


def _fetch_sp500_tickers() -> list[str]:
    resp = requests.get(SP500_URL, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    tables = pd.read_html(StringIO(resp.text))
    return tables[0]["Symbol"].tolist()


def _fetch_smallcap_tickers(limit: int = SMALLCAP_COUNT) -> list[str]:
    resp = requests.get(SMALLCAP_URL, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    table = pd.read_html(StringIO(resp.text))[0]
    return table["Symbol"].head(limit).tolist()


def get_universe() -> list[str]:
    tickers = set(_fetch_sp500_tickers()) | set(_fetch_smallcap_tickers())
    # yfinance expects e.g. "BRK-B", these sources list it as "BRK.B"
    tickers = {t.replace(".", "-") for t in tickers}
    return sorted(tickers)
