"""Wires the per-audience LangGraph state machine described in
ARCHITECTURE.md section 2:

    strategize -> compose -> verify -- fail, retries left --> compose (loop)
                                     -- pass, or retries exhausted --> finalize

Deterministic checks (src.verification.checks) always run before the two
semantic checks (src.agents.verifier.SemanticVerifier) inside the verify
node, and a failure from either blocks the trailer or sends it back to the
Composer - the graph structure is what makes generation and verification
independent, not agent discipline. See ARCHITECTURE.md section 6.
"""
from dataclasses import dataclass
from typing import Literal

from langgraph.graph import END, StateGraph

from src.agents.audience_strategist import AudienceStrategist
from src.agents.composer import Composer
from src.agents.constraint_compiler import ConstraintCompiler
from src.agents.story_mapper import StoryMapper
from src.agents.verifier import SemanticVerifier
from src.graph.state import PipelineState
from src.ingest.contract_parser import parse_contracts
from src.ingest.episode_loader import load_dialogue, load_episode, load_subtitle_track
from src.ingest.policy_parser import parse_policies
from src.llm.client import LLMClient
from src.models.constraint_map import ConstraintMap
from src.models.story_map import StoryMap
from src.models.trailer import TrailerPlan, ValidationResult
from src.observability.decision_log import DecisionLog
from src.verification.checks import (
    check_rating,
    check_rights,
    check_source_accuracy,
    check_spoilers_literal,
    run_deterministic_checks,
)

DEFAULT_MAX_REPAIR_ATTEMPTS = 2
AUDIENCES = ("family", "young_adult", "dialect_region")


def build_pipeline(
    client: LLMClient | None = None,
    strategist: AudienceStrategist | None = None,
    composer: Composer | None = None,
    verifier: SemanticVerifier | None = None,
):
    """Builds and compiles the per-audience graph. Agents can be injected
    (used by tests to run the graph with fakes, no real LLM calls) - if
    omitted, real agents are built from `client` (or a fresh LLMClient)."""
    client = client or LLMClient()
    strategist = strategist or AudienceStrategist(client)
    composer = composer or Composer(client)
    verifier = verifier or SemanticVerifier(client)

    def node_strategize(state: PipelineState) -> dict:
        promise = strategist.plan_promise(
            audience=state["audience"],
            story_map=state["story_map"],
            audience_profile=state.get("audience_profile", {}),
            historic_performance=state.get("historic_performance", {}),
        )
        state["decision_log"].record(
            stage="strategize",
            audience=state["audience"],
            notes=promise.promise,
        )
        return {"audience_promise": promise}

    def node_compose(state: PipelineState) -> dict:
        segments = composer.compose(
            audience=state["audience"],
            audience_promise=state["audience_promise"],
            story_map=state["story_map"],
            registry=state["scene_registry"],
            duration_seconds=state["duration_seconds"],
            excluded_scene_ids=state.get("excluded_scene_ids", []),
        )
        state["decision_log"].record(
            stage="compose",
            audience=state["audience"],
            output_refs=[seg.video for seg in segments],
            revision_of=f"attempt_{state.get('repair_attempts', 0)}",
        )
        return {"segments": segments}

    def node_verify(state: PipelineState) -> dict:
        segments = state["segments"]
        registry = state["scene_registry"]
        constraints = state["constraint_map"]
        story_map = state["story_map"]
        audience = state["audience"]
        territory = state["territory"]
        as_of_date = state.get("as_of_date")

        det_result = run_deterministic_checks(
            segments, registry, constraints, story_map, audience, territory,
            state["duration_seconds"], as_of_date,
        )
        implied_spoiler_facts = verifier.check_spoilers(segments, story_map)
        bias_warnings = verifier.check_bias(audience, state["audience_promise"], segments)

        failures = list(det_result["failures"])
        for fact_id in implied_spoiler_facts:
            failures.append(f"spoiler_implied: segment set implies protected fact '{fact_id}'")

        offending = _offending_scene_ids(
            segments, registry, constraints, story_map, audience, territory, as_of_date
        )
        literal_violated = set(check_spoilers_literal(segments, story_map))
        for fact in story_map.protected_facts:
            if fact.fact_id in literal_violated or fact.fact_id in implied_spoiler_facts:
                offending.update(fact.scene_ids)

        state["decision_log"].record(
            stage="verify",
            audience=audience,
            verification_result={
                "failures": failures,
                "warnings": det_result["warnings"],
                "bias_warnings": bias_warnings,
            },
        )

        new_excluded = list(set(state.get("excluded_scene_ids", [])) | offending)
        return {
            "failures": failures,
            "warnings": det_result["warnings"],
            "bias_warnings": bias_warnings,
            "excluded_scene_ids": new_excluded,
            "repair_attempts": state.get("repair_attempts", 0) + (1 if failures else 0),
        }

    def _offending_scene_ids(
        segments, registry, constraints, story_map, audience, territory, as_of_date
    ) -> set[str]:
        """Which segments' scene ids to exclude on the next Composer attempt -
        determined by re-running per-segment checks, not by parsing failure
        message strings."""
        offending: set[str] = set()
        for seg in segments:
            if not check_source_accuracy(seg, registry):
                offending.add(seg.video)
                continue  # rights/rating are meaningless for a scene that doesn't exist
            if check_rights(seg, constraints, territory, as_of_date):
                offending.add(seg.video)
            if check_rating(seg, constraints, audience, registry):
                offending.add(seg.video)
        return offending

    def should_repair(state: PipelineState) -> Literal["compose", "finalize"]:
        max_attempts = state.get("max_repair_attempts", DEFAULT_MAX_REPAIR_ATTEMPTS)
        if state.get("failures") and state.get("repair_attempts", 0) <= max_attempts:
            return "compose"
        return "finalize"

    def node_finalize(state: PipelineState) -> dict:
        failures = state.get("failures", [])
        warnings = state.get("warnings", [])
        bias_warnings = state.get("bias_warnings", [])

        if failures:
            status = "FAIL"
        elif bias_warnings:
            status = "NEEDS_APPROVAL"
        elif warnings:
            status = "PASS_WITH_WARNINGS"
        else:
            status = "PASS"

        validation = ValidationResult(
            status=status,
            checks_run=[
                "source_accuracy", "rights", "rating", "timing",
                "spoilers_literal", "spoilers_implied", "bias", "accessibility",
            ],
            warnings=warnings,
            approvals_required=list(bias_warnings),
        )
        trailer_plan = TrailerPlan(
            trailer_id=f"{state['audience']}_v1",
            audience=state["audience"],
            duration_seconds=state["duration_seconds"],
            audience_promise=state["audience_promise"].promise,
            segments=state["segments"],
            validation=validation,
        )
        state["decision_log"].record(stage="finalize", audience=state["audience"], notes=status)
        return {"trailer_plan": trailer_plan, "validation": validation}

    graph = StateGraph(PipelineState)
    graph.add_node("strategize", node_strategize)
    graph.add_node("compose", node_compose)
    graph.add_node("verify", node_verify)
    graph.add_node("finalize", node_finalize)

    graph.set_entry_point("strategize")
    graph.add_edge("strategize", "compose")
    graph.add_edge("compose", "verify")
    graph.add_conditional_edges("verify", should_repair, {"compose": "compose", "finalize": "finalize"})
    graph.add_edge("finalize", END)

    return graph.compile()


