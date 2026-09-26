"""Append-only decision log - one JSON line per pipeline stage execution.
See ARCHITECTURE.md section 9. This is the audit trail: every final segment
should be traceable back through this log to the source material and every
check it passed, plus a record of what was revised after a replan and why.
"""
import json
import os
import time
from dataclasses import asdict, dataclass, field


@dataclass
class DecisionLogEntry:
    stage: str
    timestamp: float
    audience: str | None = None
    input_refs: list[str] = field(default_factory=list)
    output_refs: list[str] = field(default_factory=list)
    verification_result: dict | None = None
    cost_usd: float | None = None
    revision_of: str | None = None
    notes: str | None = None


class DecisionLog:
    def __init__(self, path: str = "sample_run/decision_log.jsonl"):
        self.path = path
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def record(
        self,
        stage: str,
        audience: str | None = None,
        input_refs: list[str] | None = None,
        output_refs: list[str] | None = None,
        verification_result: dict | None = None,
        cost_usd: float | None = None,
        revision_of: str | None = None,
        notes: str | None = None,
    ) -> None:
        entry = DecisionLogEntry(
            stage=stage,
            timestamp=time.time(),
            audience=audience,
            input_refs=input_refs or [],
            output_refs=output_refs or [],
            verification_result=verification_result,
            cost_usd=cost_usd,
            revision_of=revision_of,
            notes=notes,
        )
        with open(self.path, "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

    def record_replan(self, replan_result) -> None:
        """Convenience wrapper for src.replanning.change_handler.ReplanResult -
        keeps the 'what changed and why' trail in the same log as everything
        else rather than a separate replanning-only file."""
        self.record(
            stage="replan",
            output_refs=sorted(replan_result.affected_segment_ids),
            notes="; ".join(replan_result.notes),
        )

    def read_all(self) -> list[dict]:
        """Reads the log back as a list of entries - used by the
        validation_report.md generator and by tests asserting a specific
        stage ran."""
        if not os.path.exists(self.path):
            return []
        with open(self.path) as f:
            return [json.loads(line) for line in f if line.strip()]