#!/usr/bin/env python3
"""Freeze complete external-reference matrices into portable paper artifacts."""

from __future__ import annotations

import argparse
from collections import Counter
from collections import defaultdict
import json
from pathlib import Path
import statistics
import sys
from typing import Any
from typing import Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_aaai_comparison_tables import (  # noqa: E402
	REGISTERED_MAX_RSS_GB,
)
from scripts.generate_aaai_comparison_tables import (  # noqa: E402
	REGISTERED_REMOTE_REFERENCE_NUM_WORKERS,
)
from scripts.generate_aaai_comparison_tables import (  # noqa: E402
	REGISTERED_TIMEOUT_SECONDS,
)
from scripts.generate_aaai_comparison_tables import _direct_temporal_valid  # noqa: E402
from scripts.generate_aaai_comparison_tables import _external_row  # noqa: E402
from scripts.generate_aaai_comparison_tables import _validate_case_set  # noqa: E402
from scripts.generate_aaai_comparison_tables import _validate_clean_success  # noqa: E402
from scripts.generate_aaai_comparison_tables import (  # noqa: E402
	_validate_external_reference_protocol,
)
from scripts.generate_aaai_comparison_tables import (  # noqa: E402
	_validate_published_moose_reference,
)
from scripts.generate_aaai_comparison_tables import render_external_table  # noqa: E402
from scripts.public_result_schema import outcome_only_payload  # noqa: E402


DEFAULT_INSTANCE_SUMMARY = (
	PROJECT_ROOT
	/ "artifacts/external_planning_references/"
	/ "aaai-instance-references-72b0604f/summary.json"
)
DEFAULT_DIRECT_SUMMARY = (
	PROJECT_ROOT
	/ "artifacts/direct_temporal_references/"
	/ "aaai-direct-temporal-72b0604f/summary.json"
)
DEFAULT_RAW_MOOSE_RESULT = (
	PROJECT_ROOT
	/ "paper_artifacts/gp2pl_evaluation/v1/"
	/ "raw_moose_extension_five_seed_summary.json"
)
DEFAULT_PUBLISHED_REFERENCE = (
	PROJECT_ROOT
	/ "paper_artifacts/gp2pl_evaluation/v1/moose_published_reference.json"
)
DEFAULT_BENCHMARK = (
	PROJECT_ROOT / "paper_artifacts/temporal_goal_benchmark/v1/benchmark.json"
)
DEFAULT_OUTPUT_JSON = (
	PROJECT_ROOT
	/ "paper_artifacts/gp2pl_evaluation/v1/external_reference_results.json"
)
DEFAULT_LATEX_OUTPUT_DIR = PROJECT_ROOT / "latex_code/aamas_method_paper/sections"

ACHIEVEMENT_UNION_CONTRACT = {
	"count": 1228,
}
LAMA_CONTRACT = {
	"count": 868,
}
MRPHJ_CONTRACT = {
	"count": 360,
}
TEMPORAL_CONTRACT = {
	"count": 1228,
}
REPAIR_CONTRACTS = {
	"achievement": {
		"count": 9,
	},
	"direct_temporal": {
		"count": 46,
	},
}


