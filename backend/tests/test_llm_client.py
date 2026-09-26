"""Unit tests for LLMClient (src/llm/client.py) - the single choke point
every agent calls through (src/agents/base.py), and the home of the
budget-guard cost tracking that node_finalize (src/graph/pipeline.py) reads
to populate TrailerPlan.estimated_cost_usd / lower_cost_fallback. Previously
untested even though the rest of the pipeline depends on its behavior.
"""
import pytest

from src.config import settings
from src.llm.client import LLMClient


@pytest.fixture(autouse=True)
def _restore_settings():
    """settings (src/config.py) is a module-level singleton shared by the
    whole process - snapshot and restore the fields these tests mutate so
    changes can't leak into other test modules."""
    original_mock_mode = settings.mock_mode
    original_budget = settings.budget_usd
    yield
    settings.mock_mode = original_mock_mode
    settings.budget_usd = original_budget


def test_call_raises_when_not_mocked_and_real_api_path_unimplemented():
    settings.mock_mode = False
    client = LLMClient()
    with pytest.raises(NotImplementedError):
        client.call("any prompt")


def test_mock_mode_returns_the_cached_response(monkeypatch):
    settings.mock_mode = True
    monkeypatch.setattr("src.llm.replay.get_cached_response", lambda prompt: "a canned response")

    client = LLMClient()
    result = client.call("a prompt")

    assert result == "a canned response"


def test_mock_mode_call_still_records_cost(monkeypatch):
    """Mock/replay is also the fallback path for the 'model unavailable'
    surprise event (ARCHITECTURE.md section 8) - a run that falls back to it
    shouldn't look free just because no real API call happened."""
    settings.mock_mode = True
    monkeypatch.setattr("src.llm.replay.get_cached_response", lambda prompt: "a canned response")

    client = LLMClient()
    assert client.total_cost_usd == 0.0
    client.call("a prompt")
    assert client.total_cost_usd > 0.0


def test_cost_accumulates_across_multiple_calls(monkeypatch):
    settings.mock_mode = True
    monkeypatch.setattr("src.llm.replay.get_cached_response", lambda prompt: "response")

    client = LLMClient()
    client.call("prompt one")
    after_first_call = client.total_cost_usd
    client.call("prompt two")

    assert client.total_cost_usd > after_first_call


def test_longer_prompts_cost_more(monkeypatch):
    settings.mock_mode = True
    monkeypatch.setattr("src.llm.replay.get_cached_response", lambda prompt: "short response")

    cheap_client = LLMClient()
    cheap_client.call("x")

    expensive_client = LLMClient()
    expensive_client.call("x" * 10_000)

    assert expensive_client.total_cost_usd > cheap_client.total_cost_usd


def test_over_budget_is_false_until_the_threshold_is_crossed(monkeypatch):
    settings.mock_mode = True
    settings.budget_usd = 0.000001  # near-zero ceiling so a single call trips it
    monkeypatch.setattr("src.llm.replay.get_cached_response", lambda prompt: "response")

    client = LLMClient()
    assert client.over_budget() is False  # nothing spent yet

    client.call("prompt")
    assert client.over_budget() is True


def test_over_budget_false_when_comfortably_under_the_default_budget(monkeypatch):
    settings.mock_mode = True
    monkeypatch.setattr("src.llm.replay.get_cached_response", lambda prompt: "response")

    client = LLMClient()
    client.call("a short prompt")

    assert client.over_budget() is False