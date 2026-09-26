"""Loads the episode package (scene descriptions, dialogue, subtitle tracks)
and builds the SceneRegistry - the authoritative list of what actually
exists. See ARCHITECTURE.md section 3.1.

TODO: parse the actual supplied episode package format once available
(timecodes, human/AI scene descriptions, dialogue, both subtitle tracks).
"""
from src.models.scene import SceneRegistry


def load_episode(path: str) -> SceneRegistry:
    raise NotImplementedError("Parse episode package at `path` into a SceneRegistry")


def load_dialogue(path: str) -> str:
    raise NotImplementedError


def load_subtitle_track(path: str, track_name: str) -> str:
    raise NotImplementedError