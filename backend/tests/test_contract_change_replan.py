"""Required failure mode: a contract changes mid-run (e.g. music rights
expire) - only the segments/trailers actually citing that contract should be
flagged for replanning, not every trailer. See ARCHITECTURE.md section 3.8
and the 'music rights expire after the first trailer plan is created'
surprise event."""
from src.models.trailer import TrailerPlan, ValidationResult
from src.replanning.change_handler import ChangeHandler
from src.replanning.evidence_graph import EvidenceGraph
from tests.conftest import make_segment


def _trailer(trailer_id, audience, segments):
    return TrailerPlan(
        trailer_id=trailer_id,
        audience=audience,
        duration_seconds=30,
        audience_promise="test promise",
        segments=segments,
        validation=ValidationResult(status="PASS"),
    )


def test_only_affected_trailer_is_flagged_for_replan():
    graph = EvidenceGraph()

    family_trailer = _trailer(
        "family_v1",
        "family",
        [make_segment(video="scene_01", evidence=["scene:scene_01", "contract:music-03"])],
    )
    young_adult_trailer = _trailer(
        "young_adult_v1",
        "young_adult",
        [make_segment(video="scene_02", evidence=["scene:scene_02"])],  # no music-03 reference
    )
    graph.index(family_trailer)
    graph.index(young_adult_trailer)

    handler = ChangeHandler(graph)
    result = handler.handle_change("contract:music-03", reason="music rights expired")

    assert result.needs_replan is True
    assert result.affected_trailer_ids == {"family_v1"}
    assert "young_adult_v1" not in result.affected_trailer_ids


def test_reindexing_a_trailer_drops_stale_segments():
    graph = EvidenceGraph()
    v1 = _trailer(
        "dialect_region_v1",
        "dialect_region",
        [make_segment(video="scene_01", evidence=["scene:scene_01", "contract:music-03"])],
    )
    graph.index(v1)

    # A repair replaced the segment that cited the now-expired track
    v2 = _trailer(
        "dialect_region_v1",
        "dialect_region",
        [make_segment(video="scene_02", evidence=["scene:scene_02"])],
    )
    graph.index(v2)

    handler = ChangeHandler(graph)
    result = handler.handle_change("contract:music-03", reason="music rights expired")
    assert result.needs_replan is False  # the repaired version no longer cites it