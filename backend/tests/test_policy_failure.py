"""Required failure mode: a segment's underlying scene carries a tag
forbidden by the target audience's rating policy - must be flagged. See
ARCHITECTURE.md section 3.3."""
from src.verification.checks import check_rating
from tests.conftest import make_segment


def test_forbidden_tag_is_flagged_for_family(registry, constraints):
    segment = make_segment(video="scene_02")  # tagged intense_violence
    violations = check_rating(segment, constraints, audience="family", registry=registry)
    assert any("forbidden_tags" in v for v in violations)


def test_clean_scene_passes_for_family(registry, constraints):
    segment = make_segment(video="scene_01")
    violations = check_rating(segment, constraints, audience="family", registry=registry)
    assert violations == []


def test_rule_for_other_audience_does_not_apply(registry, constraints):
    # the family-01 rule shouldn't restrict the young_adult audience
    segment = make_segment(video="scene_02")
    violations = check_rating(segment, constraints, audience="young_adult", registry=registry)
    assert violations == []