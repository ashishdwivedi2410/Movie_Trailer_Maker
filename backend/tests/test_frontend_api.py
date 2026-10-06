"""Tests for the routes the web frontend calls: /api/dialects and /api/generate-trailer."""
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import src.api as api
from src.models.trailer import Segment, TrailerPlan, ValidationResult

client = TestClient(api.app)


@pytest.fixture(autouse=True)
def isolated_dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path / "runs"))
    return tmp_path


def _plan(audience: str) -> TrailerPlan:
    return TrailerPlan(
        trailer_id=f"{audience}_v1",
        audience=audience,
        duration_seconds=30,
        audience_promise="promise",
        segments=[Segment(source_in="00:00:10.000", source_out="00:00:20.000", video="s1",
                          audio="x", subtitle="hi", reason="r", evidence=["scene:s1"])],
        validation=ValidationResult(status="PASS", checks_run=["rights"]),
    )


@pytest.fixture
def fake_pipeline(monkeypatch):
    calls = []

    def fake_run_all_trailers(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(trailers={a: _plan(a) for a in kwargs["audiences"]})

    monkeypatch.setattr(api, "run_all_trailers", fake_run_all_trailers)
    return calls


def _files(**overrides):
    f = {
        "subtitle_dialect_1": ("a.srt", b"1\n00:00:01,000 --> 00:00:02,000\nhi\n"),
        "subtitle_dialect_2": ("b.vtt", b"WEBVTT\n"),
        "rating_policies_file": ("policies.json", b"{}"),
        "contracts_file": ("contracts.json", b"{}"),
    }
    f.update(overrides)
    return [(k, v) for k, v in f.items() if v is not None]


def _form(**overrides):
    d = {"scene_descriptions": "scene 1: kitchen", "dialogue_text": "hello", "category": "family"}
    d.update(overrides)
    return {k: v for k, v in d.items() if v is not None}


def _post(files=None, data=None, episodes=(("ep.mp4", b"video"),)):
    multipart = [("episode_files", (n, io.BytesIO(c))) for n, c in episodes]
    multipart += [(k, (n, io.BytesIO(c))) for k, (n, c) in (files if files is not None else _files())]
    return client.post("/api/generate-trailer", files=multipart, data=data if data is not None else _form())


def _field_errors(resp):
    return {e["field"]: e["message"] for e in resp.json()["detail"]}


# --- /api/generate-trailer: shape and routing -------------------------------


@pytest.mark.parametrize("category", ["family", "young_adult"])
def test_runs_only_the_selected_category_and_returns_one_trailer(fake_pipeline, category):
    r = _post(data=_form(category=category))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["audience"] == category            # a single trailer object...
    assert "trailers" not in body                  # ...not the {trailers: {...}} wrapper
    assert body["validation"]["status"] == "PASS"
    assert body["run_id"]
    assert fake_pipeline[0]["audiences"] == (category,)


def test_dialect_region_passes_typed_dialect_to_strategist(fake_pipeline):
    r = _post(data=_form(category="dialect_region", dialect="  Bhojpuri  "))
    assert r.status_code == 200, r.text
    assert r.json()["dialect"] == "Bhojpuri"  # trimmed
    assert fake_pipeline[0]["audience_profiles"]["dialect_region"]["dialect"] == "Bhojpuri"


def test_any_dialect_name_is_accepted(fake_pipeline):
    for name in ("Kanpuri Hindi", "Hinglish", "Bhojpuri (Purvanchal)"):
        assert _post(data=_form(category="dialect_region", dialect=name)).status_code == 200


def test_dialect_ignored_for_other_categories(fake_pipeline):
    r = _post(data=_form(category="family", dialect="Bhojpuri"))
    assert r.status_code == 200 and "dialect" not in r.json()


def test_staged_layout_and_paths_passed_to_pipeline(fake_pipeline):
    _post()
    call = fake_pipeline[0]
    inputs = Path(call["episode_path"])
    assert (inputs / "episode" / "00_ep.mp4").read_bytes() == b"video"
    assert (inputs / "scene_descriptions.txt").read_text() == "scene 1: kitchen"
    assert (inputs / "dialogue.txt").read_text() == "hello"
    assert (inputs / "subtitles" / "track_a.srt").exists()
    assert (inputs / "subtitles" / "track_b.vtt").exists()
    assert Path(call["contracts_path"]).parent == inputs / "contracts"
    assert Path(call["policies_path"]).parent == inputs / "policies"


def test_multiple_episode_files_are_all_saved(fake_pipeline):
    _post(episodes=(("a.mp4", b"1"), ("b.mov", b"2")))
    episode_dir = Path(fake_pipeline[0]["episode_path"]) / "episode"
    assert sorted(p.name for p in episode_dir.iterdir()) == ["00_a.mp4", "01_b.mov"]


def test_each_request_gets_its_own_run_dir(fake_pipeline):
    _post()
    _post()
    assert fake_pipeline[0]["episode_path"] != fake_pipeline[1]["episode_path"]


def test_uploaded_scene_file_and_reference_files(fake_pipeline):
    r = _post(
        files=_files(
            scene_descriptions_file=("scenes.json", b'[{"id": "s1"}]'),
            audience_profiles_file=("p.json", json.dumps({"family": {"likes": "cozy"}}).encode()),
            historic_performance_file=("h.csv", b"metric,value\nctr,0.4\n"),
            cost_sheet_file=("cost.csv", b"a,b\n1,2\n"),
        ),
        data=_form(scene_descriptions=""),
    )
    assert r.status_code == 200, r.text
    call = fake_pipeline[0]
    assert (Path(call["episode_path"]) / "scene_descriptions.json").exists()
    assert call["audience_profiles"]["family"] == {"likes": "cozy"}
    assert call["historic_performance"]["family"] == {"rows": [{"metric": "ctr", "value": "0.4"}]}


# --- validation ------------------------------------------------------------


def test_missing_everything_reports_each_field(fake_pipeline):
    r = client.post("/api/generate-trailer", data={})
    assert r.status_code == 422
    assert set(_field_errors(r)) == {
        "episode_files", "scene_descriptions", "dialogue_text", "subtitle_dialect_1",
        "subtitle_dialect_2", "rating_policies_file", "contracts_file", "category",
    }
    assert fake_pipeline == []


def test_wrong_extensions_rejected(fake_pipeline):
    r = _post(files=_files(subtitle_dialect_1=("a.txt", b"x"), contracts_file=("c.docx", b"x")))
    assert r.status_code == 422
    errs = _field_errors(r)
    assert "subtitle_dialect_1" in errs and "contracts_file" in errs
    assert fake_pipeline == []


def test_dialect_region_requires_a_dialect(fake_pipeline):
    assert "dialect" in _field_errors(_post(data=_form(category="dialect_region")))
    assert "dialect" in _field_errors(_post(data=_form(category="dialect_region", dialect="   ")))
    assert fake_pipeline == []


def test_dialect_too_long_or_with_control_chars_rejected(fake_pipeline):
    assert "dialect" in _field_errors(_post(data=_form(category="dialect_region", dialect="x" * 61)))
    assert "dialect" in _field_errors(_post(data=_form(category="dialect_region", dialect="bad\x00name")))
    assert fake_pipeline == []


def test_unknown_category_rejected(fake_pipeline):
    assert "category" in _field_errors(_post(data=_form(category="everyone")))


def test_invalid_reference_json_is_a_field_error_and_cleans_up(fake_pipeline, tmp_path):
    r = _post(files=_files(audience_profiles_file=("p.json", b"{not json")))
    assert r.status_code == 422 and "audience_profiles_file" in _field_errors(r)
    runs = tmp_path / "runs"
    assert not runs.exists() or list(runs.iterdir()) == []


def test_oversized_upload_413_and_cleaned_up(fake_pipeline, tmp_path, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "0.001")  # ~1 KB
    r = _post(episodes=(("big.mp4", b"x" * 5000),))
    assert r.status_code == 413
    assert fake_pipeline == []
    runs = tmp_path / "runs"
    assert not runs.exists() or list(runs.iterdir()) == []


def test_malicious_filenames_stay_inside_run_dir(fake_pipeline, tmp_path):
    r = _post(files=_files(contracts_file=("../../../evil.json", b"{}")),
              episodes=(("..\\..\\x.mp4", b"v"),))
    assert r.status_code == 200, r.text
    run_root = (tmp_path / "runs").resolve()
    for p in run_root.rglob("*"):
        assert run_root in p.resolve().parents or p.resolve() == run_root
    assert not (tmp_path / "evil.json").exists()


# --- current reality: ingest parsers are still stubs -------------------------


def test_returns_501_while_ingest_is_not_implemented():
    # No fake_pipeline fixture: this runs the real run_all_trailers.
    r = _post()
    assert r.status_code == 501
    assert "not" in r.json()["detail"].lower()