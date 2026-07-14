#!/usr/bin/env python3
"""Generate gated GP2PL empirical figures from frozen experiment artifacts."""

from __future__ import annotations

import argparse
from bisect import bisect_right
from datetime import datetime
from datetime import timezone
import hashlib
import io
import json
from pathlib import Path
import statistics
import sys
from typing import Any
from typing import Mapping
from typing import Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FixedLocator  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_FILE = (
	PROJECT_ROOT / "latex_code/aamas_method_paper/figures/fig2_evaluation.pdf"
)
DEFAULT_VALIDATION_RUN_ROOT = PROJECT_ROOT / "artifacts/jason_full_test_runs"
REGISTERED_SEEDS = (0, 1, 2, 3, 4)
REGISTERED_NUM_WORKERS = 6
REGISTERED_TIMEOUT_SECONDS = 1800
REGISTERED_JAVA_STACK_SIZE = "64m"
MINIMUM_LOG_SECONDS = 0.1
FIGURE_WIDTH_INCHES = 7.0
FIGURE_HEIGHT_INCHES = 3.0
TEMPORAL_MARKER_SECONDS = (1.0, 10.0, 100.0, 1800.0)

DOMAIN_ORDER = (
	"barman",
	"ferry",
	"gripper",
	"logistics",
	"miconic",
	"rovers",
	"satellite",
	"transport",
	"numeric-ferry",
	"numeric-miconic",
	"numeric-minecraft",
	"numeric-transport",
	"blocksworld-clear",
	"blocksworld-on",
	"blocksworld-tower",
	"depots",
)
BENCHMARK_GROUPS = (
	("classical", "Classical", DOMAIN_ORDER[:8]),
	("numeric", "Numeric", DOMAIN_ORDER[8:12]),
	("serialized_width", "Serialized-width", DOMAIN_ORDER[12:]),
)
ATOMIC_VARIANTS = (
	("validated_evidence_adapter", "Evidence Only"),
	("action_only_closure", "Action Closure"),
	("maximal_certified_program", "Maximal Certified"),
	("full", "Full GP2PL"),
)
TEMPORAL_VARIANTS = (
	("dfa_aware_unprotected", "Unprotected DFA"),
	("certified_flat", "Certified Flat"),
	("certified_balanced", "Certified Balanced"),
	("completion_boundary_monitor", "Completion Monitor"),
)

COLORS = {
	"blue": "#0072B2",
	"orange": "#E69F00",
	"green": "#009E73",
	"purple": "#CC79A7",
	"gray": "#7F7F7F",
	"light_gray": "#D9D9D9",
	"text": "#1A1A1A",
}
ATOMIC_STYLES = {
	"validated_evidence_adapter": (COLORS["gray"], "o"),
	"action_only_closure": (COLORS["orange"], "s"),
	"maximal_certified_program": (COLORS["green"], "^"),
	"full": (COLORS["blue"], "D"),
}
TEMPORAL_STYLES = {
	"dfa_aware_unprotected": (COLORS["gray"], ":", "o"),
	"certified_flat": (COLORS["orange"], "--", "s"),
	"certified_balanced": (COLORS["blue"], "-", "D"),
	"completion_boundary_monitor": (COLORS["purple"], "-.", "^"),
}
GROUP_STYLES = {
	"classical": (COLORS["blue"], "o"),
	"numeric": (COLORS["green"], "s"),
	"serialized_width": (COLORS["orange"], "D"),
}


def build_figure_dataset(payload: Mapping[str, Any]) -> dict[str, Any]:
	"""Validate one paired paper matrix and derive every plotted value."""

	_validate_release_gate(payload)
	atomic_runs = tuple(payload.get("atomic_runs") or ())
	atomic_by_key = _indexed_atomic_runs(atomic_runs)
	atomic_domain_coverage: dict[str, dict[str, list[float]]] = {}
	for domain in DOMAIN_ORDER:
		atomic_domain_coverage[domain] = {
			"evidence_adapter": [
				_domain_coverage(
					atomic_by_key[(seed, "validated_evidence_adapter")],
					domain,
				)
				for seed in REGISTERED_SEEDS
			],
			"full": [
				_domain_coverage(atomic_by_key[(seed, "full")], domain)
				for seed in REGISTERED_SEEDS
			],
		}

	atomic_tradeoff: dict[str, list[dict[str, float | int]]] = {
		variant: [] for variant, _method in ATOMIC_VARIANTS
	}
	for variant, _method in ATOMIC_VARIANTS:
		for seed in REGISTERED_SEEDS:
			run = atomic_by_key[(seed, variant)]
			selected_branch_count = 0
			valid_trace_count = 0
			test_count = 0
			for domain in DOMAIN_ORDER:
				domain_record = _domain_record(run, domain)
				library_metrics = _mapping_field(
					domain_record,
					"library_metrics",
					label=f"{variant} seed {seed} domain {domain}",
				)
				execution = _execution_metrics(domain_record, domain=domain)
				branch_count = int(library_metrics.get("selected_branch_count") or 0)
				if branch_count < 0:
					raise ValueError("selected branch count cannot be negative")
				selected_branch_count += branch_count
				valid_trace_count += int(execution["valid_trace_count"])
				test_count += int(execution["test_count"])
			if selected_branch_count <= 0:
				raise ValueError(
					f"{variant} seed {seed} has no emitted branches for log-scale plot",
				)
			atomic_tradeoff[variant].append(
				{
					"seed": seed,
					"selected_branch_count": selected_branch_count,
					"coverage_percent": 100.0 * valid_trace_count / test_count,
				},
			)

	temporal_runs = tuple(payload.get("temporal_runs") or ())
	temporal_by_variant = _indexed_temporal_runs(temporal_runs)
	temporal_curves: dict[str, dict[str, Any]] = {}
	for variant, _method in TEMPORAL_VARIANTS:
		results = tuple(temporal_by_variant[variant].get("results") or ())
		x_values, y_values = cumulative_solved_fraction(
			results,
			timeout_seconds=REGISTERED_TIMEOUT_SECONDS,
		)
		temporal_curves[variant] = {
			"x_seconds": x_values,
			"solved_percent": y_values,
			"sample_count": len(results),
			"solved_count": sum(_temporal_result_is_valid(row) for row in results),
			"final_percent": y_values[-1],
		}

	return {
		"source_revision": dict(payload.get("source_revision") or {}),
		"atomic_domain_coverage": atomic_domain_coverage,
		"atomic_tradeoff": atomic_tradeoff,
		"temporal_curves": temporal_curves,
		"timeout_seconds": REGISTERED_TIMEOUT_SECONDS,
	}


def cumulative_solved_fraction(
	records: Sequence[Mapping[str, Any]],
	*,
	timeout_seconds: int,
) -> tuple[list[float], list[float]]:
	"""Return an all-query cumulative solved curve; failures stay in its denominator."""

	if not records:
		raise ValueError("temporal matrix has no query records")
	cutoff = float(timeout_seconds)
	solved_times: list[float] = []
	for record in records:
		if not _temporal_result_is_valid(record):
			continue
		raw_duration = record.get("duration_seconds")
		if raw_duration is None:
			raise ValueError("successful temporal query has no duration")
		duration = float(raw_duration)
		if duration < 0.0 or duration > cutoff:
			raise ValueError("successful temporal query duration is outside the timeout")
		solved_times.append(max(MINIMUM_LOG_SECONDS, duration))
	solved_times.sort()
	total_count = len(records)
	x_values = [MINIMUM_LOG_SECONDS]
	y_values = [0.0]
	for solved_count, duration in enumerate(solved_times, start=1):
		x_values.append(duration)
		y_values.append(100.0 * solved_count / total_count)
	x_values.append(cutoff)
	y_values.append(100.0 * len(solved_times) / total_count)
	return x_values, y_values


