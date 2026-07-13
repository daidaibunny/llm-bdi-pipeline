#!/usr/bin/env python3
"""Run the registered compiler rejection and symbol-invariance challenge matrix."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import subprocess
import time
from typing import Any, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "artifacts/certificate_challenge_runs"


@dataclass(frozen=True)
class CertificateCase:
	"""One exact production-code property exercised through a focused test node."""

	name: str
	family: str
	kind: str
	node_id: str


CHALLENGE_CASES = (
	CertificateCase(
		"Unbound Body Variable",
		"Binding",
		"rejection",
		"tests/domain_level_planning/test_library_contract.py::"
		"test_domain_level_library_contract_rejects_unbound_body_variables",
	),
	CertificateCase(
		"Cyclic Producer Graph",
		"Preparation",
		"rejection",
		"tests/domain_level_planning/test_atomic_module_synthesis.py::"
		"test_schema_regression_rejects_cyclic_producer_graph_before_search",
	),
	CertificateCase(
		"Obstruction Exchange",
		"Progress",
		"rejection",
		"tests/domain_level_planning/test_atomic_module_synthesis.py::"
		"test_recursive_progress_rejects_delete_add_obstruction_exchange",
	),
	CertificateCase(
		"Ambiguous Capacity Key",
		"Release",
		"rejection",
		"tests/domain_level_planning/test_atomic_module_synthesis.py::"
		"test_resource_release_rejects_symmetric_modes_without_capacity_key",
	),
	CertificateCase(
		"Cyclic Completion Threat",
		"Threat",
		"rejection",
		"tests/domain_level_planning/test_temporal_goal_appender.py::"
		"test_append_temporal_goal_rejects_cyclic_conjunctive_threats",
	),
	CertificateCase(
		"Forbidden Completion Addition",
		"Negative Guard",
		"rejection",
		"tests/domain_level_planning/test_temporal_goal_appender.py::"
		"test_append_temporal_goal_rejects_uncertified_negative_guard_preservation",
	),
	CertificateCase(
		"Exact Terminal Step",
		"Numeric Progress",
		"acceptance",
		"tests/domain_level_planning/test_temporal_goal_appender.py::"
		"test_numeric_until_separates_repeatable_preserving_and_exact_terminal_steps",
	),
)

METAMORPHIC_CASES = (
	CertificateCase(
		"Predicate and Action Renaming",
		"Vocabulary Renaming",
		"invariance",
		"tests/domain_level_planning/test_no_domain_hardcoding.py::"
		"test_atomic_synthesis_is_invariant_under_vocabulary_alpha_renaming",
	),
	CertificateCase(
		"Action Parameter Permutation",
		"Parameter Permutation",
		"invariance",
		"tests/domain_level_planning/test_no_domain_hardcoding.py::"
		"test_atomic_synthesis_is_invariant_under_action_parameter_permutation",
	),
	CertificateCase(
		"Evidence Object Renaming",
		"Object Renaming",
		"invariance",
		"tests/domain_level_planning/test_no_domain_hardcoding.py::"
		"test_atomic_compilation_is_invariant_under_evidence_object_renaming",
	),
	CertificateCase(
		"Unreferenced Static Injection",
		"Irrelevant Fluent",
		"invariance",
		"tests/domain_level_planning/test_no_domain_hardcoding.py::"
		"test_atomic_synthesis_ignores_unreferenced_static_vocabulary",
	),
	CertificateCase(
		"Negative Guard Renaming",
		"Negative Renaming",
		"invariance",
		"tests/domain_level_planning/test_certified_effects.py::"
		"test_negative_guard_preservation_is_symbol_invariant",
	),
	CertificateCase(
		"Support Ranking Renaming",
		"Progress Renaming",
		"invariance",
		"tests/domain_level_planning/test_certified_effects.py::"
		"test_support_depth_certificate_is_invariant_under_vocabulary_renaming",
	),
)


def build_case_command(case: CertificateCase) -> tuple[str, ...]:
	"""Return one isolated, exact-node command for a registered challenge."""

	return ("uv", "run", "pytest", case.node_id, "-q", "--tb=short")


def _source_revision() -> dict[str, Any]:
	try:
		commit = subprocess.run(
			("git", "rev-parse", "HEAD"),
			cwd=PROJECT_ROOT,
			check=True,
			capture_output=True,
			text=True,
		).stdout.strip()
		status = subprocess.run(
			("git", "status", "--porcelain=v1", "--untracked-files=all"),
			cwd=PROJECT_ROOT,
			check=True,
			capture_output=True,
			text=True,
		).stdout.splitlines()
	except (OSError, subprocess.CalledProcessError) as error:
		return {"available": False, "error": str(error)}
	return {
		"available": True,
		"commit": commit,
		"tracked_changes": any(not line.startswith("??") for line in status),
		"untracked_files": any(line.startswith("??") for line in status),
	}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(
		json.dumps(payload, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)


def _selected_cases(names: Sequence[str]) -> tuple[CertificateCase, ...]:
	all_cases = (*CHALLENGE_CASES, *METAMORPHIC_CASES)
	if not names:
		return all_cases
	selected_names = {str(name).strip() for name in names if str(name).strip()}
	selected = tuple(case for case in all_cases if case.name in selected_names)
	missing = sorted(selected_names - {case.name for case in selected})
	if missing:
		raise ValueError(f"Unknown certificate challenge names: {', '.join(missing)}")
	return selected


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
	parser.add_argument("--run-id")
	parser.add_argument("--case", action="append", default=[])
	args = parser.parse_args()
	run_id = args.run_id or f"certificate-matrix-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
	run_root = args.output_root.expanduser().resolve() / run_id
	if run_root.exists():
		raise ValueError(f"Output directory already exists: {run_root}")
	run_root.mkdir(parents=True)
	cases = _selected_cases(args.case)
	records: list[dict[str, Any]] = []
	for index, case in enumerate(cases, start=1):
		start = time.perf_counter()
		result = subprocess.run(
			build_case_command(case),
			cwd=PROJECT_ROOT,
			capture_output=True,
			text=True,
			check=False,
		)
		case_root = run_root / "cases" / f"{index:02d}"
		case_root.mkdir(parents=True)
		(case_root / "stdout.log").write_text(result.stdout, encoding="utf-8")
		(case_root / "stderr.log").write_text(result.stderr, encoding="utf-8")
		record = {
			"name": case.name,
			"family": case.family,
			"kind": case.kind,
			"node_id": case.node_id,
			"command": list(build_case_command(case)),
			"success": result.returncode == 0,
			"return_code": result.returncode,
			"duration_seconds": time.perf_counter() - start,
			"stdout": str(case_root / "stdout.log"),
			"stderr": str(case_root / "stderr.log"),
		}
		records.append(record)
		status = "ok" if record["success"] else "fail"
		print(
			f"[{status}] family={case.family} case={case.name} "
			f"seconds={record['duration_seconds']:.2f}",
			flush=True,
		)
	payload = {
		"schema_version": 1,
		"artifact_kind": "certificate_and_symbol_invariance_challenge_matrix",
		"run_id": run_id,
		"created_at": datetime.now().isoformat(timespec="seconds"),
		"source_revision": _source_revision(),
		"case_count": len(records),
		"success_count": sum(bool(record["success"]) for record in records),
		"records": records,
		"success": all(bool(record["success"]) for record in records),
	}
	_write_json(run_root / "summary.json", payload)
	print(f"[run] summary={run_root / 'summary.json'}", flush=True)
	return 0 if payload["success"] else 1


if __name__ == "__main__":
	raise SystemExit(main())
