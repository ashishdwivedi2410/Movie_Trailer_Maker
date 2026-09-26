"""Parses actor / music / territory / promotional-use contracts into
RightsRule entries. Contracts are natural-language legal text, so this is
LLM-assisted extraction (via an agent) followed by structural validation -
never treated as free-form instructions to the rest of the pipeline.
See ARCHITECTURE.md section 3.3."""
from src.models.constraint_map import RightsRule


def parse_contracts(path: str) -> list[RightsRule]:
    raise NotImplementedError("Extract RightsRule entries from contract documents at `path`")