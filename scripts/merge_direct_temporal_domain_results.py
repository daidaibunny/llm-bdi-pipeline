#!/usr/bin/env python3
"""Replace one complete domain in a direct temporal reference matrix."""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any
from typing import Mapping
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_direct_temporal_reference import record_sort_key  # noqa: E402
from scripts.run_direct_temporal_reference import (  # noqa: E402
	summarize_temporal_reference_records,
)
from scripts.run_external_planning_references import (  # noqa: E402
	is_infrastructure_failure,
)


def merge_domain_results(
	base: Mapping[str, Any],
	replacement: Mapping[str, Any],
	*,
	run_id: str | None = None,
) -> dict[str, Any]:
	"""Replace an exact domain case set under an unchanged TIDE protocol."""

	_validate_summary_identity(base, label="base")
	_validate_summary_identity(replacement, label="replacement")
	_validate_protocol_pair(base, replacement)

	replacement_domains = tuple(str(item) for item in replacement.get("domains") or ())
	if len(replacement_domains) != 1:
		raise ValueError("replacement summary must contain exactly one domain")
	replacement_domain = replacement_domains[0]
	base_domains = tuple(str(item) for item in base.get("domains") or ())
	if replacement_domain not in base_domains:
		raise ValueError("replacement domain is absent from the base summary")

	base_records = _index_records(base.get("results") or (), label="base")
	replacement_records = _index_records(
		replacement.get("results") or (),
		label="replacement",
	)
	base_domain_ids = {
		sample_id
		for sample_id, record in base_records.items()
		if str(record.get("domain") or "") == replacement_domain
	}
	if set(replacement_records) != base_domain_ids:
		raise ValueError("replacement does not contain the complete base domain case set")
	if any(
		str(record.get("domain") or "") != replacement_domain
		for record in replacement_records.values()
	):
		raise ValueError("replacement summary contains a case from another domain")
	if replacement.get("success") is not True or int(
		replacement.get("infrastructure_failure_count") or 0,
	):
		raise ValueError("replacement summary contains infrastructure failures")

	merged_records = dict(base_records)
	for sample_id, record in replacement_records.items():
		_validate_semantic_input(base_records[sample_id], record, sample_id=sample_id)
		merged_records[sample_id] = deepcopy(record)
	ordered_records = sorted(merged_records.values(), key=record_sort_key)
	timeout_seconds = int(
		dict(replacement.get("parameters") or {}).get(
			"timeout_seconds_total_compile_and_plan",
		)
		or 0,
	)
	infrastructure_failure_count = sum(
		is_infrastructure_failure(record.get("status")) for record in ordered_records
	)

	merged = deepcopy(dict(base))
	merged.update(
		{
			"run_id": run_id
			or f"{base.get('run_id')}+{replacement_domain}-domain-rerun",
			"finished_at": str(replacement.get("finished_at") or ""),
			"source_revision": deepcopy(replacement.get("source_revision")),
			"parameters": deepcopy(replacement.get("parameters")),
			"toolchain": deepcopy(replacement.get("toolchain")),
			"results": ordered_records,
			"selected_case_count": len(ordered_records),
			"metrics": summarize_temporal_reference_records(
				ordered_records,
				timeout_seconds=timeout_seconds,
			),
			"infrastructure_failure_count": infrastructure_failure_count,
			"success": infrastructure_failure_count == 0,
			"domain_rerun": {
				"strategy": "replace_complete_domain_case_set",
				"replacement_domain": replacement_domain,
				"replaced_case_count": len(replacement_records),
				"base_run_id": str(base.get("run_id") or ""),
				"replacement_run_id": str(replacement.get("run_id") or ""),
				"semantic_inputs_verified": True,
				"protocol_verified": True,
				"replacement_status_counts": dict(
					sorted(
						Counter(
							str(record.get("status") or "")
							for record in replacement_records.values()
						).items(),
					),
				),
			},
		},
	)
	return merged


def _validate_summary_identity(payload: Mapping[str, Any], *, label: str) -> None:
	if payload.get("artifact_kind") != "direct_temporal_planning_reference":
		raise ValueError(f"{label} is not a direct temporal reference summary")
	if payload.get("method") != "TIDE + LAMA" or payload.get("variant") != "tide_lama":
		raise ValueError(f"{label} is not a TIDE + LAMA summary")
	records = tuple(payload.get("results") or ())
	if int(payload.get("selected_case_count") or 0) != len(records):
		raise ValueError(f"{label} selected case count is inconsistent")