def build_external_reference_dataset(
	*,
	instance_summary_file: str | Path,
	direct_summary_file: str | Path,
	raw_moose_result_file: str | Path,
	published_reference_file: str | Path,
	benchmark_file: str | Path,
) -> dict[str, Any]:
	"""Validate complete external matrices and return one portable result dataset."""

	instance_path = Path(instance_summary_file).expanduser().resolve()
	direct_path = Path(direct_summary_file).expanduser().resolve()
	raw_path = Path(raw_moose_result_file).expanduser().resolve()
	published_path = Path(published_reference_file).expanduser().resolve()
	benchmark_path = Path(benchmark_file).expanduser().resolve()
	instance = _read_json(instance_path)
	direct = _read_json(direct_path)
	raw_moose = _read_json(raw_path)
	published = _read_json(published_path)
	benchmark = _read_json(benchmark_path)

	_validate_published_moose_reference(published)
	_validate_raw_moose_result(raw_moose)
	_validate_clean_success(instance, label="instance references")
	_validate_clean_success(direct, label="direct temporal reference")
	_validate_external_reference_protocol(
		instance,
		label="instance references",
		expected_num_workers=REGISTERED_REMOTE_REFERENCE_NUM_WORKERS,
	)
	_validate_external_reference_protocol(
		direct,
		label="direct temporal reference",
		direct_temporal=True,
		expected_num_workers=REGISTERED_REMOTE_REFERENCE_NUM_WORKERS,
	)

	_validate_achievement_case_sets(instance)
	_validate_temporal_case_set(
		direct,
		benchmark=benchmark,
	)
	rows = _external_rows(
		instance=instance,
		direct=direct,
		raw_moose=raw_moose,
		published=published,
	)
	records = sorted(
		(
			*(
				_portable_achievement_record(record)
				for record in instance.get("results") or ()
			),
			*(
				_portable_direct_record(record)
				for record in direct.get("results") or ()
			),
		),
		key=lambda record: (
			str(record["record_kind"]),
			str(record["case_id"]),
		),
	)
	if len(records) != 2456:
		raise ValueError(f"portable external record count mismatch: {len(records)}")
	result = {
		"artifact_kind": "gp2pl_external_reference_results",
		"schema_version": 1,
		"protocol": {
			"achievement_case_count": ACHIEVEMENT_UNION_CONTRACT["count"],
			"temporal_case_count": TEMPORAL_CONTRACT["count"],
			"record_count": len(records),
			"primary_num_workers": REGISTERED_REMOTE_REFERENCE_NUM_WORKERS,
			"repair_num_workers": 1,
			"timeout_seconds": REGISTERED_TIMEOUT_SECONDS,
			"max_rss_gb": REGISTERED_MAX_RSS_GB,
			"plan_verifier_timeout_seconds": REGISTERED_TIMEOUT_SECONDS,
			"hardware_equivalence_confirmed_by_experiment_owner": True,
			"runtime_measurement_excludes_queue_wait": True,
			"par2_allowed_methods": ["LAMA", "MRP+HJ", "FOND4LTLf + LAMA"],
			"raw_moose_runtime_comparison_allowed": False,
		},
		"case_contracts": {
			"achievement_union": dict(ACHIEVEMENT_UNION_CONTRACT),
			"lama": dict(LAMA_CONTRACT),
			"enhsp_hmrphj": dict(MRPHJ_CONTRACT),
			"temporal": dict(TEMPORAL_CONTRACT),
			"achievement_repair": dict(REPAIR_CONTRACTS["achievement"]),
			"direct_temporal_repair": dict(REPAIR_CONTRACTS["direct_temporal"]),
		},
		"rows": rows,
		"status_counts": {
			"achievement": dict(
				sorted(
					Counter(
						str(record.get("status") or "")
						for record in instance.get("results") or ()
					).items(),
				),
			),
			"direct_temporal": dict(
				sorted(
					Counter(
						str(record.get("status") or "")
						for record in direct.get("results") or ()
					).items(),
				),
			),
		},
		"records": records,
	}
	serialized = json.dumps(result, sort_keys=True)
	if "/Users/" in serialized:
		raise ValueError("portable external result contains a machine-local path")
	return outcome_only_payload(result)


def _validate_raw_moose_result(payload: Mapping[str, Any]) -> None:
	if payload.get("artifact_kind") != "gp2pl_raw_moose_extension_five_seed_result":
		raise ValueError("unexpected Raw MOOSE extension artifact")
	protocol = dict(payload.get("protocol") or {})
	if (
		int(protocol.get("record_count") or 0) != 740
		or int(protocol.get("case_count_per_seed") or 0) != 148
		or int(protocol.get("num_workers") or 0) != 6
		or protocol.get("runtime_comparison_allowed") is not False
	):
		raise ValueError("Raw MOOSE extension protocol mismatch")
	records = tuple(payload.get("records") or ())
	if len(records) != 740 or len(
		{
			(int(record.get("seed") or 0), str(record.get("case_id") or ""))
			for record in records
		},
	) != 740:
		raise ValueError("Raw MOOSE extension records are incomplete or duplicated")
	aggregate = dict(payload.get("aggregate") or {})
	if (
		int(aggregate.get("pooled_valid_count") or 0) != 117
		or int(aggregate.get("pooled_evaluation_count") or 0) != 740
	):
		raise ValueError("Raw MOOSE extension aggregate mismatch")


def _validate_achievement_case_sets(payload: Mapping[str, Any]) -> None:
	by_method: dict[str, list[str]] = defaultdict(list)
	for record in payload.get("results") or ():
		by_method[str(record.get("method") or "")].append(
			f"{record.get('domain')}:{Path(str(record.get('problem_file') or '')).name}",
		)
	if set(by_method) != {"LAMA", "MRP+HJ"}:
		raise ValueError("external achievement methods are incomplete")
	_validate_case_set(by_method["LAMA"], contract=LAMA_CONTRACT, label="LAMA case set")
	_validate_case_set(
		by_method["MRP+HJ"],
		contract=MRPHJ_CONTRACT,
		label="MRP+HJ case set",
	)
	_validate_case_set(
		[*by_method["LAMA"], *by_method["MRP+HJ"]],
		contract=ACHIEVEMENT_UNION_CONTRACT,
		label="achievement union case set",
	)


