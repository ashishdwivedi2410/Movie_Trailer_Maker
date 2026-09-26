"""Tests for the actual LangGraph wiring in src/graph/pipeline.py, using
build_pipeline()'s fake-agent injection (see its docstring: "used by tests
to run the graph with fakes, no real LLM calls") so the graph's control flow
- the repair loop, retry exhaustion, approval routing, and the budget-guard
cost fields on TrailerPlan - is exercised directly, rather than only via the
hand-built fixtures the other tests use for the deterministic checks
underneath it. Previously zero tests touched build_pipeline() at all.
"""
import json

from src.agents.audience_strategist import AudienceStrategist
from src.agents.composer import Composer
from src.agents.verifier import SemanticVerifier
from src.graph.pipeline import DEFAULT_MAX_REPAIR_ATTEMPTS, build_pipeline
from src.models.promise import AudiencePromise
from src.observability.decision_log import DecisionLog
from tests.conftest import make_segment
from tests.fakes import FakeComposer, FakeLLMClient, FakeStrategist, FakeVerifier


def _promise(audience="family"):
    return AudiencePromise(audience=audience, promise="p", emotional_arc="a")


def _initial_state(tmp_path, registry, constraints, story_map, **overrides):
    state = {
        "audience": "family",
        "story_map": story_map,
        "constraint_map": constraints,
        "scene_registry": registry,
        "audience_profile": {},
        "historic_performance": {},
        "territory": "US",
        "duration_seconds": 2,
        "decision_log": DecisionLog(path=str(tmp_path / "decision_log.jsonl")),
        "excluded_scene_ids": [],
        "repair_attempts": 0,
        "cost_baseline_usd": 0.0,
    }
    state.update(overrides)
    return state


def test_happy_path_passes_straight_through(tmp_path, registry, constraints, story_map):
    segments = [make_segment("scene_01", evidence=["scene:scene_01"], subtitle="hi")]
    strategist = FakeStrategist(_promise())
    composer = FakeComposer([segments])
    verifier = FakeVerifier()

    app = build_pipeline(client=FakeLLMClient(), strategist=strategist, composer=composer, verifier=verifier)
    final = app.invoke(_initial_state(tmp_path, registry, constraints, story_map))

    assert final["validation"].status == "PASS"
    assert final["trailer_plan"].segments[0].video == "scene_01"
    assert composer.calls == [[]]  # composed exactly once, nothing excluded
    # Nothing in this test ever calls client.call(), so the run cost nothing.
    assert final["trailer_plan"].estimated_cost_usd == 0.0
    assert final["trailer_plan"].lower_cost_fallback is None


def test_verifier_rejection_triggers_repair_and_excludes_the_offending_scene(
    tmp_path, registry, constraints, story_map,
):
    bad_segment = make_segment("scene_02", evidence=["scene:scene_02"])  # forbidden tag for family
    good_segment = make_segment("scene_01", evidence=["scene:scene_01"], subtitle="hi")
    composer = FakeComposer([[bad_segment], [good_segment]])

    app = build_pipeline(
        client=FakeLLMClient(), strategist=FakeStrategist(_promise()),
        composer=composer, verifier=FakeVerifier(),
    )
    final = app.invoke(_initial_state(tmp_path, registry, constraints, story_map))

    assert final["validation"].status == "PASS"
    assert len(composer.calls) == 2
    assert composer.calls[0] == []  # nothing excluded on the first attempt
    assert "scene_02" in composer.calls[1]  # excluded after it was rejected


def test_retries_exhausted_fails_closed(tmp_path, registry, constraints, story_map):
    """ARCHITECTURE.md design principle 5 ('fail closed'): a repair loop
    that never produces a clean segment set must end in FAIL, never get
    silently waived through."""
    bad_segment = make_segment("scene_02", evidence=["scene:scene_02"])
    composer = FakeComposer([[bad_segment]] * (DEFAULT_MAX_REPAIR_ATTEMPTS + 2))

    app = build_pipeline(
        client=FakeLLMClient(), strategist=FakeStrategist(_promise()),
        composer=composer, verifier=FakeVerifier(),
    )
    final = app.invoke(_initial_state(tmp_path, registry, constraints, story_map))

    assert final["validation"].status == "FAIL"
    assert final["failures"]


def test_bias_warning_routes_to_needs_approval_not_a_hard_fail(tmp_path, registry, constraints, story_map):
    segments = [make_segment("scene_01", evidence=["scene:scene_01"], subtitle="hi")]
    verifier = FakeVerifier(bias_warnings=["stereotyped personalization"])

    app = build_pipeline(
        client=FakeLLMClient(), strategist=FakeStrategist(_promise("dialect_region")),
        composer=FakeComposer([segments]), verifier=verifier,
    )
    state = _initial_state(tmp_path, registry, constraints, story_map, audience="dialect_region")
    final = app.invoke(state)

    assert final["validation"].status == "NEEDS_APPROVAL"
    assert "stereotyped personalization" in final["validation"].approvals_required


def test_finalize_prices_the_run_through_real_agents_and_a_fake_client(
    tmp_path, registry, constraints, story_map,
):
    """End-to-end through the REAL AudienceStrategist/Composer/SemanticVerifier
    (not fake-agent injection this time), wired to a FakeLLMClient - exercises
    the agents' own parsing logic together with the graph and the cost-
    baseline diffing added to node_finalize, all in one pass."""
    strategist_raw = json.dumps({
        "promise": "p", "emotional_arc": "a", "personalization_notes": [], "bias_warnings": [],
    })
    composer_raw = json.dumps({"segments": [
        {"source_in": "00:00:01.000", "source_out": "00:00:03.000", "video": "scene_01",
         "audio": "dialogue", "subtitle": "hi", "reason": "r", "evidence": ["scene:scene_01"]},
    ]})
    spoiler_raw = json.dumps({"violated_fact_ids": []})
    bias_raw = json.dumps({"warnings": []})
    client = FakeLLMClient([strategist_raw, composer_raw, spoiler_raw, bias_raw])

    app = build_pipeline(
        client=client,
        strategist=AudienceStrategist(client),
        composer=Composer(client),
        verifier=SemanticVerifier(client),
    )
    final = app.invoke(_initial_state(tmp_path, registry, constraints, story_map))

    assert final["validation"].status == "PASS"
    assert final["trailer_plan"].estimated_cost_usd > 0  # four real client.call()s were priced

    entries = final["decision_log"].read_all()
    finalize_entries = [e for e in entries if e["stage"] == "finalize"]
    assert finalize_entries and finalize_entries[0]["cost_usd"] > 0