def build_five_seed_figure_dataset(
	payload: Mapping[str, Any],
	*,
	run_summaries: Mapping[int, Mapping[str, Any]],
	run_seconds: Mapping[int, Mapping[tuple[str, int], float]],
) -> dict[str, Any]:
	"""Validate five Full GP2PL runs and derive coverage and runtime curves."""

	_validate_five_seed_result_gate(payload)
	protocol = _mapping_field(payload, "protocol", label="five-seed result")
	source_aggregate = _mapping_field(
		payload,
		"source_aggregate",
		label="five-seed result",
	)
	seeds = tuple(int(seed) for seed in protocol["seeds"])
	if set(run_summaries) != set(seeds) or set(run_seconds) != set(seeds):
		raise ValueError("five-seed figure inputs do not cover every registered seed")

	domain_rows = {
		str(row.get("domain") or ""): row
		for row in tuple(payload.get("domains") or ())
		if isinstance(row, Mapping)
	}
	if set(domain_rows) != set(DOMAIN_ORDER):
		raise ValueError("five-seed result does not contain the registered 16 domains")
	domain_coverage: dict[str, list[float]] = {}
	for domain in DOMAIN_ORDER:
		rates = tuple(domain_rows[domain].get("success_rates") or ())
		if len(rates) != len(seeds):
			raise ValueError(f"domain {domain} does not contain five seed rates")
		domain_coverage[domain] = [100.0 * float(rate) for rate in rates]

	seed_result_rows = {
		int(row.get("seed", -1)): row
		for row in tuple(payload.get("seed_results") or ())
		if isinstance(row, Mapping)
	}
	if set(seed_result_rows) != set(seeds):
		raise ValueError("five-seed result has incomplete seed summaries")

	validated_rows: dict[int, list[dict[str, Any]]] = {}
	observed_worker_counts: set[int] = set()
	observed_source_commits: set[str] = set()
	pooled_success_count = 0
	pooled_evaluation_count = 0
	for seed_index, seed in enumerate(seeds):
		summary = run_summaries[seed]
		seed_result = seed_result_rows[seed]
		_validate_five_seed_child_summary(
			summary,
			seed=seed,
			expected_run_id=str(seed_result.get("run_id") or ""),
			expected_source_commit=str(seed_result.get("source_commit") or ""),
		)
		settings = _mapping_field(summary, "settings", label=f"seed {seed} summary")
		observed_worker_counts.add(int(settings.get("num_workers") or 0))
		observed_source_commits.add(
			str(_mapping_field(summary, "source_revision", label=f"seed {seed}").get(
				"commit",
			)
			or ""),
		)

		rows: list[dict[str, Any]] = []
		domain_success = {domain: 0 for domain in DOMAIN_ORDER}
		domain_total = {domain: 0 for domain in DOMAIN_ORDER}
		seen_cases: set[tuple[str, int]] = set()
		for raw_record in tuple(summary.get("validations") or ()):
			if not isinstance(raw_record, Mapping):
				raise ValueError(f"seed {seed} has a malformed validation record")
			domain = str(raw_record.get("domain") or "")
			test_index = int(raw_record.get("test_index") or 0)
			case_key = (domain, test_index)
			if domain not in domain_total or test_index <= 0 or case_key in seen_cases:
				raise ValueError(f"seed {seed} has an invalid case identifier {case_key}")
			seen_cases.add(case_key)
			domain_total[domain] += 1
			success = raw_record.get("success") is True
			if success:
				if (
					raw_record.get("status") != "success"
					or raw_record.get("plan_verifier_attempted") is not True
					or raw_record.get("plan_verifier_success") is not True
				):
					raise ValueError(
						f"seed {seed} case {case_key} lacks Jason and VAL acceptance",
					)
				if case_key not in run_seconds[seed]:
					raise ValueError(f"seed {seed} case {case_key} has no Jason runtime")
				duration = float(run_seconds[seed][case_key])
				if duration < 0.0 or duration > REGISTERED_TIMEOUT_SECONDS:
					raise ValueError(
						f"seed {seed} case {case_key} runtime is outside the deadline",
					)
				domain_success[domain] += 1
			else:
				duration = None
			rows.append(
				{
					"domain": domain,
					"test_index": test_index,
					"success": success,
					"run_seconds": duration,
				},
			)

		for domain in DOMAIN_ORDER:
			expected_total = int(domain_rows[domain].get("test_count") or 0)
			expected_successes = tuple(
				int(value) for value in domain_rows[domain].get("success_counts") or ()
			)
			if len(expected_successes) != len(seeds):
				raise ValueError(f"domain {domain} has incomplete success counts")
			if domain_total[domain] != expected_total:
				raise ValueError(f"seed {seed} domain {domain} test count disagrees")
			if domain_success[domain] != expected_successes[seed_index]:
				raise ValueError(f"seed {seed} domain {domain} coverage disagrees")
		seed_success_count = sum(row["success"] for row in rows)
		if seed_success_count != int(seed_result.get("success_count") or -1):
			raise ValueError(f"seed {seed} success count disagrees")
		if len(rows) != int(seed_result.get("evaluation_count") or -1):
			raise ValueError(f"seed {seed} evaluation count disagrees")
		validated_rows[seed] = rows
		pooled_success_count += seed_success_count
		pooled_evaluation_count += len(rows)

	if len(observed_worker_counts) != 1 or next(iter(observed_worker_counts)) <= 0:
		raise ValueError("five seed runs do not share one positive Jason worker count")
	observed_worker_count = next(iter(observed_worker_counts))
	if observed_worker_count != int(protocol.get("validation_workers") or 0):
		raise ValueError("five seed worker count disagrees with the frozen protocol")
	freeze = _mapping_field(payload, "compiler_freeze", label="five-seed result")
	formal_revisions = {str(value) for value in freeze.get("formal_run_revisions") or ()}
	if observed_source_commits != formal_revisions:
		raise ValueError("five seed source revisions disagree with the compiler freeze")

	aggregate = _mapping_field(payload, "aggregate", label="five-seed result")
	if pooled_success_count != int(aggregate.get("pooled_success_count") or -1):
		raise ValueError("five-seed pooled success count disagrees")
	if pooled_evaluation_count != int(aggregate.get("pooled_evaluation_count") or -1):
		raise ValueError("five-seed pooled evaluation count disagrees")

	group_curves = {
		group_key: _five_seed_group_curve(
			validated_rows,
			seeds=seeds,
			domains=set(domains),
		)
		for group_key, _label, domains in BENCHMARK_GROUPS
	}
	return {
		"domain_coverage": domain_coverage,
		"group_curves": group_curves,
		"seeds": list(seeds),
		"jason_workers": observed_worker_count,
		"source_revisions": sorted(observed_source_commits),
		"compiler_closure_sha256": str(freeze.get("closure_sha256") or ""),
		"source_aggregate_run_id": str(source_aggregate.get("run_id") or ""),
		"source_aggregate_sha256": str(source_aggregate.get("sha256") or ""),
		"pooled_success_count": pooled_success_count,
		"pooled_evaluation_count": pooled_evaluation_count,
		"mean_success_percent": 100.0 * float(aggregate["mean_success_rate"]),
		"sample_sd_success_percent": (
			100.0 * float(aggregate["sample_sd_success_rate"])
		),
		"timeout_seconds": REGISTERED_TIMEOUT_SECONDS,
	}


