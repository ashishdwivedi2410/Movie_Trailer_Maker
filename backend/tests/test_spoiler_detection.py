"""Required failure mode: a segment set includes the scene tied to a
protected fact - must be flagged as a spoiler. See ARCHITECTURE.md section
3.6, and the 'historically best-performing scene contains a spoiler'
surprise event."""
from src.verification.checks import check_spoilers_literal
from tests.conftest import make_segment


def test_spoiler_scene_is_flagged(story_map):
    segments = [make_segment(video="scene_09_twist")]
    violated = check_spoilers_literal(segments, story_map)
    assert "twist_reveal" in violated


def test_non_spoiler_segments_pass(story_map):
    segments = [make_segment(video="scene_01")]
    violated = check_spoilers_literal(segments, story_map)
    assert violated == []