#!/usr/bin/env python3
"""Append every test goal from a MOOSE ASL batch and validate it in Jason."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
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
from evaluation.jason_runtime.runner import PredicatePattern  # noqa: E402
from evaluation.jason_runtime.runner import RuntimeActionSchema  # noqa: E402
from scripts.run_moose_faithful_e2e import DEFAULT_DOMAINS  # noqa: E402
from scripts.run_moose_faithful_e2e import natural_sort_key  # noqa: E402
from plan_library.rendering import sanitize_identifier  # noqa: E402
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
	compact_completion_wrappers: bool
	output_dir: Path
	runtime_wrapper_text: str | None = None


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
	parser.add_argument("--timeout-seconds", type=int, default=1800)
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
		"--write-domain-long-asl",
		action="store_true",
		help=(
			"Also write one full-test ASL per domain. Disabled by default because "
			"large validation suites can still produce bulky ASL artifacts."
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
		"--compact-completion-wrappers",
		action="store_true",
		help=(
			"Deprecated compatibility flag. Full-test validation always uses "
			"query-local guard-transition replay wrappers."
		),
	)
	parser.add_argument(
		"--suppress-final-summary-json",
		action="store_true",
		help=(
			"Do not print the full summary JSON to stdout. The summary file is "
			"still written; per-test status lines remain visible."
		),
	)
	args = parser.parse_args()
	args.atomic_library_mode = normalise_atomic_library_mode(args.atomic_library_mode)

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
			"jason_java_stack_size": args.jason_java_stack_size,
			"plan_verifier_command": args.plan_verifier_command,
			"require_plan_verifier": bool(args.require_plan_verifier),
			"plan_verifier_timeout_seconds": args.plan_verifier_timeout_seconds,
			"atomic_library_mode": args.atomic_library_mode,
			"prepare_only": bool(args.prepare_only),
			"write_domain_long_asl": bool(args.write_domain_long_asl),
			"write_per_test_runtime_asl": bool(args.write_per_test_runtime_asl),
			"max_domain_long_asl_mb": args.max_domain_long_asl_mb,
			"suppress_final_summary_json": bool(args.suppress_final_summary_json),
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
			test_name_regex=args.test_name_regex,
			compact_completion_wrappers=bool(args.compact_completion_wrappers),
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
		summary=summary,
		summary_file=summary_file,
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
	compact_completion_wrappers: bool = False,
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
		base_plan_library_asl_text = plan_library_asl.read_text(encoding="utf-8").rstrip()
		wrapper_text_by_problem: dict[Path, str] = {}
		wrapper_plan_count: int | None = None
		if write_domain_long_asl:
			wrapper_text_by_problem, wrapper_plan_count = build_full_test_wrapper_texts(
				domain=domain,
				problem_files=test_instances,
				domain_file=domain_file,
				compact_completion_wrappers=compact_completion_wrappers,
			)
			append_record = append_guard_transition_full_test_wrappers(
				domain=domain,
				plan_library_asl=plan_library_asl,
				problem_files=test_instances,
				domain_file=domain_file,
				max_output_bytes=max_domain_long_asl_bytes,
				compact_completion_wrappers=compact_completion_wrappers,
				wrapper_text_by_problem=wrapper_text_by_problem,
				appended_plan_count=wrapper_plan_count,
			)
		else:
			append_record = {
				"success": True,
				"wrapper_mode": "per_test_guard_trans_replay_without_json_metadata",
				"compact_completion_wrappers": compact_completion_wrappers,
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
				compact_completion_wrappers=compact_completion_wrappers,
				output_dir=(
					run_root
					/ "jason"
					/ domain
					/ f"test_{index:04d}_{safe_path_fragment(problem_file.stem)}"
				),
				runtime_wrapper_text=wrapper_text_by_problem.get(problem_file),
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
		command.append("--validated-policy-lifting")
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
	compact_completion_wrappers: bool = False,
	wrapper_text_by_problem: Mapping[Path, str] | None = None,
	appended_plan_count: int | None = None,
) -> dict[str, Any]:
	"""Append one query-local guard-transition replay wrapper per test problem.

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
			compact_completion_wrappers=compact_completion_wrappers,
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
			"\n\n/* Full-test query-local guard-transition replay wrappers.\n"
			"   Each PDDL conjunctive goal is treated as one DFA-style transition\n"
			"   guard whose positive achievement literals must hold together. */\n\n",
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
		"wrapper_mode": "guard_trans_replay_without_json_metadata",
		"compact_completion_wrappers": compact_completion_wrappers,
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
	compact_completion_wrappers: bool = False,
) -> tuple[dict[Path, str], int]:
	"""Render each full-test query wrapper once, keyed by problem file."""

	wrapper_map: dict[Path, str] = {}
	total_plan_count = 0
	action_schemas = _runtime_action_schemas_for_domain(domain_file)
	for index, problem_file in enumerate(problem_files, start=1):
		wrapper_lines, wrapper_plan_count = full_test_wrapper_lines(
			domain=domain,
			index=index,
			problem_file=problem_file,
			domain_file=domain_file,
			action_schemas=action_schemas,
			compact_completion_wrappers=compact_completion_wrappers,
		)
		wrapper_map[problem_file] = "\n".join(wrapper_lines).rstrip()
		total_plan_count += wrapper_plan_count
	return wrapper_map, total_plan_count


