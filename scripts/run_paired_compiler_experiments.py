#!/usr/bin/env python3
"""Run hash-paired atomic and temporal compiler comparisons."""

from __future__ import annotations

import argparse
from collections import Counter
import copy
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
from typing import Any, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
DEFAULT_BATCH_ROOT = PROJECT_ROOT / "artifacts/moose_asl_batches"
DEFAULT_BENCHMARK_ROOT = PROJECT_ROOT / "paper_artifacts/temporal_goal_benchmark/v1"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "artifacts/paired_compiler_experiments"
REGISTERED_SEEDS = (0, 1, 2, 3, 4)

if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from domain_level_planning import AtomicCompilerVariant  # noqa: E402
from domain_level_planning import TemporalCompilerVariant  # noqa: E402
from domain_level_planning import evidence_program_from_moose_readable_policy  # noqa: E402
from domain_level_planning import policy_evidence_program_fingerprint  # noqa: E402
from evaluation.external_reference_planners import (  # noqa: E402
	ExternalReferenceMethod,
)
from evaluation.external_reference_planners import (  # noqa: E402
	reference_methods_for_domain,
)
from scripts.run_external_planning_references import (  # noqa: E402
	model_batch_manifest_metadata,
)
from scripts.run_moose_faithful_e2e import DEFAULT_DOMAINS  # noqa: E402


@dataclass(frozen=True)
class RegisteredRun:
	"""One isolated subprocess and the summary artifact it must produce."""

	stage: str
	method: str
	variant: str
	run_id: str
	command: tuple[str, ...]
	summary_file: Path
	seed: int | None = None
	input_batch_id: str | None = None


@dataclass(frozen=True)
class TemporalAtomicInput:
	"""Exact atomic-library root consumed by every temporal compiler variant."""

	batch_root: Path
	batch_id: str
	evidence_batch_id: str
	provenance: str


def parse_seed_batch_assignments(values: Sequence[str]) -> dict[int, str]:
	"""Parse repeated ``SEED=BATCH_ID`` arguments without implicit seed ordering."""

	assignments: dict[int, str] = {}
	for raw_value in values:
		seed_text, separator, batch_id = str(raw_value).partition("=")
		if not separator or not seed_text.strip() or not batch_id.strip():
			raise ValueError(
				f"seed batch assignment must use SEED=BATCH_ID: {raw_value!r}",
			)
		try:
			seed = int(seed_text)
		except ValueError as error:
			raise ValueError(
				f"seed batch assignment must use integer SEED=BATCH_ID: {raw_value!r}",
			) from error
		if seed in assignments:
			raise ValueError(f"duplicate seed batch assignment: {seed}")
		assignments[seed] = batch_id.strip()
	return assignments


def resolve_temporal_atomic_input(
	*,
	stage: str,
	run_id: str,
	atomic_output_root: Path,
	evidence_batch_root: Path,
	requested_batch_id: str | None,
	seed_batches: Mapping[int, str],
) -> TemporalAtomicInput:
	"""Bind temporal variants to a current Full Compiler atomic artifact."""

	if stage == "all":
		if requested_batch_id:
			raise ValueError(
				"--temporal-batch-id is temporal-only; --stage all always consumes "
				"the same-run seed-0 Full Compiler output.",
			)
		evidence_batch_id = seed_batches.get(0)
		if not evidence_batch_id:
			raise ValueError("--stage all requires the registered seed-0 evidence batch")
		return TemporalAtomicInput(
			batch_root=atomic_output_root,
			batch_id=f"{run_id}-seed0-{AtomicCompilerVariant.FULL.value}",
			evidence_batch_id=evidence_batch_id,
			provenance="same_run_seed0_full_compiler",
		)
	if stage == "temporal":
		batch_id = requested_batch_id or seed_batches.get(0)
		if not batch_id:
			raise ValueError("temporal stage requires --temporal-batch-id")
		return TemporalAtomicInput(
			batch_root=evidence_batch_root,
			batch_id=batch_id,
			evidence_batch_id=batch_id,
			provenance="explicit_precompiled_batch",
		)
	raise ValueError(f"No temporal atomic input exists for stage {stage!r}")


def validate_resume_manifest(
	previous: Mapping[str, Any],
	current: Mapping[str, Any],
) -> None:
	"""Require an interrupted paired run to retain its exact registered contract."""

	immutable_keys = (
		"domains",
		"registered_seeds",
		"case_contract",
		"seed_batches",
		"seed_batch_manifests",
		"generate_evidence",
		"temporal_atomic_input",
		"num_workers",
		"timeout_seconds",
		"jason_java_stack_size",
		"paper_matrix_complete",
		"runs",
	)
	for key in immutable_keys:
		if previous.get(key) != current.get(key):
			raise ValueError(f"resume contract mismatch for {key}")


def registered_run_summary_complete(
	run: RegisteredRun,
) -> bool:
	"""Return whether a child summary contains its complete registered outcome."""

	if run.stage == "Evidence" or not run.summary_file.is_file():
		return False
	payload = _read_json(run.summary_file)
	if run.stage in {"Atomic", "Temporal"}:
		return bool(payload.get("completed_at"))
	case_count = int(payload.get("case_count") or 0)
	return case_count > 0 and len(tuple(payload.get("records") or ())) == case_count


