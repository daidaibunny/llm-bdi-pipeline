#!/usr/bin/env python3
"""Replace only infrastructure-failed external-reference cases with retries."""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
from typing import Mapping
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_direct_temporal_reference import (  # noqa: E402
	record_sort_key as direct_record_sort_key,
)
from scripts.run_direct_temporal_reference import (  # noqa: E402
	summarize_temporal_reference_records,
)
from scripts.run_external_planning_references import (  # noqa: E402
	is_infrastructure_failure,
)
from scripts.run_external_planning_references import (  # noqa: E402
	record_sort_key as achievement_record_sort_key,
)
from scripts.run_external_planning_references import summarize_records  # noqa: E402


KINDS = ("achievement", "direct_temporal")
PRIMARY_NUM_WORKERS = 20
RETRY_NUM_WORKERS = 1
TIMEOUT_SECONDS = 1800
MAX_RSS_GB = 8.0


def merge_infrastructure_retries(
	primary: Mapping[str, Any],
	retry: Mapping[str, Any],
	*,
	kind: str,
	primary_sha256: str,
	retry_sha256: str,
) -> dict[str, Any]:
	"""Merge an exact serial retry set into one complete primary summary."""

	if kind not in KINDS:
		raise ValueError(f"Unknown external-reference kind: {kind}")
	_validate_summary_hash(primary_sha256, label="primary")
	_validate_summary_hash(retry_sha256, label="retry")
	_validate_clean_revision(primary, label="primary")
	_validate_clean_revision(retry, label="retry")
	_validate_protocol(primary, kind=kind, num_workers=PRIMARY_NUM_WORKERS)
	_validate_protocol(retry, kind=kind, num_workers=RETRY_NUM_WORKERS)
	toolchain_verification = _validate_toolchain_pair(primary, retry, kind=kind)
	if kind == "direct_temporal" and primary.get("benchmark_sha256") != retry.get(
		"benchmark_sha256",
	):
		raise ValueError("direct temporal retry changes the benchmark fingerprint")

	primary_records = tuple(dict(record) for record in primary.get("results") or ())
	retry_records = tuple(dict(record) for record in retry.get("results") or ())
	primary_by_key = _index_records(primary_records, kind=kind, label="primary")
	retry_by_key = _index_records(retry_records, kind=kind, label="retry")
	infrastructure_keys = {
		key
		for key, record in primary_by_key.items()
		if is_infrastructure_failure(record.get("status"))
	}
	if not infrastructure_keys:
		raise ValueError("primary summary has no infrastructure failures to repair")
	if set(retry_by_key) != infrastructure_keys:
		raise ValueError(
			"retry case set does not exactly match primary infrastructure failures",
		)
	if any(
		is_infrastructure_failure(record.get("status"))
		for record in retry_by_key.values()
	):
		raise ValueError("retry summary still contains infrastructure failures")
	if retry.get("success") is not True or int(
		retry.get("infrastructure_failure_count") or 0,
	) != 0:
		raise ValueError("retry summary is not infrastructure-complete")
	observed_primary_failures = sum(
		is_infrastructure_failure(record.get("status"))
		for record in primary_records
	)
	if observed_primary_failures != int(
		primary.get("infrastructure_failure_count") or 0,
	):
		raise ValueError("primary infrastructure failure count is inconsistent")

	merged_by_key = dict(primary_by_key)
	for key in sorted(infrastructure_keys):
		primary_record = primary_by_key[key]
		retry_record = deepcopy(retry_by_key[key])
		_validate_input_fingerprint(primary_record, retry_record, kind=kind, key=key)
		retry_record["infrastructure_retry"] = {
			"primary_status": str(primary_record.get("status") or ""),
			"primary_elapsed_seconds": float(
				primary_record.get("elapsed_seconds") or 0.0,
			),
			"primary_run_id": str(primary.get("run_id") or ""),
			"primary_source_revision": dict(primary.get("source_revision") or {}),
			"retry_run_id": str(retry.get("run_id") or ""),
			"retry_source_revision": dict(retry.get("source_revision") or {}),
			"retry_num_workers": RETRY_NUM_WORKERS,
		}
		merged_by_key[key] = retry_record

	merged_records = _sort_records(merged_by_key.values(), kind=kind)
	remaining_failures = sum(
		is_infrastructure_failure(record.get("status"))
		for record in merged_records
	)
	if remaining_failures:
		raise ValueError("merged summary still contains infrastructure failures")
	merged = deepcopy(dict(primary))
	merged.update(
		{
			"finished_at": str(retry.get("finished_at") or ""),
			"results": merged_records,
			"infrastructure_failure_count": 0,
			"success": True,
			"source_revisions": [
				dict(primary.get("source_revision") or {}),
				dict(retry.get("source_revision") or {}),
			],
			"infrastructure_repair": {
				"strategy": "replace_exact_infrastructure_failures",
				"primary_summary_sha256": primary_sha256,
				"retry_summary_sha256": retry_sha256,
				"primary_run_id": str(primary.get("run_id") or ""),
				"retry_run_id": str(retry.get("run_id") or ""),
				"primary_source_revision": dict(
					primary.get("source_revision") or {},
				),
				"retry_source_revision": dict(retry.get("source_revision") or {}),
				"primary_num_workers": PRIMARY_NUM_WORKERS,
				"retry_num_workers": RETRY_NUM_WORKERS,
				"replaced_case_count": len(infrastructure_keys),
				"replaced_case_ids": sorted(infrastructure_keys),
				"replaced_case_set_sha256": _case_set_sha256(infrastructure_keys),
				"primary_status_counts": dict(
					sorted(
						Counter(
							str(primary_by_key[key].get("status") or "")
							for key in infrastructure_keys
						).items(),
					),
				),
				"input_fingerprints_verified": True,
				"toolchain_verified": True,
				"toolchain_verification": toolchain_verification,
				"resource_limits_verified": True,
				"hardware_equivalence_confirmed_by_experiment_owner": True,
				"runtime_measurement_excludes_queue_wait": True,
				"runtime_comparison_allowed": True,
			},
		}
	)
	if kind == "achievement":
		merged["metrics"] = summarize_records(
			merged_records,
			timeout_seconds=TIMEOUT_SECONDS,
		)
	else:
		merged["selected_case_count"] = len(merged_records)
		merged["metrics"] = summarize_temporal_reference_records(
			merged_records,
			timeout_seconds=TIMEOUT_SECONDS,
		)
	return merged


