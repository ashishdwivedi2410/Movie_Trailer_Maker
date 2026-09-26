"""Shared fixtures for the required failure-mode tests. This is a small
synthetic episode/contract/policy set - not the real supplied episode, just
enough to exercise every deterministic check independently of any pipeline
wiring."""
import pytest

from src.models.constraint_map import ConstraintMap, RatingRule, RightsRule
from src.models.scene import Scene, SceneRegistry
from src.models.story_map import ProtectedFact, StoryMap
from src.models.trailer import Segment


@pytest.fixture
def registry():
    return SceneRegistry(
        scenes={
            "scene_01": Scene(
                scene_id="scene_01",
                source_in="00:00:01.000",
                source_out="00:00:05.000",
                tags=[],
            ),
            "scene_02": Scene(
                scene_id="scene_02",
                source_in="00:00:06.000",
                source_out="00:00:10.000",
                tags=["intense_violence"],
            ),
            "scene_09_twist": Scene(
                scene_id="scene_09_twist",
                source_in="00:09:00.000",
                source_out="00:09:04.000",
                tags=[],
            ),
        }
    )


@pytest.fixture
def constraints():
    return ConstraintMap(
        rights_rules=[
            RightsRule(
                rule_id="music-03",
                subject_type="music_track",
                subject_id="track_03",
                allowed_territories=["US"],
                allowed_until="2026-10-01",
            ),
        ],
        rating_rules=[
            RatingRule(
                rule_id="family-01",
                audience="family",
                forbidden_tags=["intense_violence"],
            ),
        ],
    )


@pytest.fixture
def story_map():
    return StoryMap(
        protected_facts=[
            ProtectedFact(
                fact_id="twist_reveal",
                description="The mentor is revealed to be the antagonist's brother.",
                scene_ids=["scene_09_twist"],
            ),
        ]
    )


def make_segment(video: str, evidence: list[str] | None = None, **overrides) -> Segment:
    """Small helper so each test doesn't repeat every required Segment field."""
    defaults = dict(
        source_in="00:00:01.000",
        source_out="00:00:03.000",
        video=video,
        audio="dialogue_and_music",
        reason="test segment",
        evidence=evidence if evidence is not None else [f"scene:{video}"],
    )
    defaults.update(overrides)
    return Segment(**defaults)