def _validate_protocol_pair(
	base: Mapping[str, Any],
	replacement: Mapping[str, Any],
) -> None:
	for key in ("benchmark_id", "benchmark_sha256", "method", "variant"):
		if base.get(key) != replacement.get(key):
			raise ValueError(f"replacement changes {key}")
	parameter_keys = (
		"num_workers",
		"timeout_seconds_total_compile_and_plan",
		"max_rss_gb",
		"plan_verifier_timeout_seconds",
		"tide_internal_runs_per_case",
		"tide_subproblem_timeout_ms",
		"tide_configuration",
	)
	base_parameters = dict(base.get("parameters") or {})
	replacement_parameters = dict(replacement.get("parameters") or {})
	if any(
		base_parameters.get(key) != replacement_parameters.get(key)
		for key in parameter_keys
	):
		raise ValueError("replacement changes the TIDE resource or search protocol")
	if _toolchain_contract(base) != _toolchain_contract(replacement):
		raise ValueError("replacement changes the pinned TIDE toolchain")


def _toolchain_contract(payload: Mapping[str, Any]) -> dict[str, Any]:
	toolchain = dict(payload.get("toolchain") or {})
	tide = dict(toolchain.get("tide") or {})
	mona = dict(toolchain.get("mona") or {})
	return {
		"tide_revision": tide.get("pinned_revision"),
		"tide_configuration": tide.get("configuration"),
		"mona_version": mona.get("version"),
		"mona_sha256": mona.get("executable_sha256"),
	}


def _index_records(
	records: Sequence[Mapping[str, Any]],
	*,
	label: str,
) -> dict[str, dict[str, Any]]:
	indexed: dict[str, dict[str, Any]] = {}
	for raw_record in records:
		record = dict(raw_record)
		sample_id = str(record.get("sample_id") or "")
		if not sample_id or sample_id in indexed:
			raise ValueError(f"{label} has a duplicate or empty sample id: {sample_id}")
		indexed[sample_id] = record
	return indexed


def _validate_semantic_input(
	base: Mapping[str, Any],
	replacement: Mapping[str, Any],
	*,
	sample_id: str,
) -> None:
	for field in (
		"sample_id",
		"domain",
		"profile",
		"method",
		"variant",
		"domain_sha256",
		"problem_sha256",
		"tide_temporal_goal",
	):
		if base.get(field) != replacement.get(field):
			raise ValueError(f"semantic input changed for {sample_id}: {field}")


def _read_json(path: Path) -> dict[str, Any]:
	try:
		payload = json.loads(path.read_text(encoding="utf-8"))
	except (OSError, json.JSONDecodeError) as error:
		raise ValueError(f"Cannot read JSON artifact {path}: {error}") from error
	if not isinstance(payload, dict):
		raise ValueError(f"JSON artifact is not an object: {path}")
	return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
	path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--base-summary", type=Path, required=True)
	parser.add_argument("--replacement-summary", type=Path, required=True)
	parser.add_argument("--output-dir", type=Path, required=True)
	parser.add_argument("--run-id")
	return parser.parse_args()


def main() -> int:
	args = parse_args()
	output_dir = args.output_dir.expanduser().resolve()
	if output_dir.exists():
		raise ValueError(f"Merged output directory already exists: {output_dir}")
	output_dir.mkdir(parents=True)
	merged = merge_domain_results(
		_read_json(args.base_summary.expanduser().resolve()),
		_read_json(args.replacement_summary.expanduser().resolve()),
		run_id=args.run_id,
	)
	_write_json(output_dir / "summary.json", merged)
	(output_dir / "results.jsonl").write_text(
		"".join(
			json.dumps(record, sort_keys=True) + "\n" for record in merged["results"]
		),
		encoding="utf-8",
	)
	metrics = dict(merged["metrics"])
	print(
		"merged direct temporal reference "
		f"valid={metrics['valid_trace_count']}/{metrics['supported_case_count']} "
		f"domain={merged['domain_rerun']['replacement_domain']} "
		f"artifact={output_dir / 'summary.json'}",
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
