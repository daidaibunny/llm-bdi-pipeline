#!/usr/bin/env python3
"""Run a paired Jason smoke ablation over temporal-controller structures."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domain_level_planning import TemporalCompilerVariant  # noqa: E402
from domain_level_planning import append_temporal_goal_to_library  # noqa: E402
from evaluation.jason_runtime import JasonPlanLibraryRunner  # noqa: E402
from evaluation.jason_runtime.runner import build_runtime_problem_artifacts  # noqa: E402
from plan_library.models import AgentSpeakBodyStep  # noqa: E402
from plan_library.models import AgentSpeakPlan  # noqa: E402
from plan_library.models import AgentSpeakTrigger  # noqa: E402
from plan_library.models import PlanLibrary  # noqa: E402
from plan_library.rendering import render_plan_library_asl  # noqa: E402
from scripts.run_full_test_jason_validation import (  # noqa: E402
    prepare_shared_jason_environments,
)
from scripts.run_full_test_jason_validation import (  # noqa: E402
    resolve_jason_classpath_once,
)
from scripts.run_temporal_goal_benchmark_execution import (  # noqa: E402
    controller_structure_metrics,
)


VARIANTS = (
    TemporalCompilerVariant.CERTIFIED_FLAT,
    TemporalCompilerVariant.CERTIFIED_LINEAR,
    TemporalCompilerVariant.CERTIFIED_BALANCED,
)


@dataclass(frozen=True)
class _EnvironmentTask:
    domain: str
    domain_file: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=(32, 128, 512))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--jason-java-stack-size", default="64m")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT / "artifacts/controller_structure_smoke",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sizes = tuple(sorted(set(int(size) for size in args.sizes)))
    if not sizes or sizes[0] < 1:
        raise ValueError("Every conjunction size must be positive.")
    repeats = max(1, int(args.repeats))
    root = args.output_root.expanduser().resolve()
    if root.exists():
        raise ValueError(f"Output directory already exists: {root}")
    root.mkdir(parents=True)

    domain_file = root / "domain.pddl"
    domain_file.write_text(_domain_text(), encoding="utf-8")
    base_library = _base_library()
    base_asl = root / "base_plan_library.asl"
    base_asl.write_text(render_plan_library_asl(base_library), encoding="utf-8")

    shared_summary: dict[str, object] = {}
    shared_summary_file = root / "shared_environment.json"
    shared_summary_file.write_text("{}\n", encoding="utf-8")
    classpath = resolve_jason_classpath_once()
    compiled_dirs = prepare_shared_jason_environments(
        tasks=(_EnvironmentTask("controller-smoke", domain_file),),
        classpath=classpath,
        run_root=root,
        timeout_seconds=max(1, int(args.timeout_seconds)),
        summary=shared_summary,
        summary_file=shared_summary_file,
    )
    compiled_environment_dir = compiled_dirs.get(str(domain_file.resolve()))
    if compiled_environment_dir is None:
        raise RuntimeError("Failed to compile the shared Jason smoke environment.")

    records: list[dict[str, object]] = []
    for size in sizes:
        problem_file = root / f"problem_{size}.pddl"
        problem_file.write_text(_problem_text(size), encoding="utf-8")
        runtime_artifacts = build_runtime_problem_artifacts(
            domain_file=domain_file,
            problem_file=problem_file,
        )
        dfa_payload = _dfa_payload(size)
        compiled = {
            variant: append_temporal_goal_to_library(
                plan_library=base_library,
                goal_name="g_smoke",
                dfa_payload=dfa_payload,
                domain_file=domain_file,
                compiler_variant=variant,
            )
            for variant in VARIANTS
        }
        _contract_check(compiled)
        for repeat in range(repeats):
            ordered_variants = (
                VARIANTS[repeat % len(VARIANTS) :] + VARIANTS[: repeat % len(VARIANTS)]
            )
            for variant in ordered_variants:
                updated = compiled[variant]
                output_dir = root / f"n_{size}" / variant.value / f"repeat_{repeat + 1}"
                wall_start = time.perf_counter()
                result = JasonPlanLibraryRunner(
                    timeout_seconds=max(1, int(args.timeout_seconds)),
                    jason_classpath=classpath,
                    compiled_environment_dir=compiled_environment_dir,
                    jason_java_stack_size=str(args.jason_java_stack_size),
                    require_plan_verifier=False,
                ).validate(
                    domain_file=domain_file,
                    problem_file=problem_file,
                    plan_library_asl=base_asl,
                    plan_library_asl_text=render_plan_library_asl(updated),
                    goal_name="g_smoke",
                    output_dir=output_dir,
                    runtime_artifacts=runtime_artifacts,
                    temporal_dfa_payload=dfa_payload,
                )
                record = {
                    "size": size,
                    "repeat": repeat + 1,
                    "variant": variant.value,
                    "success": result.success,
                    "status": result.status,
                    "action_count": result.action_count,
                    "run_seconds": result.timing_profile.get("run_seconds"),
                    "total_seconds": result.timing_profile.get("total_seconds"),
                    "wall_seconds": time.perf_counter() - wall_start,
                    "trace_sha256": _trace_sha256(output_dir / "committed_plan.plan"),
                    **controller_structure_metrics(base_library, updated),
                }
                records.append(record)
                print(
                    f"[smoke] n={size} repeat={repeat + 1} variant={variant.value} "
                    f"success={result.success} actions={result.action_count} "
                    f"run={float(record['run_seconds'] or 0):.4f}s",
                    flush=True,
                )

    summary = {
        "schema_version": 1,
        "artifact_kind": "paired_temporal_controller_structure_smoke",
        "sizes": list(sizes),
        "repeats": repeats,
        "variants": [variant.value for variant in VARIANTS],
        "paired_trace_equivalent": _paired_trace_equivalent(records),
        "records": records,
        "aggregate": _aggregate(records),
    }
    (root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"[summary] file={root / 'summary.json'}", flush=True)
    return (
        0
        if all(bool(record["success"]) for record in records)
        and bool(summary["paired_trace_equivalent"])
        else 1
    )


def _domain_text() -> str:
    return (
        """
