# Stage 1 of the pipeline: produces the day's macro thesis (plain text) that
# every downstream agent is given as context.

import json

from anthropic import Anthropic, beta_tool

from investor.data_sources.macro import get_headlines, get_macro_snapshot

MODEL = "claude-opus-5-5"
# Opus 5.5 defaults to "medium" effort (Opus 5 defaulted to "high"); pinned
# explicitly so every stage keeps the depth of analysis it had on Opus 5.
EFFORT = "high"

SYSTEM_PROMPT = """You are a macro analyst for an aggressive-but-sensible retail
investor. Use the tools to pull current US macro data and news headlines,
then write a short (150-250 word) macro thesis covering: (1) what forces are
currently controlling markets, (2) what forces are likely to control markets
in the near future (days to weeks), and (3) how those forces might affect
stocks, gold, and crypto. Be concrete and reference the actual data and
headlines you pulled - don't speculate beyond what the tools tell you."""


# Tool return values must be str (or content blocks), never a raw dict/list -
# the Anthropic SDK accepts it locally but the API rejects it at request time.
@beta_tool
def fetch_macro_snapshot() -> str:
    """Fetch the latest US macro indicators: fed funds rate, CPI, unemployment rate."""
    return json.dumps(get_macro_snapshot())


@beta_tool
def fetch_headlines() -> str:
    """Fetch current top financial/business news headlines."""
    return json.dumps(get_headlines())


def run_macro_agent() -> str:
    client = Anthropic()
    # tool_runner drives the tool-use loop (call tools, feed results back)
    # until Claude returns a final text-only message.
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=2000,
        output_config={"effort": EFFORT},
        system=SYSTEM_PROMPT,
        tools=[fetch_macro_snapshot, fetch_headlines],
        messages=[{"role": "user", "content": "Write today's macro thesis."}],
    )

    final_message = None
    for message in runner:
        final_message = message

    text = "".join(block.text for block in final_message.content if block.type == "text")
    if not text:
        raise ValueError("macro agent did not produce a final response")

    return text
