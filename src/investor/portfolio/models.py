# Data model for a parsed portfolio.md.

from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    ticker: str
    quantity: float
    asset_class: str  # "equity" | "crypto"


@dataclass(frozen=True)
class Portfolio:
    positions: list[Position]
