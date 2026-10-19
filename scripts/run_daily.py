# Orchestrator: runs the full daily pipeline end-to-end and writes a report.
# Each agent's output narrows the scope for the next one:
#   macro (thesis) -> screener (50 candidates) -> deep-dive (10 picks) -> portfolio (buy/sell/hold actions)

from datetime import date
from pathlib import Path

from investor.agents.deep_dive_agent import run_deep_dive_agent
from investor.agents.macro_agent import run_macro_agent
from investor.agents.portfolio_agent import run_portfolio_agent
from investor.agents.screener_agent import run_screener_agent
from investor.portfolio.store import load_portfolio
from investor.reports.generator import generate_report, write_report

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PORTFOLIO_PATH = PROJECT_ROOT / "portfolio.md"
REPORTS_DIR = PROJECT_ROOT / "reports"


def main():
    print("Running macro agent...")
    thesis = run_macro_agent()

    print("Running screener agent...")
    candidates = run_screener_agent(thesis)

    print("Running deep-dive agent...")
    picks = run_deep_dive_agent(thesis, candidates)

    print("Running portfolio agent...")
    portfolio = load_portfolio(PORTFOLIO_PATH)
    actions = run_portfolio_agent(thesis, picks, portfolio)

    report = generate_report(thesis, picks, actions)
    report_path = write_report(report, date.today().isoformat(), REPORTS_DIR)
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