def validate_seed_batch_manifest(
	*,
	batch_root: Path,
	seed: int,
	domains: Sequence[str],
) -> dict[str, Any]:
	"""Validate one evidence batch against the registered seeded protocol."""

	manifest_file = batch_root / "batch_manifest.json"
	if not manifest_file.is_file():
		raise ValueError(f"Seed {seed} batch has no manifest: {manifest_file}")
	manifest = _read_json(manifest_file)
	settings = manifest.get("settings")
	if not isinstance(settings, Mapping):
		raise ValueError(f"Seed {seed} batch manifest has no settings")
	if int(settings.get("random_seed", -1)) != int(seed):
		raise ValueError(f"Evidence batch does not use assigned seed {seed}")
	expected_settings = {
		"num_workers": 1,
		"num_permutations": 3,
		"goal_max_size": 1,
		"train_timeout_seconds": 43200,
	}
	for key, value in expected_settings.items():
		if int(settings.get(key) or 0) != value:
			raise ValueError(f"Seed {seed} batch has nonregistered setting {key}")
	if float(settings.get("max_rss_gb") or 0.0) != 16.0:
		raise ValueError(f"Seed {seed} batch has nonregistered memory limit")
	manifest_domains = tuple(str(domain) for domain in manifest.get("domains") or ())
	if set(manifest_domains) != set(domains) or len(manifest_domains) != len(domains):
		raise ValueError(f"Seed {seed} batch domain set does not match the experiment")
	metadata = model_batch_manifest_metadata(batch_root, domains=domains)
	return {**metadata, "domains": list(manifest_domains)}


def build_evidence_run_command(
	*,
	project_root: Path,
	batch_root: Path,
	batch_id: str,
	seed: int,
	domains: Sequence[str],
) -> tuple[str, ...]:
	"""Build one isolated paper-protocol MOOSE evidence synthesis run."""

	command = [
		"uv",
		"run",
		"python",
		str(project_root / "scripts/run_timestamped_moose_asl_batch.py"),
		"--artifact-root",
		str(batch_root),
		"--timestamp-id",
		str(batch_id),
		"--num-workers",
		"1",
		"--random-seed",
		str(int(seed)),
		"--num-permutations",
		"3",
		"--goal-max-size",
		"1",
		"--atomic-library-mode",
		"validated-policy-lifting",
		"--compiler-variant",
		AtomicCompilerVariant.FULL.value,
		"--max-rss-gb",
		"16",
		"--train-timeout-seconds",
		"43200",
		"--skip-temporal-append",
	]
	for domain in domains:
		command.extend(("--domain", str(domain)))
	return tuple(command)


def build_atomic_run_command(
	*,
	project_root: Path,
	batch_root: Path,
	batch_id: str,
	output_root: Path,
	run_id: str,
	variant: AtomicCompilerVariant,
	domains: Sequence[str],
	num_workers: int,
	timeout_seconds: int,
	java_stack_size: str,
	plan_verifier_command: str,
) -> tuple[str, ...]:
	"""Build one full held-out Jason and VAL run for one atomic variant."""

	command = [
		"uv",
		"run",
		"python",
		str(project_root / "scripts/run_full_test_jason_validation.py"),
		"--batch-root",
		str(batch_root),
		"--batch-id",
		str(batch_id),
		"--output-root",
		str(output_root),
		"--run-id",
		run_id,
		"--num-workers",
		str(max(1, int(num_workers))),
		"--timeout-seconds",
		str(max(1, int(timeout_seconds))),
		"--plan-verifier-timeout-seconds",
		str(max(1, int(timeout_seconds))),
		"--jason-java-stack-size",
		str(java_stack_size),
		"--plan-verifier-command",
		str(plan_verifier_command),
		"--atomic-library-mode",
		"validated-policy-lifting",
		"--compiler-variant",
		variant.value,
		"--suppress-final-summary-json",
		"--resume",
	]
	for domain in domains:
		command.extend(("--domain", str(domain)))
	return tuple(command)


def build_temporal_run_command(
	*,
	project_root: Path,
	benchmark_root: Path,
	batch_root: Path,
	batch_id: str,
	output_root: Path,
	run_id: str,
	variant: TemporalCompilerVariant,
	domains: Sequence[str],
	num_workers: int,
	timeout_seconds: int,
	java_stack_size: str,
	plan_verifier_command: str,
) -> tuple[str, ...]:
	"""Build one full TEG run for one temporal compiler variant."""

	command = [
		"uv",
		"run",
		"python",
		str(project_root / "scripts/run_temporal_goal_benchmark_execution.py"),
		"--benchmark-root",
		str(benchmark_root),
		"--batch-root",
		str(batch_root),
		"--batch-id",
		str(batch_id),
		"--output-root",
		str(output_root),
		"--run-id",
		run_id,
		"--num-workers",
		str(max(1, int(num_workers))),
		"--timeout-seconds",
		str(max(1, int(timeout_seconds))),
		"--plan-verifier-timeout-seconds",
		str(max(1, int(timeout_seconds))),
		"--jason-java-stack-size",
		str(java_stack_size),
		"--plan-verifier-command",
		str(plan_verifier_command),
		"--temporal-compiler-variant",
		variant.value,
		"--resume",
	]
	for domain in domains:
		command.extend(("--domain", str(domain)))
	return tuple(command)


def build_challenge_run_command(
	*,
	project_root: Path,
	output_root: Path,
	run_id: str,
) -> tuple[str, ...]:
	"""Build the registered certificate and symbol-invariance matrix command."""

	return (
		"uv",
		"run",
		"python",
		str(project_root / "scripts/run_certificate_challenge_matrix.py"),
		"--output-root",
		str(output_root),
		"--run-id",
		run_id,
	)


