#!/usr/bin/env python3
"""Run native task-level MOOSE, LAMA, and ENHSP planning references."""

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
import shutil
import statistics
import subprocess
import sys
import time
from typing import Any
from typing import Mapping
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
DEFAULT_BATCH_ROOT = PROJECT_ROOT / "artifacts/moose_asl_batches"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "artifacts/external_planning_references"
DEFAULT_ENHSP_ROOT = PROJECT_ROOT / ".external/enhsp-socs24"

if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from evaluation.external_plan_verifier import run_external_plan_verifier  # noqa: E402
from evaluation.external_reference_planners import (  # noqa: E402
	ExternalReferenceMethod,
)
from evaluation.external_reference_planners import build_enhsp_command  # noqa: E402
from evaluation.external_reference_planners import (  # noqa: E402
	reference_methods_for_domain,
)
from scripts.run_full_test_jason_validation import (  # noqa: E402
	source_revision_metadata,
)
from scripts.run_moose_faithful_e2e import DEFAULT_DOMAINS  # noqa: E402
from scripts.run_moose_faithful_e2e import MOOSE_ROOT  # noqa: E402
from scripts.run_moose_faithful_e2e import container_path  # noqa: E402
from scripts.run_moose_faithful_e2e import moose_runtime_command  # noqa: E402
from scripts.run_moose_faithful_e2e import natural_sort_key  # noqa: E402
from scripts.run_moose_faithful_e2e import normalise_pddl_for_moose  # noqa: E402


ACHIEVEMENT_METHODS = (
	ExternalReferenceMethod.RAW_MOOSE,
	ExternalReferenceMethod.LAMA,
	ExternalReferenceMethod.ENHSP_HMRPHJ,
)
INFRASTRUCTURE_FAILURES = {
	"input_error",
	"plan_verifier_unavailable",
	"runner_error",
	"tool_unavailable",
}


@dataclass(frozen=True)
class ReferenceTask:
	"""One method/problem pair evaluated in an isolated artifact directory."""

	method: ExternalReferenceMethod
	domain: str
	domain_file: Path
	problem_file: Path
	output_dir: Path
	model_file: Path | None = None


@dataclass(frozen=True)
class GuardedCommandResult:
	"""Persisted subprocess outcome under the common paper resource limits."""

	command: tuple[str, ...]
	exit_code: int
	elapsed_seconds: float
	stdout_file: Path
	stderr_file: Path


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--batch-root", type=Path, default=DEFAULT_BATCH_ROOT)
	parser.add_argument("--batch-id", default="latest")
	parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
	parser.add_argument("--run-id")
	parser.add_argument(
		"--method",
		action="append",
		choices=tuple(method.value for method in ACHIEVEMENT_METHODS),
		help="Repeat to select references. The default runs every applicable method.",
	)
	parser.add_argument("--domain", action="append", choices=DEFAULT_DOMAINS)
	parser.add_argument("--num-workers", type=int, default=1)
	parser.add_argument("--timeout-seconds", type=int, default=1800)
	parser.add_argument("--max-rss-gb", type=float, default=8.0)
	parser.add_argument("--plan-verifier-timeout-seconds", type=int, default=1800)
	parser.add_argument(
		"--plan-verifier-command",
		default=f"bash {PROJECT_ROOT / 'scripts/validate_with_docker_val.sh'}",
	)
	parser.add_argument(
		"--enhsp-jar",
		type=Path,
		default=DEFAULT_ENHSP_ROOT / "enhsp.jar",
	)
	parser.add_argument("--max-cases", type=int)
	parser.add_argument("--resume", action="store_true")
	return parser.parse_args()


def build_moose_reference_arguments(
	*,
	method: ExternalReferenceMethod,
	domain_file: str,
	problem_file: str,
	plan_file: str,
	model_file: str | None = None,
) -> tuple[str, ...]:
	"""Build arguments consumed by the official MOOSE Apptainer artifact."""

	if method is ExternalReferenceMethod.RAW_MOOSE:
		if not model_file:
			raise ValueError("Raw MOOSE reference requires a learned model file.")
		return (
			"policy",
			str(model_file),
			str(domain_file),
			str(problem_file),
			"--bound",
			"0",
			"--plan-file",
			str(plan_file),
		)
	if method is ExternalReferenceMethod.LAMA:
		return (
			"search",
			"lama-first",
			str(domain_file),
			str(problem_file),
			"--plan-file",
			str(plan_file),
		)
	raise ValueError(f"{method.value} is not executed by the MOOSE artifact.")