def _validate_five_seed_result_gate(payload: Mapping[str, Any]) -> None:
	if payload.get("artifact_kind") != (
		"gp2pl_five_seed_full_compiler_submission_result"
	):
		raise ValueError("unsupported five-seed result artifact")
	if int(payload.get("schema_version") or 0) != 1:
		raise ValueError("unsupported five-seed result schema")
	protocol = _mapping_field(payload, "protocol", label="five-seed result")
	expected_protocol = {
		"method": "Full GP2PL",
		"compiler_variant": "full",
		"atomic_library_mode": "validated-policy-lifting",
		"independent_seed_runs": True,
		"evidence_union": False,
		"best_seed_selection": False,
	}
	for key, expected in expected_protocol.items():
		if protocol.get(key) != expected:
			raise ValueError(f"five-seed result has unexpected {key}")
	if tuple(protocol.get("seeds") or ()) != REGISTERED_SEEDS:
		raise ValueError("five-seed result must contain seeds 0--4")
	if int(protocol.get("domain_count") or 0) != len(DOMAIN_ORDER):
		raise ValueError("five-seed result must contain 16 domains")
	source_aggregate = _mapping_field(
		payload,
		"source_aggregate",
		label="five-seed result",
	)
	if source_aggregate.get("verified_against_child_runs") is not True:
		raise ValueError("five-seed result has an unverified source aggregate")
	if len(str(source_aggregate.get("sha256") or "")) != 64:
		raise ValueError("five-seed result source aggregate has no SHA-256")
	expected_source_protocol = {
		"moose_internal_workers": 1,
		"moose_seed_parallelism": len(REGISTERED_SEEDS),
		"cross_seed_jason_parallelism": 1,
		"jason_workers_per_repetition": int(
			protocol.get("validation_workers") or 0,
		),
	}
	for key, expected in expected_source_protocol.items():
		if source_aggregate.get(key) != expected:
			if key == "jason_workers_per_repetition":
				raise ValueError(
					"five seed worker count disagrees with source aggregate",
				)
			raise ValueError(
				f"five-seed result source aggregate has unexpected {key}",
			)
	freeze = _mapping_field(payload, "compiler_freeze", label="five-seed result")
	if freeze.get("byte_identical_to_formal_run_revisions") is not True:
		raise ValueError("five-seed result lacks a byte-identical compiler freeze")
	if len(str(freeze.get("closure_sha256") or "")) < 16:
		raise ValueError("five-seed result lacks a compiler closure hash")


def _validate_five_seed_child_summary(
	summary: Mapping[str, Any],
	*,
	seed: int,
	expected_run_id: str,
	expected_source_commit: str,
) -> None:
	if summary.get("artifact_kind") != (
		"full_test_jason_validation_from_moose_asl_batch"
	):
		raise ValueError(f"seed {seed} has the wrong validation artifact kind")
	if str(summary.get("run_id") or "") != expected_run_id:
		raise ValueError(f"seed {seed} validation run id disagrees")
	settings = _mapping_field(summary, "settings", label=f"seed {seed} summary")
	expected_settings = {
		"atomic_library_mode": "validated-policy-lifting",
		"compiler_variant": "full",
		"method": "Full Compiler",
		"require_plan_verifier": True,
		"timeout_seconds": REGISTERED_TIMEOUT_SECONDS,
		"plan_verifier_timeout_seconds": REGISTERED_TIMEOUT_SECONDS,
		"jason_java_stack_size": REGISTERED_JAVA_STACK_SIZE,
	}
	for key, expected in expected_settings.items():
		if settings.get(key) != expected:
			raise ValueError(f"seed {seed} has unexpected {key}")
	revision = _mapping_field(summary, "source_revision", label=f"seed {seed}")
	if str(revision.get("commit") or "") != expected_source_commit:
		raise ValueError(f"seed {seed} source revision disagrees")


def _five_seed_group_curve(
	validated_rows: Mapping[int, Sequence[Mapping[str, Any]]],
	*,
	seeds: Sequence[int],
	domains: set[str],
) -> dict[str, Any]:
	seed_success_times: dict[int, list[float]] = {}
	seed_totals: dict[int, int] = {}
	all_times = {MINIMUM_LOG_SECONDS, float(REGISTERED_TIMEOUT_SECONDS)}
	for seed in seeds:
		relevant = [row for row in validated_rows[seed] if row["domain"] in domains]
		seed_totals[seed] = len(relevant)
		times = sorted(
			max(MINIMUM_LOG_SECONDS, float(row["run_seconds"]))
			for row in relevant
			if row["success"]
		)
		seed_success_times[seed] = times
		all_times.update(times)
	if len(set(seed_totals.values())) != 1 or not seed_totals:
		raise ValueError("benchmark group has inconsistent seed denominators")
	x_values = sorted(all_times)
	seed_curves = {
		seed: [
			100.0 * bisect_right(seed_success_times[seed], value) / seed_totals[seed]
			for value in x_values
		]
		for seed in seeds
	}
	columns = tuple(zip(*(seed_curves[seed] for seed in seeds), strict=True))
	mean_values = [statistics.mean(column) for column in columns]
	minimum_values = [min(column) for column in columns]
	maximum_values = [max(column) for column in columns]
	return {
		"x_seconds": x_values,
		"mean_percent": mean_values,
		"minimum_percent": minimum_values,
		"maximum_percent": maximum_values,
		"seed_percent": seed_curves,
		"case_count_per_seed": next(iter(seed_totals.values())),
		"final_percent": mean_values[-1],
	}


def generate_empirical_figure(
	*,
	paired_results_file: str | Path,
	output_file: str | Path,
) -> dict[str, Any]:
	"""Render the empirical vector PDF only after all release gates pass."""

	input_path = Path(paired_results_file).expanduser().resolve()
	output_path = Path(output_file).expanduser().resolve()
	diagnostic_path = output_path.with_suffix(".diagnostic.json")
	try:
		payload = _read_json(input_path)
		dataset = build_figure_dataset(payload)
	except (OSError, TypeError, ValueError) as error:
		_write_json(
			diagnostic_path,
			{
				"artifact_kind": "gp2pl_empirical_figure_diagnostic",
				"success": False,
				"source_file": _portable_artifact_path(input_path),
				"output_file_untouched": _portable_artifact_path(output_path),
				"error": str(error),
			},
		)
		raise

	pdf_bytes = _render_empirical_figure(dataset)
	output_path.parent.mkdir(parents=True, exist_ok=True)
	output_path.write_bytes(pdf_bytes)
	temporal_curves = dict(dataset["temporal_curves"])
	metadata = {
		"schema_version": 1,
		"artifact_kind": "gp2pl_empirical_figure",
		"source_file": _portable_artifact_path(input_path),
		"source_sha256": _sha256(input_path),
		"source_revision": dict(dataset["source_revision"]),
		"output_file": _portable_artifact_path(output_path),
		"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
		"atomic_seed_count": len(REGISTERED_SEEDS),
		"atomic_domain_count": len(DOMAIN_ORDER),
		"atomic_variant_count": len(ATOMIC_VARIANTS),
		"temporal_variant_count": len(TEMPORAL_VARIANTS),
		"temporal_sample_count": int(
			next(iter(temporal_curves.values()))["sample_count"],
		),
		"timeout_seconds": REGISTERED_TIMEOUT_SECONDS,
		"figure_width_inches": FIGURE_WIDTH_INCHES,
		"figure_height_inches": FIGURE_HEIGHT_INCHES,
	}
	_write_json(output_path.with_suffix(".metadata.json"), metadata)
	_write_json(
		diagnostic_path,
		{
			"artifact_kind": "gp2pl_empirical_figure_diagnostic",
			"success": True,
			"source_file": _portable_artifact_path(input_path),
			"output_file": _portable_artifact_path(output_path),
		},
	)
	return metadata