def _validate_protocol(
	summary: Mapping[str, Any],
	*,
	kind: str,
	num_workers: int,
) -> None:
	parameters = dict(summary.get("parameters") or {})
	if int(parameters.get("num_workers") or 0) != num_workers:
		raise ValueError(f"summary does not use {num_workers} workers")
	timeout_key = (
		"timeout_seconds_total_compile_and_plan"
		if kind == "direct_temporal"
		else "timeout_seconds"
	)
	if int(parameters.get(timeout_key) or 0) != TIMEOUT_SECONDS:
		raise ValueError("summary changes the registered timeout")
	if float(parameters.get("max_rss_gb") or 0.0) != MAX_RSS_GB:
		raise ValueError("summary changes the registered memory limit")
	if int(parameters.get("plan_verifier_timeout_seconds") or 0) != TIMEOUT_SECONDS:
		raise ValueError("summary changes the registered VAL timeout")
	if str(parameters.get("moose_runtime_backend") or "") != "sandbox":
		raise ValueError("summary does not use the isolated MOOSE sandbox")
	if str(parameters.get("moose_runtime_lock_scope") or "") != "none":
		raise ValueError("summary unexpectedly uses a MOOSE runtime lock")
	if int(parameters.get("moose_runtime_max_parallelism") or 0) != num_workers:
		raise ValueError("summary MOOSE parallelism does not match its worker count")
	if kind == "direct_temporal":
		if parameters.get("fond4ltlf_compiler_isolation") != (
			"per_case_mona_workspace"
		):
			raise ValueError("direct retry lacks per-case FOND4LTLf isolation")
		if str(parameters.get("fond4ltlf_compiler_lock_scope") or "") != "none":
			raise ValueError("direct retry unexpectedly uses a compiler lock")
		if int(parameters.get("fond4ltlf_compiler_max_parallelism") or 0) != (
			num_workers
		):
			raise ValueError("compiler parallelism does not match the worker count")


