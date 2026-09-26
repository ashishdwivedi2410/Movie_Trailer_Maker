"""Shared test doubles for exercising the actual agents, LLMClient, and
build_pipeline() - previously untested even though build_pipeline() accepts
strategist/composer/verifier injection specifically so tests can do this
without a real API key. See src/graph/pipeline.py's build_pipeline()
docstring.
"""
from src.models.promise import AudiencePromise
from src.models.trailer import Segment


class FakeLLMClient:
    """Drop-in double for src.llm.client.LLMClient: returns queued canned
    responses in order instead of calling a real or replayed model, while
    still pricing each call the same way the real client does, so tests
    exercising the budget guard in node_finalize see realistic numbers."""

    def __init__(self, responses: list[str] | None = None):
        self.responses = list(responses or [])
        self.prompts: list[str] = []
        self.total_cost_usd = 0.0
        self.consecutive_failures = 0
        self.circuit_open = False

    def call(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self.responses:
            raise AssertionError("FakeLLMClient ran out of queued responses")
        response = self.responses.pop(0)
        self.total_cost_usd += (len(prompt) + len(response)) / 4 / 1000 * 0.01
        return response

    def over_budget(self) -> bool:
        from src.config import settings
        return self.total_cost_usd > settings.budget_usd


class FakeStrategist:
    """Fake Audience Strategist for build_pipeline() injection - returns a
    fixed AudiencePromise instead of calling an LLM."""

    def __init__(self, promise: AudiencePromise):
        self.promise = promise
        self.calls = 0

    def plan_promise(self, audience, story_map, audience_profile, historic_performance):
        self.calls += 1
        return self.promise


class FakeComposer:
    """Fake Composer for build_pipeline() injection - returns queued segment
    lists in order, one per compose() call, so a test can script exactly
    what the repair loop sees on each attempt. Records the excluded_scene_ids
    seen on each call so a test can assert the repair loop actually narrowed
    the option pool."""

    def __init__(self, segment_lists: list[list[Segment]]):
        self.segment_lists = list(segment_lists)
        self.calls: list[list[str]] = []

    def compose(
        self, audience, audience_promise, story_map, registry, duration_seconds,
        excluded_scene_ids=None,
    ):
        self.calls.append(list(excluded_scene_ids or []))
        if not self.segment_lists:
            raise AssertionError("FakeComposer ran out of queued segment lists")
        return self.segment_lists.pop(0)


class FakeVerifier:
    """Fake semantic Verifier for build_pipeline() injection - returns fixed
    spoiler/bias results instead of calling an LLM, so a test can isolate the
    graph's repair/approval routing from real semantic judgment (the real
    deterministic checks in src/verification/checks.py still run for real,
    since node_verify calls those directly rather than through this agent)."""

    def __init__(self, spoiler_fact_ids: list[str] | None = None, bias_warnings: list[str] | None = None):
        self.spoiler_fact_ids = spoiler_fact_ids or []
        self.bias_warnings = bias_warnings or []

    def check_spoilers(self, segments, story_map):
        return self.spoiler_fact_ids

    def check_bias(self, audience, audience_promise, segments):
        return self.bias_warnings