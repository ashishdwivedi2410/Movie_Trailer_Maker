"""Constraint Map - policies and contracts compiled into testable rules.
See ARCHITECTURE.md section 3.3. This is the ONLY place mid-run 'instructions'
are allowed to come from source material, and even then only from contract/
policy files loaded at setup - never from scene descriptions or subtitles."""
from pydantic import BaseModel


class RightsRule(BaseModel):
    rule_id: str
    subject_type: str  # "actor" | "music_track" | "dialogue"
    subject_id: str
    allowed_territories: list[str] = []
    allowed_until: str | None = None  # ISO date, None = no expiry
    notes: str | None = None


class RatingRule(BaseModel):
    rule_id: str
    audience: str  # "family" | "young_adult" | "dialect_region"
    forbidden_tags: list[str] = []
    max_intensity: str | None = None


class ConstraintMap(BaseModel):
    rights_rules: list[RightsRule] = []
    rating_rules: list[RatingRule] = []

    def rights_for(self, subject_type: str, subject_id: str) -> RightsRule | None:
        for r in self.rights_rules:
            if r.subject_type == subject_type and r.subject_id == subject_id:
                return r
        return None