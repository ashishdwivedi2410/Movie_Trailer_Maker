# AI Collaboration Note

## Where AI tools were used
Claude was used for the entire implementation of this backend: architecture
design, all Pydantic models, all five agents (Story Mapper, Constraint
Compiler, Audience Strategist, Composer, semantic Verifier), the deterministic
verification layer, the evidence-graph/replanning layer, the decision log,
the LangGraph pipeline wiring, all five required tests, the CLI/API entry
points, and the CI workflow. No other AI coding tool was used in this build.

## What was generated vs. hand-written
Every file in this repo was drafted by Claude, one file at a time, with the
repo structure and file contents reviewed before moving to the next piece.
The human's role was directing scope and order (which component to build
next, when to pause and check the folder structure), setting the repo
convention (moving everything under `backend/` to match an existing
monorepo layout with `frontend/`, `devops/`, `.github/`), and reviewing each
file as it was delivered - including catching that a zip shared partway
through the build was a stale snapshot missing everything written afterward.

## Plausible-but-wrong suggestions caught during review

| Suggestion / output | Why it looked reasonable | Why it was wrong | What was used instead |
|---|---|---|---|
| Early `mkdir -p dir/{a,b,c}` scaffolding command | Standard bash brace expansion | The execution shell didn't expand braces, so it silently created one literal directory named `{src` instead of the intended folder tree | Rewrote with one explicit `mkdir -p` per directory; caught by listing the actual directory tree afterward instead of trusting the command's exit code |
| `src/config.py` reported as done (checked off) in an early file-structure summary | It had been included in an earlier scaffolding script, so it was assumed to exist | That script aborted partway through (an unrelated failure upstream) before ever reaching the `config.py` step, so the file was never actually created despite being listed as complete | Only caught when actually running the pipeline end-to-end and hitting `ModuleNotFoundError: No module named 'src.config'` - recreated the file and re-verified with a real run, not just a file listing |
| First draft of `_offending_scene_ids()` in `src/graph/pipeline.py` | Correct signature, docstring, and loop structure at a glance | Was missing the `audience` parameter and the rights/rating check calls entirely - a leftover placeholder line did nothing | Rewrote the function fully, then re-validated by running the graph end-to-end with injected fake agents to confirm the repair loop actually excludes the right scenes on retry |
| Docstring diagram in `pipeline.py` using a literal `\--` | Reads fine as plain ASCII art | Python raised a `SyntaxWarning` for an unrecognized escape sequence inside the (non-raw) triple-quoted string | Reworded the diagram to avoid backslashes |

## Verification approach
- Every file was syntax-checked with `python3 -m py_compile` before being
  shared.
- `pytest` was actually run, not just written: 13/13 passing across all five
  required failure modes (missing scene, rights restriction, spoiler, policy
  failure, changed contract).
- The LangGraph wiring was validated by injecting fake Strategist/Composer/
  Verifier agents (no real API calls) and running `app.invoke()` end-to-end
  for both a repair-then-pass case and an exhausts-retries case - confirming
  the compose -> verify -> repair loop and the fail-closed `FAIL` status
  actually work, not just that the code parses.
- `src/main.py`'s output-writing was validated by monkeypatching
  `run_all_trailers`, running `main()` with `--mock`, and checking all four
  output files were written with correct content.
- `src/api.py`'s endpoints were tested with FastAPI's `TestClient`, including
  confirming the still-unimplemented `ingest/` layer surfaces as a clean
  `501` rather than an opaque `500`.
- `.github/workflows/backend.yml` was parsed with `pyyaml` before delivery
  to confirm it's valid YAML.

## What's still open
`src/ingest/`'s real file-parsing logic and `src/llm/client.py`'s real
Anthropic API call remain stubs, pending confirmation of the actual supplied
material format and a decision on API integration approach - see
`KNOWN_LIMITATIONS.md`.