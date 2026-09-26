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