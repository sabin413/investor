# Renders the pipeline's output (thesis + picks + actions) into a markdown
# report and writes it to reports/YYYY-MM-DD.md. This is the app's only
# persistence layer - no database, the dated files are the historical record.

from pathlib import Path

TIMEFRAME_LABELS = {"short_term": "short-term", "medium_term": "medium-term"}


def generate_report(thesis: str, picks: list[dict], actions: list[dict]) -> str:
    lines = ["# Daily Investor Report", "", "## Macro Summary", "", thesis, "", "## Top Candidates", ""]

    for pick in picks:
        label = TIMEFRAME_LABELS.get(pick["timeframe"], pick["timeframe"])
        lines.append(f"- **{pick['ticker']}** ({label}): {pick['reason']}")

    lines += ["", "## Portfolio Actions", ""]
    for action in actions:
        lines.append(f"- **{action['ticker']}** — {action['action'].upper()}: {action['reason']}")

    lines.append("")
    return "\n".join(lines)


def write_report(content: str, date_str: str, reports_dir) -> Path:
    reports_path = Path(reports_dir)
    reports_path.mkdir(parents=True, exist_ok=True)

    report_path = reports_path / f"{date_str}.md"
    report_path.write_text(content)
    return report_path
