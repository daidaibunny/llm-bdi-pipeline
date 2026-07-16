#!/usr/bin/env python3
"""Generate conference-neutral result data and LaTeX tables from pinned artifacts."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import statistics
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK_ROOT = PROJECT_ROOT / "paper_artifacts/temporal_goal_benchmark/v1"
DEFAULT_CONFORMANCE_ROOT = (
	PROJECT_ROOT / "paper_artifacts/temporal_semantic_conformance/v1"
)
DEFAULT_DOMAIN_ROOT = PROJECT_ROOT / "src/domains"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "artifacts/evaluation_tables"


def main() -> None:
	parser = argparse.ArgumentParser(
		description="Generate fail-closed evaluation tables from pinned artifacts.",
	)
	parser.add_argument("--benchmark-root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
	parser.add_argument("--execution-summary", type=Path, required=True)
	parser.add_argument("--atomic-library-root", type=Path, required=True)
	parser.add_argument("--benchmark-compatibility", type=Path)
	parser.add_argument("--conformance-root", type=Path, default=DEFAULT_CONFORMANCE_ROOT)
	parser.add_argument("--domain-root", type=Path, default=DEFAULT_DOMAIN_ROOT)
	parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
	args = parser.parse_args()

	result = build_evaluation_result_dataset(
		benchmark_root=args.benchmark_root,
		execution_summary_file=args.execution_summary,
		atomic_library_root=args.atomic_library_root,
		benchmark_compatibility_file=args.benchmark_compatibility,
		conformance_root=args.conformance_root,
		domain_root=args.domain_root,
	)
	write_result_files(result, output_dir=args.output_dir)
	print(
		"generated evaluation results "
		f"run={result['provenance']['execution_run_id']} "
		f"domains={result['benchmark']['domain_count']} "
		f"cases={result['benchmark']['problem_count']}",
	)


def build_evaluation_result_dataset(
	*,
	benchmark_root: str | Path,
	execution_summary_file: str | Path,
	atomic_library_root: str | Path,
	conformance_root: str | Path,
	domain_root: str | Path,
	benchmark_compatibility_file: str | Path | None = None,
) -> dict[str, Any]:
	"""Validate pinned inputs and return the normalized evaluation dataset."""

	benchmark_path = Path(benchmark_root).expanduser().resolve()
	execution_path = Path(execution_summary_file).expanduser().resolve()
	atomic_root = Path(atomic_library_root).expanduser().resolve()
	conformance_path = Path(conformance_root).expanduser().resolve()
	domains_path = Path(domain_root).expanduser().resolve()
	conformance = _load_conformance_result(conformance_path)

	manifest = _read_json(benchmark_path / "manifest.json")
	benchmark_file = benchmark_path / str(manifest.get("benchmark_file") or "benchmark.json")
	benchmark = _read_json(benchmark_file)
	benchmark_sha256 = _sha256(benchmark_file)
	_require_equal(
		benchmark_sha256,
		manifest.get("benchmark_sha256"),
		"benchmark hash mismatch",
	)
	_require_equal(
		benchmark.get("benchmark_id"),
		manifest.get("benchmark_id"),
		"benchmark id mismatch",
	)

	release_validation = _read_json(benchmark_path / "release_validation.json")
	_require_equal(
		release_validation.get("benchmark_sha256"),
		benchmark_sha256,
		"release-validation benchmark hash mismatch",
	)
	for check_name, passed in dict(
		release_validation.get("delivered_validation_matches_independent") or {},
	).items():
		if passed is not True:
			raise ValueError(f"release-validation check failed: {check_name}")

	prediction_file = benchmark_path / "model_run/translation_predictions.jsonl"
	model_run = _read_json(benchmark_path / "model_run/run_config.json")
	prediction_sha256 = _sha256(prediction_file)
	_require_equal(
		prediction_sha256,
		model_run.get("translation_predictions_sha256"),
		"prediction hash mismatch",
	)
	_require_equal(
		prediction_sha256,
		release_validation.get("frozen_predictions_sha256"),
		"release-validation prediction hash mismatch",
	)
	predictions = _read_jsonl(prediction_file)
	translation_results = _read_jsonl(
		benchmark_path / "validation/translation_validation_results.jsonl",
	)

	execution = _read_json(execution_path)
	source_revision = dict(execution.get("source_revision") or {})
	if source_revision.get("tracked_changes") is not False:
		raise ValueError("execution artifact has tracked source changes")
	commit = str(source_revision.get("commit") or "").strip()
	if len(commit) < 8:
		raise ValueError("execution artifact has no pinned source commit")
	_require_equal(
		execution.get("benchmark_id"),
		benchmark.get("benchmark_id"),
		"execution benchmark id mismatch",
	)
	benchmark_compatibility = certify_benchmark_compatibility(
		benchmark=benchmark,
		current_benchmark_sha256=benchmark_sha256,
		execution_benchmark_sha256=str(execution.get("benchmark_sha256") or ""),
		compatibility_file=benchmark_compatibility_file,
	)

	case_index = _case_index(benchmark)
	results = tuple(execution.get("results") or ())
	if len(results) != len(case_index):
		raise ValueError(
			"execution result count mismatch: "
			f"expected {len(case_index)}, observed {len(results)}",
		)
	result_ids = [str(row.get("sample_id") or "") for row in results]
	if len(set(result_ids)) != len(result_ids) or set(result_ids) != set(case_index):
		raise ValueError("execution sample ids do not exactly cover the benchmark")

	prediction_ids = [str(row.get("translation_id") or "") for row in predictions]
	validation_by_id = {
		str(row.get("translation_id") or ""): row for row in translation_results
	}
	if len(set(prediction_ids)) != len(prediction_ids):
		raise ValueError("prediction artifact contains duplicate translation ids")
	if set(prediction_ids) != set(validation_by_id):
		raise ValueError("prediction and translation-validation ids differ")
	benchmark_translation_ids = {
		str(case.get("translation_id") or "") for case in case_index.values()
	}
	if set(prediction_ids) != benchmark_translation_ids:
		raise ValueError("predictions do not exactly cover benchmark translation ids")

	domain_results: dict[str, list[dict[str, Any]]] = defaultdict(list)
	profile_results: dict[str, list[dict[str, Any]]] = defaultdict(list)
	failure_counts: Counter[str] = Counter()
	for row in results:
		domain = str(row.get("domain") or "")
		profile = str(row.get("profile") or "")
		domain_results[domain].append(row)
		profile_results[profile].append(row)
		failure_counts.update(_execution_failure_categories(row))

	atomic_inputs = dict(execution.get("atomic_library_inputs") or {})
	if set(atomic_inputs) != set(domain_results):
		raise ValueError("atomic library inputs do not exactly cover execution domains")

	domain_rows: list[dict[str, Any]] = []
	for domain in sorted(domain_results):
		library_dir = atomic_root / domain
		asl_file = library_dir / "plan_library.asl"
		json_file = library_dir / "plan_library.json"
		input_record = dict(atomic_inputs[domain])
		if _sha256(asl_file) != input_record.get("plan_library_asl_sha256"):
			raise ValueError(f"atomic ASL hash mismatch: {domain}")
		if _sha256(json_file) != input_record.get("plan_library_json_sha256"):
			raise ValueError(f"atomic JSON hash mismatch: {domain}")
		library = _read_json(json_file)
		metadata = dict(library.get("metadata") or {})
		synthesis = dict(metadata.get("atomic_module_synthesis") or {})
		quality = dict(metadata.get("library_quality") or {})
		evidence = dict(metadata.get("evidence_module") or {})
		pddl_support = dict(metadata.get("pddl_support") or {})
		if evidence.get("source_provider") != "moose":
			raise ValueError(f"unsupported evidence provider in {domain}")
		if pddl_support.get("is_compilable") is not True:
			raise ValueError(f"PDDL compilation is not certified for {domain}")
		if quality.get("validated_policy_lifting_ready") is not True:
			raise ValueError(f"validated policy lifting is not ready for {domain}")
		if synthesis.get("selector_backend") != "clingo_asp_minimize":
			raise ValueError(f"Clingo selector metadata missing for {domain}")
		_assert_module_closure(domain, synthesis)

		candidate_counts = dict(synthesis.get("candidate_source_counts") or {})
		candidate_count = int(
			candidate_counts.get("joint_unique")
			or synthesis.get("raw_candidate_count")
			or 0
		)
		selected_branch_count = int(
			synthesis.get("plan_count") or len(tuple(library.get("plans") or ()))
		)
		rows = domain_results[domain]
		domain_rows.append(
			{
				"domain": domain,
				"train_count": len(tuple((domains_path / domain / "train").glob("*.pddl"))),
				"test_count": len(tuple((domains_path / domain / "test").glob("*.pddl"))),
				"moose_status": "readable_policy",
				"atomic_compilation_status": "certified",
				"candidate_count": candidate_count,
				"evidence_candidate_count": int(
					candidate_counts.get("validated_evidence") or 0
				),
				"schema_candidate_count": int(candidate_counts.get("schema") or 0),
				"selected_branch_count": selected_branch_count,
				"library_size_bytes": asl_file.stat().st_size,
				"jason_success_count": _count(rows, _jason_success),
				"val_success_count": _count(rows, _val_success),
				"gold_dfa_accept_count": _count(rows, _gold_accepted),
				"prediction_dfa_accept_count": _count(rows, _prediction_accepted),
				"execution_total": len(rows),
				"median_action_count": _median(row.get("action_count") for row in rows),
				"median_runtime_seconds": _median(
					row.get("duration_seconds") for row in rows
				),
			}
		)

	translation_profile_ids: dict[str, set[str]] = defaultdict(set)
	for case in case_index.values():
		translation_profile_ids[str(case.get("profile") or "")].add(
			str(case.get("translation_id") or ""),
		)
	profile_rows: list[dict[str, Any]] = []
	for profile in sorted(profile_results):
		rows = profile_results[profile]
		translation_ids = translation_profile_ids[profile]
		profile_rows.append(
			{
				"profile": profile,
				"query_count": len(rows),
				"success_count": _count(rows, _end_to_end_success),
				"translation_count": len(translation_ids),
				"json_valid_count": sum(
					1
					for translation_id in translation_ids
					if _prediction_accepted_by_schema(
						next(
							row
							for row in predictions
							if row.get("translation_id") == translation_id
						)
					)
				),
				"dfa_equivalent_count": sum(
					1
					for translation_id in translation_ids
					if _translation_equivalent(validation_by_id[translation_id])
				),
				"controller_compiled_count": len(rows) - sum(
					1 for row in rows if row.get("status") == "controller_compile_failed"
				),
				"jason_success_count": _count(rows, _jason_success),
				"val_success_count": _count(rows, _val_success),
				"gold_dfa_accept_count": _count(rows, _gold_accepted),
				"prediction_dfa_accept_count": _count(rows, _prediction_accepted),
				"median_action_count": _median(row.get("action_count") for row in rows),
				"median_runtime_seconds": _median(
					row.get("duration_seconds") for row in rows
				),
			}
		)

	execution_success_count = sum(1 for row in results if _end_to_end_success(row))
	started_at = _parse_datetime(str(execution.get("started_at") or ""))
	completed_at = _parse_datetime(str(execution.get("completed_at") or ""))
	return {
		"schema_version": 1,
		"benchmark": {
			"benchmark_id": benchmark.get("benchmark_id"),
			"benchmark_sha256": benchmark_sha256,
			"domain_count": len(domain_results),
			"problem_count": len(results),
		},
		"translation": {
			"total": len(predictions),
			"json_valid_count": sum(
				1 for row in predictions if _prediction_accepted_by_schema(row)
			),
			"dfa_equivalent_count": sum(
				1 for row in translation_results if _translation_equivalent(row)
			),
		},
		"execution": {
			"success_count": execution_success_count,
			"jason_success_count": _count(results, _jason_success),
			"val_success_count": _count(results, _val_success),
			"gold_dfa_accept_count": _count(results, _gold_accepted),
			"prediction_dfa_accept_count": _count(results, _prediction_accepted),
			"median_action_count": _median(row.get("action_count") for row in results),
			"median_runtime_seconds": _median(
				row.get("duration_seconds") for row in results
			),
			"wall_runtime_seconds": (completed_at - started_at).total_seconds(),
			"failure_counts": dict(sorted(failure_counts.items())),
		},
		"atomic": {
			"candidate_count": sum(row["candidate_count"] for row in domain_rows),
			"selected_branch_count": sum(
				row["selected_branch_count"] for row in domain_rows
			),
			"library_size_bytes": sum(row["library_size_bytes"] for row in domain_rows),
		},
		"conformance": conformance,
		"domains": domain_rows,
		"profiles": profile_rows,
		"provenance": {
			"benchmark_compatibility": benchmark_compatibility,
			"execution_run_id": execution.get("run_id"),
			"execution_commit": commit,
			"execution_summary_sha256": _sha256(execution_path),
			"prediction_sha256": prediction_sha256,
			"model_id": predictions[0].get("model_id") if predictions else None,
			"prompt_source_commit": model_run.get("prompt_source_commit"),
		},
	}


def render_result_macros(result: dict[str, Any]) -> str:
	"""Render aggregate LaTeX macros from a normalized result dataset."""

	benchmark = dict(result["benchmark"])
	translation = dict(result["translation"])
	execution = dict(result["execution"])
	atomic = dict(result["atomic"])
	conformance = dict(result["conformance"])
	provenance = dict(result["provenance"])
	removed_branch_count = atomic["candidate_count"] - atomic["selected_branch_count"]
	reduction_percent = (
		100 * removed_branch_count / atomic["candidate_count"]
		if atomic["candidate_count"]
		else 0
	)
	values = {
		"BenchmarkDomainCount": benchmark["domain_count"],
		"TEGProblemCount": benchmark["problem_count"],
		"TranslationInputCount": translation["total"],
		"TranslationJSONValidCount": translation["json_valid_count"],
		"TranslationEquivalentCount": translation["dfa_equivalent_count"],
		"TEGEndToEndSuccessCount": execution["success_count"],
		"TEGJasonSuccessCount": execution["jason_success_count"],
		"TEGVALSuccessCount": execution["val_success_count"],
		"TEGGoldDFAAcceptCount": execution["gold_dfa_accept_count"],
		"TEGPredictionDFAAcceptCount": execution["prediction_dfa_accept_count"],
		"TEGMedianActionCount": execution["median_action_count"],
		"TEGMedianRuntimeSeconds": execution["median_runtime_seconds"],
		"TEGWallRuntimeSeconds": execution["wall_runtime_seconds"],
		"TEGWallRuntimeMinutes": execution["wall_runtime_seconds"] / 60,
		"AtomicCandidateCount": atomic["candidate_count"],
		"AtomicSelectedBranchCount": atomic["selected_branch_count"],
		"AtomicRemovedBranchCount": removed_branch_count,
		"AtomicReductionPercent": reduction_percent,
		"AtomicLibrarySizeKiB": atomic["library_size_bytes"] / 1024,
		"ConformanceSemanticCaseCount": conformance["semantic_case_count"],
		"ConformanceSemanticSuccessCount": conformance["semantic_success_count"],
		"ConformanceZeroActionCaseCount": conformance["zero_action_case_count"],
		"ConformanceZeroActionSuccessCount": conformance["zero_action_success_count"],
		"ConformanceRunID": conformance["run_id"],
		"TEGExecutionRunID": provenance["execution_run_id"],
		"TEGExecutionCommit": str(provenance["execution_commit"])[:8],
	}
	lines = ["% Auto-generated by scripts/generate_evaluation_tables.py."]
	for name, value in values.items():
		lines.append(f"\\newcommand{{\\{name}}}{{{_format_macro_value(value)}}}")
	return "\n".join(lines) + "\n"


def render_domain_table(result: dict[str, Any]) -> str:
	"""Render the per-domain atomic-library and execution result table."""

	rows = list(result["domains"])
	for row in rows:
		count = int(row["execution_total"])
		if any(
			int(row[key]) != count
			for key in (
				"jason_success_count",
				"val_success_count",
				"gold_dfa_accept_count",
				"prediction_dfa_accept_count",
			)
		):
			raise ValueError(f"cannot render incomplete domain row: {row['domain']}")

	def cells(row: dict[str, Any] | None) -> list[str]:
		if row is None:
			return [""] * 6
		count = int(row["execution_total"])
		return [
			_domain_label(row["domain"]),
			f"{row['train_count']}/{row['test_count']}",
			f"{row['evidence_candidate_count']}/{row['schema_candidate_count']}",
			str(row["selected_branch_count"]),
			f"{row['jason_success_count']}/{count}",
			f"{row['median_runtime_seconds']:.1f}",
		]

	lines = [
		"% Auto-generated by scripts/generate_evaluation_tables.py.",
		"\\begin{table}[htbp]",
		"\\centering",
		"\\small",
		"\\setlength{\\tabcolsep}{2.0pt}",
		"\\begin{tabular}{lrrrrr}",
		"\\toprule",
		"Domain & Tr/Te & E/S & Sel. & E2E & s \\\\",
		"\\midrule",
	]
	for row in rows:
		lines.append(" & ".join(cells(row)) + " \\\\")
	lines.extend(
		[
			"\\bottomrule",
			"\\end{tabular}",
			"\\caption{Per-domain fixed seed-0 atomic cores and temporal "
			"execution. Tr/Te denotes train/test instances; E/S denotes "
			"evidence/schema candidates; Sel. denotes selected branches; E2E "
			"requires Jason, neutral-goal VAL, and both DFA checks; s is median "
			"wall-clock seconds per query.}",
			"\\label{tab:domain-results}",
			"\\end{table}",
		],
	)
	return "\n".join(lines) + "\n"


def render_profile_table(result: dict[str, Any]) -> str:
	"""Render a compact per-profile translation and end-to-end result table."""

	benchmark = dict(result["benchmark"])
	translation = dict(result["translation"])
	execution = dict(result["execution"])
	lines = [
		"% Auto-generated by scripts/generate_evaluation_tables.py.",
		"\\begin{table}[htbp]",
		"\\centering",
		"\\small",
		"\\setlength{\\tabcolsep}{1.7pt}",
		"\\begin{tabular}{lrrrr}",
		"\\toprule",
		"Profile & DFA equiv. & E2E valid & Med. act. & Med. s \\\\",
		"\\midrule",
	]
	for row in result["profiles"]:
		lines.append(
			f"{_profile_label(row['profile'])} & "
			f"{row['dfa_equivalent_count']}/{row['translation_count']} & "
			f"{row['success_count']}/{row['query_count']} & "
			f"{_format_number(row['median_action_count'])} & "
			f"{row['median_runtime_seconds']:.1f} \\\\"
		)
	lines.extend(
		[
			"\\midrule",
			f"All & {int(translation['dfa_equivalent_count']):,}/"
			f"{int(translation['total']):,} & "
			f"{int(execution['success_count']):,}/"
			f"{int(benchmark['problem_count']):,} & "
			f"{_format_number(execution['median_action_count'])} & "
			f"{execution['median_runtime_seconds']:.1f} \\\\",
		],
	)
	lines.extend(
		[
			"\\bottomrule",
			"\\end{tabular}",
			"\\caption{Translation and execution by temporal profile. DFA equiv. "
			"counts the 475 distinct translation inputs whose gold and predicted "
			"DFAs have exactly the same finite-trace language. E2E valid counts all "
			"1,228 bound queries and requires controller compilation, Jason "
			"completion, neutral-goal VAL, and acceptance by both DFA trace oracles. "
			"Medians are primitive actions and wall-clock seconds; the All row is "
			"pooled across all bound queries.}",
			"\\label{tab:profile-results}",
			"\\end{table}",
		],
	)
	return "\n".join(lines) + "\n"


def write_result_files(result: dict[str, Any], *, output_dir: str | Path) -> None:
	"""Write deterministic machine-readable and LaTeX result files."""

	root = Path(output_dir).expanduser().resolve()
	root.mkdir(parents=True, exist_ok=True)
	(root / "result_macros.tex").write_text(
		render_result_macros(result),
		encoding="utf-8",
	)
	(root / "result_domain_table.tex").write_text(
		render_domain_table(result),
		encoding="utf-8",
	)
	(root / "result_profile_table.tex").write_text(
		render_profile_table(result),
		encoding="utf-8",
	)
	(root / "evaluation_results.json").write_text(
		json.dumps(result, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)


def _load_conformance_result(root: Path) -> dict[str, Any]:
	manifest = _read_json(root / "manifest.json")
	for filename, expected_sha256 in dict(manifest.get("files") or {}).items():
		_require_equal(
			_sha256(root / str(filename)),
			expected_sha256,
			f"conformance fixture hash mismatch: {filename}",
		)
	release_record = dict(manifest.get("release_validation") or {})
	release_file = root / str(release_record.get("filename") or "")
	_require_equal(
		_sha256(release_file),
		release_record.get("sha256"),
		"conformance result hash mismatch",
	)
	result = _read_json(release_file)
	source_revision = dict(result.get("source_revision") or {})
	if source_revision.get("tracked_changes") is not False:
		raise ValueError("conformance artifact has tracked source changes")
	if len(str(source_revision.get("commit") or "")) < 8:
		raise ValueError("conformance artifact has no pinned source commit")
	if result.get("success") is not True:
		raise ValueError("conformance artifact is not successful")
	records = tuple(result.get("records") or ())
	if any(record.get("success") is not True for record in records):
		raise ValueError("conformance artifact contains a failed record")
	_require_equal(
		len(records),
		result.get("success_count"),
		"conformance success count mismatch",
	)
	_require_equal(
		result.get("suite_sha256"),
		dict(manifest.get("files") or {}).get("suite.json"),
		"conformance suite hash mismatch",
	)
	semantic_records = tuple(
		record for record in records if record.get("kind") == "finite_trace_semantics"
	)
	zero_action_records = tuple(
		record for record in records if record.get("kind") == "zero_action_end_to_end"
	)
	_require_equal(
		len(semantic_records),
		result.get("semantic_case_count"),
		"conformance semantic-case count mismatch",
	)
	_require_equal(
		len(zero_action_records),
		result.get("zero_action_case_count"),
		"conformance zero-action count mismatch",
	)
	_require_equal(
		len(records),
		len(semantic_records) + len(zero_action_records),
		"conformance record kind mismatch",
	)
	return {
		"run_id": result.get("run_id"),
		"source_commit": source_revision.get("commit"),
		"result_sha256": _sha256(release_file),
		"suite_sha256": result.get("suite_sha256"),
		"semantic_case_count": len(semantic_records),
		"semantic_success_count": sum(
			1 for record in semantic_records if record.get("success") is True
		),
		"zero_action_case_count": len(zero_action_records),
		"zero_action_success_count": sum(
			1 for record in zero_action_records if record.get("success") is True
		),
	}


def _case_index(benchmark: dict[str, Any]) -> dict[str, dict[str, Any]]:
	index: dict[str, dict[str, Any]] = {}
	for domain_payload in dict(benchmark.get("domains") or {}).values():
		for sample_id, case in dict(domain_payload.get("cases") or {}).items():
			if sample_id in index:
				raise ValueError(f"duplicate benchmark sample id: {sample_id}")
			index[str(sample_id)] = dict(case)
	return index


def _assert_module_closure(domain: str, synthesis: dict[str, Any]) -> None:
	for role in tuple(synthesis.get("predicate_roles") or ()):
		if role.get("expected_module") and not role.get("emitted_module"):
			raise ValueError(
				f"atomic module closure failed for {domain}:{role.get('predicate')}",
			)


def _execution_failure_categories(row: dict[str, Any]) -> Iterable[str]:
	validation = dict(row.get("execution_validation") or {})
	if row.get("status") == "controller_compile_failed":
		yield "controller_compile_failed"
	if row.get("jason_status") == "timeout":
		yield "jason_timeout"
	elif row.get("jason_status") != "success":
		yield "jason_failure"
	if validation.get("val_attempted") is True and validation.get("val_success") is not True:
		yield "val_failure"
	if validation.get("gold_accepted") is False:
		yield "gold_dfa_rejection"
	if validation.get("prediction_accepted") is False:
		yield "prediction_dfa_rejection"


def _end_to_end_success(row: dict[str, Any]) -> bool:
	return (
		row.get("success") is True
		and _jason_success(row)
		and _val_success(row)
		and _gold_accepted(row)
		and _prediction_accepted(row)
	)


def _jason_success(row: dict[str, Any]) -> bool:
	return row.get("jason_status") == "success"


def _val_success(row: dict[str, Any]) -> bool:
	validation = dict(row.get("execution_validation") or {})
	return validation.get("val_attempted") is True and validation.get("val_success") is True


def _gold_accepted(row: dict[str, Any]) -> bool:
	return dict(row.get("execution_validation") or {}).get("gold_accepted") is True


def _prediction_accepted(row: dict[str, Any]) -> bool:
	return dict(row.get("execution_validation") or {}).get("prediction_accepted") is True


def _prediction_accepted_by_schema(row: dict[str, Any]) -> bool:
	return row.get("outcome") == "accepted" and isinstance(row.get("prediction"), dict)


def _translation_equivalent(row: dict[str, Any]) -> bool:
	return row.get("success") is True and row.get("status") == "semantically_equivalent"


def _count(rows: Iterable[dict[str, Any]], predicate: Any) -> int:
	return sum(1 for row in rows if predicate(row))


def _median(values: Iterable[object]) -> float:
	numeric = [float(value) for value in values if value is not None]
	if not numeric:
		return 0.0
	return float(statistics.median(numeric))


def _parse_datetime(value: str) -> datetime:
	try:
		return datetime.fromisoformat(value)
	except ValueError as error:
		raise ValueError(f"invalid execution timestamp: {value}") from error


def _read_json(path: Path) -> dict[str, Any]:
	try:
		return json.loads(path.read_text(encoding="utf-8"))
	except (OSError, json.JSONDecodeError) as error:
		raise ValueError(f"cannot read JSON artifact {path}: {error}") from error


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
	try:
		return [
			json.loads(line)
			for line in path.read_text(encoding="utf-8").splitlines()
			if line.strip()
		]
	except (OSError, json.JSONDecodeError) as error:
		raise ValueError(f"cannot read JSONL artifact {path}: {error}") from error


def _sha256(path: Path) -> str:
	try:
		return hashlib.sha256(path.read_bytes()).hexdigest()
	except OSError as error:
		raise ValueError(f"cannot hash artifact {path}: {error}") from error


def certify_benchmark_compatibility(
	*,
	benchmark: dict[str, Any],
	current_benchmark_sha256: str,
	execution_benchmark_sha256: str,
	compatibility_file: str | Path | None,
) -> str | None:
	"""Prove that a benchmark hash change is confined to release provenance."""

	if execution_benchmark_sha256 == current_benchmark_sha256:
		return None
	if compatibility_file is None:
		_require_equal(
			execution_benchmark_sha256,
			current_benchmark_sha256,
			"execution benchmark hash mismatch",
		)
	compatibility_path = Path(compatibility_file).expanduser().resolve()
	record = _read_json(compatibility_path)
	_require_equal(
		record.get("artifact_kind"),
		"benchmark_provenance_compatibility",
		"unsupported benchmark compatibility artifact",
	)
	_require_equal(record.get("schema_version"), 1, "compatibility schema mismatch")
	_require_equal(
		record.get("serialization"),
		"json_indent_2_sort_keys_true_newline",
		"unsupported benchmark serialization",
	)
	_require_equal(
		record.get("current_benchmark_sha256"),
		current_benchmark_sha256,
		"compatibility current benchmark hash mismatch",
	)
	_require_equal(
		record.get("execution_benchmark_sha256"),
		execution_benchmark_sha256,
		"compatibility execution benchmark hash mismatch",
	)
	_require_equal(
		_json_payload_sha256(benchmark),
		current_benchmark_sha256,
		"current benchmark is not canonically serialized",
	)

	reconstructed = deepcopy(benchmark)
	replacements = tuple(record.get("replacements") or ())
	if not replacements:
		raise ValueError("benchmark compatibility contains no provenance replacement")
	seen_pointers: set[str] = set()
	for raw_replacement in replacements:
		if not isinstance(raw_replacement, dict):
			raise ValueError("benchmark compatibility replacement must be an object")
		pointer = str(raw_replacement.get("json_pointer") or "")
		if pointer in seen_pointers:
			raise ValueError(f"duplicate benchmark compatibility pointer: {pointer}")
		seen_pointers.add(pointer)
		_replace_provenance_pointer(
			reconstructed,
			pointer=pointer,
			current_value=raw_replacement.get("current_value"),
			execution_value=raw_replacement.get("execution_value"),
		)
	_require_equal(
		_json_payload_sha256(reconstructed),
		execution_benchmark_sha256,
		"compatibility replacements do not reconstruct the execution benchmark",
	)
	return "release_provenance_replacement_v1"


def _replace_provenance_pointer(
	payload: dict[str, Any],
	*,
	pointer: str,
	current_value: object,
	execution_value: object,
) -> None:
	parts = tuple(
		part.replace("~1", "/").replace("~0", "~")
		for part in pointer.split("/")[1:]
	)
	if len(parts) < 2 or parts[0] != "provenance":
		raise ValueError(
			"benchmark compatibility may replace provenance fields only: "
			f"{pointer}",
		)
	target: dict[str, Any] = payload
	for part in parts[:-1]:
		child = target.get(part)
		if not isinstance(child, dict):
			raise ValueError(f"benchmark compatibility pointer is missing: {pointer}")
		target = child
	leaf = parts[-1]
	if leaf not in target:
		raise ValueError(f"benchmark compatibility pointer is missing: {pointer}")
	_require_equal(
		target[leaf],
		current_value,
		f"benchmark compatibility current value mismatch at {pointer}",
	)
	target[leaf] = deepcopy(execution_value)


def _json_payload_sha256(payload: object) -> str:
	serialized = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
	return hashlib.sha256(serialized).hexdigest()


def _require_equal(observed: object, expected: object, message: str) -> None:
	if observed != expected:
		raise ValueError(f"{message}: expected {expected!r}, observed {observed!r}")


def _format_macro_value(value: object) -> str:
	if isinstance(value, bool):
		return "true" if value else "false"
	if isinstance(value, int):
		return f"{value:,}"
	if isinstance(value, float):
		if value.is_integer():
			return f"{int(value):,}"
		return f"{value:,.1f}"
	return str(value).replace("_", "\\_")


def _format_number(value: object) -> str:
	number = float(value)
	return str(int(number)) if number.is_integer() else f"{number:.1f}"


def _domain_label(value: object) -> str:
	return str(value).replace("_", "\\_")


def _profile_label(value: object) -> str:
	labels = {
		"ordered_two_milestone": "Ordered-2",
		"ordered_three_milestone": "Ordered-3",
		"persistence_until": "Strong Until",
		"same_state_conjunction": "Conjunction",
		"same_state_with_negation": "Conj.+negation",
	}
	return labels.get(str(value), str(value).replace("_", "\\_"))


if __name__ == "__main__":
	main()