def build_registered_case_contract(
	*,
	project_root: Path,
	benchmark_root: Path,
	domains: Sequence[str],
) -> dict[str, Any]:
	"""Fingerprint every registered held-out case before any method runs."""

	achievement_cases: list[str] = []
	external_cases: dict[str, list[str]] = {
		ExternalReferenceMethod.RAW_MOOSE.value: [],
		ExternalReferenceMethod.LAMA.value: [],
		ExternalReferenceMethod.ENHSP_HMRPHJ.value: [],
	}
	benchmark_file = benchmark_root / "benchmark.json"
	benchmark = _read_json(benchmark_file)
	benchmark_domains = benchmark.get("domains")
	if not isinstance(benchmark_domains, Mapping):
		raise ValueError("Temporal benchmark has no domain case mapping.")
	temporal_cases: list[str] = []
	for domain in domains:
		domain_root = project_root / "src/domains" / domain
		domain_file = domain_root / "domain.pddl"
		test_dir = domain_root / "test"
		if not domain_file.is_file() or not test_dir.is_dir():
			raise ValueError(f"Missing registered domain or test split: {domain}")
		problem_files = tuple(sorted(test_dir.glob("*.pddl")))
		if not problem_files:
			raise ValueError(f"Registered domain has no held-out problems: {domain}")
		applicable = set(reference_methods_for_domain(domain_file))
		for problem_file in problem_files:
			case_id = f"{domain}:{problem_file.name}"
			achievement_cases.append(case_id)
			for method in applicable:
				external_cases[method.value].append(case_id)
		domain_payload = benchmark_domains.get(domain)
		if not isinstance(domain_payload, Mapping):
			raise ValueError(f"Temporal benchmark is missing domain: {domain}")
		cases = domain_payload.get("cases")
		if not isinstance(cases, Mapping) or not cases:
			raise ValueError(f"Temporal benchmark has no cases for domain: {domain}")
		temporal_cases.extend(str(case_id) for case_id in cases)
	return {
		"achievement": _case_set_contract(achievement_cases),
		"temporal": {
			**_case_set_contract(temporal_cases),
			"benchmark_sha256": _sha256(benchmark_file),
		},
		"external": {
			method: _case_set_contract(case_ids)
			for method, case_ids in external_cases.items()
		},
	}


def _case_set_contract(case_ids: Sequence[str]) -> dict[str, Any]:
	unique_ids = {str(case_id) for case_id in case_ids}
	if len(unique_ids) != len(case_ids):
		raise ValueError("Registered case set contains duplicate identifiers.")
	encoded = json.dumps(
		sorted(unique_ids),
		separators=(",", ":"),
	).encode("utf-8")
	return {
		"count": len(unique_ids),
		"sha256": hashlib.sha256(encoded).hexdigest(),
	}


