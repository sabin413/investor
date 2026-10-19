from pathlib import Path

import pytest

from investor.portfolio.store import CRYPTO_TICKERS, load_portfolio

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_loads_real_portfolio(tmp_path):
    path = tmp_path / "portfolio.md"
    path.write_text("# stocks and shares\n\nBTC 0.1\nAMZN 25\n")

    portfolio = load_portfolio(path)

    assert portfolio.positions[0].ticker == "BTC"
    assert portfolio.positions[0].quantity == 0.1
    assert portfolio.positions[0].asset_class == "crypto"

    assert portfolio.positions[1].ticker == "AMZN"
    assert portfolio.positions[1].quantity == 25
    assert portfolio.positions[1].asset_class == "equity"


def test_ignores_blank_lines_and_comments(tmp_path):
    path = tmp_path / "portfolio.md"
    path.write_text("# header\n\nMU 4.5\n\n# trailing comment\nORCL 50\n")

    portfolio = load_portfolio(path)

    assert [p.ticker for p in portfolio.positions] == ["MU", "ORCL"]


def test_rejects_malformed_line(tmp_path):
    path = tmp_path / "portfolio.md"
    path.write_text("# header\nAMZN\n")

    with pytest.raises(ValueError):
        load_portfolio(path)


def test_rejects_non_numeric_quantity(tmp_path):
    path = tmp_path / "portfolio.md"
    path.write_text("# header\nAMZN abc\n")

    with pytest.raises(ValueError):
        load_portfolio(path)


def test_rejects_empty_portfolio(tmp_path):
    path = tmp_path / "portfolio.md"
    path.write_text("# header\n")

    with pytest.raises(ValueError):
        load_portfolio(path)


def test_loads_actual_project_portfolio():
    portfolio = load_portfolio(PROJECT_ROOT / "portfolio.md")

    # portfolio.md changes whenever the user trades, so check that it parses
    # cleanly rather than pinning specific holdings.
    assert portfolio.positions
    for p in portfolio.positions:
        assert p.quantity > 0
        expected = "crypto" if p.ticker in CRYPTO_TICKERS else "equity"
        assert p.asset_class == expected
