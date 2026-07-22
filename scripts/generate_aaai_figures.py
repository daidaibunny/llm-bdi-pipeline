#!/usr/bin/env python3
"""Generate gated GP2PL empirical figures from frozen experiment records."""

from __future__ import annotations

import argparse
from bisect import bisect_right
from datetime import datetime
from datetime import timezone
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
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from matplotlib.ticker import FixedLocator  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402
from matplotlib.ticker import NullLocator  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_FILE = (
	PROJECT_ROOT / "latex_code/aamas_method_paper/figures/fig3_evaluation.png"
)
LEGACY_OUTPUT_FILE = (
	PROJECT_ROOT / "latex_code/aamas_method_paper/figures/fig2_evaluation.pdf"
)
DEFAULT_VALIDATION_RUN_ROOT = PROJECT_ROOT / "artifacts/jason_full_test_runs"
REGISTERED_SEEDS = (0, 1, 2, 3, 4)
REGISTERED_NUM_WORKERS = 6
REGISTERED_FIVE_SEED_VALIDATION_WORKERS = 8
REGISTERED_TIMEOUT_SECONDS = 1800
REGISTERED_JAVA_STACK_SIZE = "64m"
MINIMUM_LOG_SECONDS = 0.1
FIGURE_WIDTH_INCHES = 7.0
FIGURE_HEIGHT_INCHES = 4.25
FROZEN_ABLATION_FIGURE_HEIGHT_INCHES = 17.0 / 6.0
FROZEN_ABLATION_MANUSCRIPT_WIDTH_FRACTION = 2.0 / 3.0
FROZEN_ABLATION_TEXT_POINTS = 10.5
FIGURE_DPI = 600
FIGURE_FONT_FAMILY = "Helvetica"
MINIMUM_FIGURE_TEXT_POINTS = 9.0
FIGURE_COLOR_MODE = "colorblind-safe with redundant encodings"
TEMPORAL_MARKER_SECONDS = (1.0, 10.0, 100.0, 1800.0)
ATOMIC_FOCUS_DOMAIN = "blocksworld-tower"

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
	("action_only_closure", "Direct Producers"),
	("maximal_certified_program", "Maximum Feasible"),
	("full", "Full GP2PL"),
)
TEMPORAL_VARIANTS = (
	("dfa_aware_unprotected", "Unprotected Serialization"),
	("certified_flat", "Certified Flat"),
	("certified_balanced", "Certified Balanced"),
	("completion_boundary_monitor", "Module-Return Monitor"),
)
ATOMIC_FIGURE_LABELS = {
	"validated_evidence_adapter": "Evidence",
	"action_only_closure": "Direct",
	"maximal_certified_program": "Maximum",
	"full": "Full",
}
TEMPORAL_FIGURE_LABELS = {
	"dfa_aware_unprotected": "Unprotected",
	"certified_flat": "Certified flat",
	"certified_balanced": "Certified balanced",
	"completion_boundary_monitor": "Module return",
}

COLORS = {
	"blue": "#0072B2",
	"orange": "#D55E00",
	"green": "#009E73",
	"purple": "#CC79A7",
	"gray": "#666666",
	"light_gray": "#D4D4D4",
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
		"atomic_domain_coverage": atomic_domain_coverage,
		"atomic_tradeoff": atomic_tradeoff,
		"temporal_curves": temporal_curves,
		"timeout_seconds": REGISTERED_TIMEOUT_SECONDS,
	}


