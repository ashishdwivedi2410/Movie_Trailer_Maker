"""Parses the supplied cost sheet (per-resource pricing: LLM calls, music
licensing, editor time, etc.) into a CostSheet. See ARCHITECTURE.md sections
3.1 and 8.

TODO: parse the actual supplied cost-sheet format once available - same open
question as the episode/contract/policy formats in the other src/ingest/
modules, so this is left as a typed stub rather than a guessed format.
"""
from src.models.cost_sheet import CostSheet


def parse_cost_sheet(path: str) -> CostSheet:
    raise NotImplementedError("Extract CostLineItem entries from the cost sheet at `path`")