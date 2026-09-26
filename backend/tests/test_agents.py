"""Tests for the actual agents (src/agents/*.py) using FakeLLMClient (see
tests/fakes.py) so no real model call happens. Previously these agents had
zero test coverage even though their JSON-parsing and filtering logic -
dropping invalid/excluded/evidence-less segments, deduping bias warnings,
restricting spoiler ids to ones that actually exist - is exactly the kind of
thing a bad refactor could silently break without anyone noticing.
"""
import json

import pytest

from src.agents.audience_strategist import AudienceStrategist
from src.agents.composer import Composer
from src.agents.verifier import SemanticVerifier
from src.models.promise import AudiencePromise
from src.models.story_map import ProtectedFact, StoryMap
from tests.conftest import make_segment
from tests.fakes import FakeLLMClient


def _promise(audience="family"):
    return AudiencePromise(audience=audience, promise="p", emotional_arc="a")


class TestAudienceStrategist:
    def test_parses_response_into_an_audience_promise(self):
        raw = json.dumps({
            "promise": "A thrilling family-friendly adventure.",
            "emotional_arc": "wonder -> tension -> relief",
            "personalization_notes": [
                {"claim": "kid-friendly humor", "grounded": True, "evidence_scene_ids": ["scene_01"]},
            ],
            "bias_warnings": [],
        })
        strategist = AudienceStrategist(FakeLLMClient([raw]))

        promise = strategist.plan_promise("family", StoryMap(), {}, {})

        assert promise.audience == "family"
        assert promise.promise == "A thrilling family-friendly adventure."
        assert promise.personalization_notes[0].grounded is True

    def test_ungrounded_dialect_region_note_gets_flagged_even_if_the_model_missed_it(self):
        """AudienceStrategist._audit_bias - the belt-and-suspenders check the
        (now-removed) dead src/verification/bias_audit.py duplicated."""
        raw = json.dumps({
            "promise": "promise", "emotional_arc": "arc",
            "personalization_notes": [
                {"claim": "this region likes fast pacing", "grounded": False, "evidence_scene_ids": []},
            ],
            "bias_warnings": [],  # model did NOT self-report this
        })
        strategist = AudienceStrategist(FakeLLMClient([raw]))

        promise = strategist.plan_promise("dialect_region", StoryMap(), {}, {})

        assert any("this region likes fast pacing" in w for w in promise.bias_warnings)

    def test_ungrounded_note_for_non_dialect_audience_is_not_auto_flagged(self):
        raw = json.dumps({
            "promise": "promise", "emotional_arc": "arc",
            "personalization_notes": [
                {"claim": "families like happy endings", "grounded": False, "evidence_scene_ids": []},
            ],
            "bias_warnings": [],
        })
        strategist = AudienceStrategist(FakeLLMClient([raw]))

        promise = strategist.plan_promise("family", StoryMap(), {}, {})

        assert promise.bias_warnings == []

    def test_non_json_response_raises_value_error(self):
        strategist = AudienceStrategist(FakeLLMClient(["not valid json"]))
        with pytest.raises(ValueError):
            strategist.plan_promise("family", StoryMap(), {}, {})


class TestComposer:
    def test_keeps_valid_segments(self, registry):
        raw = json.dumps({"segments": [
            {"source_in": "00:00:01.000", "source_out": "00:00:02.000", "video": "scene_01",
             "audio": "dialogue", "reason": "r", "evidence": ["scene:scene_01"]},
        ]})
        composer = Composer(FakeLLMClient([raw]))

        segments = composer.compose("family", _promise(), StoryMap(), registry, 30)

        assert len(segments) == 1
        assert segments[0].video == "scene_01"

    def test_drops_segments_with_no_evidence(self, registry):
        raw = json.dumps({"segments": [
            {"source_in": "00:00:01.000", "source_out": "00:00:02.000", "video": "scene_01",
             "audio": "dialogue", "reason": "r", "evidence": []},
        ]})
        composer = Composer(FakeLLMClient([raw]))

        segments = composer.compose("family", _promise(), StoryMap(), registry, 30)

        assert segments == []

    def test_drops_segments_referencing_a_nonexistent_scene(self, registry):
        """Direct defense against the 'model proposes a nonexistent scene'
        surprise event (ARCHITECTURE.md section 3.1)."""
        raw = json.dumps({"segments": [
            {"source_in": "00:00:01.000", "source_out": "00:00:02.000", "video": "scene_99_missing",
             "audio": "dialogue", "reason": "r", "evidence": ["scene:scene_99_missing"]},
        ]})
        composer = Composer(FakeLLMClient([raw]))

        segments = composer.compose("family", _promise(), StoryMap(), registry, 30)

        assert segments == []

    def test_drops_explicitly_excluded_scenes(self, registry):
        raw = json.dumps({"segments": [
            {"source_in": "00:00:01.000", "source_out": "00:00:02.000", "video": "scene_01",
             "audio": "dialogue", "reason": "r", "evidence": ["scene:scene_01"]},
        ]})
        composer = Composer(FakeLLMClient([raw]))

        segments = composer.compose(
            "family", _promise(), StoryMap(), registry, 30, excluded_scene_ids=["scene_01"],
        )

        assert segments == []

    def test_non_json_response_raises_value_error(self, registry):
        composer = Composer(FakeLLMClient(["not valid json"]))
        with pytest.raises(ValueError):
            composer.compose("family", _promise(), StoryMap(), registry, 30)


class TestSemanticVerifier:
    def test_check_spoilers_filters_to_known_fact_ids_only(self):
        """The model's raw output is not trusted outright - only fact ids
        that actually exist in the story map's protected_facts registry
        survive, per ARCHITECTURE.md design principle 3."""
        story_map = StoryMap(protected_facts=[
            ProtectedFact(fact_id="twist_reveal", description="d", scene_ids=["scene_09"]),
        ])
        raw = json.dumps({"violated_fact_ids": ["twist_reveal", "not_a_real_fact_id"]})
        verifier = SemanticVerifier(FakeLLMClient([raw]))

        result = verifier.check_spoilers([make_segment("scene_01")], story_map)

        assert result == ["twist_reveal"]

    def test_check_spoilers_short_circuits_with_no_protected_facts(self):
        """No protected facts means nothing to spoil - should never even
        make a call (a FakeLLMClient with no queued responses would raise if
        it were called)."""
        verifier = SemanticVerifier(FakeLLMClient([]))
        result = verifier.check_spoilers([make_segment("scene_01")], StoryMap())
        assert result == []

    def test_check_bias_unions_with_the_strategists_own_warnings(self):
        """A second independent check should only ever add coverage, never
        let either check's silence override the other's flag."""
        promise = AudiencePromise(
            audience="dialect_region", promise="p", emotional_arc="a",
            bias_warnings=["strategist already flagged this"],
        )
        raw = json.dumps({"warnings": ["semantic check found this too", "strategist already flagged this"]})
        verifier = SemanticVerifier(FakeLLMClient([raw]))

        result = verifier.check_bias("dialect_region", promise, [make_segment("scene_01")])

        assert "strategist already flagged this" in result
        assert "semantic check found this too" in result
        assert len(result) == 2  # deduplicated, not concatenated

    def test_non_json_response_raises_value_error(self):
        verifier = SemanticVerifier(FakeLLMClient(["not valid json"]))
        with pytest.raises(ValueError):
            verifier.check_bias("family", _promise(), [make_segment("scene_01")])