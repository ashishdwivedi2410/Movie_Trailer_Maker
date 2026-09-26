"""Backward-traversable graph: fact -> set of segments citing it, built from
each segment's `evidence` field. See ARCHITECTURE.md section 3.8. This IS the
retrieval mechanism the Change Handler uses to find exactly which segments a
world-state change affects, so full trailers are never rebuilt from scratch.
"""
from collections import defaultdict

from src.models.trailer import Segment, TrailerPlan


class EvidenceGraph:
    def __init__(self):
        self._fact_to_segment_ids: dict[str, set[str]] = defaultdict(set)
        self._segment_by_id: dict[str, Segment] = {}
        self._trailer_by_segment_id: dict[str, str] = {}

    def index(self, trailer: TrailerPlan) -> None:
        """Indexes (or re-indexes) one trailer's segments. Safe to call again
        after a repair/replan - existing entries for this trailer_id are
        replaced, not accumulated, so a stale segment can never linger in the
        graph after its trailer has moved on."""
        self._drop_trailer(trailer.trailer_id)
        for i, seg in enumerate(trailer.segments):
            seg_id = f"{trailer.trailer_id}:{i}"
            self._segment_by_id[seg_id] = seg
            self._trailer_by_segment_id[seg_id] = trailer.trailer_id
            for fact in seg.evidence:
                self._fact_to_segment_ids[fact].add(seg_id)

    def _drop_trailer(self, trailer_id: str) -> None:
        stale_ids = [sid for sid, tid in self._trailer_by_segment_id.items() if tid == trailer_id]
        for sid in stale_ids:
            self._segment_by_id.pop(sid, None)
            self._trailer_by_segment_id.pop(sid, None)
            for segment_ids in self._fact_to_segment_ids.values():
                segment_ids.discard(sid)

    def affected_segment_ids(self, changed_fact: str) -> set[str]:
        """Segment ids that must be invalidated when `changed_fact` changes."""
        return set(self._fact_to_segment_ids.get(changed_fact, set()))

    def affected_trailers(self, changed_fact: str) -> set[str]:
        """Which trailer_ids have at least one segment affected by
        `changed_fact` - the Change Handler only needs to re-run Composer /
        Verifier for these, never every trailer."""
        return {self._trailer_by_segment_id[sid] for sid in self.affected_segment_ids(changed_fact)}

    def segment(self, segment_id: str) -> Segment | None:
        return self._segment_by_id.get(segment_id)