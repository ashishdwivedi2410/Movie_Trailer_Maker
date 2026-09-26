"""Mock/replay mode: records prompt -> response pairs keyed by an input hash
during a real run, then replays them deterministically for evaluation
without requiring an API key. Also doubles as the fallback path when the
preferred model is unavailable. See ARCHITECTURE.md section 8."""
import hashlib
import json
import os

CACHE_PATH = "fixtures/replay_cache.json"


def _hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()


def get_cached_response(prompt: str) -> str:
    if not os.path.exists(CACHE_PATH):
        raise FileNotFoundError(
            "No replay cache found - run once with a real API key first "
            "(save_response gets called automatically), or add fixtures manually."
        )
    with open(CACHE_PATH) as f:
        cache = json.load(f)
    key = _hash(prompt)
    if key not in cache:
        raise KeyError(f"No cached response for this prompt (hash {key[:8]}...)")
    return cache[key]


def save_response(prompt: str, response: str) -> None:
    cache = {}
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            cache = json.load(f)
    cache[_hash(prompt)] = response
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)