def build_frozen_ablation_figure_dataset(
	payload: Mapping[str, Any],
) -> dict[str, Any]:
	"""Validate the frozen paired release and derive all Figure 3 values."""

	_validate_frozen_ablation_gate(payload)
	protocol = _mapping_field(payload, "protocol", label="frozen ablation")
	case_contract = _mapping_field(protocol, "case_contract", label="protocol")
	achievement_contract = _mapping_field(
		case_contract,
		"achievement",
		label="case contract",
	)
	temporal_contract = _mapping_field(
		case_contract,
		"temporal",
		label="case contract",
	)
	atomic_case_count_per_seed = int(achievement_contract["count"])
	temporal_case_count = int(temporal_contract["count"])

	atomic_records = tuple(dict(row) for row in payload["atomic_records"])
	atomic_by_variant = {
		variant: tuple(row for row in atomic_records if row["variant"] == variant)
		for variant, _method in ATOMIC_VARIANTS
	}
	atomic_domain_coverage: dict[str, dict[str, list[float]]] = {}
	for domain in DOMAIN_ORDER:
		atomic_domain_coverage[domain] = {}
		for output_key, variant in (
			("evidence_adapter", "validated_evidence_adapter"),
			("full", "full"),
		):
			values: list[float] = []
			for seed in REGISTERED_SEEDS:
				domain_records = tuple(
					row
					for row in atomic_by_variant[variant]
					if int(row["seed"]) == seed and row["domain"] == domain
				)
				if not domain_records:
					raise ValueError(
						f"atomic record matrix has no {variant} seed {seed} {domain}",
					)
				values.append(
					100.0
					* sum(row["valid"] is True for row in domain_records)
					/ len(domain_records),
				)
			atomic_domain_coverage[domain][output_key] = values

	atomic_summary_by_variant = {
		str(row["variant"]): dict(row) for row in payload["atomic"]
	}
	atomic_seed_rows = tuple(dict(row) for row in payload["atomic_seed_results"])
	atomic_tradeoff_summary: dict[str, dict[str, float]] = {}
	for variant, _method in ATOMIC_VARIANTS:
		summary = atomic_summary_by_variant[variant]
		seed_rows = sorted(
			(row for row in atomic_seed_rows if row["variant"] == variant),
			key=lambda row: int(row["seed"]),
		)
		coverage_values = [
			100.0 * int(row["valid_count"]) / int(row["case_count"])
			for row in seed_rows
		]
		atomic_tradeoff_summary[variant] = {
			"branch_mean": float(summary["mean_branch_count"]),
			"branch_sd": float(summary["sd_branch_count"]),
			"coverage_mean": statistics.mean(coverage_values),
			"coverage_sd": statistics.stdev(coverage_values),
		}

	atomic_domain_variant_coverage: dict[str, dict[str, float]] = {}
	for domain in DOMAIN_ORDER:
		atomic_domain_variant_coverage[domain] = {}
		for variant, _method in ATOMIC_VARIANTS:
			domain_records = tuple(
				row for row in atomic_by_variant[variant] if row["domain"] == domain
			)
			if not domain_records:
				raise ValueError(f"atomic record matrix has no {variant} {domain}")
			atomic_domain_variant_coverage[domain][variant] = (
				100.0
				* sum(row["valid"] is True for row in domain_records)
				/ len(domain_records)
			)
	atomic_affected_domains = [
		domain
		for domain in DOMAIN_ORDER
		if len(
			{
				round(value, 10)
				for value in atomic_domain_variant_coverage[domain].values()
			},
		)
		> 1
	]
	atomic_unchanged_domains = [
		domain for domain in DOMAIN_ORDER if domain not in atomic_affected_domains
	]
	atomic_unchanged_variant_coverage: dict[str, float] = {}
	for variant, _method in ATOMIC_VARIANTS:
		unchanged_records = tuple(
			row
			for row in atomic_by_variant[variant]
			if row["domain"] in atomic_unchanged_domains
		)
		if unchanged_records:
			atomic_unchanged_variant_coverage[variant] = (
				100.0
				* sum(row["valid"] is True for row in unchanged_records)
				/ len(unchanged_records)
			)

	focus_records = tuple(
		row for row in atomic_records if row["domain"] == ATOMIC_FOCUS_DOMAIN
	)
	if not focus_records:
		raise ValueError(f"atomic focus domain is absent: {ATOMIC_FOCUS_DOMAIN}")
	focus_horizon_seconds = max(
		MINIMUM_LOG_SECONDS,
		max(float(row["duration_seconds"]) for row in focus_records),
	)
	atomic_focus_curves: dict[str, dict[str, Any]] = {}
	for variant, _method in ATOMIC_VARIANTS:
		variant_records = tuple(
			row for row in focus_records if row["variant"] == variant
		)
		x_values, y_values = _cumulative_frozen_valid_fraction(
			variant_records,
			timeout_seconds=focus_horizon_seconds,
		)
		atomic_focus_curves[variant] = {
			"x_seconds": x_values,
			"solved_percent": y_values,
			"sample_count": len(variant_records),
			"solved_count": sum(row["valid"] is True for row in variant_records),
			"final_percent": y_values[-1],
		}

	temporal_records = tuple(dict(row) for row in payload["temporal_records"])
	temporal_curves: dict[str, dict[str, Any]] = {}
	for variant, _method in TEMPORAL_VARIANTS:
		variant_records = tuple(
			row for row in temporal_records if row["variant"] == variant
		)
		x_values, y_values = _cumulative_frozen_valid_fraction(
			variant_records,
			timeout_seconds=REGISTERED_TIMEOUT_SECONDS,
		)
		temporal_curves[variant] = {
			"x_seconds": x_values,
			"solved_percent": y_values,
			"sample_count": len(variant_records),
			"solved_count": sum(row["valid"] is True for row in variant_records),
			"final_percent": y_values[-1],
		}

	return {
		"atomic_domain_coverage": atomic_domain_coverage,
		"atomic_domain_variant_coverage": atomic_domain_variant_coverage,
		"atomic_affected_domains": atomic_affected_domains,
		"atomic_unchanged_domains": atomic_unchanged_domains,
		"atomic_unchanged_variant_coverage": atomic_unchanged_variant_coverage,
		"atomic_focus_domain": ATOMIC_FOCUS_DOMAIN,
		"atomic_focus_curves": atomic_focus_curves,
		"atomic_focus_horizon_seconds": focus_horizon_seconds,
		"atomic_tradeoff_summary": atomic_tradeoff_summary,
		"temporal_curves": temporal_curves,
		"atomic_case_count": atomic_case_count_per_seed * len(REGISTERED_SEEDS),
		"temporal_case_count": temporal_case_count,
		"timeout_seconds": REGISTERED_TIMEOUT_SECONDS,
	}


