"""FastAPI entry point - exposes the same pipeline as the CLI over REST.

Run with: uvicorn src.api:app --reload
"""
import os
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config import settings
from src.dialects import DialectsUnavailable, load_dialects
from src.graph.pipeline import run_all_trailers
from src.observability.decision_log import DecisionLog
from src.uploads import stage_request

app = FastAPI(title="Autonomous Trailer Director")

# Same-origin deployments (nginx serving the frontend and proxying /api) need
# no CORS. For local dev with the frontend on another origin, set e.g.
# CORS_ORIGINS=http://localhost:5500,http://127.0.0.1:5500
_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

DEFAULT_DURATIONS = {"family": 30, "young_adult": 30, "dialect_region": 30}


class GenerateTrailersRequest(BaseModel):
    episode_path: str
    contracts_path: str
    policies_path: str
    territory: str = "US"
    audience_profiles: dict[str, dict] = {}
    historic_performance: dict[str, dict] = {}
    duration_by_audience: dict[str, int] = DEFAULT_DURATIONS
    out_dir: str = "sample_run/"
    mock: bool = False


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/trailers")
def generate_trailers(request: GenerateTrailersRequest) -> dict:
    if request.mock:
        settings.mock_mode = True

    os.makedirs(request.out_dir, exist_ok=True)
    decision_log = DecisionLog(path=os.path.join(request.out_dir, "decision_log.jsonl"))

    try:
        result = run_all_trailers(
            episode_path=request.episode_path,
            contracts_path=request.contracts_path,
            policies_path=request.policies_path,
            territory=request.territory,
            audience_profiles=request.audience_profiles,
            historic_performance=request.historic_performance,
            duration_by_audience=request.duration_by_audience,
            decision_log=decision_log,
        )
    except NotImplementedError as e:
        # src/ingest/'s file-format question isn't resolved yet - surface
        # that clearly rather than a bare 500.
        raise HTTPException(status_code=501, detail=str(e)) from e

    return {
        "story_map": result.story_map.model_dump(),
        "constraint_map": result.constraint_map.model_dump(),
        "trailers": {audience: plan.model_dump() for audience, plan in result.trailers.items()},
    }


# --- Routes used by the web frontend (frontend/js/api.js) -------------------


@app.get("/api/dialects")
def list_dialects() -> dict:
    try:
        return {"dialects": load_dialects()}
    except DialectsUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@app.post("/api/generate-trailer")
def generate_trailer(
    episode_files: Annotated[list[UploadFile] | None, File()] = None,
    scene_descriptions: Annotated[str, Form()] = "",
    scene_descriptions_file: Annotated[UploadFile | None, File()] = None,
    dialogue_text: Annotated[str, Form()] = "",
    subtitle_dialect_1: Annotated[UploadFile | None, File()] = None,
    subtitle_dialect_2: Annotated[UploadFile | None, File()] = None,
    rating_policies_file: Annotated[UploadFile | None, File()] = None,
    contracts_file: Annotated[UploadFile | None, File()] = None,
    audience_profiles_file: Annotated[UploadFile | None, File()] = None,
    historic_performance_file: Annotated[UploadFile | None, File()] = None,
    cost_sheet_file: Annotated[UploadFile | None, File()] = None,
    category: Annotated[str, Form()] = "",
    dialect: Annotated[str | None, Form()] = None,
) -> dict:
    """Runs the pipeline for the ONE category the user picked and returns that
    single trailer object (the shape frontend/js/render-output.js renders)."""
    valid_dialects: list[str] = []
    if category == "dialect_region":
        try:
            valid_dialects = load_dialects()
        except DialectsUnavailable as e:
            raise HTTPException(status_code=503, detail=str(e)) from e

    # Raises 422 (field-level messages) / 413 before anything is run.
    staged = stage_request(
        episode_files=episode_files,
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
        dialect=dialect,
        valid_dialects=valid_dialects,
    )

    decision_log = DecisionLog(path=str(staged.out_dir / "decision_log.jsonl"))
    try:
        result = run_all_trailers(
            episode_path=str(staged.inputs_dir),
            contracts_path=str(staged.contracts_path),
            policies_path=str(staged.policies_path),
            territory="US",
            audience_profiles=staged.audience_profiles,
            historic_performance=staged.historic_performance,
            duration_by_audience=DEFAULT_DURATIONS,
            decision_log=decision_log,
            audiences=(staged.category,),
        )
    except NotImplementedError as e:
        # src/ingest/ parsers are still stubs: say so in words a user can read.
        raise HTTPException(
            status_code=501,
            detail=f"This server cannot process uploaded episode files yet (ingest is not implemented: {e}).",
        ) from e

    payload = result.trailers[staged.category].model_dump()
    payload["run_id"] = staged.run_id
    if staged.dialect:
        payload["dialect"] = staged.dialect
    return payload