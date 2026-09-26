"""Trailer plan schema - matches the edit-decision-list format specified in
the assignment brief exactly (segments with evidence, reason, risk_flags;
a validation block with status and required approvals)."""
from pydantic import BaseModel
from typing import Literal


class Segment(BaseModel):
    source_in: str
    source_out: str
    video: str  # scene_id
    audio: str
    subtitle: str | None = None
    reason: str
    evidence: list[str]  # scene ids / constraint ids this segment cites
    risk_flags: list[str] = []


class ValidationResult(BaseModel):
    status: Literal["PASS", "PASS_WITH_WARNINGS", "FAIL", "NEEDS_APPROVAL"]
    checks_run: list[str] = []
    warnings: list[str] = []
    approvals_required: list[str] = []


class TrailerPlan(BaseModel):
    trailer_id: str
    audience: str
    duration_seconds: int
    audience_promise: str
    segments: list[Segment]
    validation: ValidationResult
    estimated_cost_usd: float | None = None
    lower_cost_fallback: str | None = None