def _validate_frozen_ablation_gate(payload: Mapping[str, Any]) -> None:
	if payload.get("artifact_kind") != "gp2pl_paired_ablation_results":
		raise ValueError("unsupported frozen ablation result file")
	if int(payload.get("schema_version") or 0) != 1:
		raise ValueError("unsupported frozen ablation schema")
	protocol = _mapping_field(payload, "protocol", label="frozen ablation")
	if tuple(protocol.get("registered_seeds") or ()) != REGISTERED_SEEDS:
		raise ValueError("frozen ablation must contain registered seeds 0--4")
	if int(protocol.get("num_workers") or 0) != REGISTERED_NUM_WORKERS:
		raise ValueError("frozen ablation worker protocol disagrees")
	if int(protocol.get("timeout_seconds") or 0) != REGISTERED_TIMEOUT_SECONDS:
		raise ValueError("frozen ablation timeout protocol disagrees")
	if protocol.get("jason_java_stack_size") != REGISTERED_JAVA_STACK_SIZE:
		raise ValueError("frozen ablation Java stack protocol disagrees")
	atomic_pairing = _mapping_field(protocol, "atomic_pairing", label="protocol")
	if atomic_pairing.get("paired") is not True:
		raise ValueError("frozen ablation atomic pairing is not certified")
	if int(atomic_pairing.get("seed_domain_group_count") or 0) != (
		len(REGISTERED_SEEDS) * len(DOMAIN_ORDER)
	):
		raise ValueError("frozen ablation atomic pairing group count disagrees")
	temporal_pairing = _mapping_field(
		protocol,
		"temporal_pairing",
		label="protocol",
	)
	if temporal_pairing.get("paired") is not True:
		raise ValueError("frozen ablation temporal pairing is not certified")
	if int(temporal_pairing.get("domain_count") or 0) != len(DOMAIN_ORDER):
		raise ValueError("frozen ablation temporal domain count disagrees")
	case_contract = _mapping_field(protocol, "case_contract", label="protocol")
	achievement_contract = _mapping_field(
		case_contract,
		"achievement",
		label="case contract",
	)
	temporal_contract = _mapping_field(
		case_contract,
		"temporal",
		label="case contract",
	)
	atomic_case_count_per_seed = int(achievement_contract.get("count") or 0)
	temporal_case_count = int(temporal_contract.get("count") or 0)
	if atomic_case_count_per_seed <= 0 or temporal_case_count <= 0:
		raise ValueError("frozen ablation case contracts are empty")
	atomic_summaries = tuple(dict(row) for row in payload.get("atomic") or ())
	if {row.get("variant") for row in atomic_summaries} != {
		variant for variant, _method in ATOMIC_VARIANTS
	}:
		raise ValueError("frozen ablation atomic summary variants disagree")
	atomic_records = tuple(dict(row) for row in payload.get("atomic_records") or ())
	expected_atomic_record_count = (
		atomic_case_count_per_seed * len(REGISTERED_SEEDS) * len(ATOMIC_VARIANTS)
	)
	if len(atomic_records) != expected_atomic_record_count:
		raise ValueError("frozen ablation atomic record matrix is incomplete")
	_atomic_record_matrix(
		atomic_records,
		atomic_summaries=atomic_summaries,
		atomic_seed_results=tuple(payload.get("atomic_seed_results") or ()),
		case_count_per_seed=atomic_case_count_per_seed,
	)

	temporal_summaries = tuple(dict(row) for row in payload.get("temporal") or ())
	if {row.get("variant") for row in temporal_summaries} != {
		variant for variant, _method in TEMPORAL_VARIANTS
	}:
		raise ValueError("frozen ablation temporal summary variants disagree")
	temporal_records = tuple(
		dict(row) for row in payload.get("temporal_records") or ()
	)
	if len(temporal_records) != temporal_case_count * len(TEMPORAL_VARIANTS):
		raise ValueError("frozen ablation temporal record matrix is incomplete")
	_temporal_record_matrix(
		temporal_records,
		temporal_summaries=temporal_summaries,
		case_count=temporal_case_count,
	)
	if int(temporal_pairing.get("sample_count") or 0) != temporal_case_count:
		raise ValueError("frozen ablation temporal pairing sample count disagrees")


def _atomic_record_matrix(
	records: Sequence[Mapping[str, Any]],
	*,
	atomic_summaries: Sequence[Mapping[str, Any]],
	atomic_seed_results: Sequence[Mapping[str, Any]],
	case_count_per_seed: int,
) -> None:
	by_variant: dict[str, dict[tuple[int, str], Mapping[str, Any]]] = {}
	for variant, _method in ATOMIC_VARIANTS:
		variant_rows = [row for row in records if row.get("variant") == variant]
		index: dict[tuple[int, str], Mapping[str, Any]] = {}
		for row in variant_rows:
			seed = int(row.get("seed", -1))
			case_id = str(row.get("case_id") or "")
			key = (seed, case_id)
			if seed not in REGISTERED_SEEDS or not case_id or key in index:
				raise ValueError(f"invalid atomic record key for {variant}: {key}")
			if row.get("domain") not in DOMAIN_ORDER:
				raise ValueError(f"atomic record has unknown domain: {row.get('domain')}")
			expected_valid = (
				row.get("status") == "success"
				and row.get("jason_success") is True
				and row.get("val_attempted") is True
				and row.get("val_success") is True
			)
			if (row.get("valid") is True) != expected_valid:
				raise ValueError(f"atomic validity oracle disagrees for {variant} {key}")
			index[key] = row
		by_variant[variant] = index
	reference_variant = ATOMIC_VARIANTS[0][0]
	reference = by_variant[reference_variant]
	for variant, index in by_variant.items():
		if set(index) != set(reference):
			raise ValueError(f"atomic record matrix differs for {variant}")
		for key, row in index.items():
			reference_row = reference[key]
			if row.get("domain") != reference_row.get("domain"):
				raise ValueError(f"atomic paired input differs for {variant} {key}")
	for seed in REGISTERED_SEEDS:
		if sum(key[0] == seed for key in reference) != case_count_per_seed:
			raise ValueError(f"atomic record matrix seed {seed} count disagrees")

	seed_index: dict[tuple[int, str], Mapping[str, Any]] = {}
	for raw_row in atomic_seed_results:
		row = dict(raw_row)
		key = (int(row.get("seed", -1)), str(row.get("variant") or ""))
		if key in seed_index:
			raise ValueError(f"duplicate atomic seed summary: {key}")
		seed_index[key] = row
	expected_seed_keys = {
		(seed, variant)
		for seed in REGISTERED_SEEDS
		for variant, _method in ATOMIC_VARIANTS
	}
	if set(seed_index) != expected_seed_keys:
		raise ValueError("atomic seed summary matrix is incomplete")
	for key, row in seed_index.items():
		seed, variant = key
		variant_rows = [
			record for record_key, record in by_variant[variant].items() if record_key[0] == seed
		]
		if int(row.get("case_count") or 0) != len(variant_rows):
			raise ValueError(f"atomic seed summary case count disagrees: {key}")
		if int(row.get("valid_count") or 0) != sum(
			record.get("valid") is True for record in variant_rows
		):
			raise ValueError(f"atomic seed summary validity disagrees: {key}")

	summary_index = {str(row["variant"]): row for row in atomic_summaries}
	for variant, index in by_variant.items():
		summary = summary_index[variant]
		if int(summary.get("test_count") or 0) != len(index):
			raise ValueError(f"atomic summary case count disagrees for {variant}")
		if int(summary.get("valid_trace_count") or 0) != sum(
			row.get("valid") is True for row in index.values()
		):
			raise ValueError(f"atomic summary validity disagrees for {variant}")


