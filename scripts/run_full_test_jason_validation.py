#!/usr/bin/env python3
"""Append every test goal from a MOOSE ASL batch and validate it in Jason."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from dataclasses import dataclass
from datetime import datetime
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
ATOMIC_LIBRARY_MODES = ("faithful", "post-moose-recursive")

if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from evaluation.jason_runtime import JasonPlanLibraryRunner  # noqa: E402
from evaluation.jason_runtime.runner import _build_environment_java_source  # noqa: E402
from evaluation.jason_runtime.runner import _resolve_jason_classpath  # noqa: E402
from evaluation.jason_runtime.runner import _runtime_action_schema  # noqa: E402
from scripts.run_moose_faithful_e2e import DEFAULT_DOMAINS  # noqa: E402
from scripts.run_moose_faithful_e2e import natural_sort_key  # noqa: E402
from plan_library.rendering import sanitize_identifier  # noqa: E402
from utils.pddl_parser import PDDLFact  # noqa: E402
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
	base_plan_library_asl: Path
	goal_name: str
	output_dir: Path


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
		help="Root for full-test Jason validation artifacts.",
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
	parser.add_argument("--timeout-seconds", type=int, default=90)
	parser.add_argument(
		"--atomic-library-mode",
		choices=ATOMIC_LIBRARY_MODES,
		default="post-moose-recursive",
		help=(
			"Compile raw MOOSE decision-list macros faithfully, or synthesize "
			"post-MOOSE recursive atomic modules before Jason validation. Defaults "
			"to the current post-MOOSE recursive architecture."
		),
	)
	parser.add_argument(
		"--write-domain-long-asl",
		action="store_true",
		help=(
			"Also write one full-test ASL per domain. Disabled by default because "
			"large validation suites can still produce bulky ASL artifacts."
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
	args = parser.parse_args()

	domains = tuple(args.domain or DEFAULT_DOMAINS)
	batch_root = resolve_batch_root(args.batch_root, args.batch_id)
	batch_id = batch_root.name
	run_id = args.run_id or f"{batch_id}-full-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
	run_root = args.output_root.expanduser().resolve() / run_id
	if run_root.exists():
		print(f"output directory already exists: {run_root}", file=sys.stderr)
		return 2
	run_root.mkdir(parents=True)

	summary: dict[str, Any] = {
		"artifact_kind": "full_test_jason_validation_from_moose_asl_batch",
		"created_at": datetime.now().isoformat(timespec="seconds"),
		"source_batch_id": batch_id,
		"source_batch_root": str(batch_root),
		"run_id": run_id,
		"run_root": str(run_root),
		"settings": {
			"domains": list(domains),
			"num_workers": args.num_workers,
			"timeout_seconds": args.timeout_seconds,
			"atomic_library_mode": args.atomic_library_mode,
			"prepare_only": bool(args.prepare_only),
			"write_domain_long_asl": bool(args.write_domain_long_asl),
			"max_domain_long_asl_mb": args.max_domain_long_asl_mb,
		},
		"domains": {},
		"validations": [],
	}
	summary_file = run_root / "summary.json"
	write_json(summary_file, summary)

	tasks: list[JasonTask] = []
	for domain in domains:
		record, domain_tasks = prepare_domain_for_full_test(
			domain=domain,
			batch_root=batch_root,
			run_root=run_root,
			timeout_seconds=args.timeout_seconds,
			atomic_library_mode=args.atomic_library_mode,
			write_domain_long_asl=bool(args.write_domain_long_asl),
			max_domain_long_asl_bytes=max(1, int(args.max_domain_long_asl_mb)) * 1024 * 1024,
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
		print(json.dumps(summary, indent=2, sort_keys=True))
		return 0 if summary["success"] else 1

	classpath = resolve_jason_classpath_once()
	validation_records = run_jason_tasks(
		tasks=tuple(tasks),
		classpath=classpath,
		run_root=run_root,
		num_workers=max(1, int(args.num_workers)),
		timeout_seconds=max(1, int(args.timeout_seconds)),
		summary=summary,
		summary_file=summary_file,
	)
	summary["validations"] = validation_records
	for domain in domains:
		domain_items = [item for item in validation_records if item["domain"] == domain]
		if not domain_items:
			continue
		summary["domains"][domain]["jason_validation"] = {
			"test_count": len(domain_items),
			"success_count": sum(1 for item in domain_items if item.get("success")),
			"failure_count": sum(1 for item in domain_items if not item.get("success")),
		}
	summary["completed_at"] = datetime.now().isoformat(timespec="seconds")
	summary["success"] = all(item.get("success") for item in validation_records) and all(
		bool(record.get("success")) for record in summary["domains"].values()
	)
	write_json(summary_file, summary)
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
		"plan_library_asl": str(domain_output / "plan_library.asl"),
		"atomic_library_mode": atomic_library_mode,
		"success": False,
	}
	try:
		if not readable_policy.exists():
			raise FileNotFoundError(f"Missing readable MOOSE policy: {readable_policy}")
		if not domain_file.exists():
			raise FileNotFoundError(f"Missing domain file: {domain_file}")
		test_instances = tuple(sorted(test_dir.glob("*.pddl"), key=natural_sort_key))
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
			),
			stdout_file=log_dir / "compile_atomic_library.stdout.json",
			stderr_file=log_dir / "compile_atomic_library.stderr.txt",
			timeout_seconds=timeout_seconds,
		)
		record["compile_atomic_library"] = compile_result.to_dict()
		if not compile_result.success:
			return record, ()

		plan_library_asl = domain_output / "plan_library.asl"
		base_plan_library_asl = domain_output / "atomic_plan_library.asl"
		shutil.copyfile(plan_library_asl, base_plan_library_asl)
		if write_domain_long_asl:
			append_record = append_state_monitor_full_test_wrappers(
				domain=domain,
				plan_library_asl=plan_library_asl,
				problem_files=test_instances,
				max_output_bytes=max_domain_long_asl_bytes,
			)
		else:
			append_record = {
				"success": True,
				"wrapper_mode": "per_test_query_local_dfa_state_monitor_without_json_metadata",
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
					base_plan_library_asl=base_plan_library_asl,
					goal_name=f"g_{safe_goal_fragment(domain)}_test_{index}",
					output_dir=(
					run_root
					/ "jason"
					/ domain
					/ f"test_{index:04d}_{safe_path_fragment(problem_file.stem)}"
				),
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
) -> tuple[str, ...]:
	"""Return the compile command used before full-test Jason validation."""

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
	if atomic_library_mode == "post-moose-recursive":
		command.append("--post-moose-recursive")
	return tuple(command)


def append_state_monitor_full_test_wrappers(
	*,
	domain: str,
	plan_library_asl: Path,
	problem_files: Sequence[Path],
	max_output_bytes: int,
) -> dict[str, Any]:
	"""Append the same query-local DFA-state wrappers as the temporal appender.

	This validation runner intentionally writes only ASL. It avoids the canonical
	``plan_library.json`` temporal metadata because full-test batches can contain
	hundreds of query wrappers and their DFA payloads are not needed by Jason.
	"""

	base_text = plan_library_asl.read_text(encoding="utf-8").rstrip()
	goal_count = 0
	plan_count = 0
	line_count = len(base_text.splitlines()) + 5
	with plan_library_asl.open("w", encoding="utf-8") as output:
		output.write(base_text)
		output.write(
			"\n\n/* Full-test query-local DFA-state temporal wrappers.\n"
			"   These wrappers keep the same ASL shape as the temporal goal appender,\n"
			"   but skip JSON DFA metadata because Jason only needs the ASL file. */\n\n",
		)
		for index, problem_file in enumerate(problem_files, start=1):
			wrapper_lines, wrapper_plan_count = state_monitor_wrapper_lines(
				domain=domain,
				index=index,
				problem_file=problem_file,
			)
			for line in wrapper_lines:
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
			plan_count += wrapper_plan_count
			goal_count += 1
	return {
		"success": True,
		"wrapper_mode": "query_local_dfa_state_monitor_without_json_metadata",
		"query_count": goal_count,
		"appended_plan_count": plan_count,
		"line_count": line_count,
		"domain_long_asl_written": True,
	}


def state_monitor_wrapper_lines(
	*,
	domain: str,
	index: int,
	problem_file: Path,
) -> tuple[tuple[str, ...], int]:
	"""Return one test problem's query-local DFA-state temporal wrapper."""

	problem = PDDLParser.parse_problem(problem_file)
	goal_facts = tuple(fact for fact in problem.goal_facts if fact.is_positive)
	if len(goal_facts) != len(problem.goal_facts):
		raise ValueError(
			f"{problem_file} contains negative goal literals; full-test Jason "
			"validation only appends positive atomic progress goals.",
		)
	if not goal_facts:
		raise ValueError(f"{problem_file} contains no positive goal literals.")
	goal_name = f"g_{safe_goal_fragment(domain)}_test_{index}"
	atoms = tuple(render_fact_atom(fact) for fact in goal_facts)
	lines: list[str] = [
		f"/* full_test_problem={problem_file.name} */",
		f"tg_state({goal_name}, s0).",
		"",
	]
	for atom_index, atom in enumerate(atoms, start=1):
		source_state = f"s{atom_index - 1}"
		target_state = f"s{atom_index}"
		lines.extend(
			[
				f"/* plan={goal_name}_progress_{atom_index} | source_instruction_ids=none */",
				f"+!{goal_name} : tg_state({goal_name}, {source_state}) <-",
				f"\t!{atom};",
				f"\t-tg_state({goal_name}, {source_state});",
				f"\t+tg_state({goal_name}, {target_state});",
				f"\t!{goal_name}.",
				"",
			],
		)
	accepting_state = f"s{len(atoms)}"
	lines.extend(
		[
			f"/* plan={goal_name}_accepting_1 | source_instruction_ids=none */",
			f"+!{goal_name} : tg_state({goal_name}, {accepting_state}) <-",
			f"\t-tg_state({goal_name}, {accepting_state});",
			f"\t+tg_state({goal_name}, s0).",
			"",
		],
	)
	return tuple(lines), len(atoms) + 1