(define (domain controller-smoke)
 (:requirements :strips :typing :negative-preconditions)
 (:types item)
 (:predicates
  (pending ?x - item)
  (done ?x - item)
  (last ?x - item)
  (complete))
 (:action mark
  :parameters (?x - item)
  :precondition (and (pending ?x) (not (last ?x)))
  :effect (and (done ?x) (not (pending ?x))))
 (:action mark-last
  :parameters (?x - item)
  :precondition (and (pending ?x) (last ?x))
  :effect (and (done ?x) (complete) (not (pending ?x))))
)
""".strip()
        + "\n"
    )


def _problem_text(size: int) -> str:
    objects = " ".join(f"item{index}" for index in range(1, size + 1))
    initial = " ".join(f"(pending item{index})" for index in range(1, size + 1))
    goal = " ".join(f"(done item{index})" for index in range(1, size + 1))
    return (
        f"""
(define (problem controller-smoke-{size})
 (:domain controller-smoke)
 (:objects {objects} - item)
 (:init {initial} (last item{size}))
 (:goal (and {goal} (complete)))
)
""".strip()
        + "\n"
    )


def _base_library() -> PlanLibrary:
    return PlanLibrary(
        domain_name="controller-smoke",
        plans=(
            AgentSpeakPlan(
                "done_already_satisfied",
                AgentSpeakTrigger("achievement_goal", "done", ("X",)),
                ("obj_tp(X, item)", "done(X)"),
                (),
            ),
            AgentSpeakPlan(
                "done_via_mark_last",
                AgentSpeakTrigger("achievement_goal", "done", ("X",)),
                ("obj_tp(X, item)", "pending(X)", "last(X)", "not done(X)"),
                (AgentSpeakBodyStep("action", "mark-last", ("X",)),),
            ),
            AgentSpeakPlan(
                "done_via_mark",
                AgentSpeakTrigger("achievement_goal", "done", ("X",)),
                (
                    "obj_tp(X, item)",
                    "pending(X)",
                    "not last(X)",
                    "not done(X)",
                ),
                (AgentSpeakBodyStep("action", "mark", ("X",)),),
            ),
            AgentSpeakPlan(
                "complete_already_satisfied",
                AgentSpeakTrigger("achievement_goal", "complete", ()),
                ("complete",),
                (),
            ),
            AgentSpeakPlan(
                "complete_via_last_item",
                AgentSpeakTrigger("achievement_goal", "complete", ()),
                ("last(X)", "not complete"),
                (AgentSpeakBodyStep("subgoal", "done", ("X",)),),
            ),
        ),
    )


def _dfa_payload(size: int) -> dict[str, object]:
    guard = " & ".join(
        (*tuple(f"done(item{index})" for index in range(1, size + 1)), "complete")
    )
    return {
        "formula": "synthetic conjunction used only for controller-structure smoke",
        "initial_state": "q0",
        "accepting_states": ["q1"],
        "guarded_transitions": [
            {"source_state": "q0", "target_state": "q1", "raw_label": guard},
            {"source_state": "q0", "target_state": "q0", "raw_label": "not complete"},
            {"source_state": "q1", "target_state": "q1", "raw_label": "true"},
        ],
    }


def _contract_check(compiled: dict[TemporalCompilerVariant, PlanLibrary]) -> None:
    contracts = {
        variant: library.metadata["temporal_goal_append"]["experiment_contract"]
        for variant, library in compiled.items()
    }
    if len({str(contract["dfa_fingerprint"]) for contract in contracts.values()}) != 1:
        raise ValueError("Controller variants did not share one DFA fingerprint.")
    if (
        len(
            {
                str(contract["atomic_library_fingerprint"])
                for contract in contracts.values()
            }
        )
        != 1
    ):
        raise ValueError(
            "Controller variants did not share one atomic-library fingerprint."
        )


def _trace_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _paired_trace_equivalent(records: list[dict[str, object]]) -> bool:
    for size in {int(record["size"]) for record in records}:
        for repeat in {int(record["repeat"]) for record in records}:
            selected = [
                record
                for record in records
                if int(record["size"]) == size and int(record["repeat"]) == repeat
            ]
            if len(selected) != len(VARIANTS):
                return False
            if {record["variant"] for record in selected} != {
                variant.value for variant in VARIANTS
            }:
                return False
            if len({int(record["action_count"]) for record in selected}) != 1:
                return False
            trace_hashes = {record["trace_sha256"] for record in selected}
            if None in trace_hashes or len(trace_hashes) != 1:
                return False
    return True


def _aggregate(records: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for size in sorted({int(record["size"]) for record in records}):
        for variant in VARIANTS:
            selected = [
                record
                for record in records
                if int(record["size"]) == size and record["variant"] == variant.value
            ]
            run_times = [float(record["run_seconds"]) for record in selected]
            rows.append(
                {
                    "size": size,
                    "variant": variant.value,
                    "success_count": sum(
                        bool(record["success"]) for record in selected
                    ),
                    "median_run_seconds": statistics.median(run_times),
                    "min_run_seconds": min(run_times),
                    "max_run_seconds": max(run_times),
                    "controller_plan_count": selected[0]["controller_plan_count"],
                    "max_trigger_fanout": selected[0]["max_trigger_fanout"],
                    "max_controller_body_steps": selected[0][
                        "max_controller_body_steps"
                    ],
                    "controller_asl_bytes": selected[0]["controller_asl_bytes"],
                    "trace_equivalent": len(
                        {str(record["trace_sha256"]) for record in selected}
                    )
                    == 1,
                }
            )
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