def _temporal_record_matrix(
	records: Sequence[Mapping[str, Any]],
	*,
	temporal_summaries: Sequence[Mapping[str, Any]],
	case_count: int,
) -> None:
	by_variant: dict[str, dict[str, Mapping[str, Any]]] = {}
	for variant, _method in TEMPORAL_VARIANTS:
		index: dict[str, Mapping[str, Any]] = {}
		for row in (row for row in records if row.get("variant") == variant):
			sample_id = str(row.get("sample_id") or "")
			if not sample_id or sample_id in index:
				raise ValueError(f"invalid temporal record key for {variant}: {sample_id}")
			if row.get("domain") not in DOMAIN_ORDER:
				raise ValueError(
					f"temporal record has unknown domain: {row.get('domain')}",
				)
			expected_valid = (
				row.get("status") == "success"
				and row.get("jason_status") == "success"
				and row.get("val_attempted") is True
				and row.get("val_success") is True
				and row.get("gold_accepted") is True
				and row.get("prediction_accepted") is True
			)
			if (row.get("valid") is True) != expected_valid:
				raise ValueError(
					f"temporal validity oracle disagrees for {variant} {sample_id}",
				)
			if expected_valid:
				duration = float(row.get("duration_seconds") or -1.0)
				if duration < 0.0 or duration > REGISTERED_TIMEOUT_SECONDS:
					raise ValueError(
						f"valid temporal duration is outside deadline: {variant} {sample_id}",
					)
			index[sample_id] = row
		by_variant[variant] = index
	reference_variant = TEMPORAL_VARIANTS[0][0]
	reference = by_variant[reference_variant]
	if len(reference) != case_count:
		raise ValueError("temporal record matrix case count disagrees")
	for variant, index in by_variant.items():
		if set(index) != set(reference):
			raise ValueError(f"temporal record matrix differs for {variant}")
		for sample_id, row in index.items():
			reference_row = reference[sample_id]
			for field in ("domain", "profile"):
				if row.get(field) != reference_row.get(field):
					raise ValueError(
						f"temporal paired input differs for {variant} {sample_id}: {field}",
					)
	summary_index = {str(row["variant"]): row for row in temporal_summaries}
	for variant, index in by_variant.items():
		summary = summary_index[variant]
		if int(summary.get("test_count") or 0) != len(index):
			raise ValueError(f"temporal summary case count disagrees for {variant}")
		if int(summary.get("valid_trace_count") or 0) != sum(
			row.get("valid") is True for row in index.values()
		):
			raise ValueError(f"temporal summary validity disagrees for {variant}")


def _cumulative_frozen_valid_fraction(
	records: Sequence[Mapping[str, Any]],
	*,
	timeout_seconds: float | int,
) -> tuple[list[float], list[float]]:
	if not records:
		raise ValueError("frozen temporal matrix has no query records")
	cutoff = float(timeout_seconds)
	solved_times = sorted(
		max(MINIMUM_LOG_SECONDS, float(record["duration_seconds"]))
		for record in records
		if record.get("valid") is True
	)
	x_values = [MINIMUM_LOG_SECONDS]
	y_values = [0.0]
	for solved_count, duration in enumerate(solved_times, start=1):
		x_values.append(duration)
		y_values.append(100.0 * solved_count / len(records))
	x_values.append(cutoff)
	y_values.append(100.0 * len(solved_times) / len(records))
	return x_values, y_values


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
) -> dict[str, Any]:
	"""Validate frozen five-seed outcomes and derive coverage and runtime curves."""

	_validate_five_seed_result_gate(payload)
	protocol = _mapping_field(payload, "protocol", label="five-seed result")
	seeds = tuple(int(seed) for seed in protocol["seeds"])

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

	case_records = tuple(dict(row) for row in payload.get("case_records") or ())
	validated_rows: dict[int, list[dict[str, Any]]] = {}
	pooled_success_count = 0
	pooled_evaluation_count = 0
	for seed_index, seed in enumerate(seeds):
		seed_result = seed_result_rows[seed]
		rows: list[dict[str, Any]] = []
		domain_success = {domain: 0 for domain in DOMAIN_ORDER}
		domain_total = {domain: 0 for domain in DOMAIN_ORDER}
		seen_cases: set[tuple[str, str]] = set()
		for raw_record in (row for row in case_records if int(row.get("seed", -1)) == seed):
			domain = str(raw_record.get("domain") or "")
			test_id = str(raw_record.get("test_id") or "")
			case_key = (domain, test_id)
			if domain not in domain_total or not test_id or case_key in seen_cases:
				raise ValueError(f"seed {seed} has an invalid case identifier {case_key}")
			seen_cases.add(case_key)
			domain_total[domain] += 1
			success = raw_record.get("valid") is True
			if success:
				if raw_record.get("status") != "success" or raw_record.get(
					"val_success",
				) is not True:
					raise ValueError(
						f"seed {seed} case {case_key} lacks Jason and VAL acceptance",
					)
				duration = float(raw_record.get("jason_run_seconds") or 0.0)
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
					"test_id": test_id,
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

	observed_worker_count = int(protocol.get("validation_workers") or 0)
	if observed_worker_count <= 0:
		raise ValueError("five-seed result has no positive Jason worker count")

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
		raise ValueError("unsupported five-seed result file")
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
	if int(protocol.get("validation_workers") or 0) != (
		REGISTERED_FIVE_SEED_VALIDATION_WORKERS
	):
		raise ValueError("five-seed result has an unexpected validation worker count")
	if not payload.get("case_records"):
		raise ValueError("five-seed result has no case-level outcomes")


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
		"font_family": FIGURE_FONT_FAMILY,
		"minimum_text_size_points": MINIMUM_FIGURE_TEXT_POINTS,
		"color_mode": FIGURE_COLOR_MODE,
	}
	_write_json(output_path.with_suffix(".metadata.json"), metadata)
	_write_json(
		diagnostic_path,
		{
			"artifact_kind": "gp2pl_empirical_figure_diagnostic",
			"success": True,
		},
	)
	return metadata