def materialize_runtime_asl_for_task(task: JasonTask) -> Path:
	"""Write a per-test ASL file with the same wrapper shape as the long library."""

	runtime_asl = task.output_dir / "plan_library.asl"
	base_text = task.base_plan_library_asl.read_text(encoding="utf-8").rstrip()
	wrapper_lines, _ = state_monitor_wrapper_lines(
		domain=task.domain,
		index=task.index,
		problem_file=task.problem_file,
	)
	runtime_asl.write_text(
		base_text + "\n\n" + "\n".join(wrapper_lines).rstrip() + "\n",
		encoding="utf-8",
	)
	return runtime_asl


def render_fact_atom(fact: PDDLFact) -> str:
	"""Render a grounded PDDL fact as the AgentSpeak atom used by the ASL renderer."""

	predicate = sanitize_identifier(fact.predicate)
	arguments = tuple(sanitize_identifier(argument) for argument in fact.args)
	if not arguments:
		return predicate
	return f"{predicate}({', '.join(arguments)})"


def run_jason_tasks(
	*,
	tasks: Sequence[JasonTask],
	classpath: str,
	run_root: Path,
	num_workers: int,
	timeout_seconds: int,
	summary: dict[str, Any],
	summary_file: Path,
) -> list[dict[str, Any]]:
	"""Run Jason validation tasks in a bounded worker pool."""

	compiled_environment_dirs = prepare_shared_jason_environments(
		tasks=tuple(tasks),
		classpath=classpath,
		run_root=run_root,
		timeout_seconds=timeout_seconds,
		summary=summary,
		summary_file=summary_file,
	)
	records: list[dict[str, Any]] = []
	with ThreadPoolExecutor(max_workers=num_workers) as executor:
		future_map = {
			executor.submit(
				validate_one_task,
				task,
				classpath=classpath,
				compiled_environment_dirs=compiled_environment_dirs,
				timeout_seconds=timeout_seconds,
			): task
			for task in tasks
		}
		for future in as_completed(future_map):
			record = future.result()
			records.append(record)
			summary["validations"] = sorted(
				records,
				key=lambda item: (str(item["domain"]), int(item["test_index"])),
			)
			write_json(summary_file, summary)
			status = "ok" if record.get("success") else "fail"
			print(
				f"[{status}] {record['domain']} test={record['test_index']} "
				f"goal={record['goal_name']} status={record.get('status')}",
				flush=True,
			)
	return sorted(records, key=lambda item: (str(item["domain"]), int(item["test_index"])))


