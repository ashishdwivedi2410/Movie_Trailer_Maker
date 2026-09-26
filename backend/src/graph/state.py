"""LangGraph pipeline state - the working memory passed node to node for a
single audience's strategize -> compose -> verify -> repair loop. See
ARCHITECTURE.md sections 2 and 4.

One of these runs per audience (family / young_adult / dialect_region); the
story map and constraint map are built once, upstream, and passed in as
already-computed values (see run_all_trailers in pipeline.py) rather than
being rebuilt inside this per-audience loop.
"""
from typing import TypedDict

from src.models.constraint_map import ConstraintMap
from src.models.promise import AudiencePromise
from src.models.scene import SceneRegistry
from src.models.story_map import StoryMap
from src.models.trailer import Segment, TrailerPlan, ValidationResult
from src.observability.decision_log import DecisionLog


class PipelineState(TypedDict, total=False):
    # --- set once, before the graph runs ---
    audience: str
    story_map: StoryMap
    constraint_map: ConstraintMap
    scene_registry: SceneRegistry
    audience_profile: dict
    historic_performance: dict
    territory: str
    duration_seconds: int
    as_of_date: str | None
    max_repair_attempts: int
    decision_log: DecisionLog

    # --- produced as the graph runs ---
    audience_promise: AudiencePromise
    segments: list[Segment]
    excluded_scene_ids: list[str]
    repair_attempts: int
    failures: list[str]
    warnings: list[str]
    bias_warnings: list[str]
    validation: ValidationResult
    trailer_plan: TrailerPlan