def _validate_temporal_case_set(
	payload: Mapping[str, Any],
	*,
	benchmark: Mapping[str, Any],
) -> None:
	benchmark_ids = [
		str(sample_id)
		for domain in dict(benchmark.get("domains") or {}).values()
		for sample_id in dict(dict(domain).get("cases") or {})
	]
	_validate_case_set(
		benchmark_ids,
		contract=TEMPORAL_CONTRACT,
		label="benchmark temporal case set",
	)
	result_ids = [
		str(record.get("sample_id") or "") for record in payload.get("results") or ()
	]
	_validate_case_set(
		result_ids,
		contract=TEMPORAL_CONTRACT,
		label="direct temporal case set",
	)
	if set(result_ids) != set(benchmark_ids):
		raise ValueError("direct temporal case identifiers differ from the benchmark")
	if int(payload.get("selected_case_count") or 0) != TEMPORAL_CONTRACT["count"]:
		raise ValueError("direct temporal benchmark identity changed")


def _external_rows(
	*,
	instance: Mapping[str, Any],
	direct: Mapping[str, Any],
	raw_moose: Mapping[str, Any],
	published: Mapping[str, Any],
) -> list[dict[str, Any]]:
	published_results = dict(published.get("published_results") or {})
	raw_protocol = dict(raw_moose.get("protocol") or {})
	raw_aggregate = dict(raw_moose.get("aggregate") or {})
	rows = [
		{
			"method": "MOOSE",
			"source": "Reported",
			"scope": "Original MOOSE domains, five seeds",
			"case_count": int(published_results.get("case_count_per_seed") or 0),
			"supported_case_count": int(
				published_results.get("case_count_per_seed") or 0,
			),
			"unsupported_case_count": 0,
			"valid_trace_count": float(
				published_results.get("mean_solved_count") or 0.0,
			),
			"seed_count": int(published_results.get("seed_count") or 0),
			"par2_seconds": None,
		},
		{
			"method": "Raw MOOSE extension",
			"source": "Measured",
			"scope": "Added domains, five seeds",
			"case_count": int(raw_protocol.get("case_count_per_seed") or 0),
			"supported_case_count": int(raw_protocol.get("case_count_per_seed") or 0),
			"unsupported_case_count": 0,
			"valid_trace_count": float(raw_aggregate.get("mean_valid_count") or 0.0),
			"seed_count": 5,
			"coverage_sample_sd": float(
				raw_aggregate.get("sample_sd_valid_count") or 0.0,
			),
			"par2_seconds": None,
		},
	]
	instance_by_method: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
	for record in instance.get("results") or ():
		instance_by_method[str(record.get("method") or "")].append(record)
	rows.extend(
		_external_row(method, scope, instance_by_method[method])
		for method, scope in (
			("LAMA", "Classical achievement"),
			("MRP+HJ", "Numeric achievement"),
		)
	)
	direct_records = tuple(dict(record) for record in direct.get("results") or ())
	supported = [record for record in direct_records if record.get("supported") is True]
	valid = [record for record in supported if _direct_temporal_valid(record)]
	rows.append(
		{
			"method": "FOND4LTLf + LAMA",
			"source": "Measured",
			"scope": "Supported Boolean TEG",
			"case_count": len(supported),
			"supported_case_count": len(supported),
			"unsupported_case_count": len(direct_records) - len(supported),
			"valid_trace_count": len(valid),
			"par2_seconds": statistics.mean(
				float(record.get("elapsed_seconds") or 0.0)
				if _direct_temporal_valid(record)
				else float(2 * REGISTERED_TIMEOUT_SECONDS)
				for record in supported
			),
		},
	)
	return rows


def _portable_achievement_record(record: Mapping[str, Any]) -> dict[str, Any]:
	return {
		"record_kind": "achievement",
		"case_id": (
			f"{record.get('domain')}:"
			f"{Path(str(record.get('problem_file') or '')).name}"
		),
		"method": str(record.get("method") or ""),
		"variant": str(record.get("variant") or ""),
		"domain": str(record.get("domain") or ""),
		"status": str(record.get("status") or ""),
		"valid": record.get("plan_verifier_success") is True,
		"action_count": int(record.get("action_count") or 0),
		"elapsed_seconds": float(record.get("elapsed_seconds") or 0.0),
		"runtime_lock_wait_seconds": float(
			record.get("runtime_lock_wait_seconds") or 0.0,
		),
		"planner_exit_code": record.get("planner_exit_code"),
		"infrastructure_retry": _portable_retry(record),
	}


