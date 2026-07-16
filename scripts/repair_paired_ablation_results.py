#!/usr/bin/env python3
"""Repair derived metrics in a completed paired ablation artifact."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any
from typing import Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_aaai_comparison_tables import (  # noqa: E402
	child_revision_contract_sha256,
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
	return parser.parse_args()


def main() -> int:
	result = repair_paired_results(_parse_args().paired_results)
	print(
		f"repaired_cases={result['repaired_case_count']} "
		f"fanout={result['variant_maxima']} "
		f"paired_results={result['paired_results']}",
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