def generate_five_seed_empirical_figure(
	*,
	five_seed_results_file: str | Path,
	validation_run_root: str | Path,
	output_file: str | Path,
) -> dict[str, Any]:
	"""Render the main five-seed coverage figure from frozen, hashed inputs."""

	input_path = Path(five_seed_results_file).expanduser().resolve()
	run_root = Path(validation_run_root).expanduser().resolve()
	output_path = Path(output_file).expanduser().resolve()
	diagnostic_path = output_path.with_suffix(".diagnostic.json")
	try:
		payload = _read_json(input_path)
		run_summaries, run_seconds, child_hashes = _load_five_seed_run_inputs(
			payload,
			validation_run_root=run_root,
		)
		dataset = build_five_seed_figure_dataset(
			payload,
			run_summaries=run_summaries,
			run_seconds=run_seconds,
		)
	except (OSError, TypeError, ValueError) as error:
		_write_json(
			diagnostic_path,
			{
				"artifact_kind": "gp2pl_five_seed_figure_diagnostic",
				"success": False,
				"source_file": _portable_artifact_path(input_path),
				"output_file_untouched": _portable_artifact_path(output_path),
				"error": str(error),
			},
		)
		raise

	pdf_bytes = _render_five_seed_figure(dataset)
	output_path.parent.mkdir(parents=True, exist_ok=True)
	output_path.write_bytes(pdf_bytes)
	metadata = {
		"schema_version": 1,
		"artifact_kind": "gp2pl_five_seed_empirical_figure",
		"source_file": _portable_artifact_path(input_path),
		"source_sha256": _sha256(input_path),
		"source_aggregate_run_id": dataset["source_aggregate_run_id"],
		"source_aggregate_sha256": dataset["source_aggregate_sha256"],
		"child_summary_sha256": child_hashes,
		"output_file": _portable_artifact_path(output_path),
		"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
		"seed_count": len(dataset["seeds"]),
		"domain_count": len(DOMAIN_ORDER),
		"benchmark_group_count": len(BENCHMARK_GROUPS),
		"pooled_success_count": int(dataset["pooled_success_count"]),
		"pooled_evaluation_count": int(dataset["pooled_evaluation_count"]),
		"mean_success_percent": float(dataset["mean_success_percent"]),
		"sample_sd_success_percent": float(
			dataset["sample_sd_success_percent"],
		),
		"jason_workers": int(dataset["jason_workers"]),
		"timeout_seconds": REGISTERED_TIMEOUT_SECONDS,
		"runtime_measure": "jason_timing_profile.run_seconds",
		"compiler_closure_sha256": dataset["compiler_closure_sha256"],
		"source_revisions": dataset["source_revisions"],
		"figure_width_inches": FIGURE_WIDTH_INCHES,
		"figure_height_inches": FIGURE_HEIGHT_INCHES,
	}
	_write_json(output_path.with_suffix(".metadata.json"), metadata)
	_write_json(
		diagnostic_path,
		{
			"artifact_kind": "gp2pl_five_seed_figure_diagnostic",
			"success": True,
			"source_file": _portable_artifact_path(input_path),
			"output_file": _portable_artifact_path(output_path),
		},
	)
	return metadata


def _load_five_seed_run_inputs(
	payload: Mapping[str, Any],
	*,
	validation_run_root: Path,
) -> tuple[
	dict[int, dict[str, Any]],
	dict[int, dict[tuple[str, int], float]],
	dict[str, str],
]:
	seed_rows = tuple(payload.get("seed_results") or ())
	run_summaries: dict[int, dict[str, Any]] = {}
	run_seconds: dict[int, dict[tuple[str, int], float]] = {}
	child_hashes: dict[str, str] = {}
	for seed_row in seed_rows:
		if not isinstance(seed_row, Mapping):
			raise ValueError("five-seed result contains a malformed seed row")
		seed = int(seed_row.get("seed", -1))
		run_id = str(seed_row.get("run_id") or "")
		run_dir = validation_run_root / run_id
		summary_file = run_dir / "summary.json"
		observed_hash = _sha256(summary_file)
		expected_hash = str(seed_row.get("summary_sha256") or "")
		if observed_hash != expected_hash:
			raise ValueError(f"seed {seed} child summary hash disagrees")
		summary = _read_json(summary_file)
		run_summaries[seed] = summary
		child_hashes[str(seed)] = observed_hash
		seed_times: dict[tuple[str, int], float] = {}
		for validation in tuple(summary.get("validations") or ()):
			if not isinstance(validation, Mapping) or validation.get("success") is not True:
				continue
			domain = str(validation.get("domain") or "")
			test_index = int(validation.get("test_index") or 0)
			runtime_file = _resolve_jason_validation_file(
				validation,
				run_dir=run_dir,
			)
			runtime_payload = _read_json(runtime_file)
			timing = _mapping_field(
				runtime_payload,
				"timing_profile",
				label=f"seed {seed} case {(domain, test_index)}",
			)
			raw_seconds = timing.get("run_seconds")
			if raw_seconds is None:
				raise ValueError(
					f"seed {seed} case {(domain, test_index)} has no run_seconds",
				)
			seed_times[(domain, test_index)] = float(raw_seconds)
		run_seconds[seed] = seed_times
	return run_summaries, run_seconds, child_hashes


def _resolve_jason_validation_file(
	validation: Mapping[str, Any],
	*,
	run_dir: Path,
) -> Path:
	output_dir = Path(str(validation.get("output_dir") or ""))
	direct_path = output_dir / "jason_validation.json"
	if direct_path.is_file():
		return direct_path
	domain = str(validation.get("domain") or "")
	portable_path = run_dir / "jason" / domain / output_dir.name / "jason_validation.json"
	if portable_path.is_file():
		return portable_path
	raise ValueError(f"missing Jason timing artifact for {domain}/{output_dir.name}")