def _portable_direct_record(record: Mapping[str, Any]) -> dict[str, Any]:
	validation = dict(record.get("execution_validation") or {})
	return {
		"record_kind": "direct_temporal",
		"case_id": str(record.get("sample_id") or ""),
		"sample_id": str(record.get("sample_id") or ""),
		"method": str(record.get("method") or ""),
		"variant": str(record.get("variant") or ""),
		"domain": str(record.get("domain") or ""),
		"profile": str(record.get("profile") or ""),
		"grounded_formula": str(record.get("grounded_formula") or ""),
		"status": str(record.get("status") or ""),
		"supported": record.get("supported") is True,
		"valid": _direct_temporal_valid(record),
		"action_count": int(record.get("action_count") or 0),
		"compiled_action_count": int(record.get("compiled_action_count") or 0),
		"elapsed_seconds": float(record.get("elapsed_seconds") or 0.0),
		"compiler_seconds": float(record.get("compiler_seconds") or 0.0),
		"planner_seconds": float(record.get("planner_seconds") or 0.0),
		"compiler_lock_wait_seconds": float(
			record.get("compiler_lock_wait_seconds") or 0.0,
		),
		"runtime_lock_wait_seconds": float(
			record.get("runtime_lock_wait_seconds") or 0.0,
		),
		"execution_validation": {
			"val_attempted": validation.get("val_attempted"),
			"val_success": validation.get("val_success"),
			"replay_valid": validation.get("replay_valid"),
			"gold_accepted": validation.get("gold_accepted"),
			"prediction_accepted": validation.get("prediction_accepted"),
			"state_count": validation.get("state_count"),
			"legality_certificate": validation.get("legality_certificate"),
		},
		"infrastructure_retry": _portable_retry(record),
	}


def _portable_retry(record: Mapping[str, Any]) -> dict[str, Any] | None:
	retry = record.get("infrastructure_retry")
	if not isinstance(retry, Mapping):
		return None
	return {
		"primary_status": str(retry.get("primary_status") or ""),
		"primary_elapsed_seconds": float(
			retry.get("primary_elapsed_seconds") or 0.0,
		),
		"retry_num_workers": int(retry.get("retry_num_workers") or 0),
	}


def render_external_reference_macros(result: Mapping[str, Any]) -> str:
	"""Render manuscript prose values from the frozen external rows."""

	rows = {str(row["method"]): dict(row) for row in result["rows"]}
	lama = rows["LAMA"]
	mrphj = rows["MRP+HJ"]
	direct = rows["FOND4LTLf + LAMA"]
	contracts = dict(result["case_contracts"])
	achievement_repair_count = int(dict(contracts["achievement_repair"])["count"])
	direct_repair_count = int(dict(contracts["direct_temporal_repair"])["count"])
	return "\n".join(
		(
			"% Auto-generated by scripts/freeze_external_reference_results.py.",
			"\\newcommand{\\ExternalAchievementValidCount}"
			f"{{{lama['valid_trace_count'] + mrphj['valid_trace_count']}}}",
			"\\newcommand{\\ExternalAchievementCaseCount}"
			f"{{{lama['case_count'] + mrphj['case_count']}}}",
			f"\\newcommand{{\\ExternalLAMAValidCount}}{{{lama['valid_trace_count']}}}",
			f"\\newcommand{{\\ExternalLAMACaseCount}}{{{lama['case_count']}}}",
			f"\\newcommand{{\\ExternalLAMAParTwoSeconds}}{{{lama['par2_seconds']:.1f}}}",
			f"\\newcommand{{\\ExternalMRPHJValidCount}}{{{mrphj['valid_trace_count']}}}",
			f"\\newcommand{{\\ExternalMRPHJCaseCount}}{{{mrphj['case_count']}}}",
			f"\\newcommand{{\\ExternalMRPHJParTwoSeconds}}{{{mrphj['par2_seconds']:.1f}}}",
			f"\\newcommand{{\\ExternalDirectValidCount}}{{{direct['valid_trace_count']}}}",
			f"\\newcommand{{\\ExternalDirectSupportedCount}}{{{direct['supported_case_count']}}}",
			f"\\newcommand{{\\ExternalDirectUnsupportedCount}}{{{direct['unsupported_case_count']}}}",
			"\\newcommand{\\ExternalDirectTotalCaseCount}"
			f"{{{direct['supported_case_count'] + direct['unsupported_case_count']}}}",
			f"\\newcommand{{\\ExternalDirectParTwoSeconds}}{{{direct['par2_seconds']:.1f}}}",
			"\\newcommand{\\ExternalAchievementRepairCount}"
			f"{{{achievement_repair_count}}}",
			"\\newcommand{\\ExternalDirectRepairCount}"
			f"{{{direct_repair_count}}}",
		),
	) + "\n"


