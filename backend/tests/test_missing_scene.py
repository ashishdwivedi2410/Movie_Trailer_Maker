"""Required failure mode: a proposed segment references a scene_id that
doesn't exist in the registry - must be a hard reject. See ARCHITECTURE.md
section 3.6 and the 'model proposes a nonexistent scene' surprise event."""
from src.verification.checks import check_source_accuracy
from tests.conftest import make_segment


def test_missing_scene_is_rejected(registry):
    fake_segment = make_segment(video="scene_99_does_not_exist")
    assert check_source_accuracy(fake_segment, registry) is False


def test_real_scene_passes(registry):
    real_segment = make_segment(video="scene_01")
    assert check_source_accuracy(real_segment, registry) is True