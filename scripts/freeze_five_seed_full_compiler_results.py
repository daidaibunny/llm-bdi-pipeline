#!/usr/bin/env python3
"""Freeze five independent Full GP2PL runs into paper-facing result artifacts."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
from typing import Any, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ROOT = PROJECT_ROOT / "artifacts/jason_full_test_runs"
DEFAULT_RUN_PREFIX = "pddl-five-seed-20260713-153900-full-test-seed"
DEFAULT_SOURCE_AGGREGATE = (
	PROJECT_ROOT
	/ "artifacts/parser_order_full_val_logs/pddl-five-seed-20260713-153900"
	/ "five_seed_summary.json"
)
DEFAULT_OUTPUT_JSON = (
	PROJECT_ROOT
	/ "paper_artifacts/gp2pl_evaluation/v1/five_seed_full_compiler_summary.json"
)
DEFAULT_LATEX_OUTPUT_DIR = PROJECT_ROOT / "latex_code/aamas_method_paper/sections"
EXPECTED_SEEDS = (0, 1, 2, 3, 4)
REGISTERED_TRACKED_CHANGE_SEEDS = (4,)
REGISTERED_VALIDATION_WORKERS = 8
REGISTERED_JASON_TIMEOUT_SECONDS = 1800
REGISTERED_PLAN_VERIFIER_TIMEOUT_SECONDS = 1800
REGISTERED_JAVA_STACK_SIZE = "64m"
SEED_COMMAND_NAMES = ("Zero", "One", "Two", "Three", "Four")
EXPECTED_CASE_COUNT = 1228
EXPECTED_DOMAINS = (
	"barman",
	"blocksworld-clear",
	"blocksworld-on",
	"blocksworld-tower",
	"depots",
	"ferry",
	"gripper",
	"logistics",
	"miconic",
	"numeric-ferry",
	"numeric-miconic",
	"numeric-minecraft",
	"numeric-transport",
	"rovers",
	"satellite",
	"transport",
)
COMPILER_EXECUTION_CLOSURE_PATHS = (
	"src/domain_level_planning",
	"src/evaluation/jason_runtime",
	"src/plan_library",
	"src/utils/pddl_parser.py",
	"src/main.py",
	"scripts/run_full_test_jason_validation.py",
	"scripts/run_moose_faithful_e2e.py",
	"scripts/run_moose_asl_batch.sh",
	"scripts/run_pddl_five_seed_full_test.sh",
)


def main() -> None:
	parser = argparse.ArgumentParser(
		description=(
			"Validate and freeze the five independent Full GP2PL Jason/VAL runs."
		),
	)
	parser.add_argument(
		"--seed-summary",
		action="append",
		default=[],
		metavar="SEED=PATH",
		help=(
			"Summary for one seed. Repeat for seeds 0--4. If omitted, use the "
			"registered pddl-five-seed-20260713-153900 results."
		),
	)
	parser.add_argument(
		"--compiler-freeze-revision",
		default="HEAD",
		help="Git revision whose compiler execution closure is frozen.",
	)
	parser.add_argument(
		"--source-aggregate",
		type=Path,
		default=DEFAULT_SOURCE_AGGREGATE,
		help=(
			"Five-seed runner aggregate that indexes the five child validations. "
			"Its counts and execution protocol are checked against the child runs."
		),
	)
	parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
	parser.add_argument(
		"--latex-output-dir",
		type=Path,
		default=DEFAULT_LATEX_OUTPUT_DIR,
	)
	args = parser.parse_args()

	summary_files = (
		_parse_seed_summaries(args.seed_summary)
		if args.seed_summary
		else _default_summary_files()
	)
	result = build_five_seed_result_dataset(
		summary_files,
		allowed_tracked_change_seeds=REGISTERED_TRACKED_CHANGE_SEEDS,
	)
	result["source_aggregate"] = validate_source_aggregate(
		args.source_aggregate,
		result=result,
		project_root=PROJECT_ROOT,
	)
	execution_commits = [row["source_commit"] for row in result["seed_results"]]
	result["compiler_freeze"] = build_compiler_freeze_metadata(
		project_root=PROJECT_ROOT,
		freeze_revision=args.compiler_freeze_revision,
		execution_revisions=execution_commits,
	)
	write_result_files(
		result,
		output_json=args.output_json,
		latex_output_dir=args.latex_output_dir,
	)
	print(
		"frozen five-seed Full GP2PL results "
		f"success={result['aggregate']['pooled_success_count']}/"
		f"{result['aggregate']['pooled_evaluation_count']} "
		f"mean={result['aggregate']['mean_success_rate'] * 100:.2f}% "
		f"sd={result['aggregate']['sample_sd_success_rate'] * 100:.2f}pp "
		f"artifact={Path(args.output_json).expanduser().resolve()}",
	)


def build_five_seed_result_dataset(
	summary_files: Mapping[int, str | Path],
	*,
	compiler_freeze: Mapping[str, Any] | None = None,
	expected_seeds: Sequence[int] = EXPECTED_SEEDS,
	expected_domains: Sequence[str] | None = EXPECTED_DOMAINS,
	expected_case_count: int | None = EXPECTED_CASE_COUNT,
	allowed_tracked_change_seeds: Sequence[int] = (),
) -> dict[str, Any]:
	"""Validate five complete summaries and return a compact descriptive dataset."""

	seed_order = tuple(expected_seeds)
	if set(summary_files) != set(seed_order):
		raise ValueError(
			"seed summaries must exactly cover "
			f"{list(seed_order)}; observed {sorted(summary_files)}",
		)

	seed_results: list[dict[str, Any]] = []
	case_outcomes_by_seed: dict[int, dict[tuple[str, str], bool]] = {}
	domain_success_by_seed: dict[int, Counter[str]] = {}
	domain_total_by_seed: dict[int, Counter[str]] = {}
	failure_diagnostics: Counter[str] = Counter()
	snapshot_hash: str | None = None
	completed_at_values: list[str] = []

	for seed in seed_order:
		summary_path = Path(summary_files[seed]).expanduser().resolve()
		summary = _read_json(summary_path)
		_validate_summary_header(
			summary,
			seed=seed,
			allow_tracked_changes=seed in set(allowed_tracked_change_seeds),
		)
		validations = tuple(summary.get("validations") or ())
		if expected_case_count is not None and len(validations) != expected_case_count:
			raise ValueError(
				f"seed {seed} case count mismatch: expected {expected_case_count}, "
				f"observed {len(validations)}",
			)

		input_snapshot = dict(summary.get("input_snapshot") or {})
		if input_snapshot.get("success") is not True:
			raise ValueError(f"seed {seed} input snapshot is incomplete")
		if int(input_snapshot.get("task_count") or -1) != len(validations):
			raise ValueError(f"seed {seed} input snapshot task count mismatch")
		observed_snapshot_hash = str(input_snapshot.get("manifest_sha256") or "")
		if len(observed_snapshot_hash) < 16:
			raise ValueError(f"seed {seed} input snapshot hash is missing")
		if snapshot_hash is None:
			snapshot_hash = observed_snapshot_hash
		elif snapshot_hash != observed_snapshot_hash:
			raise ValueError("five seeds do not share the same input snapshot")

		case_outcomes: dict[tuple[str, str], bool] = {}
		domain_success: Counter[str] = Counter()
		domain_total: Counter[str] = Counter()
		status_counts: Counter[str] = Counter()
		val_success_count = 0
		for validation in validations:
			case_key = _case_key(validation)
			if case_key in case_outcomes:
				raise ValueError(f"seed {seed} contains duplicate case {case_key}")
			success = _validate_case_record(validation, seed=seed, case_key=case_key)
			case_outcomes[case_key] = success
			domain_total[case_key[0]] += 1
			status_counts[str(validation.get("status") or "missing")] += 1
			if success:
				domain_success[case_key[0]] += 1
				val_success_count += 1
			else:
				failure_diagnostics[
					str(validation.get("error") or "unspecified method failure")
				] += 1

		observed_domains = set(domain_total)
		if expected_domains is not None and observed_domains != set(expected_domains):
			raise ValueError(
				f"seed {seed} domain set mismatch: observed {sorted(observed_domains)}",
			)
		_validate_domain_summaries(
			summary,
			seed=seed,
			domain_success=domain_success,
			domain_total=domain_total,
		)
		all_succeeded = all(case_outcomes.values())
		if summary.get("success") is not all_succeeded:
			raise ValueError(f"seed {seed} top-level success flag is inconsistent")

		source_revision = dict(summary.get("source_revision") or {})
		completed_at = str(summary.get("completed_at") or "")
		completed_at_values.append(completed_at)
		seed_results.append(
			{
				"seed": seed,
				"run_id": str(summary.get("run_id") or ""),
				"completed_at": completed_at,
				"source_commit": str(source_revision.get("commit") or ""),
				"tracked_source_changes": bool(source_revision.get("tracked_changes")),
				"summary_sha256": _sha256(summary_path),
				"success_count": sum(case_outcomes.values()),
				"failure_count": len(case_outcomes) - sum(case_outcomes.values()),
				"evaluation_count": len(case_outcomes),
				"val_success_count": val_success_count,
				"status_counts": dict(sorted(status_counts.items())),
			}
		)
		case_outcomes_by_seed[seed] = case_outcomes
		domain_success_by_seed[seed] = domain_success
		domain_total_by_seed[seed] = domain_total

	baseline_cases = set(case_outcomes_by_seed[seed_order[0]])
	for seed in seed_order[1:]:
		if set(case_outcomes_by_seed[seed]) != baseline_cases:
			raise ValueError(f"seed {seed} case identifiers differ from seed 0")

	pattern_counts: Counter[str] = Counter()
	persistent_failures: list[dict[str, str]] = []
	seed_sensitive_cases: list[dict[str, str]] = []
	domain_case_patterns: dict[str, list[str]] = defaultdict(list)
	for domain, test_id in sorted(baseline_cases):
		pattern = "".join(
			"1" if case_outcomes_by_seed[seed][(domain, test_id)] else "0"
			for seed in seed_order
		)
		pattern_counts[pattern] += 1
		domain_case_patterns[domain].append(pattern)
		case_record = {"domain": domain, "test_id": test_id}
		if pattern == "0" * len(seed_order):
			persistent_failures.append(case_record)
		elif "0" in pattern and "1" in pattern:
			seed_sensitive_cases.append({**case_record, "pattern": pattern})

	domain_rows: list[dict[str, Any]] = []
	for domain in sorted(domain_case_patterns):
		totals = [domain_total_by_seed[seed][domain] for seed in seed_order]
		if len(set(totals)) != 1:
			raise ValueError(f"domain {domain} has inconsistent test counts")
		success_counts = [domain_success_by_seed[seed][domain] for seed in seed_order]
		rates = [count / totals[0] for count in success_counts]
		patterns = domain_case_patterns[domain]
		domain_rows.append(
			{
				"domain": domain,
				"test_count": totals[0],
				"success_counts": success_counts,
				"success_rates": rates,
				"mean_success_rate": statistics.mean(rates),
				"sample_sd_success_rate": statistics.stdev(rates),
				"all_seed_success_case_count": patterns.count("1" * len(seed_order)),
				"seed_sensitive_case_count": sum(
					1 for pattern in patterns if "0" in pattern and "1" in pattern
				),
				"all_seed_failure_case_count": patterns.count("0" * len(seed_order)),
			}
		)

	success_counts = [row["success_count"] for row in seed_results]
	success_rates = [count / len(baseline_cases) for count in success_counts]
	pooled_success_count = sum(success_counts)
	pooled_evaluation_count = len(baseline_cases) * len(seed_order)
	all_seed_success_count = pattern_counts["1" * len(seed_order)]
	all_seed_failure_count = pattern_counts["0" * len(seed_order)]
	seed_sensitive_count = sum(
		count
		for pattern, count in pattern_counts.items()
		if "0" in pattern and "1" in pattern
	)

	return {
		"artifact_kind": "gp2pl_five_seed_full_compiler_submission_result",
		"schema_version": 1,
		"released_at": max(completed_at_values),
		"compiler_freeze": dict(compiler_freeze or {}),
		"protocol": {
			"method": "Full GP2PL",
			"source_method_label": "Full Compiler",
			"atomic_library_mode": "validated-policy-lifting",
			"compiler_variant": "full",
			"seeds": list(seed_order),
			"domain_count": len(domain_rows),
			"case_count_per_seed": len(baseline_cases),
			"input_snapshot_manifest_sha256": snapshot_hash,
			"fresh_validation": True,
			"validation_workers": REGISTERED_VALIDATION_WORKERS,
			"jason_timeout_seconds": REGISTERED_JASON_TIMEOUT_SECONDS,
			"plan_verifier_timeout_seconds": (
				REGISTERED_PLAN_VERIFIER_TIMEOUT_SECONDS
			),
			"jason_java_stack_size": REGISTERED_JAVA_STACK_SIZE,
			"tracked_change_seed_exceptions": sorted(allowed_tracked_change_seeds),
			"independent_seed_runs": True,
			"evidence_union": False,
			"best_seed_selection": False,
			"success_contract": "Jason completion plus original-goal VAL acceptance",
		},
		"seed_results": seed_results,
		"aggregate": {
			"mean_success_count": statistics.mean(success_counts),
			"sample_sd_success_count": statistics.stdev(success_counts),
			"mean_success_rate": statistics.mean(success_rates),
			"sample_sd_success_rate": statistics.stdev(success_rates),
			"pooled_success_count": pooled_success_count,
			"pooled_evaluation_count": pooled_evaluation_count,
			"failure_count": pooled_evaluation_count - pooled_success_count,
			"successful_trace_val_count": sum(
				row["val_success_count"] for row in seed_results
			),
			"all_seed_success_case_count": all_seed_success_count,
			"seed_sensitive_case_count": seed_sensitive_count,
			"all_seed_failure_case_count": all_seed_failure_count,
			"at_least_one_seed_success_case_count": (
				len(baseline_cases) - all_seed_failure_count
			),
			"timeout_count": 0,
			"nonzero_exit_count": 0,
		},
		"domains": domain_rows,
		"case_outcomes": {
			"pattern_counts": dict(sorted(pattern_counts.items())),
			"persistent_failures": persistent_failures,
			"seed_sensitive_cases": seed_sensitive_cases,
		},
		"failure_diagnostics": [
			{"diagnostic": diagnostic, "count": count}
			for diagnostic, count in failure_diagnostics.most_common()
		],
	}


def validate_source_aggregate(
	aggregate_file: str | Path,
	*,
	result: Mapping[str, Any],
	project_root: str | Path = PROJECT_ROOT,
) -> dict[str, Any]:
	"""Verify the runner aggregate against independently validated child runs."""

	root = Path(project_root).expanduser().resolve()
	path = Path(aggregate_file).expanduser().resolve()
	try:
		portable_path = path.relative_to(root).as_posix()
	except ValueError as error:
		raise ValueError("source aggregate must be inside the project root") from error
	aggregate = _read_json(path)
	protocol = dict(result.get("protocol") or {})
	seed_rows = tuple(result.get("seed_results") or ())
	domain_rows = tuple(result.get("domains") or ())
	seeds = tuple(int(value) for value in protocol.get("seeds") or ())
	domain_by_name = {str(row["domain"]): row for row in domain_rows}
	seed_by_id = {int(row["seed"]): row for row in seed_rows}

	expected_header = {
		"schema_version": 1,
		"protocol": "five_independent_moose_synthesis_repetitions",
		"evidence_merged": False,
		"moose_internal_workers": 1,
		"moose_seed_parallelism": len(seeds),
		"cross_seed_jason_parallelism": 1,
		"jason_workers_per_repetition": int(protocol["validation_workers"]),
	}
	for key, expected in expected_header.items():
		if aggregate.get(key) != expected:
			raise ValueError(
				f"source aggregate has unexpected {key}: {aggregate.get(key)!r}",
			)
	if tuple(int(value) for value in aggregate.get("seeds") or ()) != seeds:
		raise ValueError("source aggregate seed order differs from child runs")

	aggregate_domains = dict(aggregate.get("aggregate_domains") or {})
	if set(aggregate_domains) != set(domain_by_name):
		raise ValueError("source aggregate domain set differs from child runs")
	for domain, result_row in domain_by_name.items():
		source_row = dict(aggregate_domains[domain] or {})
		expected_success = sum(int(value) for value in result_row["success_counts"])
		expected_total = int(result_row["test_count"]) * len(seeds)
		expected_values = {
			"completed_repetitions": len(seeds),
			"successful_cases_across_repetitions": expected_success,
			"total_cases_across_repetitions": expected_total,
		}
		for key, expected in expected_values.items():
			if source_row.get(key) != expected:
				raise ValueError(
					f"aggregate domain {domain} has unexpected {key}: "
					f"{source_row.get(key)!r}",
				)
		_float_must_match(
			source_row.get("mean_seed_coverage"),
			result_row["mean_success_rate"],
			label=f"aggregate domain {domain} mean coverage",
		)
		_float_must_match(
			source_row.get("sample_stddev_seed_coverage"),
			result_row["sample_sd_success_rate"],
			label=f"aggregate domain {domain} sample standard deviation",
		)

	repetitions = tuple(aggregate.get("repetitions") or ())
	if len(repetitions) != len(seeds):
		raise ValueError("source aggregate repetition count differs from child runs")
	repetition_by_seed = {int(row.get("seed", -1)): row for row in repetitions}
	if set(repetition_by_seed) != set(seeds):
		raise ValueError("source aggregate repetitions do not cover every seed once")
	for seed in seeds:
		repetition = dict(repetition_by_seed[seed] or {})
		seed_row = seed_by_id[seed]
		if repetition.get("validation_run_id") != seed_row["run_id"]:
			raise ValueError(f"source aggregate seed {seed} child run id differs")
		if repetition.get("moose_exit_code") != 0:
			raise ValueError(f"source aggregate seed {seed} MOOSE generation failed")
		evidence = dict(repetition.get("evidence") or {})
		if set(evidence) != set(domain_by_name) or any(
			dict(record or {}).get("generation_success") is not True
			for record in evidence.values()
		):
			raise ValueError(
				f"source aggregate seed {seed} has incomplete MOOSE evidence",
			)
		validation = dict(repetition.get("validation") or {})
		if set(validation) != set(domain_by_name):
			raise ValueError(
				f"source aggregate seed {seed} validation domain set differs",
			)
		for domain, result_row in domain_by_name.items():
			source_row = dict(validation[domain] or {})
			expected_success = int(result_row["success_counts"][seed])
			expected_total = int(result_row["test_count"])
			if source_row.get("success") != expected_success:
				raise ValueError(
					f"source aggregate seed {seed} domain {domain} success differs",
				)
			if source_row.get("total") != expected_total:
				raise ValueError(
					f"source aggregate seed {seed} domain {domain} total differs",
				)
			if source_row.get("timeout") != 0:
				raise ValueError(
					f"source aggregate seed {seed} domain {domain} timed out",
				)
			_float_must_match(
				source_row.get("coverage"),
				expected_success / expected_total,
				label=(
					f"source aggregate seed {seed} domain {domain} coverage"
				),
			)

	return {
		"artifact_kind": "gp2pl_five_seed_runner_aggregate_provenance",
		"schema_version": int(aggregate["schema_version"]),
		"run_id": str(aggregate.get("run_id") or ""),
		"path": portable_path,
		"sha256": _sha256(path),
		"protocol": str(aggregate["protocol"]),
		"moose_internal_workers": int(aggregate["moose_internal_workers"]),
		"moose_seed_parallelism": int(aggregate["moose_seed_parallelism"]),
		"cross_seed_jason_parallelism": int(
			aggregate["cross_seed_jason_parallelism"],
		),
		"jason_workers_per_repetition": int(
			aggregate["jason_workers_per_repetition"],
		),
		"verified_against_child_runs": True,
	}


def _float_must_match(observed: object, expected: object, *, label: str) -> None:
	try:
		observed_value = float(observed)
		expected_value = float(expected)
	except (TypeError, ValueError) as error:
		raise ValueError(f"{label} is not numeric") from error
	if abs(observed_value - expected_value) > 1e-12:
		raise ValueError(
			f"{label} differs: observed {observed_value}, expected {expected_value}",
		)


def build_compiler_freeze_metadata(
	*,
	project_root: str | Path,
	freeze_revision: str,
	execution_revisions: Sequence[str],
) -> dict[str, Any]:
	"""Hash the exact compiler/runtime closure and match every execution revision."""

	root = Path(project_root).expanduser().resolve()
	resolved_freeze = _git_output(root, "rev-parse", freeze_revision).strip()
	if len(resolved_freeze) != 40:
		raise ValueError("compiler freeze revision did not resolve to a full commit")
	if subprocess.run(
		("git", "diff", "--quiet", "--", *COMPILER_EXECUTION_CLOSURE_PATHS),
		cwd=root,
		check=False,
	).returncode != 0:
		raise ValueError("compiler execution closure has uncommitted changes")

	freeze_digest, freeze_files = _git_closure_digest(root, resolved_freeze)
	resolved_execution_revisions = sorted(set(execution_revisions))
	for revision in resolved_execution_revisions:
		digest, files = _git_closure_digest(root, revision)
		if files != freeze_files or digest != freeze_digest:
			raise ValueError(
				"compiler execution closure differs between freeze revision and "
				f"formal run revision {revision}",
			)
	return {
		"revision": resolved_freeze,
		"closure_sha256": freeze_digest,
		"closure_file_count": len(freeze_files),
		"closure_paths": list(COMPILER_EXECUTION_CLOSURE_PATHS),
		"closure_files": freeze_files,
		"formal_run_revisions": resolved_execution_revisions,
		"byte_identical_to_formal_run_revisions": True,
		"semantic_changes_after_freeze_permitted": False,
	}


def render_result_macros(result: Mapping[str, Any]) -> str:
	"""Render stable LaTeX commands for the five-seed atomic result."""

	aggregate = dict(result["aggregate"])
	protocol = dict(result["protocol"])
	seed_results = tuple(result["seed_results"])
	lines = [
		"% Auto-generated by scripts/freeze_five_seed_full_compiler_results.py.",
		f"\\newcommand{{\\AtomicFiveSeedCaseCount}}{{{_format_int(protocol['case_count_per_seed'])}}}",
		f"\\newcommand{{\\AtomicFiveSeedPooledSuccessCount}}{{{_format_int(aggregate['pooled_success_count'])}}}",
		f"\\newcommand{{\\AtomicFiveSeedPooledEvaluationCount}}{{{_format_int(aggregate['pooled_evaluation_count'])}}}",
		f"\\newcommand{{\\AtomicFiveSeedMeanSuccessPercent}}{{{aggregate['mean_success_rate'] * 100:.2f}}}",
		f"\\newcommand{{\\AtomicFiveSeedSampleSDPercent}}{{{aggregate['sample_sd_success_rate'] * 100:.2f}}}",
		f"\\newcommand{{\\AtomicFiveSeedAllSuccessCount}}{{{_format_int(aggregate['all_seed_success_case_count'])}}}",
		f"\\newcommand{{\\AtomicFiveSeedSensitiveCount}}{{{_format_int(aggregate['seed_sensitive_case_count'])}}}",
		f"\\newcommand{{\\AtomicFiveSeedPersistentFailureCount}}{{{_format_int(aggregate['all_seed_failure_case_count'])}}}",
		f"\\newcommand{{\\AtomicFiveSeedAtLeastOneSuccessCount}}{{{_format_int(aggregate['at_least_one_seed_success_case_count'])}}}",
	]
	for row, seed_name in zip(seed_results, SEED_COMMAND_NAMES, strict=True):
		lines.append(
			f"\\newcommand{{\\AtomicSeed{seed_name}SuccessCount}}"
			f"{{{_format_int(row['success_count'])}}}",
		)
	return "\n".join(lines) + "\n"


def render_main_table(result: Mapping[str, Any]) -> str:
	"""Render the compact main-paper table for five-seed held-out coverage."""

	protocol = dict(result["protocol"])
	domain_rows = tuple(result["domains"])
	seed_results = tuple(result["seed_results"])
	all_seed_complete = tuple(
		row
		for row in domain_rows
		if all(
			count == row["test_count"]
			for count in row["success_counts"]
		)
	)
	variable_domains = tuple(
		sorted(
			(row for row in domain_rows if row not in all_seed_complete),
			key=lambda row: (-int(row["test_count"]), str(row["domain"])),
		)
	)
	lines = [
		"% Auto-generated by scripts/freeze_five_seed_full_compiler_results.py.",
		"\\begin{table}[htbp]",
		"\\centering",
		"\\small",
		"\\setlength{\\tabcolsep}{2.4pt}",
		"\\begin{tabular}{lrrr}",
		"\\toprule",
		"Scope & Cases/seed & Valid/seed & Coverage (\\%) \\\\",
		"\\midrule",
	]
	all_success_counts = tuple(int(row["success_count"]) for row in seed_results)
	lines.append(
		f"All {len(domain_rows)} domains & "
		f"{_format_int(protocol['case_count_per_seed'])} & "
		f"{_format_count_range(all_success_counts)} & "
		f"{_format_mean_and_sample_sd(result['aggregate'])} \\\\"
	)
	if all_seed_complete:
		stable_case_count = sum(int(row["test_count"]) for row in all_seed_complete)
		stable_success_counts = tuple(
			sum(int(row["success_counts"][index]) for row in all_seed_complete)
			for index in range(len(seed_results))
		)
		lines.append(
			f"All-seed complete ({len(all_seed_complete)}) & "
			f"{_format_int(stable_case_count)} & "
			f"{_format_count_range(stable_success_counts)} & "
			"100.0 $\\pm$ 0.0 \\\\"
		)
	for row in variable_domains:
		lines.append(
			f"{_domain_display_name(row['domain'])} & "
			f"{_format_int(row['test_count'])} & "
			f"{_format_count_range(row['success_counts'])} & "
			f"{_format_mean_and_sample_sd(row)} \\\\"
		)
	lines.extend(
		[
			"\\bottomrule",
			"\\end{tabular}",
			(
				"\\caption{Full GP2PL atomic held-out coverage over $n=5$ "
				"independently compiled evidence-seed libraries. Coverage is mean "
				"$\\pm$ sample standard deviation (SD) across seeds; Valid/seed "
				"gives the raw minimum--"
				"maximum count. Domains complete in every seed are aggregated, and every "
				"remaining domain is shown separately. No run is pooled or selected.}"
			),
			"\\label{tab:five-seed-atomic}",
			"\\end{table}",
		],
	)
	return "\n".join(lines) + "\n"


def render_domain_table(result: Mapping[str, Any]) -> str:
	"""Render the complete supplement table by domain and seed."""

	lines = [
		"% Auto-generated by scripts/freeze_five_seed_full_compiler_results.py.",
		"\\begin{table*}[htbp]",
		"\\centering",
		"\\small",
		"\\setlength{\\tabcolsep}{3pt}",
		"\\begin{tabular}{lrrrrrrr}",
		"\\toprule",
		(
			"Domain & Test & Seed 0 & Seed 1 & Seed 2 & Seed 3 & Seed 4 & "
			"Coverage (\\%) \\\\"
		),
		"\\midrule",
	]
	for row in result["domains"]:
		counts = " & ".join(str(value) for value in row["success_counts"])
		lines.append(
			f"{row['domain']} & {row['test_count']} & {counts} & "
			f"{_format_mean_and_sample_sd(row)} \\\\"
		)
	lines.extend(
		[
			"\\bottomrule",
			"\\end{tabular}",
			(
				"\\caption{Complete Full GP2PL atomic held-out successes by independent "
				"MOOSE goal-order seed. Coverage is mean $\\pm$ sample standard "
				"deviation (SD) for $n=5$ "
				"independently compiled libraries; no evidence is pooled and no "
				"best seed is selected.}"
			),
			"\\label{tab:five-seed-atomic-domains}",
			"\\end{table*}",
		],
	)
	return "\n".join(lines) + "\n"


def _format_count_range(values: Sequence[int]) -> str:
	"""Format a per-seed count as one value or an inclusive observed range."""

	minimum = min(int(value) for value in values)
	maximum = max(int(value) for value in values)
	if minimum == maximum:
		return _format_int(minimum)
	return f"{_format_int(minimum)}--{_format_int(maximum)}"


def _format_mean_and_sample_sd(row: Mapping[str, Any]) -> str:
	"""Format seed-level percentage mean and sample standard deviation."""

	mean = float(row["mean_success_rate"]) * 100
	sample_sd = float(row["sample_sd_success_rate"]) * 100
	return f"{mean:.1f} $\\pm$ {sample_sd:.1f}"


def _domain_display_name(value: object) -> str:
	"""Render a domain identifier as a compact paper-facing label."""

	return str(value).replace("-", " ").title()


def write_result_files(
	result: Mapping[str, Any],
	*,
	output_json: str | Path,
	latex_output_dir: str | Path,
) -> None:
	"""Write the compact JSON and all LaTeX fragments."""

	json_path = Path(output_json).expanduser().resolve()
	latex_dir = Path(latex_output_dir).expanduser().resolve()
	json_path.parent.mkdir(parents=True, exist_ok=True)
	latex_dir.mkdir(parents=True, exist_ok=True)
	json_path.write_text(
		json.dumps(result, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)
	(latex_dir / "result_five_seed_atomic_macros.tex").write_text(
		render_result_macros(result),
		encoding="utf-8",
	)
	(latex_dir / "result_five_seed_atomic_table.tex").write_text(
		render_main_table(result),
		encoding="utf-8",
	)
	(latex_dir / "result_five_seed_atomic_domain_table.tex").write_text(
		render_domain_table(result),
		encoding="utf-8",
	)


def _validate_summary_header(
	summary: Mapping[str, Any],
	*,
	seed: int,
	allow_tracked_changes: bool,
) -> None:
	if summary.get("artifact_kind") != "full_test_jason_validation_from_moose_asl_batch":
		raise ValueError(f"seed {seed} has the wrong artifact kind")
	settings = dict(summary.get("settings") or {})
	expected_settings = {
		"atomic_library_mode": "validated-policy-lifting",
		"compiler_variant": "full",
		"jason_java_stack_size": REGISTERED_JAVA_STACK_SIZE,
		"method": "Full Compiler",
		"num_workers": REGISTERED_VALIDATION_WORKERS,
		"plan_verifier_timeout_seconds": (
			REGISTERED_PLAN_VERIFIER_TIMEOUT_SECONDS
		),
		"require_plan_verifier": True,
		"timeout_seconds": REGISTERED_JASON_TIMEOUT_SECONDS,
		"write_per_test_runtime_asl": True,
	}
	for key, expected in expected_settings.items():
		if settings.get(key) != expected:
			raise ValueError(f"seed {seed} has unexpected {key}: {settings.get(key)!r}")
	if int(summary.get("resumed_validation_count") or 0) != 0:
		raise ValueError(f"seed {seed} reused validation results")
	source_revision = dict(summary.get("source_revision") or {})
	if source_revision.get("available") is not True:
		raise ValueError(f"seed {seed} has no source revision")
	if source_revision.get("tracked_changes") is not False and not allow_tracked_changes:
		raise ValueError(f"seed {seed} has tracked source changes")
	if source_revision.get("untracked_files") is not False:
		raise ValueError(f"seed {seed} has untracked source files")
	if len(str(source_revision.get("commit") or "")) != 40:
		raise ValueError(f"seed {seed} source commit is not pinned")


def _validate_case_record(
	validation: Mapping[str, Any],
	*,
	seed: int,
	case_key: tuple[str, str],
) -> bool:
	if validation.get("timed_out") is not False:
		raise ValueError(f"seed {seed} case {case_key} timed out")
	if validation.get("exit_code") != 0:
		raise ValueError(f"seed {seed} case {case_key} has nonzero exit status")
	success = validation.get("success")
	if not isinstance(success, bool):
		raise ValueError(f"seed {seed} case {case_key} has no Boolean outcome")
	expected_status = "success" if success else "failed"
	if validation.get("status") != expected_status:
		raise ValueError(f"seed {seed} case {case_key} has inconsistent status")
	if success:
		if (
			validation.get("plan_verifier_attempted") is not True
			or validation.get("plan_verifier_success") is not True
		):
			raise ValueError(
				f"seed {seed} case {case_key} successful case lacks VAL acceptance",
			)
		if validation.get("action_count_complete") is not True:
			raise ValueError(f"seed {seed} case {case_key} has an incomplete trace")
		action_count = validation.get("action_count")
		if not isinstance(action_count, int) or action_count < 0:
			raise ValueError(f"seed {seed} case {case_key} has invalid action count")
	return success


def _validate_domain_summaries(
	summary: Mapping[str, Any],
	*,
	seed: int,
	domain_success: Counter[str],
	domain_total: Counter[str],
) -> None:
	domain_records = dict(summary.get("domains") or {})
	if not domain_records:
		return
	if set(domain_records) != set(domain_total):
		raise ValueError(f"seed {seed} domain summary set mismatch")
	for domain, record in domain_records.items():
		validation = dict(record.get("jason_validation") or {})
		if int(validation.get("test_count") or -1) != domain_total[domain]:
			raise ValueError(f"seed {seed} domain {domain} test count mismatch")
		if int(validation.get("success_count") or -1) != domain_success[domain]:
			raise ValueError(f"seed {seed} domain {domain} success count mismatch")


def _case_key(validation: Mapping[str, Any]) -> tuple[str, str]:
	domain = str(validation.get("domain") or "").strip()
	problem_file = str(validation.get("problem_file") or "").strip()
	test_id = Path(problem_file).stem
	if not domain or not test_id:
		raise ValueError("validation record is missing its domain or problem identifier")
	return domain, test_id


def _default_summary_files() -> dict[int, Path]:
	return {
		seed: DEFAULT_RUN_ROOT / f"{DEFAULT_RUN_PREFIX}{seed}" / "summary.json"
		for seed in EXPECTED_SEEDS
	}


def _parse_seed_summaries(values: Sequence[str]) -> dict[int, Path]:
	result: dict[int, Path] = {}
	for value in values:
		seed_text, separator, path_text = value.partition("=")
		if not separator or not seed_text.isdigit() or not path_text:
			raise ValueError(f"invalid --seed-summary value: {value!r}")
		seed = int(seed_text)
		if seed in result:
			raise ValueError(f"duplicate --seed-summary for seed {seed}")
		result[seed] = Path(path_text)
	return result


def _git_closure_digest(root: Path, revision: str) -> tuple[str, dict[str, str]]:
	files_text = _git_output(
		root,
		"ls-tree",
		"-r",
		"--name-only",
		revision,
		"--",
		*COMPILER_EXECUTION_CLOSURE_PATHS,
	)
	files = tuple(sorted(line for line in files_text.splitlines() if line.strip()))
	if not files:
		raise ValueError(f"compiler closure is empty at revision {revision}")
	digest = hashlib.sha256()
	file_hashes: dict[str, str] = {}
	for path in files:
		content = subprocess.run(
			("git", "show", f"{revision}:{path}"),
			cwd=root,
			capture_output=True,
			check=True,
		).stdout
		file_hashes[path] = hashlib.sha256(content).hexdigest()
		digest.update(path.encode("utf-8"))
		digest.update(b"\0")
		digest.update(content)
		digest.update(b"\0")
	return digest.hexdigest(), file_hashes


def _git_output(root: Path, *arguments: str) -> str:
	try:
		return subprocess.run(
			("git", *arguments),
			cwd=root,
			text=True,
			capture_output=True,
			check=True,
		).stdout
	except subprocess.CalledProcessError as error:
		raise ValueError(error.stderr.strip() or "git command failed") from error


def _domain_count_cell(domain: Mapping[str, Any] | None, index: int) -> str:
	if domain is None:
		return "--"
	return f"{domain['success_counts'][index]}/{domain['test_count']}"


def _read_json(path: Path) -> dict[str, Any]:
	if not path.is_file():
		raise ValueError(f"required summary does not exist: {path}")
	data = json.loads(path.read_text(encoding="utf-8"))
	if not isinstance(data, dict):
		raise ValueError(f"expected a JSON object: {path}")
	return data


def _sha256(path: Path) -> str:
	return hashlib.sha256(path.read_bytes()).hexdigest()


def _format_int(value: int | float) -> str:
	return f"{int(value):,}"


if __name__ == "__main__":
	main()
