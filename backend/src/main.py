"""CLI entry point.

Usage:
    python -m src.main \
        --episode fixtures/episode_package \
        --contracts fixtures/contracts \
        --policies fixtures/policies \
        --out sample_run/ \
        [--territory US] [--mock]

Writes story_map.json, constraint_map.json, one <audience>_trailer.json per
audience, validation_report.md, and decision_log.jsonl into --out, matching
the required sample_run/ layout in the assignment brief.
"""
import argparse
import os

from src.config import settings
from src.graph.pipeline import RunResult, run_all_trailers
from src.models.trailer import TrailerPlan
from src.observability.decision_log import DecisionLog

DEFAULT_DURATIONS = {"family": 30, "young_adult": 30, "dialect_region": 30}


def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous Trailer Director")
    parser.add_argument("--episode", required=True, help="Path to the episode package")
    parser.add_argument("--contracts", required=True, help="Path to contract documents")
    parser.add_argument("--policies", required=True, help="Path to rating policy documents")
    parser.add_argument("--out", default="sample_run/", help="Output directory")
    parser.add_argument("--territory", default="US", help="Distribution territory for rights checks")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use recorded LLM responses (fixtures/replay_cache.json) instead of calling a real API",
    )
    args = parser.parse_args()

    if args.mock:
        settings.mock_mode = True

    os.makedirs(args.out, exist_ok=True)
    decision_log = DecisionLog(path=os.path.join(args.out, "decision_log.jsonl"))

    # TODO: audience_profiles / historic_performance are part of the supplied
    # material - wire these up to real files once src/ingest/'s file-format
    # question is resolved. Empty dicts keep the pipeline runnable meanwhile;
    # AudienceStrategist already treats them as optional hypotheses, not
    # required inputs.
    result = run_all_trailers(
        episode_path=args.episode,
        contracts_path=args.contracts,
        policies_path=args.policies,
        territory=args.territory,
        audience_profiles={},
        historic_performance={},
        duration_by_audience=DEFAULT_DURATIONS,
        decision_log=decision_log,
    )

    _write_outputs(args.out, result)


def _write_outputs(out_dir: str, result: RunResult) -> None:
    _write_json(os.path.join(out_dir, "story_map.json"), result.story_map.model_dump_json(indent=2))
    _write_json(os.path.join(out_dir, "constraint_map.json"), result.constraint_map.model_dump_json(indent=2))

    for audience, trailer_plan in result.trailers.items():
        path = os.path.join(out_dir, f"{audience}_trailer.json")
        _write_json(path, trailer_plan.model_dump_json(indent=2))
        print(f"Wrote {path} [{trailer_plan.validation.status}]")

    report_path = os.path.join(out_dir, "validation_report.md")
    with open(report_path, "w") as f:
        f.write(_render_validation_report(result.trailers))
    print(f"Wrote {report_path}")


def _write_json(path: str, content: str) -> None:
    with open(path, "w") as f:
        f.write(content)


def _render_validation_report(trailers: dict[str, TrailerPlan]) -> str:
    lines = ["# Validation Report", ""]
    for audience, plan in trailers.items():
        lines.append(f"## {audience} ({plan.trailer_id})")
        lines.append(f"- Status: **{plan.validation.status}**")
        lines.append(f"- Segments: {len(plan.segments)}")
        if plan.validation.warnings:
            lines.append("- Warnings:")
            lines.extend(f"  - {w}" for w in plan.validation.warnings)
        if plan.validation.approvals_required:
            lines.append("- Approvals required:")
            lines.extend(f"  - {a}" for a in plan.validation.approvals_required)
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()