def resolve_model_batch(
	batch_root: str | Path,
	batch_id: str,
	domains: Sequence[str],
) -> Path:
	"""Resolve one MOOSE batch containing a model for every selected domain."""

	root = Path(batch_root).expanduser().resolve()
	if not root.is_dir():
		raise ValueError(f"Missing MOOSE model batch root: {root}")
	candidates = (
		tuple(sorted((path for path in root.iterdir() if path.is_dir()), reverse=True))
		if str(batch_id) == "latest"
		else (root / str(batch_id),)
	)
	for candidate in candidates:
		if all(model_file_for_domain(candidate, domain).is_file() for domain in domains):
			return candidate
	raise ValueError(
		"No complete MOOSE model batch contains every selected domain: "
		+ ", ".join(domains),
	)


def model_file_for_domain(batch_root: str | Path, domain: str) -> Path:
	"""Return the canonical native model location in a timestamped batch."""

	root = Path(batch_root)
	return root / "run_logs" / domain / f"{domain}.model"


def parse_guard_failure(stderr_text: str) -> str:
	"""Map the resource guard's explicit diagnostic to a stable status."""

	text = str(stderr_text).lower()
	if "timeout exceeded" in text:
		return "timeout"
	if "memory limit exceeded" in text:
		return "memory_limit"
	return "planner_failed"


def summarize_records(
	records: Sequence[Mapping[str, Any]],
	*,
	timeout_seconds: int,
) -> dict[str, Any]:
	"""Aggregate table-ready coverage, plan length, and PAR-2 by short method name."""

	method_records: dict[str, list[Mapping[str, Any]]] = {}
	for record in records:
		method_records.setdefault(str(record.get("method") or "unknown"), []).append(record)
	methods: dict[str, Any] = {}
	for method, items in sorted(method_records.items()):
		valid = [item for item in items if item.get("plan_verifier_success") is True]
		par2_values = [
			float(item.get("elapsed_seconds") or 0.0)
			if item.get("plan_verifier_success") is True
			else 2.0 * max(1, int(timeout_seconds))
			for item in items
		]
		methods[method] = {
			"case_count": len(items),
			"valid_trace_count": len(valid),
			"coverage": len(valid) / len(items) if items else 0.0,
			"median_actions_jointly_solved": (
				statistics.median(float(item.get("action_count") or 0) for item in valid)
				if valid
				else None
			),
			"median_solved_seconds": (
				statistics.median(float(item.get("elapsed_seconds") or 0.0) for item in valid)
				if valid
				else None
			),
			"par2_seconds": statistics.mean(par2_values) if par2_values else None,
		}
	return {
		"case_count": len(records),
		"valid_trace_count": sum(
			1 for record in records if record.get("plan_verifier_success") is True
		),
		"methods": methods,
	}


