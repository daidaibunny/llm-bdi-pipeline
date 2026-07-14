#!/usr/bin/env python3
"""Validate final comparison artifacts and generate AAAI result tables."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import sys
from typing import Any
from typing import Mapping
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "latex_code/aamas_method_paper/sections"

if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_certificate_challenge_matrix import CHALLENGE_CASES  # noqa: E402
from scripts.run_certificate_challenge_matrix import METAMORPHIC_CASES  # noqa: E402


REGISTERED_SEEDS = (0, 1, 2, 3, 4)
REGISTERED_NUM_WORKERS = 6
REGISTERED_TIMEOUT_SECONDS = 1800
REGISTERED_MAX_RSS_GB = 8.0
REGISTERED_JAVA_STACK_SIZE = "64m"
PINNED_ENHSP_REVISION = "537bed55a60d9456975c56afbadd50fc8acb1dc9"
PINNED_FOND4LTLF_REVISION = "011d9d9a5bfd6406d2c358faf8f63167f6c839bb"
REGISTERED_CHALLENGE_NODE_IDS = tuple(
	case.node_id for case in (*CHALLENGE_CASES, *METAMORPHIC_CASES)
)
ATOMIC_METHODS = (
	("validated_evidence_adapter", "Evidence Only"),
	("action_only_closure", "Action Closure"),
	("maximal_certified_program", "Maximal Certified"),
	("full", "Full GP2PL"),
)
TEMPORAL_METHODS = (
	("dfa_aware_unprotected", "Unprotected DFA"),
	("certified_flat", "Certified Flat"),
	("certified_balanced", "Certified Balanced"),
	("completion_boundary_monitor", "Completion Monitor"),
)


def parse_seed_file_assignments(values: Sequence[str]) -> tuple[tuple[int, Path], ...]:
	"""Parse repeated ``SEED=FILE`` assignments for Raw MOOSE summaries."""

	assignments: dict[int, Path] = {}
	for value in values:
		seed_text, separator, filename = str(value).partition("=")
		if not separator or not seed_text.strip() or not filename.strip():
			raise ValueError(f"raw MOOSE summary must use SEED=FILE: {value!r}")
		try:
			seed = int(seed_text)
		except ValueError as error:
			raise ValueError(f"raw MOOSE seed is not an integer: {value!r}") from error
		if seed in assignments:
			raise ValueError(f"duplicate Raw MOOSE seed: {seed}")
		assignments[seed] = Path(filename).expanduser().resolve()
	if tuple(sorted(assignments)) != REGISTERED_SEEDS:
		raise ValueError("Raw MOOSE comparison requires exactly seeds 0,1,2,3,4")
	return tuple(sorted(assignments.items()))


def build_comparison_dataset(
	*,
	paired_results_file: str | Path,
	raw_moose_summaries: Sequence[tuple[int, str | Path]],
	instance_reference_summary_file: str | Path,
	direct_temporal_summary_file: str | Path,
	challenge_summary_file: str | Path,
) -> dict[str, Any]:
	"""Build a fail-closed compact dataset from every registered comparison."""

	paired_path = Path(paired_results_file).expanduser().resolve()
	instance_path = Path(instance_reference_summary_file).expanduser().resolve()
	direct_path = Path(direct_temporal_summary_file).expanduser().resolve()
	challenge_path = Path(challenge_summary_file).expanduser().resolve()
	paired = _read_json(paired_path)
	instance = _read_json(instance_path)
	direct = _read_json(direct_path)
	challenge = _read_json(challenge_path)
	raw_records = tuple(
		(seed, Path(path).expanduser().resolve(), _read_json(path))
		for seed, path in raw_moose_summaries
	)
	_validate_paired_result(paired)
	_validate_clean_success(instance, label="instance references")
	_validate_clean_success(direct, label="direct temporal reference")
	_validate_clean_success(challenge, label="challenge matrix")
	_validate_external_reference_protocol(instance, label="instance references")
	_validate_achievement_toolchain(instance, label="instance references")
	_validate_external_reference_protocol(
		direct,
		label="direct temporal reference",
		direct_temporal=True,
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
	_validate_common_source_revision(
		(
			("paired compiler result", paired),
			("instance references", instance),
			("direct temporal reference", direct),
			("challenge matrix", challenge),
			*(
				(f"Raw MOOSE seed {seed}", summary)
				for seed, _path, summary in raw_records
			),
		),
	)
	_validate_raw_moose_runs(
		raw_records,
		contract=_registered_external_case_contract(paired, "raw_moose"),
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
	external_rows = _aggregate_external(raw_records, instance, direct)
	challenge_count, challenge_success = _validate_challenge_matrix(challenge)
	return {
		"schema_version": 1,
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
			"raw_moose_summaries": [
				{
					"seed": seed,
					"file": str(path),
					"sha256": _sha256(path),
				}
				for seed, path, _summary in raw_records
			],
			"instance_reference_summary_file": str(instance_path),
			"instance_reference_summary_sha256": _sha256(instance_path),
			"direct_temporal_summary_file": str(direct_path),
			"direct_temporal_summary_sha256": _sha256(direct_path),
			"challenge_summary_file": str(challenge_path),
			"challenge_summary_sha256": _sha256(challenge_path),
		},
	}


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
	if int(paired.get("num_workers") or 0) != REGISTERED_NUM_WORKERS:
		raise ValueError("paired result does not use the registered worker count")
	if int(paired.get("timeout_seconds") or 0) != REGISTERED_TIMEOUT_SECONDS:
		raise ValueError("paired result does not use the registered timeout")
	if str(paired.get("jason_java_stack_size") or "") != REGISTERED_JAVA_STACK_SIZE:
		raise ValueError("paired result does not use the registered Java stack size")
	expected_commit = str(
		dict(paired.get("source_revision") or {}).get("commit") or "",
	)
	for run in paired.get("atomic_runs") or ():
		summary = dict(dict(run).get("summary") or {})
		_validate_child_source_revision(
			summary,
			label="atomic child run",
			expected_commit=expected_commit,
		)
		_validate_jason_protocol(
			dict(summary.get("settings") or {}),
			label="atomic child run",
		)
	for run in paired.get("temporal_runs") or ():
		run_payload = dict(run)
		_validate_child_source_revision(
			run_payload,
			label="temporal child run",
			expected_commit=expected_commit,
		)
		_validate_jason_protocol(
			dict(run_payload.get("parameters") or {}),
			label="temporal child run",
			jason_timeout_key="jason_timeout_seconds",
		)


def _validate_child_source_revision(
	payload: Mapping[str, Any],
	*,
	label: str,
	expected_commit: str,
) -> None:
	revision = dict(payload.get("source_revision") or {})
	if revision.get("tracked_changes") is not False or revision.get(
		"untracked_files",
	) is not False:
		raise ValueError(f"{label} was not executed from a clean revision")
	if str(revision.get("commit") or "") != expected_commit:
		raise ValueError(f"{label} does not share the paired source revision")


def _validate_jason_protocol(
	settings: Mapping[str, Any],
	*,
	label: str,
	jason_timeout_key: str = "timeout_seconds",
) -> None:
	if int(settings.get("num_workers") or 0) != REGISTERED_NUM_WORKERS:
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


def _validate_common_source_revision(
	records: Sequence[tuple[str, Mapping[str, Any]]],
) -> None:
	revisions = {
		str(dict(payload.get("source_revision") or {}).get("commit") or "")
		for _label, payload in records
	}
	if len(revisions) != 1:
		raise ValueError(
			"final comparison artifacts do not share the same source revision: "
			+ ", ".join(sorted(revisions)),
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
		_validate_external_reference_protocol(summary, label=f"Raw MOOSE seed {seed}")
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
	direct_temporal: bool = False,
) -> None:
	parameters = summary.get("parameters")
	if not isinstance(parameters, Mapping):
		raise ValueError(f"{label} has no resource protocol")
	if int(parameters.get("num_workers") or 0) != REGISTERED_NUM_WORKERS:
		raise ValueError(f"{label} does not use the registered worker count")
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
	for method, scope in (
		("Raw MOOSE", "Achievement, five seeds"),
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
		"\\begin{table*}[t]",
		"\\centering",
		"\\footnotesize",
		"\\setlength{\\tabcolsep}{3.1pt}",
		"\\caption{Paired atomic compiler comparison over five fixed evidence seeds. "
		"Compiled counts domain libraries; Targets uses the shared positive-add-effect "
		"predicate denominator; Valid requires Jason success and original-goal VAL. "
		"Size and time are mean $\\pm$ sample standard deviation over seeds.}",
		"\\label{tab:atomic-comparison}",
		"\\begin{tabular}{lrrrrrr}",
		"\\toprule",
		r"Method & Compiled & Targets & Valid & Branches & KiB & Compile s \\",
		"\\midrule",
	]
	for row in result["atomic"]:
		lines.append(
			f"{row['method']} & {row['compiled_count']}/{row['compiled_total']} & "
			f"{row['covered_target_count']}/{row['producible_target_count']} & "
			f"{row['valid_trace_count']}/{row['test_count']} & "
			f"{_mean_sd_text(row['mean_branch_count'], row['sd_branch_count'])} & "
			f"{_mean_sd_text(row['mean_library_kib'], row['sd_library_kib'])} & "
			f"{_mean_sd_text(row['mean_compile_seconds'], row['sd_compile_seconds'])} "
			+ r"\\",
		)
	lines.extend(("\\bottomrule", "\\end{tabular}", "\\end{table*}"))
	return "\n".join(lines) + "\n"


def render_temporal_table(result: Mapping[str, Any]) -> str:
	"""Render the paired temporal baseline and ablation table."""

	joint_count = int(result["temporal_joint_action_case_count"])
	lines = [
		"% Auto-generated by scripts/generate_aaai_comparison_tables.py.",
		"\\begin{table*}[t]",
		"\\centering",
		"\\footnotesize",
		"\\setlength{\\tabcolsep}{3.1pt}",
		"\\caption{Paired temporal compiler comparison on identical DFA, binding, and "
		"atomic-library hashes. Valid requires Jason, neutral-goal VAL, and both DFA "
		f"oracles. Actions are medians on the {joint_count} jointly solved queries."
		"}",
		"\\label{tab:temporal-comparison}",
		"\\begin{tabular}{lrrrrrr}",
		"\\toprule",
		r"Method & Built & Valid & PAR-2 s & Actions & Plans & Fan-out \\",
		"\\midrule",
	]
	for row in result["temporal"]:
		lines.append(
			f"{row['method']} & {row['compiled_count']}/{row['test_count']} & "
			f"{row['valid_trace_count']}/{row['test_count']} & "
			f"{_number(row['par2_seconds'])} & "
			f"{_number(row['median_joint_action_count'])} & "
			f"{_number(row['median_controller_plan_count'])} & "
			f"{row['maximum_trigger_fanout']} " + r"\\",
		)
	lines.extend(("\\bottomrule", "\\end{tabular}", "\\end{table*}"))
	return "\n".join(lines) + "\n"


def render_external_table(result: Mapping[str, Any]) -> str:
	"""Render task-level external planning references without mixing scopes."""

	lines = [
		"% Auto-generated by scripts/generate_aaai_comparison_tables.py.",
		"\\begin{table*}[t]",
		"\\centering",
		"\\footnotesize",
		"\\setlength{\\tabcolsep}{4.0pt}",
		"\\caption{Native external planning references under the same 30-minute, 8-GiB "
		"per-task budget. Denominators follow each tool's declared scope; unsupported "
		"FOND4LTLf inputs are reported separately from planner failures.}",
		"\\label{tab:external-references}",
		"\\begin{tabular}{llrrr}",
		"\\toprule",
		r"Method & Scope & Valid & Unsupported & PAR-2 s \\",
		"\\midrule",
	]
	for row in result["external"]:
		lines.append(
			f"{row['method']} & {row['scope']} & "
			f"{row['valid_trace_count']}/{row['case_count']} & "
			f"{row['unsupported_case_count']} & {_number(row['par2_seconds'])} "
			+ r"\\",
		)
	lines.extend(("\\bottomrule", "\\end{tabular}", "\\end{table*}"))
	return "\n".join(lines) + "\n"


def render_comparison_macros(result: Mapping[str, Any]) -> str:
	"""Render aggregate challenge and joint-case macros for manuscript prose."""

	challenges = dict(result["challenges"])
	return "\n".join(
		(
			"% Auto-generated by scripts/generate_aaai_comparison_tables.py.",
			f"\\newcommand{{\\ChallengeCaseCount}}{{{challenges['case_count']}}}",
			f"\\newcommand{{\\ChallengeSuccessCount}}{{{challenges['success_count']}}}",
			"\\newcommand{\\AtomicJointActionCaseCount}"
			f"{{{result['atomic_joint_action_case_count']}}}",
			"\\newcommand{\\TemporalJointActionCaseCount}"
			f"{{{result['temporal_joint_action_case_count']}}}",
		)
	) + "\n"


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
		"--raw-moose-summary",
		action="append",
		default=[],
		help="Raw MOOSE result as SEED=FILE; repeat for seeds 0--4.",
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
		raw_moose_summaries=parse_seed_file_assignments(args.raw_moose_summary),
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
