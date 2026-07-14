#!/usr/bin/env python3
"""Generate the gated GP2PL empirical figure from one paired experiment."""

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
				"source_file": str(input_path),
				"output_file_untouched": str(output_path),
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
		"source_file": str(input_path),
		"source_sha256": _sha256(input_path),
		"source_revision": dict(dataset["source_revision"]),
		"output_file": str(output_path),
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
			"source_file": str(input_path),
			"output_file": str(output_path),
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


def _render_empirical_figure(dataset: Mapping[str, Any]) -> bytes:
	rc_parameters = {
		"font.family": "DejaVu Sans",
		"font.size": 5.8,
		"font.weight": "normal",
		"axes.titlesize": 6.8,
		"axes.titleweight": "normal",
		"axes.labelsize": 5.8,
		"axes.labelweight": "normal",
		"xtick.labelsize": 5.1,
		"ytick.labelsize": 5.1,
		"legend.fontsize": 4.7,
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
			left=0.16,
			right=0.99,
			top=0.935,
			bottom=0.14,
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
			color=COLORS["gray"],
			markerfacecolor="white",
			linewidth=0,
			label="Evidence Only",
		),
		Line2D(
			[],
			[],
			marker="D",
			color=COLORS["blue"],
			markerfacecolor=COLORS["blue"],
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
		points = tuple(tradeoff[variant])
		x_values = [float(point["selected_branch_count"]) for point in points]
		y_values = [float(point["coverage_percent"]) for point in points]
		axis.scatter(
			x_values,
			y_values,
			s=8,
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
			markersize=3.7,
			markerfacecolor=face_color,
			markeredgecolor="white",
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
			markersize=2.4,
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


def _sha256(path: Path) -> str:
	hasher = hashlib.sha256()
	with path.open("rb") as handle:
		for chunk in iter(lambda: handle.read(1024 * 1024), b""):
			hasher.update(chunk)
	return hasher.hexdigest()


def _parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--paired-results", type=Path, required=True)
	parser.add_argument("--output-file", type=Path, default=DEFAULT_OUTPUT_FILE)
	return parser.parse_args()


def main() -> int:
	args = _parse_args()
	try:
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