def _validate_toolchain_pair(
	primary: Mapping[str, Any],
	retry: Mapping[str, Any],
	*,
	kind: str,
) -> dict[str, Any]:
	primary_fingerprint = _toolchain_fingerprint(primary, kind=kind)
	retry_fingerprint = _toolchain_fingerprint(retry, kind=kind)
	if primary_fingerprint != retry_fingerprint:
		raise ValueError("retry changes the registered external toolchain")
	verification: dict[str, Any] = {
		"semantic_identity": (
			"exact_pinned_revisions_and_versions"
			if kind == "direct_temporal"
			else "exact_portable_artifact_hashes_and_revisions"
		),
		"semantic_identity_sha256": _mapping_sha256(primary_fingerprint),
		"path_embedded_launchers": {},
	}
	if kind != "direct_temporal":
		return verification
	primary_toolchain = dict(primary.get("toolchain") or {})
	retry_toolchain = dict(retry.get("toolchain") or {})
	primary_fond = dict(primary_toolchain.get("fond4ltlf") or {})
	retry_fond = dict(retry_toolchain.get("fond4ltlf") or {})
	primary_mona = dict(primary_toolchain.get("mona") or {})
	retry_mona = dict(retry_toolchain.get("mona") or {})
	verification["path_embedded_launchers"] = {
		"fond4ltlf": _validate_path_embedded_launcher(
			primary_fond,
			retry_fond,
			label="FOND4LTLf",
			root_key="root",
		),
		"mona": _validate_path_embedded_launcher(
			primary_mona,
			retry_mona,
			label="MONA",
			root_key=None,
		),
	}
	return verification


def _validate_path_embedded_launcher(
	primary: Mapping[str, Any],
	retry: Mapping[str, Any],
	*,
	label: str,
	root_key: str | None,
) -> dict[str, Any]:
	primary_sha256 = str(primary.get("executable_sha256") or "")
	retry_sha256 = str(retry.get("executable_sha256") or "")
	_validate_summary_hash(primary_sha256, label=f"primary {label} launcher")
	_validate_summary_hash(retry_sha256, label=f"retry {label} launcher")
	if primary_sha256 == retry_sha256:
		return {
			"equivalence": "exact_sha256",
			"primary_sha256": primary_sha256,
			"retry_sha256": retry_sha256,
			"retry_file_sha256_verified": None,
			"replacement_count": 0,
		}
	primary_executable = _required_path(primary, "executable", label=label)
	retry_executable = _required_path(retry, "executable", label=label)
	if root_key is None:
		primary_root = _mona_installation_root(primary)
		retry_root = _mona_installation_root(retry)
	else:
		primary_root = _required_path(primary, root_key, label=label)
		retry_root = _required_path(retry, root_key, label=label)
	try:
		primary_relative = primary_executable.relative_to(primary_root)
		retry_relative = retry_executable.relative_to(retry_root)
	except ValueError as error:
		raise ValueError(f"{label} launcher is outside its installation root") from error
	if primary_relative != retry_relative:
		raise ValueError(f"{label} launcher relative path changed")
	if not retry_executable.is_file():
		raise ValueError(f"retry {label} launcher is unavailable for verification")
	retry_bytes = retry_executable.read_bytes()
	if hashlib.sha256(retry_bytes).hexdigest() != retry_sha256:
		raise ValueError(f"retry {label} launcher fingerprint does not match its file")
	retry_prefix = str(retry_root).encode("utf-8")
	primary_prefix = str(primary_root).encode("utf-8")
	replacement_count = retry_bytes.count(retry_prefix)
	if not retry_prefix or not primary_prefix or replacement_count <= 0:
		raise ValueError(f"{label} launcher has no verifiable installation prefix")
	rewritten_bytes = retry_bytes.replace(retry_prefix, primary_prefix)
	if hashlib.sha256(rewritten_bytes).hexdigest() != primary_sha256:
		raise ValueError(
			f"{label} launcher fingerprint change is not explained by its install path",
		)
	return {
		"equivalence": "absolute_install_prefix_rewrite",
		"primary_sha256": primary_sha256,
		"retry_sha256": retry_sha256,
		"retry_file_sha256_verified": True,
		"replacement_count": replacement_count,
	}


def _required_path(
	payload: Mapping[str, Any],
	key: str,
	*,
	label: str,
) -> Path:
	value = str(payload.get(key) or "")
	if not value:
		raise ValueError(f"{label} has no {key}")
	return Path(value)


def _mona_installation_root(payload: Mapping[str, Any]) -> Path:
	executable = _required_path(payload, "executable", label="MONA")
	if len(executable.parents) < 2:
		raise ValueError("MONA launcher has no installation root")
	return executable.parents[1]


def _mapping_sha256(payload: Mapping[str, Any]) -> str:
	encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
		"utf-8",
	)
	return hashlib.sha256(encoded).hexdigest()


