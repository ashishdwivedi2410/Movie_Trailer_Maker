# Known Limitations

Documented up front, per the assignment's request for "a known-limitations
note and a list of decisions that must remain with humans."

## Scope cuts made for the 10-12 hour budget
- No rendered video output — edit decision lists only (explicitly allowed).
- No database — story/constraint maps and the evidence graph are flat JSON,
  adequate for a single-episode run; would move to Postgres for indexed
  evidence-graph traversal at production scale.
- No custom UI — CLI and the required JSON/markdown artifacts only.
- No separate vision-model pass over raw video frames — the ingest layer
  treats human-authored scene descriptions as ground truth rather than
  re-deriving them from footage. This is the first thing to add for real
  deployment; it's currently the weakest link in multimodal grounding.

## Decisions that must remain with humans
- Any `NEEDS_APPROVAL` / `PASS_WITH_WARNINGS` trailer: source conflicts
  between subtitle tracks, bias-check flags, exhausted repair retries, or
  ambiguous rights coverage.
- Final sign-off on cultural/dialect framing for the dialect-region trailer —
  the bias check can flag unsupported stereotyping, but confirming a
  portrayal is genuinely respectful is a human judgment.
- Legal interpretation of ambiguous or partial contract language — the
  Constraint Compiler extracts rules from contract text but does not
  adjudicate genuinely ambiguous clauses.

## Known weak points
- Spoiler detection relies on the protected-facts registry built by the Story
  Mapper; a spoiler the story map itself failed to capture would not be caught.
- The bias/stereotype check is heuristic (flags missing evidence for a
  personalization claim); it cannot certify a passing trailer is bias-free,
  only that a specific failure pattern wasn't detected.