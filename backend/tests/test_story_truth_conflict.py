"""Required failure mode: a segment relies on a relationship the Story
Mapper flagged as disputed between dialect subtitle tracks - must surface as
a named human-approval requirement, never ship silently. See
ARCHITECTURE.md sections 3.2 and 3.6, and the 'a dialect subtitle changes a
relationship' surprise event."""
from src.models.story_map import Relationship, StoryMap
from src.verification.checks import check_story_truth
from tests.conftest import make_segment


def _story_map_with_relationship(source_conflict: bool) -> StoryMap:
    return StoryMap(
        relationships=[
            Relationship(
                characters=("Mira", "Tomas"),
                kind="sibling",
                evidence_scene_ids=["scene_01"],
                source_conflict=source_conflict,
            )
        ]
    )


def test_unresolved_conflict_requires_approval():
    story_map = _story_map_with_relationship(source_conflict=True)
    segment = make_segment(video="scene_01", evidence=["scene:scene_01"])

    reasons = check_story_truth(segment, story_map)

    assert reasons
    assert any("Mira & Tomas" in r for r in reasons)


def test_resolved_relationship_does_not_require_approval():
    story_map = _story_map_with_relationship(source_conflict=False)
    segment = make_segment(video="scene_01", evidence=["scene:scene_01"])

    assert check_story_truth(segment, story_map) == []


def test_segment_not_touching_the_disputed_scene_is_unaffected():
    story_map = _story_map_with_relationship(source_conflict=True)
    unrelated_segment = make_segment(video="scene_02", evidence=["scene:scene_02"])

    assert check_story_truth(unrelated_segment, story_map) == []