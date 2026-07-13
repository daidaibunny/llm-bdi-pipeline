#!/usr/bin/env python3
"""
Run the current faithful MOOSE-to-ASL pipeline end to end.

This script uses the selected domain train split as MOOSE training input,
dumps the learned first-order decision-list policy, and compiles it into a
per-domain AgentSpeak(L) atomic literal library. The historical two-query
temporal append smoke test is still available for targeted probes, but batch
paper validation should use ``--skip-temporal-append`` and then run the full
test split through ``scripts/run_full_test_jason_validation.py``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

try:
	import resource
except ImportError:  # pragma: no cover - Unix-only guard.
	resource = None  # type: ignore[assignment]


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
MOOSE_ROOT = PROJECT_ROOT / ".external" / "moose"
MOOSE_PAPER_GOAL_PERMUTATIONS = 3
MOOSE_PAPER_SYNTHESIS_TIMEOUT_SECONDS = 12 * 60 * 60
MOOSE_PAPER_PLANNING_TIMEOUT_SECONDS = 1800
MOOSE_REPRODUCTION_RANDOM_SEED = 0
MOOSE_REPRODUCTION_SYNTHESIS_WORKERS = 12


def load_selected_benchmark_domain_ids() -> tuple[str, ...]:
	"""Load the selected benchmark domain ids from the registry control file."""

	registry_file = (
		PROJECT_ROOT / "src" / "benchmark_registry" / "achievement_goals" / "registry.json"
	)
	payload = json.loads(registry_file.read_text(encoding="utf-8"))
	return tuple(str(domain_id) for domain_id in payload["selected_domain_ids"])


DEFAULT_DOMAINS = load_selected_benchmark_domain_ids()

if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from utils.pddl_parser import PDDLFact  # noqa: E402
from utils.pddl_parser import PDDLNumericCondition  # noqa: E402
from utils.pddl_parser import PDDLNumericExpression  # noqa: E402
from utils.pddl_parser import PDDLNumericFluent  # noqa: E402
from utils.pddl_parser import PDDLParser  # noqa: E402
from plan_library.models import AgentSpeakBodyStep  # noqa: E402
from plan_library.models import PlanLibrary  # noqa: E402
from plan_library.rendering import render_plan_library_asl  # noqa: E402
from domain_level_planning.temporal_goal_appender import (  # noqa: E402
	append_temporal_goal_to_library,
)


@dataclass(frozen=True)
class CommandResult:
	"""One subprocess execution record."""

	command: tuple[str, ...]
	cwd: str
	stdout_file: str
	stderr_file: str
	exit_code: int | None
	timed_out: bool
	duration_seconds: float

	@property
	def success(self) -> bool:
		return not self.timed_out and self.exit_code == 0

	def to_dict(self) -> dict[str, object]:
		return {
			"command": list(self.command),
			"cwd": self.cwd,
			"stdout_file": self.stdout_file,
			"stderr_file": self.stderr_file,
			"exit_code": self.exit_code,
			"timed_out": self.timed_out,
			"duration_seconds": self.duration_seconds,
			"success": self.success,
		}


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"--domain",
		action="append",
		choices=DEFAULT_DOMAINS,
		help="Selected domain. Repeat to run multiple domains. Defaults to all benchmark domains.",
	)
	parser.add_argument(
		"--output-root",
		type=Path,
		default=PROJECT_ROOT / "tmp" / "moose_faithful_e2e",
		help="Non-canonical run logs and generated lifted LTLf JSON.",
	)
	parser.add_argument(
		"--library-root",
		type=Path,
		default=PROJECT_ROOT / "artifacts" / "domain_libraries",
		help="Canonical per-domain ASL library root.",
	)
	parser.add_argument(
		"--random-seed",
		type=int,
		default=MOOSE_REPRODUCTION_RANDOM_SEED,
		help="Seed for this independent MOOSE synthesis repetition.",
	)
	parser.add_argument(
		"--num-workers",
		type=int,
		default=MOOSE_REPRODUCTION_SYNTHESIS_WORKERS,
		help="MOOSE synthesis threads within each sequentially processed domain.",
	)
	parser.add_argument(
		"--num-permutations",
		type=int,
		default=MOOSE_PAPER_GOAL_PERMUTATIONS,
		help="Goal orderings per problem; Algorithm 1 in the MOOSE paper defaults to 3.",
	)
	parser.add_argument("--goal-max-size", type=int, default=1)
	parser.add_argument(
		"--atomic-library-mode",
		choices=("faithful", "validated-policy-lifting"),
		default="faithful",
		help=(
			"Compile raw MOOSE decision-list macros faithfully, or validate and "
			"lift MOOSE singleton policy evidence with the PDDL schema before "
			"ASL rendering."
		),
	)
	parser.add_argument(
		"--train-timeout-seconds",
		type=int,
		default=MOOSE_PAPER_SYNTHESIS_TIMEOUT_SECONDS,
		help="MOOSE synthesis wall-clock cap; the paper uses 12 hours.",
	)
	parser.add_argument("--dump-timeout-seconds", type=int, default=300)
	parser.add_argument("--append-timeout-seconds", type=int, default=300)
	parser.add_argument("--jason-timeout-seconds", type=int, default=1800)
	parser.add_argument(
		"--moose-plan-timeout-seconds",
		type=int,
		default=MOOSE_PAPER_PLANNING_TIMEOUT_SECONDS,
		help="MOOSE test-time planning cap; the paper uses 1800 seconds.",
	)
	parser.add_argument("--moose-plan-bound", type=int, default=5000)
	parser.add_argument(
		"--jason-plan-verifier-command",
		help="Optional VAL or IPC verifier command for Jason-exported PDDL traces.",
	)
	parser.add_argument(
		"--require-jason-plan-verifier",
		action="store_true",
		help="Require Jason-exported PDDL plan traces to pass VAL/IPC verification.",
	)
	parser.add_argument(
		"--jason-plan-verifier-timeout-seconds",
		type=int,
		default=1800,
		help="Hard timeout for VAL/IPC verification of Jason-exported traces.",
	)
	parser.add_argument(
		"--moose-runtime",
		choices=("docker", "local"),
		default="docker",
		help="Run MOOSE in the exact Docker/Apptainer environment or local Python.",
	)
	parser.add_argument(
		"--max-rss-gb",
		type=float,
		default=16.0,
		help="Best-effort memory guard for external MOOSE and MONA subprocesses.",
	)
	parser.add_argument(
		"--skip-moose-policy-validation",
		action="store_true",
		help="Skip direct MOOSE policy execution on the two selected test instances.",
	)
	parser.add_argument(
		"--skip-temporal-append",
		action="store_true",
		help=(
			"Generate only the atomic MOOSE-backed ASL library. Do not append the "
			"legacy first-two test query wrappers or run stage-1 validation."
		),
	)
	parser.add_argument(
		"--skip-jason-validation",
		action="store_true",
		help="Skip Jason execution after appending the two temporal query wrappers.",
	)
	parser.add_argument(
		"--fail-fast",
		action="store_true",
		help="Stop after the first domain-level failure.",
	)
	args = parser.parse_args()
	args.atomic_library_mode = normalise_atomic_library_mode(args.atomic_library_mode)

	domains = tuple(args.domain or DEFAULT_DOMAINS)
	output_root = args.output_root.expanduser().resolve()
	output_root.mkdir(parents=True, exist_ok=True)
	summary = {
		"pipeline": _pipeline_name(args.atomic_library_mode),
		"domains": [],
		"settings": {
			"domains": list(domains),
			"random_seed": args.random_seed,
			"num_workers": args.num_workers,
			"num_permutations": args.num_permutations,
			"goal_max_size": args.goal_max_size,
			"atomic_library_mode": args.atomic_library_mode,
			"max_rss_gb": args.max_rss_gb,
			"moose_runtime": args.moose_runtime,
			"full_train_split": True,
			"temporal_append_in_stage1": not args.skip_temporal_append,
			"test_instance_count": 0 if args.skip_temporal_append else 2,
			"skip_jason_validation": args.skip_jason_validation,
			"skip_moose_policy_validation": args.skip_moose_policy_validation,
		},
	}
	for domain_name in domains:
		record = run_domain(domain_name, args=args, output_root=output_root)
		summary["domains"].append(record)
		(output_root / "summary.json").write_text(
			json.dumps(summary, indent=2, sort_keys=True) + "\n",
			encoding="utf-8",
		)
		if args.fail_fast and not bool(record.get("success")):
			break
	print(json.dumps(summary, indent=2, sort_keys=True))
	return 0 if all(bool(item.get("success")) for item in summary["domains"]) else 1


def run_domain(
	domain_name: str,
	*,
	args: argparse.Namespace,
	output_root: Path,
) -> dict[str, Any]:
	"""Run training, compilation, temporal append, and validation for one domain."""

	domain_root = PROJECT_ROOT / "src" / "domains" / domain_name
	domain_file = domain_root / "domain.pddl"
	train_dir = domain_root / "train"
	test_dir = domain_root / "test"
	source_metadata = load_domain_source_metadata(domain_root)
	run_root = output_root / domain_name
	log_root = run_root / "logs"
	log_root.mkdir(parents=True, exist_ok=True)
	model_file = run_root / f"{domain_name}.model"
	readable_policy_file = run_root / f"{domain_name}.model.readable"
	goal_json = run_root / f"{domain_name}_first2_test_goals.json"
	compat_root = run_root / "moose_compatible_pddl"

	record: dict[str, Any] = {
		"domain": domain_name,
		"domain_file": str(domain_file),
		"evidence_provider_path": "native_train_dump_policy",
		"moose_official_benchmark": is_moose_official_benchmark(source_metadata),
		"source_metadata": source_metadata,
		"train_dir": str(train_dir),
		"success": False,
		"commands": {},
		"selected_test_instances": [],
		"temporal_append_in_stage1": not args.skip_temporal_append,
	}
	try:
		test_instances: tuple[Path, ...] = ()
		if not args.skip_temporal_append:
			test_instances = first_n_test_instances(test_dir, count=2)
			record["selected_test_instances"] = [str(path) for path in test_instances]
			query_append_mode = selected_query_append_mode(test_instances)
			record["query_append_mode"] = query_append_mode
			if query_append_mode == "ltlf_singleton_predicate_sequence":
				write_test_goal_dataset(
					domain_name=domain_name,
					problem_files=test_instances,
					output_file=goal_json,
				)
				record["ltlf_goal_json"] = str(goal_json)
		compat = materialize_moose_compatible_pddl(
			domain_file=domain_file,
			train_dir=train_dir,
			test_instances=test_instances,
			output_root=compat_root,
		)
		record["moose_compatible_pddl"] = compat

		train_result = run_command(
			moose_train_command(
				domain_file=Path(compat["domain_file"]),
				train_dir=Path(compat["train_dir"]),
				model_file=model_file,
				random_seed=args.random_seed,
				num_workers=args.num_workers,
				num_permutations=args.num_permutations,
				goal_max_size=args.goal_max_size,
				runtime=args.moose_runtime,
				max_rss_gb=args.max_rss_gb,
			),
			cwd=MOOSE_ROOT,
			stdout_file=log_root / "moose_train.stdout.txt",
			stderr_file=log_root / "moose_train.stderr.txt",
			timeout_seconds=args.train_timeout_seconds,
			max_rss_gb=args.max_rss_gb,
		)
		record["commands"]["moose_train"] = train_result.to_dict()
		if not train_result.success:
			return record

		dump_result = run_command(
			moose_dump_policy_command(
				model_file=Path(model_file),
				runtime=args.moose_runtime,
				max_rss_gb=args.max_rss_gb,
			),
			cwd=MOOSE_ROOT,
			stdout_file=readable_policy_file,
			stderr_file=log_root / "moose_dump_policy.stderr.txt",
			timeout_seconds=args.dump_timeout_seconds,
			max_rss_gb=args.max_rss_gb,
		)
		record["commands"]["moose_dump_policy"] = dump_result.to_dict()
		if not dump_result.success:
			return record

		compile_result = run_command(
			compile_moose_atomic_library_command(
				readable_policy_file=readable_policy_file,
				domain_file=domain_file,
				domain_name=domain_name,
				library_root=args.library_root,
				atomic_library_mode=args.atomic_library_mode,
			),
			cwd=PROJECT_ROOT,
			stdout_file=log_root / "compile_atomic_library.stdout.json",
			stderr_file=log_root / "compile_atomic_library.stderr.txt",
			timeout_seconds=args.append_timeout_seconds,
			max_rss_gb=args.max_rss_gb,
		)
		record["commands"]["compile_atomic_library"] = compile_result.to_dict()
		if not compile_result.success:
			return record

		record["canonical_library"] = {
			"json": str(args.library_root / domain_name / "plan_library.json"),
			"asl": str(args.library_root / domain_name / "plan_library.asl"),
		}
		if args.skip_temporal_append:
			record["temporal_append_skipped"] = True
			record["moose_policy_validation"] = []
			record["moose_policy_validation_skipped"] = True
			record["jason_validation"] = []
			record["jason_validation_skipped"] = True
			record["success"] = True
			return record

		if record.get("query_append_mode") == "ltlf_singleton_predicate_sequence":
			query_ids = tuple(f"query_{index}" for index in range(1, len(test_instances) + 1))
			append_command = [
				sys.executable,
				str(PROJECT_ROOT / "src" / "main.py"),
				"append-lifted-temporal-goal",
				"--domain-file",
				str(domain_file),
				"--ltlf-goal-json",
				str(goal_json),
				"--library-root",
				str(args.library_root),
			]
			for query_id in query_ids:
				append_command.extend(("--query-id", query_id))
			append_result = run_command(
				tuple(append_command),
				cwd=PROJECT_ROOT,
				stdout_file=log_root / "append_temporal_goals.stdout.json",
				stderr_file=log_root / "append_temporal_goals.stderr.txt",
				timeout_seconds=args.append_timeout_seconds,
				max_rss_gb=args.max_rss_gb,
				extra_env={"EVALUATION_MONA_MEMORY_LIMIT_MIB": str(int(args.max_rss_gb * 1024))},
			)
			record["commands"]["append_temporal_goals"] = append_result.to_dict()
			if not append_result.success:
				return record
		else:
			record["evaluation_pddl_goal_wrapper_bridge"] = append_problem_goal_wrappers_to_library(
				domain_name=domain_name,
				problem_files=test_instances,
				library_root=args.library_root,
				artifact_metadata={
					"base_artifact_kind": "domain_library",
					"artifact_kind": "domain_library_with_evaluation_pddl_goal_wrapper_bridge",
					"pddl_domain_name": domain_name,
					"query_append_mode": record.get("query_append_mode"),
				},
			)

		if not args.skip_moose_policy_validation:
			record["moose_policy_validation"] = [
				run_moose_policy_validation(
					domain_name=domain_name,
					domain_file=Path(compat["domain_file"]),
					problem_file=Path(compat["test_files"][index - 1]),
					model_file=model_file,
					run_root=run_root,
					index=index,
					timeout_seconds=args.moose_plan_timeout_seconds,
					bound=args.moose_plan_bound,
					max_rss_gb=args.max_rss_gb,
					runtime=args.moose_runtime,
				)
				for index, problem_file in enumerate(test_instances, start=1)
			]

		if args.skip_jason_validation:
			record["jason_validation"] = []
			record["jason_validation_skipped"] = True
			record["success"] = True
			return record

		jason_results = [
			run_jason_validation(
				domain_name=domain_name,
				domain_file=domain_file,
				problem_file=problem_file,
				goal_name=f"g_{_safe_goal_fragment(domain_name)}_test_{index}",
				run_root=run_root,
				index=index,
				timeout_seconds=args.jason_timeout_seconds,
				plan_verifier_command=args.jason_plan_verifier_command,
				require_plan_verifier=bool(args.require_jason_plan_verifier),
				plan_verifier_timeout_seconds=max(
					1,
					int(args.jason_plan_verifier_timeout_seconds),
				),
				library_root=args.library_root,
				max_rss_gb=args.max_rss_gb,
			)
			for index, problem_file in enumerate(test_instances, start=1)
		]
		record["jason_validation"] = jason_results
		record["jason_validation_skipped"] = False
		record["success"] = all(bool(result.get("success")) for result in jason_results)
		return record
	except Exception as error:  # noqa: BLE001 - persisted in run summary.
		record["error"] = str(error)
		return record


def _pipeline_name(atomic_library_mode: str) -> str:
	if normalise_atomic_library_mode(atomic_library_mode) == "validated-policy-lifting":
		return "validated_policy_lifting_to_asl_e2e"
	return "faithful_moose_decision_list_to_asl_e2e"


def normalise_atomic_library_mode(mode: str) -> str:
	"""Return the configured atomic library mode."""

	return mode


def compile_moose_atomic_library_command(
	*,
	readable_policy_file: Path,
	domain_file: Path,
	domain_name: str,
	library_root: Path,
	atomic_library_mode: str,
) -> tuple[str, ...]:
	"""Return the selected Evidence Module atomic library compilation command."""

	command = [
		sys.executable,
		str(PROJECT_ROOT / "src" / "main.py"),
		"compile-moose-atomic-library",
		"--policy-file",
		str(readable_policy_file),
		"--domain-file",
		str(domain_file),
		"--domain-name",
		domain_name,
		"--library-root",
		str(library_root),
		"--overwrite",
	]
	if normalise_atomic_library_mode(atomic_library_mode) == "validated-policy-lifting":
		command.append("--validated-policy-lifting")
	return tuple(command)


def run_moose_policy_validation(
	*,
	domain_name: str,
	domain_file: Path,
	problem_file: Path,
	model_file: Path,
	run_root: Path,
	index: int,
	timeout_seconds: int,
	bound: int,
	max_rss_gb: float,
	runtime: str,
) -> dict[str, Any]:
	"""Execute MOOSE's own policy on one held-out test instance."""

	log_root = run_root / "logs"
	result = run_command(
		moose_policy_command(
			model_file=model_file,
			domain_file=domain_file,
			problem_file=problem_file,
			plan_file=run_root / f"moose_policy_test_{index}.plan",
			bound=bound,
			runtime=runtime,
			max_rss_gb=max_rss_gb,
		),
		cwd=MOOSE_ROOT,
		stdout_file=log_root / f"moose_policy_test_{index}.stdout.txt",
		stderr_file=log_root / f"moose_policy_test_{index}.stderr.txt",
		timeout_seconds=timeout_seconds,
		max_rss_gb=max_rss_gb,
	)
	payload = result.to_dict()
	payload["domain"] = domain_name
	payload["problem_file"] = str(problem_file)
	return payload


