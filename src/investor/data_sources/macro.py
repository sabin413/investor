# Free macro data: FRED for indicators, CNBC RSS for headlines. Used by macro_agent.

import xml.etree.ElementTree as ET

import requests

from investor.config import FRED_API_KEY

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
CNBC_TOP_NEWS_RSS = "https://www.cnbc.com/id/100003114/device/rss/rss.html"
HEADERS = {"User-Agent": "Mozilla/5.0"}

SERIES = {
    "fed_funds_rate": "FEDFUNDS",
    "cpi": "CPIAUCSL",
    "unemployment_rate": "UNRATE",
}


def get_macro_snapshot() -> dict:
    if not FRED_API_KEY:
        raise ValueError("FRED_API_KEY is not set")

    snapshot = {}
    for name, series_id in SERIES.items():
        # One request per series - FRED has no bulk multi-series endpoint.
        resp = requests.get(
            FRED_URL,
            params={
                "series_id": series_id,
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 1,  # only need the latest observation
            },
            timeout=10,
        )
        resp.raise_for_status()
        observations = resp.json().get("observations")
        if not observations:
            raise ValueError(f"no observations returned for series {series_id!r}")

        obs = observations[0]
        snapshot[name] = {"date": obs["date"], "value": float(obs["value"])}

    return snapshot


def get_headlines(limit: int = 15) -> list[str]:
    resp = requests.get(CNBC_TOP_NEWS_RSS, headers=HEADERS, timeout=10)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    titles = [title for item in root.findall(".//item") if (title := item.findtext("title"))]
    if not titles:
        raise ValueError("no headlines found in RSS feed")

    return titles[:limit]