def write_result_files(
	result: Mapping[str, Any],
	*,
	output_json: str | Path,
	latex_output_dir: str | Path,
	update_manifest: bool,
) -> None:
	"""Write portable JSON, the external table, macros, and release manifest."""

	json_path = Path(output_json).expanduser().resolve()
	latex_root = Path(latex_output_dir).expanduser().resolve()
	json_path.parent.mkdir(parents=True, exist_ok=True)
	latex_root.mkdir(parents=True, exist_ok=True)
	_write_json(json_path, result)
	table = render_external_table({"external": result["rows"]}).replace(
		"% Auto-generated by scripts/generate_aaai_comparison_tables.py.",
		"% Auto-generated by scripts/freeze_external_reference_results.py.",
		1,
	)
	(latex_root / "result_external_reference_table.tex").write_text(
		table,
		encoding="utf-8",
	)
	(latex_root / "result_external_reference_macros.tex").write_text(
		render_external_reference_macros(result),
		encoding="utf-8",
	)
	if update_manifest:
		_update_release_manifest(json_path.parent, result=result)


def _update_release_manifest(
	release_root: Path,
	*,
	result: Mapping[str, Any],
) -> None:
	manifest_path = release_root / "manifest.json"
	manifest = _read_json(manifest_path)
	manifest["external_reference_record_count"] = int(
		dict(result["protocol"])["record_count"],
	)
	manifest["files"] = [
		str(path.relative_to(release_root))
		for path in sorted(release_root.rglob("*"))
		if path.is_file() and path != manifest_path
	]
	_write_json(manifest_path, manifest)


def _read_json(path: Path) -> dict[str, Any]:
	try:
		payload = json.loads(path.read_text(encoding="utf-8"))
	except (OSError, json.JSONDecodeError) as error:
		raise ValueError(f"Cannot read JSON artifact {path}: {error}") from error
	if not isinstance(payload, dict):
		raise ValueError(f"JSON artifact is not an object: {path}")
	return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(
		json.dumps(payload, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--instance-summary", type=Path, default=DEFAULT_INSTANCE_SUMMARY)
	parser.add_argument("--direct-summary", type=Path, default=DEFAULT_DIRECT_SUMMARY)
	parser.add_argument("--raw-moose-result", type=Path, default=DEFAULT_RAW_MOOSE_RESULT)
	parser.add_argument(
		"--published-reference",
		type=Path,
		default=DEFAULT_PUBLISHED_REFERENCE,
	)
	parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
	parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
	parser.add_argument(
		"--latex-output-dir",
		type=Path,
		default=DEFAULT_LATEX_OUTPUT_DIR,
	)
	parser.add_argument("--no-update-manifest", action="store_true")
	return parser.parse_args()


def main() -> int:
	args = parse_args()
	result = build_external_reference_dataset(
		instance_summary_file=args.instance_summary,
		direct_summary_file=args.direct_summary,
		raw_moose_result_file=args.raw_moose_result,
		published_reference_file=args.published_reference,
		benchmark_file=args.benchmark,
	)
	write_result_files(
		result,
		output_json=args.output_json,
		latex_output_dir=args.latex_output_dir,
		update_manifest=not args.no_update_manifest,
	)
	rows = {str(row["method"]): dict(row) for row in result["rows"]}
	print(
		"frozen external references "
		f"LAMA={rows['LAMA']['valid_trace_count']}/{rows['LAMA']['case_count']} "
		f"MRP+HJ={rows['MRP+HJ']['valid_trace_count']}/"
		f"{rows['MRP+HJ']['case_count']} "
		f"direct={rows['FOND4LTLf + LAMA']['valid_trace_count']}/"
		f"{rows['FOND4LTLf + LAMA']['supported_case_count']} "
		f"artifact={Path(args.output_json).expanduser().resolve()}",
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
