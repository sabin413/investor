import pytest

from investor.data_sources import macro
from tests.conftest import FakeResponse


def test_get_macro_snapshot(monkeypatch):
    monkeypatch.setattr(macro, "FRED_API_KEY", "fake-key")

    def fake_get(url, params, timeout):
        return FakeResponse({"observations": [{"date": "2026-08-01", "value": "4.33"}]})

    monkeypatch.setattr(macro.requests, "get", fake_get)

    snapshot = macro.get_macro_snapshot()

    assert set(snapshot) == {"fed_funds_rate", "cpi", "unemployment_rate"}
    assert snapshot["fed_funds_rate"] == {"date": "2026-08-01", "value": 4.33}


def test_get_macro_snapshot_requires_api_key(monkeypatch):
    monkeypatch.setattr(macro, "FRED_API_KEY", None)

    with pytest.raises(ValueError):
        macro.get_macro_snapshot()


def test_get_macro_snapshot_rejects_empty_observations(monkeypatch):
    monkeypatch.setattr(macro, "FRED_API_KEY", "fake-key")
    monkeypatch.setattr(macro.requests, "get", lambda *a, **k: FakeResponse({"observations": []}))

    with pytest.raises(ValueError):
        macro.get_macro_snapshot()


def test_get_headlines(monkeypatch):
    xml = """<rss><channel>
      <item><title>Fed raises rates</title></item>
      <item><title>Markets rally</title></item>
    </channel></rss>"""
    monkeypatch.setattr(macro.requests, "get", lambda *a, **k: FakeResponse(text=xml))

    assert macro.get_headlines() == ["Fed raises rates", "Markets rally"]


def test_get_headlines_respects_limit(monkeypatch):
    xml = "<rss><channel>" + "".join(f"<item><title>H{i}</title></item>" for i in range(5)) + "</channel></rss>"
    monkeypatch.setattr(macro.requests, "get", lambda *a, **k: FakeResponse(text=xml))

    assert macro.get_headlines(limit=2) == ["H0", "H1"]


def test_get_headlines_rejects_empty_feed(monkeypatch):
    monkeypatch.setattr(macro.requests, "get", lambda *a, **k: FakeResponse(text="<rss><channel></channel></rss>"))

    with pytest.raises(ValueError):
        macro.get_headlines()
