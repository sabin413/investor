# Parses portfolio.md - one "TICKER QUANTITY" line per position - into a Portfolio.

from pathlib import Path

from investor.portfolio.models import Portfolio, Position

# Portfolio.md has no explicit asset-class column, so crypto tickers are
# recognized from this fixed set; anything else is treated as an equity.
CRYPTO_TICKERS = {"BTC", "ETH", "SOL", "DOGE", "XRP", "ADA"}


def load_portfolio(path) -> Portfolio:
    path = Path(path)
    positions = []

    for line_no, raw_line in enumerate(path.read_text().splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"{path}:{line_no}: expected 'TICKER QUANTITY', got {raw_line!r}")

        ticker, quantity_str = parts
        try:
            quantity = float(quantity_str)
        except ValueError:
            raise ValueError(f"{path}:{line_no}: quantity {quantity_str!r} is not a number") from None

        ticker = ticker.upper()
        asset_class = "crypto" if ticker in CRYPTO_TICKERS else "equity"
        positions.append(Position(ticker=ticker, quantity=quantity, asset_class=asset_class))

    if not positions:
        raise ValueError(f"{path}: no positions found")

    return Portfolio(positions=positions)
