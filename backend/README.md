# Autonomous Trailer Director — Backend

Agentic system that plans three audience-specific trailer edit decision
lists (family, young adult, dialect-region) from one episode: evidence-grounded
creative planning, independent verification, and selective replanning when
contracts, policies, or facts change mid-run.

Full design → `ARCHITECTURE.md` · AI usage log → `AI_COLLABORATION.md` · scope cuts → `KNOWN_LIMITATIONS.md`

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add ANTHROPIC_API_KEY, or skip and use --mock
```

## Run
```bash
python -m src.main \
  --episode fixtures/episode_package \
  --contracts fixtures/contracts \
  --policies fixtures/policies \
  --out sample_run/ \
  --mock          # drop this flag once real API keys + episode data are in place
```

## API
```bash
uvicorn src.api:app --reload
```

Routes used by the web frontend (`frontend/js/api.js`):

| Route | Purpose |
|---|---|
| `POST /api/generate-trailer` | Multipart form (see field names in `src/uploads.py`). Runs **only the selected category** and returns **one trailer object** (plus `run_id`, and the user-typed `dialect` for dialect-region). **422** carries `[{"field", "message"}]` per bad input; **413** if a file is over the limit; **501** while the `src/ingest/` parsers are unimplemented. |

Uploads are staged per request under `RUNS_DIR/<run_id>/inputs/` (layout documented in `src/uploads.py`); the client never supplies a server path.

Optional settings (environment variables):

| Variable | Default | Meaning |
|---|---|---|
| `RUNS_DIR` | `runs` | Where per-request uploads and outputs are written |
| `MAX_UPLOAD_MB` | `500` | Per-file upload limit |
| `CORS_ORIGINS` | *(none)* | Comma-separated origins, only needed when the frontend is served from a different origin than the API |

Behind nginx, proxy `/api/` to the backend and raise `client_max_body_size` above the video size (the default 1 MB rejects uploads).

`POST /trailers` (JSON, server-side paths) is the older CLI-style route and is unchanged.

## Test
```bash
pytest -v
```
Covers the five required failure modes: missing scene, rights restriction, spoiler, policy failure, changed contract.

## Layout
```
src/models/         Scene, StoryMap, ConstraintMap, TrailerPlan schemas
src/ingest/         Episode/contract/policy loading
src/agents/         StoryMapper, ConstraintCompiler, AudienceStrategist, Composer, Verifier
src/graph/          LangGraph pipeline wiring
src/verification/   Deterministic checks (source accuracy, rights, timing, spoilers)
src/replanning/     Evidence graph + selective replanning
src/llm/            Model client with fallback + mock/replay
src/observability/  Decision log
tests/              Required failure-mode tests
fixtures/           Drop supplied episode/contract/policy material here
sample_run/         Generated output lands here after a run
```