#!/usr/bin/env python3
"""
Generate completed baseline JSON records for final domain-level experiments.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re
import sys
from time import perf_counter
from typing import Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from domain_level_planning.paper_backend_audit import (  # noqa: E402
	audit_learned_policy_for_asl_binding,
)
from low_level_planning.fast_downward import (  # noqa: E402
	FastDownwardPlanner,
	FastDownwardPlannerConfig,
)
from low_level_planning.strips_state import STRIPSStateSimulator  # noqa: E402
from low_level_planning.strips_state import fact_to_signature  # noqa: E402
from utils.pddl_parser import PDDLParser  # noqa: E402


def main() -> None:
	"""Generate baseline records and write them as a JSON list."""

	parser = argparse.ArgumentParser(
		description="Generate baseline rows for domain-level ASL experiments.",
	)
	parser.add_argument("--domain-file", type=Path, required=True)
	parser.add_argument("--eval-problem", type=Path, action="append", default=[])
	parser.add_argument("--eval-base", type=Path, default=None)
	parser.add_argument("--eval-glob", default="")
	parser.add_argument("--eval-count", type=int, default=None)
	parser.add_argument("--output", type=Path, required=True)
	parser.add_argument(
		"--work-dir",
		type=Path,
		default=Path("tmp/paper-final/baselines/work"),
		help="Directory for generated planner tasks and plan files.",
	)
	parser.add_argument(
		"--fast-downward",
		type=Path,
		default=PROJECT_ROOT / "fast-downward" / "fast-downward.py",
		help="Fast Downward driver used for the classical per-problem baseline.",
	)
	parser.add_argument("--planner-timeout-seconds", type=int, default=60)
	parser.add_argument(
		"--skip-classical-planner",
		action="store_true",
		help="Do not run the classical per-problem planner baseline.",
	)
	parser.add_argument(
		"--external-sketch-policy",
		action="append",
		default=[],
		help="Audit-only external sketch baseline in NAME=PATH format.",
	)
	parser.add_argument(
		"--external-sketch-vocabulary",
		action="append",
		default=[],
		help="Optional NAME=PATH JSON vocabulary adapter for a sketch policy.",
	)
	parser.add_argument(
		"--moose-status-csv",
		action="append",
		default=[],
		help="MOOSE reproduction status in LABEL=PATH format.",
	)
	args = parser.parse_args()

	problem_files = _problem_files(
		explicit=tuple(args.eval_problem or ()),
		base=args.eval_base,
		glob_text=args.eval_glob,
		count=args.eval_count,
	)
	if not problem_files:
		raise ValueError("At least one evaluation problem is required.")

	records: list[dict[str, object]] = []
	if not args.skip_classical_planner:
		records.append(
			generate_classical_planner_baseline(
				domain_file=args.domain_file,
				problem_files=problem_files,
				planner_executable=args.fast_downward,
				timeout_seconds=args.planner_timeout_seconds,
				work_dir=args.work_dir / "classical-planner",
			),
		)
	vocabularies = _named_paths(tuple(args.external_sketch_vocabulary or ()))
	for name, policy_file in _named_paths(tuple(args.external_sketch_policy or ())).items():
		records.append(
			generate_external_sketch_audit_baseline(
				domain_file=args.domain_file,
				problem_count=len(problem_files),
				source_name=name,
				policy_file=policy_file,
				vocabulary_file=vocabularies.get(name),
			),
		)
	for label, status_file in _named_paths(tuple(args.moose_status_csv or ())).items():
		records.append(
			generate_moose_status_baseline(
				label=label,
				status_file=status_file,
			),
		)

	args.output.parent.mkdir(parents=True, exist_ok=True)
	args.output.write_text(
		json.dumps(records, indent=2, sort_keys=True),
		encoding="utf-8",
	)
	print(f"wrote {args.output} baseline_count={len(records)}")


def generate_classical_planner_baseline(
	*,
	domain_file: str | Path,
	problem_files: Sequence[str | Path],
	planner_executable: str | Path | None,
	timeout_seconds: int,
	work_dir: str | Path,
) -> dict[str, object]:
	"""Run and validate a per-problem classical planner baseline."""

	started = perf_counter()
	domain = PDDLParser.parse_domain(domain_file)
	simulator = STRIPSStateSimulator(str(domain_file))
	planner = FastDownwardPlanner(
		FastDownwardPlannerConfig(
			executable=str(planner_executable) if planner_executable else None,
			timeout_seconds=timeout_seconds,
		),
	)
	destination = Path(work_dir)
	destination.mkdir(parents=True, exist_ok=True)
	details: list[dict[str, object]] = []
	for problem_file in tuple(problem_files or ()):
		problem_path = Path(problem_file)
		problem = PDDLParser.parse_problem(problem_path)
		goal_facts = tuple(fact for fact in problem.goal_facts if fact.is_positive)
		goal_atoms = frozenset(fact_to_signature(fact) for fact in goal_facts)
		initial_state = simulator.initial_state_from_problem(str(problem_path))
		if goal_atoms.issubset(initial_state):
			details.append(
				{
					"problem_name": problem.name,
					"problem_file": str(problem_path),
					"solved": True,
					"plan_length": 0,
					"validation": "goal_already_satisfied",
					"error": None,
				},
			)
			continue
		result = planner.solve_transition_goal(
			domain_file=domain_file,
			base_problem_file=problem_path,
			goal_literals=tuple(fact.to_signature() for fact in goal_facts),
			work_dir=destination,
			task_name=_slug(problem.name),
		)
		validation = "planner_failed"
		solved = False
		error = result.error
		if result.success:
			try:
				final_state = simulator.apply_plan(
					state=initial_state,
					actions=result.actions,
				)
				solved = goal_atoms.issubset(final_state)
				validation = "strips_simulator_valid" if solved else "goal_not_reached"
				error = None if solved else "planner plan did not reach all goals"
			except ValueError as exc:
				validation = "strips_simulator_rejected"
				error = str(exc)
		details.append(
			{
				"problem_name": problem.name,
				"problem_file": str(problem_path),
				"solved": solved,
				"plan_length": len(result.actions),
				"validation": validation,
				"plan_file": result.plan_file,
				"error": error,
			},
		)
	solved_count = sum(1 for item in details if bool(item["solved"]))
	failed_count = len(details) - solved_count
	return {
		"label": "fast_downward_lama_per_problem",
		"domain_name": domain.name,
		"solver_family": "classical_planner",
		"solved_count": solved_count,
		"failed_count": failed_count,
		"coverage_ratio": solved_count / len(details) if details else 0.0,
		"runtime_planner": "offline_baseline_only",
		"comparison_scope": "per_problem_trace_baseline",
		"domain_level_artifact": False,
		"coverage_semantics": "executed_and_strips_validated",
		"evidence_source": "Fast Downward lama-first plus local STRIPS simulation",
		"validation": {
			"problem_count": len(details),
			"timeout_seconds": timeout_seconds,
			"duration_seconds": perf_counter() - started,
			"problem_results": details,
		},
		"notes": "solves each evaluation problem independently; not a domain-level library",
	}


def generate_external_sketch_audit_baseline(
	*,
	domain_file: str | Path,
	problem_count: int,
	source_name: str,
	policy_file: str | Path,
	vocabulary_file: str | Path | None = None,
) -> dict[str, object]:
	"""Create an audit-only baseline record for a raw learned sketch artifact."""

	domain = PDDLParser.parse_domain(domain_file)
	vocabulary = _read_vocabulary_adapter(vocabulary_file)
	report, _, _ = audit_learned_policy_for_asl_binding(
		source_name=source_name,
		policy_file=policy_file,
		domain=domain,
		vocabulary_map=vocabulary,
	)
	return {
		"label": f"raw_{source_name}_policy_audit",
		"domain_name": domain.name,
		"solver_family": "external_generalized_planning_policy",
		"solved_count": 0,
		"failed_count": problem_count,
		"coverage_ratio": 0.0,
		"runtime_planner": "not_runtime_executed",
		"comparison_scope": "artifact_audit",
		"domain_level_artifact": True,
		"coverage_semantics": "not_directly_executable_without_asl_binding",
		"evidence_source": "learner-sketches policy artifact",
		"validation": report.to_dict(),
		"notes": (
			"raw qualitative sketch audit; ready_for_executable_asl="
			f"{report.ready_for_executable_asl}"
		),
	}


def generate_moose_status_baseline(
	*,
	label: str,
	status_file: str | Path,
) -> dict[str, object]:
	"""Create a MOOSE reproduction baseline from a completed status CSV."""

	rows = _read_status_rows(status_file)
	solved = tuple(row for row in rows if _status_is_success(str(row.get("status") or "")))
	failed_count = len(rows) - len(solved)
	return {
		"label": label,
		"domain_name": _domain_name_from_label(label),
		"solver_family": "moose_generalized_planner",
		"solved_count": len(solved),
		"failed_count": failed_count,
		"coverage_ratio": len(solved) / len(rows) if rows else 0.0,
		"runtime_planner": "moose_policy_execution_or_training_probe",
		"comparison_scope": "generalized_planning_reproduction",
		"domain_level_artifact": True,
		"coverage_semantics": "completed_status_csv",
		"evidence_source": str(Path(status_file)),
		"validation": {
			"status_file": str(Path(status_file)),
			"row_count": len(rows),
			"success_statuses": sorted({str(row.get("status") or "") for row in solved}),
		},
		"notes": "imported from completed MOOSE reproduction status",
	}


def _problem_files(
	*,
	explicit: Sequence[Path],
	base: Path | None,
	glob_text: str,
	count: int | None,
) -> tuple[Path, ...]:
	if explicit:
		return tuple(path.expanduser().resolve() for path in explicit)
	if base is None or not glob_text:
		return ()
	files = tuple(sorted(base.expanduser().resolve().glob(glob_text)))
	if count is not None:
		files = files[:count]
	return files


def _named_paths(raw_values: Sequence[str]) -> dict[str, Path]:
	paths: dict[str, Path] = {}
	for raw_value in tuple(raw_values or ()):
		text = str(raw_value or "").strip()
		if not text:
			continue
		if "=" not in text:
			raise ValueError("Named paths must use LABEL=PATH.")
		label, raw_path = text.split("=", 1)
		name = label.strip()
		if not name:
			raise ValueError("Named path label must not be empty.")
		paths[name] = Path(raw_path.strip()).expanduser().resolve()
	return paths


def _read_vocabulary_adapter(path: str | Path | None) -> Mapping[str, str]:
	if path is None:
		return {}
	data = json.loads(Path(path).read_text(encoding="utf-8"))
	if isinstance(data, dict) and isinstance(data.get("predicate_map"), dict):
		return {str(key): str(value) for key, value in data["predicate_map"].items()}
	if isinstance(data, dict):
		return {str(key): str(value) for key, value in data.items()}
	raise ValueError(f"Vocabulary adapter must be a JSON object: {path}")


def _read_status_rows(path: str | Path) -> tuple[dict[str, str], ...]:
	with Path(path).open(encoding="utf-8", newline="") as handle:
		return tuple(dict(row) for row in csv.DictReader(handle))


def _status_is_success(status: str) -> bool:
	return status.strip().lower() in {"ok", "good", "success", "solved", "valid"}


def _domain_name_from_label(label: str) -> str:
	text = str(label or "").strip()
	if not text:
		return ""
	return re.split(r"[_:-]", text, maxsplit=1)[0]


def _slug(text: str) -> str:
	value = "".join(character if character.isalnum() else "-" for character in text.lower())
	return "-".join(part for part in value.split("-") if part) or "task"


if __name__ == "__main__":
	main()