def full_test_wrapper_lines(
	*,
	domain: str,
	index: int,
	problem_file: Path,
	compact_completion_wrappers: bool = False,
	problem: Any | None = None,
	domain_file: Path | None = None,
	action_schemas: Sequence[RuntimeActionSchema] | None = None,
) -> tuple[tuple[str, ...], int]:
	"""Return the query-local guard-transition replay wrapper for a test problem."""

	_ = compact_completion_wrappers
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
	return guard_transition_replay_wrapper_lines(
		domain=domain,
		index=index,
		problem_file=problem_file,
		problem=problem,
		domain_file=domain_file,
		action_schemas=action_schemas,
	)


def compact_recursive_completion_wrapper_lines(
	*,
	domain: str,
	index: int,
	problem_file: Path,
	goal_facts: Sequence[PDDLFact],
	init_facts: Sequence[PDDLFact],
) -> tuple[tuple[str, ...], int] | None:
	"""Compile repeated same-predicate goals into a query-local completion loop."""

	if len(goal_facts) < 2:
		return None
	predicate = goal_facts[0].predicate
	arity = len(goal_facts[0].args)
	if any(fact.predicate != predicate or len(fact.args) != arity for fact in goal_facts):
		return None
	varying_positions = tuple(
		position
		for position in range(arity)
		if len({fact.args[position] for fact in goal_facts}) > 1
	)
	if not varying_positions:
		return None
	target_tuples = {
		tuple(fact.args[position] for position in varying_positions)
		for fact in goal_facts
	}
	if len(target_tuples) != len(goal_facts):
		return None
	variable_names = tuple(_variable_name(position) for position in range(len(varying_positions)))
	target_arguments = tuple(
		variable_names[varying_positions.index(position)]
		if position in varying_positions
		else sanitize_identifier(goal_facts[0].args[position])
		for position in range(arity)
	)
	target_atom = _render_call(predicate, target_arguments)
	range_binder = _select_exact_range_binder(
		init_facts=init_facts,
		target_tuples=target_tuples,
		target_variables=variable_names,
		target_atom=target_atom,
	)
	if range_binder is None:
		return None
	goal_name = f"g_{safe_goal_fragment(domain)}_test_{index}"
	entry_proposition = query_entry_proposition(goal_name)
	context = " & ".join((entry_proposition, range_binder, f"not {target_atom}"))
	lines = [
		f"/* full_test_problem={problem_file.name} */",
		f"{entry_proposition}.",
		"",
		f"/* plan={goal_name}_recursive_completion | source_instruction_ids=none */",
		f"+!{goal_name} : {context} <-",
		f"\t!{target_atom};",
		f"\t!{goal_name}.",
		"",
		f"/* plan={goal_name}_completion_done | source_instruction_ids=none */",
		f"+!{goal_name} : {entry_proposition} <-",
		"\ttrue.",
		"",
	]
	return tuple(lines), 2