def _toolchain_fingerprint(
	summary: Mapping[str, Any],
	*,
	kind: str,
) -> dict[str, Any]:
	toolchain = dict(summary.get("toolchain") or {})
	if kind == "achievement":
		moose = dict(toolchain.get("moose") or {})
		enhsp = dict(toolchain.get("enhsp") or {})
		return {
			"moose_artifact_sha256": moose.get("artifact_sha256"),
			"moose_docker_image": moose.get("docker_image"),
			"moose_git_revision": moose.get("git_revision"),
			"enhsp_configuration": enhsp.get("configuration"),
			"enhsp_git_revision": enhsp.get("git_revision"),
			"enhsp_jar_sha256": enhsp.get("jar_sha256"),
		}
	fond = dict(toolchain.get("fond4ltlf") or {})
	mona = dict(toolchain.get("mona") or {})
	lama = dict(toolchain.get("lama") or {})
	return {
		"fond_git_revision": fond.get("git_revision"),
		"fond_release": fond.get("release"),
		"isolation_wrapper_sha256": fond.get("isolation_wrapper_sha256"),
		"mona_version": mona.get("version"),
		"moose_artifact_sha256": lama.get("moose_artifact_sha256"),
		"moose_git_revision": lama.get("moose_git_revision"),
		"moose_docker_image": lama.get("docker_image"),
	}


def _validate_input_fingerprint(
	primary: Mapping[str, Any],
	retry: Mapping[str, Any],
	*,
	kind: str,
	key: str,
) -> None:
	fields = ["domain_sha256", "problem_sha256"]
	if kind == "achievement":
		fields.extend(("method", "variant"))
	else:
		fields.extend(("sample_id", "profile", "grounded_formula"))
	for field in fields:
		if primary.get(field) != retry.get(field):
			raise ValueError(f"retry input fingerprint changed for {key}: {field}")


def _index_records(
	records: Sequence[Mapping[str, Any]],
	*,
	kind: str,
	label: str,
) -> dict[str, dict[str, Any]]:
	indexed: dict[str, dict[str, Any]] = {}
	for raw_record in records:
		record = dict(raw_record)
		key = _record_key(record, kind=kind)
		if not key or key in indexed:
			raise ValueError(f"{label} summary has duplicate or empty case key: {key}")
		indexed[key] = record
	return indexed


def _record_key(record: Mapping[str, Any], *, kind: str) -> str:
	if kind == "achievement":
		return (
			f"{record.get('variant')}:{record.get('domain')}:"
			f"{Path(str(record.get('problem_file') or '')).name}"
		)
	return str(record.get("sample_id") or "")


def _sort_records(
	records: Sequence[Mapping[str, Any]] | Any,
	*,
	kind: str,
) -> list[dict[str, Any]]:
	items = [dict(record) for record in records]
	key = direct_record_sort_key if kind == "direct_temporal" else achievement_record_sort_key
	return sorted(items, key=key)


def _validate_clean_revision(summary: Mapping[str, Any], *, label: str) -> None:
	revision = dict(summary.get("source_revision") or {})
	if len(str(revision.get("commit") or "")) != 40:
		raise ValueError(f"{label} summary has no full source revision")
	if revision.get("tracked_changes") is not False:
		raise ValueError(f"{label} summary has tracked source changes")
	if revision.get("untracked_files") is not False:
		raise ValueError(f"{label} summary has untracked source files")


def _validate_summary_hash(value: str, *, label: str) -> None:
	if len(value) != 64:
		raise ValueError(f"{label} summary has no SHA-256 fingerprint")


def _case_set_sha256(case_ids: Sequence[str] | set[str]) -> str:
	encoded = json.dumps(sorted(case_ids), separators=(",", ":")).encode("utf-8")
	return hashlib.sha256(encoded).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
	try:
		payload = json.loads(path.read_text(encoding="utf-8"))
	except (OSError, json.JSONDecodeError) as error:
		raise ValueError(f"Cannot read summary {path}: {error}") from error
	if not isinstance(payload, dict):
		raise ValueError(f"Summary is not a JSON object: {path}")
	return payload


def _sha256(path: Path) -> str:
	return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--kind", choices=KINDS, required=True)
	parser.add_argument("--primary-summary", type=Path, required=True)
	parser.add_argument("--retry-summary", type=Path, required=True)
	parser.add_argument("--output-summary", type=Path, required=True)
	return parser.parse_args()


def main() -> int:
	args = parse_args()
	primary_path = args.primary_summary.expanduser().resolve()
	retry_path = args.retry_summary.expanduser().resolve()
	output_path = args.output_summary.expanduser().resolve()
	merged = merge_infrastructure_retries(
		_read_json(primary_path),
		_read_json(retry_path),
		kind=str(args.kind),
		primary_sha256=_sha256(primary_path),
		retry_sha256=_sha256(retry_path),
	)
	_write_json(output_path, merged)
	print(
		f"merged kind={args.kind} cases={len(merged['results'])} "
		f"replaced={merged['infrastructure_repair']['replaced_case_count']} "
		f"output={output_path}",
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
