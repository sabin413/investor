import pytest

from investor.data_sources import crypto
from tests.conftest import FakeResponse


def test_get_crypto_price(monkeypatch):
    def fake_get(url, params, timeout):
        assert params["ids"] == "bitcoin"
        return FakeResponse({"bitcoin": {"usd": 65000.0}})

    monkeypatch.setattr(crypto.requests, "get", fake_get)

    assert crypto.get_crypto_price("BTC") == 65000.0


def test_get_crypto_price_unknown_ticker():
    with pytest.raises(ValueError):
        crypto.get_crypto_price("NOTACOIN")


def test_get_crypto_price_missing_data(monkeypatch):
    monkeypatch.setattr(crypto.requests, "get", lambda *a, **k: FakeResponse({}))

    with pytest.raises(ValueError):
        crypto.get_crypto_price("BTC")
