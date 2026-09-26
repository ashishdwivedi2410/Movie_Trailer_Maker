"""Story Map - characters, relationships, events, emotional beats, and the
protected-facts (spoiler) registry. Every entry should cite scene_ids from
the SceneRegistry. See ARCHITECTURE.md section 3.2."""
from pydantic import BaseModel


class Character(BaseModel):
    name: str
    scene_ids: list[str] = []


class Relationship(BaseModel):
    characters: tuple[str, str]
    kind: str  # e.g. "sibling", "rival"
    evidence_scene_ids: list[str] = []
    source_conflict: bool = False  # True if subtitle tracks disagree - see change_handler


class Event(BaseModel):
    event_id: str
    description: str
    scene_ids: list[str]
    emotional_beat: str | None = None


class ProtectedFact(BaseModel):
    """A spoiler: a fact that must not be revealed or implied by a trailer."""
    fact_id: str
    description: str
    scene_ids: list[str]


class StoryMap(BaseModel):
    characters: list[Character] = []
    relationships: list[Relationship] = []
    events: list[Event] = []
    protected_facts: list[ProtectedFact] = []