@dataclass
class RunResult:
    story_map: StoryMap
    constraint_map: ConstraintMap
    trailers: dict[str, TrailerPlan]


def run_all_trailers(
    episode_path: str,
    contracts_path: str,
    policies_path: str,
    territory: str,
    audience_profiles: dict[str, dict],
    historic_performance: dict[str, dict],
    duration_by_audience: dict[str, int],
    decision_log: DecisionLog,
    client: LLMClient | None = None,
) -> RunResult:
    """Ingests once, builds the story/constraint maps once, then runs the
    per-audience graph for each of AUDIENCES. This is the top-level entry
    point src/main.py and src/api.py call. Returns the story map and
    constraint map alongside the three trailers since the submission
    structure requires story_map.json / constraint_map.json as their own
    files, not just embedded in each trailer.

    NOTE: load_episode / parse_contracts / parse_policies in src/ingest/ are
    still stubs pending a decision on the real supplied file formats - this
    function will raise NotImplementedError until those are filled in. The
    graph wiring above does not depend on that decision and is independently
    runnable/testable with injected agents (see validate_pipeline.py-style
    tests using build_pipeline() directly).
    """
    client = client or LLMClient()

    registry = load_episode(episode_path)
    dialogue = load_dialogue(episode_path)
    subtitle_a = load_subtitle_track(episode_path, "track_a")
    subtitle_b = load_subtitle_track(episode_path, "track_b")
    contracts_text = parse_contracts(contracts_path)
    policies_text = parse_policies(policies_path)

    story_map = StoryMapper(client).build(registry, dialogue, subtitle_a, subtitle_b)
    constraint_map = ConstraintCompiler(client).build(contracts_text, policies_text)

    app = build_pipeline(client)
    results: dict[str, TrailerPlan] = {}

    for audience in AUDIENCES:
        initial_state: PipelineState = {
            "audience": audience,
            "story_map": story_map,
            "constraint_map": constraint_map,
            "scene_registry": registry,
            "audience_profile": audience_profiles.get(audience, {}),
            "historic_performance": historic_performance.get(audience, {}),
            "territory": territory,
            "duration_seconds": duration_by_audience.get(audience, 30),
            "max_repair_attempts": DEFAULT_MAX_REPAIR_ATTEMPTS,
            "decision_log": decision_log,
            "excluded_scene_ids": [],
            "repair_attempts": 0,
        }
        final_state = app.invoke(initial_state)
        results[audience] = final_state["trailer_plan"]

    return RunResult(story_map=story_map, constraint_map=constraint_map, trailers=results)