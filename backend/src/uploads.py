"""Validates and stages the frontend's multipart upload for one trailer run.

Every request gets its own directory, so concurrent runs cannot overwrite
each other, and the client never chooses a filesystem path - uploaded
filenames are sanitised and only ever used as a suffix inside that directory:

    <RUNS_DIR>/<run_id>/
        inputs/                      <- passed to the pipeline as episode_path
            episode/00_<name>        episode video file(s)
            scene_descriptions.txt   from the textarea, or
            scene_descriptions.<ext> from the uploaded file
            dialogue.txt
            subtitles/track_a.<ext>  "first dialect subtitle track"
            subtitles/track_b.<ext>  "second dialect subtitle track"
            contracts/<name>
            policies/<name>
            cost_sheet.<ext>         optional, stored for later use
        out/                         decision_log.jsonl etc.

The src/ingest/ parsers (still stubs) should read from that layout.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile

VALID_CATEGORIES = ("family", "young_adult", "dialect_region")
MAX_DIALECT_CHARS = 60

SUBTITLE_EXT = {".srt", ".vtt"}
DOC_EXT = {".json", ".pdf"}
SCENE_EXT = {".json", ".txt"}
REFERENCE_EXT = {".json", ".csv"}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".mpg", ".mpeg"}


def runs_root() -> Path:
    return Path(os.getenv("RUNS_DIR", "runs"))


def max_upload_bytes() -> int:
    return int(float(os.getenv("MAX_UPLOAD_MB", "500")) * 1024 * 1024)


def field_errors(errors: list[tuple[str, str]], status: int = 422) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail=[{"field": field, "message": message} for field, message in errors],
    )


def _present(upload: UploadFile | None) -> bool:
    return upload is not None and bool(upload.filename)


def _ext(upload: UploadFile) -> str:
    return Path(upload.filename or "").suffix.lower()


def _clean_name(filename: str | None, fallback: str) -> str:
    name = Path((filename or "").replace("\\", "/")).name
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name).lstrip(".")
    return name or fallback


def _save(upload: UploadFile, dest: Path, field: str) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    limit = max_upload_bytes()
    written = 0
    too_big = False
    with dest.open("wb") as out:
        while chunk := upload.file.read(1024 * 1024):
            written += len(chunk)
            if written > limit:
                too_big = True
                break
            out.write(chunk)
    if too_big:
        dest.unlink(missing_ok=True)
        raise field_errors(
            [(field, f"{upload.filename} is larger than the {limit // (1024 * 1024)} MB limit.")],
            status=413,
        )
    return dest


def _validate(
    *,
    episode_files: list[UploadFile],
    scene_descriptions: str,
    scene_descriptions_file: UploadFile | None,
    dialogue_text: str,
    subtitle_dialect_1: UploadFile | None,
    subtitle_dialect_2: UploadFile | None,
    rating_policies_file: UploadFile | None,
    contracts_file: UploadFile | None,
    audience_profiles_file: UploadFile | None,
    historic_performance_file: UploadFile | None,
    cost_sheet_file: UploadFile | None,
    category: str,
    dialect: str,
) -> list[tuple[str, str]]:
    errors: list[tuple[str, str]] = []

    episodes = [f for f in episode_files if _present(f)]
    if not episodes:
        errors.append(("episode_files", "Upload at least one episode video or clip."))
    for f in episodes:
        if _ext(f) not in VIDEO_EXT:
            errors.append(("episode_files", f"{f.filename} is not a supported video file."))

    if not scene_descriptions.strip() and not _present(scene_descriptions_file):
        errors.append(("scene_descriptions", "Add scene descriptions as text, or upload a file."))
    if _present(scene_descriptions_file) and _ext(scene_descriptions_file) not in SCENE_EXT:
        errors.append(("scene_descriptions_file", "Scene descriptions file must be .json or .txt."))

    if not dialogue_text.strip():
        errors.append(("dialogue_text", "Enter the source dialogue."))

    for name, upload, label in (
        ("subtitle_dialect_1", subtitle_dialect_1, "first"),
        ("subtitle_dialect_2", subtitle_dialect_2, "second"),
    ):
        if not _present(upload):
            errors.append((name, f"Upload the {label} dialect subtitle track (.srt/.vtt)."))
        elif _ext(upload) not in SUBTITLE_EXT:
            errors.append((name, "Subtitle file must be .srt or .vtt."))

    for name, upload, label in (
        ("rating_policies_file", rating_policies_file, "rating policies"),
        ("contracts_file", contracts_file, "contracts"),
    ):
        if not _present(upload):
            errors.append((name, f"Upload a {label} file (.json or .pdf)."))
        elif _ext(upload) not in DOC_EXT:
            errors.append((name, f"{label.capitalize()} file must be .json or .pdf."))

    for name, upload in (
        ("audience_profiles_file", audience_profiles_file),
        ("historic_performance_file", historic_performance_file),
        ("cost_sheet_file", cost_sheet_file),
    ):
        if _present(upload) and _ext(upload) not in REFERENCE_EXT:
            errors.append((name, "File must be .json or .csv."))

    if category not in VALID_CATEGORIES:
        errors.append(("category", "Select a trailer category."))
    elif category == "dialect_region":
        if not dialect:
            errors.append(("dialect", "Enter the dialect for the regional campaign."))
        elif len(dialect) > MAX_DIALECT_CHARS:
            errors.append(("dialect", f"Dialect must be {MAX_DIALECT_CHARS} characters or fewer."))
        elif any(ord(c) < 32 or ord(c) == 127 for c in dialect):
            errors.append(("dialect", "Dialect contains invalid characters."))

    return errors


def _parse_reference(path: Path, field: str, audience: str) -> dict[str, dict]:
    """Reads an optional audience-profiles / historic-performance file into
    the {audience: {...}} shape run_all_trailers() expects.

    JSON keyed by audience name is used as-is; any other JSON is treated as
    the data for the selected audience; CSV becomes {"rows": [...]}.
    """
    try:
        text = path.read_text(encoding="utf-8-sig")
        if path.suffix.lower() == ".csv":
            data: object = {"rows": list(csv.DictReader(io.StringIO(text)))}
        else:
            data = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError, csv.Error) as e:
        raise field_errors([(field, f"Could not read this file: {e}")]) from e

    if isinstance(data, dict) and any(k in VALID_CATEGORIES for k in data):
        return {k: v for k, v in data.items() if isinstance(v, dict)}
    return {audience: data if isinstance(data, dict) else {"data": data}}


@dataclass
class StagedRun:
    run_id: str
    category: str
    dialect: str | None
    inputs_dir: Path
    out_dir: Path
    contracts_path: Path
    policies_path: Path
    audience_profiles: dict[str, dict]
    historic_performance: dict[str, dict]


def stage_request(
    *,
    episode_files: list[UploadFile] | None,
    scene_descriptions: str,
    scene_descriptions_file: UploadFile | None,
    dialogue_text: str,
    subtitle_dialect_1: UploadFile | None,
    subtitle_dialect_2: UploadFile | None,
    rating_policies_file: UploadFile | None,
    contracts_file: UploadFile | None,
    audience_profiles_file: UploadFile | None,
    historic_performance_file: UploadFile | None,
    cost_sheet_file: UploadFile | None,
    category: str,
    dialect: str | None,
) -> StagedRun:
    episodes = [f for f in (episode_files or []) if _present(f)]
    # Free text typed by the user; only meaningful for the dialect-region category.
    dialect_name = (dialect or "").strip()
    errors = _validate(
        episode_files=episodes,
        scene_descriptions=scene_descriptions,
        scene_descriptions_file=scene_descriptions_file,
        dialogue_text=dialogue_text,
        subtitle_dialect_1=subtitle_dialect_1,
        subtitle_dialect_2=subtitle_dialect_2,
        rating_policies_file=rating_policies_file,
        contracts_file=contracts_file,
        audience_profiles_file=audience_profiles_file,
        historic_performance_file=historic_performance_file,
        cost_sheet_file=cost_sheet_file,
        category=category,
        dialect=dialect_name,
    )
    if errors:
        raise field_errors(errors)

    run_id = uuid.uuid4().hex[:12]
    root = runs_root() / run_id
    inputs = root / "inputs"
    out = root / "out"

    try:
        out.mkdir(parents=True)
        for i, f in enumerate(episodes):
            _save(f, inputs / "episode" / f"{i:02d}_{_clean_name(f.filename, 'episode.mp4')}",
                  "episode_files")

        if _present(scene_descriptions_file):
            _save(scene_descriptions_file,
                  inputs / f"scene_descriptions{_ext(scene_descriptions_file)}",
                  "scene_descriptions_file")
        else:
            (inputs / "scene_descriptions.txt").write_text(scene_descriptions, encoding="utf-8")
        (inputs / "dialogue.txt").write_text(dialogue_text, encoding="utf-8")

        for upload, track, field in (
            (subtitle_dialect_1, "track_a", "subtitle_dialect_1"),
            (subtitle_dialect_2, "track_b", "subtitle_dialect_2"),
        ):
            _save(upload, inputs / "subtitles" / f"{track}{_ext(upload)}", field)

        contracts = _save(contracts_file,
                          inputs / "contracts" / _clean_name(contracts_file.filename, "contracts"),
                          "contracts_file")
        policies = _save(rating_policies_file,
                         inputs / "policies" / _clean_name(rating_policies_file.filename, "policies"),
                         "rating_policies_file")

        profiles: dict[str, dict] = {}
        historic: dict[str, dict] = {}
        if _present(audience_profiles_file):
            saved = _save(audience_profiles_file,
                          inputs / f"audience_profiles{_ext(audience_profiles_file)}",
                          "audience_profiles_file")
            profiles = _parse_reference(saved, "audience_profiles_file", category)
        if _present(historic_performance_file):
            saved = _save(historic_performance_file,
                          inputs / f"historic_performance{_ext(historic_performance_file)}",
                          "historic_performance_file")
            historic = _parse_reference(saved, "historic_performance_file", category)
        if _present(cost_sheet_file):
            _save(cost_sheet_file, inputs / f"cost_sheet{_ext(cost_sheet_file)}", "cost_sheet_file")
    except BaseException:
        shutil.rmtree(root, ignore_errors=True)
        raise

    if category == "dialect_region":
        # The Strategist reads this from audience_profile.
        profiles["dialect_region"] = {**profiles.get("dialect_region", {}), "dialect": dialect_name}

    return StagedRun(
        run_id=run_id,
        category=category,
        dialect=dialect_name if category == "dialect_region" else None,
        inputs_dir=inputs,
        out_dir=out,
        contracts_path=contracts,
        policies_path=policies,
        audience_profiles=profiles,
        historic_performance=historic,
    )