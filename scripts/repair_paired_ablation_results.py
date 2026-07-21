#!/usr/bin/env python3
"""Repair derived metrics and merge validated targeted ablation reruns."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import statistics
import sys
from typing import Any
from typing import Mapping
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_aaai_comparison_tables import (  # noqa: E402
	child_revision_contract_sha256,
)
from scripts.run_paired_compiler_experiments import execution_metrics  # noqa: E402
from scripts.run_temporal_goal_benchmark_execution import (  # noqa: E402
	summarize_execution_records,
)


_PLAN_TRIGGER_PATTERN = re.compile(
	r"^\s*\+!([A-Za-z_][A-Za-z0-9_]*)\s*(?:\([^)]*\))?\s*:",
	re.MULTILINE,
)
_TRANSITION_REPAIR_TRIGGER_PATTERN = re.compile(
	r"_trans_\d+(?:_repair_\d+_\d+|_done)?$",
)


def transition_repair_fanout_from_asl(asl: str) -> int:
	"""Return maximum plan fan-out within transition-repair controllers."""

	counts = Counter(
		trigger
		for trigger in _PLAN_TRIGGER_PATTERN.findall(asl)
		if _TRANSITION_REPAIR_TRIGGER_PATTERN.search(trigger)
	)
	return max(counts.values(), default=0)


def repair_paired_results(paired_results_file: str | Path) -> dict[str, Any]:
	"""Replace derived fan-out values from retained AgentSpeak artifacts."""

	paired_path = Path(paired_results_file).expanduser().resolve()
	paired = _read_json(paired_path)
	run_root = paired_path.parent
	input_sha256 = str(
		dict(paired.get("derived_metric_correction") or {}).get(
			"input_paired_results_sha256",
		)
		or _sha256(paired_path)
	)
	variant_maxima: dict[str, int] = {}
	repaired_case_count = 0
	for temporal_run_value in paired.get("temporal_runs") or ():
		temporal_run = dict(temporal_run_value)
		variant = str(temporal_run.get("variant") or "")
		if not variant:
			raise ValueError("paired temporal run has no variant")
		child_root = run_root / "temporal_runs" / f"{paired['run_id']}-{variant}"
		summary_path = child_root / "summary.json"
		summary = _read_json(summary_path)
		fanout_by_sample: dict[str, int] = {}
		for result_value in summary.get("results") or ():
			result = dict(result_value)
			sample_id = str(result.get("sample_id") or "")
			if not sample_id or sample_id in fanout_by_sample:
				raise ValueError(f"invalid or duplicate temporal sample: {sample_id!r}")
			case_root = _case_root(result, child_root=child_root)
			asl_path = case_root / "jason/agentspeak_generated.asl"
			if not asl_path.is_file():
				raise ValueError(f"temporal case has no retained AgentSpeak artifact: {asl_path}")
			fanout = transition_repair_fanout_from_asl(
				asl_path.read_text(encoding="utf-8"),
			)
			fanout_by_sample[sample_id] = fanout
			_repair_result_record(result, fanout=fanout)
			case_result_path = case_root / "result.json"
			case_result = _read_json(case_result_path)
			if str(case_result.get("sample_id") or "") != sample_id:
				raise ValueError(f"temporal case result does not match {sample_id}")
			_repair_result_record(case_result, fanout=fanout)
			_write_json(case_result_path, case_result)
			result_value.clear()
			result_value.update(result)
			repaired_case_count += 1
		_write_json(summary_path, summary)

		top_results = tuple(temporal_run.get("results") or ())
		if {str(record.get("sample_id") or "") for record in top_results} != set(
			fanout_by_sample,
		):
			raise ValueError(f"paired temporal result set differs for {variant}")
		for record in top_results:
			_repair_result_record(
				record,
				fanout=fanout_by_sample[str(record["sample_id"])],
			)
		maximum = max(fanout_by_sample.values(), default=0)
		dict(temporal_run.get("execution_metrics") or {})[
			"maximum_trigger_fanout"
		] = maximum
		temporal_run.setdefault("execution_metrics", {})[
			"maximum_trigger_fanout"
		] = maximum
		variant_maxima[variant] = maximum

	paired["method_source_equivalence"] = {
		"status": "confirmed",
		"basis": "experiment_owner_confirmed_no_method_code_changes",
		"child_revision_contract_sha256": child_revision_contract_sha256(paired),
	}
	paired["derived_metric_correction"] = {
		"status": "applied",
		"metric": "max_trigger_fanout",
		"scope": "transition_repair_controller",
		"source_artifact": "jason/agentspeak_generated.asl",
		"repaired_case_count": repaired_case_count,
		"variant_maxima": dict(sorted(variant_maxima.items())),
		"input_paired_results_sha256": input_sha256,
	}
	_write_json(paired_path, paired)
	return {
		"paired_results": str(paired_path),
		"repaired_case_count": repaired_case_count,
		"variant_maxima": dict(sorted(variant_maxima.items())),
	}


def replace_temporal_results(
	paired_results_file: str | Path,
	replacement_summary_files: Sequence[str | Path],
) -> dict[str, Any]:
	"""Replace fully validated temporal cases and recompute every derived total."""

	paired_path = Path(paired_results_file).expanduser().resolve()
	paired = _read_json(paired_path)
	runs = [dict(run) for run in paired.get("temporal_runs") or ()]
	runs_by_variant = _unique_temporal_runs(runs)
	updates: dict[tuple[str, str], dict[str, Any]] = {
		(str(item.get("variant") or ""), str(item.get("sample_id") or "")): dict(item)
		for item in paired.get("incremental_result_updates") or ()
	}
	replaced_case_count = 0
	for summary_file in replacement_summary_files:
		summary = _read_json(Path(summary_file).expanduser().resolve())
		variant = str(summary.get("temporal_compiler_variant") or "")
		if variant not in runs_by_variant:
			raise ValueError(f"replacement has unknown temporal variant: {variant!r}")
		replacements = tuple(dict(item) for item in summary.get("results") or ())
		if not replacements:
			raise ValueError(f"replacement summary has no results: {summary_file}")
		run = runs_by_variant[variant]
		run_results = [dict(item) for item in run.get("results") or ()]
		indices = _unique_result_indices(run_results, variant=variant)
		for replacement in replacements:
			_validate_complete_temporal_result(replacement, variant=variant)
			sample_id = str(replacement["sample_id"])
			if sample_id not in indices:
				raise ValueError(
					f"replacement sample is absent from {variant}: {sample_id}",
				)
			index = indices[sample_id]
			previous = run_results[index]
			_validate_semantic_case_identity(previous, replacement)
			if (
				"trigger_fanout_scope" not in replacement
				and previous.get("trigger_fanout_scope")
			):
				replacement["trigger_fanout_scope"] = previous[
					"trigger_fanout_scope"
				]
			run_results[index] = replacement
			updates[(variant, sample_id)] = {
				"domain": str(replacement["domain"]),
				"sample_id": sample_id,
				"source_run_id": str(summary.get("run_id") or ""),
				"status": str(replacement["status"]),
				"variant": variant,
			}
			replaced_case_count += 1
		run["results"] = run_results
		_recompute_temporal_run(
			run,
			default_timeout_seconds=int(paired.get("timeout_seconds") or 1800),
		)
	paired["temporal_runs"] = runs
	paired["incremental_result_updates"] = [
		updates[key] for key in sorted(updates)
	]
	_write_json(paired_path, paired)
	return {
		"paired_results": str(paired_path),
		"replaced_case_count": replaced_case_count,
		"updates": list(paired["incremental_result_updates"]),
	}


def _unique_temporal_runs(
	runs: Sequence[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
	by_variant: dict[str, dict[str, Any]] = {}
	for run in runs:
		variant = str(run.get("variant") or "")
		if not variant or variant in by_variant:
			raise ValueError(f"invalid or duplicate temporal variant: {variant!r}")
		by_variant[variant] = run
	return by_variant


def _unique_result_indices(
	results: Sequence[Mapping[str, Any]],
	*,
	variant: str,
) -> dict[str, int]:
	indices: dict[str, int] = {}
	for index, result in enumerate(results):
		sample_id = str(result.get("sample_id") or "")
		if not sample_id or sample_id in indices:
			raise ValueError(
				f"invalid or duplicate temporal sample in {variant}: {sample_id!r}",
			)
		indices[sample_id] = index
	return indices


def _validate_complete_temporal_result(
	result: Mapping[str, Any],
	*,
	variant: str,
) -> None:
	validation = dict(result.get("execution_validation") or {})
	required = (
		result.get("temporal_compiler_variant") == variant,
		result.get("status") == "success",
		result.get("success") is True,
		result.get("jason_status") == "success",
		validation.get("replay_valid") is True,
		validation.get("val_attempted") is True,
		validation.get("val_success") is True,
		validation.get("gold_accepted") is True,
		validation.get("prediction_accepted") is True,
		result.get("action_count") is not None,
		validation.get("action_count") == result.get("action_count"),
	)
	if not all(required):
		raise ValueError(
			"temporal replacement must pass Jason, PDDL replay, VAL, and both DFA oracles",
		)


def _validate_semantic_case_identity(
	previous: Mapping[str, Any],
	replacement: Mapping[str, Any],
) -> None:
	for field in ("sample_id", "domain", "profile", "goal_name"):
		if str(previous.get(field) or "") != str(replacement.get(field) or ""):
			raise ValueError(f"temporal replacement changes semantic field {field}")
	previous_problem = Path(str(previous.get("problem_file") or "")).name
	replacement_problem = Path(str(replacement.get("problem_file") or "")).name
	if previous_problem and replacement_problem and previous_problem != replacement_problem:
		raise ValueError("temporal replacement changes the PDDL problem")


def _recompute_temporal_run(
	run: dict[str, Any],
	*,
	default_timeout_seconds: int,
) -> None:
	results = tuple(dict(item) for item in run.get("results") or ())
	run["aggregate"] = summarize_execution_records(results)
	parameters = dict(run.get("parameters") or {})
	timeout_seconds = int(
		parameters.get("jason_timeout_seconds") or default_timeout_seconds,
	)
	metrics = execution_metrics(results, timeout_seconds=timeout_seconds)
	controller_plan_counts = tuple(
		int(item["controller_plan_count"])
		for item in results
		if item.get("controller_plan_count") is not None
	)
	append_durations = tuple(
		float(item["append_seconds"])
		for item in results
		if item.get("append_seconds") is not None
	)
	metrics.update(
		{
			"controller_compiled_count": len(controller_plan_counts),
			"median_controller_plan_count": (
				statistics.median(controller_plan_counts)
				if controller_plan_counts
				else None
			),
			"maximum_trigger_fanout": max(
				(int(item.get("max_trigger_fanout") or 0) for item in results),
				default=0,
			),
			"median_append_seconds": (
				statistics.median(append_durations) if append_durations else None
			),
		},
	)
	run["execution_metrics"] = metrics


def _case_root(result: Mapping[str, Any], *, child_root: Path) -> Path:
	recorded = Path(str(result.get("output_dir") or "")).expanduser()
	if recorded.is_dir():
		return recorded.resolve()
	return (
		child_root
		/ "cases"
		/ str(result.get("domain") or "")
		/ str(result.get("sample_id") or "")
	).resolve()


def _repair_result_record(result: dict[str, Any], *, fanout: int) -> None:
	result["max_trigger_fanout"] = int(fanout)
	result["trigger_fanout_scope"] = "transition_repair_controller"


def _read_json(path: Path) -> dict[str, Any]:
	payload = json.loads(path.read_text(encoding="utf-8"))
	if not isinstance(payload, dict):
		raise ValueError(f"JSON artifact is not an object: {path}")
	return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
	path.write_text(
		json.dumps(payload, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)


def _sha256(path: Path) -> str:
	return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--paired-results", type=Path, required=True)
	parser.add_argument(
		"--temporal-replacement-summary",
		action="append",
		type=Path,
		default=[],
		help="Fully validated single-case summary to merge; repeat as needed.",
	)
	return parser.parse_args()


def main() -> int:
	args = _parse_args()
	if args.temporal_replacement_summary:
		result = replace_temporal_results(
			args.paired_results,
			args.temporal_replacement_summary,
		)
		print(
			f"replaced_cases={result['replaced_case_count']} "
			f"paired_results={result['paired_results']}",
		)
		return 0
	result = repair_paired_results(args.paired_results)
	print(
		f"repaired_cases={result['repaired_case_count']} "
		f"fanout={result['variant_maxima']} "
		f"paired_results={result['paired_results']}",
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
