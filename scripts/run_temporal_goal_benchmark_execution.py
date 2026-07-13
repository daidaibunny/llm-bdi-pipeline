#!/usr/bin/env python3
"""Execute the canonical TEG benchmark with Jason, VAL, and DFA validation."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import time
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
DEFAULT_BENCHMARK_ROOT = (
	PROJECT_ROOT / "paper_artifacts/temporal_goal_benchmark/v1"
)
DEFAULT_BATCH_ROOT = PROJECT_ROOT / "artifacts/moose_asl_batches"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "artifacts/temporal_goal_execution_runs"

if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from domain_level_planning import TemporalCompilerVariant  # noqa: E402
from domain_level_planning import append_temporal_goal_to_library  # noqa: E402
from domain_level_planning import build_lifted_temporal_goal_case_dfa  # noqa: E402
from domain_level_planning import dfa_semantic_fingerprint  # noqa: E402
from domain_level_planning import load_lifted_ltlf_goal_dataset  # noqa: E402
from evaluation.jason_runtime import JasonPlanLibraryRunner  # noqa: E402
from evaluation.jason_runtime.runner import build_runtime_problem_artifacts  # noqa: E402
from evaluation.temporal_compilation import DFABuilder  # noqa: E402
from evaluation.temporal_benchmark import (  # noqa: E402
	validate_temporal_goal_benchmark_bundle,
)
from evaluation.temporal_goal_validation import validate_execution_trace  # noqa: E402
from plan_library.models import PlanLibrary  # noqa: E402
from plan_library.rendering import render_plan_library_asl  # noqa: E402
from scripts.run_full_test_jason_validation import (  # noqa: E402
	prepare_shared_jason_environments,
)
from scripts.run_full_test_jason_validation import resolve_jason_classpath_once  # noqa: E402
from temporal_specification.prediction_validation import (  # noqa: E402
	ValidatedLTLfPrediction,
)
from temporal_specification.prediction_validation import (  # noqa: E402
	ValidatedTemporalAtom,
)


@dataclass(frozen=True)
class TemporalExecutionTask:
	"""One independently compiled and validated benchmark invocation."""

	domain: str
	sample_id: str
	profile: str
	domain_file: Path
	problem_file: Path
	plan_library_json: Path
	plan_library_asl: Path
	goal_case: Any
	benchmark_case: Mapping[str, Any]
	audit_row: Mapping[str, Any]
	output_dir: Path


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--benchmark-root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
	parser.add_argument("--batch-root", type=Path, default=DEFAULT_BATCH_ROOT)
	parser.add_argument(
		"--batch-id",
		default="latest",
		help="Atomic ASL batch id, or latest complete batch for selected domains.",
	)
	parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
	parser.add_argument("--run-id")
	parser.add_argument("--num-workers", type=int, default=8)
	parser.add_argument("--timeout-seconds", type=int, default=1800)
	parser.add_argument("--plan-verifier-timeout-seconds", type=int, default=1800)
	parser.add_argument("--jason-java-stack-size", default="64m")
	parser.add_argument(
		"--temporal-compiler-variant",
		choices=tuple(variant.value for variant in TemporalCompilerVariant),
		default=TemporalCompilerVariant.CERTIFIED_BALANCED.value,
		help=(
			"Registered query compiler variant. The default is Certified Balanced."
		),
	)
	parser.add_argument(
		"--plan-verifier-command",
		default=f"bash {PROJECT_ROOT / 'scripts/validate_with_docker_val.sh'}",
	)
	parser.add_argument("--domain", action="append")
	parser.add_argument("--sample-id-regex")
	parser.add_argument("--max-cases", type=int)
	parser.add_argument(
		"--resume",
		action="store_true",
		help="Reuse completed per-case result files in an existing run directory.",
	)
	return parser.parse_args()


def main() -> int:
	args = parse_args()
	compiler_variant = TemporalCompilerVariant(args.temporal_compiler_variant)
	benchmark_root = args.benchmark_root.expanduser().resolve()
	bundle = _read_json(benchmark_root / "benchmark.json")
	validate_release_inputs(benchmark_root=benchmark_root, bundle=bundle)
	all_domains = tuple(sorted(_mapping(bundle, "domains")))
	domains = tuple(args.domain or all_domains)
	unknown = sorted(set(domains) - set(all_domains))
	if unknown:
		raise ValueError(f"Unknown benchmark domains: {', '.join(unknown)}")
	batch_root = resolve_complete_batch(
		args.batch_root,
		args.batch_id,
		domains=domains,
	)
	run_id = args.run_id or f"teg-execution-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
	run_root = args.output_root.expanduser().resolve() / run_id
	if run_root.exists() and not args.resume:
		raise ValueError(f"Output directory already exists: {run_root}")
	run_root.mkdir(parents=True, exist_ok=True)

	audit_rows = load_audit_rows_from_archive(
		benchmark_root / "source/temporal-nl-v1-20260711-final-private-validation.tar.gz",
	)
	expected_problem_count = int(_mapping(bundle, "counts")["problem_case_count"])
	if len(audit_rows) != expected_problem_count:
		raise ValueError(
			"Private audit row count differs from canonical benchmark count: "
			f"audit={len(audit_rows)}, benchmark={expected_problem_count}.",
		)
	tasks = load_execution_tasks(
		benchmark_root=benchmark_root,
		bundle=bundle,
		batch_root=batch_root,
		audit_rows=audit_rows,
		domains=domains,
		run_root=run_root,
		sample_id_regex=args.sample_id_regex,
		max_cases=args.max_cases,
	)
	if not tasks:
		raise ValueError("No benchmark cases matched the requested selection.")

	summary_file = run_root / "summary.json"
	summary: dict[str, Any] = {
		"schema_version": 1,
		"artifact_kind": "temporal_goal_execution_validation",
		"run_id": run_id,
		"started_at": datetime.now().isoformat(timespec="seconds"),
		"source_revision": source_revision_metadata(PROJECT_ROOT),
		"benchmark_id": bundle.get("benchmark_id"),
		"benchmark_file": str(benchmark_root / "benchmark.json"),
		"benchmark_sha256": _sha256(benchmark_root / "benchmark.json"),
		"atomic_batch_root": str(batch_root),
		"atomic_library_inputs": atomic_library_input_metadata(batch_root, domains),
		"selected_domains": list(domains),
		"selected_case_count": len(tasks),
		"temporal_compiler_variant": compiler_variant.value,
		"method": compiler_variant.display_name,
		"parameters": {
			"num_workers": max(1, int(args.num_workers)),
			"jason_timeout_seconds": max(1, int(args.timeout_seconds)),
			"plan_verifier_timeout_seconds": max(
				1,
				int(args.plan_verifier_timeout_seconds),
			),
			"jason_java_stack_size": str(args.jason_java_stack_size),
			"plan_verifier_command": str(args.plan_verifier_command),
			"temporal_compiler_variant": compiler_variant.value,
		},
		"results": [],
	}
	_write_json(summary_file, summary)

	classpath = resolve_jason_classpath_once()
	compiled_environment_dirs = prepare_shared_jason_environments(
		tasks=tasks,
		classpath=classpath,
		run_root=run_root,
		timeout_seconds=max(1, int(args.timeout_seconds)),
		summary=summary,
		summary_file=summary_file,
	)

	existing = (
		load_completed_records(tasks, compiler_variant=compiler_variant)
		if args.resume
		else {}
	)
	records = list(existing.values())
	pending = tuple(task for task in tasks if task.sample_id not in existing)
	results_jsonl = run_root / "execution_results.jsonl"
	with ThreadPoolExecutor(max_workers=max(1, int(args.num_workers))) as executor:
		future_map = {
			executor.submit(
				validate_execution_task,
				task,
				classpath=classpath,
				compiled_environment_dirs=compiled_environment_dirs,
				timeout_seconds=max(1, int(args.timeout_seconds)),
				jason_java_stack_size=str(args.jason_java_stack_size),
				plan_verifier_command=str(args.plan_verifier_command),
				plan_verifier_timeout_seconds=max(
					1,
					int(args.plan_verifier_timeout_seconds),
				),
				compiler_variant=compiler_variant,
			): task
			for task in pending
		}
		for future in as_completed(future_map):
			record = future.result()
			records.append(record)
			_append_jsonl(results_jsonl, record)
			print(progress_line(record), flush=True)
			summary["results"] = sorted(records, key=_record_sort_key)
			summary["aggregate"] = summarize_execution_records(records)
			_write_json(summary_file, summary)

	sorted_records = sorted(records, key=_record_sort_key)
	results_jsonl.write_text(
		"".join(json.dumps(record, sort_keys=True) + "\n" for record in sorted_records),
		encoding="utf-8",
	)
	summary["results"] = sorted_records
	summary["aggregate"] = summarize_execution_records(sorted_records)
	summary["completed_at"] = datetime.now().isoformat(timespec="seconds")
	summary["success"] = bool(sorted_records) and all(
		bool(record.get("success")) for record in sorted_records
	)
	_write_json(summary_file, summary)
	print_summary(summary, summary_file=summary_file)
	return 0 if summary["success"] else 1


def load_execution_tasks(
	*,
	benchmark_root: Path,
	bundle: Mapping[str, Any],
	batch_root: Path,
	audit_rows: Mapping[str, Mapping[str, Any]],
	domains: Sequence[str],
	run_root: Path,
	sample_id_regex: str | None,
	max_cases: int | None,
) -> tuple[TemporalExecutionTask, ...]:
	"""Load benchmark invocations and verify their atomic-library closure inputs."""

	pattern = re.compile(sample_id_regex) if sample_id_regex else None
	tasks: list[TemporalExecutionTask] = []
	domain_payloads = _mapping(bundle, "domains")
	for domain in domains:
		domain_record = _mapping(domain_payloads, domain)
		bundle_cases = _mapping(domain_record, "cases")
		dataset = load_lifted_ltlf_goal_dataset(
			benchmark_root / "domains" / f"{domain}.json",
		)
		case_by_id = {case.query_id: case for case in dataset.cases}
		domain_file = PROJECT_ROOT / str(domain_record["domain_file"])
		library_root = batch_root / "domain_libraries" / domain
		plan_library_json = library_root / "plan_library.json"
		plan_library_asl = library_root / "plan_library.asl"
		for required in (domain_file, plan_library_json, plan_library_asl):
			if not required.is_file():
				raise ValueError(f"Missing execution input: {required}")
		for sample_id, case_payload in sorted(bundle_cases.items()):
			if pattern is not None and not pattern.search(sample_id):
				continue
			if sample_id not in case_by_id or sample_id not in audit_rows:
				raise ValueError(f"Incomplete benchmark linkage for {sample_id}.")
			goal_case = case_by_id[sample_id]
			verify_invocation_binding(
				sample_id=sample_id,
				benchmark_case=case_payload,
				audit_row=audit_rows[sample_id],
			)
			problem_file = PROJECT_ROOT / str(case_payload["problem_file"])
			if not problem_file.is_file():
				raise ValueError(f"Missing benchmark problem: {problem_file}")
			tasks.append(
				TemporalExecutionTask(
					domain=domain,
					sample_id=sample_id,
					profile=str(case_payload.get("profile") or "unknown"),
					domain_file=domain_file,
					problem_file=problem_file,
					plan_library_json=plan_library_json,
					plan_library_asl=plan_library_asl,
					goal_case=goal_case,
					benchmark_case=case_payload,
					audit_row=audit_rows[sample_id],
					output_dir=run_root / "cases" / domain / sample_id,
				),
			)
	if max_cases is not None:
		return tuple(tasks[: max(0, int(max_cases))])
	return tuple(tasks)


def validate_release_inputs(
	*,
	benchmark_root: Path,
	bundle: Mapping[str, Any],
) -> None:
	"""Validate the tracked bundle, operational views, and sealed archive hashes."""

	manifest = _read_json(benchmark_root / "manifest.json")
	benchmark_file = benchmark_root / str(manifest.get("benchmark_file") or "")
	if _sha256(benchmark_file) != str(manifest.get("benchmark_sha256") or ""):
		raise ValueError("Canonical benchmark SHA-256 differs from release manifest.")
	validate_temporal_goal_benchmark_bundle(
		bundle,
		benchmark_root=benchmark_root,
		domains_root=PROJECT_ROOT / "src/domains",
	)
	archives = _mapping(manifest, "sealed_input_archives")
	for archive_name, record_value in archives.items():
		record = _as_mapping(record_value, label=f"sealed archive {archive_name}")
		path = benchmark_root / "source" / str(record.get("filename") or "")
		if not path.is_file() or _sha256(path) != str(record.get("sha256") or ""):
			raise ValueError(f"Sealed source archive verification failed: {path}")


def atomic_library_input_metadata(
	batch_root: Path,
	domains: Sequence[str],
) -> dict[str, dict[str, str]]:
	"""Record exact atomic ASL and structured-library hashes used by the run."""

	return {
		domain: {
			"plan_library_json": str(
				batch_root / "domain_libraries" / domain / "plan_library.json"
			),
			"plan_library_json_sha256": _sha256(
				batch_root / "domain_libraries" / domain / "plan_library.json"
			),
			"plan_library_asl": str(
				batch_root / "domain_libraries" / domain / "plan_library.asl"
			),
			"plan_library_asl_sha256": _sha256(
				batch_root / "domain_libraries" / domain / "plan_library.asl"
			),
		}
		for domain in domains
	}


def validate_execution_task(
	task: TemporalExecutionTask,
	*,
	classpath: str,
	compiled_environment_dirs: Mapping[str, Path],
	timeout_seconds: int,
	jason_java_stack_size: str,
	plan_verifier_command: str,
	plan_verifier_timeout_seconds: int,
	compiler_variant: TemporalCompilerVariant,
) -> dict[str, Any]:
	"""Compile and independently validate one benchmark invocation."""

	start = time.perf_counter()
	task.output_dir.mkdir(parents=True, exist_ok=True)
	base = {
		"domain": task.domain,
		"sample_id": task.sample_id,
		"profile": task.profile,
		"goal_name": task.goal_case.goal_name,
		"problem_file": str(task.problem_file),
		"output_dir": str(task.output_dir),
		"temporal_compiler_variant": compiler_variant.value,
		"method": compiler_variant.display_name,
		"input_fingerprint": temporal_execution_input_fingerprint(
			task,
			compiler_variant=compiler_variant,
		),
	}
	try:
		library = PlanLibrary.from_dict(_read_json(task.plan_library_json))
		dfa_start = time.perf_counter()
		dfa_payload = build_lifted_temporal_goal_case_dfa(
			goal_case=task.goal_case,
			dfa_builder=DFABuilder(),
		)
		base.update(
			{
				"dfa_build_seconds": time.perf_counter() - dfa_start,
				"atomic_library_fingerprint": _canonical_payload_fingerprint(
					library.to_dict(),
				),
				"dfa_fingerprint": dfa_semantic_fingerprint(dfa_payload),
			},
		)
		_write_json(task.output_dir / "dfa_payload.json", dfa_payload)
		append_start = time.perf_counter()
		updated = append_temporal_goal_to_library(
			plan_library=library,
			goal_name=task.goal_case.goal_name,
			dfa_payload=dfa_payload,
			domain_file=task.domain_file,
			compiler_variant=compiler_variant,
		)
		append_metadata = _mapping(updated.metadata, "temporal_goal_append")
		experiment_contract = _mapping(append_metadata, "experiment_contract")
		if experiment_contract["atomic_library_fingerprint"] != base[
			"atomic_library_fingerprint"
		] or experiment_contract["dfa_fingerprint"] != base["dfa_fingerprint"]:
			raise ValueError(
				"temporal experiment contract changed its paired atomic-library or DFA "
				"fingerprint during compilation.",
			)
		base.update(
			{
				"append_seconds": time.perf_counter() - append_start,
				"atomic_library_fingerprint": experiment_contract[
					"atomic_library_fingerprint"
				],
				"dfa_fingerprint": experiment_contract["dfa_fingerprint"],
				"controller_fingerprint": experiment_contract[
					"controller_fingerprint"
				],
				"monitor_observation_boundary": append_metadata.get(
					"monitor_observation_boundary",
				),
				**controller_structure_metrics(library, updated),
			},
		)
	except Exception as error:  # noqa: BLE001 - structured compiler rejection.
		record = {
			**base,
			"success": False,
			"status": temporal_compile_status(error),
			"compiler_error_type": type(error).__name__,
			"error": str(error),
			"duration_seconds": time.perf_counter() - start,
		}
		_write_json(task.output_dir / "result.json", record)
		return record

	runtime_asl_text = render_plan_library_asl(updated)
	try:
		runtime_artifacts = build_runtime_problem_artifacts(
			domain_file=task.domain_file,
			problem_file=task.problem_file,
		)
		jason_result = JasonPlanLibraryRunner(
			timeout_seconds=timeout_seconds,
			jason_classpath=classpath,
			compiled_environment_dir=compiled_environment_dirs.get(
				str(task.domain_file.resolve()),
			),
			jason_java_stack_size=jason_java_stack_size,
			require_plan_verifier=False,
		).validate(
			domain_file=task.domain_file,
			problem_file=task.problem_file,
			plan_library_asl=task.plan_library_asl,
			plan_library_asl_text=runtime_asl_text,
			goal_name=task.goal_case.goal_name,
			output_dir=task.output_dir / "jason",
			runtime_artifacts=runtime_artifacts,
			temporal_dfa_payload=dfa_payload,
			temporal_monitor_observation_boundary=str(
				base["monitor_observation_boundary"],
			),
		)
	except Exception as error:  # noqa: BLE001 - persisted as runtime infrastructure failure.
		record = {
			**base,
			"success": False,
			"status": "jason_infrastructure_error",
			"error": str(error),
			"duration_seconds": time.perf_counter() - start,
		}
		_write_json(task.output_dir / "result.json", record)
		return record

	jason_payload = jason_result.to_dict()
	if not jason_result.success:
		record = {
			**base,
			"success": False,
			"status": "jason_timeout" if jason_result.timed_out else "jason_failed",
			"jason_status": jason_result.status,
			"jason_timed_out": jason_result.timed_out,
			"observed_action_prefix_count": jason_result.action_count,
			"error": jason_result.error,
			"duration_seconds": time.perf_counter() - start,
		}
		_write_json(task.output_dir / "result.json", record)
		return record

	artifacts = _mapping(jason_payload, "artifacts")
	plan_file = Path(str(artifacts.get("committed_plan_trace") or ""))
	if not plan_file.is_file():
		record = {
			**base,
			"success": False,
			"status": "committed_trace_missing",
			"error": f"Jason succeeded without committed trace: {plan_file}",
			"duration_seconds": time.perf_counter() - start,
		}
		_write_json(task.output_dir / "result.json", record)
		return record

	try:
		execution = validate_execution_trace(
			audit_row=task.audit_row,
			prediction=benchmark_prediction(task.sample_id, task.benchmark_case),
			domain_file=task.domain_file,
			problem_file=task.problem_file,
			plan_file=plan_file,
			output_dir=task.output_dir / "temporal_validation",
			plan_verifier_command=plan_verifier_command,
			plan_verifier_timeout_seconds=plan_verifier_timeout_seconds,
		)
		execution_payload = execution.to_dict()
		status = execution_status(execution_payload)
		record = {
			**base,
			"success": execution.success,
			"status": status,
			"jason_status": jason_result.status,
			"execution_validation": execution_payload,
			"action_count": execution.action_count,
			"duration_seconds": time.perf_counter() - start,
		}
	except Exception as error:  # noqa: BLE001 - independent validator diagnostics.
		record = {
			**base,
			"success": False,
			"status": "trace_validation_error",
			"error": str(error),
			"duration_seconds": time.perf_counter() - start,
		}
	_write_json(task.output_dir / "result.json", record)
	return record


def controller_structure_metrics(
	base_library: PlanLibrary,
	updated_library: PlanLibrary,
) -> dict[str, Any]:
	"""Measure only query-local plans appended to an unchanged atomic library."""

	base_plan_count = len(base_library.plans)
	if tuple(updated_library.plans[:base_plan_count]) != tuple(base_library.plans):
		raise ValueError("temporal append changed or reordered the atomic plan prefix")
	query_plans = tuple(updated_library.plans[base_plan_count:])
	trigger_counts = Counter(
		(
			plan.trigger.event_type,
			plan.trigger.symbol,
			plan.trigger.arguments,
		)
		for plan in query_plans
	)
	base_asl_bytes = len(render_plan_library_asl(base_library).encode("utf-8"))
	updated_asl_bytes = len(render_plan_library_asl(updated_library).encode("utf-8"))
	return {
		"controller_plan_count": len(query_plans),
		"max_trigger_fanout": max(trigger_counts.values(), default=0),
		"controller_context_literal_count": sum(
			len(plan.context) for plan in query_plans
		),
		"controller_body_step_count": sum(len(plan.body) for plan in query_plans),
		"controller_asl_bytes": updated_asl_bytes - base_asl_bytes,
	}


def benchmark_prediction(
	sample_id: str,
	case: Mapping[str, Any],
) -> ValidatedLTLfPrediction:
	"""Rehydrate the frozen validated prediction stored in the canonical bundle."""

	atoms: list[ValidatedTemporalAtom] = []
	for raw_atom in _sequence(case, "atoms"):
		atom = _as_mapping(raw_atom, label=f"{sample_id} atom")
		kind = str(atom.get("kind") or "")
		if kind not in {"predicate", "numeric_equality"}:
			raise ValueError(f"{sample_id} has unsupported atom kind {kind!r}.")
		name_key = "predicate" if kind == "predicate" else "function"
		name = str(atom.get(name_key) or "").strip()
		if not name:
			raise ValueError(f"{sample_id} atom is missing {name_key}.")
		value = atom.get("value") if kind == "numeric_equality" else None
		if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
			raise ValueError(f"{sample_id} numeric equality has non-integer value.")
		atoms.append(
			ValidatedTemporalAtom(
				symbol=str(atom.get("symbol") or ""),
				kind=kind,
				name=name,
				args=tuple(str(item) for item in _sequence(atom, "args")),
				value=value,
			),
		)
	parameters = tuple(
		(str(item["name"]), str(item["pddl_type"]))
		for raw_item in _sequence(case, "declared_parameters")
		for item in (_as_mapping(raw_item, label=f"{sample_id} parameter"),)
	)
	constraints = tuple(
		json.dumps(item, sort_keys=True)
		for item in _sequence(case, "constraints")
	)
	return ValidatedLTLfPrediction(
		sample_id=sample_id,
		ltlf_formula=str(case.get("ltlf_formula") or ""),
		atoms=tuple(atoms),
		declared_parameters=parameters,
		constraints=constraints,
	)


def verify_invocation_binding(
	*,
	sample_id: str,
	benchmark_case: Mapping[str, Any],
	audit_row: Mapping[str, Any],
) -> None:
	"""Require the public execution projection to match the sealed assignment."""

	bindings = {
		str(key): str(value)
		for key, value in _mapping(benchmark_case, "bindings").items()
	}
	assignment = {
		str(key): str(value)
		for key, value in _mapping(audit_row, "assignment").items()
	}
	if bindings != assignment:
		raise ValueError(
			f"{sample_id} invocation binding differs from sealed audit assignment: "
			f"benchmark={bindings}, audit={assignment}.",
		)


def load_audit_rows_from_archive(
	archive: str | Path,
) -> dict[str, Mapping[str, Any]]:
	"""Read sealed construction-audit rows without extracting hidden files."""

	archive_path = Path(archive).resolve()
	if not archive_path.is_file():
		raise ValueError(f"Missing private validation archive: {archive_path}")
	rows: dict[str, Mapping[str, Any]] = {}
	with tarfile.open(archive_path, mode="r:gz") as bundle:
		for member in bundle.getmembers():
			member_path = Path(member.name)
			if member_path.is_absolute() or ".." in member_path.parts:
				raise ValueError(f"Unsafe private archive member: {member.name!r}")
			if member.issym() or member.islnk():
				raise ValueError(f"Private archive links are not accepted: {member.name!r}")
			if member_path.name != "construction_audit.jsonl":
				continue
			handle = bundle.extractfile(member)
			if handle is None:
				raise ValueError(f"Cannot read private archive member: {member.name}")
			for raw_line in handle.read().decode("utf-8").splitlines():
				if not raw_line.strip():
					continue
				row = _as_mapping(json.loads(raw_line), label=member.name)
				sample_id = str(row.get("sample_id") or "").strip()
				if not sample_id or sample_id in rows:
					raise ValueError(f"Invalid or duplicate audit sample id {sample_id!r}.")
				rows[sample_id] = row
	if not rows:
		raise ValueError("Private validation archive contains no construction audit rows.")
	return rows


def resolve_complete_batch(
	batch_root: Path,
	batch_id: str,
	*,
	domains: Sequence[str],
) -> Path:
	"""Resolve an atomic batch containing both ASL and JSON for every domain."""

	root = batch_root.expanduser().resolve()
	if not root.is_dir():
		raise ValueError(f"Missing atomic batch root: {root}")
	candidates = (
		tuple(sorted((item for item in root.iterdir() if item.is_dir()), reverse=True))
		if batch_id == "latest"
		else (root / batch_id,)
	)
	for candidate in candidates:
		if all(
			(candidate / "domain_libraries" / domain / "plan_library.json").is_file()
			and (candidate / "domain_libraries" / domain / "plan_library.asl").is_file()
			for domain in domains
		):
			return candidate
	raise ValueError(
		"No complete atomic ASL batch contains every selected domain: "
		f"{', '.join(domains)}.",
	)


def temporal_compile_status(error: Exception) -> str:
	"""Map fail-closed temporal compiler diagnostics to stable result classes."""

	message = str(error).lower()
	if any(
		marker in message
		for marker in (
			"branching_or_state_dependent",
			"nonlinear_temporal_goal_not_supported",
			"unsupported temporal",
			"no unique progress path",
		)
	):
		return "unsupported_temporal_controller"
	if "uncertified_numeric" in message:
		return "unsupported_numeric_preservation"
	if "negative_guard_not_preserved" in message:
		return "negative_guard_not_preserved"
	if "cyclic" in message or "threat" in message:
		return "uncertified_threat_cycle"
	return "temporal_compile_failed"


def execution_status(payload: Mapping[str, Any]) -> str:
	"""Return the first failed independent execution-validation obligation."""

	if payload.get("replay_valid") is not True:
		return "pddl_replay_failed"
	zero_action_certificate = (
		payload.get("action_count") == 0
		and payload.get("state_count") == 1
		and payload.get("legality_certificate")
		== "vacuous_zero_action_pddl_replay"
	)
	if not zero_action_certificate:
		if payload.get("val_attempted") is not True:
			return "val_unavailable"
		if payload.get("val_success") is not True:
			return "val_failed"
	if payload.get("gold_accepted") is not True:
		return "gold_dfa_rejected"
	if payload.get("prediction_accepted") is not True:
		return "predicted_dfa_rejected"
	return "success"


def summarize_execution_records(
	records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
	"""Aggregate exact status counts without collapsing compiler and runtime failures."""

	def grouped(field: str) -> dict[str, dict[str, Any]]:
		groups: dict[str, list[Mapping[str, Any]]] = {}
		for record in records:
			groups.setdefault(str(record.get(field) or "unknown"), []).append(record)
		return {
			name: {
				"total": len(items),
				"success_count": sum(bool(item.get("success")) for item in items),
				"status_counts": dict(
					sorted(Counter(str(item.get("status")) for item in items).items()),
				),
			}
			for name, items in sorted(groups.items())
		}

	return {
		"total": len(records),
		"success_count": sum(bool(record.get("success")) for record in records),
		"status_counts": dict(
			sorted(Counter(str(record.get("status")) for record in records).items()),
		),
		"domains": grouped("domain"),
		"profiles": grouped("profile"),
	}


def progress_line(record: Mapping[str, Any]) -> str:
	"""Render one concise per-case terminal progress record."""

	status = str(record.get("status") or "unknown")
	prefix = "ok" if record.get("success") else "fail"
	execution = record.get("execution_validation")
	execution_map = execution if isinstance(execution, Mapping) else {}
	return (
		f"[{prefix}] {record.get('domain')} sample={record.get('sample_id')} "
		f"profile={record.get('profile')} status={status} "
		f"jason={'ok' if record.get('jason_status') == 'success' else 'not_ok'} "
		f"val={_status_token(execution_map.get('val_success'))} "
		f"gold_dfa={_status_token(execution_map.get('gold_accepted'))} "
		f"pred_dfa={_status_token(execution_map.get('prediction_accepted'))} "
		f"actions={record.get('action_count', 'n/a')} "
		f"seconds={float(record.get('duration_seconds') or 0.0):.2f}"
	)


def print_summary(summary: Mapping[str, Any], *, summary_file: Path) -> None:
	aggregate = _mapping(summary, "aggregate")
	print("[summary] domain,total,success,status_counts", flush=True)
	for domain, record in _mapping(aggregate, "domains").items():
		item = _as_mapping(record, label=f"domain {domain}")
		print(
			f"[summary] {domain},{item.get('total')},{item.get('success_count')},"
			f"{json.dumps(item.get('status_counts'), sort_keys=True)}",
			flush=True,
		)
	print(f"[summary] file={summary_file}", flush=True)


def temporal_execution_input_fingerprint(
	task: TemporalExecutionTask,
	*,
	compiler_variant: TemporalCompilerVariant,
) -> str:
	"""Fingerprint every immutable input that determines one temporal case."""

	payload = {
		"domain": task.domain,
		"sample_id": task.sample_id,
		"profile": task.profile,
		"domain_sha256": _sha256(task.domain_file),
		"problem_sha256": _sha256(task.problem_file),
		"plan_library_json_sha256": _sha256(task.plan_library_json),
		"plan_library_asl_sha256": _sha256(task.plan_library_asl),
		"goal_case": task.goal_case.to_dict(),
		"benchmark_case": dict(task.benchmark_case),
		"audit_row": dict(task.audit_row),
		"temporal_compiler_variant": compiler_variant.value,
	}
	return _canonical_payload_fingerprint(payload)


def load_completed_records(
	tasks: Sequence[TemporalExecutionTask],
	*,
	compiler_variant: TemporalCompilerVariant,
) -> dict[str, Mapping[str, Any]]:
	"""Load only complete records whose exact temporal inputs still match."""

	records: dict[str, Mapping[str, Any]] = {}
	for task in tasks:
		result_file = task.output_dir / "result.json"
		if result_file.is_file():
			record = _read_json(result_file)
			if (
				record.get("sample_id") == task.sample_id
				and "status" in record
				and record.get("input_fingerprint")
				== temporal_execution_input_fingerprint(
					task,
					compiler_variant=compiler_variant,
				)
			):
				records[task.sample_id] = record
	return records


def source_revision_metadata(project_root: Path) -> dict[str, Any]:
	"""Capture code revision and distinguish tracked changes from local artifacts."""

	try:
		commit = subprocess.run(
			("git", "rev-parse", "HEAD"),
			cwd=project_root,
			capture_output=True,
			text=True,
			check=True,
		).stdout.strip()
		status = subprocess.run(
			("git", "status", "--porcelain=v1", "--untracked-files=all"),
			cwd=project_root,
			capture_output=True,
			text=True,
			check=True,
		).stdout.splitlines()
	except (OSError, subprocess.CalledProcessError) as error:
		return {"available": False, "error": str(error)}
	return {
		"available": True,
		"commit": commit,
		"tracked_changes": any(not line.startswith("??") for line in status),
		"untracked_files": any(line.startswith("??") for line in status),
	}


def _status_token(value: Any) -> str:
	if value is True:
		return "ok"
	if value is False:
		return "fail"
	return "not_attempted"


def _record_sort_key(record: Mapping[str, Any]) -> tuple[str, str]:
	return (str(record.get("domain") or ""), str(record.get("sample_id") or ""))


def _read_json(path: Path) -> dict[str, Any]:
	payload = json.loads(path.read_text(encoding="utf-8"))
	return dict(_as_mapping(payload, label=str(path)))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(
		json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)


def _canonical_payload_fingerprint(payload: object) -> str:
	encoded = json.dumps(
		payload,
		sort_keys=True,
		separators=(",", ":"),
		default=str,
	).encode("utf-8")
	return hashlib.sha256(encoded).hexdigest()


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	with path.open("a", encoding="utf-8") as handle:
		handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
	return _as_mapping(payload.get(key), label=key)


def _sequence(payload: Mapping[str, Any], key: str) -> Sequence[Any]:
	value = payload.get(key)
	if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
		raise ValueError(f"{key} must be an array.")
	return value


def _as_mapping(value: Any, *, label: str) -> Mapping[str, Any]:
	if not isinstance(value, Mapping):
		raise ValueError(f"{label} must be an object.")
	return value


def _sha256(path: Path) -> str:
	return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
	os.environ.setdefault(
		"MONA_BIN",
		str(PROJECT_ROOT / ".external/mona-1.4/Front/mona"),
	)
	raise SystemExit(main())