def load_domain_source_metadata(domain_root: Path) -> dict[str, Any]:
	"""Load optional benchmark provenance for a selected domain."""

	source_file = domain_root / "source.json"
	if not source_file.exists():
		return {}
	try:
		payload = json.loads(source_file.read_text(encoding="utf-8"))
	except json.JSONDecodeError:
		return {"source_file": str(source_file), "source_parse_error": True}
	return dict(payload) if isinstance(payload, dict) else {"source_file": str(source_file)}


def is_moose_official_benchmark(source_metadata: dict[str, Any]) -> bool:
	"""Return whether the selected domain came from the MOOSE official artifact."""

	return str(source_metadata.get("source_id") or "") == "moose_official_artifact"


def run_jason_validation(
	*,
	domain_name: str,
	domain_file: Path,
	problem_file: Path,
	goal_name: str,
	run_root: Path,
	index: int,
	timeout_seconds: int,
	plan_verifier_command: str | None,
	require_plan_verifier: bool,
	plan_verifier_timeout_seconds: int,
	library_root: Path,
	max_rss_gb: float,
) -> dict[str, Any]:
	"""Run the canonical ASL library in Jason for one appended goal."""

	log_root = run_root / "logs"
	output_dir = run_root / "jason" / f"test_{index}"
	result = run_command(
		(
			sys.executable,
			str(PROJECT_ROOT / "src" / "main.py"),
			"validate-jason-plan-library",
			"--domain-file",
			str(domain_file),
			"--problem-file",
			str(problem_file),
			"--goal-name",
			goal_name,
			"--library-root",
			str(library_root),
			"--output-dir",
			str(output_dir),
			"--timeout-seconds",
			str(timeout_seconds),
			"--plan-verifier-timeout-seconds",
			str(plan_verifier_timeout_seconds),
			*(("--plan-verifier-command", plan_verifier_command) if plan_verifier_command else ()),
			*(("--require-plan-verifier",) if require_plan_verifier else ()),
		),
		cwd=PROJECT_ROOT,
		stdout_file=log_root / f"jason_test_{index}.stdout.json",
		stderr_file=log_root / f"jason_test_{index}.stderr.txt",
		timeout_seconds=timeout_seconds + 30,
		max_rss_gb=max_rss_gb,
	)
	payload = result.to_dict()
	payload["domain"] = domain_name
	payload["problem_file"] = str(problem_file)
	payload["goal_name"] = goal_name
	payload["jason_output_dir"] = str(output_dir)
	if result.stdout_file and Path(result.stdout_file).exists():
		try:
			payload.update(json.loads(Path(result.stdout_file).read_text(encoding="utf-8")))
		except json.JSONDecodeError:
			pass
	return payload


