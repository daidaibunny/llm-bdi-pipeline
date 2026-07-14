#!/usr/bin/env python3
"""Run the native FOND4LTLf plus LAMA direct temporal reference."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any
from typing import Mapping
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
DEFAULT_BENCHMARK_ROOT = PROJECT_ROOT / "paper_artifacts/temporal_goal_benchmark/v1"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "artifacts/direct_temporal_references"
DEFAULT_FOND4LTLF_ROOT = PROJECT_ROOT / ".external/fond4ltlf-0.0.4"
DEFAULT_MONA_EXECUTABLE = PROJECT_ROOT / ".external/mona-1.4/Front/mona"
FOND4LTLF_COMPILER_LOCK = (
	Path(tempfile.gettempdir()) / "gp2pl-fond4ltlf-ltlf2dfa-runtime.lock"
)

if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from evaluation.external_reference_planners import (  # noqa: E402
	ExternalReferenceMethod,
)
from evaluation.external_reference_planners import (  # noqa: E402
	build_fond4ltlf_command,
)
from evaluation.external_reference_planners import (  # noqa: E402
	build_ground_fond4ltlf_formula,
)
from evaluation.external_reference_planners import (  # noqa: E402
	filter_compilation_actions,
)
from evaluation.external_reference_planners import (  # noqa: E402
	normalize_fond4ltlf_domain,
)
from evaluation.temporal_goal_validation import validate_execution_trace  # noqa: E402
from scripts.run_external_planning_references import (  # noqa: E402
	MOOSE_RUNTIME_LOCK,
	build_moose_reference_arguments,
	is_infrastructure_failure,
	parse_guard_failure,
	run_guarded_command,
)
from scripts.run_full_test_jason_validation import (  # noqa: E402
	source_revision_metadata,
)
from scripts.run_moose_faithful_e2e import MOOSE_ROOT  # noqa: E402
from scripts.run_moose_faithful_e2e import container_path  # noqa: E402
from scripts.run_moose_faithful_e2e import moose_runtime_command  # noqa: E402
from scripts.run_temporal_goal_benchmark_execution import (  # noqa: E402
	benchmark_prediction,
)
from scripts.run_temporal_goal_benchmark_execution import execution_status  # noqa: E402
from scripts.run_temporal_goal_benchmark_execution import (  # noqa: E402
	load_audit_rows_from_archive,
)
from scripts.run_temporal_goal_benchmark_execution import (  # noqa: E402
	validate_release_inputs,
)
from scripts.run_temporal_goal_benchmark_execution import (  # noqa: E402
	verify_invocation_binding,
)
from utils.pddl_parser import PDDLParser  # noqa: E402


METHOD = ExternalReferenceMethod.FOND4LTLF_LAMA


@dataclass(frozen=True)
class DirectTemporalTask:
	"""One benchmark formula solved without an AgentSpeak atomic library."""

	domain: str
	sample_id: str
	profile: str
	domain_file: Path
	problem_file: Path
	benchmark_case: Mapping[str, Any]
	audit_row: Mapping[str, Any]
	output_dir: Path


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--benchmark-root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
	parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
	parser.add_argument("--run-id")
	parser.add_argument("--domain", action="append")
	parser.add_argument("--sample-id-regex")
	parser.add_argument("--max-cases", type=int)
	parser.add_argument("--num-workers", type=int, default=1)
	parser.add_argument("--timeout-seconds", type=int, default=1800)
	parser.add_argument("--max-rss-gb", type=float, default=8.0)
	parser.add_argument("--plan-verifier-timeout-seconds", type=int, default=1800)
	parser.add_argument(
		"--plan-verifier-command",
		default=f"bash {PROJECT_ROOT / 'scripts/validate_with_docker_val.sh'}",
	)
	parser.add_argument(
		"--fond4ltlf-executable",
		type=Path,
		default=DEFAULT_FOND4LTLF_ROOT / ".venv/bin/fond4ltlf",
	)
	parser.add_argument(
		"--mona-executable",
		type=Path,
		default=DEFAULT_MONA_EXECUTABLE,
	)
	parser.add_argument("--resume", action="store_true")
	return parser.parse_args()


def main() -> int:
	args = parse_args()
	if args.num_workers <= 0 or args.timeout_seconds <= 0 or args.max_rss_gb <= 0:
		raise ValueError("Worker, timeout, and memory values must be positive.")
	benchmark_root = args.benchmark_root.expanduser().resolve()
	bundle = _read_json(benchmark_root / "benchmark.json")
	validate_release_inputs(benchmark_root=benchmark_root, bundle=bundle)
	all_domains = tuple(sorted(_mapping(bundle, "domains")))
	domains = tuple(args.domain or all_domains)
	unknown = sorted(set(domains) - set(all_domains))
	if unknown:
		raise ValueError(f"Unknown benchmark domains: {', '.join(unknown)}")
	run_id = args.run_id or f"direct-temporal-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
	run_root = args.output_root.expanduser().resolve() / run_id
	try:
		run_root.relative_to(PROJECT_ROOT)
	except ValueError as error:
		raise ValueError(
			"Direct temporal artifacts must remain under the project root so the "
			"official LAMA container can access them.",
		) from error
	if run_root.exists() and not args.resume:
		raise ValueError(f"Output directory already exists: {run_root}")
	run_root.mkdir(parents=True, exist_ok=True)
	audit_rows = load_audit_rows_from_archive(
		benchmark_root / "source/temporal-nl-v1-20260711-final-private-validation.tar.gz",
	)
	tasks = build_direct_temporal_tasks(
		benchmark_root=benchmark_root,
		bundle=bundle,
		audit_rows=audit_rows,
		domains=domains,
		run_root=run_root,
		sample_id_regex=args.sample_id_regex,
		max_cases=args.max_cases,
	)
	if not tasks:
		raise ValueError("No temporal benchmark cases matched the requested selection.")

	summary_file = run_root / "summary.json"
	summary: dict[str, Any] = {
		"schema_version": 1,
		"artifact_kind": "direct_temporal_planning_reference",
		"run_id": run_id,
		"started_at": datetime.now().isoformat(timespec="seconds"),
		"source_revision": source_revision_metadata(PROJECT_ROOT),
		"benchmark_id": bundle.get("benchmark_id"),
		"benchmark_file": str(benchmark_root / "benchmark.json"),
		"benchmark_sha256": _sha256(benchmark_root / "benchmark.json"),
		"method": METHOD.display_name,
		"variant": METHOD.value,
		"domains": list(domains),
		"selected_case_count": len(tasks),
		"parameters": {
			"num_workers": int(args.num_workers),
			"timeout_seconds_total_compile_and_plan": int(args.timeout_seconds),
			"max_rss_gb": float(args.max_rss_gb),
			"plan_verifier_timeout_seconds": int(args.plan_verifier_timeout_seconds),
			"plan_verifier_command": str(args.plan_verifier_command),
			"fond4ltlf_compiler_max_parallelism": 1,
			"fond4ltlf_compiler_lock_scope": "host",
			"moose_runtime_max_parallelism": 1,
			"moose_runtime_lock_scope": "host",
		},
		"toolchain": temporal_toolchain_metadata(
			args.fond4ltlf_executable,
			args.mona_executable,
		),
		"results": [],
	}
	_write_json(summary_file, summary)
	existing = load_completed_records(tasks) if args.resume else {}
	records = list(existing.values())
	pending = tuple(task for task in tasks if task.sample_id not in existing)
	with ThreadPoolExecutor(max_workers=int(args.num_workers)) as executor:
		future_map = {
			executor.submit(
				run_direct_temporal_task,
				task,
				fond4ltlf_executable=args.fond4ltlf_executable.expanduser().resolve(),
				mona_executable=args.mona_executable.expanduser().resolve(),
				timeout_seconds=int(args.timeout_seconds),
				max_rss_gb=float(args.max_rss_gb),
				plan_verifier_command=str(args.plan_verifier_command),
				plan_verifier_timeout_seconds=int(args.plan_verifier_timeout_seconds),
			): task
			for task in pending
		}
		for future in as_completed(future_map):
			task = future_map[future]
			try:
				record = future.result()
			except Exception as error:  # noqa: BLE001 - persisted infrastructure failure.
				record = base_record(task)
				record.update(status="runner_error", error=str(error))
				_write_json(task.output_dir / "result.json", record)
			records.append(record)
			print(progress_line(record), flush=True)
			summary["results"] = sorted(records, key=record_sort_key)
			_write_json(summary_file, summary)

	records = sorted(records, key=record_sort_key)
	metrics = summarize_temporal_reference_records(
		records,
		timeout_seconds=int(args.timeout_seconds),
	)
	summary.update(
		{
			"finished_at": datetime.now().isoformat(timespec="seconds"),
			"results": records,
			"metrics": metrics,
			"infrastructure_failure_count": sum(
				1
				for record in records
				if is_infrastructure_failure(record.get("status"))
			),
		}
	)
	summary["success"] = summary["infrastructure_failure_count"] == 0
	_write_json(summary_file, summary)
	_write_jsonl(run_root / "results.jsonl", records)
	print(
		f"[summary] valid={metrics['valid_trace_count']}/"
		f"{metrics['supported_case_count']} supported "
		f"unsupported={metrics['unsupported_case_count']} artifact={summary_file}",
		flush=True,
	)
	return 0 if summary["success"] else 1


def build_direct_temporal_tasks(
	*,
	benchmark_root: Path,
	bundle: Mapping[str, Any],
	audit_rows: Mapping[str, Mapping[str, Any]],
	domains: Sequence[str],
	run_root: Path,
	sample_id_regex: str | None,
	max_cases: int | None,
) -> tuple[DirectTemporalTask, ...]:
	"""Build paired direct-reference tasks without loading an atomic ASL library."""

	pattern = re.compile(sample_id_regex) if sample_id_regex else None
	domain_records = _mapping(bundle, "domains")
	tasks: list[DirectTemporalTask] = []
	for domain in domains:
		domain_record = _as_mapping(domain_records[domain], label=f"domain {domain}")
		domain_file = PROJECT_ROOT / "src/domains" / domain / "domain.pddl"
		if not domain_file.is_file():
			raise ValueError(f"Missing benchmark domain: {domain_file}")
		for sample_id, raw_case in sorted(_mapping(domain_record, "cases").items()):
			if pattern is not None and pattern.search(sample_id) is None:
				continue
			case = _as_mapping(raw_case, label=sample_id)
			if sample_id not in audit_rows:
				raise ValueError(f"Missing sealed audit row for {sample_id}.")
			verify_invocation_binding(
				sample_id=sample_id,
				benchmark_case=case,
				audit_row=audit_rows[sample_id],
			)
			problem_file = PROJECT_ROOT / str(case.get("problem_file") or "")
			if not problem_file.is_file():
				raise ValueError(f"Missing benchmark problem: {problem_file}")
			tasks.append(
				DirectTemporalTask(
					domain=domain,
					sample_id=sample_id,
					profile=str(case.get("profile") or "unknown"),
					domain_file=domain_file,
					problem_file=problem_file,
					benchmark_case=case,
					audit_row=audit_rows[sample_id],
					output_dir=run_root / "cases" / domain / sample_id,
				),
			)
	if max_cases is not None:
		return tuple(tasks[: max(0, int(max_cases))])
	return tuple(tasks)


def run_direct_temporal_task(
	task: DirectTemporalTask,
	*,
	fond4ltlf_executable: Path,
	mona_executable: Path,
	timeout_seconds: int,
	max_rss_gb: float,
	plan_verifier_command: str,
	plan_verifier_timeout_seconds: int,
) -> dict[str, Any]:
	"""Compile, solve, project, and independently validate one temporal formula."""

	task.output_dir.mkdir(parents=True, exist_ok=True)
	record = base_record(task)
	if not fond4ltlf_executable.is_file():
		record.update(
			status="tool_unavailable",
			error=f"Missing pinned FOND4LTLf executable: {fond4ltlf_executable}",
		)
		_write_json(task.output_dir / "result.json", record)
		return record
	if not mona_executable.is_file():
		record.update(
			status="tool_unavailable",
			error=f"Missing pinned MONA executable: {mona_executable}",
		)
		_write_json(task.output_dir / "result.json", record)
		return record
	try:
		normalized_domain = normalize_fond4ltlf_domain(
			task.domain_file.read_text(encoding="utf-8"),
		)
		grounded_formula = build_ground_fond4ltlf_formula(task.benchmark_case)
	except ValueError as error:
		record.update(
			status=unsupported_status(error),
			supported=False,
			error=str(error),
		)
		_write_json(task.output_dir / "result.json", record)
		return record

	record["supported"] = True
	record["grounded_formula"] = grounded_formula
	compatible_domain = task.output_dir / "fond4ltlf_domain.pddl"
	compatible_domain.write_text(normalized_domain, encoding="utf-8")
	compiled_domain = task.output_dir / "compiled_domain.pddl"
	compiled_problem = task.output_dir / "compiled_problem.pddl"
	compiled_plan = task.output_dir / "compiled.plan"
	projected_plan = task.output_dir / "plan.plan"
	compiler_command = build_fond4ltlf_command(
		executable=fond4ltlf_executable,
		domain_file=compatible_domain,
		problem_file=task.problem_file,
		formula=grounded_formula,
		output_domain_file=compiled_domain,
		output_problem_file=compiled_problem,
	)
	compiler_result = run_guarded_command(
		compiler_command,
		output_dir=task.output_dir,
		timeout_seconds=timeout_seconds,
		max_rss_gb=max_rss_gb,
		extra_env={
			"PATH": str(mona_executable.parent)
			+ os.pathsep
			+ os.environ.get("PATH", ""),
		},
		artifact_stem="compiler",
		exclusive_lock_file=FOND4LTLF_COMPILER_LOCK,
	)
	record.update(
		{
			"compiler_command": list(compiler_result.command),
			"compiler_timeout_seconds": float(timeout_seconds),
			"compiler_exit_code": compiler_result.exit_code,
			"compiler_seconds": compiler_result.elapsed_seconds,
			"compiler_stdout": str(compiler_result.stdout_file),
			"compiler_stderr": str(compiler_result.stderr_file),
			"compiler_lock_wait_seconds": (
				compiler_result.runtime_lock_wait_seconds
			),
		}
	)
	if compiler_result.exit_code != 0:
		record["status"] = stage_failure_status("compiler", compiler_result.stderr_file)
		record["elapsed_seconds"] = compiler_result.elapsed_seconds
		_write_json(task.output_dir / "result.json", record)
		return record
	if not compiled_domain.is_file() or not compiled_problem.is_file():
		record.update(
			status="compiler_failed",
			error="FOND4LTLf exited successfully without both compiled PDDL files.",
			elapsed_seconds=compiler_result.elapsed_seconds,
		)
		_write_json(task.output_dir / "result.json", record)
		return record
	remaining_planner_seconds = timeout_seconds - compiler_result.elapsed_seconds
	if remaining_planner_seconds <= 0:
		record.update(
			status="planner_timeout",
			elapsed_seconds=compiler_result.elapsed_seconds,
		)
		_write_json(task.output_dir / "result.json", record)
		return record

	try:
		lama_arguments = build_moose_reference_arguments(
			method=ExternalReferenceMethod.LAMA,
			domain_file=container_path(compiled_domain),
			problem_file=container_path(compiled_problem),
			plan_file=container_path(compiled_plan),
		)
		planner_command = moose_runtime_command(
			lama_arguments,
			runtime="docker",
			max_rss_gb=max_rss_gb,
		)
	except (FileNotFoundError, ValueError) as error:
		record.update(status="tool_unavailable", error=str(error))
		_write_json(task.output_dir / "result.json", record)
		return record
	planner_result = run_guarded_command(
		planner_command,
		output_dir=task.output_dir,
		timeout_seconds=remaining_planner_seconds,
		max_rss_gb=max_rss_gb,
		artifact_stem="planner",
		exclusive_lock_file=MOOSE_RUNTIME_LOCK,
	)
	record.update(
		{
			"planner_command": list(planner_result.command),
			"planner_timeout_seconds": remaining_planner_seconds,
			"planner_exit_code": planner_result.exit_code,
			"planner_seconds": planner_result.elapsed_seconds,
			"planner_stdout": str(planner_result.stdout_file),
			"planner_stderr": str(planner_result.stderr_file),
			"runtime_lock_wait_seconds": planner_result.runtime_lock_wait_seconds,
			"elapsed_seconds": (
				compiler_result.elapsed_seconds + planner_result.elapsed_seconds
			),
		}
	)
	if planner_result.exit_code != 0:
		record["status"] = stage_failure_status("planner", planner_result.stderr_file)
		_write_json(task.output_dir / "result.json", record)
		return record
	if not compiled_plan.is_file():
		record["status"] = "no_plan"
		_write_json(task.output_dir / "result.json", record)
		return record
	try:
		action_names = {
			action.name.lower() for action in PDDLParser.parse_domain(task.domain_file).actions
		}
		projected_actions = filter_compilation_actions(
			compiled_plan.read_text(encoding="utf-8", errors="replace"),
			original_action_names=action_names,
		)
		projected_plan.write_text(
			"".join(f"{action}\n" for action in projected_actions),
			encoding="utf-8",
		)
	except ValueError as error:
		record.update(status="plan_projection_failed", error=str(error))
		_write_json(task.output_dir / "result.json", record)
		return record
	record.update(
		{
			"compiled_action_count": sum(
				1
				for line in compiled_plan.read_text(
					encoding="utf-8",
					errors="replace",
				).splitlines()
				if line.strip() and not line.lstrip().startswith(";")
			),
			"action_count": len(projected_actions),
			"compiled_plan_file": str(compiled_plan),
			"plan_file": str(projected_plan),
		}
	)
	try:
		execution = validate_execution_trace(
			audit_row=task.audit_row,
			prediction=benchmark_prediction(task.sample_id, task.benchmark_case),
			domain_file=task.domain_file,
			problem_file=task.problem_file,
			plan_file=projected_plan,
			output_dir=task.output_dir / "temporal_validation",
			plan_verifier_command=plan_verifier_command,
			plan_verifier_timeout_seconds=plan_verifier_timeout_seconds,
			mona_executable=mona_executable,
		)
		execution_payload = execution.to_dict()
		record.update(
			{
				"execution_validation": execution_payload,
				"success": execution.success,
				"status": "valid" if execution.success else execution_status(execution_payload),
				"action_count": execution.action_count,
			}
		)
	except (OSError, RuntimeError, ValueError) as error:
		message = str(error)
		status = "pddl_replay_failed" if "Trace step " in message else "trace_validation_error"
		record.update(status=status, error=message)
	_write_json(task.output_dir / "result.json", record)
	return record


def unsupported_status(error: ValueError) -> str:
	"""Map official FOND4LTLf limitations to explicit applicability outcomes."""

	message = str(error).lower()
	if "numeric pddl" in message:
		return "unsupported_numeric_pddl"
	if "numeric equality" in message:
		return "unsupported_numeric_formula"
	if "underscore encoding" in message:
		return "unsupported_identifier_encoding"
	if "does not support pddl requirements" in message:
		return "unsupported_pddl_requirement"
	return "input_error"


def stage_failure_status(stage: str, stderr_file: Path) -> str:
	"""Prefix the shared resource-guard status with the failing pipeline stage."""

	failure = parse_guard_failure(
		stderr_file.read_text(encoding="utf-8", errors="replace"),
	)
	if failure == "planner_failed":
		return f"{stage}_failed"
	return f"{stage}_{failure}"


def summarize_temporal_reference_records(
	records: Sequence[Mapping[str, Any]],
	*,
	timeout_seconds: int,
) -> dict[str, Any]:
	"""Aggregate applicability, valid coverage, plan length, time, and PAR-2."""

	supported = [record for record in records if record.get("supported") is True]
	valid = [record for record in supported if record.get("success") is True]
	par2 = [
		float(record.get("elapsed_seconds") or 0.0)
		if record.get("success") is True
		else 2.0 * max(1, int(timeout_seconds))
		for record in supported
	]
	return {
		"case_count": len(records),
		"supported_case_count": len(supported),
		"unsupported_case_count": len(records) - len(supported),
		"valid_trace_count": len(valid),
		"coverage_on_supported": len(valid) / len(supported) if supported else None,
		"overall_coverage": len(valid) / len(records) if records else None,
		"mean_actions_on_valid": (
			sum(float(record.get("action_count") or 0) for record in valid) / len(valid)
			if valid
			else None
		),
		"mean_seconds_on_valid": (
			sum(float(record.get("elapsed_seconds") or 0.0) for record in valid) / len(valid)
			if valid
			else None
		),
		"par2_seconds_on_supported": sum(par2) / len(par2) if par2 else None,
	}


def base_record(task: DirectTemporalTask) -> dict[str, Any]:
	return {
		"method": METHOD.display_name,
		"variant": METHOD.value,
		"domain": task.domain,
		"sample_id": task.sample_id,
		"profile": task.profile,
		"domain_file": str(task.domain_file),
		"problem_file": str(task.problem_file),
		"domain_sha256": _sha256(task.domain_file),
		"problem_sha256": _sha256(task.problem_file),
		"supported": None,
		"success": False,
		"status": "pending",
		"action_count": 0,
		"elapsed_seconds": 0.0,
	}


def load_completed_records(
	tasks: Sequence[DirectTemporalTask],
) -> dict[str, dict[str, Any]]:
	"""Reuse only results whose benchmark inputs still match byte-for-byte."""

	completed: dict[str, dict[str, Any]] = {}
	for task in tasks:
		result_file = task.output_dir / "result.json"
		if not result_file.is_file():
			continue
		record = _read_json(result_file)
		if (
			record.get("variant") == METHOD.value
			and record.get("sample_id") == task.sample_id
			and record.get("domain_sha256") == _sha256(task.domain_file)
			and record.get("problem_sha256") == _sha256(task.problem_file)
			and not is_infrastructure_failure(record.get("status"))
		):
			completed[task.sample_id] = record
	return completed


def progress_line(record: Mapping[str, Any]) -> str:
	if record.get("supported") is False:
		prefix = "skip"
	else:
		prefix = "ok" if record.get("success") is True else "fail"
	return (
		f"[{prefix}] method={METHOD.display_name} domain={record.get('domain')} "
		f"sample={record.get('sample_id')} status={record.get('status')} "
		f"actions={record.get('action_count', 0)} "
		f"elapsed={float(record.get('elapsed_seconds') or 0.0):.1f}s"
	)


def record_sort_key(record: Mapping[str, Any]) -> tuple[str, str]:
	return str(record.get("domain") or ""), str(record.get("sample_id") or "")


def temporal_toolchain_metadata(
	fond4ltlf_executable: Path,
	mona_executable: Path,
) -> dict[str, Any]:
	"""Record pinned direct-reference compiler and planner identities."""

	executable = fond4ltlf_executable.expanduser().resolve()
	fond_root = executable.parents[2] if len(executable.parents) >= 3 else executable.parent
	return {
		"fond4ltlf": {
			"root": str(fond_root),
			"git_revision": _git_revision(fond_root),
			"release": "v0.0.4",
			"executable": str(executable),
			"executable_sha256": _sha256(executable),
		},
		"mona": {
			"version": "1.4-18",
			"executable": str(mona_executable.expanduser().resolve()),
			"executable_sha256": _sha256(mona_executable),
		},
		"lama": {
			"source": "MOOSE official artifact search lama-first",
			"moose_root": str(MOOSE_ROOT),
			"moose_git_revision": _git_revision(MOOSE_ROOT),
			"moose_artifact_sha256": _sha256(MOOSE_ROOT / "moose.sif"),
			"docker_image": "moose-exact-ubuntu22:local",
		},
	}


def _git_revision(repository: Path) -> str | None:
	if not (repository / ".git").exists():
		return None
	completed = subprocess.run(
		("git", "-C", str(repository), "rev-parse", "HEAD"),
		capture_output=True,
		text=True,
		check=False,
	)
	return completed.stdout.strip() if completed.returncode == 0 else None


def _mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
	value = payload.get(key)
	if not isinstance(value, Mapping):
		raise ValueError(f"Expected object field {key!r}.")
	return value


def _as_mapping(value: Any, *, label: str) -> Mapping[str, Any]:
	if not isinstance(value, Mapping):
		raise ValueError(f"Expected {label} to be an object.")
	return value


def _read_json(path: Path) -> dict[str, Any]:
	payload = json.loads(path.read_text(encoding="utf-8"))
	if not isinstance(payload, dict):
		raise ValueError(f"Expected JSON object: {path}")
	return payload


def _sha256(path: str | Path) -> str | None:
	file_path = Path(path).expanduser()
	if not file_path.is_file():
		return None
	digest = hashlib.sha256()
	with file_path.open("rb") as handle:
		for chunk in iter(lambda: handle.read(1024 * 1024), b""):
			digest.update(chunk)
	return digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
	path.write_text(
		"".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
		encoding="utf-8",
	)


if __name__ == "__main__":
	raise SystemExit(main())