def main() -> int:
	args = parse_args()
	domains = tuple(args.domain or DEFAULT_DOMAINS)
	methods = tuple(
		ExternalReferenceMethod(value) for value in (args.method or ())
	) or ACHIEVEMENT_METHODS
	if args.max_rss_gb <= 0:
		raise ValueError("--max-rss-gb must be positive.")
	if args.num_workers <= 0 or args.timeout_seconds <= 0:
		raise ValueError("Worker and timeout values must be positive.")
	model_batch = (
		resolve_model_batch(args.batch_root, args.batch_id, domains)
		if ExternalReferenceMethod.RAW_MOOSE in methods
		else None
	)
	run_id = args.run_id or f"external-reference-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
	run_root = args.output_root.expanduser().resolve() / run_id
	if run_root.exists() and not args.resume:
		raise ValueError(f"Output directory already exists: {run_root}")
	run_root.mkdir(parents=True, exist_ok=True)
	tasks = build_tasks(
		domains=domains,
		methods=methods,
		run_root=run_root,
		model_batch=model_batch,
	)
	if args.max_cases is not None:
		tasks = tasks[: max(0, int(args.max_cases))]
	if not tasks:
		raise ValueError("No applicable external reference tasks were selected.")

	summary_file = run_root / "summary.json"
	manifest = {
		"schema_version": 1,
		"artifact_kind": "external_achievement_planning_references",
		"run_id": run_id,
		"started_at": datetime.now().isoformat(timespec="seconds"),
		"source_revision": source_revision_metadata(PROJECT_ROOT),
		"methods": [method.display_name for method in methods],
		"variants": [method.value for method in methods],
		"domains": list(domains),
		"model_batch": str(model_batch) if model_batch is not None else None,
		"parameters": {
			"num_workers": int(args.num_workers),
			"timeout_seconds": int(args.timeout_seconds),
			"max_rss_gb": float(args.max_rss_gb),
			"plan_verifier_timeout_seconds": int(args.plan_verifier_timeout_seconds),
			"plan_verifier_command": str(args.plan_verifier_command),
		},
		"toolchain": toolchain_metadata(args.enhsp_jar),
		"results": [],
	}
	_write_json(summary_file, manifest)

	existing = load_completed_records(tasks) if args.resume else {}
	records = list(existing.values())
	pending = tuple(task for task in tasks if task_key(task) not in existing)
	with ThreadPoolExecutor(max_workers=int(args.num_workers)) as executor:
		future_map = {
			executor.submit(
				run_reference_task,
				task,
				timeout_seconds=int(args.timeout_seconds),
				max_rss_gb=float(args.max_rss_gb),
				enhsp_jar=args.enhsp_jar.expanduser().resolve(),
				plan_verifier_command=str(args.plan_verifier_command),
				plan_verifier_timeout_seconds=int(args.plan_verifier_timeout_seconds),
			): task
			for task in pending
		}
		for future in as_completed(future_map):
			task = future_map[future]
			try:
				record = future.result()
			except Exception as error:  # noqa: BLE001 - persist per-case infrastructure failure.
				record = base_record(task)
				record.update(status="runner_error", error=str(error))
				_write_json(task.output_dir / "result.json", record)
			records.append(record)
			print(progress_line(record), flush=True)
			manifest["results"] = sorted(records, key=record_sort_key)
			_write_json(summary_file, manifest)

	records = sorted(records, key=record_sort_key)
	metrics = summarize_records(records, timeout_seconds=int(args.timeout_seconds))
	manifest.update(
		{
			"finished_at": datetime.now().isoformat(timespec="seconds"),
			"results": records,
			"metrics": metrics,
			"infrastructure_failure_count": sum(
				1 for record in records if record.get("status") in INFRASTRUCTURE_FAILURES
			),
		}
	)
	manifest["success"] = manifest["infrastructure_failure_count"] == 0
	_write_json(summary_file, manifest)
	_write_jsonl(run_root / "results.jsonl", records)
	print(
		f"[summary] valid={metrics['valid_trace_count']}/{metrics['case_count']} "
		f"artifact={summary_file}",
		flush=True,
	)
	return 0 if manifest["success"] else 1


def build_tasks(
	*,
	domains: Sequence[str],
	methods: Sequence[ExternalReferenceMethod],
	run_root: Path,
	model_batch: Path | None,
) -> tuple[ReferenceTask, ...]:
	"""Build feature-selected tasks over every held-out problem."""

	tasks: list[ReferenceTask] = []
	for domain in domains:
		domain_root = PROJECT_ROOT / "src/domains" / domain
		domain_file = domain_root / "domain.pddl"
		test_dir = domain_root / "test"
		if not domain_file.is_file() or not test_dir.is_dir():
			raise ValueError(f"Missing benchmark domain or test split: {domain}")
		applicable = set(reference_methods_for_domain(domain_file))
		for method in methods:
			if method not in applicable:
				continue
			model_file = (
				model_file_for_domain(model_batch, domain)
				if method is ExternalReferenceMethod.RAW_MOOSE and model_batch is not None
				else None
			)
			for problem_file in sorted(test_dir.glob("*.pddl"), key=natural_sort_key):
				tasks.append(
					ReferenceTask(
						method=method,
						domain=domain,
						domain_file=domain_file,
						problem_file=problem_file,
						model_file=model_file,
						output_dir=(
							run_root
							/ "cases"
							/ method.value
							/ domain
							/ problem_file.stem
						),
					),
				)
	return tuple(tasks)


