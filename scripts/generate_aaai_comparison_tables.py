#!/usr/bin/env python3
"""Validate final comparison artifacts and generate AAAI result tables."""

from __future__ import annotations

import argparse
from collections import Counter
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any
from typing import Mapping
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "latex_code/aamas_method_paper/sections"
DEFAULT_PUBLISHED_MOOSE_REFERENCE = (
	PROJECT_ROOT
	/ "paper_artifacts/gp2pl_evaluation/v1/moose_published_reference.json"
)

if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_certificate_challenge_matrix import CHALLENGE_CASES  # noqa: E402
from scripts.run_certificate_challenge_matrix import METAMORPHIC_CASES  # noqa: E402


REGISTERED_SEEDS = (0, 1, 2, 3, 4)
REGISTERED_PAIRED_NUM_WORKERS = 6
REGISTERED_RAW_MOOSE_NUM_WORKERS = 6
REGISTERED_REMOTE_REFERENCE_NUM_WORKERS = 20
REGISTERED_TIMEOUT_SECONDS = 1800
REGISTERED_MAX_RSS_GB = 8.0
REGISTERED_JAVA_STACK_SIZE = "64m"
PINNED_ENHSP_REVISION = "537bed55a60d9456975c56afbadd50fc8acb1dc9"
PINNED_FOND4LTLF_REVISION = "011d9d9a5bfd6406d2c358faf8f63167f6c839bb"
REGISTERED_PUBLISHED_MOOSE_DOMAIN_COVERAGE = (
	("barman", 90, 90.0),
	("ferry", 90, 90.0),
	("gripper", 90, 90.0),
	("logistics", 90, 89.6),
	("miconic", 90, 90.0),
	("rovers", 90, 90.0),
	("satellite", 90, 90.0),
	("transport", 90, 90.0),
	("numeric-ferry", 90, 90.0),
	("numeric-miconic", 90, 90.0),
	("numeric-minecraft", 90, 90.0),
	("numeric-transport", 90, 90.0),
)
REGISTERED_RAW_MOOSE_EXTENSION_DOMAINS = (
	"blocksworld-clear",
	"blocksworld-on",
	"blocksworld-tower",
	"depots",
)
REGISTERED_MOOSE_SCOPE_CONTRACTS = {
	"original_moose": {
		"count": 1080,
		"sha256": "b99b12be1bcbe05983b0727dea0517a671530a55c686068e12908bb12eefb8f1",
	},
	"gp2pl_extension": {
		"count": 148,
		"sha256": "ae3ccea2e2f30093ff13fca34ba31451087fdcb78ffab18fc7ddd473ebb8ab5d",
	},
	"selected_union": {
		"count": 1228,
		"sha256": "3b3d38e19e5e885c3ad15658baf77a26a1aad6cc8a369dfc1284c653a4e385ec",
	},
}
REGISTERED_CHALLENGE_NODE_IDS = tuple(
	case.node_id for case in (*CHALLENGE_CASES, *METAMORPHIC_CASES)
)
ATOMIC_METHODS = (
	("validated_evidence_adapter", "Evidence Only"),
	("action_only_closure", "Direct Producers"),
	("maximal_certified_program", "Maximum Feasible"),
	("full", "Full GP2PL"),
)
TEMPORAL_METHODS = (
	("dfa_aware_unprotected", "Unprotected Serialization"),
	("certified_flat", "Certified Flat"),
	("certified_balanced", "Certified Balanced"),
	("completion_boundary_monitor", "Module-Return Monitor"),
)
ATOMIC_MACRO_PREFIXES = {
	"validated_evidence_adapter": "AtomicEvidenceOnly",
	"action_only_closure": "AtomicDirectProducers",
	"maximal_certified_program": "AtomicMaximumFeasible",
	"full": "AtomicFullGPPL",
}
TEMPORAL_MACRO_PREFIXES = {
	"dfa_aware_unprotected": "TemporalUnprotected",
	"certified_flat": "TemporalCertifiedFlat",
	"certified_balanced": "TemporalCertifiedBalanced",
	"completion_boundary_monitor": "TemporalModuleReturn",
}


def build_paired_ablation_dataset(
	*,
	paired_results_file: str | Path,
	challenge_summary_file: str | Path,
) -> dict[str, Any]:
	"""Build the complete atomic and temporal ablation release."""

	paired_path = Path(paired_results_file).expanduser().resolve()
	challenge_path = Path(challenge_summary_file).expanduser().resolve()
	paired = _read_json(paired_path)
	challenge = _read_json(challenge_path)
	_validate_paired_result(paired)
	_validate_clean_success(challenge, label="challenge matrix")
	atomic_rows, atomic_joint_count = _aggregate_atomic(paired)
	temporal_rows, temporal_joint_count = _aggregate_temporal(paired)
	challenge_count, challenge_success = _validate_challenge_matrix(challenge)
	atomic_records, atomic_seed_results = _portable_atomic_ablation_records(paired)
	temporal_records, temporal_breakdowns = _portable_temporal_ablation_records(paired)
	paired_contrasts = {
		"atomic": _paired_binary_contrasts(
			atomic_records,
			methods=ATOMIC_METHODS,
			key_fields=("seed", "case_id"),
		),
		"temporal": _paired_binary_contrasts(
			temporal_records,
			methods=TEMPORAL_METHODS,
			key_fields=("sample_id",),
		),
	}
	return {
		"schema_version": 1,
		"artifact_kind": "gp2pl_paired_ablation_results",
		"run_id": str(paired.get("run_id") or ""),
		"atomic": atomic_rows,
		"atomic_records": atomic_records,
		"atomic_seed_results": atomic_seed_results,
		"atomic_joint_action_case_count": atomic_joint_count,
		"temporal": temporal_rows,
		"temporal_records": temporal_records,
		"temporal_breakdowns": temporal_breakdowns,
		"paired_contrasts": paired_contrasts,
		"temporal_joint_action_case_count": temporal_joint_count,
		"challenges": {
			"case_count": challenge_count,
			"success_count": challenge_success,
		},
		"protocol": {
			"registered_seeds": list(REGISTERED_SEEDS),
			"num_workers": int(paired.get("num_workers") or 0),
			"timeout_seconds": int(paired.get("timeout_seconds") or 0),
			"jason_java_stack_size": str(
				paired.get("jason_java_stack_size") or "",
			),
			"case_contract": dict(paired.get("case_contract") or {}),
			"atomic_pairing": dict(paired.get("atomic_pairing") or {}),
			"temporal_pairing": dict(paired.get("temporal_pairing") or {}),
		},
		"provenance": {
			"paired_results_sha256": _sha256(paired_path),
			"challenge_summary_sha256": _sha256(challenge_path),
			"source_revision": dict(paired.get("source_revision") or {}),
			"challenge_source_revision": dict(
				challenge.get("source_revision") or {},
			),
			"method_source_equivalence": dict(
				paired.get("method_source_equivalence") or {},
			),
			"derived_metric_correction": dict(
				paired.get("derived_metric_correction") or {},
			),
		},
	}


