"""FastAPI entry point - exposes the same pipeline as the CLI over REST.

Run with: uvicorn src.api:app --reload
"""
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.config import settings
from src.graph.pipeline import run_all_trailers
from src.observability.decision_log import DecisionLog

app = FastAPI(title="Autonomous Trailer Director")

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