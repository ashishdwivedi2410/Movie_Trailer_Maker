"""Audience promise - the creative contract set BEFORE any clip is selected.
See ARCHITECTURE.md section 3.4. Kept as its own schema (rather than a bare
string) so the personalization reasoning and bias check are inspectable
artifacts, not just something the Audience Strategist did silently."""
from pydantic import BaseModel


class PersonalizationNote(BaseModel):
    claim: str
    grounded: bool  # True only if backed by story-map evidence, not audience data alone
    evidence_scene_ids: list[str] = []


class AudiencePromise(BaseModel):
    audience: str
    promise: str
    emotional_arc: str
    personalization_notes: list[PersonalizationNote] = []
    bias_warnings: list[str] = []