def validate_one_task(
	task: JasonTask,
	*,
	classpath: str,
	compiled_environment_dirs: Mapping[str, Path],
	timeout_seconds: int,
) -> dict[str, Any]:
	"""Run one Jason validation and return a compact record."""

	start = time.perf_counter()
	task.output_dir.mkdir(parents=True, exist_ok=True)
	try:
		runtime_asl = materialize_runtime_asl_for_task(task)
		result = JasonPlanLibraryRunner(
			timeout_seconds=timeout_seconds,
			jason_classpath=classpath,
			compiled_environment_dir=compiled_environment_dirs.get(
				str(task.domain_file.resolve()),
			),
		).validate(
			domain_file=task.domain_file,
			problem_file=task.problem_file,
			plan_library_asl=runtime_asl,
			goal_name=task.goal_name,
			output_dir=task.output_dir,
		)
		payload = result.to_dict()
		record = {
			"domain": task.domain,
			"test_index": task.index,
			"problem_file": str(task.problem_file),
			"goal_name": task.goal_name,
			"success": bool(payload.get("success")),
			"status": payload.get("status"),
			"timed_out": bool(payload.get("timed_out")),
			"exit_code": payload.get("exit_code"),
			"action_count": int(
				payload.get("action_count") or len(tuple(payload.get("action_path") or ())),
			),
			"output_dir": str(task.output_dir),
			"runtime_plan_library_asl": str(runtime_asl),
			"domain_full_plan_library_asl": str(task.plan_library_asl),
			"error": payload.get("error"),
			"duration_seconds": time.perf_counter() - start,
		}
	except Exception as error:  # noqa: BLE001 - persisted for full-test diagnosis.
		record = {
			"domain": task.domain,
			"test_index": task.index,
			"problem_file": str(task.problem_file),
			"goal_name": task.goal_name,
			"success": False,
			"status": "exception",
			"timed_out": False,
			"exit_code": None,
			"action_count": 0,
			"output_dir": str(task.output_dir),
			"error": str(error),
			"duration_seconds": time.perf_counter() - start,
		}
	(task.output_dir / "validation_record.json").write_text(
		json.dumps(record, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)
	return record


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
			environment_java_path.write_text(environment_java, encoding="utf-8")
			with stdout_file.open("w", encoding="utf-8") as stdout_handle:
				with stderr_file.open("w", encoding="utf-8") as stderr_handle:
					completed = subprocess.run(
						[
							javac_bin,
							"-cp",
							classpath,
							environment_java_path.name,
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
