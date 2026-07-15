#!/usr/bin/env python3
"""Freeze complete external-reference matrices into portable paper artifacts."""

from __future__ import annotations

import argparse
from collections import Counter
from collections import defaultdict
import hashlib
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
from scripts.generate_aaai_comparison_tables import (  # noqa: E402
	_validate_achievement_toolchain,
)
from scripts.generate_aaai_comparison_tables import _validate_case_set  # noqa: E402
from scripts.generate_aaai_comparison_tables import _validate_clean_success  # noqa: E402
from scripts.generate_aaai_comparison_tables import (  # noqa: E402
	_validate_direct_temporal_toolchain,
)
from scripts.generate_aaai_comparison_tables import (  # noqa: E402
	_validate_external_reference_protocol,
)
from scripts.generate_aaai_comparison_tables import (  # noqa: E402
	_validate_infrastructure_repair,
)
from scripts.generate_aaai_comparison_tables import (  # noqa: E402
	_validate_published_moose_reference,
)
from scripts.generate_aaai_comparison_tables import render_external_table  # noqa: E402


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
	"sha256": "3b3d38e19e5e885c3ad15658baf77a26a1aad6cc8a369dfc1284c653a4e385ec",
}
LAMA_CONTRACT = {
	"count": 868,
	"sha256": "c8f110be1c7ea0c339a6d82c0bf81d11d89a376383d2083251e582053903fd93",
}
MRPHJ_CONTRACT = {
	"count": 360,
	"sha256": "ab2effc2380ae2b3cd0a0d20b6638dd1a0711c01bb5fe1efbf619603a5320324",
}
TEMPORAL_CONTRACT = {
	"count": 1228,
	"sha256": "55aeb7ea6137d802a0a69552bc01959c33be5aa0652cf8eb69bd2637b19d7a40",
}
TEMPORAL_BENCHMARK_SHA256 = (
	"ee94775ba695492d8d31242e6271afe14e5fa00cad29b910159737766d384e13"
)
REPAIR_CONTRACTS = {
	"achievement": {
		"count": 9,
		"sha256": "540d406302160a3ca075cf1344b0d9a546746199c4c96040899e7a2bfd0cf934",
	},
	"direct_temporal": {
		"count": 46,
		"sha256": "68d1aa65b26b12d27168c5a94d286922d2735779f5329600a3860ebbb5dcc33f",
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
	_validate_infrastructure_repair(
		instance,
		label="instance references",
		direct_temporal=False,
	)
	_validate_infrastructure_repair(
		direct,
		label="direct temporal reference",
		direct_temporal=True,
	)
	_validate_repair_contract(instance, kind="achievement")
	_validate_repair_contract(direct, kind="direct_temporal")
	_validate_external_reference_protocol(
		instance,
		label="instance references",
		expected_num_workers=REGISTERED_REMOTE_REFERENCE_NUM_WORKERS,
	)
	_validate_achievement_toolchain(instance, label="instance references")
	_validate_external_reference_protocol(
		direct,
		label="direct temporal reference",
		direct_temporal=True,
		expected_num_workers=REGISTERED_REMOTE_REFERENCE_NUM_WORKERS,
	)
	moose_toolchain = dict(dict(instance.get("toolchain") or {}).get("moose") or {})
	moose_artifact_sha256 = str(moose_toolchain.get("artifact_sha256") or "")
	_validate_direct_temporal_toolchain(
		direct,
		expected_moose_artifact_hash=moose_artifact_sha256,
	)
	if str(dict(raw_moose.get("toolchain") or {}).get("artifact_sha256") or "") != (
		moose_artifact_sha256
	):
		raise ValueError("Raw MOOSE and external references use different artifacts")

	_validate_achievement_case_sets(instance)
	_validate_temporal_case_set(
		direct,
		benchmark=benchmark,
		benchmark_path=benchmark_path,
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
			"temporal": {
				**TEMPORAL_CONTRACT,
				"benchmark_sha256": TEMPORAL_BENCHMARK_SHA256,
			},
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
		"provenance": {
			"instance_summary_sha256": _sha256(instance_path),
			"direct_summary_sha256": _sha256(direct_path),
			"raw_moose_result_sha256": _sha256(raw_path),
			"published_reference_sha256": _sha256(published_path),
			"benchmark_sha256": _sha256(benchmark_path),
			"instance_source_revision": dict(instance.get("source_revision") or {}),
			"direct_source_revision": dict(direct.get("source_revision") or {}),
			"instance_infrastructure_repair": dict(
				instance.get("infrastructure_repair") or {},
			),
			"direct_infrastructure_repair": dict(
				direct.get("infrastructure_repair") or {},
			),
			"achievement_toolchain": _portable_achievement_toolchain(instance),
			"direct_temporal_toolchain": _portable_direct_toolchain(direct),
		},
		"records": records,
	}
	serialized = json.dumps(result, sort_keys=True)
	if "/Users/" in serialized:
		raise ValueError("portable external result contains a machine-local path")
	return result


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


def _validate_repair_contract(payload: Mapping[str, Any], *, kind: str) -> None:
	repair = dict(payload.get("infrastructure_repair") or {})
	contract = REPAIR_CONTRACTS[kind]
	if (
		int(repair.get("replaced_case_count") or 0) != int(contract["count"])
		or str(repair.get("replaced_case_set_sha256") or "")
		!= str(contract["sha256"])
	):
		raise ValueError(f"{kind} infrastructure repair contract mismatch")


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
	benchmark_path: Path,
) -> None:
	if _sha256(benchmark_path) != TEMPORAL_BENCHMARK_SHA256:
		raise ValueError("registered temporal benchmark file changed")
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
	if (
		str(payload.get("benchmark_sha256") or "") != TEMPORAL_BENCHMARK_SHA256
		or int(payload.get("selected_case_count") or 0) != TEMPORAL_CONTRACT["count"]
	):
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
		"domain_sha256": str(record.get("domain_sha256") or ""),
		"problem_sha256": str(record.get("problem_sha256") or ""),
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
		"domain_sha256": str(record.get("domain_sha256") or ""),
		"problem_sha256": str(record.get("problem_sha256") or ""),
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
		"primary_run_id": str(retry.get("primary_run_id") or ""),
		"retry_run_id": str(retry.get("retry_run_id") or ""),
		"retry_num_workers": int(retry.get("retry_num_workers") or 0),
	}


