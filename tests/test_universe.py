from investor.data_sources import universe


def test_get_universe_dedupes_sorts_and_normalizes_tickers(monkeypatch):
    monkeypatch.setattr(universe, "_fetch_sp500_tickers", lambda: ["MSFT", "BRK.B", "AAPL", "AAPL"])
    monkeypatch.setattr(universe, "_fetch_smallcap_tickers", lambda: ["ZBRA", "AAPL"])

    result = universe.get_universe()

    assert result == ["AAPL", "BRK-B", "MSFT", "ZBRA"]
