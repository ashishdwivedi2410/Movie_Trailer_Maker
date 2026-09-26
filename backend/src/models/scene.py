"""Scene registry - the authoritative source of truth for what actually
exists in the supplied episode. Anything not in here is invalid by
construction (see ARCHITECTURE.md section 3.1 and the 'hallucinated scene'
surprise event)."""
from pydantic import BaseModel


class Scene(BaseModel):
    scene_id: str
    source_in: str  # timecode, e.g. "00:02:14.200"
    source_out: str
    description_human: str | None = None
    description_ai: str | None = None
    characters: list[str] = []
    tags: list[str] = []


class SceneRegistry(BaseModel):
    scenes: dict[str, Scene]

    def exists(self, scene_id: str) -> bool:
        return scene_id in self.scenes

    def get(self, scene_id: str) -> Scene | None:
        return self.scenes.get(scene_id)