def _select_exact_range_binder(
	*,
	init_facts: Sequence[PDDLFact],
	target_tuples: set[tuple[str, ...]],
	target_variables: Sequence[str],
	target_atom: str,
) -> str | None:
	"""Find a PDDL fact pattern whose projection is exactly the goal object set."""

	candidates: list[tuple[tuple[int, int, int, str], str]] = []
	facts_by_predicate: dict[tuple[str, int], list[PDDLFact]] = {}
	for fact in init_facts:
		if fact.args:
			facts_by_predicate.setdefault((fact.predicate, len(fact.args)), []).append(fact)
	for (predicate, arity), facts in facts_by_predicate.items():
		if arity < len(target_variables):
			continue
		for positions in combinations(range(arity), len(target_variables)):
			projected = {
				tuple(fact.args[position] for position in positions)
				for fact in facts
			}
			if projected != target_tuples:
				continue
			arguments = _range_binder_arguments(
				arity=arity,
				positions=positions,
				target_variables=target_variables,
			)
			binder = _render_call(predicate, arguments)
			if binder == target_atom:
				continue
			score = (
				len(facts),
				arity,
				sum(1 for arg in arguments if arg not in target_variables),
				binder,
			)
			candidates.append((score, binder))
	if not candidates:
		return None
	return min(candidates, key=lambda item: item[0])[1]


def _range_binder_arguments(
	*,
	arity: int,
	positions: Sequence[int],
	target_variables: Sequence[str],
) -> tuple[str, ...]:
	auxiliary_index = 0
	arguments: list[str] = []
	for position in range(arity):
		if position in positions:
			arguments.append(target_variables[tuple(positions).index(position)])
			continue
		arguments.append(_auxiliary_variable_name(auxiliary_index))
		auxiliary_index += 1
	return tuple(arguments)


def _variable_name(index: int) -> str:
	names = ("X", "Y", "Z", "A", "B", "C")
	if index < len(names):
		return names[index]
	return f"X{index + 1}"


def _auxiliary_variable_name(index: int) -> str:
	names = ("A", "B", "C", "D", "E", "F")
	if index < len(names):
		return names[index]
	return f"A{index + 1}"


