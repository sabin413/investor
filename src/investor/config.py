import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
FRED_API_KEY = os.environ.get("FRED_API_KEY")

# Minimal risk guardrail: block a suggested buy that would push a single
# position above this share of total portfolio value.
MAX_SINGLE_POSITION_PCT = 0.20
