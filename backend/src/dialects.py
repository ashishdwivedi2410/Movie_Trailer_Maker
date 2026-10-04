"""Dialect list served to the frontend's "Dialect-region viewers" dropdown.

The list is data, not code: edit backend/data/dialects.json (or point the
DIALECTS_FILE env var at another file). Format:

    {"dialects": ["Dialect name 1", "Dialect name 2"]}

If the file is missing, malformed, or empty, load_dialects() raises
DialectsUnavailable and the API answers 503 with the reason, so the
frontend can show a real error instead of made-up placeholder dialects.
"""
import json
import os
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "dialects.json"


class DialectsUnavailable(Exception):
    pass


def load_dialects() -> list[str]:
    path = Path(os.getenv("DIALECTS_FILE") or DEFAULT_PATH)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise DialectsUnavailable(f"Dialect list not found at {path}.") from e
    except (OSError, json.JSONDecodeError) as e:
        raise DialectsUnavailable(f"Dialect list at {path} could not be read: {e}") from e

    items = data.get("dialects") if isinstance(data, dict) else data
    if not isinstance(items, list) or not all(isinstance(d, str) and d.strip() for d in items):
        raise DialectsUnavailable(
            f'Dialect list at {path} must look like {{"dialects": ["name", ...]}}.'
        )
    if not items:
        raise DialectsUnavailable(
            f"No dialects are configured yet. Add names to {path} (or set DIALECTS_FILE)."
        )
    return [d.strip() for d in items]