def _portable_achievement_toolchain(payload: Mapping[str, Any]) -> dict[str, Any]:
	toolchain = dict(payload.get("toolchain") or {})
	moose = dict(toolchain.get("moose") or {})
	enhsp = dict(toolchain.get("enhsp") or {})
	return {
		"moose": {
			"artifact_sha256": str(moose.get("artifact_sha256") or ""),
			"docker_image": str(moose.get("docker_image") or ""),
			"docker_image_id": str(moose.get("docker_image_id") or ""),
			"git_revision": str(moose.get("git_revision") or ""),
		},
		"enhsp": {
			"configuration": str(enhsp.get("configuration") or ""),
			"git_revision": str(enhsp.get("git_revision") or ""),
			"jar_sha256": str(enhsp.get("jar_sha256") or ""),
		},
	}


def _portable_direct_toolchain(payload: Mapping[str, Any]) -> dict[str, Any]:
	toolchain = dict(payload.get("toolchain") or {})
	fond = dict(toolchain.get("fond4ltlf") or {})
	mona = dict(toolchain.get("mona") or {})
	lama = dict(toolchain.get("lama") or {})
	return {
		"fond4ltlf": {
			"git_revision": str(fond.get("git_revision") or ""),
			"release": str(fond.get("release") or ""),
			"executable_sha256": str(fond.get("executable_sha256") or ""),
			"isolation_wrapper_sha256": str(
				fond.get("isolation_wrapper_sha256") or "",
			),
		},
		"mona": {
			"version": str(mona.get("version") or ""),
			"executable_sha256": str(mona.get("executable_sha256") or ""),
		},
		"lama": {
			"moose_artifact_sha256": str(
				lama.get("moose_artifact_sha256") or "",
			),
			"moose_git_revision": str(lama.get("moose_git_revision") or ""),
			"docker_image": str(lama.get("docker_image") or ""),
		},
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
	manifest["files"] = {
		str(path.relative_to(release_root)): _sha256(path)
		for path in sorted(release_root.rglob("*"))
		if path.is_file() and path != manifest_path
	}
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


def _sha256(path: Path) -> str:
	return hashlib.sha256(path.read_bytes()).hexdigest()


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