def run_command(
	command: Sequence[str],
	*,
	cwd: Path,
	stdout_file: Path,
	stderr_file: Path,
	timeout_seconds: int,
	max_rss_gb: float,
	extra_env: dict[str, str] | None = None,
) -> CommandResult:
	"""Run one command with file-backed logs, timeout, and best-effort memory guard."""

	stdout_file.parent.mkdir(parents=True, exist_ok=True)
	stderr_file.parent.mkdir(parents=True, exist_ok=True)
	env = {**os.environ, **dict(extra_env or {})}
	start = time.perf_counter()
	timed_out = False
	exit_code: int | None = None
	with stdout_file.open("w", encoding="utf-8") as stdout_handle:
		with stderr_file.open("w", encoding="utf-8") as stderr_handle:
			try:
				process = subprocess.run(
					tuple(str(item) for item in command),
					cwd=cwd,
					env=env,
					stdout=stdout_handle,
					stderr=stderr_handle,
					check=False,
					timeout=timeout_seconds,
					preexec_fn=memory_limit_preexec(max_rss_gb),
				)
				exit_code = process.returncode
			except subprocess.TimeoutExpired:
				timed_out = True
	duration = time.perf_counter() - start
	return CommandResult(
		command=tuple(str(item) for item in command),
		cwd=str(cwd),
		stdout_file=str(stdout_file),
		stderr_file=str(stderr_file),
		exit_code=exit_code,
		timed_out=timed_out,
		duration_seconds=duration,
	)