def _portable_atomic_ablation_records(
	paired: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
	records: list[dict[str, Any]] = []
	seed_results: list[dict[str, Any]] = []
	for run_value in sorted(
		paired.get("atomic_runs") or (),
		key=lambda run: (int(run.get("seed") or 0), str(run.get("variant") or "")),
	):
		run = dict(run_value)
		seed = int(run.get("seed") or 0)
		variant = str(run.get("variant") or "")
		method = str(run.get("method") or "")
		run_records: list[dict[str, Any]] = []
		for validation_value in dict(run.get("summary") or {}).get("validations") or ():
			validation = dict(validation_value)
			problem = Path(str(validation.get("problem_file") or "")).name
			record = {
				"seed": seed,
				"variant": variant,
				"method": method,
				"case_id": f"{validation.get('domain')}:{problem}",
				"domain": str(validation.get("domain") or ""),
				"test": Path(problem).stem,
				"status": str(validation.get("status") or ""),
				"valid": _achievement_valid(validation),
				"jason_success": validation.get("success") is True,
				"val_attempted": validation.get("plan_verifier_attempted") is True,
				"val_success": validation.get("plan_verifier_success") is True,
				"timed_out": validation.get("timed_out") is True,
				"duration_seconds": float(
					validation.get("duration_seconds") or 0.0,
				),
				"action_count": validation.get("action_count"),
				"observed_action_prefix_count": int(
					validation.get("observed_action_prefix_count") or 0,
				),
				"input_fingerprint": str(
					validation.get("input_fingerprint") or "",
				),
			}
			records.append(record)
			run_records.append(record)
		seed_results.append(
			{
				"seed": seed,
				"variant": variant,
				"method": method,
				"case_count": len(run_records),
				"valid_count": sum(record["valid"] for record in run_records),
				"status_counts": dict(
					sorted(Counter(record["status"] for record in run_records).items()),
				),
			},
		)
	return records, seed_results


def _portable_temporal_ablation_records(
	paired: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
	records: list[dict[str, Any]] = []
	breakdowns: list[dict[str, Any]] = []
	for run_value in sorted(
		paired.get("temporal_runs") or (),
		key=lambda run: str(run.get("variant") or ""),
	):
		run = dict(run_value)
		variant = str(run.get("variant") or "")
		method = str(run.get("method") or "")
		run_records: list[dict[str, Any]] = []
		for result_value in run.get("results") or ():
			result = dict(result_value)
			validation = dict(result.get("execution_validation") or {})
			record = {
				"variant": variant,
				"method": method,
				"sample_id": str(result.get("sample_id") or ""),
				"domain": str(result.get("domain") or ""),
				"profile": str(result.get("profile") or ""),
				"status": str(result.get("status") or ""),
				"valid": _temporal_valid(result),
				"jason_status": str(result.get("jason_status") or ""),
				"jason_timed_out": result.get("jason_timed_out") is True,
				"duration_seconds": float(result.get("duration_seconds") or 0.0),
				"action_count": result.get("action_count"),
				"observed_action_prefix_count": int(
					result.get("observed_action_prefix_count") or 0,
				),
				"controller_plan_count": result.get("controller_plan_count"),
				"max_trigger_fanout": result.get("max_trigger_fanout"),
				"trigger_fanout_scope": str(
					result.get("trigger_fanout_scope") or "",
				),
				"val_attempted": validation.get("val_attempted") is True,
				"val_success": validation.get("val_success") is True,
				"gold_accepted": validation.get("gold_accepted") is True,
				"prediction_accepted": validation.get("prediction_accepted") is True,
				"input_fingerprint": str(result.get("input_fingerprint") or ""),
				"atomic_library_fingerprint": str(
					result.get("atomic_library_fingerprint") or "",
				),
				"dfa_fingerprint": str(result.get("dfa_fingerprint") or ""),
				"controller_fingerprint": str(
					result.get("controller_fingerprint") or "",
				),
			}
			records.append(record)
			run_records.append(record)
		breakdowns.append(
			{
				"variant": variant,
				"method": method,
				"case_count": len(run_records),
				"valid_count": sum(record["valid"] for record in run_records),
				"status_counts": dict(
					sorted(Counter(record["status"] for record in run_records).items()),
				),
				"domains": _temporal_group_breakdown(run_records, key="domain"),
				"profiles": _temporal_group_breakdown(run_records, key="profile"),
			},
		)
	return records, breakdowns


def _temporal_group_breakdown(
	records: Sequence[Mapping[str, Any]],
	*,
	key: str,
) -> list[dict[str, Any]]:
	groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
	for record in records:
		groups[str(record.get(key) or "")].append(record)
	return [
		{
			key: value,
			"case_count": len(group),
			"valid_count": sum(record.get("valid") is True for record in group),
		}
		for value, group in sorted(groups.items())
	]


def _paired_binary_contrasts(
	records: Sequence[Mapping[str, Any]],
	*,
	methods: Sequence[tuple[str, str]],
	key_fields: Sequence[str],
) -> list[dict[str, Any]]:
	by_variant: dict[str, dict[tuple[Any, ...], bool]] = defaultdict(dict)
	for record in records:
		variant = str(record.get("variant") or "")
		key = tuple(record.get(field) for field in key_fields)
		if key in by_variant[variant]:
			raise ValueError(f"duplicate paired outcome for {variant}: {key}")
		by_variant[variant][key] = record.get("valid") is True
	contrasts: list[dict[str, Any]] = []
	for (left_variant, left_method), (right_variant, right_method) in zip(
		methods,
		methods[1:],
	):
		left = by_variant[left_variant]
		right = by_variant[right_variant]
		if set(left) != set(right):
			raise ValueError(
				f"paired contrast case sets differ: {left_variant}, {right_variant}",
			)
		both_valid = sum(left[key] and right[key] for key in left)
		left_only = sum(left[key] and not right[key] for key in left)
		right_only = sum(not left[key] and right[key] for key in left)
		neither = len(left) - both_valid - left_only - right_only
		contrasts.append(
			{
				"left_variant": left_variant,
				"left_method": left_method,
				"right_variant": right_variant,
				"right_method": right_method,
				"case_count": len(left),
				"both_valid_count": both_valid,
				"left_only_valid_count": left_only,
				"right_only_valid_count": right_only,
				"neither_valid_count": neither,
				"valid_count_difference": right_only - left_only,
				"valid_rate_difference": (
					(right_only - left_only) / len(left) if left else 0.0
				),
				"exact_two_sided_p": _exact_paired_binary_p(left_only, right_only),
			},
		)
	return contrasts


def _exact_paired_binary_p(left_only: int, right_only: int) -> float:
	discordant = int(left_only) + int(right_only)
	if discordant == 0:
		return 1.0
	extreme = min(int(left_only), int(right_only))
	tail = sum(math.comb(discordant, index) for index in range(extreme + 1))
	return min(1.0, 2.0 * tail / (2**discordant))


def parse_seed_file_assignments(values: Sequence[str]) -> tuple[tuple[int, Path], ...]:
	"""Parse repeated ``SEED=FILE`` assignments for Raw MOOSE extensions."""

	assignments: dict[int, Path] = {}
	for value in values:
		seed_text, separator, filename = str(value).partition("=")
		if not separator or not seed_text.strip() or not filename.strip():
			raise ValueError(f"Raw MOOSE extension must use SEED=FILE: {value!r}")
		try:
			seed = int(seed_text)
		except ValueError as error:
			raise ValueError(f"raw MOOSE seed is not an integer: {value!r}") from error
		if seed in assignments:
			raise ValueError(f"duplicate Raw MOOSE extension seed: {seed}")
		assignments[seed] = Path(filename).expanduser().resolve()
	if tuple(sorted(assignments)) != REGISTERED_SEEDS:
		raise ValueError("Raw MOOSE extension requires exactly seeds 0,1,2,3,4")
	return tuple(sorted(assignments.items()))


def build_comparison_dataset(
	*,
	paired_results_file: str | Path,
	raw_moose_summaries: Sequence[tuple[int, str | Path]] = (),
	instance_reference_summary_file: str | Path,
	direct_temporal_summary_file: str | Path,
	challenge_summary_file: str | Path,
	published_moose_reference_file: str | Path | None = None,
	raw_moose_extension_summaries: Sequence[tuple[int, str | Path]] = (),
) -> dict[str, Any]:
	"""Build a fail-closed compact dataset from every registered comparison."""

	paired_path = Path(paired_results_file).expanduser().resolve()
	instance_path = Path(instance_reference_summary_file).expanduser().resolve()
	direct_path = Path(direct_temporal_summary_file).expanduser().resolve()
	challenge_path = Path(challenge_summary_file).expanduser().resolve()
	published_moose_path = (
		Path(published_moose_reference_file).expanduser().resolve()
		if published_moose_reference_file is not None
		else None
	)
	paired = _read_json(paired_path)
	instance = _read_json(instance_path)
	direct = _read_json(direct_path)
	challenge = _read_json(challenge_path)
	published_moose = (
		_read_json(published_moose_path) if published_moose_path is not None else None
	)
	if published_moose is not None:
		_validate_published_moose_reference(published_moose)
	selected_raw_summaries = (
		raw_moose_extension_summaries
		if published_moose is not None
		else raw_moose_summaries
	)
	raw_records = tuple(
		(seed, Path(path).expanduser().resolve(), _read_json(path))
		for seed, path in selected_raw_summaries
	)
	_validate_paired_result(paired)
	_validate_clean_success(instance, label="instance references")
	_validate_clean_success(direct, label="direct temporal reference")
	_validate_clean_success(challenge, label="challenge matrix")
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
	_validate_direct_temporal_toolchain(
		direct,
		expected_moose_artifact_hash=str(
			dict(dict(instance.get("toolchain") or {}).get("moose") or {}).get(
				"artifact_sha256",
			)
			or "",
		),
	)
	raw_moose_contract = _registered_external_case_contract(paired, "raw_moose")
	if published_moose is not None:
		scope_contracts = dict(published_moose.get("scope_contracts") or {})
		selected_union = dict(scope_contracts.get("selected_union") or {})
		if dict(selected_union.get("case_contract") or {}) != dict(
			raw_moose_contract,
		):
			raise ValueError(
				"published MOOSE scope union does not match the paired Raw MOOSE corpus",
			)
		extension_scope = dict(scope_contracts.get("gp2pl_extension") or {})
		raw_moose_contract = dict(extension_scope.get("case_contract") or {})
	_validate_raw_moose_runs(
		raw_records,
		contract=raw_moose_contract,
		seed_batch_manifests=dict(paired.get("seed_batch_manifests") or {}),
	)
	_validate_common_achievement_toolchain(raw_records, instance=instance)
	_validate_instance_reference_case_sets(instance, paired=paired)
	_validate_case_set(
		[str(record.get("sample_id") or "") for record in direct.get("results") or ()],
		contract=_registered_case_contract(paired, "temporal"),
		label="direct temporal case set",
	)
	expected_temporal_benchmark = str(
		_registered_case_contract(paired, "temporal").get("benchmark_sha256") or "",
	)
	if str(direct.get("benchmark_sha256") or "") != expected_temporal_benchmark:
		raise ValueError("direct temporal benchmark hash does not match the registered input")

	atomic_rows, atomic_joint_count = _aggregate_atomic(paired)
	temporal_rows, temporal_joint_count = _aggregate_temporal(paired)
	external_rows = _aggregate_external(
		raw_records,
		instance,
		direct,
		published_moose=published_moose,
	)
	challenge_count, challenge_success = _validate_challenge_matrix(challenge)
	return {
		"schema_version": 2,
		"artifact_kind": "aaai_final_comparison_results",
		"atomic": atomic_rows,
		"atomic_joint_action_case_count": atomic_joint_count,
		"temporal": temporal_rows,
		"temporal_joint_action_case_count": temporal_joint_count,
		"external": external_rows,
		"challenges": {
			"case_count": challenge_count,
			"success_count": challenge_success,
		},
		"provenance": {
			"paired_results_file": str(paired_path),
			"paired_results_sha256": _sha256(paired_path),
			"method_source_equivalence": dict(
				paired.get("method_source_equivalence") or {},
			),
			"derived_metric_correction": dict(
				paired.get("derived_metric_correction") or {},
			),
			"raw_moose_extension_summaries": [
				{
					"seed": seed,
					"file": str(path),
					"sha256": _sha256(path),
				}
				for seed, path, _summary in raw_records
			],
			"published_moose_reference_file": (
				str(published_moose_path) if published_moose_path is not None else None
			),
			"published_moose_reference_sha256": (
				_sha256(published_moose_path)
				if published_moose_path is not None
				else None
			),
			"instance_reference_summary_file": str(instance_path),
			"instance_reference_summary_sha256": _sha256(instance_path),
			"direct_temporal_summary_file": str(direct_path),
			"direct_temporal_summary_sha256": _sha256(direct_path),
			"challenge_summary_file": str(challenge_path),
			"challenge_summary_sha256": _sha256(challenge_path),
		},
	}


def _validate_published_moose_reference(payload: Mapping[str, Any]) -> None:
	if (
		int(payload.get("schema_version") or 0) != 1
		or payload.get("artifact_kind")
		!= "published_moose_planning_coverage_reference"
	):
		raise ValueError("published MOOSE reference has an invalid schema")
	source = dict(payload.get("source") or {})
	if (
		str(source.get("arxiv_version") or "") != "2511.11095v1"
		or str(source.get("table") or "") != "Table 4"
	):
		raise ValueError(
			"published MOOSE reference must use arXiv 2511.11095v1 Table 4",
		)
	published = payload.get("published_results")
	if not isinstance(published, Mapping):
		raise ValueError("published MOOSE reference has no result payload")
	if (
		int(published.get("seed_count") or 0) != 5
		or published.get("validation_origin") != "reported_by_source_authors"
		or published.get("runtime_comparison_allowed") is not False
	):
		raise ValueError("published MOOSE reference has an invalid reporting contract")
	domain_rows = tuple(published.get("domains") or ())
	if not domain_rows or not all(isinstance(row, Mapping) for row in domain_rows):
		raise ValueError("published MOOSE reference has no domain coverage")
	domain_names = tuple(str(row.get("domain") or "") for row in domain_rows)
	if len(set(domain_names)) != len(domain_names) or not all(domain_names):
		raise ValueError("published MOOSE reference has duplicate or empty domains")
	case_count = sum(int(row.get("case_count_per_seed") or 0) for row in domain_rows)
	mean_solved = sum(float(row.get("mean_solved_count") or 0.0) for row in domain_rows)
	if (
		case_count != int(published.get("case_count_per_seed") or 0)
		or abs(mean_solved - float(published.get("mean_solved_count") or 0.0))
		> 1e-9
	):
		raise ValueError("published MOOSE domain aggregate does not match its total")
	for row in domain_rows:
		domain_case_count = int(row.get("case_count_per_seed") or 0)
		domain_mean = float(row.get("mean_solved_count") or 0.0)
		if domain_case_count <= 0 or not 0.0 <= domain_mean <= domain_case_count:
			raise ValueError("published MOOSE domain coverage is outside its scope")
	observed_coverage = tuple(
		(
			str(row.get("domain") or ""),
			int(row.get("case_count_per_seed") or 0),
			float(row.get("mean_solved_count") or 0.0),
		)
		for row in domain_rows
	)
	if observed_coverage != REGISTERED_PUBLISHED_MOOSE_DOMAIN_COVERAGE:
		raise ValueError("published MOOSE reference changes the registered Table 4 coverage")
	scopes = payload.get("scope_contracts")
	if not isinstance(scopes, Mapping):
		raise ValueError("published MOOSE reference has no scope contracts")
	original_scope = dict(scopes.get("original_moose") or {})
	extension_scope = dict(scopes.get("gp2pl_extension") or {})
	if tuple(original_scope.get("domains") or ()) != domain_names:
		raise ValueError("published MOOSE domains do not match the original scope")
	if tuple(extension_scope.get("domains") or ()) != (
		REGISTERED_RAW_MOOSE_EXTENSION_DOMAINS
	):
		raise ValueError("published MOOSE reference changes the local extension domains")
	if set(original_scope.get("domains") or ()) & set(
		extension_scope.get("domains") or (),
	):
		raise ValueError("published and local MOOSE scopes overlap")
	for label in ("original_moose", "gp2pl_extension", "selected_union"):
		contract = dict(dict(scopes.get(label) or {}).get("case_contract") or {})
		if int(contract.get("count") or 0) <= 0 or len(
			str(contract.get("sha256") or ""),
		) != 64:
			raise ValueError(f"published MOOSE {label} has an invalid case contract")
		if contract != REGISTERED_MOOSE_SCOPE_CONTRACTS[label]:
			raise ValueError(f"published MOOSE {label} changes the registered case set")


def _validate_paired_result(paired: Mapping[str, Any]) -> None:
	_validate_clean_success(paired, label="paired compiler result")
	if paired.get("infrastructure_complete") is not True:
		raise ValueError("paired compiler infrastructure is incomplete")
	if paired.get("paired_inputs_verified") is not True:
		raise ValueError("paired compiler inputs are not verified")
	if dict(paired.get("atomic_pairing") or {}).get("paired") is not True:
		raise ValueError("atomic inputs are not paired")
	if dict(paired.get("temporal_pairing") or {}).get("paired") is not True:
		raise ValueError("temporal inputs are not paired")
	if tuple(paired.get("registered_seeds") or ()) != REGISTERED_SEEDS:
		raise ValueError("paired result does not contain registered seeds 0--4")
	if paired.get("paper_matrix_complete") is not True:
		raise ValueError("paired result is not the registered complete paper matrix")
	seed_manifests = paired.get("seed_batch_manifests")
	if not isinstance(seed_manifests, Mapping) or set(seed_manifests) != {
		str(seed) for seed in REGISTERED_SEEDS
	}:
		raise ValueError("paired result has incomplete seed-batch manifests")
	for seed in REGISTERED_SEEDS:
		_validate_seed_batch_contract(
			dict(seed_manifests[str(seed)]),
			seed=seed,
			label=f"paired seed {seed}",
		)
	if int(paired.get("num_workers") or 0) != REGISTERED_PAIRED_NUM_WORKERS:
		raise ValueError("paired result does not use the registered worker count")
	if int(paired.get("timeout_seconds") or 0) != REGISTERED_TIMEOUT_SECONDS:
		raise ValueError("paired result does not use the registered timeout")
	if str(paired.get("jason_java_stack_size") or "") != REGISTERED_JAVA_STACK_SIZE:
		raise ValueError("paired result does not use the registered Java stack size")
	expected_commit = str(
		dict(paired.get("source_revision") or {}).get("commit") or "",
	)
	child_revisions_match = True
	for run in paired.get("atomic_runs") or ():
		summary = dict(dict(run).get("summary") or {})
		child_revisions_match = _child_source_revision_matches(
			summary,
			expected_commit=expected_commit,
		) and child_revisions_match
		_validate_jason_protocol(
			dict(summary.get("settings") or {}),
			label="atomic child run",
		)
	for run in paired.get("temporal_runs") or ():
		run_payload = dict(run)
		child_revisions_match = _child_source_revision_matches(
			run_payload,
			expected_commit=expected_commit,
		) and child_revisions_match
		_validate_jason_protocol(
			dict(run_payload.get("parameters") or {}),
			label="temporal child run",
			jason_timeout_key="jason_timeout_seconds",
		)
	if not child_revisions_match:
		_validate_method_source_equivalence(paired)


def _child_source_revision_matches(
	payload: Mapping[str, Any],
	*,
	expected_commit: str,
) -> bool:
	revision = dict(payload.get("source_revision") or {})
	return (
		revision.get("tracked_changes") is False
		and revision.get("untracked_files") is False
		and str(revision.get("commit") or "") == expected_commit
	)


def child_revision_contract_sha256(paired: Mapping[str, Any]) -> str:
	"""Hash every atomic and temporal child source-revision record."""

	records: list[dict[str, Any]] = []
	for run in paired.get("atomic_runs") or ():
		run_payload = dict(run)
		summary = dict(run_payload.get("summary") or {})
		records.append(
			{
				"stage": "atomic",
				"seed": int(run_payload.get("seed") or 0),
				"variant": str(run_payload.get("variant") or ""),
				"source_revision": dict(summary.get("source_revision") or {}),
			},
		)
	for run in paired.get("temporal_runs") or ():
		run_payload = dict(run)
		records.append(
			{
				"stage": "temporal",
				"variant": str(run_payload.get("variant") or ""),
				"source_revision": dict(run_payload.get("source_revision") or {}),
			},
		)
	encoded = json.dumps(
		sorted(records, key=lambda item: (item["stage"], item.get("seed", -1), item["variant"])),
		sort_keys=True,
		separators=(",", ":"),
	).encode("utf-8")
	return hashlib.sha256(encoded).hexdigest()


def _validate_method_source_equivalence(paired: Mapping[str, Any]) -> None:
	equivalence = dict(paired.get("method_source_equivalence") or {})
	if equivalence.get("status") != "confirmed" or equivalence.get("basis") != (
		"experiment_owner_confirmed_no_method_code_changes"
	):
		raise ValueError(
			"paired child revisions differ without confirmed method-source equivalence",
		)
	expected = child_revision_contract_sha256(paired)
	if str(equivalence.get("child_revision_contract_sha256") or "") != expected:
		raise ValueError("method-source equivalence does not cover child revisions")


def _validate_jason_protocol(
	settings: Mapping[str, Any],
	*,
	label: str,
	jason_timeout_key: str = "timeout_seconds",
) -> None:
	if int(settings.get("num_workers") or 0) != REGISTERED_PAIRED_NUM_WORKERS:
		raise ValueError(f"{label} does not use the registered worker count")
	if int(settings.get(jason_timeout_key) or 0) != REGISTERED_TIMEOUT_SECONDS:
		raise ValueError(f"{label} does not use the registered timeout")
	if int(settings.get("plan_verifier_timeout_seconds") or 0) != (
		REGISTERED_TIMEOUT_SECONDS
	):
		raise ValueError(f"{label} does not use the registered VAL timeout")
	if str(settings.get("jason_java_stack_size") or "") != REGISTERED_JAVA_STACK_SIZE:
		raise ValueError(f"{label} does not use the registered Java stack size")


def _validate_clean_success(payload: Mapping[str, Any], *, label: str) -> None:
	if payload.get("success") is not True:
		raise ValueError(f"{label} is not successful")
	revision = dict(payload.get("source_revision") or {})
	if revision.get("tracked_changes") is not False:
		raise ValueError(f"{label} has tracked source changes")
	if revision.get("untracked_files") is not False:
		raise ValueError(f"{label} has untracked source files")
	if len(str(revision.get("commit") or "")) < 8:
		raise ValueError(f"{label} has no pinned source commit")


def _validate_infrastructure_repair(
	payload: Mapping[str, Any],
	*,
	label: str,
	direct_temporal: bool,
) -> None:
	repair = payload.get("infrastructure_repair")
	if repair is None:
		return
	if not isinstance(repair, Mapping):
		raise ValueError(f"{label} has malformed infrastructure repair provenance")
	if repair.get("strategy") != "replace_exact_infrastructure_failures":
		raise ValueError(f"{label} uses an unregistered infrastructure repair strategy")
	if int(repair.get("primary_num_workers") or 0) != (
		REGISTERED_REMOTE_REFERENCE_NUM_WORKERS
	):
		raise ValueError(f"{label} repair changes the primary worker protocol")
	if int(repair.get("retry_num_workers") or 0) != 1:
		raise ValueError(f"{label} repair does not use the registered serial retry worker")
	for key in ("primary_summary_sha256", "retry_summary_sha256"):
		if len(str(repair.get(key) or "")) != 64:
			raise ValueError(f"{label} repair has no {key}")
	for key in (
		"input_fingerprints_verified",
		"toolchain_verified",
		"resource_limits_verified",
		"hardware_equivalence_confirmed_by_experiment_owner",
		"runtime_measurement_excludes_queue_wait",
		"runtime_comparison_allowed",
	):
		if repair.get(key) is not True:
			raise ValueError(f"{label} repair does not establish {key}")
	if direct_temporal:
		_validate_direct_repair_toolchain_verification(repair, label=label)
	primary_revision = dict(repair.get("primary_source_revision") or {})
	retry_revision = dict(repair.get("retry_source_revision") or {})
	_validate_repair_revision(primary_revision, label=f"{label} primary repair")
	_validate_repair_revision(retry_revision, label=f"{label} retry")
	if primary_revision != dict(payload.get("source_revision") or {}):
		raise ValueError(f"{label} repair changes the primary source revision")
	replaced_ids = tuple(str(value) for value in repair.get("replaced_case_ids") or ())
	if not replaced_ids or len(replaced_ids) != len(set(replaced_ids)):
		raise ValueError(f"{label} repair has an invalid replaced case set")
	if int(repair.get("replaced_case_count") or 0) != len(replaced_ids):
		raise ValueError(f"{label} repair has an inconsistent replaced case count")
	encoded = json.dumps(sorted(replaced_ids), separators=(",", ":")).encode("utf-8")
	if hashlib.sha256(encoded).hexdigest() != str(
		repair.get("replaced_case_set_sha256") or "",
	):
		raise ValueError(f"{label} repair case-set fingerprint does not match")
	annotated_ids = {
		_repaired_record_key(record, direct_temporal=direct_temporal)
		for record in payload.get("results") or ()
		if isinstance(record, Mapping)
		and isinstance(record.get("infrastructure_retry"), Mapping)
	}
	if annotated_ids != set(replaced_ids):
		raise ValueError(f"{label} repair annotations do not match replaced cases")


def _validate_direct_repair_toolchain_verification(
	repair: Mapping[str, Any],
	*,
	label: str,
) -> None:
	verification = repair.get("toolchain_verification")
	if not isinstance(verification, Mapping):
		raise ValueError(f"{label} repair has no toolchain verification evidence")
	if verification.get("semantic_identity") != (
		"exact_pinned_revisions_and_versions"
	):
		raise ValueError(f"{label} repair changes the pinned toolchain identity")
	if len(str(verification.get("semantic_identity_sha256") or "")) != 64:
		raise ValueError(f"{label} repair has no portable toolchain fingerprint")
	launchers = verification.get("path_embedded_launchers")
	if not isinstance(launchers, Mapping) or set(launchers) != {"fond4ltlf", "mona"}:
		raise ValueError(f"{label} repair has incomplete path-embedded launchers")
	for launcher_name in ("fond4ltlf", "mona"):
		launcher = launchers.get(launcher_name)
		if not isinstance(launcher, Mapping):
			raise ValueError(f"{label} repair has malformed path-embedded launcher")
		primary_sha256 = str(launcher.get("primary_sha256") or "")
		retry_sha256 = str(launcher.get("retry_sha256") or "")
		if len(primary_sha256) != 64 or len(retry_sha256) != 64:
			raise ValueError(f"{label} repair has incomplete launcher fingerprints")
		equivalence = str(launcher.get("equivalence") or "")
		if equivalence == "exact_sha256":
			if primary_sha256 != retry_sha256:
				raise ValueError(f"{label} repair has inconsistent launcher equality")
			continue
		if equivalence == "absolute_install_prefix_rewrite":
			if (
				primary_sha256 == retry_sha256
				or launcher.get("retry_file_sha256_verified") is not True
				or int(launcher.get("replacement_count") or 0) <= 0
			):
				raise ValueError(
					f"{label} repair has unverified path-embedded launcher",
				)
			continue
		raise ValueError(f"{label} repair has unverified path-embedded launcher")


def _validate_repair_revision(revision: Mapping[str, Any], *, label: str) -> None:
	if len(str(revision.get("commit") or "")) < 8:
		raise ValueError(f"{label} has no pinned source revision")
	if revision.get("tracked_changes") is not False:
		raise ValueError(f"{label} has tracked source changes")
	if revision.get("untracked_files") is not False:
		raise ValueError(f"{label} has untracked source files")


def _repaired_record_key(
	record: Mapping[str, Any],
	*,
	direct_temporal: bool,
) -> str:
	if direct_temporal:
		return str(record.get("sample_id") or "")
	return (
		f"{record.get('variant')}:{record.get('domain')}:"
		f"{Path(str(record.get('problem_file') or '')).name}"
	)


def _validate_raw_moose_runs(
	runs: Sequence[tuple[int, Path, Mapping[str, Any]]],
	*,
	contract: Mapping[str, Any],
	seed_batch_manifests: Mapping[str, Any],
) -> None:
	seeds = tuple(sorted(seed for seed, _path, _summary in runs))
	if seeds != REGISTERED_SEEDS:
		raise ValueError("Raw MOOSE comparison requires exactly seeds 0--4")
	for seed, _path, summary in runs:
		_validate_clean_success(summary, label=f"Raw MOOSE seed {seed}")
		_validate_external_reference_protocol(
			summary,
			label=f"Raw MOOSE seed {seed}",
			expected_num_workers=REGISTERED_RAW_MOOSE_NUM_WORKERS,
		)
		_validate_achievement_toolchain(summary, label=f"Raw MOOSE seed {seed}")
		_validate_raw_moose_training_contract(summary, seed=seed)
		paired_manifest = seed_batch_manifests.get(str(seed))
		if not isinstance(paired_manifest, Mapping):
			raise ValueError(f"Raw MOOSE seed {seed} has no paired model batch")
		if str(dict(summary["model_batch_manifest"]).get("sha256") or "") != str(
			paired_manifest.get("sha256") or "",
		):
			raise ValueError(
				f"Raw MOOSE seed {seed} does not use the paired model batch",
			)
		if str(
			dict(summary["model_batch_manifest"]).get("artifact_sha256") or "",
		) != str(paired_manifest.get("artifact_sha256") or ""):
			raise ValueError(
				f"Raw MOOSE seed {seed} does not use the paired evidence artifacts",
			)
		methods = {str(row.get("method") or "") for row in summary.get("results") or ()}
		if methods != {"Raw MOOSE"}:
			raise ValueError(f"Raw MOOSE seed {seed} contains methods {sorted(methods)}")
		_validate_case_set(
			[
				_external_achievement_case_key(record)
				for record in summary.get("results") or ()
			],
			contract=contract,
			label=f"Raw MOOSE seed {seed} case set",
		)


def _validate_raw_moose_training_contract(
	summary: Mapping[str, Any],
	*,
	seed: int,
) -> None:
	label = f"Raw MOOSE seed {seed}"
	manifest = summary.get("model_batch_manifest")
	if not isinstance(manifest, Mapping):
		raise ValueError(f"{label} has no model-batch manifest")
	_validate_seed_batch_contract(manifest, seed=seed, label=label)


def _validate_seed_batch_contract(
	manifest: Mapping[str, Any],
	*,
	seed: int,
	label: str,
) -> None:
	if len(str(manifest.get("sha256") or "")) != 64:
		raise ValueError(f"{label} has no model-batch manifest hash")
	if len(str(manifest.get("artifact_sha256") or "")) != 64:
		raise ValueError(f"{label} has no evidence-artifact hash")
	settings = manifest.get("settings")
	if not isinstance(settings, Mapping):
		raise ValueError(f"{label} has no model-batch training settings")
	if int(settings.get("random_seed", -1)) != seed:
		raise ValueError(f"{label} does not use its assigned training seed")
	expected = {
		"num_workers": 1,
		"num_permutations": 3,
		"goal_max_size": 1,
		"train_timeout_seconds": 43200,
	}
	for key, value in expected.items():
		if int(settings.get(key) or 0) != value:
			raise ValueError(f"{label} has nonregistered training setting {key}")
	if float(settings.get("max_rss_gb") or 0.0) != 16.0:
		raise ValueError(f"{label} has nonregistered training memory limit")


def _validate_external_reference_protocol(
	summary: Mapping[str, Any],
	*,
	label: str,
	expected_num_workers: int,
	direct_temporal: bool = False,
) -> None:
	parameters = summary.get("parameters")
	if not isinstance(parameters, Mapping):
		raise ValueError(f"{label} has no resource protocol")
	if int(parameters.get("num_workers") or 0) != expected_num_workers:
		raise ValueError(
			f"{label} does not use the registered {expected_num_workers} workers",
		)
	timeout_key = (
		"timeout_seconds_total_compile_and_plan"
		if direct_temporal
		else "timeout_seconds"
	)
	if int(parameters.get(timeout_key) or 0) != REGISTERED_TIMEOUT_SECONDS:
		raise ValueError(f"{label} does not use the registered timeout")
	if float(parameters.get("max_rss_gb") or 0.0) != REGISTERED_MAX_RSS_GB:
		raise ValueError(f"{label} does not use the registered memory limit")
	if int(parameters.get("plan_verifier_timeout_seconds") or 0) != (
		REGISTERED_TIMEOUT_SECONDS
	):
		raise ValueError(f"{label} does not use the registered VAL timeout")


def _validate_achievement_toolchain(
	summary: Mapping[str, Any],
	*,
	label: str,
) -> None:
	toolchain = dict(summary.get("toolchain") or {})
	moose = dict(toolchain.get("moose") or {})
	enhsp = dict(toolchain.get("enhsp") or {})
	if len(str(moose.get("artifact_sha256") or "")) != 64:
		raise ValueError(f"{label} has no pinned MOOSE artifact hash")
	if str(moose.get("docker_image") or "") != "moose-exact-ubuntu22:local":
		raise ValueError(f"{label} does not use the pinned MOOSE image")
	if str(enhsp.get("git_revision") or "") != PINNED_ENHSP_REVISION:
		raise ValueError(f"{label} does not use the pinned ENHSP revision")
	if len(str(enhsp.get("jar_sha256") or "")) != 64:
		raise ValueError(f"{label} has no pinned ENHSP jar hash")
	if str(enhsp.get("configuration") or "") != "sat-hmrphj":
		raise ValueError(f"{label} does not use the registered MRP+HJ configuration")


def _validate_common_achievement_toolchain(
	raw_runs: Sequence[tuple[int, Path, Mapping[str, Any]]],
	*,
	instance: Mapping[str, Any],
) -> None:
	summaries = [instance, *(summary for _seed, _path, summary in raw_runs)]
	moose_hashes = {
		str(
			dict(dict(summary.get("toolchain") or {}).get("moose") or {}).get(
				"artifact_sha256",
			)
			or "",
		)
		for summary in summaries
	}
	if len(moose_hashes) != 1:
		raise ValueError("external references do not share the same MOOSE artifact")
	enhsp_hashes = {
		str(
			dict(dict(summary.get("toolchain") or {}).get("enhsp") or {}).get(
				"jar_sha256",
			)
			or "",
		)
		for summary in summaries
	}
	if len(enhsp_hashes) != 1:
		raise ValueError("external references do not share the same ENHSP artifact")


def _validate_direct_temporal_toolchain(
	summary: Mapping[str, Any],
	*,
	expected_moose_artifact_hash: str,
) -> None:
	toolchain = dict(summary.get("toolchain") or {})
	fond = dict(toolchain.get("fond4ltlf") or {})
	mona = dict(toolchain.get("mona") or {})
	lama = dict(toolchain.get("lama") or {})
	if str(fond.get("git_revision") or "") != PINNED_FOND4LTLF_REVISION:
		raise ValueError("direct temporal reference does not use the pinned FOND4LTLf revision")
	if str(fond.get("release") or "") != "v0.0.4":
		raise ValueError("direct temporal reference does not use FOND4LTLf v0.0.4")
	if len(str(fond.get("executable_sha256") or "")) != 64:
		raise ValueError("direct temporal reference has no FOND4LTLf executable hash")
	if str(mona.get("version") or "") != "1.4-18":
		raise ValueError("direct temporal reference does not use MONA 1.4-18")
	if len(str(mona.get("executable_sha256") or "")) != 64:
		raise ValueError("direct temporal reference has no MONA executable hash")
	if (
		len(expected_moose_artifact_hash) != 64
		or str(lama.get("moose_artifact_sha256") or "")
		!= expected_moose_artifact_hash
	):
		raise ValueError("direct temporal LAMA does not share the pinned MOOSE artifact")


def _validate_instance_reference_case_sets(
	summary: Mapping[str, Any],
	*,
	paired: Mapping[str, Any],
) -> None:
	records_by_method: dict[str, list[str]] = defaultdict(list)
	for record in summary.get("results") or ():
		records_by_method[str(record.get("method") or "")].append(
			_external_achievement_case_key(record),
		)
	for variant, display_name in (("lama", "LAMA"), ("enhsp_hmrphj", "MRP+HJ")):
		_validate_case_set(
			records_by_method.get(display_name, []),
			contract=_registered_external_case_contract(paired, variant),
			label=f"{display_name} case set",
		)


def _aggregate_atomic(
	paired: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], int]:
	runs = tuple(dict(run) for run in paired.get("atomic_runs") or ())
	expected_pairs = {
		(seed, variant)
		for seed in REGISTERED_SEEDS
		for variant, _method in ATOMIC_METHODS
	}
	observed_pairs = {(int(run.get("seed")), str(run.get("variant"))) for run in runs}
	if observed_pairs != expected_pairs or len(runs) != len(expected_pairs):
		raise ValueError("atomic run matrix is incomplete or contains duplicates")
	domains = tuple(str(item) for item in paired.get("domains") or ())
	if not domains:
		raise ValueError("paired result has no domains")
	by_pair = {(int(run["seed"]), str(run["variant"])): run for run in runs}
	achievement_contract = _registered_case_contract(paired, "achievement")
	joint_keys_by_seed: dict[int, set[str]] = {}
	for seed in REGISTERED_SEEDS:
		validation_maps = {
			variant: _achievement_validation_map(
				dict(by_pair[(seed, variant)].get("summary") or {}).get("validations")
				or (),
			)
			for variant, _method in ATOMIC_METHODS
		}
		key_sets = {frozenset(records) for records in validation_maps.values()}
		if len(key_sets) != 1:
			raise ValueError(f"atomic held-out case mismatch for seed={seed}")
		observed_keys = set(next(iter(key_sets)))
		_validate_case_set(
			observed_keys,
			contract=achievement_contract,
			label=f"registered achievement case set for seed={seed}",
		)
		joint = observed_keys
		for records in validation_maps.values():
			joint.intersection_update(
				key for key, record in records.items() if _achievement_valid(record)
			)
		joint_keys_by_seed[seed] = joint
	rows: list[dict[str, Any]] = []
	for variant, method in ATOMIC_METHODS:
		variant_runs = [by_pair[(seed, variant)] for seed in REGISTERED_SEEDS]
		seed_branches: list[float] = []
		seed_sizes: list[float] = []
		seed_compile_seconds: list[float] = []
		validations: list[Mapping[str, Any]] = []
		compiled_count = 0
		covered_targets = 0
		producible_targets = 0
		joint_actions: list[float] = []
		for seed, run in zip(REGISTERED_SEEDS, variant_runs, strict=True):
			domain_records = dict(run.get("domains") or {})
			if set(domain_records) != set(domains):
				raise ValueError(
					f"atomic domain matrix mismatch for seed={seed}, variant={variant}",
				)
			branches = 0
			size_bytes = 0
			compile_seconds = 0.0
			for record in domain_records.values():
				domain_record = dict(record or {})
				compiled_count += int(domain_record.get("compile_success") is True)
				compile_seconds += float(domain_record.get("compile_seconds") or 0.0)
				metrics = dict(domain_record.get("library_metrics") or {})
				if not metrics:
					raise ValueError(
						f"missing atomic library metrics for seed={seed}, variant={variant}",
					)
				covered_targets += int(metrics.get("covered_target_count") or 0)
				producible_targets += int(metrics.get("producible_target_count") or 0)
				branches += int(metrics.get("selected_branch_count") or 0)
				size_bytes += int(metrics.get("asl_bytes") or 0)
			seed_branches.append(float(branches))
			seed_sizes.append(size_bytes / 1024.0)
			seed_compile_seconds.append(compile_seconds)
			validation_map = _achievement_validation_map(
				dict(run.get("summary") or {}).get("validations") or (),
			)
			validations.extend(validation_map.values())
			joint_actions.extend(
				float(validation_map[key]["action_count"])
				for key in sorted(joint_keys_by_seed[seed])
				if validation_map[key].get("action_count") is not None
			)
		mean_branches, sd_branches = _mean_sample_sd(seed_branches)
		mean_size, sd_size = _mean_sample_sd(seed_sizes)
		mean_compile, sd_compile = _mean_sample_sd(seed_compile_seconds)
		rows.append(
			{
				"variant": variant,
				"method": method,
				"compiled_count": compiled_count,
				"compiled_total": len(domains) * len(REGISTERED_SEEDS),
				"covered_target_count": covered_targets,
				"producible_target_count": producible_targets,
				"valid_trace_count": sum(_achievement_valid(row) for row in validations),
				"test_count": len(validations),
				"mean_branch_count": mean_branches,
				"sd_branch_count": sd_branches,
				"mean_library_kib": mean_size,
				"sd_library_kib": sd_size,
				"mean_compile_seconds": mean_compile,
				"sd_compile_seconds": sd_compile,
				"median_joint_action_count": _median(joint_actions),
			},
		)
	return rows, sum(len(keys) for keys in joint_keys_by_seed.values())


def _registered_case_contract(
	payload: Mapping[str, Any],
	label: str,
) -> Mapping[str, Any]:
	case_contract = payload.get("case_contract")
	if not isinstance(case_contract, Mapping):
		raise ValueError("paired result has no registered case contract")
	contract = case_contract.get(label)
	if not isinstance(contract, Mapping):
		raise ValueError(f"paired result has no {label} case contract")
	return contract


def _registered_external_case_contract(
	payload: Mapping[str, Any],
	method: str,
) -> Mapping[str, Any]:
	case_contract = payload.get("case_contract")
	if not isinstance(case_contract, Mapping):
		raise ValueError("paired result has no registered case contract")
	external = case_contract.get("external")
	if not isinstance(external, Mapping):
		raise ValueError("paired result has no external case contract")
	contract = external.get(method)
	if not isinstance(contract, Mapping):
		raise ValueError(f"paired result has no {method} case contract")
	return contract


def _external_achievement_case_key(record: Mapping[str, Any]) -> str:
	return (
		f"{record.get('domain')}:"
		f"{Path(str(record.get('problem_file') or '')).name}"
	)


def _validate_case_set(
	case_ids: Sequence[str] | set[str],
	*,
	contract: Mapping[str, Any],
	label: str,
) -> None:
	normalized_ids = tuple(str(case_id) for case_id in case_ids)
	unique_ids = set(normalized_ids)
	if len(normalized_ids) != len(unique_ids):
		raise ValueError(f"{label} contains duplicate identifiers")
	encoded = json.dumps(
		sorted(unique_ids),
		separators=(",", ":"),
	).encode("utf-8")
	observed_hash = hashlib.sha256(encoded).hexdigest()
	expected_count = int(contract.get("count") or 0)
	expected_hash = str(contract.get("sha256") or "")
	if expected_count <= 0 or len(expected_hash) != 64:
		raise ValueError(f"invalid {label} contract")
	if len(unique_ids) != expected_count or observed_hash != expected_hash:
		raise ValueError(
			f"{label} mismatch: observed={len(unique_ids)}, expected={expected_count}",
		)


def _aggregate_temporal(
	paired: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], int]:
	runs = tuple(dict(run) for run in paired.get("temporal_runs") or ())
	by_variant = {str(run.get("variant")): run for run in runs}
	expected = {variant for variant, _method in TEMPORAL_METHODS}
	if set(by_variant) != expected or len(runs) != len(expected):
		raise ValueError("temporal run matrix is incomplete or contains duplicates")
	temporal_contract = _registered_case_contract(paired, "temporal")
	expected_benchmark_hash = str(temporal_contract.get("benchmark_sha256") or "")
	observed_benchmark_hashes = {
		str(run.get("benchmark_sha256") or "") for run in runs
	}
	if (
		len(expected_benchmark_hash) != 64
		or observed_benchmark_hashes != {expected_benchmark_hash}
	):
		raise ValueError("temporal runs do not use the registered temporal benchmark")
	result_maps = {
		variant: _temporal_result_map(
			by_variant[variant].get("results") or (),
			variant=variant,
		)
		for variant, _method in TEMPORAL_METHODS
	}
	key_sets = {frozenset(records) for records in result_maps.values()}
	if len(key_sets) != 1 or not key_sets:
		raise ValueError("temporal result sample sets differ")
	joint = set(next(iter(key_sets)))
	_validate_case_set(
		joint,
		contract=temporal_contract,
		label="registered temporal case set",
	)
	for records in result_maps.values():
		joint.intersection_update(
			key for key, record in records.items() if _temporal_valid(record)
		)
	cutoff = int(paired.get("timeout_seconds") or 1800)
	rows: list[dict[str, Any]] = []
	for variant, method in TEMPORAL_METHODS:
		records = result_maps[variant]
		compiled = [
			record
			for record in records.values()
			if record.get("controller_plan_count") is not None
		]
		valid = [record for record in records.values() if _temporal_valid(record)]
		par2 = [
			float(record.get("duration_seconds") or 0.0)
			if _temporal_valid(record)
			else float(2 * cutoff)
			for record in records.values()
		]
		rows.append(
			{
				"variant": variant,
				"method": method,
				"compiled_count": len(compiled),
				"test_count": len(records),
				"valid_trace_count": len(valid),
				"par2_seconds": statistics.mean(par2) if par2 else None,
				"median_joint_action_count": _median(
					float(records[key]["action_count"])
					for key in sorted(joint)
					if records[key].get("action_count") is not None
				),
				"median_controller_plan_count": _median(
					float(record["controller_plan_count"])
					for record in compiled
				),
				"maximum_trigger_fanout": max(
					(int(record.get("max_trigger_fanout") or 0) for record in compiled),
					default=0,
				),
				"median_append_seconds": _median(
					float(record["append_seconds"])
					for record in compiled
					if record.get("append_seconds") is not None
				),
			},
		)
	return rows, len(joint)


