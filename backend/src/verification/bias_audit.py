"""Deterministic bias/stereotype guard - plain code, checked independently of
both the Audience Strategist's own self-report and the semantic Verifier's
LLM judgment in src/agents/verifier.py. See ARCHITECTURE.md sections 3.4 and
3.6. Intentionally overlaps with AudienceStrategist._audit_bias: the whole
point of this check is that it does not depend on the Strategist having
audited itself correctly - a second, independent pass over the same data.
"""
from src.models.promise import AudiencePromise


def audit_grounding(promise: AudiencePromise) -> list[str]:
    """Any personalization_note marked grounded=False for the dialect_region
    audience is itself a bias warning, regardless of whether the agent that
    produced `promise` already flagged it. Returns only NEW warnings not
    already present in promise.bias_warnings - callers decide whether/how to
    merge (e.g. the pipeline unions this with the Strategist's own list and
    the semantic Verifier's independent findings)."""
    if promise.audience != "dialect_region":
        return []
    new_warnings = []
    for note in promise.personalization_notes:
        if not note.grounded:
            warning = f"Ungrounded personalization for dialect_region audience: {note.claim}"
            if warning not in promise.bias_warnings:
                new_warnings.append(warning)
    return new_warnings