def generate_frozen_ablation_figure(
	*,
	ablation_results_file: str | Path,
	output_file: str | Path,
) -> dict[str, Any]:
	"""Render the canonical high-resolution Figure 3 from the frozen release."""

	input_path = Path(ablation_results_file).expanduser().resolve()
	output_path = Path(output_file).expanduser().resolve()
	diagnostic_path = output_path.with_suffix(".diagnostic.json")
	try:
		payload = _read_json(input_path)
		dataset = build_frozen_ablation_figure_dataset(payload)
	except (OSError, TypeError, ValueError) as error:
		_write_json(
			diagnostic_path,
			{
				"artifact_kind": "gp2pl_ablation_figure_diagnostic",
				"success": False,
				"error": str(error),
			},
		)
		raise

	png_bytes = _render_frozen_ablation_figure(dataset)
	output_path.parent.mkdir(parents=True, exist_ok=True)
	output_path.write_bytes(png_bytes)
	pixel_width = round(FIGURE_WIDTH_INCHES * FIGURE_DPI)
	pixel_height = round(FROZEN_ABLATION_FIGURE_HEIGHT_INCHES * FIGURE_DPI)
	metadata = {
		"schema_version": 1,
		"artifact_kind": "gp2pl_ablation_empirical_figure",
		"atomic_seed_count": len(REGISTERED_SEEDS),
		"atomic_domain_count": len(DOMAIN_ORDER),
		"atomic_variant_count": len(ATOMIC_VARIANTS),
		"atomic_case_count": int(dataset["atomic_case_count"]),
		"atomic_affected_domain_count": len(dataset["atomic_affected_domains"]),
		"atomic_unchanged_domain_count": len(dataset["atomic_unchanged_domains"]),
		"atomic_focus_domain": str(dataset["atomic_focus_domain"]),
		"atomic_focus_case_count": int(
			next(iter(dict(dataset["atomic_focus_curves"]).values()))["sample_count"],
		),
		"temporal_variant_count": len(TEMPORAL_VARIANTS),
		"temporal_case_count": int(dataset["temporal_case_count"]),
		"timeout_seconds": REGISTERED_TIMEOUT_SECONDS,
		"figure_width_inches": FIGURE_WIDTH_INCHES,
		"figure_height_inches": FROZEN_ABLATION_FIGURE_HEIGHT_INCHES,
		"manuscript_width_fraction": FROZEN_ABLATION_MANUSCRIPT_WIDTH_FRACTION,
		"pixel_width": pixel_width,
		"pixel_height": pixel_height,
		"dpi": FIGURE_DPI,
		"font_family": FIGURE_FONT_FAMILY,
		"minimum_text_size_points": FROZEN_ABLATION_TEXT_POINTS,
		"effective_minimum_text_size_points": (
			FROZEN_ABLATION_TEXT_POINTS
			* FROZEN_ABLATION_MANUSCRIPT_WIDTH_FRACTION
		),
		"color_mode": FIGURE_COLOR_MODE,
		"panel_contract": (
			"affected-domain atomic coverage matrix; full paired Tower atomic "
			"time-to-valid coverage; all-query temporal time-to-valid coverage"
		),
	}
	_write_json(output_path.with_suffix(".metadata.json"), metadata)
	_write_json(
		diagnostic_path,
		{
			"artifact_kind": "gp2pl_ablation_figure_diagnostic",
			"success": True,
		},
	)
	return metadata