def guard_transition_replay_wrapper_lines(
	*,
	domain: str,
	index: int,
	problem_file: Path,
	problem: Any | None = None,
	domain_file: Path | None = None,
	action_schemas: Sequence[RuntimeActionSchema] | None = None,
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
	schemas = tuple(action_schemas or _runtime_action_schemas_for_domain(domain_file))
	ordering_edges = _goal_threat_edges(goal_facts, schemas, closure_depth=2)
	ordered_goal_facts = _stable_topological_goal_order(goal_facts, ordering_edges)
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
	if (
		len(atoms) > 1
		and schemas
		and not numeric_goal_conditions
		and _goal_predicates_are_globally_persistent(goal_facts, schemas)
	):
		return _monotonic_guard_transition_wrapper_lines(
			goal_name=goal_name,
			entry_proposition=entry_proposition,
			transition_name=transition_name,
			problem_file=problem_file,
			atoms=atoms,
		)
	done_context = " & ".join((entry_proposition, *atoms))
	lines: list[str] = [
		f"/* full_test_problem={problem_file.name} */",
		f"{entry_proposition}.",
		"",
		f"/* plan={goal_name}_transition_sequence | source_instruction_ids=none */",
		f"+!{goal_name} : {entry_proposition} <-",
		f"\t!{transition_name}.",
		"",
		f"/* plan={transition_name}_done | source_instruction_ids=none */",
		f"+!{transition_name} : {done_context} <-",
		"\ttrue.",
		"",
	]
	for atom in atoms:
		lines.extend(
			[
				f"/* plan={transition_name}_repair_{safe_goal_fragment(atom)} | source_instruction_ids=none */",
				f"+!{transition_name} : {entry_proposition} & not {atom} <-",
				f"\t!{atom};",
				f"\t!{transition_name}.",
				"",
			],
		)
	return tuple(lines), 2 + len(atoms)


def _goal_predicates_are_globally_persistent(
	goal_facts: Sequence[PDDLFact],
	action_schemas: Sequence[RuntimeActionSchema],
) -> bool:
	goal_predicates = {
		sanitize_identifier(fact.predicate)
		for fact in tuple(goal_facts or ())
	}
	deleted_predicates = {
		pattern.predicate
		for action in tuple(action_schemas or ())
		for pattern in _negative_patterns(action.effects)
	}
	return bool(goal_predicates) and goal_predicates.isdisjoint(deleted_predicates)


def _monotonic_guard_transition_wrapper_lines(
	*,
	goal_name: str,
	entry_proposition: str,
	transition_name: str,
	problem_file: Path,
	atoms: Sequence[str],
) -> tuple[tuple[str, ...], int]:
	"""Compile a threat-free conjunctive guard into indexed transition steps."""

	first_step = f"{transition_name}_step_1"
	lines: list[str] = [
		f"/* full_test_problem={problem_file.name} */",
		f"{entry_proposition}.",
		"",
		f"/* plan={goal_name}_certified_monotonic_transition | source_instruction_ids=none */",
		f"+!{goal_name} : {entry_proposition} <-",
		f"\t!{first_step}.",
		"",
	]
	for index, atom in enumerate(atoms, start=1):
		step_name = f"{transition_name}_step_{index}"
		next_step = f"{transition_name}_step_{index + 1}"
		lines.extend(
			[
				f"/* plan={step_name}_advance | source_instruction_ids=none */",
				f"+!{step_name} : {entry_proposition} & {atom} <-",
				f"\t!{next_step}.",
				"",
				f"/* plan={step_name}_repair | source_instruction_ids=none */",
				f"+!{step_name} : {entry_proposition} & not {atom} <-",
				f"\t!{atom};",
				f"\t!{step_name}.",
				"",
			],
		)
	final_step = f"{transition_name}_step_{len(atoms) + 1}"
	lines.extend(
		[
			f"/* plan={final_step}_done | source_instruction_ids=none */",
			f"+!{final_step} : {entry_proposition} <-",
			"\ttrue.",
			"",
		],
	)
	return tuple(lines), 2 + (2 * len(atoms))


def _runtime_action_schemas_for_domain(
	domain_file: Path | None,
) -> tuple[RuntimeActionSchema, ...]:
	if domain_file is None:
		return ()
	try:
		domain = PDDLParser.parse_domain(domain_file)
	except Exception:  # noqa: BLE001 - preserve parser order when probing incomplete domains.
		return ()
	return tuple(_runtime_action_schema(action) for action in tuple(domain.actions or ()))


def _deduplicate_strings(values: Sequence[str]) -> tuple[str, ...]:
	return tuple(dict.fromkeys(str(value) for value in tuple(values or ())))


@dataclass(frozen=True)
class _LiftedTerm:
	"""One threat-analysis term with explicit constant/variable identity."""

	symbol: str
	variable_scope: object | None = None

	@property
	def is_variable(self) -> bool:
		return self.variable_scope is not None


@dataclass(frozen=True)
class _LiftedAtom:
	predicate: str
	arguments: tuple[_LiftedTerm, ...]


def _threat_ordered_goal_facts(
	goal_facts: Sequence[PDDLFact],
	action_schemas: Sequence[RuntimeActionSchema],
) -> tuple[PDDLFact, ...]:
	"""Order conjunctive achievements so delete-threatening goals run earlier."""

	facts = tuple(goal_facts or ())
	schemas = tuple(action_schemas or ())
	if len(facts) < 2 or not schemas:
		return facts
	return _stable_topological_goal_order(
		facts,
		_goal_threat_edges(facts, schemas, closure_depth=2),
	)


def _goal_threat_edges(
	goal_facts: Sequence[PDDLFact],
	action_schemas: Sequence[RuntimeActionSchema],
	*,
	closure_depth: int,
) -> dict[int, set[int]]:
	"""Return producer-delete and support-dependency edges for one guard block."""

	facts = tuple(goal_facts or ())
	schemas = tuple(action_schemas or ())
	threat_edges: dict[int, set[int]] = {index: set() for index in range(len(facts))}
	if len(facts) < 2 or not schemas:
		return threat_edges
	for achiever_index, achiever in enumerate(facts):
		threats = _possible_delete_patterns_for_goal(
			_lifted_atom_from_fact(achiever),
			action_schemas=schemas,
			depth=closure_depth,
		)
		for protected_index, protected in enumerate(facts):
			if achiever_index == protected_index:
				continue
			protected_atom = _lifted_atom_from_fact(protected)
			if any(_lifted_atom_unifies(threat, protected_atom) for threat in threats):
				threat_edges[achiever_index].add(protected_index)
	for source, target in _same_predicate_argument_dependency_edges(facts):
		threat_edges[source].add(target)
	return threat_edges


def _same_predicate_argument_dependency_edges(
	facts: Sequence[PDDLFact],
) -> tuple[tuple[int, int], ...]:
	"""Infer support-style ordering from repeated predicate argument sharing."""

	edges: list[tuple[int, int]] = []
	for source_index, source in enumerate(facts):
		source_arguments = tuple(sanitize_identifier(argument) for argument in source.args)
		if len(source_arguments) < 2:
			continue
		for target_index, target in enumerate(facts):
			if source_index == target_index or source.predicate != target.predicate:
				continue
			target_arguments = tuple(sanitize_identifier(argument) for argument in target.args)
			if len(target_arguments) != len(source_arguments):
				continue
			if source_arguments[0] in target_arguments[1:]:
				edges.append((source_index, target_index))
	return tuple(dict.fromkeys(edges))


def _lifted_atom_from_fact(fact: PDDLFact) -> _LiftedAtom:
	return _LiftedAtom(
		predicate=sanitize_identifier(fact.predicate),
		arguments=tuple(
			_LiftedTerm(sanitize_identifier(argument))
			for argument in fact.args
		),
	)


def _possible_delete_patterns_for_goal(
	goal: _LiftedAtom,
	*,
	action_schemas: Sequence[RuntimeActionSchema],
	depth: int,
	_seen: frozenset[tuple[str, tuple[str, ...]]] = frozenset(),
) -> tuple[_LiftedAtom, ...]:
	if depth <= 0:
		return ()
	key = (
		goal.predicate,
		tuple("*" if argument.is_variable else argument.symbol for argument in goal.arguments),
	)
	if key in _seen:
		return ()
	next_seen = frozenset((*_seen, key))
	deletes: list[_LiftedAtom] = []
	for action in tuple(action_schemas or ()):
		action_parameters = frozenset(action.parameters)
		for effect in _positive_patterns(action.effects):
			binding = _unify_action_effect_with_goal(
				effect=effect,
				action_parameters=action_parameters,
				goal=goal,
			)
			if binding is None:
				continue
			for delete_effect in _negative_patterns(action.effects):
				deletes.append(
					_map_runtime_pattern(
						delete_effect,
						binding=binding,
						action_parameters=action_parameters,
					),
				)
			for precondition in _positive_patterns(action.preconditions):
				mapped_precondition = _map_runtime_pattern(
					precondition,
					binding=binding,
					action_parameters=action_parameters,
				)
				if not _has_producer_for_pattern(mapped_precondition, action_schemas):
					continue
				deletes.extend(
					_possible_delete_patterns_for_goal(
						mapped_precondition,
						action_schemas=action_schemas,
						depth=depth - 1,
						_seen=next_seen,
					),
				)
	return tuple(dict.fromkeys(deletes))


def _positive_patterns(patterns: Sequence[PredicatePattern]) -> tuple[PredicatePattern, ...]:
	return tuple(pattern for pattern in tuple(patterns or ()) if pattern.positive)


def _negative_patterns(patterns: Sequence[PredicatePattern]) -> tuple[PredicatePattern, ...]:
	return tuple(pattern for pattern in tuple(patterns or ()) if not pattern.positive)


def _has_producer_for_pattern(
	target: _LiftedAtom,
	action_schemas: Sequence[RuntimeActionSchema],
) -> bool:
	return any(
		_unify_action_effect_with_goal(
			effect=effect,
			action_parameters=frozenset(action.parameters),
			goal=target,
		)
		is not None
		for action in tuple(action_schemas or ())
		for effect in _positive_patterns(action.effects)
	)


def _unify_action_effect_with_goal(
	*,
	effect: PredicatePattern,
	action_parameters: frozenset[str],
	goal: _LiftedAtom,
) -> dict[str, _LiftedTerm] | None:
	if effect.predicate != goal.predicate or len(effect.args) != len(goal.arguments):
		return None
	binding: dict[str, _LiftedTerm] = {}
	for effect_argument, goal_argument in zip(effect.args, goal.arguments):
		if effect_argument in action_parameters:
			previous = binding.get(effect_argument)
			if previous is not None and previous != goal_argument:
				return None
			binding[effect_argument] = goal_argument
			continue
		if goal_argument.is_variable:
			continue
		if effect_argument != goal_argument.symbol:
			return None
	variable_scope = object()
	for parameter in action_parameters:
		binding.setdefault(
			parameter,
			_LiftedTerm(parameter, variable_scope=variable_scope),
		)
	return binding


def _map_runtime_pattern(
	pattern: PredicatePattern,
	*,
	binding: Mapping[str, _LiftedTerm],
	action_parameters: frozenset[str],
) -> _LiftedAtom:
	arguments = tuple(
		binding[argument]
		if argument in action_parameters
		else _LiftedTerm(argument)
		for argument in pattern.args
	)
	return _LiftedAtom(
		predicate=pattern.predicate,
		arguments=arguments,
	)


def _lifted_atom_unifies(left: _LiftedAtom, right: _LiftedAtom) -> bool:
	if left.predicate != right.predicate or len(left.arguments) != len(right.arguments):
		return False
	bindings: dict[_LiftedTerm, _LiftedTerm] = {}
	for left_argument, right_argument in zip(left.arguments, right.arguments):
		left_argument = _resolve_lifted_term(left_argument, bindings)
		right_argument = _resolve_lifted_term(right_argument, bindings)
		if left_argument == right_argument:
			continue
		if left_argument.is_variable:
			bindings[left_argument] = right_argument
			continue
		if right_argument.is_variable:
			bindings[right_argument] = left_argument
			continue
		return False
	return True


def _resolve_lifted_term(
	term: _LiftedTerm,
	bindings: Mapping[_LiftedTerm, _LiftedTerm],
) -> _LiftedTerm:
	resolved = term
	seen: set[_LiftedTerm] = set()
	while resolved.is_variable and resolved in bindings and resolved not in seen:
		seen.add(resolved)
		resolved = bindings[resolved]
	return resolved


def _stable_topological_goal_order(
	facts: Sequence[PDDLFact],
	edges: Mapping[int, set[int]],
) -> tuple[PDDLFact, ...]:
	"""Return a stable topological order, or parser order when threats cycle."""

	remaining = set(range(len(facts)))
	incoming = {
		index: {
			source
			for source, targets in edges.items()
			if index in targets and source != index
		}
		for index in remaining
	}
	order: list[int] = []
	while remaining:
		ready = [index for index in sorted(remaining) if not incoming[index] & remaining]
		if not ready:
			return tuple(facts)
		chosen = ready[0]
		order.append(chosen)
		remaining.remove(chosen)
	return tuple(facts[index] for index in order)


def render_runtime_asl_for_task(task: JasonTask, *, problem: Any | None = None) -> str:
	"""Render the per-test ASL with the same wrapper shape as the long library."""

	if task.runtime_wrapper_text is None:
		wrapper_lines, _ = full_test_wrapper_lines(
			domain=task.domain,
			index=task.index,
			problem_file=task.problem_file,
			compact_completion_wrappers=task.compact_completion_wrappers,
			problem=problem,
			domain_file=task.domain_file,
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
	results_jsonl = run_root / "validation_results.jsonl"
	summary["validation_results_jsonl"] = str(results_jsonl)
	records: list[dict[str, Any]] = []
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
			for task in tasks
		}
		for future in as_completed(future_map):
			record = future.result()
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
	return sorted(records, key=lambda item: (str(item["domain"]), int(item["test_index"])))


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
	task.output_dir.mkdir(parents=True, exist_ok=True)
	try:
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
			"problem_file": str(task.problem_file),
			"goal_name": task.goal_name,
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
		record = {
			"domain": task.domain,
			"test_index": task.index,
			"problem_file": str(task.problem_file),
			"goal_name": task.goal_name,
			"success": False,
			"status": "exception",
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