def validate_atomic_pairing(
	runs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
	"""Require all variants for one seed/domain to share exact evidence inputs."""

	groups: dict[tuple[int, str], list[tuple[str, Mapping[str, Any]]]] = {}
	for run in runs:
		seed = int(run["seed"])
		variant = str(run.get("variant") or "")
		for domain, record in dict(run.get("domains") or {}).items():
			groups.setdefault((seed, str(domain)), []).append(
				(variant, dict(record or {})),
			)
	expected_variants = {variant.value for variant in AtomicCompilerVariant}
	for (seed, domain), variant_records in groups.items():
		observed_variants = {variant for variant, _record in variant_records}
		if observed_variants != expected_variants:
			raise ValueError(
				"atomic variant matrix incomplete for "
				f"seed={seed}, domain={domain}: {sorted(observed_variants)}",
			)
		records = [record for _variant, record in variant_records]
		raw_hashes = {
			str(record.get("readable_policy_sha256") or "") for record in records
		}
		if "" in raw_hashes or len(raw_hashes) != 1:
			raise ValueError(
				f"readable evidence hash mismatch for seed={seed}, domain={domain}",
			)
		normalized_hashes = {
			str(record.get("evidence_program_fingerprint") or "")
			for record in records
		}
		if "" in normalized_hashes or len(normalized_hashes) != 1:
			raise ValueError(
				"normalized evidence fingerprint mismatch for "
				f"seed={seed}, domain={domain}",
			)
	return {
		"paired": True,
		"seed_domain_group_count": len(groups),
	}


def validate_temporal_pairing(
	runs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
	"""Require temporal variants to share benchmark, library, and DFA inputs."""

	if not runs:
		return {"paired": True, "sample_count": 0}
	observed_variants = {str(run.get("variant") or "") for run in runs}
	expected_variants = {variant.value for variant in TemporalCompilerVariant}
	if observed_variants != expected_variants:
		raise ValueError(
			f"temporal variant matrix incomplete: {sorted(observed_variants)}",
		)
	benchmark_hashes = {str(run.get("benchmark_sha256") or "") for run in runs}
	if "" in benchmark_hashes or len(benchmark_hashes) != 1:
		raise ValueError("temporal benchmark fingerprint mismatch")
	domain_names = {
		str(domain)
		for run in runs
		for domain in dict(run.get("atomic_library_inputs") or {})
	}
	for domain in domain_names:
		library_hashes = {
			(
				str(record.get("plan_library_json_sha256") or ""),
				str(record.get("plan_library_asl_sha256") or ""),
			)
			for run in runs
			for record in (
				dict(run.get("atomic_library_inputs") or {}).get(domain, {}),
			)
		}
		if any(not all(item) for item in library_hashes) or len(library_hashes) != 1:
			raise ValueError(f"atomic library fingerprint mismatch for domain={domain}")
	results_by_variant: dict[str, dict[str, str]] = {}
	controller_fingerprints: set[str] = set()
	for run in runs:
		variant = str(run.get("variant") or "")
		variant_results: dict[str, str] = {}
		for record in tuple(run.get("results") or ()):
			sample_id = str(record.get("sample_id") or "")
			fingerprint = str(record.get("dfa_fingerprint") or "")
			controller_fingerprint = str(
				record.get("controller_fingerprint") or "",
			)
			if not sample_id:
				raise ValueError(f"temporal result without sample id for variant={variant}")
			if not fingerprint:
				raise ValueError(
					f"missing DFA fingerprint for variant={variant}, sample={sample_id}",
				)
			if not controller_fingerprint:
				raise ValueError(
					"missing controller fingerprint for "
					f"variant={variant}, sample={sample_id}",
				)
			if sample_id in variant_results:
				raise ValueError(
					f"duplicate temporal sample for variant={variant}, sample={sample_id}",
				)
			variant_results[sample_id] = fingerprint
			controller_fingerprints.add(controller_fingerprint)
		results_by_variant[variant] = variant_results
	reference_sample_ids = set(next(iter(results_by_variant.values())))
	for variant, variant_results in results_by_variant.items():
		if set(variant_results) != reference_sample_ids:
			raise ValueError(
				"temporal sample matrix incomplete for "
				f"variant={variant}: observed={len(variant_results)}, "
				f"expected={len(reference_sample_ids)}",
			)
	for sample_id in sorted(reference_sample_ids):
		fingerprints = {
			variant_results[sample_id]
			for variant_results in results_by_variant.values()
		}
		if len(fingerprints) != 1:
			raise ValueError(f"DFA fingerprint mismatch for sample={sample_id}")
	return {
		"paired": True,
		"sample_count": len(reference_sample_ids),
		"domain_count": len(domain_names),
		"controller_fingerprint_count": len(controller_fingerprints),
	}


def pairing_outcome(
	*,
	label: str,
	runs: Sequence[Mapping[str, Any]],
	validator: Any,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
	"""Persist a failed controlled-input check instead of losing the run report."""

	if not runs:
		return None, None
	try:
		return dict(validator(runs)), None
	except ValueError as error:
		message = str(error)
		return (
			{"paired": False, "error": message},
			{
				"stage": "Pairing",
				"method": label,
				"error": message,
			},
		)


def atomic_library_metrics(
	library_file: Path,
	asl_file: Path,
) -> dict[str, Any]:
	"""Extract paper-table structure metrics from one emitted atomic library."""

	payload = _read_json(library_file)
	plans = tuple(payload.get("plans") or ())
	metadata = dict(payload.get("metadata") or {})
	synthesis = dict(metadata.get("atomic_module_synthesis") or {})
	source_counts = dict(synthesis.get("candidate_source_counts") or {})
	raw_roles = synthesis.get("predicate_roles")
	denominator_available = isinstance(raw_roles, (list, tuple))
	roles = tuple(raw_roles or ())
	producible_roles = tuple(
		dict(role)
		for role in roles
		if isinstance(role, Mapping)
		and role.get("role") == "producible_fluent"
		and bool(role.get("expected_module"))
	)
	covered_roles = tuple(
		role for role in producible_roles if bool(role.get("emitted_module"))
	)
	module_predicates = tuple(
		sorted(str(item) for item in tuple(synthesis.get("module_predicates") or ()))
	)
	declared_producible_targets = tuple(
		sorted(
			str(role.get("predicate"))
			for role in producible_roles
			if str(role.get("predicate") or "").strip()
		)
	)
	context_literal_count = 0
	body_step_count = 0
	primitive_action_step_count = 0
	subgoal_step_count = 0
	for raw_plan in plans:
		plan = dict(raw_plan or {})
		context_literal_count += len(tuple(plan.get("context") or ()))
		body = tuple(plan.get("body") or ())
		body_step_count += len(body)
		for raw_step in body:
			step = dict(raw_step or {})
			if step.get("kind") == "action":
				primitive_action_step_count += 1
			elif step.get("kind") == "subgoal":
				subgoal_step_count += 1
	return {
		"candidate_count": int(synthesis.get("raw_candidate_count") or 0),
		"evidence_candidate_count": int(
			source_counts.get("validated_evidence") or 0,
		),
		"schema_candidate_count": int(source_counts.get("schema") or 0),
		"selected_branch_count": len(plans),
		"module_count": len(module_predicates),
		"module_predicates": module_predicates,
		"declared_producible_target_predicates": declared_producible_targets,
		"producible_target_denominator_available": denominator_available,
		"producible_target_count": len(producible_roles),
		"covered_target_count": len(covered_roles),
		"module_closure_complete": len(covered_roles) == len(producible_roles),
		"context_literal_count": context_literal_count,
		"body_step_count": body_step_count,
		"primitive_action_step_count": primitive_action_step_count,
		"subgoal_step_count": subgoal_step_count,
		"asl_bytes": asl_file.stat().st_size,
	}


def apply_common_target_coverage(
	runs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
	"""Apply one PDDL-derived target denominator to every paired atomic variant."""

	normalized = copy.deepcopy(list(runs))
	groups: dict[tuple[int, str], list[dict[str, Any]]] = {}
	for run in normalized:
		seed = int(run["seed"])
		for domain, raw_record in dict(run.get("domains") or {}).items():
			groups.setdefault((seed, str(domain)), []).append(dict(raw_record or {}))
	for (seed, domain), records in groups.items():
		full_record = next(
			(
				dict(run.get("domains") or {}).get(domain)
				for run in normalized
				if int(run["seed"]) == seed
				and str(run.get("variant") or "") == AtomicCompilerVariant.FULL.value
			),
			None,
		)
		full_metrics = dict(dict(full_record or {}).get("library_metrics") or {})
		if not bool(full_metrics.get("producible_target_denominator_available")):
			raise ValueError(
				"missing full compiler target denominator for "
				f"seed={seed}, domain={domain}",
			)
		expected = tuple(
			sorted(
				str(item)
				for item in tuple(
					full_metrics.get("declared_producible_target_predicates") or (),
				)
			)
		)
		for run in normalized:
			if int(run["seed"]) != seed:
				continue
			domain_record = dict(run.get("domains") or {}).get(domain)
			if domain_record is None:
				continue
			metrics = dict(dict(domain_record).get("library_metrics") or {})
			modules = {
				str(item) for item in tuple(metrics.get("module_predicates") or ())
			}
			covered = tuple(item for item in expected if item in modules)
			metrics.update(
				{
					"common_producible_target_predicates": expected,
					"covered_producible_target_predicates": covered,
					"producible_target_count": len(expected),
					"covered_target_count": len(covered),
					"module_closure_complete": len(covered) == len(expected),
				},
			)
			domain_record["library_metrics"] = metrics
	return normalized


def execution_metrics(
	records: Sequence[Mapping[str, Any]],
	*,
	timeout_seconds: int,
) -> dict[str, Any]:
	"""Aggregate coverage, valid traces, plan length, and PAR-2 runtime."""

	items = tuple(records)
	solved = tuple(item for item in items if bool(item.get("success")))
	valid = tuple(
		item
		for item in solved
		if bool(item.get("plan_verifier_success"))
		or bool(dict(item.get("execution_validation") or {}).get("val_success"))
	)
	action_counts = tuple(
		int(item["action_count"])
		for item in valid
		if item.get("action_count") is not None
	)
	solved_durations = tuple(float(item.get("duration_seconds") or 0.0) for item in valid)
	valid_record_ids = {id(item) for item in valid}
	cutoff = max(1, int(timeout_seconds))
	par2_values = tuple(
		float(item.get("duration_seconds") or 0.0)
		if id(item) in valid_record_ids
		else float(2 * cutoff)
		for item in items
	)
	return {
		"test_count": len(items),
		"success_count": len(solved),
		"valid_trace_count": len(valid),
		"timeout_count": sum(
			bool(item.get("timed_out")) or bool(item.get("jason_timed_out"))
			for item in items
		),
		"status_counts": dict(
			sorted(Counter(str(item.get("status") or "unknown") for item in items).items()),
		),
		"median_action_count": (
			statistics.median(action_counts) if action_counts else None
		),
		"median_solved_seconds": (
			statistics.median(solved_durations) if solved_durations else None
		),
		"par2_seconds": statistics.mean(par2_values) if par2_values else None,
	}


def _read_json(path: Path) -> dict[str, Any]:
	with path.open("r", encoding="utf-8") as handle:
		payload = json.load(handle)
	if not isinstance(payload, dict):
		raise ValueError(f"Expected JSON object: {path}")
	return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(
		json.dumps(payload, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)


def _sha256(path: Path) -> str:
	hasher = hashlib.sha256()
	with path.open("rb") as handle:
		for chunk in iter(lambda: handle.read(1024 * 1024), b""):
			hasher.update(chunk)
	return hasher.hexdigest()


def _run_registered_command(
	run: RegisteredRun,
	*,
	project_root: Path,
	log_root: Path,
) -> int:
	"""Execute one run, tee concise progress, and retain full subprocess logs."""

	stdout_file = log_root / f"{run.run_id}.stdout.log"
	stderr_file = log_root / f"{run.run_id}.stderr.log"
	stdout_file.parent.mkdir(parents=True, exist_ok=True)
	prefix = f"[{run.stage}] [{run.method}]"
	if run.seed is not None:
		prefix += f" [seed={run.seed}]"
	with stdout_file.open("w", encoding="utf-8") as stdout_handle:
		with stderr_file.open("w", encoding="utf-8") as stderr_handle:
			process = subprocess.Popen(
				run.command,
				cwd=project_root,
				stdout=subprocess.PIPE,
				stderr=stderr_handle,
				text=True,
				bufsize=1,
			)
			assert process.stdout is not None
			for line in process.stdout:
				stdout_handle.write(line)
				if line.startswith(("[ok]", "[fail]", "[run]", "summary_file=")):
					print(f"{prefix} {line.rstrip()}", flush=True)
			return process.wait()


def _normalize_atomic_summary(
	*,
	seed: int,
	variant: AtomicCompilerVariant,
	summary: Mapping[str, Any],
) -> dict[str, Any]:
	validations = tuple(summary.get("validations") or ())
	settings = dict(summary.get("settings") or {})
	timeout_seconds = int(settings.get("timeout_seconds") or 1800)
	validations_by_domain: dict[str, list[Mapping[str, Any]]] = {}
	for validation in validations:
		domain = str(validation.get("domain") or "")
		if domain:
			validations_by_domain.setdefault(domain, []).append(validation)
	domains: dict[str, dict[str, Any]] = {}
	for domain, raw_record in dict(summary.get("domains") or {}).items():
		record = dict(raw_record or {})
		readable_policy = Path(str(record.get("readable_policy_file") or ""))
		library_file = Path(str(record.get("plan_library_json") or ""))
		asl_file = Path(str(record.get("plan_library_asl") or ""))
		normalized_fingerprint = record.get("evidence_program_fingerprint")
		if readable_policy.is_file() and not normalized_fingerprint:
			evidence_program = evidence_program_from_moose_readable_policy(
				readable_policy.read_text(encoding="utf-8"),
				source_name=f"moose:{domain}",
				policy_file=readable_policy,
			)
			normalized_fingerprint = policy_evidence_program_fingerprint(
				evidence_program,
			)
		domains[str(domain)] = {
			"readable_policy_file": str(readable_policy),
			"readable_policy_sha256": (
				_sha256(readable_policy) if readable_policy.is_file() else None
			),
			"evidence_program_fingerprint": normalized_fingerprint,
			"compile_success": bool(
				dict(record.get("compile_atomic_library") or {}).get("success"),
			),
			"compile_seconds": dict(record.get("compile_atomic_library") or {}).get(
				"duration_seconds",
			),
			"validation_success": record.get("validation_success"),
			"execution_metrics": execution_metrics(
				validations_by_domain.get(str(domain), ()),
				timeout_seconds=timeout_seconds,
			),
			"library_metrics": (
				atomic_library_metrics(library_file, asl_file)
				if library_file.is_file() and asl_file.is_file()
				else None
			),
		}
	return {
		"seed": seed,
		"variant": variant.value,
		"method": variant.display_name,
		"domains": domains,
		"execution_metrics": execution_metrics(
			validations,
			timeout_seconds=timeout_seconds,
		),
		"summary": dict(summary),
	}


def _normalize_temporal_summary(
	*,
	variant: TemporalCompilerVariant,
	summary: Mapping[str, Any],
) -> dict[str, Any]:
	results = list(summary.get("results") or ())
	parameters = dict(summary.get("parameters") or {})
	metrics = execution_metrics(
		results,
		timeout_seconds=int(parameters.get("jason_timeout_seconds") or 1800),
	)
	controller_plan_counts = tuple(
		int(record["controller_plan_count"])
		for record in results
		if record.get("controller_plan_count") is not None
	)
	append_durations = tuple(
		float(record["append_seconds"])
		for record in results
		if record.get("append_seconds") is not None
	)
	metrics.update(
		{
			"controller_compiled_count": len(controller_plan_counts),
			"median_controller_plan_count": (
				statistics.median(controller_plan_counts)
				if controller_plan_counts
				else None
			),
			"maximum_trigger_fanout": max(
				(
					int(record.get("max_trigger_fanout") or 0)
					for record in results
				),
				default=0,
			),
			"median_append_seconds": (
				statistics.median(append_durations) if append_durations else None
			),
		},
	)
	return {
		"variant": variant.value,
		"method": variant.display_name,
		"parameters": parameters,
		"benchmark_sha256": summary.get("benchmark_sha256"),
		"atomic_library_inputs": dict(summary.get("atomic_library_inputs") or {}),
		"results": results,
		"aggregate": dict(summary.get("aggregate") or {}),
		"execution_metrics": metrics,
	}


def _parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"--stage",
		choices=("atomic", "temporal", "challenges", "all"),
		default="all",
	)
	parser.add_argument(
		"--seed-batch",
		action="append",
		default=[],
		help="Atomic evidence batch as SEED=BATCH_ID. Repeat for every seed.",
	)
	parser.add_argument(
		"--generate-evidence",
		action="store_true",
		help=(
			"Generate isolated MOOSE evidence batches for fixed seeds 0--4 before "
			"running compiler comparisons."
		),
	)
	parser.add_argument(
		"--temporal-batch-id",
		help=(
			"Precompiled atomic batch for --stage temporal. With --stage all, every "
			"temporal variant consumes the same-run seed-0 Full Compiler output."
		),
	)
	parser.add_argument("--batch-root", type=Path, default=DEFAULT_BATCH_ROOT)
	parser.add_argument("--benchmark-root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
	parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
	parser.add_argument("--run-id")
	parser.add_argument("--domain", action="append", choices=DEFAULT_DOMAINS)
	parser.add_argument("--num-workers", type=int, default=6)
	parser.add_argument("--timeout-seconds", type=int, default=1800)
	parser.add_argument("--jason-java-stack-size", default="64m")
	parser.add_argument(
		"--plan-verifier-command",
		default=f"bash {PROJECT_ROOT / 'scripts/validate_with_docker_val.sh'}",
	)
	parser.add_argument(
		"--allow-incomplete-matrix",
		action="store_true",
		help="Permit fewer than five seeds for smoke runs; never use for paper tables.",
	)
	parser.add_argument(
		"--resume",
		action="store_true",
		help=(
			"Resume the same registered matrix. Completed child runs are reused only "
			"when the registered semantic manifest matches exactly."
		),
	)
	parser.add_argument("--dry-run", action="store_true")
	return parser.parse_args()


def main() -> int:
	args = _parse_args()
	project_root = PROJECT_ROOT
	run_id = args.run_id or f"paired-compilers-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
	run_root = args.output_root.expanduser().resolve() / run_id
	manifest_file = run_root / "manifest.json"
	previous_manifest: dict[str, Any] | None = None
	if run_root.exists():
		if not args.resume or not manifest_file.is_file():
			raise ValueError(f"Output directory already exists: {run_root}")
		previous_manifest = _read_json(manifest_file)
	run_root.mkdir(parents=True, exist_ok=True)
	domains = tuple(args.domain or DEFAULT_DOMAINS)
	seed_batches = parse_seed_batch_assignments(args.seed_batch)
	if args.generate_evidence:
		if seed_batches:
			raise ValueError(
				"--generate-evidence creates its own seed batches; do not also pass "
				"--seed-batch.",
			)
		seed_batches = {
			seed: f"{run_id}-evidence-seed{seed}" for seed in REGISTERED_SEEDS
		}
	if args.stage in {"atomic", "all"}:
		if not args.allow_incomplete_matrix and tuple(sorted(seed_batches)) != REGISTERED_SEEDS:
			raise ValueError(
				"paper atomic matrix requires exactly seeds 0,1,2,3,4; supply five "
				"--seed-batch entries or use --allow-incomplete-matrix for smoke runs.",
			)
		if not seed_batches:
			raise ValueError("atomic stage requires at least one --seed-batch SEED=BATCH_ID")
	atomic_output_root = run_root / "atomic_runs"
	temporal_output_root = run_root / "temporal_runs"
	temporal_atomic_input = (
		resolve_temporal_atomic_input(
			stage=args.stage,
			run_id=run_id,
			atomic_output_root=atomic_output_root,
			evidence_batch_root=args.batch_root.expanduser().resolve(),
			requested_batch_id=args.temporal_batch_id,
			seed_batches=seed_batches,
		)
		if args.stage in {"temporal", "all"}
		else None
	)
	seed_batch_manifests = (
		{}
		if args.generate_evidence
		else {
			str(seed): validate_seed_batch_manifest(
				batch_root=args.batch_root.expanduser().resolve() / batch_id,
				seed=seed,
				domains=domains,
			)
			for seed, batch_id in sorted(seed_batches.items())
		}
	)
	case_contract = build_registered_case_contract(
		project_root=project_root,
		benchmark_root=args.benchmark_root.expanduser().resolve(),
		domains=domains,
	)

	runs: list[RegisteredRun] = []
	if args.generate_evidence:
		for seed, batch_id in sorted(seed_batches.items()):
			runs.append(
				RegisteredRun(
					stage="Evidence",
					method="MOOSE Evidence",
					variant="moose",
					run_id=batch_id,
					seed=seed,
					command=build_evidence_run_command(
						project_root=project_root,
						batch_root=args.batch_root.expanduser().resolve(),
						batch_id=batch_id,
						seed=seed,
						domains=domains,
					),
					summary_file=(
						args.batch_root.expanduser().resolve()
						/ batch_id
						/ "batch_manifest.json"
					),
				),
			)
	if args.stage in {"atomic", "all"}:
		for seed, batch_id in sorted(seed_batches.items()):
			for variant in AtomicCompilerVariant:
				child_id = f"{run_id}-seed{seed}-{variant.value}"
				runs.append(
					RegisteredRun(
						stage="Atomic",
						method=variant.display_name,
						variant=variant.value,
						run_id=child_id,
						seed=seed,
						input_batch_id=batch_id,
						command=build_atomic_run_command(
							project_root=project_root,
							batch_root=args.batch_root.expanduser().resolve(),
							batch_id=batch_id,
							output_root=atomic_output_root,
							run_id=child_id,
							variant=variant,
							domains=domains,
							num_workers=args.num_workers,
							timeout_seconds=args.timeout_seconds,
							java_stack_size=args.jason_java_stack_size,
							plan_verifier_command=args.plan_verifier_command,
						),
						summary_file=atomic_output_root / child_id / "summary.json",
					),
				)
	if args.stage in {"temporal", "all"}:
		assert temporal_atomic_input is not None
		for variant in TemporalCompilerVariant:
			child_id = f"{run_id}-{variant.value}"
			runs.append(
				RegisteredRun(
					stage="Temporal",
					method=variant.display_name,
					variant=variant.value,
					run_id=child_id,
					input_batch_id=temporal_atomic_input.batch_id,
					command=build_temporal_run_command(
						project_root=project_root,
						benchmark_root=args.benchmark_root.expanduser().resolve(),
						batch_root=temporal_atomic_input.batch_root,
						batch_id=temporal_atomic_input.batch_id,
						output_root=temporal_output_root,
						run_id=child_id,
						variant=variant,
						domains=domains,
						num_workers=args.num_workers,
						timeout_seconds=args.timeout_seconds,
						java_stack_size=args.jason_java_stack_size,
						plan_verifier_command=args.plan_verifier_command,
					),
					summary_file=temporal_output_root / child_id / "summary.json",
				),
			)
	if args.stage in {"challenges", "all"}:
		child_id = f"{run_id}-certificate-challenges"
		challenge_output_root = run_root / "challenge_runs"
		runs.append(
			RegisteredRun(
				stage="Challenges",
				method="Certificate Matrix",
				variant="certificate_matrix",
				run_id=child_id,
				command=build_challenge_run_command(
					project_root=project_root,
					output_root=challenge_output_root,
					run_id=child_id,
				),
				summary_file=challenge_output_root / child_id / "summary.json",
			),
		)
	manifest = {
		"schema_version": 1,
		"artifact_kind": "paired_compiler_experiment_matrix",
		"run_id": run_id,
		"created_at": (
			str(previous_manifest.get("created_at"))
			if previous_manifest is not None
			else datetime.now().isoformat(timespec="seconds")
		),
		"resumed_at": (
			datetime.now().isoformat(timespec="seconds")
			if previous_manifest is not None
			else None
		),
		"domains": list(domains),
		"registered_seeds": list(REGISTERED_SEEDS),
		"case_contract": case_contract,
		"seed_batches": {str(seed): batch for seed, batch in seed_batches.items()},
		"seed_batch_manifests": seed_batch_manifests,
		"generate_evidence": bool(args.generate_evidence),
		"temporal_batch_id": (
			temporal_atomic_input.batch_id if temporal_atomic_input is not None else None
		),
		"temporal_atomic_input": (
			{
				"batch_root": str(temporal_atomic_input.batch_root),
				"batch_id": temporal_atomic_input.batch_id,
				"evidence_batch_id": temporal_atomic_input.evidence_batch_id,
				"provenance": temporal_atomic_input.provenance,
			}
			if temporal_atomic_input is not None
			else None
		),
		"num_workers": max(1, int(args.num_workers)),
		"timeout_seconds": max(1, int(args.timeout_seconds)),
		"jason_java_stack_size": str(args.jason_java_stack_size),
		"paper_matrix_complete": tuple(sorted(seed_batches)) == REGISTERED_SEEDS,
		"runs": [
			{
				"stage": run.stage,
				"method": run.method,
				"variant": run.variant,
				"seed": run.seed,
				"input_batch_id": run.input_batch_id,
				"run_id": run.run_id,
				"command": list(run.command),
				"summary_file": str(run.summary_file),
			}
			for run in runs
		],
	}
	if previous_manifest is not None:
		validate_resume_manifest(previous_manifest, manifest)
	_write_json(manifest_file, manifest)
	if args.dry_run:
		print(f"[run] dry-run manifest={manifest_file}")
		return 0

	atomic_records: list[dict[str, Any]] = []
	temporal_records: list[dict[str, Any]] = []
	evidence_records: list[dict[str, Any]] = []
	challenge_records: list[dict[str, Any]] = []
	infrastructure_failures: list[dict[str, Any]] = []
	failed_input_batches: set[str] = set()
	for run in runs:
		if run.input_batch_id in failed_input_batches:
			infrastructure_failures.append(
				{
					"stage": run.stage,
					"method": run.method,
					"seed": run.seed,
					"status": "dependency_failed",
					"input_batch_id": run.input_batch_id,
				},
			)
			print(
				f"[fail] stage={run.stage} method={run.method} "
				f"input_batch={run.input_batch_id} status=dependency_failed",
				flush=True,
			)
			continue
		reused = args.resume and registered_run_summary_complete(
			run,
		)
		if reused:
			print(
				f"[resume] stage={run.stage} method={run.method} seed={run.seed} "
				f"summary={run.summary_file}",
				flush=True,
			)
			return_code = 0
		else:
			print(
				f"[run] stage={run.stage} method={run.method} seed={run.seed}",
				flush=True,
			)
			return_code = _run_registered_command(
				run,
				project_root=project_root,
				log_root=run_root / "logs",
			)
		allowed_return_codes = {0, 1} if run.stage in {"Atomic", "Temporal"} else {0}
		if return_code not in allowed_return_codes or not run.summary_file.is_file():
			failed_input_batches.add(run.run_id)
			infrastructure_failures.append(
				{
					"stage": run.stage,
					"method": run.method,
					"seed": run.seed,
					"return_code": return_code,
					"summary_file": str(run.summary_file),
				},
			)
			continue
		summary = _read_json(run.summary_file)
		if run.stage == "Evidence":
			evidence_records.append(
				{
					"seed": run.seed,
					"batch_id": run.run_id,
					"manifest": summary,
				},
			)
		elif run.stage == "Atomic":
			assert run.seed is not None
			atomic_records.append(
				_normalize_atomic_summary(
					seed=run.seed,
					variant=AtomicCompilerVariant(run.variant),
					summary=summary,
				),
			)
		elif run.stage == "Temporal":
			temporal_records.append(
				_normalize_temporal_summary(
					variant=TemporalCompilerVariant(run.variant),
					summary=summary,
				),
			)
		else:
			challenge_records.append(dict(summary))
	if args.generate_evidence and not failed_input_batches:
		try:
			seed_batch_manifests = {
				str(seed): validate_seed_batch_manifest(
					batch_root=args.batch_root.expanduser().resolve() / batch_id,
					seed=seed,
					domains=domains,
				)
				for seed, batch_id in sorted(seed_batches.items())
			}
		except ValueError as error:
			infrastructure_failures.append(
				{
					"stage": "Evidence",
					"method": "Seed batch contract",
					"error": str(error),
				},
			)
	if atomic_records:
		try:
			atomic_records = apply_common_target_coverage(atomic_records)
		except ValueError as error:
			infrastructure_failures.append(
				{
					"stage": "Aggregation",
					"method": "Atomic target coverage",
					"error": str(error),
				},
			)
	atomic_pairing, atomic_pairing_failure = pairing_outcome(
		label="Atomic",
		runs=atomic_records,
		validator=validate_atomic_pairing,
	)
	temporal_pairing, temporal_pairing_failure = pairing_outcome(
		label="Temporal",
		runs=temporal_records,
		validator=validate_temporal_pairing,
	)
	for pairing_failure in (atomic_pairing_failure, temporal_pairing_failure):
		if pairing_failure is not None:
			infrastructure_failures.append(pairing_failure)
	paired_inputs_verified = all(
		outcome is None or bool(outcome.get("paired"))
		for outcome in (atomic_pairing, temporal_pairing)
	)
	result = {
		**manifest,
		"seed_batch_manifests": seed_batch_manifests,
		"completed_at": datetime.now().isoformat(timespec="seconds"),
		"atomic_pairing": atomic_pairing,
		"temporal_pairing": temporal_pairing,
		"evidence_runs": evidence_records,
		"atomic_runs": atomic_records,
		"temporal_runs": temporal_records,
		"challenge_runs": challenge_records,
		"infrastructure_failures": infrastructure_failures,
		"infrastructure_complete": not infrastructure_failures,
		"paired_inputs_verified": paired_inputs_verified,
		"success": not infrastructure_failures and paired_inputs_verified,
	}
	_write_json(run_root / "paired_results.json", result)
	print(
		f"[run] paired_results={run_root / 'paired_results.json'} "
		f"infrastructure_failures={len(infrastructure_failures)}",
		flush=True,
	)
	return 0 if not infrastructure_failures else 2


if __name__ == "__main__":
	raise SystemExit(main())
