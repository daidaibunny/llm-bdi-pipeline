#!/usr/bin/env python3
"""Append every test goal from a MOOSE ASL batch and validate it in Jason."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from dataclasses import dataclass
from dataclasses import replace
from datetime import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
DEFAULT_BATCH_ROOT = PROJECT_ROOT / "artifacts" / "moose_asl_batches"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "artifacts" / "jason_full_test_runs"
ATOMIC_LIBRARY_MODES = ("faithful", "validated-policy-lifting")

if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from evaluation.jason_runtime import JasonPlanLibraryRunner  # noqa: E402
from evaluation.jason_runtime.runner import _build_indexed_belief_base_java_source  # noqa: E402
from evaluation.jason_runtime.runner import _build_environment_java_source  # noqa: E402
from evaluation.jason_runtime.runner import _resolve_jason_classpath  # noqa: E402
from evaluation.jason_runtime.runner import _runtime_action_schema  # noqa: E402
from evaluation.jason_runtime.runner import build_runtime_problem_artifacts  # noqa: E402
from domain_level_planning import AtomicCompilerVariant  # noqa: E402
from scripts.run_moose_faithful_e2e import DEFAULT_DOMAINS  # noqa: E402
from scripts.run_moose_faithful_e2e import natural_sort_key  # noqa: E402
from plan_library.models import PlanLibrary  # noqa: E402
from plan_library.rendering import render_plan_library_asl  # noqa: E402
from plan_library.rendering import sanitize_identifier  # noqa: E402
from domain_level_planning.certified_effects import (  # noqa: E402
	preservation_safe_plan_selection,
	query_local_preservation_alias_plans,
	threat_safe_positive_literal_order,
)
from domain_level_planning.transition_repair_tree import (  # noqa: E402
	TransitionRepairLiteral,
	compile_transition_repair_tree,
)
from utils.pddl_parser import PDDLFact  # noqa: E402
from utils.pddl_parser import PDDLNumericAssignment  # noqa: E402
from utils.pddl_parser import PDDLNumericCondition  # noqa: E402
from utils.pddl_parser import PDDLNumericExpression  # noqa: E402
from utils.pddl_parser import PDDLNumericFluent  # noqa: E402
from utils.pddl_parser import PDDLParser  # noqa: E402


@dataclass(frozen=True)
class ShellCommandResult:
	"""File-backed command result for compile and append stages."""

	command: tuple[str, ...]
	stdout_file: str
	stderr_file: str
	exit_code: int | None
	duration_seconds: float
	timed_out: bool = False

	@property
	def success(self) -> bool:
		return not self.timed_out and self.exit_code == 0

	def to_dict(self) -> dict[str, Any]:
		return {
			"command": list(self.command),
			"stdout_file": self.stdout_file,
			"stderr_file": self.stderr_file,
			"exit_code": self.exit_code,
			"duration_seconds": self.duration_seconds,
			"timed_out": self.timed_out,
			"success": self.success,
		}


@dataclass(frozen=True)
class JasonTask:
	"""One full-test Jason validation task."""

	domain: str
	index: int
	problem_file: Path
	domain_file: Path
	plan_library_asl: Path
	base_plan_library_asl_text: str
	goal_name: str
	output_dir: Path
	runtime_wrapper_text: str | None = None
	atomic_plan_library: PlanLibrary | None = None
	base_plan_library_sha256: str | None = None
	atomic_plan_library_sha256: str | None = None
	source_problem_file: Path | None = None
	source_domain_file: Path | None = None


def source_revision_metadata(project_root: Path) -> dict[str, Any]:
	"""Capture the exact source revision used to start one validation run."""

	try:
		commit_result = subprocess.run(
			("git", "rev-parse", "HEAD"),
			cwd=project_root,
			text=True,
			capture_output=True,
			check=True,
		)
		status_result = subprocess.run(
			("git", "status", "--porcelain=v1", "--untracked-files=all"),
			cwd=project_root,
			text=True,
			capture_output=True,
			check=True,
		)
	except (OSError, subprocess.CalledProcessError) as error:
		return {
			"available": False,
			"error": str(error),
		}
	status_lines = tuple(
		line for line in status_result.stdout.splitlines() if line.strip()
	)
	return {
		"available": True,
		"commit": commit_result.stdout.strip(),
		"tracked_changes": any(not line.startswith("??") for line in status_lines),
		"untracked_files": any(line.startswith("??") for line in status_lines),
	}


def validation_input_fingerprint(task: JasonTask) -> str:
	"""Fingerprint the immutable inputs that determine one validation case."""

	base_asl_sha256 = task.base_plan_library_sha256 or hashlib.sha256(
		task.base_plan_library_asl_text.encode("utf-8"),
	).hexdigest()
	if task.atomic_plan_library_sha256:
		atomic_library_sha256 = task.atomic_plan_library_sha256
	elif task.atomic_plan_library is not None:
		atomic_library_sha256 = hashlib.sha256(
			json.dumps(
				task.atomic_plan_library.to_dict(),
				sort_keys=True,
				separators=(",", ":"),
			).encode("utf-8"),
		).hexdigest()
	else:
		atomic_library_sha256 = "none"
	wrapper_sha256 = (
		hashlib.sha256(task.runtime_wrapper_text.encode("utf-8")).hexdigest()
		if task.runtime_wrapper_text is not None
		else "generated_from_registered_inputs"
	)
	payload = {
		"domain": task.domain,
		"domain_sha256": _sha256_file(task.domain_file),
		"problem_sha256": _sha256_file(task.problem_file),
		"goal_name": task.goal_name,
		"base_plan_library_sha256": base_asl_sha256,
		"atomic_plan_library_sha256": atomic_library_sha256,
		"runtime_wrapper_sha256": wrapper_sha256,
	}
	return hashlib.sha256(
		json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
	).hexdigest()


def snapshot_jason_task_inputs(
	tasks: Sequence[JasonTask],
	*,
	run_root: Path,
	recovery_timeout_seconds: float = 900.0,
	poll_interval_seconds: float = 0.25,
) -> tuple[JasonTask, ...]:
	"""Stage immutable PDDL inputs and return tasks bound to the snapshot.

	The source benchmark tree is materialized data and may be replaced while a
	long validation run is active. Every worker therefore reads a run-local copy.
	A complete manifest makes the copy reusable even when the source tree is
	temporarily unavailable during a later resume.
	"""

	all_tasks = tuple(tasks)
	if not all_tasks:
		return ()
	if recovery_timeout_seconds <= 0 or poll_interval_seconds <= 0:
		raise ValueError("input snapshot recovery timing must be positive")
	snapshot_root = run_root / "input_snapshot"
	manifest_file = snapshot_root / "manifest.json"
	if manifest_file.is_file():
		return _load_snapshotted_jason_tasks(
			all_tasks,
			run_root=run_root,
			manifest_file=manifest_file,
		)

	deadline = time.monotonic() + float(recovery_timeout_seconds)
	copied_files: dict[Path, tuple[Path, str]] = {}
	snapshotted_tasks: list[JasonTask] = []
	manifest_tasks: list[dict[str, Any]] = []
	for task in all_tasks:
		source_domain = (task.source_domain_file or task.domain_file).resolve()
		source_problem = (task.source_problem_file or task.problem_file).resolve()
		domain_target = snapshot_root / task.domain / "domain.pddl"
		problem_target = snapshot_root / task.domain / "test" / source_problem.name
		snapshot_domain, domain_sha256 = _snapshot_file_with_recovery(
			source=source_domain,
			target=domain_target,
			deadline=deadline,
			poll_interval_seconds=poll_interval_seconds,
			cache=copied_files,
		)
		snapshot_problem, problem_sha256 = _snapshot_file_with_recovery(
			source=source_problem,
			target=problem_target,
			deadline=deadline,
			poll_interval_seconds=poll_interval_seconds,
			cache=copied_files,
		)
		snapshotted_tasks.append(
			replace(
				task,
				domain_file=snapshot_domain,
				problem_file=snapshot_problem,
				source_domain_file=source_domain,
				source_problem_file=source_problem,
			),
		)
		manifest_tasks.append(
			{
				"domain": task.domain,
				"test_index": task.index,
				"source_domain_file": str(source_domain),
				"source_problem_file": str(source_problem),
				"snapshot_domain_file": str(snapshot_domain.relative_to(run_root)),
				"snapshot_problem_file": str(snapshot_problem.relative_to(run_root)),
				"domain_sha256": domain_sha256,
				"problem_sha256": problem_sha256,
			},
		)
	manifest = {
		"schema_version": 1,
		"artifact_kind": "full_test_validation_input_snapshot",
		"task_count": len(snapshotted_tasks),
		"tasks": manifest_tasks,
	}
	_write_json_atomically(manifest_file, manifest)
	return tuple(snapshotted_tasks)


def _snapshot_file_with_recovery(
	*,
	source: Path,
	target: Path,
	deadline: float,
	poll_interval_seconds: float,
	cache: dict[Path, tuple[Path, str]],
) -> tuple[Path, str]:
	if source in cache:
		return cache[source]
	last_error: OSError | None = None
	while True:
		try:
			before = source.stat()
			content = source.read_bytes()
			after = source.stat()
			if (
				before.st_size != after.st_size
				or before.st_mtime_ns != after.st_mtime_ns
				or len(content) != after.st_size
			):
				raise OSError(f"source changed while snapshotting: {source}")
			target.parent.mkdir(parents=True, exist_ok=True)
			temporary = target.with_name(f".{target.name}.snapshot.tmp")
			temporary.write_bytes(content)
			temporary.replace(target)
			digest = hashlib.sha256(content).hexdigest()
			cache[source] = (target, digest)
			return target, digest
		except OSError as error:
			last_error = error
			if time.monotonic() >= deadline:
				raise TimeoutError(
					"validation input did not become stable before the recovery "
					f"deadline: {source}: {last_error}",
				) from error
			time.sleep(poll_interval_seconds)


def _load_snapshotted_jason_tasks(
	tasks: Sequence[JasonTask],
	*,
	run_root: Path,
	manifest_file: Path,
) -> tuple[JasonTask, ...]:
	try:
		manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
	except (OSError, json.JSONDecodeError) as error:
		raise ValueError(f"invalid validation input snapshot manifest: {error}") from error
	if not isinstance(manifest, Mapping) or manifest.get("schema_version") != 1:
		raise ValueError("unsupported validation input snapshot manifest")
	entries = manifest.get("tasks")
	if not isinstance(entries, list) or len(entries) != len(tasks):
		raise ValueError("validation input snapshot task set does not match the run")
	entry_by_key = {
		(str(entry.get("domain") or ""), int(entry.get("test_index") or -1)): entry
		for raw_entry in entries
		if isinstance(raw_entry, Mapping)
		for entry in (dict(raw_entry),)
	}
	result: list[JasonTask] = []
	for task in tasks:
		entry = entry_by_key.get((task.domain, task.index))
		if entry is None:
			raise ValueError(
				"validation input snapshot is missing "
				f"{task.domain} test {task.index}",
			)
		source_domain = (task.source_domain_file or task.domain_file).resolve()
		source_problem = (task.source_problem_file or task.problem_file).resolve()
		if (
			str(entry.get("source_domain_file") or "") != str(source_domain)
			or str(entry.get("source_problem_file") or "") != str(source_problem)
		):
			raise ValueError("validation input snapshot source mapping changed")
		snapshot_domain = run_root / str(entry.get("snapshot_domain_file") or "")
		snapshot_problem = run_root / str(entry.get("snapshot_problem_file") or "")
		if (
			_sha256_file(snapshot_domain) != str(entry.get("domain_sha256") or "")
			or _sha256_file(snapshot_problem) != str(entry.get("problem_sha256") or "")
		):
			raise ValueError("validation input snapshot content hash mismatch")
		result.append(
			replace(
				task,
				domain_file=snapshot_domain,
				problem_file=snapshot_problem,
				source_domain_file=source_domain,
				source_problem_file=source_problem,
			),
		)
	return tuple(result)


def _write_json_atomically(path: Path, payload: Mapping[str, Any]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	temporary = path.with_name(f".{path.name}.tmp")
	temporary.write_text(
		json.dumps(payload, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)
	temporary.replace(path)


def load_completed_validation_records(
	tasks: Sequence[JasonTask],
) -> dict[tuple[str, int], dict[str, Any]]:
	"""Load only per-test records whose complete registered inputs still match."""

	completed: dict[tuple[str, int], dict[str, Any]] = {}
	for task in tasks:
		record_file = task.output_dir / "validation_record.json"
		if not record_file.is_file():
			continue
		try:
			record = json.loads(record_file.read_text(encoding="utf-8"))
		except (OSError, json.JSONDecodeError):
			continue
		if not isinstance(record, Mapping):
			continue
		if (
			str(record.get("domain") or "") != task.domain
			or int(record.get("test_index") or -1) != task.index
			or str(record.get("goal_name") or "") != task.goal_name
			or str(record.get("input_fingerprint") or "")
			!= validation_input_fingerprint(task)
		):
			continue
		completed[(task.domain, task.index)] = dict(record)
	return completed


def validate_full_test_resume_summary(
	previous: Mapping[str, Any],
	*,
	source_revision: Mapping[str, Any],
	batch_id: str,
	settings: Mapping[str, Any],
) -> None:
	"""Reject a resume request that changes source, evidence, or run settings."""

	if dict(previous.get("source_revision") or {}) != dict(source_revision):
		raise ValueError("resume source revision does not match the original run")
	if str(previous.get("source_batch_id") or "") != str(batch_id):
		raise ValueError("resume evidence batch does not match the original run")
	previous_settings = dict(previous.get("settings") or {})
	for key, value in settings.items():
		if key in {"resume_enabled", "suppress_final_summary_json"}:
			continue
		if previous_settings.get(key) != value:
			raise ValueError(f"resume setting does not match the original run: {key}")


def _sha256_file(path: Path) -> str:
	hasher = hashlib.sha256()
	with path.open("rb") as handle:
		for chunk in iter(lambda: handle.read(1024 * 1024), b""):
			hasher.update(chunk)
	return hasher.hexdigest()


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"--batch-id",
		default="latest",
		help="Timestamped MOOSE ASL batch id, or 'latest'.",
	)
	parser.add_argument(
		"--batch-root",
		type=Path,
		default=DEFAULT_BATCH_ROOT,
		help="Root containing timestamped MOOSE ASL batches.",
	)
	parser.add_argument(
		"--output-root",
		type=Path,
		default=DEFAULT_OUTPUT_ROOT,
		help="Root for full-test Jason validation files.",
	)
	parser.add_argument(
		"--run-id",
		help="Stable output id. Defaults to <batch-id>-full-test-YYYYmmdd-HHMMSS.",
	)
	parser.add_argument(
		"--domain",
		action="append",
		choices=DEFAULT_DOMAINS,
		help="Domain to validate. Repeat to select multiple. Defaults to all selected domains.",
	)
	parser.add_argument("--num-workers", type=int, default=6)
	parser.add_argument("--timeout-seconds", type=int, default=1800)
	parser.add_argument(
		"--input-recovery-timeout-seconds",
		type=float,
		default=900.0,
		help=(
			"Maximum infrastructure-only wait for materialized PDDL inputs to "
			"become stable before creating the immutable run snapshot."
		),
	)
	parser.add_argument(
		"--jason-java-stack-size",
		default="64m",
		help=(
			"Java thread stack size for Jason, passed as -Xss<size>. "
			"Defaults to 64m so large parser-order query wrappers do not "
			"overflow the JVM default stack."
		),
	)
	parser.add_argument(
		"--plan-verifier-command",
		help=(
			"VAL or IPC verifier command. Defaults to VAL_VALIDATE_BIN, VAL_BIN, "
			"IPC_VALIDATE_BIN, or Validate/validate/VAL on PATH."
		),
	)
	parser.add_argument(
		"--require-plan-verifier",
		action=argparse.BooleanOptionalAction,
		default=True,
		help=(
			"Require the exported PDDL plan trace to pass VAL/IPC verifier. "
			"Enabled by default for paper-quality validation."
		),
	)
	parser.add_argument(
		"--plan-verifier-timeout-seconds",
		type=int,
		default=1800,
		help="Hard timeout for VAL/IPC plan verification.",
	)
	parser.add_argument(
		"--atomic-library-mode",
		choices=ATOMIC_LIBRARY_MODES,
		default="validated-policy-lifting",
		help=(
			"Compile raw MOOSE decision-list macros faithfully, or validate and "
			"lift MOOSE singleton policy evidence with the PDDL schema before "
			"Jason validation. Defaults to validated-policy-lifting."
		),
	)
	parser.add_argument(
		"--compiler-variant",
		choices=tuple(variant.value for variant in AtomicCompilerVariant),
		help=(
			"Registered post-evidence compiler variant. Validated policy lifting "
			"defaults to Full Compiler when omitted."
		),
	)
	parser.add_argument(
		"--write-domain-long-asl",
		action="store_true",
		help=(
			"Also write one full-test ASL per domain. Disabled by default because "
			"large validation suites can still produce bulky ASL files."
		),
	)
	parser.add_argument(
		"--write-per-test-runtime-asl",
		action="store_true",
		help=(
			"Also write each per-test runtime plan_library.asl before Jason runs. "
			"Disabled by default because agentspeak_generated.asl already contains "
			"the exact executable ASL used by Jason."
		),
	)
	parser.add_argument(
		"--max-domain-long-asl-mb",
		type=int,
		default=1024,
		help="Safety cap for --write-domain-long-asl output size.",
	)
	parser.add_argument(
		"--prepare-only",
		action="store_true",
		help="Compile and append full-test goals, but do not start Jason validation.",
	)
	parser.add_argument(
		"--test-name-regex",
		help="Optional Python regex for selecting test problem file names during probes.",
	)
	parser.add_argument(
		"--suppress-final-summary-json",
		action="store_true",
		help=(
			"Do not print the full summary JSON to stdout. The summary file is "
			"still written; per-test status lines remain visible."
		),
	)
	parser.add_argument(
		"--resume",
		action="store_true",
		help=(
			"Reuse completed per-test records only when their exact domain, problem, "
			"atomic-library, and wrapper inputs still match."
		),
	)
	args = parser.parse_args()
	if args.input_recovery_timeout_seconds <= 0:
		parser.error("--input-recovery-timeout-seconds must be positive")
	args.atomic_library_mode = normalise_atomic_library_mode(args.atomic_library_mode)
	if args.atomic_library_mode == "faithful" and args.compiler_variant:
		parser.error("--compiler-variant requires --atomic-library-mode validated-policy-lifting")
	compiler_variant = (
		AtomicCompilerVariant(args.compiler_variant or AtomicCompilerVariant.FULL.value)
		if args.atomic_library_mode == "validated-policy-lifting"
		else None
	)

	domains = tuple(args.domain or DEFAULT_DOMAINS)
	batch_root = resolve_batch_root(args.batch_root, args.batch_id)
	batch_id = batch_root.name
	run_id = args.run_id or f"{batch_id}-full-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
	run_root = args.output_root.expanduser().resolve() / run_id
	summary_file = run_root / "summary.json"
	current_revision = source_revision_metadata(PROJECT_ROOT)
	settings = {
		"domains": list(domains),
		"num_workers": args.num_workers,
		"timeout_seconds": args.timeout_seconds,
		"input_recovery_timeout_seconds": args.input_recovery_timeout_seconds,
		"jason_java_stack_size": args.jason_java_stack_size,
		"plan_verifier_command": args.plan_verifier_command,
		"require_plan_verifier": bool(args.require_plan_verifier),
		"plan_verifier_timeout_seconds": args.plan_verifier_timeout_seconds,
		"atomic_library_mode": args.atomic_library_mode,
		"compiler_variant": (
			compiler_variant.value if compiler_variant is not None else None
		),
		"method": (
			compiler_variant.display_name if compiler_variant is not None else "Raw MOOSE"
		),
		"prepare_only": bool(args.prepare_only),
		"write_domain_long_asl": bool(args.write_domain_long_asl),
		"write_per_test_runtime_asl": bool(args.write_per_test_runtime_asl),
		"max_domain_long_asl_mb": args.max_domain_long_asl_mb,
		"suppress_final_summary_json": bool(args.suppress_final_summary_json),
		"resume_enabled": bool(args.resume),
	}
	previous_summary: dict[str, Any] | None = None
	if run_root.exists():
		if not args.resume or not summary_file.is_file():
			print(f"output directory already exists: {run_root}", file=sys.stderr)
			return 2
		try:
			loaded_summary = json.loads(summary_file.read_text(encoding="utf-8"))
			if not isinstance(loaded_summary, Mapping):
				raise ValueError("existing summary is not a JSON object")
			validate_full_test_resume_summary(
				loaded_summary,
				source_revision=current_revision,
				batch_id=batch_id,
				settings=settings,
			)
			previous_summary = dict(loaded_summary)
		except (OSError, json.JSONDecodeError, ValueError) as error:
			print(f"cannot resume {run_root}: {error}", file=sys.stderr)
			return 2
	run_root.mkdir(parents=True, exist_ok=True)

	summary: dict[str, Any] = {
		"artifact_kind": "full_test_jason_validation_from_moose_asl_batch",
		"created_at": (
			str(previous_summary.get("created_at"))
			if previous_summary is not None
			else datetime.now().isoformat(timespec="seconds")
		),
		"resumed_at": (
			datetime.now().isoformat(timespec="seconds")
			if previous_summary is not None
			else None
		),
		"source_revision": current_revision,
		"source_batch_id": batch_id,
		"source_batch_root": str(batch_root),
		"run_id": run_id,
		"run_root": str(run_root),
		"settings": settings,
		"domains": {},
		"validations": [],
	}
	write_json(summary_file, summary)

	tasks: list[JasonTask] = []
	for domain in domains:
		record, domain_tasks = prepare_domain_for_full_test(
			domain=domain,
			batch_root=batch_root,
			run_root=run_root,
			timeout_seconds=args.timeout_seconds,
			atomic_library_mode=args.atomic_library_mode,
			compiler_variant=compiler_variant,
			write_domain_long_asl=bool(args.write_domain_long_asl),
			max_domain_long_asl_bytes=max(1, int(args.max_domain_long_asl_mb)) * 1024 * 1024,
			test_name_regex=args.test_name_regex,
		)
		summary["domains"][domain] = record
		tasks.extend(domain_tasks if record.get("success") else ())
		write_json(summary_file, summary)

	if args.prepare_only:
		summary["completed_at"] = datetime.now().isoformat(timespec="seconds")
		summary["success"] = all(
			bool(record.get("success")) for record in summary["domains"].values()
		)
		write_json(summary_file, summary)
		if args.suppress_final_summary_json:
			print(f"summary_file={summary_file}", flush=True)
		else:
			print(json.dumps(summary, indent=2, sort_keys=True))
		return 0 if summary["success"] else 1

	classpath = resolve_jason_classpath_once()
	validation_records = run_jason_tasks(
		tasks=tuple(tasks),
		classpath=classpath,
		run_root=run_root,
		num_workers=max(1, int(args.num_workers)),
		timeout_seconds=max(1, int(args.timeout_seconds)),
		jason_java_stack_size=str(args.jason_java_stack_size or "64m"),
		plan_verifier_command=args.plan_verifier_command,
		require_plan_verifier=bool(args.require_plan_verifier),
		plan_verifier_timeout_seconds=max(1, int(args.plan_verifier_timeout_seconds)),
		write_per_test_runtime_asl=bool(args.write_per_test_runtime_asl),
		input_recovery_timeout_seconds=max(
			0.001,
			float(args.input_recovery_timeout_seconds),
		),
		summary=summary,
		summary_file=summary_file,
		resume=bool(args.resume),
	)
	summary["validations"] = validation_records
	apply_validation_summaries(
		summary=summary,
		domains=domains,
		validation_records=validation_records,
	)
	summary["completed_at"] = datetime.now().isoformat(timespec="seconds")
	summary["success"] = bool(validation_records) and all(
		item.get("success") for item in validation_records
	) and all(
		bool(record.get("success")) for record in summary["domains"].values()
	)
	write_json(summary_file, summary)
	if args.suppress_final_summary_json:
		print(f"summary_file={summary_file}", flush=True)
	else:
		print(json.dumps(summary, indent=2, sort_keys=True))
	return 0 if summary["success"] else 1


def resolve_batch_root(batch_root: Path, batch_id: str) -> Path:
	"""Resolve an explicit or latest timestamped batch root."""

	root = batch_root.expanduser().resolve()
	if not root.exists():
		raise FileNotFoundError(f"Missing MOOSE ASL batch root: {root}")
	if batch_id == "latest":
		candidates = sorted(path for path in root.iterdir() if path.is_dir())
		if not candidates:
			raise FileNotFoundError(f"No timestamped batches found under {root}")
		return candidates[-1]
	resolved = root / batch_id
	if not resolved.exists():
		raise FileNotFoundError(f"Missing timestamped batch: {resolved}")
	return resolved


def prepare_domain_for_full_test(
	*,
	domain: str,
	batch_root: Path,
	run_root: Path,
	timeout_seconds: int,
	atomic_library_mode: str,
	write_domain_long_asl: bool,
	max_domain_long_asl_bytes: int,
	test_name_regex: str | None = None,
	compiler_variant: AtomicCompilerVariant | None = None,
) -> tuple[dict[str, Any], tuple[JasonTask, ...]]:
	"""Compile atomic ASL, append every test goal, and return Jason tasks."""

	domain_root = PROJECT_ROOT / "src" / "domains" / domain
	domain_file = domain_root / "domain.pddl"
	test_dir = domain_root / "test"
	readable_policy = batch_root / "run_logs" / domain / f"{domain}.model.readable"
	library_root = run_root / "domain_libraries"
	domain_output = library_root / domain
	log_dir = run_root / "logs" / domain
	record: dict[str, Any] = {
		"domain": domain,
		"domain_file": str(domain_file),
		"readable_policy_file": str(readable_policy),
		"plan_library_json": str(domain_output / "plan_library.json"),
		"plan_library_asl": str(domain_output / "plan_library.asl"),
		"atomic_library_mode": atomic_library_mode,
		"compiler_variant": compiler_variant.value if compiler_variant else None,
		"method": compiler_variant.display_name if compiler_variant else "Raw MOOSE",
		"success": False,
	}
	try:
		if not readable_policy.exists():
			raise FileNotFoundError(f"Missing readable MOOSE policy: {readable_policy}")
		if not domain_file.exists():
			raise FileNotFoundError(f"Missing domain file: {domain_file}")
		test_instances = tuple(sorted(test_dir.glob("*.pddl"), key=natural_sort_key))
		if test_name_regex:
			pattern = re.compile(test_name_regex)
			test_instances = tuple(
				path for path in test_instances if pattern.search(path.name)
			)
		if not test_instances:
			raise FileNotFoundError(f"No test PDDL instances found under {test_dir}")
		record["test_count"] = len(test_instances)
		record["first_test_file"] = str(test_instances[0])
		record["last_test_file"] = str(test_instances[-1])

		compile_result = run_logged_command(
			build_compile_atomic_library_command(
				readable_policy=readable_policy,
				domain_file=domain_file,
				domain=domain,
				library_root=library_root,
				atomic_library_mode=atomic_library_mode,
				compiler_variant=compiler_variant,
			),
			stdout_file=log_dir / "compile_atomic_library.stdout.json",
			stderr_file=log_dir / "compile_atomic_library.stderr.txt",
			timeout_seconds=timeout_seconds,
		)
		record["compile_atomic_library"] = compile_result.to_dict()
		if not compile_result.success:
			return record, ()

		plan_library_asl = domain_output / "plan_library.asl"
		plan_library_json = domain_output / "plan_library.json"
		atomic_plan_library = PlanLibrary.from_dict(
			json.loads(plan_library_json.read_text(encoding="utf-8")),
		)
		experiment_contract = dict(
			atomic_plan_library.metadata.get("experiment_contract") or {},
		)
		record["evidence_program_fingerprint"] = experiment_contract.get(
			"evidence_program_fingerprint",
		)
		base_plan_library_asl = domain_output / "atomic_plan_library.asl"
		shutil.copyfile(plan_library_asl, base_plan_library_asl)
		base_plan_library_asl_text = plan_library_asl.read_text(encoding="utf-8").rstrip()
		base_plan_library_sha256 = hashlib.sha256(
			base_plan_library_asl_text.encode("utf-8"),
		).hexdigest()
		atomic_plan_library_sha256 = _sha256_file(plan_library_json)
		wrapper_text_by_problem: dict[Path, str] = {}
		wrapper_plan_count: int | None = None
		if write_domain_long_asl:
			wrapper_text_by_problem, wrapper_plan_count = build_full_test_wrapper_texts(
				domain=domain,
				problem_files=test_instances,
				domain_file=domain_file,
				atomic_plan_library=atomic_plan_library,
			)
			append_record = append_guard_transition_full_test_wrappers(
				domain=domain,
				plan_library_asl=plan_library_asl,
				problem_files=test_instances,
				domain_file=domain_file,
				max_output_bytes=max_domain_long_asl_bytes,
				wrapper_text_by_problem=wrapper_text_by_problem,
				appended_plan_count=wrapper_plan_count,
			)
		else:
			append_record = {
				"success": True,
				"wrapper_mode": "dfa_guard_transition_replay",
				"transition_controller_strategy": (
					"balanced_transition_repair_tree"
				),
				"query_count": len(test_instances),
				"appended_plan_count": None,
				"domain_long_asl_written": False,
			}
		record["append_full_test_goals"] = append_record

		if not plan_library_asl.exists():
			raise FileNotFoundError(f"Missing ASL: {plan_library_asl}")
		record["appended_asl_line_count"] = len(
			plan_library_asl.read_text(encoding="utf-8").splitlines()
		)
		tasks = tuple(
			JasonTask(
				domain=domain,
				index=index,
				problem_file=problem_file,
				domain_file=domain_file,
				plan_library_asl=plan_library_asl,
				base_plan_library_asl_text=base_plan_library_asl_text,
				goal_name=f"g_{safe_goal_fragment(domain)}_test_{index}",
				output_dir=(
					run_root
					/ "jason"
					/ domain
					/ f"test_{index:04d}_{safe_path_fragment(problem_file.stem)}"
				),
				runtime_wrapper_text=wrapper_text_by_problem.get(problem_file),
				atomic_plan_library=atomic_plan_library,
				base_plan_library_sha256=base_plan_library_sha256,
				atomic_plan_library_sha256=atomic_plan_library_sha256,
			)
			for index, problem_file in enumerate(test_instances, start=1)
		)
		record["success"] = True
		return record, tasks
	except Exception as error:  # noqa: BLE001 - persisted for batch diagnosis.
		record["error"] = str(error)
		return record, ()


def build_compile_atomic_library_command(
	*,
	readable_policy: Path,
	domain_file: Path,
	domain: str,
	library_root: Path,
	atomic_library_mode: str,
	compiler_variant: AtomicCompilerVariant | str | None = None,
) -> tuple[str, ...]:
	"""Return the compile command used before full-test Jason validation."""

	atomic_library_mode = normalise_atomic_library_mode(atomic_library_mode)
	if atomic_library_mode not in ATOMIC_LIBRARY_MODES:
		raise ValueError(f"Unsupported atomic library mode: {atomic_library_mode}")
	command = [
		sys.executable,
		str(PROJECT_ROOT / "src" / "main.py"),
		"compile-moose-atomic-library",
		"--policy-file",
		str(readable_policy),
		"--domain-file",
		str(domain_file),
		"--domain-name",
		domain,
		"--library-root",
		str(library_root),
		"--overwrite",
	]
	if atomic_library_mode == "validated-policy-lifting":
		resolved_variant = (
			compiler_variant
			if isinstance(compiler_variant, AtomicCompilerVariant)
			else AtomicCompilerVariant(
				compiler_variant or AtomicCompilerVariant.FULL.value,
			)
		)
		command.extend(("--compiler-variant", resolved_variant.value))
	elif compiler_variant is not None:
		raise ValueError("compiler_variant requires validated-policy-lifting mode")
	return tuple(command)


def normalise_atomic_library_mode(mode: str) -> str:
	"""Return the configured atomic library mode."""

	return mode


def append_guard_transition_full_test_wrappers(
	*,
	domain: str,
	plan_library_asl: Path,
	problem_files: Sequence[Path],
	domain_file: Path | None = None,
	max_output_bytes: int,
	wrapper_text_by_problem: Mapping[Path, str] | None = None,
	appended_plan_count: int | None = None,
	atomic_plan_library: PlanLibrary | None = None,
) -> dict[str, Any]:
	"""Append one balanced guard-transition controller per test problem.

	This validation runner intentionally writes only ASL. It avoids the canonical
	``plan_library.json`` temporal metadata because full-test batches can contain
	hundreds of query wrappers and their DFA payloads are not needed by Jason.
	"""

	base_text = plan_library_asl.read_text(encoding="utf-8").rstrip()
	if wrapper_text_by_problem is None:
		wrapper_map, plan_count = build_full_test_wrapper_texts(
			domain=domain,
			problem_files=problem_files,
			domain_file=domain_file,
			atomic_plan_library=atomic_plan_library,
		)
	else:
		wrapper_map = dict(wrapper_text_by_problem)
		plan_count = (
			appended_plan_count
			if appended_plan_count is not None
			else len(tuple(problem_files))
		)
	line_count = len(base_text.splitlines()) + 5
	with plan_library_asl.open("w", encoding="utf-8") as output:
		output.write(base_text)
		output.write(
			"\n\n/* Full-test query-local guard-transition controllers.\n"
			"   Each PDDL conjunctive goal is treated as one DFA-style transition\n"
			"   guard. Its certified literal order is executed by a balanced repair\n"
			"   tree before the complete guard is rechecked. */\n\n",
		)
		for problem_file in problem_files:
			for line in wrapper_map[problem_file].splitlines():
				output.write(line)
				output.write("\n")
				line_count += 1
				if output.tell() > max_output_bytes:
					raise ValueError(
						"domain_long_asl_size_limit_exceeded: full-test "
						f"ASL for {domain!r} exceeded {max_output_bytes} bytes. "
						"Run without --write-domain-long-asl to validate per-test "
						"runtime ASL instead.",
					)
	return {
		"success": True,
		"wrapper_mode": "dfa_guard_transition_replay",
		"transition_controller_strategy": "balanced_transition_repair_tree",
		"query_count": len(problem_files),
		"appended_plan_count": plan_count,
		"line_count": line_count,
		"domain_long_asl_written": True,
	}


def build_full_test_wrapper_texts(
	*,
	domain: str,
	problem_files: Sequence[Path],
	domain_file: Path | None = None,
	atomic_plan_library: PlanLibrary | None = None,
) -> tuple[dict[Path, str], int]:
	"""Render each full-test query wrapper once, keyed by problem file."""

	wrapper_map: dict[Path, str] = {}
	total_plan_count = 0
	for index, problem_file in enumerate(problem_files, start=1):
		wrapper_lines, wrapper_plan_count = full_test_wrapper_lines(
			domain=domain,
			index=index,
			problem_file=problem_file,
			domain_file=domain_file,
			atomic_plan_library=atomic_plan_library,
		)
		wrapper_map[problem_file] = "\n".join(wrapper_lines).rstrip()
		total_plan_count += wrapper_plan_count
	return wrapper_map, total_plan_count


def full_test_wrapper_lines(
	*,
	domain: str,
	index: int,
	problem_file: Path,
	problem: Any | None = None,
	domain_file: Path | None = None,
	atomic_plan_library: PlanLibrary | None = None,
) -> tuple[tuple[str, ...], int]:
	"""Return the query-local guard-transition replay wrapper for a test problem."""

	problem = problem if problem is not None else PDDLParser.parse_problem(problem_file)
	goal_facts = tuple(fact for fact in problem.goal_facts if fact.is_positive)
	if len(goal_facts) != len(problem.goal_facts):
		raise ValueError(
			f"{problem_file} contains negative goal literals; full-test Jason "
			"validation only appends positive atomic progress goals.",
		)
	numeric_goal_conditions = tuple(problem.numeric_goal_conditions or ())
	if not goal_facts and not numeric_goal_conditions:
		raise ValueError(f"{problem_file} contains no supported PDDL goal steps.")
	for condition in numeric_goal_conditions:
		if condition.comparator != "=":
			raise ValueError(
				"unsupported numeric goal comparator: only equality can compile to an "
				"atomic numeric resource achievement.",
			)
	return guard_transition_replay_wrapper_lines(
		domain=domain,
		index=index,
		problem_file=problem_file,
		problem=problem,
		domain_file=domain_file,
		atomic_plan_library=atomic_plan_library,
	)


def guard_transition_replay_wrapper_lines(
	*,
	domain: str,
	index: int,
	problem_file: Path,
	problem: Any | None = None,
	domain_file: Path | None = None,
	atomic_plan_library: PlanLibrary | None = None,
) -> tuple[tuple[str, ...], int]:
	"""Return one conjunctive guard-transition replay wrapper."""

	problem = problem if problem is not None else PDDLParser.parse_problem(problem_file)
	goal_facts = tuple(fact for fact in problem.goal_facts if fact.is_positive)
	if len(goal_facts) != len(problem.goal_facts):
		raise ValueError(
			f"{problem_file} contains negative goal literals; full-test Jason "
			"validation only appends positive atomic progress goals.",
		)
	numeric_goal_conditions = tuple(problem.numeric_goal_conditions or ())
	if not goal_facts and not numeric_goal_conditions:
		raise ValueError(f"{problem_file} contains no supported PDDL goal steps.")
	goal_name = f"g_{safe_goal_fragment(domain)}_test_{index}"
	entry_proposition = query_entry_proposition(goal_name)
	ordered_goal_facts = goal_facts
	preservation_alias_plans = ()
	preservation_helper_by_predicate: Mapping[str, str] = {}
	serialization_certificate: Mapping[str, object] = {
		"certificate_kind": "singleton_transition_identity_serialization",
		"ordered_literal_indexes": list(range(len(goal_facts))),
		"threat_edges": [],
		"module_summaries_complete": True,
	}
	if len(goal_facts) + len(numeric_goal_conditions) > 1:
		if numeric_goal_conditions:
			raise ValueError(
				"uncertified_numeric_conjunctive_transition: full-test wrappers require "
				"numeric effect-preservation witnesses for mixed or multiple goals.",
			)
		if domain_file is None or atomic_plan_library is None:
			raise ValueError(
				"uncertified_conjunctive_transition: domain PDDL and the selected atomic "
				"plan library are required for threat-safe serialization.",
			)
		literal_signatures = tuple(
			(fact.predicate, tuple(fact.args)) for fact in goal_facts
		)
		domain_model = PDDLParser.parse_domain(domain_file)
		try:
			ordered_indexes, certificate = threat_safe_positive_literal_order(
				literal_signatures,
				plan_library=atomic_plan_library,
				domain=domain_model,
				object_types=problem.object_types,
			)
			serialization_certificate = certificate.to_dict()
		except ValueError as error:
			if not str(error).startswith("cyclic_conjunctive_transition_not_certified"):
				raise
			selection = preservation_safe_plan_selection(
				literal_signatures,
				plan_library=atomic_plan_library,
				domain=domain_model,
				object_types=problem.object_types,
			)
			if selection is None:
				raise
			ordered_indexes = selection.ordered_indexes
			serialization_certificate = selection.certificate.to_dict()
			(
				preservation_alias_plans,
				preservation_helper_by_predicate,
			) = query_local_preservation_alias_plans(
				selection,
				helper_prefix=f"{goal_name}_trans_1",
			)
		ordered_goal_facts = tuple(goal_facts[index] for index in ordered_indexes)
	atoms = _deduplicate_strings(
		(
			*(render_fact_atom(fact) for fact in ordered_goal_facts),
			*(
				atom
				for condition in numeric_goal_conditions
				for atom in render_numeric_goal_atoms(
					condition,
					problem=problem,
					problem_file=problem_file,
				)
			),
		),
	)
	transition_name = f"{goal_name}_trans_1"
	lines: list[str] = [
		f"/* full_test_problem={problem_file.name} */",
		f"{entry_proposition}.",
		"",
	]
	if preservation_alias_plans:
		alias_text = render_plan_library_asl(
			PlanLibrary(domain_name=domain, plans=tuple(preservation_alias_plans)),
		)
		lines.extend(("/* query-local preservation-safe atomic branches */", alias_text, ""))
	lines.extend(
		(
			f"/* plan={goal_name}_trans_sequence | source_instruction_ids=none */",
			f"+!{goal_name} : {entry_proposition} <-",
			f"\t!{transition_name}.",
			"",
		),
	)
	goal_fact_by_atom = {
		render_fact_atom(fact): fact for fact in ordered_goal_facts
	}
	repair_literals: list[TransitionRepairLiteral] = []
	for atom in atoms:
		fact = goal_fact_by_atom.get(atom)
		predicate, arguments = _split_rendered_atom(atom)
		repair_literals.append(
			TransitionRepairLiteral(
				atom=atom,
				achievement_symbol=(
					preservation_helper_by_predicate.get(fact.predicate, fact.predicate)
					if fact is not None
					else predicate
				),
				achievement_arguments=(tuple(fact.args) if fact is not None else arguments),
			),
		)
	tree_compilation = compile_transition_repair_tree(
		transition_symbol=transition_name,
		shared_context=(entry_proposition,),
		positive_literals=tuple(repair_literals),
		completion_context=(entry_proposition, *atoms),
		certificate={
			"query_entry_proposition": entry_proposition,
			"transition_index": 1,
			"serialization_certificate": dict(serialization_certificate),
		},
	)
	lines.extend(
		(
			*_render_plan_block(domain=domain, plans=tree_compilation.plans).splitlines(),
			"",
		),
	)
	return tuple(lines), 1 + len(preservation_alias_plans) + len(tree_compilation.plans)


def _deduplicate_strings(values: Sequence[str]) -> tuple[str, ...]:
	return tuple(dict.fromkeys(str(value) for value in tuple(values or ())))


def _split_rendered_atom(atom: str) -> tuple[str, tuple[str, ...]]:
	text = str(atom or "").strip()
	match = re.fullmatch(r"([a-z][a-z0-9_]*)\((.*)\)", text)
	if match is None:
		if re.fullmatch(r"[a-z][a-z0-9_]*", text):
			return text, ()
		raise ValueError(f"unsupported rendered transition atom: {atom!r}")
	arguments = tuple(
		argument.strip()
		for argument in match.group(2).split(",")
		if argument.strip()
	)
	return match.group(1), arguments


def _render_plan_block(*, domain: str, plans: Sequence[Any]) -> str:
	rendered_lines = render_plan_library_asl(
		PlanLibrary(domain_name=domain, plans=tuple(plans)),
	).splitlines()
	return "\n".join(rendered_lines[3:]).rstrip()


def render_runtime_asl_for_task(task: JasonTask, *, problem: Any | None = None) -> str:
	"""Render the per-test ASL with the same wrapper shape as the long library."""

	if task.runtime_wrapper_text is None:
		wrapper_lines, _ = full_test_wrapper_lines(
			domain=task.domain,
			index=task.index,
			problem_file=task.problem_file,
			problem=problem,
			domain_file=task.domain_file,
			atomic_plan_library=task.atomic_plan_library,
		)
		wrapper_text = "\n".join(wrapper_lines).rstrip()
	else:
		wrapper_text = task.runtime_wrapper_text.rstrip()
	return task.base_plan_library_asl_text + "\n\n" + wrapper_text + "\n"


def materialize_runtime_asl_for_task(task: JasonTask) -> Path:
	"""Write a per-test ASL file with the same wrapper shape as the long library."""

	runtime_asl = task.output_dir / "plan_library.asl"
	runtime_asl.write_text(render_runtime_asl_for_task(task), encoding="utf-8")
	return runtime_asl


def render_fact_atom(fact: PDDLFact) -> str:
	"""Render a grounded PDDL fact as the AgentSpeak atom used by the ASL renderer."""

	predicate = sanitize_identifier(fact.predicate)
	arguments = tuple(sanitize_identifier(argument) for argument in fact.args)
	if not arguments:
		return predicate
	return f"{predicate}({', '.join(arguments)})"


def render_numeric_goal_atom(condition: PDDLNumericCondition, *, problem_file: Path) -> str:
	"""Render a bounded numeric equality goal as an AgentSpeak atomic subgoal."""

	return render_numeric_goal_atoms(
		condition,
		problem=None,
		problem_file=problem_file,
	)[0]


def render_numeric_goal_atoms(
	condition: PDDLNumericCondition,
	*,
	problem: Any | None,
	problem_file: Path,
) -> tuple[str, ...]:
	"""Render bounded numeric equality as one or more atomic progress calls."""

	if condition.comparator != "=":
		raise ValueError(
			f"{problem_file} contains unsupported numeric goal comparator "
			f"{condition.comparator!r}; only equality is in the bounded resource fragment.",
		)
	fluent, target = _numeric_goal_fluent_and_target(condition.left, condition.right)
	if fluent is None or target is None:
		fluent, target = _numeric_goal_fluent_and_target(condition.right, condition.left)
	if fluent is None or target is None:
		raise ValueError(
			f"{problem_file} contains unsupported numeric goal "
			f"{condition.to_signature()!r}; expected one numeric fluent and one "
			"integer target constant.",
		)
	arguments = tuple(str(argument) for argument in tuple(fluent.args or ()))
	atom = _render_call(
		fluent.function,
		(*arguments, str(target)),
		raw_argument_indexes={len(arguments)},
	)
	repeat_count = _numeric_goal_repeat_count(
		fluent=fluent,
		target=target,
		problem=problem,
	)
	return tuple(atom for _ in range(repeat_count))


def _numeric_goal_fluent_and_target(
	left: PDDLNumericExpression,
	right: PDDLNumericExpression,
) -> tuple[PDDLNumericFluent | None, int | None]:
	if left.kind != "fluent" or right.kind != "constant":
		return None, None
	if not re.fullmatch(r"[+-]?\d+", str(right.value)):
		return None, None
	return (
		PDDLNumericFluent(
			function=str(left.value),
			args=[str(argument) for argument in tuple(left.args or ())],
		),
		int(str(right.value)),
	)


def _numeric_goal_repeat_count(
	*,
	fluent: PDDLNumericFluent,
	target: int,
	problem: Any | None,
) -> int:
	if problem is None:
		return 1
	initial = _numeric_initial_value(
		fluent=fluent,
		assignments=tuple(getattr(problem, "numeric_init", ()) or ()),
	)
	if initial is None:
		return 1
	return max(1, abs(initial - target))


def _numeric_initial_value(
	*,
	fluent: PDDLNumericFluent,
	assignments: Sequence[PDDLNumericAssignment],
) -> int | None:
	expected = (
		str(fluent.function).strip().lower(),
		tuple(str(argument).strip().lower() for argument in tuple(fluent.args or ())),
	)
	for assignment in assignments:
		candidate = (
			str(assignment.fluent.function).strip().lower(),
			tuple(
				str(argument).strip().lower()
				for argument in tuple(assignment.fluent.args or ())
			),
		)
		if candidate == expected:
			return int(assignment.value)
	return None


def _render_call(
	predicate: str,
	arguments: Sequence[str],
	*,
	raw_argument_indexes: set[int] | None = None,
) -> str:
	rendered_predicate = sanitize_identifier(predicate)
	raw_indexes = raw_argument_indexes or set()
	rendered_arguments = tuple(
		_render_call_argument(index=index, argument=argument, raw_indexes=raw_indexes)
		for index, argument in enumerate(arguments)
	)
	if not rendered_arguments:
		return rendered_predicate
	return f"{rendered_predicate}({', '.join(rendered_arguments)})"


def _render_call_argument(*, index: int, argument: str, raw_indexes: set[int]) -> str:
	if index in raw_indexes:
		return str(argument)
	if _is_wrapper_variable(argument):
		return argument
	return sanitize_identifier(argument)


def _is_wrapper_variable(value: str) -> bool:
	return bool(re.fullmatch(r"[A-Z][A-Za-z0-9_]*", str(value or "")))


def query_entry_proposition(goal_name: str) -> str:
	"""Return the zero-arity belief that enables one appended query wrapper."""

	text = safe_goal_fragment(goal_name)
	if text.startswith("g_") and len(text) > 2:
		return text[2:]
	return f"{text}_entry"


def run_jason_tasks(
	*,
	tasks: Sequence[JasonTask],
	classpath: str,
	run_root: Path,
	num_workers: int,
	timeout_seconds: int,
	jason_java_stack_size: str,
	plan_verifier_command: str | None,
	require_plan_verifier: bool,
	plan_verifier_timeout_seconds: int,
	write_per_test_runtime_asl: bool,
	summary: dict[str, Any],
	summary_file: Path,
	resume: bool = False,
	input_recovery_timeout_seconds: float = 900.0,
) -> list[dict[str, Any]]:
	"""Run Jason validation tasks in a bounded worker pool."""

	if tasks:
		all_tasks = snapshot_jason_task_inputs(
			tasks,
			run_root=run_root,
			recovery_timeout_seconds=input_recovery_timeout_seconds,
		)
		input_snapshot_manifest = run_root / "input_snapshot" / "manifest.json"
		summary["input_snapshot"] = {
			"success": True,
			"manifest_file": str(input_snapshot_manifest),
			"manifest_sha256": _sha256_file(input_snapshot_manifest),
			"task_count": len(all_tasks),
		}
	else:
		all_tasks = ()
		summary["input_snapshot"] = {
			"success": True,
			"manifest_file": None,
			"manifest_sha256": None,
			"task_count": 0,
		}
	completed = load_completed_validation_records(all_tasks) if resume else {}
	pending = tuple(
		task for task in all_tasks if (task.domain, task.index) not in completed
	)
	if resume:
		print(
			f"[resume] reused={len(completed)} pending={len(pending)}",
			flush=True,
		)
	compiled_environment_dirs = prepare_shared_jason_environments(
		tasks=pending,
		classpath=classpath,
		run_root=run_root,
		timeout_seconds=timeout_seconds,
		summary=summary,
		summary_file=summary_file,
	)
	results_jsonl = run_root / "validation_results.jsonl"
	summary["validation_results_jsonl"] = str(results_jsonl)
	summary["resumed_validation_count"] = len(completed)
	records: list[dict[str, Any]] = list(completed.values())
	with ThreadPoolExecutor(max_workers=num_workers) as executor:
		future_map = {
			executor.submit(
				validate_one_task,
				task,
				classpath=classpath,
				compiled_environment_dirs=compiled_environment_dirs,
				timeout_seconds=timeout_seconds,
				jason_java_stack_size=jason_java_stack_size,
				plan_verifier_command=plan_verifier_command,
				require_plan_verifier=require_plan_verifier,
				plan_verifier_timeout_seconds=plan_verifier_timeout_seconds,
				write_per_test_runtime_asl=write_per_test_runtime_asl,
			): task
			for task in pending
		}
		for future in as_completed(future_map):
			task = future_map[future]
			try:
				record = future.result()
			except Exception as error:  # noqa: BLE001 - isolate worker failures.
				record = validation_worker_exception_record(task, error)
			records.append(record)
			append_jsonl(results_jsonl, record)
			status = "ok" if record.get("success") else "fail"
			jason_status = _jason_runtime_status_label(record)
			verifier_status = _plan_verifier_status_label(record)
			print(
				f"[{status}] {record['domain']} test={record['test_index']} "
				f"goal={record['goal_name']} jason={jason_status} "
				f"val={verifier_status} actions={record.get('action_count')} "
				f"status={record.get('status')}",
				flush=True,
			)
	ordered_records = sorted(
		records,
		key=lambda item: (str(item["domain"]), int(item["test_index"])),
	)
	results_jsonl.write_text(
		"".join(json.dumps(record, sort_keys=True) + "\n" for record in ordered_records),
		encoding="utf-8",
	)
	return ordered_records


def _jason_runtime_status_label(record: Mapping[str, Any]) -> str:
	"""Return whether Jason produced a complete candidate action trace."""

	status = str(record.get("status") or "")
	if status in {
		"success",
		"plan_verifier_failed",
		"plan_verifier_timeout",
		"plan_verifier_unavailable",
	}:
		return "ok"
	if bool(record.get("timed_out")):
		return "timeout"
	return "fail"


def _plan_verifier_status_label(record: Mapping[str, Any]) -> str:
	"""Return whether VAL or the configured IPC verifier accepted the trace."""

	if record.get("plan_verifier_success") is True:
		return "ok"
	if record.get("plan_verifier_attempted") is not True:
		return "not_attempted"
	status = str(record.get("status") or "")
	if "timeout" in status:
		return "timeout"
	return "fail"


def validate_one_task(
	task: JasonTask,
	*,
	classpath: str,
	compiled_environment_dirs: Mapping[str, Path],
	timeout_seconds: int,
	jason_java_stack_size: str,
	plan_verifier_command: str | None,
	require_plan_verifier: bool,
	plan_verifier_timeout_seconds: int,
	write_per_test_runtime_asl: bool,
) -> dict[str, Any]:
	"""Run one Jason validation and return a compact record."""

	start = time.perf_counter()
	input_fingerprint: str | None = None
	task.output_dir.mkdir(parents=True, exist_ok=True)
	try:
		input_fingerprint = validation_input_fingerprint(task)
		runtime_artifacts = build_runtime_problem_artifacts(
			domain_file=task.domain_file,
			problem_file=task.problem_file,
		)
		runtime_asl_text = render_runtime_asl_for_task(
			task,
			problem=runtime_artifacts.problem,
		)
		runtime_asl = task.output_dir / "plan_library.asl"
		if write_per_test_runtime_asl:
			runtime_asl.write_text(runtime_asl_text, encoding="utf-8")
		result = JasonPlanLibraryRunner(
			timeout_seconds=timeout_seconds,
			jason_classpath=classpath,
			compiled_environment_dir=compiled_environment_dirs.get(
				str(task.domain_file.resolve()),
			),
			jason_java_stack_size=jason_java_stack_size,
			plan_verifier_command=plan_verifier_command,
			require_plan_verifier=require_plan_verifier,
			plan_verifier_timeout_seconds=plan_verifier_timeout_seconds,
		).validate(
			domain_file=task.domain_file,
			problem_file=task.problem_file,
			plan_library_asl=runtime_asl if write_per_test_runtime_asl else task.plan_library_asl,
			goal_name=task.goal_name,
			output_dir=task.output_dir,
			plan_library_asl_text=runtime_asl_text,
			runtime_artifacts=runtime_artifacts,
		)
		payload = result.to_dict()
		plan_verifier = dict(payload.get("plan_verifier") or {})
		artifacts = dict(payload.get("artifacts") or {})
		committed_trace_path = Path(str(artifacts.get("committed_plan_trace") or ""))
		raw_trace_path = Path(str(artifacts.get("plan_trace") or ""))
		count_trace_path = (
			committed_trace_path if committed_trace_path.exists() else raw_trace_path
		)
		action_count_fields = reported_action_count_fields(
			payload=payload,
			plan_trace_path=count_trace_path,
		)
		record = {
			"domain": task.domain,
			"test_index": task.index,
			"problem_file": str(task.source_problem_file or task.problem_file),
			"snapshot_problem_file": str(task.problem_file),
			"goal_name": task.goal_name,
			"input_fingerprint": input_fingerprint,
			"success": bool(payload.get("success")),
			"status": payload.get("status"),
			"timed_out": bool(payload.get("timed_out")),
			"exit_code": payload.get("exit_code"),
			**action_count_fields,
			"plan_verifier_success": plan_verifier.get("success"),
			"plan_verifier_attempted": plan_verifier.get("attempted"),
			"plan_verifier_available": plan_verifier.get("available"),
			"plan_trace": artifacts.get("plan_trace"),
			"committed_plan_trace": artifacts.get("committed_plan_trace"),
			"plan_verifier_stdout": artifacts.get("plan_verifier_stdout"),
			"plan_verifier_stderr": artifacts.get("plan_verifier_stderr"),
			"output_dir": str(task.output_dir),
			"runtime_plan_library_asl": (
				str(runtime_asl) if write_per_test_runtime_asl else None
			),
			"runtime_plan_library_embedded_in_agentspeak": (
				not write_per_test_runtime_asl
			),
			"domain_full_plan_library_asl": str(task.plan_library_asl),
			"error": payload.get("error"),
			"duration_seconds": time.perf_counter() - start,
		}
	except Exception as error:  # noqa: BLE001 - persisted for full-test diagnosis.
		status = (
			"input_infrastructure_error"
			if isinstance(error, OSError)
			else "exception"
		)
		record = {
			"domain": task.domain,
			"test_index": task.index,
			"problem_file": str(task.source_problem_file or task.problem_file),
			"snapshot_problem_file": str(task.problem_file),
			"goal_name": task.goal_name,
			"input_fingerprint": input_fingerprint,
			"success": False,
			"status": status,
			"timed_out": False,
			"exit_code": None,
			"action_count": None,
			"observed_action_prefix_count": 0,
			"plan_trace_action_count": 0,
			"action_count_complete": False,
			"action_count_source": "exception",
			"output_dir": str(task.output_dir),
			"error": str(error),
			"duration_seconds": time.perf_counter() - start,
		}
	(task.output_dir / "validation_record.json").write_text(
		json.dumps(record, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)
	return record


def validation_worker_exception_record(
	task: JasonTask,
	error: Exception,
) -> dict[str, Any]:
	"""Persist an unexpected worker failure without aborting sibling cases."""

	try:
		input_fingerprint: str | None = validation_input_fingerprint(task)
	except Exception:  # noqa: BLE001 - recovery records must not rethrow.
		input_fingerprint = None
	status = (
		"input_infrastructure_error"
		if isinstance(error, OSError)
		else "worker_infrastructure_error"
	)
	record = {
		"domain": task.domain,
		"test_index": task.index,
		"problem_file": str(task.source_problem_file or task.problem_file),
		"snapshot_problem_file": str(task.problem_file),
		"goal_name": task.goal_name,
		"input_fingerprint": input_fingerprint,
		"success": False,
		"status": status,
		"timed_out": False,
		"exit_code": None,
		"action_count": None,
		"observed_action_prefix_count": 0,
		"plan_trace_action_count": 0,
		"action_count_complete": False,
		"action_count_source": "worker_exception",
		"output_dir": str(task.output_dir),
		"error": str(error),
		"duration_seconds": 0.0,
	}
	task.output_dir.mkdir(parents=True, exist_ok=True)
	(task.output_dir / "validation_record.json").write_text(
		json.dumps(record, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)
	return record


def apply_validation_summaries(
	*,
	summary: dict[str, Any],
	domains: Sequence[str],
	validation_records: Sequence[Mapping[str, Any]],
) -> None:
	"""Update domain records with validation outcomes, not just prepare-stage success."""

	for domain in domains:
		domain_items = [item for item in validation_records if item.get("domain") == domain]
		record = summary.get("domains", {}).get(domain)
		if record is None or not domain_items:
			continue
		success_count = sum(1 for item in domain_items if item.get("success"))
		failure_count = sum(1 for item in domain_items if not item.get("success"))
		record["jason_validation"] = {
			"test_count": len(domain_items),
			"success_count": success_count,
			"failure_count": failure_count,
			"plan_verifier_success_count": sum(
				1 for item in domain_items if item.get("plan_verifier_success") is True
			),
			"plan_verifier_attempted_count": sum(
				1 for item in domain_items if item.get("plan_verifier_attempted") is True
			),
		}
		record["validation_success"] = failure_count == 0 and success_count == len(domain_items)
		record["success"] = bool(record.get("success")) and bool(record["validation_success"])


def reported_action_count_fields(
	*,
	payload: Mapping[str, Any],
	plan_trace_path: Path,
) -> dict[str, Any]:
	"""Return action-count fields without pretending prefix-only stdout is complete."""

	observed_prefix_count = int(
		payload.get("action_count") or len(tuple(payload.get("action_path") or ())),
	)
	plan_trace_count = _count_plan_trace_actions(plan_trace_path)
	has_execute_success = bool(
		dict(payload.get("output_summary") or {}).get("has_execute_success"),
	)
	if plan_trace_count > 0 and has_execute_success:
		return {
			"action_count": plan_trace_count,
			"observed_action_prefix_count": observed_prefix_count,
			"plan_trace_action_count": plan_trace_count,
			"action_count_complete": True,
			"action_count_source": "plan_trace",
		}
	if bool(payload.get("timed_out")) or not has_execute_success:
		return {
			"action_count": None,
			"observed_action_prefix_count": observed_prefix_count,
			"plan_trace_action_count": plan_trace_count,
			"action_count_complete": False,
			"action_count_source": "unknown_timeout"
			if bool(payload.get("timed_out"))
			else "unknown_incomplete_execution",
		}
	return {
		"action_count": observed_prefix_count,
		"observed_action_prefix_count": observed_prefix_count,
		"plan_trace_action_count": plan_trace_count,
		"action_count_complete": True,
		"action_count_source": "runtime_summary",
	}


def _count_plan_trace_actions(path: Path) -> int:
	try:
		if not path or not path.exists():
			return 0
		with path.open("r", encoding="utf-8") as handle:
			return sum(1 for line in handle if line.strip() and not line.lstrip().startswith(";"))
	except OSError:
		return 0


def prepare_shared_jason_environments(
	*,
	tasks: Sequence[JasonTask],
	classpath: str,
	run_root: Path,
	timeout_seconds: int,
	summary: dict[str, Any],
	summary_file: Path,
) -> dict[str, Path]:
	"""Compile one reusable Jason Java environment per PDDL domain."""

	compiled_dirs: dict[str, Path] = {}
	records: dict[str, dict[str, Any]] = {}
	javac_bin = shutil.which("javac")
	if not javac_bin:
		summary["shared_jason_environments"] = {
			"success": False,
			"error": "javac not found; falling back to per-task compilation",
		}
		write_json(summary_file, summary)
		return compiled_dirs

	domain_tasks = {
		str(task.domain_file.resolve()): task
		for task in sorted(tasks, key=lambda item: (item.domain, str(item.domain_file)))
	}
	for domain_file_text, task in domain_tasks.items():
		start = time.perf_counter()
		env_dir = run_root / "shared_jason_environments" / safe_path_fragment(task.domain)
		stdout_file = env_dir / "javac.stdout.txt"
		stderr_file = env_dir / "javac.stderr.txt"
		record: dict[str, Any] = {
			"domain": task.domain,
			"domain_file": domain_file_text,
			"environment_dir": str(env_dir),
			"success": False,
		}
		try:
			env_dir.mkdir(parents=True, exist_ok=True)
			domain_model = PDDLParser.parse_domain(task.domain_file)
			action_schemas = tuple(
				_runtime_action_schema(action)
				for action in tuple(domain_model.actions or ())
			)
			environment_java = _build_environment_java_source(
				class_name=JasonPlanLibraryRunner.environment_class_name,
				action_schemas=action_schemas,
				seed_facts_file_name="initial_facts.txt",
			)
			environment_java_path = (
				env_dir / f"{JasonPlanLibraryRunner.environment_class_name}.java"
			)
			belief_base_java_path = env_dir / "JasonPipelineIndexedBeliefBase.java"
			environment_java_path.write_text(environment_java, encoding="utf-8")
			belief_base_java_path.write_text(
				_build_indexed_belief_base_java_source(),
				encoding="utf-8",
			)
			with stdout_file.open("w", encoding="utf-8") as stdout_handle:
				with stderr_file.open("w", encoding="utf-8") as stderr_handle:
					completed = subprocess.run(
						[
							javac_bin,
							"-cp",
							classpath,
							environment_java_path.name,
							belief_base_java_path.name,
						],
						cwd=env_dir,
						stdout=stdout_handle,
						stderr=stderr_handle,
						check=False,
						timeout=max(30, min(int(timeout_seconds), 120)),
					)
			record.update(
				{
					"exit_code": completed.returncode,
					"stdout_file": str(stdout_file),
					"stderr_file": str(stderr_file),
					"duration_seconds": time.perf_counter() - start,
					"success": completed.returncode == 0,
				},
			)
			if completed.returncode == 0:
				compiled_dirs[domain_file_text] = env_dir
		except Exception as error:  # noqa: BLE001 - fallback preserves old behavior.
			record.update(
				{
					"error": str(error),
					"duration_seconds": time.perf_counter() - start,
					"fallback": "per_task_javac",
				},
			)
		records[task.domain] = record
		summary["shared_jason_environments"] = records
		write_json(summary_file, summary)
	return compiled_dirs


def run_logged_command(
	command: Sequence[str],
	*,
	stdout_file: Path,
	stderr_file: Path,
	timeout_seconds: int,
) -> ShellCommandResult:
	"""Run one local command and persist stdout/stderr."""

	stdout_file.parent.mkdir(parents=True, exist_ok=True)
	stderr_file.parent.mkdir(parents=True, exist_ok=True)
	start = time.perf_counter()
	timed_out = False
	exit_code: int | None = None
	with stdout_file.open("w", encoding="utf-8") as stdout_handle:
		with stderr_file.open("w", encoding="utf-8") as stderr_handle:
			try:
				completed = subprocess.run(
					tuple(str(item) for item in command),
					cwd=PROJECT_ROOT,
					stdout=stdout_handle,
					stderr=stderr_handle,
					check=False,
					timeout=timeout_seconds,
				)
				exit_code = completed.returncode
			except subprocess.TimeoutExpired:
				timed_out = True
	return ShellCommandResult(
		command=tuple(str(item) for item in command),
		stdout_file=str(stdout_file),
		stderr_file=str(stderr_file),
		exit_code=exit_code,
		duration_seconds=time.perf_counter() - start,
		timed_out=timed_out,
	)


def resolve_jason_classpath_once() -> str:
	"""Resolve Jason classpath once so full-test workers do not rerun Maven."""

	return _resolve_jason_classpath(JasonPlanLibraryRunner.default_jason_maven_artifact)


def write_json(path: Path, payload: Any) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	with path.open("a", encoding="utf-8") as handle:
		handle.write(json.dumps(payload, sort_keys=True))
		handle.write("\n")


def safe_goal_fragment(value: str) -> str:
	text = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "").strip().lower()).strip("_")
	if not text:
		return "domain"
	if text[0].isdigit():
		return f"d_{text}"
	return text


def safe_path_fragment(value: str) -> str:
	text = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "").strip()).strip("_")
	return text or "problem"


if __name__ == "__main__":
	raise SystemExit(main())