def run_reference_task(
	task: ReferenceTask,
	*,
	timeout_seconds: int,
	max_rss_gb: float,
	enhsp_jar: Path,
	plan_verifier_command: str,
	plan_verifier_timeout_seconds: int,
) -> dict[str, Any]:
	"""Run one native planner and accept it only after external VAL validation."""

	task.output_dir.mkdir(parents=True, exist_ok=True)
	record = base_record(task)
	plan_file = task.output_dir / "plan.plan"
	try:
		command = reference_command(
			task,
			plan_file=plan_file,
			enhsp_jar=enhsp_jar,
			max_rss_gb=max_rss_gb,
		)
	except (FileNotFoundError, ValueError) as error:
		record.update(status="tool_unavailable", error=str(error))
		_write_json(task.output_dir / "result.json", record)
		return record
	command_result = run_guarded_command(
		command,
		output_dir=task.output_dir,
		timeout_seconds=timeout_seconds,
		max_rss_gb=max_rss_gb,
	)
	record.update(
		{
			"command": list(command_result.command),
			"planner_exit_code": command_result.exit_code,
			"elapsed_seconds": command_result.elapsed_seconds,
			"planner_stdout": str(command_result.stdout_file),
			"planner_stderr": str(command_result.stderr_file),
		}
	)
	if command_result.exit_code != 0:
		record["status"] = parse_guard_failure(
			command_result.stderr_file.read_text(encoding="utf-8", errors="replace"),
		)
		_write_json(task.output_dir / "result.json", record)
		return record
	if not plan_file.is_file() or plan_file.stat().st_size == 0:
		record["status"] = "no_plan"
		_write_json(task.output_dir / "result.json", record)
		return record
	actions = plan_action_lines(plan_file)
	record["action_count"] = len(actions)
	record["plan_file"] = str(plan_file)
	verifier = run_external_plan_verifier(
		domain_file=task.domain_file,
		problem_file=task.problem_file,
		plan_file=plan_file,
		output_dir=task.output_dir / "validation",
		command=plan_verifier_command,
		timeout_seconds=plan_verifier_timeout_seconds,
	)
	record.update(
		{
			"plan_verifier_attempted": verifier.attempted,
			"plan_verifier_available": verifier.available,
			"plan_verifier_success": verifier.success,
			"plan_verifier_timed_out": verifier.timed_out,
			"plan_verifier_exit_code": verifier.exit_code,
			"plan_verifier_command": list(verifier.command),
		}
	)
	if not verifier.available:
		record["status"] = "plan_verifier_unavailable"
	elif verifier.timed_out:
		record["status"] = "plan_verifier_timeout"
	elif verifier.success is True:
		record["status"] = "valid"
	else:
		record["status"] = "plan_verifier_failed"
	_write_json(task.output_dir / "result.json", record)
	return record


def reference_command(
	task: ReferenceTask,
	*,
	plan_file: Path,
	enhsp_jar: Path,
	max_rss_gb: float,
) -> tuple[str, ...]:
	"""Materialize compatibility inputs and return the native planner command."""

	if task.method is ExternalReferenceMethod.ENHSP_HMRPHJ:
		if not enhsp_jar.is_file():
			raise FileNotFoundError(f"Missing pinned ENHSP jar: {enhsp_jar}")
		return build_enhsp_command(
			jar_file=enhsp_jar,
			domain_file=task.domain_file,
			problem_file=task.problem_file,
			plan_file=plan_file,
		)
	if task.method is ExternalReferenceMethod.RAW_MOOSE:
		if task.model_file is None or not task.model_file.is_file():
			raise FileNotFoundError(f"Missing Raw MOOSE model: {task.model_file}")
		compatibility_root = task.output_dir / "moose_compatible_pddl"
		compatibility_root.mkdir(parents=True, exist_ok=True)
		domain_file = compatibility_root / "domain.pddl"
		problem_file = compatibility_root / task.problem_file.name
		domain_file.write_text(
			normalise_pddl_for_moose(task.domain_file.read_text(encoding="utf-8")),
			encoding="utf-8",
		)
		problem_file.write_text(
			normalise_pddl_for_moose(task.problem_file.read_text(encoding="utf-8")),
			encoding="utf-8",
		)
	else:
		domain_file = task.domain_file
		problem_file = task.problem_file
	arguments = build_moose_reference_arguments(
		method=task.method,
		domain_file=container_path(domain_file),
		problem_file=container_path(problem_file),
		plan_file=container_path(plan_file),
		model_file=(container_path(task.model_file) if task.model_file is not None else None),
	)
	return moose_runtime_command(
		arguments,
		runtime="docker",
		max_rss_gb=max_rss_gb,
	)


