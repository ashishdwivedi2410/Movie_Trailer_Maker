"""Required failure mode: a segment uses a music track outside its allowed
territory, or after its rights have expired - both must be flagged. See
ARCHITECTURE.md sections 3.3 and 3.6, and the 'music rights expire' surprise
event."""
from src.verification.checks import check_rights
from tests.conftest import make_segment


def test_territory_violation_is_flagged(constraints):
    segment = make_segment(video="scene_01", evidence=["scene:scene_01", "contract:music-03"])
    violations = check_rights(segment, constraints, territory="IN")
    assert any("territory_not_allowed" in v for v in violations)


def test_expired_rights_are_flagged(constraints):
    segment = make_segment(video="scene_01", evidence=["scene:scene_01", "contract:music-03"])
    violations = check_rights(segment, constraints, territory="US", as_of_date="2026-11-01")
    assert any("rights_expired" in v for v in violations)


def test_valid_rights_pass(constraints):
    segment = make_segment(video="scene_01", evidence=["scene:scene_01", "contract:music-03"])
    violations = check_rights(segment, constraints, territory="US", as_of_date="2026-09-01")
    assert violations == []


def test_unknown_contract_reference_is_flagged(constraints):
    segment = make_segment(video="scene_01", evidence=["scene:scene_01", "contract:unknown-rule"])
    violations = check_rights(segment, constraints, territory="US")
    assert any("unverifiable_contract_reference" in v for v in violations)