def _aggregate_external(
	raw_runs: Sequence[tuple[int, Path, Mapping[str, Any]]],
	instance: Mapping[str, Any],
	direct: Mapping[str, Any],
	*,
	published_moose: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
	method_records: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
	for _seed, _path, summary in raw_runs:
		for record in summary.get("results") or ():
			method_records[str(record.get("method") or "")].append(record)
	for record in instance.get("results") or ():
		method_records[str(record.get("method") or "")].append(record)
	if set(method_records) != {"Raw MOOSE", "LAMA", "MRP+HJ"}:
		raise ValueError(
			"external achievement method matrix mismatch: "
			f"{sorted(method_records)}",
		)
	rows: list[dict[str, Any]] = []
	if published_moose is None:
		rows.append(
			_external_row(
				"Raw MOOSE",
				"Achievement, five seeds",
				method_records["Raw MOOSE"],
			),
		)
	else:
		published_results = dict(published_moose.get("published_results") or {})
		rows.extend(
			(
				{
					"method": "MOOSE",
					"source": "Reported",
					"scope": "Original MOOSE domains, five seeds",
					"case_count": int(
						published_results.get("case_count_per_seed") or 0,
					),
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
				_raw_moose_extension_row(raw_runs),
			),
		)
	for method, scope in (
		("LAMA", "Classical achievement"),
		("MRP+HJ", "Numeric achievement"),
	):
		records = method_records[method]
		rows.append(_external_row(method, scope, records))
	direct_records = tuple(dict(record) for record in direct.get("results") or ())
	selected_count = int(direct.get("selected_case_count") or 0)
	if selected_count != len(direct_records):
		raise ValueError("direct temporal result count mismatch")
	supported = [record for record in direct_records if record.get("supported") is True]
	valid = [record for record in supported if _direct_temporal_valid(record)]
	cutoff = int(
		dict(direct.get("parameters") or {}).get(
			"timeout_seconds_total_compile_and_plan",
		)
		or 1800
	)
	rows.append(
		{
			"method": "FOND4LTLf + LAMA",
			"source": "Measured",
			"scope": "Supported Boolean TEG",
			"case_count": len(supported),
			"supported_case_count": len(supported),
			"unsupported_case_count": len(direct_records) - len(supported),
			"valid_trace_count": len(valid),
			"par2_seconds": (
				statistics.mean(
					float(record.get("elapsed_seconds") or 0.0)
					if _direct_temporal_valid(record)
					else float(2 * cutoff)
					for record in supported
				)
				if supported
				else None
			),
		},
	)
	return rows


def _raw_moose_extension_row(
	raw_runs: Sequence[tuple[int, Path, Mapping[str, Any]]],
) -> dict[str, Any]:
	seed_records = [tuple(summary.get("results") or ()) for _seed, _path, summary in raw_runs]
	case_count = len(seed_records[0]) if seed_records else 0
	valid_counts = [
		float(sum(record.get("plan_verifier_success") is True for record in records))
		for records in seed_records
	]
	all_records = [record for records in seed_records for record in records]
	row = _external_row(
		"Raw MOOSE extension",
		"Added domains, five seeds",
		all_records,
	)
	row.update(
		{
			"case_count": case_count,
			"supported_case_count": case_count,
			"valid_trace_count": statistics.mean(valid_counts) if valid_counts else 0.0,
			"seed_count": len(seed_records),
			"coverage_sample_sd": (
				statistics.stdev(valid_counts) if len(valid_counts) > 1 else 0.0
			),
			"par2_seconds": None,
		},
	)
	return row


def _external_row(
	method: str,
	scope: str,
	records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
	valid = [record for record in records if record.get("plan_verifier_success") is True]
	par2 = [
		float(record.get("elapsed_seconds") or 0.0)
		if record.get("plan_verifier_success") is True
		else float(2 * REGISTERED_TIMEOUT_SECONDS)
		for record in records
	]
	return {
		"method": method,
		"source": "Measured",
		"scope": scope,
		"case_count": len(records),
		"supported_case_count": len(records),
		"unsupported_case_count": 0,
		"valid_trace_count": len(valid),
		"par2_seconds": statistics.mean(par2) if par2 else None,
	}


def _temporal_result_map(
	records: Sequence[Mapping[str, Any]],
	*,
	variant: str,
) -> dict[str, Mapping[str, Any]]:
	result: dict[str, Mapping[str, Any]] = {}
	for record in records:
		sample_id = str(record.get("sample_id") or "")
		if sample_id in result:
			raise ValueError(
				f"duplicate temporal result sample for {variant}: {sample_id}",
			)
		result[sample_id] = dict(record)
	return result


def _validate_challenge_matrix(summary: Mapping[str, Any]) -> tuple[int, int]:
	records = tuple(dict(record) for record in summary.get("records") or ())
	observed_ids = tuple(str(record.get("node_id") or "") for record in records)
	registered_ids = set(REGISTERED_CHALLENGE_NODE_IDS)
	if (
		len(records) != len(REGISTERED_CHALLENGE_NODE_IDS)
		or len(set(observed_ids)) != len(observed_ids)
		or set(observed_ids) != registered_ids
	):
		raise ValueError(
			"challenge matrix does not contain the unique registered cases",
		)
	case_count = int(summary.get("case_count") or 0)
	success_count = int(summary.get("success_count") or 0)
	observed_success_count = sum(record.get("success") is True for record in records)
	if (
		case_count != len(records)
		or success_count != observed_success_count
		or success_count != case_count
	):
		raise ValueError(
			"challenge matrix is incomplete: "
			f"{success_count}/{case_count}",
		)
	return case_count, success_count


def _achievement_validation_map(
	records: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
	result: dict[str, Mapping[str, Any]] = {}
	for record in records:
		key = f"{record.get('domain')}:{Path(str(record.get('problem_file'))).name}"
		if key in result:
			raise ValueError(f"duplicate achievement validation case: {key}")
		result[key] = record
	return result


def _achievement_valid(record: Mapping[str, Any]) -> bool:
	return record.get("success") is True and record.get("plan_verifier_success") is True


def _temporal_valid(record: Mapping[str, Any]) -> bool:
	validation = dict(record.get("execution_validation") or {})
	return (
		record.get("success") is True
		and record.get("jason_status") == "success"
		and validation.get("val_success") is True
		and validation.get("gold_accepted") is True
		and validation.get("prediction_accepted") is True
	)


def _direct_temporal_valid(record: Mapping[str, Any]) -> bool:
	validation = dict(record.get("execution_validation") or {})
	return (
		record.get("supported") is True
		and record.get("success") is True
		and validation.get("val_success") is True
		and validation.get("gold_accepted") is True
		and validation.get("prediction_accepted") is True
	)


def render_atomic_table(result: Mapping[str, Any]) -> str:
	"""Render the paired atomic baseline and ablation table."""

	lines = [
		"% Auto-generated by scripts/generate_aaai_comparison_tables.py.",
		"\\begin{table}[htbp]",
		"\\centering",
		"\\small",
		"\\setlength{\\tabcolsep}{4pt}",
		"\\begin{tabular}{lrrr}",
		"\\toprule",
		r"Method & Valid (\%) & Branches & KiB \\",
		"\\midrule",
	]
	for row in result["atomic"]:
		variant = str(row["variant"])
		method = str(row["method"])
		valid = f"{100 * int(row['valid_trace_count']) / int(row['test_count']):.1f}"
		branches = _mean_sd_text(row["mean_branch_count"], row["sd_branch_count"])
		library_kib = _mean_sd_text(row["mean_library_kib"], row["sd_library_kib"])
		if variant in {"maximal_certified_program", "full"}:
			valid = f"\\resultbest{{{valid}}}"
		if variant == "full":
			method = f"\\resultselected{{{method}}}"
			branches = f"\\resultselected{{{branches}}}"
			library_kib = f"\\resultselected{{{library_kib}}}"
		lines.append(
			f"{method} & {valid} & {branches} & {library_kib} " + r"\\",
		)
	lines.extend(
		(
			"\\bottomrule",
			"\\end{tabular}",
			"\\caption{Paired atomic compiler comparison over 6,140 held-out seed--case",
			"executions (16 domains, 1,228 cases, five fixed seeds). All four variants",
			"compile all 80 libraries and reach the 365 producible targets except Evidence",
			"Only (90/365). Valid requires Jason success and original-goal VAL; Branches and",
			"KiB (library size) are mean $\\pm$ sample standard deviation across seeds. Bold",
			"marks tied best coverage; blue bold marks Full GP2PL and its smaller core at",
			"equal coverage. Full configuration and timing appear in the Technical",
			"Supplement.}",
			"\\label{tab:atomic-comparison}",
			"\\end{table}",
		),
	)
	return "\n".join(lines) + "\n"


def render_temporal_table(result: Mapping[str, Any]) -> str:
	"""Render the paired temporal baseline and ablation table."""

	lines = [
		"% Auto-generated by scripts/generate_aaai_comparison_tables.py.",
		"\\begin{table}[htbp]",
		"\\centering",
		"\\small",
		"\\setlength{\\tabcolsep}{4pt}",
		"\\begin{tabular}{@{}lrrrr@{}}",
		"\\toprule",
		r"Method & Valid & PAR-2 s & Plans & Fan-out \\",
		"\\midrule",
	]
	for row in result["temporal"]:
		variant = str(row["variant"])
		method = str(row["method"])
		valid = f"{row['valid_trace_count']}/{row['test_count']}"
		fanout = str(row["maximum_trigger_fanout"])
		if variant in {"certified_flat", "certified_balanced"}:
			valid = f"\\resultbest{{{valid}}}"
		if variant == "certified_balanced":
			method = f"\\resultselected{{{method}}}"
			fanout = f"\\resultselected{{{fanout}}}"
		lines.append(
			f"{method} & {valid} & {_number(row['par2_seconds'])} & "
			f"{_number(row['median_controller_plan_count'])} & "
			f"{fanout} " + r"\\",
		)
	lines.extend(
		(
			"\\bottomrule",
			"\\end{tabular}",
			"\\caption{Paired temporal compiler comparison over 1,228 queries with identical",
			"DFA, binding, and atomic-library inputs; all four build controllers for every",
			"query. Valid requires Jason, neutral-goal VAL, and acceptance by the gold and",
			"predicted DFA trace oracles. PAR-2 charges failures twice the 1,800-second",
			"limit. Plans is the median controller size and Fan-out its maximum",
			"transition-repair value. Bold marks tied best coverage; blue bold marks Balanced",
			"and its lower fan-out relative to equal-coverage Flat. Color is not used alone.}",
			"\\label{tab:temporal-comparison}",
			"\\end{table}",
		),
	)
	return "\n".join(lines) + "\n"


def render_external_table(result: Mapping[str, Any]) -> str:
	"""Render task-level external planning references without mixing scopes."""

	lines = [
		"% Auto-generated by scripts/generate_aaai_comparison_tables.py.",
		"\\begin{table*}[htbp]",
		"\\centering",
		"\\small",
		"\\setlength{\\tabcolsep}{3.2pt}",
		"\\begin{tabular}{lllrrr}",
		"\\toprule",
		r"Method & Source & Scope & Coverage & Unsupported & PAR-2 s \\",
		"\\midrule",
	]
	for row in result["external"]:
		coverage = f"{_number(row['valid_trace_count'])}/{row['case_count']}"
		if row.get("coverage_sample_sd") is not None:
			coverage = (
				f"{_number(row['valid_trace_count'])} $\\pm$ "
				f"{_number(row['coverage_sample_sd'])}/{row['case_count']}"
			)
		lines.append(
			f"{row['method']} & {row.get('source', 'Measured')} & {row['scope']} & "
			f"{coverage} & "
			f"{row['unsupported_case_count']} & {_number(row['par2_seconds'])} "
			+ r"\\",
		)
	lines.extend(
		(
			"\\bottomrule",
			"\\end{tabular}",
			"\\caption{Scope-separated external planning references. Reported MOOSE "
			"coverage is copied from Table~4 of the five-seed extended paper~"
			"\\cite{Chen2025MooseExtended}; its runtime is not compared with local "
			"measurements. Measured rows use a 1,800-second, 8-GiB per-task budget, and "
			"PAR-2 charges nonvalid supported cases twice the cutoff. Raw MOOSE "
			"extension coverage is mean $\\pm$ sample standard deviation over five "
			"seeds; its runtime is omitted by protocol. FOND4LTLf unsupported inputs "
			"are excluded from its coverage denominator and separated from planner "
			"and compiler failures. Rows with different scopes are not ranked.}",
			"\\label{tab:external-references}",
			"\\end{table*}",
		),
	)
	return "\n".join(lines) + "\n"


def render_comparison_macros(result: Mapping[str, Any]) -> str:
	"""Render aggregate challenge and joint-case macros for manuscript prose."""

	challenges = dict(result["challenges"])
	atomic_rows = tuple(dict(row) for row in result["atomic"])
	temporal_rows = tuple(dict(row) for row in result["temporal"])
	lines = [
		"% Auto-generated by scripts/generate_aaai_comparison_tables.py.",
		f"\\newcommand{{\\ChallengeCaseCount}}{{{challenges['case_count']}}}",
		f"\\newcommand{{\\ChallengeSuccessCount}}{{{challenges['success_count']}}}",
		"\\newcommand{\\AtomicJointActionCaseCount}"
		f"{{{result['atomic_joint_action_case_count']}}}",
		"\\newcommand{\\TemporalJointActionCaseCount}"
		f"{{{result['temporal_joint_action_case_count']}}}",
		f"\\newcommand{{\\AtomicAblationCaseCount}}{{{atomic_rows[0]['test_count']}}}",
		f"\\newcommand{{\\TemporalAblationCaseCount}}{{{temporal_rows[0]['test_count']}}}",
	]
	for row in atomic_rows:
		prefix = ATOMIC_MACRO_PREFIXES[str(row["variant"])]
		lines.extend(
			(
				f"\\newcommand{{\\{prefix}ValidCount}}{{{row['valid_trace_count']}}}",
				f"\\newcommand{{\\{prefix}FailureCount}}"
				f"{{{int(row['test_count']) - int(row['valid_trace_count'])}}}",
				f"\\newcommand{{\\{prefix}CoveredTargetCount}}"
				f"{{{row['covered_target_count']}}}",
				f"\\newcommand{{\\{prefix}BranchMean}}"
				f"{{{_number(row['mean_branch_count'])}}}",
				f"\\newcommand{{\\{prefix}LibraryKiBMean}}"
				f"{{{_number(row['mean_library_kib'])}}}",
			),
		)
	for row in temporal_rows:
		prefix = TEMPORAL_MACRO_PREFIXES[str(row["variant"])]
		lines.extend(
			(
				f"\\newcommand{{\\{prefix}ValidCount}}{{{row['valid_trace_count']}}}",
				f"\\newcommand{{\\{prefix}FailureCount}}"
				f"{{{int(row['test_count']) - int(row['valid_trace_count'])}}}",
				f"\\newcommand{{\\{prefix}ParTwoSeconds}}"
				f"{{{_number(row['par2_seconds'])}}}",
				f"\\newcommand{{\\{prefix}Fanout}}"
				f"{{{row['maximum_trigger_fanout']}}}",
			),
		)
	status_macro_suffixes = {
		"jason_failed": "JasonFailedCount",
		"jason_timeout": "JasonTimeoutCount",
		"gold_dfa_rejected": "GoldDFARejectedCount",
	}
	for breakdown in result.get("temporal_breakdowns") or ():
		prefix = TEMPORAL_MACRO_PREFIXES[str(breakdown["variant"])]
		status_counts = dict(breakdown.get("status_counts") or {})
		for status, suffix in status_macro_suffixes.items():
			lines.append(
				f"\\newcommand{{\\{prefix}{suffix}}}"
				f"{{{int(status_counts.get(status, 0))}}}",
			)
	paired_contrasts = dict(result.get("paired_contrasts") or {})
	contrast_macros = (
		("atomic", "AtomicEvidenceToDirectValidGain"),
		("atomic", "AtomicDirectToMaximumValidGain"),
		("atomic", "AtomicMaximumToFullValidGain"),
		("temporal", "TemporalUnprotectedToFlatValidGain"),
		("temporal", "TemporalFlatToBalancedValidGain"),
		("temporal", "TemporalBalancedToModuleReturnValidGain"),
	)
	contrast_indexes = {"atomic": 0, "temporal": 0}
	for group, macro in contrast_macros:
		rows = tuple(paired_contrasts.get(group) or ())
		index = contrast_indexes[group]
		contrast_indexes[group] += 1
		if index < len(rows):
			contrast = dict(rows[index])
			macro_base = macro.removesuffix("ValidGain")
			lines.append(
				f"\\newcommand{{\\{macro}}}"
				f"{{{int(contrast['valid_count_difference'])}}}",
			)
			lines.append(
				f"\\newcommand{{\\{macro.replace('ValidGain', 'ExactP')}}}"
				f"{{{_latex_probability(float(contrast['exact_two_sided_p']))}}}",
			)
			lines.append(
				f"\\newcommand{{\\{macro_base}LeftOnlyValidCount}}"
				f"{{{int(contrast['left_only_valid_count'])}}}",
			)
			lines.append(
				f"\\newcommand{{\\{macro_base}RightOnlyValidCount}}"
				f"{{{int(contrast['right_only_valid_count'])}}}",
			)
	atomic_by_variant = {str(row["variant"]): row for row in atomic_rows}
	maximum = atomic_by_variant.get("maximal_certified_program")
	full = atomic_by_variant.get("full")
	if maximum is not None and full is not None:
		lines.extend(
			(
				"\\newcommand{\\AtomicFullBranchReduction}"
				f"{{{_number(float(maximum['mean_branch_count']) - float(full['mean_branch_count']))}}}",
				"\\newcommand{\\AtomicFullLibraryKiBReduction}"
				f"{{{_number(float(maximum['mean_library_kib']) - float(full['mean_library_kib']))}}}",
			),
		)
	return "\n".join(lines) + "\n"


def write_comparison_files(result: Mapping[str, Any], *, output_dir: str | Path) -> None:
	"""Write deterministic compact JSON and LaTeX comparison artifacts."""

	root = Path(output_dir).expanduser().resolve()
	root.mkdir(parents=True, exist_ok=True)
	(root / "result_comparison_macros.tex").write_text(
		render_comparison_macros(result),
		encoding="utf-8",
	)
	(root / "result_atomic_comparison_table.tex").write_text(
		render_atomic_table(result),
		encoding="utf-8",
	)
	(root / "result_temporal_comparison_table.tex").write_text(
		render_temporal_table(result),
		encoding="utf-8",
	)
	(root / "result_external_reference_table.tex").write_text(
		render_external_table(result),
		encoding="utf-8",
	)
	(root / "comparison_results.json").write_text(
		json.dumps(result, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)


def _mean_sample_sd(values: Sequence[float]) -> tuple[float, float]:
	if not values:
		return 0.0, 0.0
	return float(statistics.mean(values)), (
		float(statistics.stdev(values)) if len(values) > 1 else 0.0
	)


def _median(values: Sequence[float] | Any) -> float | None:
	items = tuple(float(value) for value in values)
	return float(statistics.median(items)) if items else None


def _mean_sd_text(mean: object, sample_sd: object) -> str:
	return f"{float(mean):.1f} $\\pm$ {float(sample_sd):.1f}"


def _number(value: object) -> str:
	if value is None:
		return "--"
	number = float(value)
	return str(int(number)) if number.is_integer() else f"{number:.1f}"


def _latex_probability(value: float) -> str:
	if value == 0.0:
		return "0"
	if value < 0.001:
		mantissa, exponent = f"{value:.2e}".split("e")
		return f"{mantissa} \\times 10^{{{int(exponent)}}}"
	return f"{value:.3f}".rstrip("0").rstrip(".")


def _read_json(path: str | Path) -> dict[str, Any]:
	resolved = Path(path).expanduser().resolve()
	try:
		payload = json.loads(resolved.read_text(encoding="utf-8"))
	except (OSError, json.JSONDecodeError) as error:
		raise ValueError(f"cannot read result artifact {resolved}: {error}") from error
	if not isinstance(payload, dict):
		raise ValueError(f"result artifact is not a JSON object: {resolved}")
	return payload


def _sha256(path: Path) -> str:
	return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--paired-results", type=Path, required=True)
	parser.add_argument(
		"--published-moose-reference",
		type=Path,
		default=DEFAULT_PUBLISHED_MOOSE_REFERENCE,
		help="Verified MOOSE arXiv v1 Table 4 coverage artifact.",
	)
	parser.add_argument(
		"--raw-moose-extension-summary",
		action="append",
		required=True,
		help="Local four-domain Raw MOOSE result as SEED=FILE; repeat for seeds 0--4.",
	)
	parser.add_argument("--instance-reference-summary", type=Path, required=True)
	parser.add_argument("--direct-temporal-summary", type=Path, required=True)
	parser.add_argument("--challenge-summary", type=Path, required=True)
	parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
	return parser.parse_args()


def main() -> int:
	args = _parse_args()
	result = build_comparison_dataset(
		paired_results_file=args.paired_results,
		published_moose_reference_file=args.published_moose_reference,
		raw_moose_extension_summaries=parse_seed_file_assignments(
			args.raw_moose_extension_summary,
		),
		instance_reference_summary_file=args.instance_reference_summary,
		direct_temporal_summary_file=args.direct_temporal_summary,
		challenge_summary_file=args.challenge_summary,
	)
	write_comparison_files(result, output_dir=args.output_dir)
	print(
		"generated AAAI comparison tables "
		f"atomic={len(result['atomic'])} temporal={len(result['temporal'])} "
		f"external={len(result['external'])}",
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
