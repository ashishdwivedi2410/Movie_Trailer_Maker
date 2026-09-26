"""Change & Replanning Handler. See ARCHITECTURE.md section 3.8.

Reacts to a world-state change (contract expiry, corrected audience data, a
policy update, a corrected story fact) by walking the EvidenceGraph backward
from the changed fact, invalidating only the segments that cite it, and
reporting exactly which trailers need Composer -> Verifier re-run - never a
full rebuild. This module only identifies scope; actually re-invoking the
Composer/Verifier for the affected trailers, and recording the event, is the
pipeline's job (src/graph/pipeline.py + src/observability/decision_log.py).
"""
from dataclasses import dataclass, field

from src.replanning.evidence_graph import EvidenceGraph


@dataclass
class ReplanResult:
    changed_fact: str
    reason: str
    affected_trailer_ids: set[str]
    affected_segment_ids: set[str]
    notes: list[str] = field(default_factory=list)

    @property
    def needs_replan(self) -> bool:
        return bool(self.affected_segment_ids)


class ChangeHandler:
    def __init__(self, evidence_graph: EvidenceGraph):
        self.graph = evidence_graph

    def handle_change(self, changed_fact: str, reason: str) -> ReplanResult:
        """`changed_fact` uses the same reference format segments cite in
        their `evidence` field (e.g. "contract:music-03", "scene:07"). Only
        identifies scope - callers re-invoke Composer/Verifier for
        `affected_trailer_ids` with the relevant scenes/contracts excluded,
        and log this event."""
        affected_segments = self.graph.affected_segment_ids(changed_fact)
        affected_trailers = self.graph.affected_trailers(changed_fact)

        if affected_segments:
            note = (
                f"'{changed_fact}' changed ({reason}); "
                f"{len(affected_segments)} segment(s) across "
                f"{len(affected_trailers)} trailer(s) require replanning"
            )
        else:
            note = f"'{changed_fact}' changed ({reason}); no segments currently cite it, no replan needed"

        return ReplanResult(
            changed_fact=changed_fact,
            reason=reason,
            affected_trailer_ids=affected_trailers,
            affected_segment_ids=affected_segments,
            notes=[note],
        )