def _validate_release_gate(payload: Mapping[str, Any]) -> None:
	for key in (
		"success",
		"paper_matrix_complete",
		"infrastructure_complete",
	):
		if payload.get(key) is not True:
			label = key.replace("_", " ")
			raise ValueError(f"paired result gate failed: {label}")
	if payload.get("paired_inputs_verified") is not True:
		raise ValueError("paired result inputs are not paired")
	if dict(payload.get("atomic_pairing") or {}).get("paired") is not True:
		raise ValueError("paired result gate failed: atomic inputs are not paired")
	if dict(payload.get("temporal_pairing") or {}).get("paired") is not True:
		raise ValueError("paired result gate failed: temporal inputs are not paired")
	if tuple(payload.get("registered_seeds") or ()) != REGISTERED_SEEDS:
		raise ValueError("paired result must contain registered seeds 0--4")
	observed_domains = tuple(str(item) for item in payload.get("domains") or ())
	if len(observed_domains) != len(DOMAIN_ORDER) or set(observed_domains) != set(
		DOMAIN_ORDER,
	):
		raise ValueError("paired result does not contain the registered 16 domains")
	if int(payload.get("num_workers") or 0) != REGISTERED_NUM_WORKERS:
		raise ValueError("paired result does not use six registered execution workers")
	if int(payload.get("timeout_seconds") or 0) != REGISTERED_TIMEOUT_SECONDS:
		raise ValueError("paired result does not use the registered 1,800-second timeout")
	if str(payload.get("jason_java_stack_size") or "") != REGISTERED_JAVA_STACK_SIZE:
		raise ValueError("paired result does not use the registered 64m Java stack")
	revision = dict(payload.get("source_revision") or {})
	if len(str(revision.get("commit") or "")) < 8:
		raise ValueError("paired result has no pinned source revision")
	if revision.get("tracked_changes") is not False:
		raise ValueError("paired result has tracked source changes")
	if revision.get("untracked_files") is not False:
		raise ValueError("paired result has untracked source files")
	expected_commit = str(revision["commit"])
	_validate_seed_manifests(payload)
	for run in tuple(payload.get("atomic_runs") or ()):
		summary = _mapping_field(run, "summary", label="atomic child run")
		_validate_child_revision(
			_mapping_field(summary, "source_revision", label="atomic child run"),
			expected_commit=expected_commit,
			label="atomic child run",
		)
		_validate_execution_protocol(
			_mapping_field(summary, "settings", label="atomic child run"),
			label="atomic child run",
			timeout_key="timeout_seconds",
		)
	for run in tuple(payload.get("temporal_runs") or ()):
		_validate_child_revision(
			_mapping_field(run, "source_revision", label="temporal child run"),
			expected_commit=expected_commit,
			label="temporal child run",
		)
		_validate_execution_protocol(
			_mapping_field(run, "parameters", label="temporal child run"),
			label="temporal child run",
			timeout_key="jason_timeout_seconds",
		)


def _validate_seed_manifests(payload: Mapping[str, Any]) -> None:
	manifests = payload.get("seed_batch_manifests")
	if not isinstance(manifests, Mapping) or set(manifests) != {
		str(seed) for seed in REGISTERED_SEEDS
	}:
		raise ValueError("paired result has incomplete MOOSE seed manifests")
	for seed in REGISTERED_SEEDS:
		manifest = _mapping_field(
			manifests,
			str(seed),
			label=f"MOOSE seed {seed}",
		)
		settings = _mapping_field(
			manifest,
			"settings",
			label=f"MOOSE seed {seed}",
		)
		expected = {
			"random_seed": seed,
			"num_workers": 1,
			"num_permutations": 3,
			"goal_max_size": 1,
			"train_timeout_seconds": 43200,
		}
		for key, value in expected.items():
			raw_value = settings.get(key)
			if raw_value is None or int(raw_value) != value:
				raise ValueError(f"MOOSE seed {seed} has nonregistered {key}")
		if float(settings.get("max_rss_gb") or 0.0) != 16.0:
			raise ValueError(f"MOOSE seed {seed} has nonregistered memory limit")


def _validate_child_revision(
	revision: Mapping[str, Any],
	*,
	expected_commit: str,
	label: str,
) -> None:
	if revision.get("tracked_changes") is not False:
		raise ValueError(f"{label} has tracked source changes")
	if revision.get("untracked_files") is not False:
		raise ValueError(f"{label} has untracked source files")
	if str(revision.get("commit") or "") != expected_commit:
		raise ValueError(f"{label} does not share the paired source revision")


def _validate_execution_protocol(
	settings: Mapping[str, Any],
	*,
	label: str,
	timeout_key: str,
) -> None:
	if int(settings.get("num_workers") or 0) != REGISTERED_NUM_WORKERS:
		raise ValueError(f"{label} does not use six execution workers")
	if int(settings.get(timeout_key) or 0) != REGISTERED_TIMEOUT_SECONDS:
		raise ValueError(f"{label} does not use the registered timeout")
	if int(settings.get("plan_verifier_timeout_seconds") or 0) != (
		REGISTERED_TIMEOUT_SECONDS
	):
		raise ValueError(f"{label} does not use the registered VAL timeout")
	if str(settings.get("jason_java_stack_size") or "") != REGISTERED_JAVA_STACK_SIZE:
		raise ValueError(f"{label} does not use the registered Java stack")


def _indexed_atomic_runs(
	runs: Sequence[Mapping[str, Any]],
) -> dict[tuple[int, str], Mapping[str, Any]]:
	expected = {
		(seed, variant)
		for seed in REGISTERED_SEEDS
		for variant, _method in ATOMIC_VARIANTS
	}
	indexed: dict[tuple[int, str], Mapping[str, Any]] = {}
	for run in runs:
		key = (int(run.get("seed", -1)), str(run.get("variant") or ""))
		if key in indexed:
			raise ValueError(f"duplicate atomic matrix cell: {key}")
		indexed[key] = run
	if set(indexed) != expected:
		raise ValueError("atomic matrix is incomplete or contains unregistered cells")
	for (seed, variant), run in indexed.items():
		domains = dict(run.get("domains") or {})
		if set(domains) != set(DOMAIN_ORDER) or len(domains) != len(DOMAIN_ORDER):
			raise ValueError(
				f"atomic matrix domain set is incomplete for seed={seed}, variant={variant}",
			)
	return indexed


