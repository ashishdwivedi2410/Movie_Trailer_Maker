"""Deterministic verification checks - plain code, not LLM calls, so they're
auditable and can't be talked out of a rejection. See ARCHITECTURE.md section
3.6 and section 6 ('why generation and validation stay independent'). These
run BEFORE the semantic checks in src/agents/verifier.py, and a failure here
blocks a trailer regardless of what the semantic checks find.
"""
from src.models.constraint_map import ConstraintMap
from src.models.scene import SceneRegistry
from src.models.story_map import StoryMap
from src.models.trailer import Segment


def check_source_accuracy(segment: Segment, registry: SceneRegistry) -> bool:
    """Every scene_id a segment cites must exist in the registry. This is the
    direct defense against a model proposing a scene that doesn't exist."""
    return registry.exists(segment.video)


def check_rights(
    segment: Segment,
    constraints: ConstraintMap,
    territory: str,
    as_of_date: str | None = None,
) -> list[str]:
    """Checks every contract reference in segment.evidence (entries shaped
    like "contract:<rule_id>") against the constraint map. Returns violated
    rule descriptions, empty if clean. An evidence entry that references a
    contract id not present in the constraint map is itself a violation -
    an unverifiable rights claim is treated as a failed one, not a pass."""
    violations = []
    for ref in segment.evidence:
        if not ref.startswith("contract:"):
            continue
        rule_id = ref.split(":", 1)[1]
        rule = next((r for r in constraints.rights_rules if r.rule_id == rule_id), None)
        if rule is None:
            violations.append(f"unverifiable_contract_reference:{ref}")
            continue
        if rule.allowed_territories and territory not in rule.allowed_territories:
            violations.append(f"territory_not_allowed:{rule.rule_id}:{territory}")
        if rule.allowed_until and as_of_date and as_of_date > rule.allowed_until:
            violations.append(f"rights_expired:{rule.rule_id}:expired_{rule.allowed_until}")
    return violations


def check_rating(
    segment: Segment,
    constraints: ConstraintMap,
    audience: str,
    registry: SceneRegistry,
) -> list[str]:
    """Checks a segment's underlying scene tags against the audience's rating
    rules. Returns violated rule descriptions, empty if clean."""
    scene = registry.get(segment.video)
    if scene is None:
        return []  # check_source_accuracy already covers a missing scene
    scene_tags = set(scene.tags)
    violations = []
    for rule in constraints.rating_rules:
        if rule.audience != audience:
            continue
        forbidden_present = scene_tags.intersection(rule.forbidden_tags)
        if forbidden_present:
            violations.append(f"forbidden_tags:{rule.rule_id}:{sorted(forbidden_present)}")
    return violations


def _to_seconds(timecode: str) -> float:
    """Parses "HH:MM:SS.mmm" into seconds."""
    hours, minutes, seconds = timecode.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def check_timing(segments: list[Segment], target_duration: int, tolerance: int = 2) -> bool:
    """True if the summed segment duration is within `tolerance` seconds of
    the target duration."""
    total = sum(_to_seconds(seg.source_out) - _to_seconds(seg.source_in) for seg in segments)
    return abs(total - target_duration) <= tolerance


def check_spoilers_literal(segments: list[Segment], story_map: StoryMap) -> list[str]:
    """Returns protected_fact ids whose scene_ids literally appear among the
    segments' chosen scenes. This is the fast, literal check - it does not
    catch a spoiler merely implied by dialogue or juxtaposition; that is
    src.agents.verifier.SemanticVerifier.check_spoilers's job."""
    used_scene_ids = {seg.video for seg in segments}
    return [
        fact.fact_id
        for fact in story_map.protected_facts
        if used_scene_ids.intersection(fact.scene_ids)
    ]


