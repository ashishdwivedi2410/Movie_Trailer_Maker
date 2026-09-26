"""Parses family / young-adult / regional rating policy documents into
RatingRule entries. See ARCHITECTURE.md section 3.3."""
from src.models.constraint_map import RatingRule


def parse_policies(path: str) -> list[RatingRule]:
    raise NotImplementedError("Extract RatingRule entries from policy documents at `path`")