def memory_limit_preexec(max_rss_gb: float):
	"""Return a subprocess preexec function that caps address-space memory."""

	if resource is None:
		return None
	memory_bytes = max(int(max_rss_gb * 1024 * 1024 * 1024), 1)

	def _apply_memory_limit() -> None:
		for limit_name in ("RLIMIT_AS", "RLIMIT_DATA", "RLIMIT_RSS"):
			limit = getattr(resource, limit_name, None)
			if limit is None:
				continue
			try:
				resource.setrlimit(limit, (memory_bytes, memory_bytes))
				break
			except (OSError, ValueError):
				continue

	return _apply_memory_limit


def moose_train_command(
	*,
	domain_file: Path,
	train_dir: Path,
	model_file: Path,
	random_seed: int,
	num_workers: int,
	num_permutations: int,
	goal_max_size: int,
	runtime: str = "docker",
	max_rss_gb: float = 16.0,
) -> tuple[str, ...]:
	"""Return the official MOOSE training command for the full train split."""

	args = (
		"train",
		container_path(domain_file) if runtime == "docker" else str(domain_file),
		container_path(train_dir) if runtime == "docker" else str(train_dir),
		"--save-file",
		container_path(model_file) if runtime == "docker" else str(model_file),
		"--random-seed",
		str(random_seed),
		"--num_workers",
		str(num_workers),
		"--num-permutations",
		str(num_permutations),
		"--goal-max-size",
		str(goal_max_size),
		"--num-training",
		"-1",
		"--num-validation",
		"-1",
	)
	return moose_runtime_command(args, runtime=runtime, max_rss_gb=max_rss_gb)