def _indexed_temporal_runs(
	runs: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
	expected = {variant for variant, _method in TEMPORAL_VARIANTS}
	indexed: dict[str, Mapping[str, Any]] = {}
	for run in runs:
		variant = str(run.get("variant") or "")
		if variant in indexed:
			raise ValueError(f"duplicate temporal matrix cell: {variant}")
		indexed[variant] = run
	if set(indexed) != expected:
		raise ValueError("temporal matrix is incomplete or contains unregistered cells")
	reference_ids: set[str] | None = None
	for variant, run in indexed.items():
		results = tuple(run.get("results") or ())
		sample_ids = [str(row.get("sample_id") or "") for row in results]
		if not sample_ids or "" in sample_ids or len(set(sample_ids)) != len(sample_ids):
			raise ValueError(f"temporal matrix has invalid sample ids for {variant}")
		if reference_ids is None:
			reference_ids = set(sample_ids)
		elif set(sample_ids) != reference_ids:
			raise ValueError("temporal matrix variants do not share one sample set")
	return indexed


def _domain_record(run: Mapping[str, Any], domain: str) -> Mapping[str, Any]:
	record = dict(run.get("domains") or {}).get(domain)
	if not isinstance(record, Mapping):
		raise ValueError(f"atomic run has no record for domain {domain}")
	return record


def _mapping_field(
	record: Mapping[str, Any],
	field: str,
	*,
	label: str,
) -> Mapping[str, Any]:
	value = record.get(field)
	if not isinstance(value, Mapping):
		raise ValueError(f"{label} has no {field}")
	return value


def _execution_metrics(
	domain_record: Mapping[str, Any],
	*,
	domain: str,
) -> Mapping[str, Any]:
	execution = _mapping_field(
		domain_record,
		"execution_metrics",
		label=f"domain {domain}",
	)
	test_count = int(execution.get("test_count") or 0)
	valid_trace_count = int(execution.get("valid_trace_count") or 0)
	if test_count <= 0:
		raise ValueError(f"domain {domain} has no held-out tests")
	if valid_trace_count < 0 or valid_trace_count > test_count:
		raise ValueError(f"domain {domain} has invalid valid-trace coverage")
	return execution


def _domain_coverage(run: Mapping[str, Any], domain: str) -> float:
	execution = _execution_metrics(_domain_record(run, domain), domain=domain)
	return 100.0 * int(execution["valid_trace_count"]) / int(execution["test_count"])


def _temporal_result_is_valid(record: Mapping[str, Any]) -> bool:
	if record.get("success") is not True:
		return False
	if str(record.get("status") or "") != "success":
		raise ValueError("successful temporal query has no successful final status")
	if str(record.get("jason_status") or "") != "success":
		raise ValueError("successful temporal query has no Jason success marker")
	validation = record.get("execution_validation")
	if not isinstance(validation, Mapping):
		raise ValueError("successful temporal query has no execution validation")
	required = (
		"success",
		"replay_valid",
		"val_attempted",
		"val_success",
		"gold_accepted",
		"prediction_accepted",
	)
	if not all(validation.get(key) is True for key in required):
		raise ValueError("successful temporal query lacks an end-to-end success oracle")
	return True


def _render_five_seed_figure(dataset: Mapping[str, Any]) -> bytes:
	rc_parameters = {
		"font.family": "DejaVu Sans",
		"font.size": 6.0,
		"font.weight": "normal",
		"axes.titlesize": 6.8,
		"axes.titleweight": "normal",
		"axes.labelsize": 6.0,
		"axes.labelweight": "normal",
		"xtick.labelsize": 5.4,
		"ytick.labelsize": 5.4,
		"legend.fontsize": 5.2,
		"axes.edgecolor": COLORS["gray"],
		"axes.linewidth": 0.5,
		"text.color": COLORS["text"],
		"axes.labelcolor": COLORS["text"],
		"xtick.color": COLORS["text"],
		"ytick.color": COLORS["text"],
		"pdf.fonttype": 42,
		"ps.fonttype": 42,
		"savefig.transparent": False,
	}
	with matplotlib.rc_context(rc_parameters):
		figure, axes = plt.subplots(
			1,
			2,
			figsize=(FIGURE_WIDTH_INCHES, FIGURE_HEIGHT_INCHES),
			gridspec_kw={"width_ratios": (1.05, 1.35)},
			facecolor="white",
		)
		coverage_axis, runtime_axis = axes
		figure.subplots_adjust(
			left=0.16,
			right=0.985,
			top=0.925,
			bottom=0.16,
			wspace=0.36,
		)
		_plot_five_seed_domain_coverage(coverage_axis, dataset)
		_plot_five_seed_runtime_groups(runtime_axis, dataset)
		buffer = io.BytesIO()
		fixed_date = datetime(2000, 1, 1, tzinfo=timezone.utc)
		figure.savefig(
			buffer,
			format="pdf",
			metadata={
				"Title": "GP2PL five-seed held-out evaluation",
				"Author": "Anonymous",
				"Creator": "GP2PL Matplotlib figure generator",
				"CreationDate": fixed_date,
				"ModDate": fixed_date,
			},
		)
		plt.close(figure)
	return buffer.getvalue()


def _plot_five_seed_domain_coverage(axis: Any, dataset: Mapping[str, Any]) -> None:
	coverage = _mapping_field(dataset, "domain_coverage", label="figure dataset")
	seed_jitter = (-0.08, -0.04, 0.0, 0.04, 0.08)
	for domain_index, domain in enumerate(DOMAIN_ORDER):
		y_value = len(DOMAIN_ORDER) - 1 - domain_index
		values = [float(value) for value in coverage[domain]]
		for seed_index, value in enumerate(values):
			axis.scatter(
				value,
				y_value + seed_jitter[seed_index],
				s=6.0,
				color=COLORS["blue"],
				alpha=0.28,
				edgecolors="none",
				zorder=2,
			)
		mean_value = statistics.mean(values)
		standard_deviation = statistics.stdev(values)
		axis.errorbar(
			mean_value,
			y_value,
			xerr=standard_deviation,
			fmt="D",
			markersize=3.2,
			color=COLORS["blue"],
			markerfacecolor=COLORS["blue"],
			markeredgecolor="white",
			markeredgewidth=0.35,
			elinewidth=0.65,
			capsize=1.4,
			zorder=4,
		)
		if standard_deviation > 0.0:
			axis.text(
				mean_value - 2.0,
				y_value + 0.16,
				f"{mean_value:.1f}",
				ha="right",
				va="bottom",
				fontsize=5.0,
				color=COLORS["text"],
			)
	for boundary_after in (7, 11):
		boundary_y = len(DOMAIN_ORDER) - 1 - boundary_after - 0.5
		axis.axhline(boundary_y, color=COLORS["light_gray"], linewidth=0.55)
	axis.axvline(100.0, color=COLORS["gray"], linewidth=0.55, linestyle="--")
	axis.set_xlim(0.0, 102.0)
	axis.set_xticks((0, 25, 50, 75, 100))
	axis.set_yticks(
		list(reversed(range(len(DOMAIN_ORDER)))),
		labels=DOMAIN_ORDER,
	)
	axis.set_ylim(-0.8, len(DOMAIN_ORDER) - 0.35)
	axis.set_xlabel("Jason + VAL coverage (%)", labelpad=2.0)
	axis.set_title("(a) Five-seed held-out coverage", loc="left", pad=2.5)
	axis.grid(axis="x", color="#E8E8E8", linewidth=0.45)
	axis.set_axisbelow(True)
	_style_axis(axis)


def _plot_five_seed_runtime_groups(axis: Any, dataset: Mapping[str, Any]) -> None:
	curves = _mapping_field(dataset, "group_curves", label="figure dataset")
	marker_seconds = (1.0, 10.0, 100.0, 1800.0)
	legend_handles = []
	for group_key, group_label, _domains in BENCHMARK_GROUPS:
		curve = _mapping_field(curves, group_key, label=f"group {group_key}")
		color, marker = GROUP_STYLES[group_key]
		x_values = tuple(float(value) for value in curve["x_seconds"])
		mean_values = tuple(float(value) for value in curve["mean_percent"])
		minimum_values = tuple(float(value) for value in curve["minimum_percent"])
		maximum_values = tuple(float(value) for value in curve["maximum_percent"])
		axis.fill_between(
			x_values,
			minimum_values,
			maximum_values,
			step="post",
			color=color,
			alpha=0.1,
			linewidth=0.0,
		)
		axis.step(
			x_values,
			mean_values,
			where="post",
			color=color,
			linewidth=1.15,
		)
		marker_values = _step_values_at(x_values, mean_values, marker_seconds)
		axis.plot(
			marker_seconds,
			marker_values,
			linestyle="none",
			marker=marker,
			markersize=2.8,
			color=color,
			markeredgecolor="white",
			markeredgewidth=0.3,
		)
		legend_handles.append(
			Line2D(
				[],
				[],
				color=color,
				marker=marker,
				markersize=2.8,
				linewidth=1.15,
				label=group_label,
			),
		)
	axis.axvline(
		REGISTERED_TIMEOUT_SECONDS,
		color=COLORS["gray"],
		linewidth=0.55,
		linestyle="--",
	)
	axis.set_xscale("log")
	axis.set_xlim(0.5, 2000.0)
	axis.set_ylim(-2.0, 102.0)
	axis.set_yticks((0, 25, 50, 75, 100))
	axis.xaxis.set_major_locator(FixedLocator((0.5, 1.0, 10.0, 100.0, 1800.0)))
	axis.xaxis.set_major_formatter(FuncFormatter(lambda value, _position: f"{value:g}"))
	axis.set_xlabel("Jason execution time (s, log scale)", labelpad=2.0)
	axis.set_ylabel("VAL-valid cases solved (%)")
	axis.set_title(
		"(b) Time-to-valid-trace by benchmark group",
		loc="left",
		pad=2.5,
	)
	axis.grid(which="major", color="#E8E8E8", linewidth=0.45)
	axis.set_axisbelow(True)
	_style_axis(axis)
	axis.legend(
		handles=legend_handles,
		loc="lower right",
		bbox_to_anchor=(0.955, 0.015),
		frameon=False,
		ncol=1,
		borderaxespad=0.15,
		handlelength=1.6,
		handletextpad=0.35,
		labelspacing=0.28,
	)


def _render_empirical_figure(dataset: Mapping[str, Any]) -> bytes:
	rc_parameters = {
		"font.family": "DejaVu Sans",
		"font.size": 6.0,
		"font.weight": "normal",
		"axes.titlesize": 6.8,
		"axes.titleweight": "normal",
		"axes.labelsize": 6.0,
		"axes.labelweight": "normal",
		"xtick.labelsize": 5.4,
		"ytick.labelsize": 5.4,
		"legend.fontsize": 5.0,
		"axes.edgecolor": COLORS["gray"],
		"axes.linewidth": 0.5,
		"text.color": COLORS["text"],
		"axes.labelcolor": COLORS["text"],
		"xtick.color": COLORS["text"],
		"ytick.color": COLORS["text"],
		"pdf.fonttype": 42,
		"ps.fonttype": 42,
		"savefig.transparent": False,
	}
	with matplotlib.rc_context(rc_parameters):
		figure = plt.figure(
			figsize=(FIGURE_WIDTH_INCHES, FIGURE_HEIGHT_INCHES),
			facecolor="white",
		)
		grid = figure.add_gridspec(
			2,
			2,
			width_ratios=(1.08, 1.0),
			height_ratios=(0.9, 1.1),
		)
		atomic_axis = figure.add_subplot(grid[:, 0])
		tradeoff_axis = figure.add_subplot(grid[0, 1])
		temporal_axis = figure.add_subplot(grid[1, 1])
		figure.subplots_adjust(
			left=0.165,
			right=0.99,
			top=0.935,
			bottom=0.145,
			wspace=0.4,
			hspace=0.64,
		)
		_plot_atomic_coverage(atomic_axis, dataset)
		_plot_atomic_tradeoff(tradeoff_axis, dataset)
		_plot_temporal_curve(temporal_axis, dataset)
		buffer = io.BytesIO()
		fixed_date = datetime(2000, 1, 1, tzinfo=timezone.utc)
		figure.savefig(
			buffer,
			format="pdf",
			metadata={
				"Title": "GP2PL paired atomic and temporal evaluation",
				"Author": "Anonymous",
				"Creator": "GP2PL Matplotlib figure generator",
				"CreationDate": fixed_date,
				"ModDate": fixed_date,
			},
		)
		plt.close(figure)
	return buffer.getvalue()


def _plot_atomic_coverage(axis: Any, dataset: Mapping[str, Any]) -> None:
	coverage = dict(dataset["atomic_domain_coverage"])
	seed_jitter = (-0.035, -0.0175, 0.0, 0.0175, 0.035)
	method_offsets = {"evidence_adapter": 0.11, "full": -0.11}
	method_styles = {
		"evidence_adapter": (COLORS["gray"], "o", "white"),
		"full": (COLORS["blue"], "D", COLORS["blue"]),
	}
	for domain_index, domain in enumerate(DOMAIN_ORDER):
		y_center = len(DOMAIN_ORDER) - 1 - domain_index
		means: dict[str, tuple[float, float]] = {}
		for key in ("evidence_adapter", "full"):
			values = [float(value) for value in coverage[domain][key]]
			color, marker, face_color = method_styles[key]
			y_mean = y_center + method_offsets[key]
			for seed_index, value in enumerate(values):
				axis.scatter(
					value,
					y_mean + seed_jitter[seed_index],
					s=5.5,
					marker=marker,
					facecolors=face_color,
					edgecolors=color,
					linewidths=0.35,
					alpha=0.32,
					zorder=2,
				)
			mean_value = statistics.mean(values)
			standard_deviation = statistics.stdev(values)
			means[key] = (mean_value, y_mean)
			axis.errorbar(
				mean_value,
				y_mean,
				xerr=standard_deviation,
				fmt=marker,
				markersize=3.1,
				markerfacecolor=face_color,
				markeredgecolor=color,
				markeredgewidth=0.6,
				ecolor=color,
				elinewidth=0.65,
				capsize=1.3,
				zorder=4,
			)
		axis.plot(
			[means["evidence_adapter"][0], means["full"][0]],
			[means["evidence_adapter"][1], means["full"][1]],
			color=COLORS["light_gray"],
			linewidth=0.45,
			zorder=1,
		)
	for boundary_after in (7, 11):
		boundary_y = len(DOMAIN_ORDER) - 1 - boundary_after - 0.5
		axis.axhline(boundary_y, color=COLORS["light_gray"], linewidth=0.55)
	axis.axvline(100.0, color=COLORS["gray"], linewidth=0.55, linestyle="--")
	axis.set_xlim(0.0, 101.8)
	axis.set_xticks((0, 25, 50, 75, 100))
	axis.set_yticks(
		list(reversed(range(len(DOMAIN_ORDER)))),
		labels=DOMAIN_ORDER,
	)
	axis.set_ylim(-1.2, len(DOMAIN_ORDER) - 0.45)
	axis.set_xlabel("Jason + VAL coverage (%)", labelpad=2.0)
	axis.set_title("(a) Paired atomic coverage", loc="left", pad=2.5)
	axis.grid(axis="x", color="#E8E8E8", linewidth=0.45)
	axis.set_axisbelow(True)
	_style_axis(axis)
	legend_handles = (
		Line2D(
			[],
			[],
			marker="o",
			markersize=3.1,
			color=COLORS["gray"],
			markerfacecolor="white",
			markeredgewidth=0.6,
			linewidth=0,
			label="Evidence Only",
		),
		Line2D(
			[],
			[],
			marker="D",
			markersize=3.1,
			color=COLORS["blue"],
			markerfacecolor=COLORS["blue"],
			markeredgewidth=0.6,
			linewidth=0,
			label="Full GP2PL",
		),
	)
	axis.legend(
		handles=legend_handles,
		loc="lower left",
		ncol=2,
		frameon=False,
		borderaxespad=0.15,
		handlelength=1.0,
		handletextpad=0.3,
		columnspacing=0.65,
	)


def _plot_atomic_tradeoff(axis: Any, dataset: Mapping[str, Any]) -> None:
	tradeoff = dict(dataset["atomic_tradeoff"])
	for variant, method in ATOMIC_VARIANTS:
		color, marker = ATOMIC_STYLES[variant]
		face_color = "white" if variant == "validated_evidence_adapter" else color
		mean_edge_color = (
			color if variant == "validated_evidence_adapter" else "white"
		)
		points = tuple(tradeoff[variant])
		x_values = [float(point["selected_branch_count"]) for point in points]
		y_values = [float(point["coverage_percent"]) for point in points]
		axis.scatter(
			x_values,
			y_values,
			s=9,
			marker=marker,
			facecolors=face_color,
			edgecolors=color,
			alpha=0.34,
			linewidths=0.3,
			label=method,
			zorder=2,
		)
		x_mean = statistics.mean(x_values)
		y_mean = statistics.mean(y_values)
		x_sd = statistics.stdev(x_values)
		y_sd = statistics.stdev(y_values)
		x_lower = max(0.5, x_mean - x_sd)
		x_upper = x_mean + x_sd
		axis.errorbar(
			x_mean,
			y_mean,
			xerr=((x_mean - x_lower,), (x_upper - x_mean,)),
			yerr=y_sd,
			fmt=marker,
			markersize=3.9,
			markerfacecolor=face_color,
			markeredgecolor=mean_edge_color,
			markeredgewidth=0.45,
			ecolor=color,
			elinewidth=0.65,
			capsize=1.3,
			zorder=4,
		)
	axis.set_xscale("log")
	axis.set_ylim(-2.0, 102.0)
	axis.set_yticks((0, 25, 50, 75, 100))
	axis.set_ylabel("Held-out coverage (%)")
	axis.set_xlabel("Emitted branches (log scale)", labelpad=2.0)
	axis.set_title("(b) Atomic coverage-size tradeoff", loc="left", pad=2.5)
	axis.grid(which="major", color="#E8E8E8", linewidth=0.45)
	axis.set_axisbelow(True)
	_style_axis(axis)
	handles, labels = axis.get_legend_handles_labels()
	legend_order = (0, 2, 1, 3)
	axis.legend(
		handles=[handles[index] for index in legend_order],
		labels=[labels[index] for index in legend_order],
		loc="lower left",
		ncol=2,
		frameon=False,
		borderaxespad=0.12,
		handlelength=1.0,
		handletextpad=0.25,
		columnspacing=0.55,
		labelspacing=0.25,
	)


def _plot_temporal_curve(axis: Any, dataset: Mapping[str, Any]) -> None:
	curves = dict(dataset["temporal_curves"])
	for variant, method in TEMPORAL_VARIANTS:
		color, line_style, marker = TEMPORAL_STYLES[variant]
		curve = dict(curves[variant])
		axis.step(
			curve["x_seconds"],
			curve["solved_percent"],
			where="post",
			color=color,
			linestyle=line_style,
			linewidth=1.05,
			label=method,
		)
		marker_values = _step_values_at(
			curve["x_seconds"],
			curve["solved_percent"],
			TEMPORAL_MARKER_SECONDS,
		)
		axis.plot(
			TEMPORAL_MARKER_SECONDS,
			marker_values,
			linestyle="none",
			marker=marker,
			markersize=2.6,
			markerfacecolor=color,
			markeredgecolor="white",
			markeredgewidth=0.3,
			zorder=3,
		)
	axis.axvline(
		REGISTERED_TIMEOUT_SECONDS,
		color=COLORS["gray"],
		linewidth=0.55,
		linestyle="--",
	)
	axis.set_xscale("log")
	axis.set_xlim(MINIMUM_LOG_SECONDS, 2000.0)
	axis.set_ylim(-2.0, 102.0)
	axis.set_yticks((0, 25, 50, 75, 100))
	axis.xaxis.set_major_locator(
		FixedLocator((0.1, 1.0, 10.0, 100.0, 1800.0)),
	)
	axis.xaxis.set_major_formatter(
		FuncFormatter(lambda value, _position: f"{value:g}"),
	)
	axis.set_ylabel("All queries solved (%)")
	axis.set_xlabel("End-to-end time (s, log scale)", labelpad=2.0)
	axis.set_title("(c) Temporal cumulative coverage", loc="left", pad=2.5)
	axis.grid(which="major", color="#E8E8E8", linewidth=0.45)
	axis.set_axisbelow(True)
	_style_axis(axis)
	legend_handles = tuple(
		Line2D(
			[],
			[],
			color=TEMPORAL_STYLES[variant][0],
			linestyle=TEMPORAL_STYLES[variant][1],
			marker=TEMPORAL_STYLES[variant][2],
			markersize=2.5,
			linewidth=1.05,
			label=method,
		)
		for variant, method in TEMPORAL_VARIANTS
	)
	legend_order = (0, 2, 1, 3)
	axis.legend(
		handles=tuple(legend_handles[index] for index in legend_order),
		loc="lower right",
		ncol=2,
		frameon=False,
		borderaxespad=0.12,
		handlelength=1.7,
		handletextpad=0.3,
		columnspacing=0.65,
		labelspacing=0.25,
	)


def _step_values_at(
	x_values: Sequence[float],
	y_values: Sequence[float],
	checkpoints: Sequence[float],
) -> tuple[float, ...]:
	"""Return right-continuous step values at shared time checkpoints."""

	if len(x_values) != len(y_values) or not x_values:
		raise ValueError("step curve coordinates must be non-empty and aligned")
	return tuple(
		float(y_values[max(0, bisect_right(x_values, checkpoint) - 1)])
		for checkpoint in checkpoints
	)


def _style_axis(axis: Any) -> None:
	"""Apply print-safe academic axis styling without changing plotted data."""

	axis.spines["top"].set_visible(False)
	axis.spines["right"].set_visible(False)
	axis.tick_params(
		axis="both",
		direction="out",
		length=2.2,
		width=0.5,
		pad=1.8,
	)
	axis.tick_params(
		axis="both",
		which="minor",
		length=1.2,
		width=0.35,
	)


def _read_json(path: Path) -> dict[str, Any]:
	with path.open("r", encoding="utf-8") as handle:
		payload = json.load(handle)
	if not isinstance(payload, dict):
		raise ValueError(f"Expected JSON object: {path}")
	return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(
		json.dumps(payload, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)


def _portable_artifact_path(path: Path) -> str:
	"""Return a repository-relative path without exposing a local home directory."""

	resolved_path = path.expanduser().resolve()
	try:
		return resolved_path.relative_to(PROJECT_ROOT).as_posix()
	except ValueError:
		return str(resolved_path)


def _sha256(path: Path) -> str:
	hasher = hashlib.sha256()
	with path.open("rb") as handle:
		for chunk in iter(lambda: handle.read(1024 * 1024), b""):
			hasher.update(chunk)
	return hasher.hexdigest()


def _parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	input_group = parser.add_mutually_exclusive_group(required=True)
	input_group.add_argument("--paired-results", type=Path)
	input_group.add_argument("--five-seed-results", type=Path)
	parser.add_argument(
		"--validation-run-root",
		type=Path,
		default=DEFAULT_VALIDATION_RUN_ROOT,
	)
	parser.add_argument("--output-file", type=Path, default=DEFAULT_OUTPUT_FILE)
	return parser.parse_args()


def main() -> int:
	args = _parse_args()
	try:
		if args.five_seed_results is not None:
			metadata = generate_five_seed_empirical_figure(
				five_seed_results_file=args.five_seed_results,
				validation_run_root=args.validation_run_root,
				output_file=args.output_file,
			)
		else:
			metadata = generate_empirical_figure(
				paired_results_file=args.paired_results,
				output_file=args.output_file,
			)
	except (OSError, TypeError, ValueError) as error:
		print(f"[fail] empirical_figure error={error}", file=sys.stderr)
		return 2
	print(
		f"[ok] empirical_figure output={metadata['output_file']} "
		f"source_sha256={metadata['source_sha256']}",
		flush=True,
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