def check_story_truth(segment: Segment, story_map: StoryMap) -> list[str]:
    """Story-truth check (#3 in ARCHITECTURE.md section 3.6): a segment built
    on a relationship the Story Mapper flagged as `source_conflict` - meaning
    the two dialect subtitle tracks disagree on what that relationship even
    is (section 3.2) - cannot ship as settled fact. Grounded, not merely
    plausible, is the bar (design principle 2), and an unresolved source
    disagreement fails that bar.

    This is the direct handler for the "a dialect subtitle changes a
    relationship" surprise event (section 7): the Story Mapper detects and
    records the conflict on the Relationship itself; this check is what
    stops that flag from being silently dropped once segments are composed,
    by turning it into a named human-approval requirement (section 1: fail
    closed) instead of the trailer quietly shipping with one track's version
    of the truth.

    Returns approval-required reasons, empty if the segment doesn't cite any
    scene involved in an unresolved relationship conflict."""
    cited_scene_ids = {segment.video}
    cited_scene_ids.update(
        ref.split(":", 1)[1] for ref in segment.evidence if ref.startswith("scene:")
    )

    reasons = []
    for relationship in story_map.relationships:
        if not relationship.source_conflict:
            continue
        if cited_scene_ids.intersection(relationship.evidence_scene_ids):
            characters = " & ".join(relationship.characters)
            reasons.append(
                f"story_truth: relationship '{characters}' (claimed as '{relationship.kind}') "
                f"is disputed between dialect subtitle tracks and needs human resolution of "
                f"the canonical track before this segment ships (video={segment.video})"
            )
    return reasons


def check_accessibility(segment: Segment) -> bool:
    """True if the segment carries readable subtitle/text content - a trailer
    should not depend only on an audio cue to convey meaning."""
    return bool(segment.subtitle and segment.subtitle.strip())


def run_deterministic_checks(
    segments: list[Segment],
    registry: SceneRegistry,
    constraints: ConstraintMap,
    story_map: StoryMap,
    audience: str,
    territory: str,
    target_duration: int,
    as_of_date: str | None = None,
) -> dict:
    """Runs every deterministic check and returns a summary:
    {"checks_run": [...], "failures": [...], "warnings": [...],
    "approvals_required": [...]}. Any failure should block the trailer (or
    send it back to the Composer for repair); warnings should not block it
    but must be surfaced in the final ValidationResult.warnings;
    approvals_required (currently just the story-truth check) means the
    trailer can ship but needs a named human sign-off - it should be merged
    into ValidationResult.approvals_required alongside the semantic bias
    check's warnings, per ARCHITECTURE.md section 1 ("fail closed").
    """
    checks_run: list[str] = []
    failures: list[str] = []
    warnings: list[str] = []
    approvals_required: list[str] = []

    checks_run.append("source_accuracy")
    for seg in segments:
        if not check_source_accuracy(seg, registry):
            failures.append(f"source_accuracy: segment references nonexistent scene '{seg.video}'")

    checks_run.append("rights")
    for seg in segments:
        for violation in check_rights(seg, constraints, territory, as_of_date):
            failures.append(f"rights: {violation} (video={seg.video})")

    checks_run.append("rating")
    for seg in segments:
        for violation in check_rating(seg, constraints, audience, registry):
            failures.append(f"rating: {violation} (video={seg.video})")

    checks_run.append("timing")
    if not check_timing(segments, target_duration):
        warnings.append(f"timing: total duration deviates from target {target_duration}s beyond tolerance")

    checks_run.append("spoilers_literal")
    for fact_id in check_spoilers_literal(segments, story_map):
        failures.append(f"spoiler: segment set includes a scene protected by fact '{fact_id}'")

    checks_run.append("story_truth")
    for seg in segments:
        approvals_required.extend(check_story_truth(seg, story_map))

    checks_run.append("accessibility")
    for seg in segments:
        if not check_accessibility(seg):
            warnings.append(f"accessibility: segment for video={seg.video} has no subtitle text")

    return {
        "checks_run": checks_run,
        "failures": failures,
        "warnings": warnings,
        "approvals_required": approvals_required,
    }