def moose_dump_policy_command(
	*,
	model_file: Path,
	runtime: str = "docker",
	max_rss_gb: float = 16.0,
) -> tuple[str, ...]:
	"""Return the official MOOSE readable policy dump command."""

	args = (
		"policy",
		container_path(model_file) if runtime == "docker" else str(model_file),
		"--dump-policy",
	)
	return moose_runtime_command(args, runtime=runtime, max_rss_gb=max_rss_gb)


def moose_policy_command(
	*,
	model_file: Path,
	domain_file: Path,
	problem_file: Path,
	plan_file: Path,
	bound: int,
	runtime: str = "docker",
	max_rss_gb: float = 16.0,
) -> tuple[str, ...]:
	"""Return the official MOOSE policy execution command."""

	args = (
		"policy",
		container_path(model_file) if runtime == "docker" else str(model_file),
		container_path(domain_file) if runtime == "docker" else str(domain_file),
		container_path(problem_file) if runtime == "docker" else str(problem_file),
		"--bound",
		str(bound),
		"--plan-file",
		container_path(plan_file) if runtime == "docker" else str(plan_file),
		"-val",
	)
	return moose_runtime_command(args, runtime=runtime, max_rss_gb=max_rss_gb)


def moose_runtime_command(
	moose_args: Sequence[str],
	*,
	runtime: str,
	max_rss_gb: float,
) -> tuple[str, ...]:
	"""Wrap official MOOSE arguments in the selected runtime."""

	if runtime == "local":
		command = "train.py" if tuple(moose_args)[0] == "train" else "policy.py"
		return (str(moose_python()), command, *tuple(moose_args)[1:])
	if runtime != "docker":
		raise ValueError(f"Unsupported MOOSE runtime: {runtime}")
	if shutil.which("docker") is None:
		raise FileNotFoundError("Docker is required for --moose-runtime docker.")
	inner_command = (
		"apptainer run --bind /work --bind /project /work/moose.sif "
		+ shlex.join(tuple(moose_args))
	)
	return (
		"docker",
		"run",
		"--rm",
		"--platform",
		"linux/amd64",
		f"--memory={int(max_rss_gb)}g",
		"--privileged",
		"-v",
		f"{MOOSE_ROOT}:/work",
		"-v",
		f"{PROJECT_ROOT}:/project",
		"-w",
		"/work",
		"moose-exact-ubuntu22:local",
		"bash",
		"-lc",
		inner_command,
	)