def generate_five_seed_empirical_figure(
	*,
	five_seed_results_file: str | Path,
	output_file: str | Path,
) -> dict[str, Any]:
	"""Render the main five-seed coverage figure from frozen outcomes."""

	input_path = Path(five_seed_results_file).expanduser().resolve()
	output_path = Path(output_file).expanduser().resolve()
	diagnostic_path = output_path.with_suffix(".diagnostic.json")
	try:
		payload = _read_json(input_path)
		dataset = build_five_seed_figure_dataset(payload)
	except (OSError, TypeError, ValueError) as error:
		_write_json(
			diagnostic_path,
			{
				"artifact_kind": "gp2pl_five_seed_figure_diagnostic",
				"success": False,
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
		"runtime_measure": "case_records.jason_run_seconds",
		"figure_width_inches": FIGURE_WIDTH_INCHES,
		"figure_height_inches": FIGURE_HEIGHT_INCHES,
		"font_family": FIGURE_FONT_FAMILY,
		"minimum_text_size_points": MINIMUM_FIGURE_TEXT_POINTS,
		"color_mode": FIGURE_COLOR_MODE,
	}
	_write_json(output_path.with_suffix(".metadata.json"), metadata)
	_write_json(
		diagnostic_path,
		{
			"artifact_kind": "gp2pl_five_seed_figure_diagnostic",
			"success": True,
		},
	)
	return metadata


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
	_validate_seed_manifests(payload)
	for run in tuple(payload.get("atomic_runs") or ()):
		summary = _mapping_field(run, "summary", label="atomic child run")
		_validate_execution_protocol(
			_mapping_field(summary, "settings", label="atomic child run"),
			label="atomic child run",
			timeout_key="timeout_seconds",
		)
	for run in tuple(payload.get("temporal_runs") or ()):
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
		"font.family": FIGURE_FONT_FAMILY,
		"font.size": MINIMUM_FIGURE_TEXT_POINTS,
		"font.weight": "normal",
		"axes.titlesize": MINIMUM_FIGURE_TEXT_POINTS,
		"axes.titleweight": "normal",
		"axes.labelsize": MINIMUM_FIGURE_TEXT_POINTS,
		"axes.labelweight": "normal",
		"xtick.labelsize": MINIMUM_FIGURE_TEXT_POINTS,
		"ytick.labelsize": MINIMUM_FIGURE_TEXT_POINTS,
		"legend.fontsize": MINIMUM_FIGURE_TEXT_POINTS,
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
			left=0.19,
			right=0.985,
			top=0.94,
			bottom=0.14,
			wspace=0.46,
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
				fontsize=MINIMUM_FIGURE_TEXT_POINTS,
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
	axis.grid(axis="x", color="0.91", linewidth=0.45)
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
	axis.grid(which="major", color="0.91", linewidth=0.45)
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


def _render_frozen_ablation_figure(dataset: Mapping[str, Any]) -> bytes:
	rc_parameters = {
		"font.family": FIGURE_FONT_FAMILY,
		"font.size": FROZEN_ABLATION_TEXT_POINTS,
		"font.weight": "normal",
		"axes.titlesize": FROZEN_ABLATION_TEXT_POINTS,
		"axes.titleweight": "normal",
		"axes.labelsize": FROZEN_ABLATION_TEXT_POINTS,
		"axes.labelweight": "normal",
		"xtick.labelsize": FROZEN_ABLATION_TEXT_POINTS,
		"ytick.labelsize": FROZEN_ABLATION_TEXT_POINTS,
		"legend.fontsize": FROZEN_ABLATION_TEXT_POINTS,
		"axes.edgecolor": COLORS["gray"],
		"axes.linewidth": 0.5,
		"text.color": COLORS["text"],
		"axes.labelcolor": COLORS["text"],
		"xtick.color": COLORS["text"],
		"ytick.color": COLORS["text"],
		"savefig.transparent": False,
	}
	with matplotlib.rc_context(rc_parameters):
		figure = plt.figure(
			figsize=(FIGURE_WIDTH_INCHES, FROZEN_ABLATION_FIGURE_HEIGHT_INCHES),
			facecolor="white",
		)
		grid = figure.add_gridspec(1, 3, width_ratios=(1.24, 1.0, 1.12))
		atomic_axis = figure.add_subplot(grid[0, 0])
		focus_axis = figure.add_subplot(grid[0, 1])
		temporal_axis = figure.add_subplot(grid[0, 2])
		figure.subplots_adjust(
			left=0.15,
			right=0.965,
			top=0.915,
			bottom=0.145,
			wspace=0.42,
		)
		_plot_atomic_domain_matrix(atomic_axis, dataset)
		_plot_atomic_focus_curve(focus_axis, dataset)
		_plot_temporal_curve(temporal_axis, dataset)
		buffer = io.BytesIO()
		figure.savefig(
			buffer,
			format="png",
			dpi=FIGURE_DPI,
			facecolor="white",
			metadata={
				"Title": "GP2PL paired atomic and temporal ablations",
				"Author": "Anonymous",
				"Software": "GP2PL Matplotlib figure generator",
			},
		)
		plt.close(figure)
	return buffer.getvalue()


def _plot_atomic_domain_matrix(axis: Any, dataset: Mapping[str, Any]) -> None:
	coverage = dict(dataset["atomic_domain_variant_coverage"])
	affected_domains = list(dataset["atomic_affected_domains"])
	unchanged_domains = list(dataset["atomic_unchanged_domains"])
	unchanged_coverage = dict(dataset["atomic_unchanged_variant_coverage"])
	row_keys: list[str] = list(affected_domains)
	row_labels = [_short_domain_label(domain) for domain in affected_domains]
	if unchanged_domains:
		row_keys.append("__unchanged__")
		row_labels.append(f"Other {len(unchanged_domains)}")
	matrix: list[list[float]] = []
	for row_key in row_keys:
		matrix.append(
			[
				float(
					unchanged_coverage[variant]
					if row_key == "__unchanged__"
					else coverage[row_key][variant],
				)
				for variant, _method in ATOMIC_VARIANTS
			],
		)
	color_map = LinearSegmentedColormap.from_list(
		"gp2pl_coverage",
		("#FFFFFF", "#D6EAF5", "#6BAED6", COLORS["blue"]),
	)
	axis.imshow(matrix, cmap=color_map, vmin=0.0, vmax=100.0, aspect="auto")
	for row_index, values in enumerate(matrix):
		for column_index, value in enumerate(values):
			label = f"{value:.0f}" if abs(value - round(value)) < 0.05 else f"{value:.1f}"
			axis.text(
				column_index,
				row_index,
				label,
				ha="center",
				va="center",
				color="white" if value >= 72.0 else COLORS["text"],
			)
	axis.add_patch(
		Rectangle(
			(2.5, -0.5),
			1.0,
			len(row_keys),
			fill=False,
			edgecolor=COLORS["blue"],
			linewidth=1.0,
		),
	)
	axis.set_xticks(range(len(ATOMIC_VARIANTS)), labels=("Evid.", "Direct", "Max.", "Full"))
	axis.set_yticks(range(len(row_labels)), labels=row_labels)
	axis.set_xticks([index - 0.5 for index in range(1, len(ATOMIC_VARIANTS))], minor=True)
	axis.set_yticks([index - 0.5 for index in range(1, len(row_labels))], minor=True)
	axis.grid(which="minor", color="white", linewidth=0.8)
	axis.tick_params(which="minor", bottom=False, left=False)
	axis.tick_params(axis="both", length=0, pad=2.0)
	axis.set_title("(a) Atomic coverage (%)", loc="left", pad=3.0)
	for spine in axis.spines.values():
		spine.set_visible(False)


def _plot_atomic_focus_curve(axis: Any, dataset: Mapping[str, Any]) -> None:
	curves = dict(dataset["atomic_focus_curves"])
	horizon = float(dataset["atomic_focus_horizon_seconds"])
	for variant in ("maximal_certified_program", "full"):
		color, marker = ATOMIC_STYLES[variant]
		line_style = "--" if variant == "maximal_certified_program" else "-"
		curve = dict(curves[variant])
		axis.step(
			curve["x_seconds"],
			curve["solved_percent"],
			where="post",
			color=color,
			linestyle=line_style,
			linewidth=1.05,
			label=ATOMIC_FIGURE_LABELS[variant],
		)
		checkpoints = tuple(
			value for value in (5.0, 10.0, 15.0, 20.0) if value <= horizon
		)
		if checkpoints:
			axis.plot(
				checkpoints,
				_step_values_at(
					curve["x_seconds"],
					curve["solved_percent"],
					checkpoints,
				),
				linestyle="none",
				marker=marker,
				markersize=2.6,
				markerfacecolor=color,
				markeredgecolor="white",
				markeredgewidth=0.3,
			)
	all_focus_records = sum(
		int(curves[variant]["sample_count"]) for variant, _method in ATOMIC_VARIANTS
	)
	minimum_duration = min(
		float(value)
		for variant, _method in ATOMIC_VARIANTS
		for value in curves[variant]["x_seconds"]
		if float(value) > MINIMUM_LOG_SECONDS
	)
	axis.set_xscale("log")
	axis.set_xlim(
		max(MINIMUM_LOG_SECONDS, minimum_duration * 0.8),
		max(20.5, horizon * 1.04),
	)
	axis.set_ylim(-2.0, 102.0)
	axis.set_yticks((0, 25, 50, 75, 100))
	axis.xaxis.set_major_locator(FixedLocator((5.0, 10.0, 20.0)))
	axis.xaxis.set_minor_locator(NullLocator())
	axis.xaxis.set_major_formatter(FuncFormatter(lambda value, _position: f"{value:g}"))
	axis.set_ylabel("Valid (%)")
	axis.set_xlabel("Time (s, log scale)", labelpad=2.0)
	axis.set_title("(b) Tower (12-50 blocks)", loc="left", pad=3.0)
	zero_methods = [
		ATOMIC_FIGURE_LABELS[variant]
		for variant in ("validated_evidence_adapter", "action_only_closure")
		if int(curves[variant]["solved_count"]) == 0
	]
	if zero_methods:
		per_variant_count = all_focus_records // len(ATOMIC_VARIANTS)
		axis.text(
			0.98,
			0.05,
			f"{'/'.join(zero_methods)}: 0/{per_variant_count}",
			transform=axis.transAxes,
			ha="right",
			va="bottom",
			color=COLORS["gray"],
		)
	axis.grid(which="major", color="#E8E8E8", linewidth=0.45)
	axis.set_axisbelow(True)
	_style_axis(axis)
	axis.legend(
		loc="upper left",
		frameon=False,
		borderaxespad=0.15,
		handlelength=1.5,
		handletextpad=0.3,
		labelspacing=0.25,
	)


def _short_domain_label(domain: str) -> str:
	return {
		"blocksworld-clear": "Blocks Clear",
		"blocksworld-on": "Blocks On",
		"blocksworld-tower": "Blocks Tower",
	}.get(domain, domain.replace("-", " ").title())


def _render_empirical_figure(dataset: Mapping[str, Any]) -> bytes:
	rc_parameters = {
		"font.family": FIGURE_FONT_FAMILY,
		"font.size": MINIMUM_FIGURE_TEXT_POINTS,
		"font.weight": "normal",
		"axes.titlesize": MINIMUM_FIGURE_TEXT_POINTS,
		"axes.titleweight": "normal",
		"axes.labelsize": MINIMUM_FIGURE_TEXT_POINTS,
		"axes.labelweight": "normal",
		"xtick.labelsize": MINIMUM_FIGURE_TEXT_POINTS,
		"ytick.labelsize": MINIMUM_FIGURE_TEXT_POINTS,
		"legend.fontsize": MINIMUM_FIGURE_TEXT_POINTS,
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
	axis.set_title("(a) Atomic lifting by domain", loc="left", pad=2.5)
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
		loc="upper left",
		ncol=2,
		frameon=False,
		borderaxespad=0.15,
		handlelength=1.0,
		handletextpad=0.3,
		columnspacing=0.65,
	)


def _plot_atomic_tradeoff(axis: Any, dataset: Mapping[str, Any]) -> None:
	tradeoff = dict(dataset.get("atomic_tradeoff") or {})
	tradeoff_summary = dict(dataset.get("atomic_tradeoff_summary") or {})
	plot_extents: list[tuple[float, float, float, float]] = []
	for variant, method in ATOMIC_VARIANTS:
		color, marker = ATOMIC_STYLES[variant]
		face_color = "white" if variant == "validated_evidence_adapter" else color
		mean_edge_color = (
			color if variant == "validated_evidence_adapter" else "white"
		)
		if variant in tradeoff_summary:
			summary = dict(tradeoff_summary[variant])
			x_mean = float(summary["branch_mean"])
			y_mean = float(summary["coverage_mean"])
			x_sd = float(summary["branch_sd"])
			y_sd = float(summary["coverage_sd"])
		else:
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
				zorder=2,
			)
			x_mean = statistics.mean(x_values)
			y_mean = statistics.mean(y_values)
			x_sd = statistics.stdev(x_values)
			y_sd = statistics.stdev(y_values)
		x_lower = max(0.0, x_mean - x_sd)
		x_upper = x_mean + x_sd
		plot_extents.append((x_lower, x_upper, y_mean - y_sd, y_mean + y_sd))
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
			label=ATOMIC_FIGURE_LABELS[variant],
			zorder=4,
		)
	x_min = min(extent[0] for extent in plot_extents)
	x_max = max(extent[1] for extent in plot_extents)
	x_padding = max(1.0, 0.07 * (x_max - x_min))
	y_min = min(extent[2] for extent in plot_extents)
	y_padding = max(1.5, 0.08 * (100.0 - y_min))
	axis.set_xlim(max(0.0, x_min - x_padding), x_max + x_padding)
	axis.set_ylim(max(0.0, y_min - y_padding), 100.8)
	axis.set_ylabel("Held-out coverage (%)")
	axis.set_xlabel("Emitted branches", labelpad=2.0)
	axis.set_title("(b) Atomic coverage-size tradeoff", loc="left", pad=2.5)
	axis.grid(which="major", color="#E8E8E8", linewidth=0.45)
	axis.set_axisbelow(True)
	_style_axis(axis)
	handles, labels = axis.get_legend_handles_labels()
	legend_order = (0, 2, 1, 3)
	axis.legend(
		handles=[handles[index] for index in legend_order],
		labels=[labels[index] for index in legend_order],
		loc="upper left",
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
	for variant, _method in TEMPORAL_VARIANTS:
		color, line_style, marker = TEMPORAL_STYLES[variant]
		curve = dict(curves[variant])
		axis.step(
			curve["x_seconds"],
			curve["solved_percent"],
			where="post",
			color=color,
			linestyle=line_style,
			linewidth=1.05,
			label=TEMPORAL_FIGURE_LABELS[variant],
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
	axis.set_xlim(MINIMUM_LOG_SECONDS, 2100.0)
	axis.set_ylim(-2.0, 102.0)
	axis.set_yticks((0, 25, 50, 75, 100))
	axis.xaxis.set_major_locator(
		FixedLocator((0.1, 1.0, 10.0, 100.0, 1800.0)),
	)
	axis.xaxis.set_minor_locator(NullLocator())
	axis.xaxis.set_major_formatter(
		FuncFormatter(
			lambda value, _position: "1.8k" if value == 1800.0 else f"{value:g}",
		),
	)
	axis.set_ylabel("Valid (%)")
	axis.set_xlabel("Time (s, log scale)", labelpad=2.0)
	axis.set_title("(c) All temporal queries", loc="left", pad=3.0)
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
			label=TEMPORAL_FIGURE_LABELS[variant],
		)
		for variant, _method in TEMPORAL_VARIANTS
	)
	legend_order = (0, 2, 1, 3)
	axis.legend(
		handles=tuple(legend_handles[index] for index in legend_order),
		loc="lower right",
		bbox_to_anchor=(0.99, 0.03),
		ncol=1,
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


def _parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	input_group = parser.add_mutually_exclusive_group(required=True)
	input_group.add_argument("--ablation-results", type=Path)
	input_group.add_argument("--paired-results", type=Path)
	input_group.add_argument("--five-seed-results", type=Path)
	parser.add_argument(
		"--validation-run-root",
		type=Path,
		default=DEFAULT_VALIDATION_RUN_ROOT,
		help=argparse.SUPPRESS,
	)
	parser.add_argument("--output-file", type=Path)
	return parser.parse_args()


def main() -> int:
	args = _parse_args()
	output_file = args.output_file
	if output_file is None:
		output_file = (
			DEFAULT_OUTPUT_FILE
			if args.ablation_results is not None
			else LEGACY_OUTPUT_FILE
		)
	try:
		if args.ablation_results is not None:
			metadata = generate_frozen_ablation_figure(
				ablation_results_file=args.ablation_results,
				output_file=output_file,
			)
		elif args.five_seed_results is not None:
			metadata = generate_five_seed_empirical_figure(
				five_seed_results_file=args.five_seed_results,
				output_file=output_file,
			)
		else:
			metadata = generate_empirical_figure(
				paired_results_file=args.paired_results,
				output_file=output_file,
			)
	except (OSError, TypeError, ValueError) as error:
		print(f"[fail] empirical_figure error={error}", file=sys.stderr)
		return 2
	print(
		f"[ok] empirical_figure result_kind={metadata['artifact_kind']}",
		flush=True,
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
