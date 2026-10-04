"""run_all_trailers(audiences=...) runs only the requested audiences."""
from types import SimpleNamespace

import pytest

from src.graph import pipeline
from src.models.constraint_map import ConstraintMap
from src.models.promise import AudiencePromise
from src.models.scene import SceneRegistry
from src.models.story_map import StoryMap
from src.observability.decision_log import DecisionLog


@pytest.fixture
def stubbed(monkeypatch):
    monkeypatch.setattr(pipeline, "load_episode", lambda p: SceneRegistry(scenes={}))
    monkeypatch.setattr(pipeline, "load_dialogue", lambda p: "")
    monkeypatch.setattr(pipeline, "load_subtitle_track", lambda p, t: "")
    monkeypatch.setattr(pipeline, "parse_contracts", lambda p: "")
    monkeypatch.setattr(pipeline, "parse_policies", lambda p: "")
    monkeypatch.setattr(pipeline, "LLMClient", lambda: SimpleNamespace(total_cost_usd=0.0))
    monkeypatch.setattr(pipeline, "StoryMapper", lambda c: SimpleNamespace(build=lambda *a: StoryMap()))
    monkeypatch.setattr(pipeline, "ConstraintCompiler", lambda c: SimpleNamespace(build=lambda *a: ConstraintMap()))

    seen = []

    class FakeApp:
        def invoke(self, state):
            seen.append(state["audience"])
            plan = SimpleNamespace(trailer_id=f"{state['audience']}_v1", segments=[])
            return {"trailer_plan": plan,
                    "audience_promise": AudiencePromise(audience=state["audience"], promise="p", emotional_arc="a")}

    monkeypatch.setattr(pipeline, "build_pipeline", lambda client: FakeApp())
    monkeypatch.setattr(pipeline.EvidenceGraph, "index", lambda self, plan: None)
    return seen


def _run(tmp_path, **kw):
    return pipeline.run_all_trailers(
        episode_path="e", contracts_path="c", policies_path="p", territory="US",
        audience_profiles={}, historic_performance={}, duration_by_audience={},
        decision_log=DecisionLog(path=str(tmp_path / "log.jsonl")), **kw)


def test_default_runs_all_three(stubbed, tmp_path):
    result = _run(tmp_path)
    assert stubbed == ["family", "young_adult", "dialect_region"]
    assert set(result.trailers) == set(stubbed)


def test_only_requested_audience_runs(stubbed, tmp_path):
    result = _run(tmp_path, audiences=("young_adult",))
    assert stubbed == ["young_adult"]
    assert list(result.trailers) == ["young_adult"]


@pytest.mark.parametrize("bad", [(), ("nope",), ("family", "nope")])
def test_rejects_unknown_or_empty_audiences(stubbed, tmp_path, bad):
    with pytest.raises(ValueError):
        _run(tmp_path, audiences=bad)
    assert stubbed == []