def moose_python() -> Path:
	"""Return the local MOOSE Python executable."""

	candidate = MOOSE_ROOT / ".venv" / "bin" / "python"
	if candidate.exists():
		return candidate
	raise FileNotFoundError(
		"Missing MOOSE virtual environment. Expected "
		f"{candidate}. Install the official MOOSE dependencies first."
	)


def first_n_test_instances(test_dir: Path, *, count: int) -> tuple[Path, ...]:
	"""Return the first test instances under natural filename ordering."""

	paths = tuple(sorted(test_dir.glob("*.pddl"), key=natural_sort_key))
	if len(paths) < count:
		raise ValueError(f"{test_dir} contains only {len(paths)} PDDL test instances.")
	return paths[:count]


def materialize_moose_compatible_pddl(
	*,
	domain_file: Path,
	train_dir: Path,
	test_instances: Sequence[Path],
	output_root: Path,
) -> dict[str, Any]:
	"""Write normalized PDDL copies for MOOSE's strict parser."""

	domain_output = output_root / "domain.pddl"
	train_output = output_root / "train"
	test_output = output_root / "test"
	domain_output.parent.mkdir(parents=True, exist_ok=True)
	train_output.mkdir(parents=True, exist_ok=True)
	test_output.mkdir(parents=True, exist_ok=True)
	domain_output.write_text(
		normalise_pddl_for_moose(domain_file.read_text(encoding="utf-8")),
		encoding="utf-8",
	)
	train_files: list[str] = []
	for source_file in sorted(train_dir.glob("*.pddl"), key=natural_sort_key):
		target_file = train_output / source_file.name
		target_file.write_text(
			normalise_pddl_for_moose(source_file.read_text(encoding="utf-8")),
			encoding="utf-8",
		)
		train_files.append(str(target_file))
	test_files: list[str] = []
	for source_file in tuple(test_instances):
		target_file = test_output / source_file.name
		target_file.write_text(
			normalise_pddl_for_moose(source_file.read_text(encoding="utf-8")),
			encoding="utf-8",
		)
		test_files.append(str(target_file))
	return {
		"domain_file": str(domain_output),
		"train_dir": str(train_output),
		"train_count": len(train_files),
		"test_files": test_files,
	}


def normalise_pddl_for_moose(text: str) -> str:
	"""Normalize PDDL syntax accepted by our parser but rejected by MOOSE's parser."""

	normalised = str(text or "").lower()
	if "(:types" not in normalised or ":typing" in normalised:
		return normalised
	requirements_match = re.search(r"\(:requirements(?P<body>[^)]*)\)", normalised)
	if requirements_match is None:
		define_match = re.search(r"\(define\s+\(domain\s+[^)]+\)", normalised)
		if define_match is None:
			return normalised
		insert_at = define_match.end()
		return (
			normalised[:insert_at]
			+ "\n (:requirements :strips :typing)"
			+ normalised[insert_at:]
		)
	body = requirements_match.group("body")
	updated = f"(:requirements{body} :typing)"
	return (
		normalised[: requirements_match.start()]
		+ updated
		+ normalised[requirements_match.end() :]
	)


def container_path(path: Path) -> str:
	"""Map a project-local host path into the Docker MOOSE container."""

	resolved = path.expanduser().resolve()
	try:
		relative = resolved.relative_to(PROJECT_ROOT)
	except ValueError as error:
		raise ValueError(f"Path is outside project root and cannot be containerized: {path}") from error
	return "/project/" + str(relative).replace(os.sep, "/")


