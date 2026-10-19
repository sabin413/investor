from investor.reports.generator import generate_report, write_report


def _sample_picks():
    return [
        {"ticker": "SMCI", "timeframe": "short_term", "reason": "Cheap and trending."},
        {"ticker": "LITE", "timeframe": "short_term", "reason": "AI optics exposure."},
        {"ticker": "USAS", "timeframe": "medium_term", "reason": "Gold hedge."},
    ]


def _sample_actions():
    return [
        {"ticker": "AMZN", "action": "hold", "reason": "Core position, no change."},
        {"ticker": "IONQ", "action": "sell", "reason": "Off-theme, cut it."},
        {"ticker": "SMCI", "action": "buy", "reason": "New high-conviction pick."},
    ]


def test_generate_report_includes_all_sections():
    report = generate_report("Macro thesis text here.", _sample_picks(), _sample_actions())

    assert "## Macro Summary" in report
    assert "Macro thesis text here." in report
    assert "## Top Candidates" in report
    assert "## Portfolio Actions" in report


def test_generate_report_formats_picks_with_readable_timeframe():
    report = generate_report("thesis", _sample_picks(), [])

    assert "**SMCI** (short-term): Cheap and trending." in report
    assert "**USAS** (medium-term): Gold hedge." in report


def test_generate_report_formats_actions_with_uppercase_verb():
    report = generate_report("thesis", [], _sample_actions())

    assert "**AMZN** — HOLD: Core position, no change." in report
    assert "**IONQ** — SELL: Off-theme, cut it." in report


def test_write_report_creates_file_with_expected_name_and_content(tmp_path):
    reports_dir = tmp_path / "reports"

    path = write_report("hello world", "2026-08-27", reports_dir)

    assert path == reports_dir / "2026-08-27.md"
    assert path.read_text() == "hello world"


def test_write_report_creates_missing_directory(tmp_path):
    reports_dir = tmp_path / "nested" / "reports"

    path = write_report("content", "2026-08-27", reports_dir)

    assert path.exists()
