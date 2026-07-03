#!/usr/bin/env python3
"""
Run a configured matrix of domain-level lifted-library experiments.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import signal
from time import perf_counter
import traceback
from typing import Iterable, Iterator, Sequence

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from domain_level_planning.experiments import (  # noqa: E402
	compare_domain_level_experiment_reports,
	run_domain_level_experiment,
)
from domain_level_planning.benchmark_registry import (  # noqa: E402
	build_preset_config_from_registry,
)
from scripts.run_domain_level_experiment import (  # noqa: E402
	_parse_external_sketch_policies,
	_read_baseline_records,
)


def main() -> None:
	"""Run a paper-grade experiment matrix from JSON config or a built-in preset."""

	parser = argparse.ArgumentParser(
		description="Run a domain-level lifted ASL experiment matrix.",
	)
	parser.add_argument(
		"--config",
		type=Path,
		default=None,
		help="JSON matrix config. If omitted, --preset is used.",
	)
	parser.add_argument(
		"--preset",
		choices=("current-minimum", "paper-diagnostic-smoke", "paper-expanded-smoke"),
		default="paper-diagnostic-smoke",
		help="Built-in matrix preset used when --config is omitted.",
	)
	parser.add_argument(
		"--output-dir",
		type=Path,
		default=Path("tmp/domain-level-experiment-matrix"),
		help="Directory for per-experiment reports and summary files.",
	)
	parser.add_argument(
		"--fail-fast",
		action="store_true",
		help="Abort the matrix on the first failed entry instead of writing a diagnostic row.",
	)
	args = parser.parse_args()

	config, config_base = _load_matrix_config(args.config, preset=args.preset)
	result = run_experiment_matrix(
		config=config,
		config_base=config_base,
		output_dir=args.output_dir,
		continue_on_error=not args.fail_fast,
		preserve_files=(args.config,) if args.config is not None else (),
	)
	print(
		"wrote "
		f"{result['summary_file']} "
		f"succeeded={result['succeeded_count']} "
		f"failed={result['failed_count']} "
		f"reports={result['experiment_count']}",
	)


def run_experiment_matrix(
	*,
	config: dict[str, object],
	config_base: Path,
	output_dir: Path,
	continue_on_error: bool = True,
	preserve_files: Iterable[Path | str] = (),
) -> dict[str, object]:
	"""Run each matrix entry and persist reports plus comparison artifacts."""

	matrix_name = str(config.get("matrix_name") or "domain-level-experiment-matrix")
	entries = tuple(config.get("experiments") or ())
	if not entries:
		raise ValueError("Experiment matrix config requires a non-empty 'experiments' list.")
	output_dir.mkdir(parents=True, exist_ok=True)
	_reset_managed_matrix_output(output_dir, preserve_files=preserve_files)
	reports: list[dict[str, object]] = []
	report_files: list[Path] = []
	started = perf_counter()
	for index, raw_entry in enumerate(entries, start=1):
		if not isinstance(raw_entry, dict):
			raise ValueError(f"Experiment matrix entry {index} must be an object.")
		entry = dict(raw_entry)
		report_file = output_dir / f"{_slug(_entry_name(entry, index=index))}.json"
		entry_started = perf_counter()
		try:
			with _entry_timeout(entry, index=index):
				report = _run_matrix_entry(entry, config_base=config_base)
			report["matrix_status"] = "succeeded"
			report["matrix_entry"] = _matrix_entry_metadata(entry, index=index)
		except Exception as error:
			if not continue_on_error:
				raise
			report = _failure_report(
				entry=entry,
				index=index,
				error=error,
				config_base=config_base,
				started=entry_started,
			)
		report_file.write_text(
			json.dumps(report, indent=2, sort_keys=True),
			encoding="utf-8",
		)
		reports.append(report)
		report_files.append(report_file)
	comparison = compare_domain_level_experiment_reports(reports)
	comparison_file = output_dir / "comparison.json"
	comparison_file.write_text(
		json.dumps(comparison, indent=2, sort_keys=True),
		encoding="utf-8",
	)
	summary = _matrix_summary(
		matrix_name=matrix_name,
		reports=reports,
		report_files=report_files,
		comparison=comparison,
		comparison_file=comparison_file,
		started=started,
	)
	summary_file = output_dir / "matrix-summary.json"
	summary["summary_file"] = str(summary_file)
	summary_file.write_text(
		json.dumps(summary, indent=2, sort_keys=True),
		encoding="utf-8",
	)
	return summary


def _reset_managed_matrix_output(
	output_dir: Path,
	*,
	preserve_files: Iterable[Path | str],
) -> None:
	"""Remove stale JSON reports before writing a fresh matrix result."""

	preserved = {
		Path(path).expanduser().resolve()
		for path in preserve_files
		if str(path).strip()
	}
	for path in output_dir.glob("*.json"):
		if path.resolve() not in preserved:
			path.unlink()


def _run_matrix_entry(
	entry: dict[str, object],
	*,
	config_base: Path,
) -> dict[str, object]:
	name = _entry_name(entry, index=0)
	domain_file = _resolve_path(entry["domain_file"], config_base=config_base)
	training_problems = _problem_files(entry, key="train", config_base=config_base)
	evaluation_problems = _problem_files(entry, key="eval", config_base=config_base)
	if not training_problems:
		raise ValueError(f"Matrix entry {name!r} requires at least one training problem.")
	if not evaluation_problems:
		raise ValueError(f"Matrix entry {name!r} requires at least one evaluation problem.")
	external_policies = _parse_external_sketch_policies(
		tuple(str(item) for item in entry.get("external_sketch_policies") or ()),
		tuple(str(item) for item in entry.get("external_sketch_vocabularies") or ()),
	)
	return run_domain_level_experiment(
		experiment_name=name,
		domain_file=domain_file,
		training_problem_files=training_problems,
		evaluation_problem_files=evaluation_problems,
		domain_id=str(entry.get("domain_id") or ""),
		goal_property_group_id=str(entry.get("goal_property_group_id") or ""),
		counterexample_problem_files=_problem_files(
			entry,
			key="counterexample",
			config_base=config_base,
		),
		external_sketch_policies=external_policies,
		synthesis_profile=str(entry.get("synthesis_profile") or "bootstrap"),
		disabled_synthesis_mechanisms=tuple(
			str(item)
			for item in tuple(entry.get("disabled_synthesis_mechanisms") or ())
		),
		max_execution_steps=int(entry.get("max_steps") or 10000),
		max_depth=int(entry.get("max_depth") or 1000),
		evaluation_timeout_seconds=_optional_float(entry.get("evaluation_timeout_seconds")),
		use_synthesis_planner_traces=bool(
			entry.get("use_synthesis_planner_traces", False),
		),
		synthesis_planner_executable=(
			_resolve_path(entry["synthesis_planner_executable"], config_base=config_base)
			if entry.get("synthesis_planner_executable") is not None
			else None
		),
		synthesis_planner_timeout_seconds=int(
			entry.get("synthesis_planner_timeout_seconds") or 60,
		),
		use_counterexample_refinement=bool(
			entry.get("use_counterexample_refinement", False),
		),
		max_refinement_rounds=int(entry.get("max_refinement_rounds") or 1),
		ablation_label=str(entry.get("ablation_label") or ""),
		baselines=_baseline_records(entry, config_base=config_base),
		fail_on_paper_profile_failure=not bool(
			entry.get("allow_paper_profile_failures", False),
		),
	)


@contextmanager
def _entry_timeout(
	entry: dict[str, object],
	*,
	index: int,
) -> Iterator[None]:
	"""Raise TimeoutError when a matrix row exceeds its configured time budget."""

	raw_timeout = entry.get("timeout_seconds")
	if raw_timeout is None:
		yield
		return
	timeout_seconds = float(raw_timeout)
	if timeout_seconds <= 0:
		yield
		return
	name = _entry_name(entry, index=index)
	previous_handler = signal.getsignal(signal.SIGALRM)
	previous_timer = signal.getitimer(signal.ITIMER_REAL)
	started = perf_counter()

	def handle_timeout(_signum: int, _frame: object) -> None:
		raise TimeoutError(
			f"Matrix entry {name!r} exceeded timeout_seconds={timeout_seconds:g}.",
		)

	signal.signal(signal.SIGALRM, handle_timeout)
	signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
	try:
		yield
	finally:
		signal.signal(signal.SIGALRM, previous_handler)
		_restore_timer(previous_timer, elapsed=perf_counter() - started)


def _failure_report(
	*,
	entry: dict[str, object],
	index: int,
	error: Exception,
	config_base: Path,
	started: float,
) -> dict[str, object]:
	name = _entry_name(entry, index=index)
	evaluation_problems = _problem_files(entry, key="eval", config_base=config_base)
	failure_message = str(error)
	return {
		"experiment_name": name,
		"matrix_status": "failed",
		"matrix_entry": _matrix_entry_metadata(entry, index=index),
		"domain_file": str(_resolve_path(entry["domain_file"], config_base=config_base)),
		"generation_mode": "domain_level_experiment_matrix_diagnostic",
		"experiment_protocol": _failure_protocol(entry),
		"paper_quality_summary": {
			"synthesis_profile": str(entry.get("synthesis_profile") or "bootstrap"),
			"paper_profile_ready": False,
			"schema_only_bootstrap": False,
			"external_policy_count": len(tuple(entry.get("external_sketch_policies") or ())),
			"selected_external_sketch_candidate_count": 0,
			"output_external_sketch_candidate_count": 0,
			"selected_external_sketch_rule_names": [],
			"output_external_sketch_rule_names": [],
			"external_policy_required_for_paper_profile": False,
			"blocking_failure_count": 1,
			"blocking_failures": [failure_message],
		},
		"train_problem_count": len(_problem_files(entry, key="train", config_base=config_base)),
		"training_problem_files": [
			str(path) for path in _problem_files(entry, key="train", config_base=config_base)
		],
		"counterexample_problem_count": len(
			_problem_files(entry, key="counterexample", config_base=config_base),
		),
		"counterexample_problem_files": [
			str(path)
			for path in _problem_files(entry, key="counterexample", config_base=config_base)
		],
		"evaluation_problem_count": len(evaluation_problems),
		"evaluation_problem_files": [str(path) for path in evaluation_problems],
		"coverage": {
			"solved_count": 0,
			"failed_count": len(evaluation_problems),
			"coverage_ratio": 0.0,
			"failed_problem_names": [path.stem for path in evaluation_problems],
		},
		"failure_analysis": {
			"failed_problem_count": len(evaluation_problems),
			"failure_reason_counts": {failure_message: len(evaluation_problems)},
			"failed_problems": [
				{
					"problem_name": path.stem,
					"problem_file": str(path),
					"failure_reason": failure_message,
					"step_count": 0,
				}
				for path in evaluation_problems
			],
			"step_count_summary": {"min": 0, "max": 0, "mean": 0.0},
		},
		"evaluation_results": [],
		"plan_library": {
			"domain_name": "",
			"plan_count": 0,
			"initial_belief_count": 0,
			"primitive_action_call_count": 0,
			"subgoal_call_count": 0,
			"asl_line_count": 0,
		},
		"runtime_seconds": {
			"synthesis": perf_counter() - started,
			"evaluation_total": 0.0,
			"evaluation_by_problem": [],
		},
		"domain_level_contract": {"passed": False, "violations": [failure_message]},
		"generated_output_audit": {
			"passed": False,
			"no_synthetic_names": True,
			"no_grounded_plan_terms": True,
			"no_initial_beliefs": True,
			"goal_descriptors_read_only": True,
			"supported_asl_subset": False,
			"declared_pddl_symbols": False,
			"checked_layers": {},
			"violation_count": 1,
			"violations": [failure_message],
		},
		"validation_scope": {
			"bounded_validation_problem_count": 0,
			"bounded_validation_source": "not_run_failed_matrix_entry",
			"bounded_validation_problem_names": [],
			"evaluation_problem_count": len(evaluation_problems),
			"evaluation_source": "evaluation_problem_files",
			"coverage_is_heldout_runtime_execution": False,
		},
		"no_synthetic_names": True,
		"bounded_validation": None,
		"synthesis_report": {
			"generation_mode": "failed_before_or_during_synthesis",
			"synthesis_profile": str(entry.get("synthesis_profile") or "bootstrap"),
			"paper_profile_ready": False,
			"paper_profile_failures": [failure_message],
		},
		"learning_audit": {
			"layer_b_atomic_modules": {},
			"layer_c_goal_composer": {},
		},
		"refinement_analysis": {
			"enabled": bool(entry.get("use_counterexample_refinement", False)),
			"converged": False,
			"round_count": 0,
			"constraint_count": 0,
			"constraints_by_type": {},
			"constraints_by_failure_kind": {},
			"constraints_by_target_layer": {},
			"first_round_failed_heldout_count": len(evaluation_problems),
			"final_round_failed_heldout_count": len(evaluation_problems),
		},
		"refinement_trace": None,
		"asl": "",
		"error": {
			"type": type(error).__name__,
			"message": failure_message,
			"traceback": traceback.format_exception_only(type(error), error),
		},
	}


def _matrix_summary(
	*,
	matrix_name: str,
	reports: Sequence[dict[str, object]],
	report_files: Sequence[Path],
	comparison: dict[str, object],
	comparison_file: Path,
	started: float,
) -> dict[str, object]:
	rows: list[dict[str, object]] = []
	for report, report_file in zip(tuple(reports), tuple(report_files)):
		coverage = dict(report.get("coverage") or {})
		paper = dict(report.get("paper_quality_summary") or {})
		plan = dict(report.get("plan_library") or {})
		rows.append(
			{
				"experiment_name": str(report.get("experiment_name") or ""),
				"status": str(report.get("matrix_status") or "unknown"),
				"report_file": str(report_file),
				"coverage_ratio": float(coverage.get("coverage_ratio") or 0.0),
				"solved_count": int(coverage.get("solved_count") or 0),
				"failed_count": int(coverage.get("failed_count") or 0),
				"paper_profile_ready": bool(paper.get("paper_profile_ready")),
				"blocking_failure_count": int(paper.get("blocking_failure_count") or 0),
				"plan_count": int(plan.get("plan_count") or 0),
			},
		)
	failed = tuple(row for row in rows if row["status"] != "succeeded")
	return {
		"matrix_name": matrix_name,
		"experiment_count": len(rows),
		"succeeded_count": len(rows) - len(failed),
		"failed_count": len(failed),
		"duration_seconds": perf_counter() - started,
		"summary_file": str(Path("matrix-summary.json")),
		"comparison_file": str(comparison_file),
		"best_by_coverage": comparison.get("best_by_coverage"),
		"rows": rows,
	}


def _failure_protocol(entry: dict[str, object]) -> dict[str, object]:
	label = str(entry.get("ablation_label") or entry.get("name") or "")
	mechanism_status = _entry_mechanism_status(entry)
	return {
		"scope": "bounded_domain_level_lifted_asl_evaluation",
		"training_source": "provided_pddl_training_problems",
		"evaluation_source": "provided_pddl_evaluation_problems",
		"synthesis_profile": str(entry.get("synthesis_profile") or "bootstrap"),
		"external_policy_count": len(tuple(entry.get("external_sketch_policies") or ())),
		"disabled_synthesis_mechanisms": list(
			tuple(entry.get("disabled_synthesis_mechanisms") or ()),
		),
		"mechanism_status": mechanism_status,
		"runtime_planner": "none",
		"baselines": [],
		"ablations": [
			{
				"label": label,
				"synthesis_profile": str(entry.get("synthesis_profile") or "bootstrap"),
				"external_policy_count": len(tuple(entry.get("external_sketch_policies") or ())),
				"counterexample_refinement": bool(
					entry.get("use_counterexample_refinement", False),
				),
				"use_synthesis_planner_traces": bool(
					entry.get("use_synthesis_planner_traces", False),
				),
				"disabled_synthesis_mechanisms": list(
					tuple(entry.get("disabled_synthesis_mechanisms") or ()),
				),
				"runtime_planner": "none",
				"mechanism_status": mechanism_status,
				"enabled_mechanisms": list(
					_mechanisms_by_status(mechanism_status, "enabled"),
				),
				"disabled_mechanisms": list(
					_mechanisms_by_status(mechanism_status, "disabled"),
				),
			},
		] if label else [],
		"limitations": [
			"entry failed before a domain-level ASL library could be evaluated",
		],
	}


def _entry_mechanism_status(entry: dict[str, object]) -> dict[str, str]:
	return {
		"external_sketch_evidence": (
			"enabled"
			if len(tuple(entry.get("external_sketch_policies") or ())) > 0
			else "disabled"
		),
		"counterexample_refinement": (
			"enabled" if bool(entry.get("use_counterexample_refinement", False)) else "disabled"
		),
		"offline_synthesis_planner_traces": (
			"enabled" if bool(entry.get("use_synthesis_planner_traces", False)) else "disabled"
		),
		"layer_c_ordering": (
			"disabled"
			if "layer_c_ordering" in set(
				str(item)
				for item in tuple(entry.get("disabled_synthesis_mechanisms") or ())
			)
			else "enabled"
		),
		"paper_profile_gate": (
			"enabled"
			if str(entry.get("synthesis_profile") or "bootstrap") == "paper"
			else "disabled"
		),
	}


def _mechanisms_by_status(
	mechanism_status: dict[str, str],
	status: str,
) -> tuple[str, ...]:
	order = (
		"external_sketch_evidence",
		"counterexample_refinement",
		"offline_synthesis_planner_traces",
		"layer_c_ordering",
		"paper_profile_gate",
	)
	return tuple(
		name
		for name in order
		if str(mechanism_status.get(name) or "") == status
	)


def _matrix_entry_metadata(entry: dict[str, object], *, index: int) -> dict[str, object]:
	return {
		"index": index,
		"name": _entry_name(entry, index=index),
		"synthesis_profile": str(entry.get("synthesis_profile") or "bootstrap"),
		"use_counterexample_refinement": bool(
			entry.get("use_counterexample_refinement", False),
		),
		"allow_paper_profile_failures": bool(
			entry.get("allow_paper_profile_failures", False),
		),
		"timeout_seconds": (
			float(entry["timeout_seconds"])
			if entry.get("timeout_seconds") is not None
			else None
		),
		"evaluation_timeout_seconds": _optional_float(
			entry.get("evaluation_timeout_seconds"),
		),
		"use_synthesis_planner_traces": bool(
			entry.get("use_synthesis_planner_traces", False),
		),
		"disabled_synthesis_mechanisms": list(
			tuple(entry.get("disabled_synthesis_mechanisms") or ()),
		),
	}


def _problem_files(
	entry: dict[str, object],
	*,
	key: str,
	config_base: Path,
) -> tuple[Path, ...]:
	explicit = tuple(entry.get(f"{key}_problems") or ())
	if explicit:
		return tuple(_resolve_path(path, config_base=config_base) for path in explicit)
	glob_text = str(entry.get(f"{key}_glob") or "").strip()
	if not glob_text:
		return ()
	base = _resolve_path(entry.get(f"{key}_base") or ".", config_base=config_base)
	files = tuple(sorted(base.glob(glob_text)))
	count = entry.get(f"{key}_count")
	if count is not None:
		files = files[: int(count)]
	return files


def _baseline_records(
	entry: dict[str, object],
	*,
	config_base: Path,
) -> tuple[dict[str, object], ...]:
	paths = tuple(
		_resolve_path(path, config_base=config_base)
		for path in tuple(entry.get("baseline_json") or ())
	)
	return _read_baseline_records(paths)


def _load_matrix_config(
	config_file: Path | None,
	*,
	preset: str,
) -> tuple[dict[str, object], Path]:
	if config_file is not None:
		path = config_file.expanduser().resolve()
		return json.loads(path.read_text(encoding="utf-8")), path.parent
	return _preset_config(preset), PROJECT_ROOT


def _preset_config(preset: str) -> dict[str, object]:
	return build_preset_config_from_registry(preset)


def _resolve_path(value: object, *, config_base: Path) -> Path:
	path = Path(str(value)).expanduser()
	if path.is_absolute():
		return path
	base_candidate = (config_base / path).resolve()
	if base_candidate.exists():
		return base_candidate
	return (PROJECT_ROOT / path).resolve()


def _optional_float(value: object) -> float | None:
	if value is None:
		return None
	return float(value)


def _restore_timer(previous_timer: tuple[float, float], *, elapsed: float) -> None:
	previous_delay, previous_interval = previous_timer
	if previous_delay <= 0:
		signal.setitimer(signal.ITIMER_REAL, 0.0)
		return
	signal.setitimer(
		signal.ITIMER_REAL,
		max(0.000001, previous_delay - elapsed),
		previous_interval,
	)


def _entry_name(entry: dict[str, object], *, index: int) -> str:
	name = str(entry.get("name") or "").strip()
	return name or f"experiment-{index}"


def _slug(text: str) -> str:
	value = "".join(character if character.isalnum() else "-" for character in text.lower())
	return "-".join(part for part in value.split("-") if part) or "experiment"


if __name__ == "__main__":
	main()