def selected_query_append_mode(problem_files: Sequence[Path]) -> str:
	"""Return the append path required by the selected problem goals."""

	requires_direct_wrapper = False
	for problem_file in tuple(problem_files or ()):
		problem = PDDLParser.parse_problem(problem_file)
		if tuple(problem.numeric_goal_conditions or ()):
			requires_direct_wrapper = True
		if any(not fact.is_positive for fact in tuple(problem.goal_facts or ())):
			requires_direct_wrapper = True
	return (
		"evaluation_pddl_goal_wrapper_bridge"
		if requires_direct_wrapper
		else "ltlf_singleton_predicate_sequence"
	)


def append_problem_goal_wrappers_to_library(
	*,
	domain_name: str,
	problem_files: Sequence[Path],
	library_root: Path,
	artifact_metadata: dict[str, object] | None = None,
) -> dict[str, object]:
	"""Append PDDL test goals as an evaluation bridge, not the final query path."""

	domain_key = _safe_goal_fragment(domain_name)
	library_dir = library_root.expanduser().resolve() / domain_name
	library_json = library_dir / "plan_library.json"
	library_asl = library_dir / "plan_library.asl"
	metadata_file = library_dir / "artifact_metadata.json"
	if not library_json.exists():
		raise FileNotFoundError(f"Missing canonical plan library: {library_json}")
	library = PlanLibrary.from_dict(json.loads(library_json.read_text(encoding="utf-8")))
	append_records: list[dict[str, object]] = []
	domain_file = PROJECT_ROOT / "src" / "domains" / domain_name / "domain.pddl"
	if not domain_file.exists():
		raise FileNotFoundError(f"Missing canonical PDDL domain: {domain_file}")
	for index, problem_file in enumerate(tuple(problem_files or ()), start=1):
		goal_name = f"g_{domain_key}_test_{index}"
		entry_proposition = f"{domain_key}_test_{index}"
		body_steps = _problem_goal_body_steps(problem_file)
		raw_guard = " & ".join(_body_step_atom(step) for step in body_steps)
		library = append_temporal_goal_to_library(
			plan_library=library,
			goal_name=goal_name,
			dfa_payload={
				"initial_state": "q0",
				"accepting_states": ["q1"],
				"guarded_transitions": [
					{"source_state": "q0", "target_state": "q1", "raw_label": raw_guard},
					{"source_state": "q1", "target_state": "q1", "raw_label": "true"},
				],
			},
			domain_file=domain_file,
		)
		append_records.append(
			{
				"goal_name": goal_name,
				"entry_proposition": entry_proposition,
				"problem_file": str(problem_file),
				"raw_guard": raw_guard,
				"body_steps": [step.to_dict() for step in body_steps],
			},
		)
	updated = PlanLibrary(
		domain_name=library.domain_name,
		plans=library.plans,
		initial_beliefs=library.initial_beliefs,
		metadata={
			**dict(library.metadata),
			"evaluation_pddl_goal_wrapper_bridge": {
				"wrapper_mode": "dfa_guard_transition_replay_from_pddl_goal",
				"scope": "benchmark_smoke_only",
				"final_query_contract": (
					"validated_lifted_ltlf_json_to_ltlf2dfa_to_guard_transition_append"
				),
				"append_records": append_records,
			},
			"evaluation_pddl_goal_wrapper_bridge_history": [
				*list(
					dict(library.metadata).get(
						"evaluation_pddl_goal_wrapper_bridge_history",
					)
					or [],
				),
				{
					"wrapper_mode": "dfa_guard_transition_replay_from_pddl_goal",
					"scope": "benchmark_smoke_only",
					"query_count": len(append_records),
					"goal_names": [record["goal_name"] for record in append_records],
				},
			],
		},
	)
	library_dir.mkdir(parents=True, exist_ok=True)
	library_json.write_text(
		json.dumps(updated.to_dict(), indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)
	library_asl.write_text(render_plan_library_asl(updated), encoding="utf-8")
	existing_metadata: dict[str, object] = {}
	if metadata_file.exists():
		try:
			existing_payload = json.loads(metadata_file.read_text(encoding="utf-8"))
			if isinstance(existing_payload, dict):
				existing_metadata = existing_payload
		except json.JSONDecodeError:
			existing_metadata = {}
	metadata_file.write_text(
		json.dumps(
			{
				**existing_metadata,
				**dict(artifact_metadata or {}),
				"canonical_domain_library": True,
				"domain_library_dir": str(library_dir),
				"domain_name": updated.domain_name,
				"plan_count": len(updated.plans),
				"appended_evaluation_pddl_goal_wrapper_count": len(append_records),
			},
			indent=2,
			sort_keys=True,
		)
		+ "\n",
		encoding="utf-8",
	)
	return {
		"success": True,
		"mode": "evaluation_pddl_goal_wrapper_bridge",
		"appended_query_count": len(append_records),
		"artifact_paths": {
			"plan_library": str(library_json),
			"plan_library_asl": str(library_asl),
			"artifact_metadata": str(metadata_file),
		},
		"append_records": append_records,
	}


def _problem_goal_body_steps(problem_file: Path) -> tuple[AgentSpeakBodyStep, ...]:
	problem = PDDLParser.parse_problem(problem_file)
	steps: list[AgentSpeakBodyStep] = []
	for fact in tuple(problem.goal_facts or ()):
		if not fact.is_positive:
			raise ValueError(
				f"{problem_file} contains a negative goal literal; direct PDDL goal "
				"wrappers currently support positive predicates and bounded numeric "
				"resource equalities only."
			)
		steps.append(
			AgentSpeakBodyStep(
				"subgoal",
				fact.predicate,
				tuple(str(argument) for argument in fact.args),
			),
		)
	for condition in tuple(problem.numeric_goal_conditions or ()):
		steps.append(_numeric_goal_condition_step(condition, problem_file=problem_file))
	if not steps:
		raise ValueError(f"{problem_file} contains no supported PDDL goal steps.")
	return tuple(steps)


def _body_step_atom(step: AgentSpeakBodyStep) -> str:
	arguments = tuple(step.arguments or ())
	if not arguments:
		return step.symbol
	return f"{step.symbol}({', '.join(arguments)})"


def _numeric_goal_condition_step(
	condition: PDDLNumericCondition,
	*,
	problem_file: Path,
) -> AgentSpeakBodyStep:
	if condition.comparator != "=":
		raise ValueError(
			f"{problem_file} contains unsupported numeric goal comparator "
			f"{condition.comparator!r}; only equality is in the bounded resource fragment."
		)
	fluent, target = _numeric_goal_fluent_and_target(condition.left, condition.right)
	if fluent is None or target is None:
		fluent, target = _numeric_goal_fluent_and_target(condition.right, condition.left)
	if fluent is None or target is None:
		raise ValueError(
			f"{problem_file} contains unsupported numeric goal "
			f"{condition.to_signature()!r}; expected one numeric fluent and one "
			"integer target constant."
		)
	return AgentSpeakBodyStep(
		"subgoal",
		fluent.function,
		(*tuple(fluent.args or ()), str(target)),
	)


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


def write_test_goal_dataset(
	*,
	domain_name: str,
	problem_files: Sequence[Path],
	output_file: Path,
) -> None:
	"""Write a grounded LTLf JSON dataset from selected PDDL problem goals."""

	cases: dict[str, dict[str, object]] = {}
	for index, problem_file in enumerate(problem_files, start=1):
		problem = PDDLParser.parse_problem(problem_file)
		goal_facts = tuple(fact for fact in problem.goal_facts if fact.is_positive)
		if len(goal_facts) != len(problem.goal_facts):
			raise ValueError(
				f"{problem_file} contains negative goal literals; this runner only "
				"builds positive singleton progress transitions."
			)
		if not goal_facts:
			raise ValueError(f"{problem_file} contains no positive goal literals.")
		atoms = tuple(_fact_atom(fact) for fact in goal_facts)
		cases[f"query_{index}"] = {
			"goal_name": f"g_{_safe_goal_fragment(domain_name)}_test_{index}",
			"problem_file": str(problem_file),
			"source_text": (
				"Sequentialized positive PDDL goal literals from "
				f"{problem_file.name} for faithful MOOSE-to-ASL validation."
			),
			"ltlf_formula": sequential_eventually_formula(atoms),
			"atoms": list(atoms),
			"bindings": {},
			"atom_vocabulary": "pddl_fluents",
			"status": "supported",
		}
	output_file.parent.mkdir(parents=True, exist_ok=True)
	output_file.write_text(
		json.dumps(
			{
				"schema_version": 1,
				"goal_specification_kind": "temporal_extended_goal",
				"temporal_logic": "LTLf",
				"domain": domain_name,
				"cases": cases,
			},
			indent=2,
			sort_keys=True,
		)
		+ "\n",
		encoding="utf-8",
	)


def sequential_eventually_formula(atoms: Sequence[str]) -> str:
	"""Build a singleton-progress LTLf sequence from ordered atom strings."""

	items = tuple(str(atom).strip().replace(" ", "") for atom in atoms if str(atom).strip())
	if not items:
		raise ValueError("At least one atom is required.")
	formula = f"F({items[-1]})"
	for atom in reversed(items[:-1]):
		formula = f"F({atom} & X({formula}))"
	return formula


def natural_sort_key(path: Path) -> tuple[object, ...]:
	"""Sort paths by text fragments and embedded integers."""

	parts: list[object] = []
	for item in re.split(r"(\d+)", path.name):
		if item.isdigit():
			parts.append(int(item))
		else:
			parts.append(item.lower())
	return tuple(parts)


def _fact_atom(fact: PDDLFact) -> str:
	args = tuple(str(arg).strip() for arg in fact.args if str(arg).strip())
	if not args:
		return fact.predicate
	return f"{fact.predicate}({','.join(args)})"


def _safe_goal_fragment(value: str) -> str:
	text = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "").strip().lower()).strip("_")
	if not text:
		return "domain"
	if text[0].isdigit():
		return f"d_{text}"
	return text


if __name__ == "__main__":
	raise SystemExit(main())
