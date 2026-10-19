import pytest

from investor.data_sources import sentiment
from tests.conftest import FakeResponse


def _message(basic):
    return {"entities": {"sentiment": {"basic": basic}}}


def test_get_sentiment_counts_bullish_and_bearish(monkeypatch):
    messages = [_message("Bullish"), _message("Bullish"), _message("Bearish"), {}]
    monkeypatch.setattr(sentiment.requests, "get", lambda *a, **k: FakeResponse({"messages": messages}))

    result = sentiment.get_sentiment("AMZN")

    assert result == {"ticker": "AMZN", "message_count": 4, "bullish": 2, "bearish": 1}


def test_get_sentiment_rejects_unexpected_response(monkeypatch):
    monkeypatch.setattr(sentiment.requests, "get", lambda *a, **k: FakeResponse({"error": "nope"}))

    with pytest.raises(ValueError):
        sentiment.get_sentiment("AMZN")