def run_guarded_command(
	command: Sequence[str],
	*,
	output_dir: Path,
	timeout_seconds: int,
	max_rss_gb: float,
	extra_env: Mapping[str, str] | None = None,
) -> GuardedCommandResult:
	"""Run one planner under the shared hard process-tree resource guard."""

	stdout_file = output_dir / "planner.stdout.txt"
	stderr_file = output_dir / "planner.stderr.txt"
	guarded = (
		sys.executable,
		str(PROJECT_ROOT / "scripts/resource_guard.py"),
		"--max-rss-gb",
		str(max_rss_gb),
		"--timeout-seconds",
		str(max(1, int(timeout_seconds))),
		"--label",
		"external-planning-reference",
		"--",
		*tuple(str(item) for item in command),
	)
	started = time.monotonic()
	with stdout_file.open("w", encoding="utf-8") as stdout_handle, stderr_file.open(
		"w",
		encoding="utf-8",
	) as stderr_handle:
		completed = subprocess.run(
			guarded,
			cwd=PROJECT_ROOT,
			env={**os.environ, **dict(extra_env or {})},
			stdout=stdout_handle,
			stderr=stderr_handle,
			check=False,
		)
	return GuardedCommandResult(
		command=tuple(str(item) for item in command),
		exit_code=completed.returncode,
		elapsed_seconds=time.monotonic() - started,
		stdout_file=stdout_file,
		stderr_file=stderr_file,
	)


def plan_action_lines(plan_file: Path) -> tuple[str, ...]:
	"""Return non-comment plan actions without interpreting planner internals."""

	return tuple(
		line.strip()
		for line in plan_file.read_text(encoding="utf-8", errors="replace").splitlines()
		if line.strip() and not line.lstrip().startswith(";")
	)


def base_record(task: ReferenceTask) -> dict[str, Any]:
	"""Return immutable input identities shared by every task outcome."""

	return {
		"method": task.method.display_name,
		"variant": task.method.value,
		"domain": task.domain,
		"test": task.problem_file.stem,
		"domain_file": str(task.domain_file),
		"problem_file": str(task.problem_file),
		"domain_sha256": _sha256(task.domain_file),
		"problem_sha256": _sha256(task.problem_file),
		"model_file": str(task.model_file) if task.model_file is not None else None,
		"model_sha256": (
			_sha256(task.model_file)
			if task.model_file is not None and task.model_file.is_file()
			else None
		),
		"status": "pending",
		"action_count": 0,
		"plan_verifier_success": None,
		"elapsed_seconds": 0.0,
	}


def task_key(task: ReferenceTask) -> str:
	return f"{task.method.value}:{task.domain}:{task.problem_file.stem}"


def load_completed_records(tasks: Sequence[ReferenceTask]) -> dict[str, dict[str, Any]]:
	"""Load only per-case results whose method/domain/test identity still matches."""

	completed: dict[str, dict[str, Any]] = {}
	for task in tasks:
		result_file = task.output_dir / "result.json"
		if not result_file.is_file():
			continue
		record = json.loads(result_file.read_text(encoding="utf-8"))
		if (
			record.get("variant") == task.method.value
			and record.get("domain") == task.domain
			and record.get("test") == task.problem_file.stem
			and record.get("domain_sha256") == _sha256(task.domain_file)
			and record.get("problem_sha256") == _sha256(task.problem_file)
		):
			completed[task_key(task)] = record
	return completed


def progress_line(record: Mapping[str, Any]) -> str:
	status = "ok" if record.get("status") == "valid" else "fail"
	return (
		f"[{status}] method={record.get('method')} domain={record.get('domain')} "
		f"test={record.get('test')} status={record.get('status')} "
		f"actions={record.get('action_count', 0)} "
		f"elapsed={float(record.get('elapsed_seconds') or 0.0):.1f}s"
	)


def record_sort_key(record: Mapping[str, Any]) -> tuple[str, str, tuple[object, ...]]:
	return (
		str(record.get("variant") or ""),
		str(record.get("domain") or ""),
		natural_sort_key(Path(str(record.get("test") or ""))),
	)


def toolchain_metadata(enhsp_jar: Path) -> dict[str, Any]:
	"""Record exact source and executable identities, never a floating tool name."""

	return {
		"moose": {
			"root": str(MOOSE_ROOT),
			"git_revision": _git_revision(MOOSE_ROOT),
			"artifact_sha256": _sha256(MOOSE_ROOT / "moose.sif"),
			"docker_image": "moose-exact-ubuntu22:local",
			"docker_image_id": _docker_image_id("moose-exact-ubuntu22:local"),
		},
		"enhsp": {
			"jar": str(enhsp_jar.expanduser().resolve()),
			"git_revision": _git_revision(enhsp_jar.expanduser().resolve().parent),
			"jar_sha256": _sha256(enhsp_jar),
			"configuration": "sat-hmrphj",
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


def _docker_image_id(image: str) -> str | None:
	if shutil.which("docker") is None:
		return None
	completed = subprocess.run(
		("docker", "image", "inspect", image, "--format", "{{.Id}}"),
		capture_output=True,
		text=True,
		check=False,
	)
	return completed.stdout.strip() if completed.returncode == 0 else None


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
