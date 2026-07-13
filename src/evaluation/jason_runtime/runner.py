"""Run current PDDL-only AgentSpeak(L) libraries in the Jason interpreter."""

from __future__ import annotations

import json
import os
import re
import shutil
import shlex
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from domain_level_planning.pddl_types import obj_tp_atoms
from domain_level_planning.pddl_types import parameter_name
from domain_level_planning.temporal_goal_appender import dfa_monitor_accepting_belief
from domain_level_planning.temporal_goal_appender import dfa_monitor_state_belief
from plan_library.rendering import sanitize_identifier
from utils.pddl_parser import PDDLAction
from utils.pddl_parser import PDDLNumericAssignment
from utils.pddl_parser import PDDLNumericCondition
from utils.pddl_parser import PDDLNumericEffect
from utils.pddl_parser import PDDLNumericExpression
from utils.pddl_parser import PDDLNumericFluent
from utils.pddl_parser import PDDLParser

from .environment_adapter import Stage6EnvironmentAdapter
from .environment_adapter import build_environment_adapter


_RUNTIME_OUTPUT_EXCERPT_MAX_CHARS = 20_000
_RUNTIME_ACTION_PATH_MAX_ITEMS = 3
_PLAN_VERIFIER_OUTPUT_EXCERPT_MAX_CHARS = 20_000
_DEFAULT_PLAN_VERIFIER_TIMEOUT_SECONDS = 1800
_DEFAULT_JASON_JAVA_STACK_SIZE = "64m"
_ACTION_SUCCESS_MARKER = "runtime env action success "
_ACTION_COUNT_MARKER = "runtime env action count "
_ADAPTER_MARKERS = (
	"runtime env ready",
	"runtime env action failed",
	"runtime env unknown action",
	"runtime env compile failed",
	"execute success",
)
_PLAN_VERIFIER_SUCCESS_MARKERS = (
	"plan valid",
	"successful plans: 1",
	"plan executed successfully",
)
_PLAN_VERIFIER_FAILURE_MARKERS = (
	"plan invalid",
	"plan failed",
	"failed plans",
	"not valid",
	"goal not satisfied",
	"precondition not satisfied",
	"precondition failed",
	"violated precondition",
	"unsuccessful",
)


class JasonValidationError(RuntimeError):
	"""Raised when Jason runtime validation cannot be completed."""

	def __init__(self, message: str, *, metadata: Mapping[str, Any] | None = None) -> None:
		super().__init__(message)
		self.metadata = dict(metadata or {})


@dataclass(frozen=True)
class JasonValidationResult:
	"""Structured result for one real Jason validation run."""

	success: bool
	status: str
	domain_name: str
	goal_name: str
	exit_code: int | None
	timed_out: bool
	stdout: str
	stderr: str
	action_path: tuple[str, ...]
	action_count: int
	environment_adapter: dict[str, Any]
	plan_verifier: dict[str, Any]
	artifacts: dict[str, str]
	timing_profile: dict[str, float]
	output_summary: dict[str, Any]
	error: str | None = None

	def to_dict(self) -> dict[str, Any]:
		payload: dict[str, Any] = {
			"success": self.success,
			"status": self.status,
			"domain_name": self.domain_name,
			"goal_name": self.goal_name,
			"exit_code": self.exit_code,
			"timed_out": self.timed_out,
			"stdout": self.stdout,
			"stderr": self.stderr,
			"action_path": list(self.action_path),
			"action_count": self.action_count,
			"environment_adapter": dict(self.environment_adapter),
			"plan_verifier": dict(self.plan_verifier),
			"artifacts": dict(self.artifacts),
			"timing_profile": dict(self.timing_profile),
			"output_summary": dict(self.output_summary),
		}
		if self.error is not None:
			payload["error"] = self.error
		return payload


@dataclass(frozen=True)
class PredicatePattern:
	"""A grounded-at-runtime PDDL literal pattern."""

	predicate: str
	args: tuple[str, ...] = ()
	positive: bool = True


@dataclass(frozen=True)
class RuntimeNumericTerm:
	"""Numeric term lowered to the Jason Java environment."""

	kind: str
	value: str
	args: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimeNumericCondition:
	"""Runtime numeric comparison for action applicability."""

	comparator: str
	left: RuntimeNumericTerm
	right: RuntimeNumericTerm


@dataclass(frozen=True)
class RuntimeNumericEffect:
	"""Runtime numeric increase/decrease update."""

	operator: str
	function: str
	args: tuple[str, ...]
	amount: RuntimeNumericTerm


@dataclass(frozen=True)
class RuntimeActionSchema:
	"""PDDL action schema lowered to the Jason Java environment."""

	functor: str
	source_name: str
	parameters: tuple[str, ...]
	preconditions: tuple[PredicatePattern, ...]
	effects: tuple[PredicatePattern, ...]
	numeric_preconditions: tuple[RuntimeNumericCondition, ...] = ()
	numeric_effects: tuple[RuntimeNumericEffect, ...] = ()


@dataclass(frozen=True)
class StreamedProcessResult:
	"""Result for a subprocess whose stdout/stderr were streamed to files."""

	exit_code: int | None
	timed_out: bool


@dataclass(frozen=True)
class PlanVerifierResult:
	"""Result for validating an exported PDDL plan trace with VAL or an IPC verifier."""

	attempted: bool
	available: bool
	success: bool | None
	command: tuple[str, ...]
	exit_code: int | None
	timed_out: bool
	stdout: str
	stderr: str
	artifacts: dict[str, str]
	error: str | None = None

	def to_dict(self) -> dict[str, Any]:
		payload: dict[str, Any] = {
			"attempted": self.attempted,
			"available": self.available,
			"success": self.success,
			"command": list(self.command),
			"exit_code": self.exit_code,
			"timed_out": self.timed_out,
			"stdout": self.stdout,
			"stderr": self.stderr,
			"artifacts": dict(self.artifacts),
		}
		if self.error is not None:
			payload["error"] = self.error
		return payload


@dataclass(frozen=True)
class RuntimeProblemArtifacts:
	"""Parsed PDDL and derived runtime facts for one Jason validation task."""

	domain: Any
	problem: Any
	seed_facts: tuple[str, ...]
	action_schemas: tuple[RuntimeActionSchema, ...]
	initial_percepts: tuple[str, ...]
	static_beliefs: tuple[str, ...]
	pddl_symbol_map: str
	build_seconds: float = 0.0


@dataclass(frozen=True)
class RuntimeOutputSummary:
	"""Bounded in-memory summary of a Jason stdout/stderr artifact pair."""

	stdout_excerpt: str
	stderr_excerpt: str
	marker_output: str
	action_path: tuple[str, ...]
	action_count: int
	action_path_truncated: bool
	stdout_truncated: bool
	stderr_truncated: bool
	has_execute_success: bool

	def to_dict(self) -> dict[str, Any]:
		return {
			"action_count": self.action_count,
			"action_path_truncated": self.action_path_truncated,
			"stdout_truncated": self.stdout_truncated,
			"stderr_truncated": self.stderr_truncated,
			"has_execute_success": self.has_execute_success,
		}


@dataclass(frozen=True)
class _SingleOutputScan:
	"""Bounded scan result for one output stream file."""

	excerpt: str
	marker_lines: tuple[str, ...]
	action_path: tuple[str, ...]
	action_count: int
	truncated: bool
	action_path_truncated: bool
	has_execute_success: bool


class JasonPlanLibraryRunner:
	"""Materialize and execute a generated library against a PDDL problem in Jason."""

	environment_class_name = "JasonPipelineEnvironment"
	default_jason_maven_artifact = "io.github.jason-lang:jason:3.1.2"

	def __init__(
		self,
		*,
		timeout_seconds: int = 1800,
		environment_adapter: Stage6EnvironmentAdapter | None = None,
		jason_classpath: str | None = None,
		compiled_environment_dir: str | Path | None = None,
		jason_java_stack_size: str | None = None,
		action_trace_limit: int = 3,
		plan_verifier_command: Sequence[str] | str | None = None,
		require_plan_verifier: bool = False,
		plan_verifier_timeout_seconds: int = _DEFAULT_PLAN_VERIFIER_TIMEOUT_SECONDS,
	) -> None:
		self.timeout_seconds = timeout_seconds
		self.environment_adapter = environment_adapter or build_environment_adapter()
		self.jason_classpath = jason_classpath
		self.compiled_environment_dir = (
			Path(compiled_environment_dir).expanduser().resolve()
			if compiled_environment_dir is not None
			else None
		)
		self.jason_java_stack_size = jason_java_stack_size
		self.action_trace_limit = max(0, int(action_trace_limit))
		self.plan_verifier_command = _normalize_plan_verifier_command(
			plan_verifier_command,
		)
		self.require_plan_verifier = require_plan_verifier
		self.plan_verifier_timeout_seconds = max(1, int(plan_verifier_timeout_seconds))

	def validate(
		self,
		*,
		domain_file: str | Path,
		problem_file: str | Path,
		plan_library_asl: str | Path,
		goal_name: str,
		output_dir: str | Path,
		plan_library_asl_text: str | None = None,
		runtime_artifacts: RuntimeProblemArtifacts | None = None,
		temporal_dfa_payload: Mapping[str, Any] | None = None,
	) -> JasonValidationResult:
		"""Run one canonical AgentSpeak(L) library with real Jason action semantics."""

		total_start = time.perf_counter()
		timing_profile: dict[str, float] = {}
		domain_path = Path(domain_file).expanduser().resolve()
		problem_path = Path(problem_file).expanduser().resolve()
		library_path = Path(plan_library_asl).expanduser().resolve()
		output_path = Path(output_dir).expanduser().resolve()
		output_path.mkdir(parents=True, exist_ok=True)

		parse_start = time.perf_counter()
		artifacts = runtime_artifacts or build_runtime_problem_artifacts(
			domain_file=domain_path,
			problem_file=problem_path,
		)
		domain = artifacts.domain
		action_schemas = artifacts.action_schemas
		initial_percepts = artifacts.initial_percepts
		static_beliefs = artifacts.static_beliefs
		monitor_initial_beliefs = (
			_temporal_monitor_initial_beliefs(
				temporal_dfa_payload,
				goal_name=goal_name,
				initial_facts=artifacts.seed_facts,
			)
			if temporal_dfa_payload is not None
			else ()
		)
		timing_profile["parse_seconds"] = (
			artifacts.build_seconds
			if runtime_artifacts is not None
			else time.perf_counter() - parse_start
		)

		if not action_schemas:
			raise JasonValidationError(
				"Jason validation requires at least one PDDL action schema.",
				metadata={"domain_file": str(domain_path)},
			)

		resolve_start = time.perf_counter()
		java_bin = shutil.which("java")
		javac_bin = shutil.which("javac")
		compiled_environment_dir = self.compiled_environment_dir
		if not java_bin or (not javac_bin and compiled_environment_dir is None):
			raise JasonValidationError(
				"Jason validation requires java and, without a precompiled environment, javac.",
				metadata={"java": java_bin, "javac": javac_bin},
			)
		classpath = self.jason_classpath or _resolve_jason_classpath(
			self.default_jason_maven_artifact,
		)
		timing_profile["runtime_resolution_seconds"] = time.perf_counter() - resolve_start

		materialize_start = time.perf_counter()
		runner_asl = _build_runner_asl(
			plan_library_asl=(
				plan_library_asl_text
				if plan_library_asl_text is not None
				else library_path.read_text(encoding="utf-8")
			),
			goal_name=goal_name,
		)
		runner_mas2j = _build_runner_mas2j(domain.name)
		logging_properties = _logging_properties()

		agentspeak_path = output_path / "agentspeak_generated.asl"
		mas2j_path = output_path / "jason_runner.mas2j"
		if compiled_environment_dir is None:
			environment_java_path = output_path / f"{self.environment_class_name}.java"
			belief_base_java_path = output_path / "JasonPipelineIndexedBeliefBase.java"
		else:
			environment_java_path = (
				compiled_environment_dir / f"{self.environment_class_name}.java"
			)
			belief_base_java_path = (
				compiled_environment_dir / "JasonPipelineIndexedBeliefBase.java"
			)
		initial_facts_path = output_path / "initial_facts.txt"
		initial_percepts_path = output_path / "initial_percepts.txt"
		static_beliefs_path = output_path / "static_beliefs.txt"
		pddl_symbol_map_path = output_path / "pddl_symbol_map.tsv"
		temporal_monitor_path = output_path / "temporal_dfa_monitor.tsv"
		logging_path = output_path / "logging.properties"
		stdout_path = output_path / "jason_stdout.txt"
		stderr_path = output_path / "jason_stderr.txt"
		plan_trace_path = output_path / "jason_plan.plan"
		committed_plan_trace_path = output_path / "committed_plan.plan"
		plan_verifier_stdout_path = output_path / "plan_verifier_stdout.txt"
		plan_verifier_stderr_path = output_path / "plan_verifier_stderr.txt"
		result_path = output_path / "jason_validation.json"

		agentspeak_path.write_text(runner_asl, encoding="utf-8")
		mas2j_path.write_text(runner_mas2j, encoding="utf-8")
		if compiled_environment_dir is None:
			environment_java = _build_environment_java_source(
				class_name=self.environment_class_name,
				action_schemas=action_schemas,
				seed_facts_file_name=initial_facts_path.name,
				initial_percepts_file_name=initial_percepts_path.name,
				plan_trace_file_name=plan_trace_path.name,
				pddl_symbol_map_file_name=pddl_symbol_map_path.name,
			)
			environment_java_path.write_text(environment_java, encoding="utf-8")
			belief_base_java_path.write_text(
				_build_indexed_belief_base_java_source(),
				encoding="utf-8",
			)
		initial_facts_path.write_text(
			"# Deprecated duplicate runtime seed file omitted.\n"
			"# Reconstruct initial facts as initial_percepts.txt + static_beliefs.txt.\n",
			encoding="utf-8",
		)
		initial_percepts_path.write_text(
			"\n".join((*initial_percepts, *monitor_initial_beliefs))
			+ ("\n" if initial_percepts or monitor_initial_beliefs else ""),
			encoding="utf-8",
		)
		static_beliefs_path.write_text(
			"\n".join(static_beliefs) + ("\n" if static_beliefs else ""),
			encoding="utf-8",
		)
		pddl_symbol_map_path.write_text(
			artifacts.pddl_symbol_map,
			encoding="utf-8",
		)
		temporal_monitor_path.write_text(
			_render_temporal_monitor_config(
				temporal_dfa_payload,
				goal_name=goal_name,
				initial_facts=artifacts.seed_facts,
			)
			if temporal_dfa_payload is not None
			else "",
			encoding="utf-8",
		)
		plan_trace_path.write_text("", encoding="utf-8")
		logging_path.write_text(logging_properties, encoding="utf-8")
		timing_profile["materialize_seconds"] = time.perf_counter() - materialize_start

		if compiled_environment_dir is None:
			if javac_bin is None:
				raise JasonValidationError("Jason validation requires javac on PATH.")
			compile_start = time.perf_counter()
			compile_process = subprocess.run(
				[
					javac_bin,
					"-cp",
					classpath,
					environment_java_path.name,
					belief_base_java_path.name,
				],
				cwd=output_path,
				text=True,
				capture_output=True,
				check=False,
			)
			timing_profile["compile_seconds"] = time.perf_counter() - compile_start
			if compile_process.returncode != 0:
				error = "Jason environment Java compilation failed."
				stdout_path.write_text(compile_process.stdout, encoding="utf-8")
				stderr_path.write_text(compile_process.stderr, encoding="utf-8")
				result = JasonValidationResult(
					success=False,
					status="compile_failed",
					domain_name=domain.name,
					goal_name=goal_name,
					exit_code=compile_process.returncode,
					timed_out=False,
					stdout=compile_process.stdout,
					stderr=compile_process.stderr,
					action_path=(),
					action_count=0,
					environment_adapter=self.environment_adapter.validate(
						stdout=compile_process.stdout,
						stderr=compile_process.stderr,
					).to_dict(),
					plan_verifier=_plan_verifier_not_attempted(
						stdout_path=plan_verifier_stdout_path,
						stderr_path=plan_verifier_stderr_path,
					).to_dict(),
					artifacts=_artifact_paths(
						agentspeak_path=agentspeak_path,
						mas2j_path=mas2j_path,
						environment_java_path=environment_java_path,
						belief_base_java_path=belief_base_java_path,
						initial_facts_path=initial_facts_path,
						initial_percepts_path=initial_percepts_path,
						static_beliefs_path=static_beliefs_path,
						pddl_symbol_map_path=pddl_symbol_map_path,
						temporal_monitor_path=temporal_monitor_path,
						plan_trace_path=plan_trace_path,
						committed_plan_trace_path=committed_plan_trace_path,
						plan_verifier_stdout_path=plan_verifier_stdout_path,
						plan_verifier_stderr_path=plan_verifier_stderr_path,
						stdout_path=stdout_path,
						stderr_path=stderr_path,
						result_path=result_path,
					),
					timing_profile=timing_profile,
					output_summary=_empty_runtime_output_summary().to_dict(),
					error=error,
				)
				result_path.write_text(
					json.dumps(result.to_dict(), indent=2) + "\n",
					encoding="utf-8",
				)
				return result
		else:
			class_file = compiled_environment_dir / f"{self.environment_class_name}.class"
			if not class_file.exists():
				raise JasonValidationError(
					"Compiled Jason environment class is missing.",
					metadata={
						"compiled_environment_dir": str(compiled_environment_dir),
						"class_file": str(class_file),
					},
				)
			belief_base_class_file = (
				compiled_environment_dir / "JasonPipelineIndexedBeliefBase.class"
			)
			if not belief_base_class_file.exists():
				raise JasonValidationError(
					"Compiled Jason indexed belief base class is missing.",
					metadata={
						"compiled_environment_dir": str(compiled_environment_dir),
						"class_file": str(belief_base_class_file),
					},
				)
			timing_profile["compile_seconds"] = 0.0

		run_start = time.perf_counter()
		run_classpath_items = [classpath]
		if compiled_environment_dir is not None:
			run_classpath_items.append(str(compiled_environment_dir))
		run_classpath_items.append(str(output_path))
		run_classpath = os.pathsep.join(run_classpath_items)
		cmd = [
			java_bin,
			_jason_java_stack_option(self.jason_java_stack_size),
			"-Djava.awt.headless=true",
			f"-Djason.pipeline.actionTraceLimit={self.action_trace_limit}",
			"-Djason.pipeline.actionTraceInterval=0",
			"-Djason.pipeline.planTraceEnabled=true",
			f"-Djava.util.logging.config.file={logging_path}",
			"-cp",
			run_classpath,
			"jason.infra.local.RunLocalMAS",
			mas2j_path.name,
		]
		timed_out = False
		run_process = _run_process_streamed(
			cmd,
			cwd=output_path,
			stdout_path=stdout_path,
			stderr_path=stderr_path,
			timeout_seconds=self.timeout_seconds,
		)
		exit_code = run_process.exit_code
		timed_out = run_process.timed_out
		timing_profile["run_seconds"] = time.perf_counter() - run_start
		timing_profile["total_seconds"] = time.perf_counter() - total_start

		output_summary = _scan_runtime_output_files(
			stdout_path=stdout_path,
			stderr_path=stderr_path,
		)
		adapter_result = self.environment_adapter.validate(
			stdout=output_summary.marker_output,
			stderr="",
		)
		jason_success = (
			not timed_out
			and exit_code == 0
			and adapter_result.success
			and output_summary.has_execute_success
		)
		plan_verifier_result = _plan_verifier_not_attempted(
			stdout_path=plan_verifier_stdout_path,
			stderr_path=plan_verifier_stderr_path,
		)
		status = "success" if jason_success else "failed"
		error_message = None
		if timed_out:
			status = "timeout"
			error_message = f"Jason validation exceeded {self.timeout_seconds} seconds."
		elif exit_code != 0:
			error_message = f"Jason process exited with code {exit_code}."
		elif not adapter_result.success:
			error_message = adapter_result.error
		elif not output_summary.has_execute_success:
			error_message = "Jason process did not report execute success."
		elif jason_success:
			shutil.copyfile(plan_trace_path, committed_plan_trace_path)
			verifier_start = time.perf_counter()
			plan_verifier_result = _run_plan_verifier(
				explicit_command=self.plan_verifier_command,
				require_verifier=self.require_plan_verifier,
				domain_file=domain_path,
				problem_file=problem_path,
				plan_file=committed_plan_trace_path,
				output_dir=output_path,
				stdout_path=plan_verifier_stdout_path,
				stderr_path=plan_verifier_stderr_path,
				timeout_seconds=self.plan_verifier_timeout_seconds,
			)
			timing_profile["plan_verifier_seconds"] = (
				time.perf_counter() - verifier_start
			)
			if self.require_plan_verifier:
				if not plan_verifier_result.available:
					status = "plan_verifier_unavailable"
					error_message = plan_verifier_result.error
				elif plan_verifier_result.timed_out:
					status = "plan_verifier_timeout"
					error_message = plan_verifier_result.error
				elif plan_verifier_result.success is not True:
					status = "plan_verifier_failed"
					error_message = plan_verifier_result.error
		success = jason_success and (
			not self.require_plan_verifier or plan_verifier_result.success is True
		)

		result = JasonValidationResult(
			success=success,
			status=status,
			domain_name=domain.name,
			goal_name=goal_name,
			exit_code=exit_code,
			timed_out=timed_out,
			stdout=output_summary.stdout_excerpt,
			stderr=output_summary.stderr_excerpt,
			action_path=output_summary.action_path,
			action_count=output_summary.action_count,
			environment_adapter=adapter_result.to_dict(),
			plan_verifier=plan_verifier_result.to_dict(),
			artifacts=_artifact_paths(
				agentspeak_path=agentspeak_path,
				mas2j_path=mas2j_path,
				environment_java_path=environment_java_path,
				belief_base_java_path=belief_base_java_path,
				initial_facts_path=initial_facts_path,
				initial_percepts_path=initial_percepts_path,
				static_beliefs_path=static_beliefs_path,
				pddl_symbol_map_path=pddl_symbol_map_path,
				temporal_monitor_path=temporal_monitor_path,
				plan_trace_path=plan_trace_path,
				committed_plan_trace_path=committed_plan_trace_path,
				plan_verifier_stdout_path=plan_verifier_stdout_path,
				plan_verifier_stderr_path=plan_verifier_stderr_path,
				stdout_path=stdout_path,
				stderr_path=stderr_path,
				result_path=result_path,
			),
			timing_profile=timing_profile,
			output_summary=output_summary.to_dict(),
			error=error_message,
		)
		result_path.write_text(json.dumps(result.to_dict(), indent=2) + "\n", encoding="utf-8")
		return result


def build_runtime_problem_artifacts(
	*,
	domain_file: Path,
	problem_file: Path,
	domain: Any | None = None,
	problem: Any | None = None,
) -> RuntimeProblemArtifacts:
	"""Parse one PDDL task once and derive the facts needed by Jason."""

	start = time.perf_counter()
	domain_model = domain if domain is not None else PDDLParser.parse_domain(domain_file)
	problem_model = problem if problem is not None else PDDLParser.parse_problem(problem_file)
	action_schemas = tuple(
		_runtime_action_schema(action)
		for action in tuple(getattr(domain_model, "actions", ()) or ())
	)
	seed_facts = _seed_facts(domain=domain_model, problem=problem_model)
	initial_percepts, static_beliefs = _split_seed_facts_for_jason_runtime(
		seed_facts=seed_facts,
		action_schemas=action_schemas,
	)
	return RuntimeProblemArtifacts(
		domain=domain_model,
		problem=problem_model,
		seed_facts=seed_facts,
		action_schemas=action_schemas,
		initial_percepts=initial_percepts,
		static_beliefs=static_beliefs,
		pddl_symbol_map=_render_pddl_symbol_map(domain=domain_model, problem=problem_model),
		build_seconds=time.perf_counter() - start,
	)


def _seed_facts(
	*,
	domain_file: Path | None = None,
	problem_file: Path | None = None,
	domain: Any | None = None,
	problem: Any | None = None,
) -> tuple[str, ...]:
	if domain is None:
		if domain_file is None:
			raise ValueError("domain or domain_file is required")
		domain = PDDLParser.parse_domain(domain_file)
	if problem is None:
		if problem_file is None:
			raise ValueError("problem or problem_file is required")
		problem = PDDLParser.parse_problem(problem_file)
	facts = [
		_render_runtime_atom(_call(fact.predicate, fact.args))
		for fact in problem.init_facts
		if fact.is_positive
	]
	facts.extend(
		_numeric_assignment_fact(assignment)
		for assignment in tuple(getattr(problem, "numeric_init", ()) or ())
	)
	facts.extend(_render_runtime_atom(fact) for fact in obj_tp_atoms(problem, domain.types))
	return tuple(dict.fromkeys(facts))


def _split_seed_facts_for_jason_runtime(
	*,
	seed_facts: Sequence[str],
	action_schemas: Sequence[RuntimeActionSchema],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
	"""Split initial facts into dynamic percepts and read-only static beliefs."""

	dynamic_predicates = {
		pattern.predicate
		for schema in action_schemas
		for pattern in tuple(schema.effects or ())
	}
	dynamic_predicates.update(
		effect.function
		for schema in action_schemas
		for effect in tuple(getattr(schema, "numeric_effects", ()) or ())
	)
	initial_percepts: list[str] = []
	static_beliefs: list[str] = []
	for fact in tuple(seed_facts or ()):
		predicate = _runtime_fact_predicate(fact)
		if predicate in dynamic_predicates:
			initial_percepts.append(fact)
		else:
			static_beliefs.append(fact)
	return tuple(initial_percepts), tuple(static_beliefs)


def _numeric_assignment_fact(assignment: PDDLNumericAssignment) -> str:
	return _numeric_fluent_fact(
		fluent=assignment.fluent,
		value=assignment.value,
	)


def _numeric_fluent_fact(*, fluent: PDDLNumericFluent, value: int) -> str:
	args = tuple(_render_runtime_term(arg) for arg in tuple(fluent.args or ()))
	rendered_function = sanitize_identifier(fluent.function)
	rendered_args = (*args, str(int(value)))
	return f"{rendered_function}({','.join(rendered_args)})"


def _runtime_fact_predicate(fact: str) -> str:
	text = str(fact or "").strip()
	if "(" in text:
		return text.split("(", 1)[0].strip()
	return text


def _runtime_action_schema(action: PDDLAction) -> RuntimeActionSchema:
	return RuntimeActionSchema(
		functor=sanitize_identifier(action.name),
		source_name=action.name,
		parameters=tuple(
			sanitize_identifier(parameter_name(parameter).lstrip("?"))
			for parameter in tuple(action.parameters or ())
		),
		preconditions=tuple(_parse_pddl_patterns(action.preconditions)),
		effects=tuple(_parse_pddl_patterns(action.effects)),
		numeric_preconditions=tuple(
			_runtime_numeric_condition(condition)
			for condition in tuple(getattr(action, "numeric_preconditions", ()) or ())
		),
		numeric_effects=tuple(
			_runtime_numeric_effect(effect)
			for effect in tuple(getattr(action, "numeric_effects", ()) or ())
		),
	)


def _runtime_numeric_condition(
	condition: PDDLNumericCondition,
) -> RuntimeNumericCondition:
	return RuntimeNumericCondition(
		comparator=str(condition.comparator),
		left=_runtime_numeric_term(condition.left),
		right=_runtime_numeric_term(condition.right),
	)


def _runtime_numeric_effect(effect: PDDLNumericEffect) -> RuntimeNumericEffect:
	return RuntimeNumericEffect(
		operator=str(effect.operator),
		function=sanitize_identifier(effect.fluent.function),
		args=tuple(_render_runtime_term(argument) for argument in tuple(effect.fluent.args)),
		amount=_runtime_numeric_term(effect.amount),
	)


def _runtime_numeric_term(expression: PDDLNumericExpression) -> RuntimeNumericTerm:
	if expression.kind == "constant":
		return RuntimeNumericTerm(kind="constant", value=str(expression.value))
	return RuntimeNumericTerm(
		kind="fluent",
		value=sanitize_identifier(expression.value),
		args=tuple(_render_runtime_term(argument) for argument in tuple(expression.args)),
	)


def _render_pddl_symbol_map(*, domain: Any, problem: Any) -> str:
	"""Render a reversible map from Jason-safe symbols back to PDDL symbols."""

	symbols: list[str] = []
	symbols.extend(str(item) for item in tuple(getattr(problem, "objects", ()) or ()))
	symbols.extend(str(item) for item in tuple(getattr(domain, "constants", ()) or ()))
	for fact in tuple(getattr(problem, "init_facts", ()) or ()):
		symbols.extend(str(arg) for arg in tuple(getattr(fact, "args", ()) or ()))
	for fact in tuple(getattr(problem, "goal_facts", ()) or ()):
		symbols.extend(str(arg) for arg in tuple(getattr(fact, "args", ()) or ()))
	for assignment in tuple(getattr(problem, "numeric_init", ()) or ()):
		symbols.extend(str(arg) for arg in tuple(getattr(assignment.fluent, "args", ()) or ()))
	for condition in tuple(getattr(problem, "numeric_goal_conditions", ()) or ()):
		for expression in (condition.left, condition.right):
			if getattr(expression, "kind", "") == "fluent":
				symbols.extend(str(arg) for arg in tuple(getattr(expression, "args", ()) or ()))
	symbol_map: dict[str, str] = {}
	collisions: dict[str, set[str]] = {}
	for symbol in symbols:
		if not symbol:
			continue
		sanitized = sanitize_identifier(symbol)
		previous = symbol_map.setdefault(sanitized, symbol)
		if previous != symbol:
			collisions.setdefault(sanitized, {previous}).add(symbol)
	if collisions:
		raise JasonValidationError(
			"Cannot export an unambiguous PDDL plan trace because two PDDL symbols "
			"collapse to the same Jason-safe identifier.",
			metadata={
				"collisions": {
					key: sorted(values) for key, values in collisions.items()
				},
			},
		)
	return "".join(
		f"{sanitized}\t{source}\n"
		for sanitized, source in sorted(symbol_map.items())
	)


def _parse_pddl_patterns(expression: str) -> tuple[PredicatePattern, ...]:
	parsed = _parse_pddl_expression(expression)
	if parsed is None:
		return ()
	return tuple(_flatten_pddl_literals(parsed))


def _parse_pddl_expression(expression: str) -> Any:
	text = str(expression or "").strip()
	if not text:
		return None
	tokens = re.findall(r"\(|\)|[^\s()]+", text)
	position = 0

	def parse_one() -> Any:
		nonlocal position
		if position >= len(tokens):
			return None
		token = tokens[position]
		position += 1
		if token != "(":
			return token
		items: list[Any] = []
		while position < len(tokens) and tokens[position] != ")":
			items.append(parse_one())
		if position >= len(tokens):
			raise JasonValidationError(
				"Unmatched parenthesis while parsing PDDL expression.",
				metadata={"expression": expression},
			)
		position += 1
		return items

	return parse_one()


def _flatten_pddl_literals(node: Any, *, positive: bool = True) -> Iterable[PredicatePattern]:
	if node is None:
		return ()
	if isinstance(node, str):
		if node.lower() == "and":
			return ()
		return (PredicatePattern(predicate=sanitize_identifier(node), positive=positive),)
	if not isinstance(node, Sequence) or isinstance(node, (bytes, bytearray)):
		return ()
	items = list(node)
	if not items:
		return ()
	head = str(items[0]).lower()
	if head == "and":
		patterns: list[PredicatePattern] = []
		for child in items[1:]:
			patterns.extend(_flatten_pddl_literals(child, positive=positive))
		return tuple(patterns)
	if head == "not" and len(items) == 2:
		return tuple(_flatten_pddl_literals(items[1], positive=not positive))
	if head in {">", ">=", "<", "<=", "=", "increase", "decrease", "assign", "scale-up", "scale-down"}:
		return ()
	predicate = sanitize_identifier(str(items[0]))
	args = tuple(_render_runtime_term(str(item)) for item in items[1:])
	return (PredicatePattern(predicate=predicate, args=args, positive=positive),)


def _render_runtime_atom(atom: str) -> str:
	text = str(atom or "").strip()
	if "(" not in text:
		return sanitize_identifier(text)
	if not text.endswith(")"):
		return sanitize_identifier(text)
	predicate, raw_args = text.split("(", 1)
	args = [
		_render_runtime_term(argument.strip())
		for argument in raw_args[:-1].split(",")
		if argument.strip()
	]
	return _call(sanitize_identifier(predicate), args)


def _render_runtime_term(term: str) -> str:
	text = str(term or "").strip()
	if text.startswith("?"):
		text = text[1:]
	return sanitize_identifier(text)


def _call(predicate: str, args: Sequence[str]) -> str:
	rendered_predicate = sanitize_identifier(predicate)
	rendered_args = tuple(_render_runtime_term(arg) for arg in tuple(args or ()))
	if not rendered_args:
		return rendered_predicate
	return f"{rendered_predicate}({','.join(rendered_args)})"


def _build_runner_asl(*, plan_library_asl: str, goal_name: str) -> str:
	goal = sanitize_identifier(goal_name)
	return "\n".join(
		(
			plan_library_asl.rstrip(),
			"",
			"/* Jason Validation Entry */",
			"!execute.",
			"",
			"+!execute : true <-",
			'\t.print("execute start");',
			f"\t!{goal};",
			"\truntime_summary;",
			'\t.print("execute success");',
			"\t.stopMAS.",
			"",
			"-!execute : true <-",
			'\t.print("execute failed");',
			"\t.stopMAS.",
			"",
		),
	)


def _build_runner_mas2j(domain_name: str) -> str:
	sanitized_domain = sanitize_identifier(domain_name)
	return (
		f"MAS validate_{sanitized_domain} {{\n"
		f"    environment: {JasonPlanLibraryRunner.environment_class_name}\n"
		"    agents: agentspeak_generated beliefBaseClass JasonPipelineIndexedBeliefBase;\n"
		"    aslSourcePath: \".\";\n"
		"}\n"
	)


def _build_indexed_belief_base_java_source() -> str:
	"""Return a Jason belief base with argument-position indexes for PDDL facts."""

	return r"""
import jason.asSemantics.Agent;
import jason.asSemantics.Unifier;
import jason.asSyntax.Literal;
import jason.asSyntax.PredicateIndicator;
import jason.asSyntax.Term;
import jason.bb.DefaultBeliefBase;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class JasonPipelineIndexedBeliefBase extends DefaultBeliefBase {
	private static volatile JasonPipelineIndexedBeliefBase activeInstance;
	private final Map<String, Map<Integer, Map<String, LinkedHashSet<Literal>>>> dynamicIndex =
		new HashMap<>();
	private final Map<String, LinkedHashSet<Literal>> dynamicPredicateIndex = new HashMap<>();
	private final Map<String, LinkedHashSet<Literal>> dynamicExactIndex = new HashMap<>();
	private final Map<String, Map<Integer, Map<String, LinkedHashSet<Literal>>>> staticIndex =
		new HashMap<>();
	private final Map<String, LinkedHashSet<Literal>> staticPredicateIndex = new HashMap<>();
	private final Map<String, LinkedHashSet<Literal>> staticExactIndex = new HashMap<>();
	private final Path initialDynamicBeliefsPath = Paths.get("initial_percepts.txt");
	private final Path staticBeliefsPath = Paths.get("static_beliefs.txt");

	@Override
	public void init(Agent agent, String[] args) {
		super.init(agent, args);
		loadStaticBeliefs();
		loadInitialDynamicBeliefs();
		activeInstance = this;
	}

	public static void applyDynamicDelta(Set<String> removed, Set<String> added) {
		JasonPipelineIndexedBeliefBase instance = activeInstance;
		if (instance == null) {
			throw new IllegalStateException("Jason indexed belief base is not initialized");
		}
		synchronized (instance.getLock()) {
			for (String atom : removed) {
				instance.applyDynamicRemoval(atom);
			}
			for (String atom : added) {
				instance.applyDynamicAddition(atom);
			}
		}
	}

	@Override
	public boolean add(Literal literal) {
		boolean changed = super.add(literal);
		if (changed) {
			indexDynamicLiteral(literal);
		}
		return changed;
	}

	@Override
	public boolean add(int indexPosition, Literal literal) {
		boolean changed = super.add(indexPosition, literal);
		if (changed) {
			indexDynamicLiteral(literal);
		}
		return changed;
	}

	@Override
	public boolean remove(Literal literal) {
		boolean changed = super.remove(literal);
		deindexDynamicLiteral(literal);
		deindexStaticLiteral(literal);
		return changed;
	}

	@Override
	public void clear() {
		super.clear();
		dynamicIndex.clear();
		dynamicPredicateIndex.clear();
		dynamicExactIndex.clear();
		staticIndex.clear();
		staticPredicateIndex.clear();
		staticExactIndex.clear();
	}

	@Override
	public Literal contains(Literal literal) {
		LinkedHashSet<Literal> staticExactMatches = exactBucket(staticExactIndex, literal);
		if (staticExactMatches != null) {
			for (Literal candidate : staticExactMatches) {
				if (literal.hasSubsetAnnot(candidate)) {
					return candidate;
				}
			}
			return null;
		}
		LinkedHashSet<Literal> dynamicExactMatches = exactBucket(dynamicExactIndex, literal);
		if (dynamicExactMatches != null) {
			for (Literal candidate : dynamicExactMatches) {
				if (isLiveDynamicLiteral(candidate) && literal.hasSubsetAnnot(candidate)) {
					return candidate;
				}
			}
			return null;
		}
		return super.contains(literal);
	}

	@Override
	public Iterator<Literal> getPercepts() {
		return Collections.emptyIterator();
	}

	@Override
	public Iterator<Literal> getCandidateBeliefs(Literal literal, Unifier unifier) {
		if (literal == null || literal.isVar()) {
			return super.getCandidateBeliefs(literal, unifier);
		}
		List<Term> terms = literal.getTerms();
		if (terms == null || terms.isEmpty()) {
			return super.getCandidateBeliefs(literal, unifier);
		}
		String exactKey = exactKeyIfBound(literal, unifier);
		if (exactKey != null) {
			LinkedHashSet<Literal> staticExactMatches = staticExactIndex.get(exactKey);
			LinkedHashSet<Literal> dynamicExactMatches = dynamicExactIndex.get(exactKey);
			if (staticExactMatches == null && dynamicExactMatches == null) {
				return Collections.emptyIterator();
			}
			return candidateIterator(staticExactMatches, dynamicExactMatches);
		}
		LinkedHashSet<Literal> bestStaticBucket = null;
		LinkedHashSet<Literal> bestDynamicBucket = null;
		int bestBucketSize = Integer.MAX_VALUE;
		for (int position = 0; position < terms.size(); position++) {
			Term bound = boundTerm(terms.get(position), unifier);
			if (bound == null) {
				continue;
			}
			LinkedHashSet<Literal> staticBucket = bucketFor(
				staticIndex,
				literal.getPredicateIndicator(),
				position,
				bound.toString()
			);
			LinkedHashSet<Literal> dynamicBucket = bucketFor(
				dynamicIndex,
				literal.getPredicateIndicator(),
				position,
				bound.toString()
			);
			if (staticBucket == null && dynamicBucket == null) {
				return Collections.emptyIterator();
			}
			int bucketSize = bucketSize(staticBucket) + bucketSize(dynamicBucket);
			if (bucketSize < bestBucketSize) {
				bestStaticBucket = staticBucket;
				bestDynamicBucket = dynamicBucket;
				bestBucketSize = bucketSize;
			}
		}
		if (bestBucketSize == Integer.MAX_VALUE) {
			LinkedHashSet<Literal> staticPredicateMatches = staticPredicateIndex.get(
				predicateKey(literal.getPredicateIndicator())
			);
			LinkedHashSet<Literal> dynamicPredicateMatches = dynamicPredicateIndex.get(
				predicateKey(literal.getPredicateIndicator())
			);
			if (staticPredicateMatches == null && dynamicPredicateMatches == null) {
				return Collections.emptyIterator();
			}
			return candidateIterator(staticPredicateMatches, dynamicPredicateMatches);
		}
		return candidateIterator(bestStaticBucket, bestDynamicBucket);
	}

	@Override
	public Iterator<Literal> getCandidateBeliefs(PredicateIndicator indicator) {
		return super.getCandidateBeliefs(indicator);
	}

	@Override
	public JasonPipelineIndexedBeliefBase clone() {
		JasonPipelineIndexedBeliefBase clone = new JasonPipelineIndexedBeliefBase();
		Iterator<Literal> beliefs = iterator();
		while (beliefs != null && beliefs.hasNext()) {
			clone.add(beliefs.next().copy());
		}
		return clone;
	}

	private Term boundTerm(Term term, Unifier unifier) {
		if (term == null) {
			return null;
		}
		Term resolved = term;
		if (unifier != null && term.isVar()) {
			resolved = term.capply(unifier);
		}
		if (resolved == null || resolved.isVar()) {
			return null;
		}
		return resolved;
	}

	private void indexDynamicLiteral(Literal literal) {
		indexLiteral(literal, dynamicIndex, dynamicExactIndex);
	}

	private void applyDynamicRemoval(String atom) {
		if (atom == null || atom.isBlank()) {
			return;
		}
		Literal literal = Literal.parseLiteral(atom);
		if (super.remove(literal)) {
			deindexDynamicLiteral(literal);
		}
	}

	private void applyDynamicAddition(String atom) {
		if (atom == null || atom.isBlank()) {
			return;
		}
		Literal literal = Literal.parseLiteral(atom);
		if (super.add(literal)) {
			indexDynamicLiteral(literal);
		}
	}

	private void indexStaticLiteral(Literal literal) {
		indexLiteral(literal, staticIndex, staticExactIndex);
	}

	private void indexLiteral(
		Literal literal,
		Map<String, Map<Integer, Map<String, LinkedHashSet<Literal>>>> targetIndex,
		Map<String, LinkedHashSet<Literal>> targetExactIndex
	) {
		if (literal == null || literal.isRule()) {
			return;
		}
		List<Term> terms = literal.getTerms();
		String predicateKey = predicateKey(literal.getPredicateIndicator());
		predicateIndexFor(targetExactIndex)
			.computeIfAbsent(predicateKey, ignored -> new LinkedHashSet<>())
			.add(literal);
		String exactKey = exactKey(literal);
		if (exactKey != null) {
			targetExactIndex
				.computeIfAbsent(exactKey, ignored -> new LinkedHashSet<>())
				.add(literal);
		}
		if (terms == null || terms.isEmpty()) {
			return;
		}
		Map<Integer, Map<String, LinkedHashSet<Literal>>> byPosition =
			targetIndex.computeIfAbsent(predicateKey, ignored -> new HashMap<>());
		for (int position = 0; position < terms.size(); position++) {
			Term term = terms.get(position);
			if (term == null || term.isVar()) {
				continue;
			}
			byPosition
				.computeIfAbsent(position, ignored -> new LinkedHashMap<>())
				.computeIfAbsent(term.toString(), ignored -> new LinkedHashSet<>())
				.add(literal);
		}
	}

	private void deindexDynamicLiteral(Literal literal) {
		deindexLiteral(literal, dynamicIndex, dynamicExactIndex);
	}

	private void deindexStaticLiteral(Literal literal) {
		deindexLiteral(literal, staticIndex, staticExactIndex);
	}

	private void deindexLiteral(
		Literal literal,
		Map<String, Map<Integer, Map<String, LinkedHashSet<Literal>>>> targetIndex,
		Map<String, LinkedHashSet<Literal>> targetExactIndex
	) {
		if (literal == null || literal.isRule()) {
			return;
		}
		removeExactIndexLiteral(literal, targetExactIndex);
		removePredicateIndexLiteral(literal, predicateIndexFor(targetExactIndex));
		removeArgumentIndexLiteral(literal, targetIndex);
	}

	private Map<String, LinkedHashSet<Literal>> predicateIndexFor(
		Map<String, LinkedHashSet<Literal>> exactIndex
	) {
		if (exactIndex == dynamicExactIndex) {
			return dynamicPredicateIndex;
		}
		return staticPredicateIndex;
	}

	private void removePredicateIndexLiteral(
		Literal literal,
		Map<String, LinkedHashSet<Literal>> targetPredicateIndex
	) {
		String key = predicateKey(literal.getPredicateIndicator());
		String literalExactKey = exactKey(literal);
		LinkedHashSet<Literal> bucket = targetPredicateIndex.get(key);
		if (bucket == null) {
			return;
		}
		removeExactKeyFromBucket(bucket, literalExactKey);
		if (bucket.isEmpty()) {
			targetPredicateIndex.remove(key);
		}
	}

	private void removeExactIndexLiteral(
		Literal literal,
		Map<String, LinkedHashSet<Literal>> targetExactIndex
	) {
		String key = exactKey(literal);
		if (key == null) {
			return;
		}
		LinkedHashSet<Literal> bucket = targetExactIndex.get(key);
		if (bucket == null) {
			return;
		}
		removeExactKeyFromBucket(bucket, key);
		if (bucket.isEmpty()) {
			targetExactIndex.remove(key);
		}
	}

	private void removeArgumentIndexLiteral(
		Literal literal,
		Map<String, Map<Integer, Map<String, LinkedHashSet<Literal>>>> targetIndex
	) {
		List<Term> terms = literal.getTerms();
		if (terms == null || terms.isEmpty()) {
			return;
		}
		String predicateKey = predicateKey(literal.getPredicateIndicator());
		Map<Integer, Map<String, LinkedHashSet<Literal>>> byPosition =
			targetIndex.get(predicateKey);
		if (byPosition == null) {
			return;
		}
		for (int position = 0; position < terms.size(); position++) {
			Term term = terms.get(position);
			if (term == null || term.isVar()) {
				continue;
			}
			Map<String, LinkedHashSet<Literal>> byValue = byPosition.get(position);
			if (byValue == null) {
				continue;
			}
			LinkedHashSet<Literal> bucket = byValue.get(term.toString());
			if (bucket == null) {
				continue;
			}
			removeExactKeyFromBucket(bucket, exactKey(literal));
			if (bucket.isEmpty()) {
				byValue.remove(term.toString());
			}
			if (byValue.isEmpty()) {
				byPosition.remove(position);
			}
		}
		if (byPosition.isEmpty()) {
			targetIndex.remove(predicateKey);
		}
	}

	private void removeExactKeyFromBucket(LinkedHashSet<Literal> bucket, String key) {
		if (bucket == null || key == null) {
			return;
		}
		Iterator<Literal> iterator = bucket.iterator();
		while (iterator.hasNext()) {
			Literal candidate = iterator.next();
			if (key.equals(exactKey(candidate))) {
				iterator.remove();
			}
		}
	}

	private LinkedHashSet<Literal> bucketFor(
		Map<String, Map<Integer, Map<String, LinkedHashSet<Literal>>>> targetIndex,
		PredicateIndicator indicator,
		int position,
		String value
	) {
		Map<Integer, Map<String, LinkedHashSet<Literal>>> byPosition =
			targetIndex.get(predicateKey(indicator));
		if (byPosition == null) {
			return null;
		}
		Map<String, LinkedHashSet<Literal>> byValue = byPosition.get(position);
		if (byValue == null) {
			return null;
		}
		return byValue.get(value);
	}

	private Iterator<Literal> candidateIterator(
		LinkedHashSet<Literal> staticBucket,
		LinkedHashSet<Literal> dynamicBucket
	) {
		Iterator<Literal> staticIterator = staticBucket == null
			? Collections.emptyIterator()
			: staticBucket.iterator();
		Iterator<Literal> dynamicIterator = dynamicBucket == null
			? Collections.emptyIterator()
			: dynamicBucket.iterator();
		return new Iterator<Literal>() {
			private Literal nextDynamic = null;

			@Override
			public boolean hasNext() {
				if (staticIterator.hasNext()) {
					return true;
				}
				if (nextDynamic != null) {
					return true;
				}
				nextDynamic = nextLiveDynamic();
				return nextDynamic != null;
			}

			@Override
			public Literal next() {
				if (staticIterator.hasNext()) {
					return staticIterator.next();
				}
				if (nextDynamic == null) {
					nextDynamic = nextLiveDynamic();
				}
				if (nextDynamic == null) {
					throw new java.util.NoSuchElementException();
				}
				Literal result = nextDynamic;
				nextDynamic = null;
				return result;
			}

			private Literal nextLiveDynamic() {
				while (dynamicIterator.hasNext()) {
					Literal candidate = dynamicIterator.next();
					if (isLiveDynamicLiteral(candidate)) {
						return candidate;
					}
				}
				return null;
			}
		};
	}

	private boolean isLiveDynamicLiteral(Literal candidate) {
		String key = exactKey(candidate);
		if (key == null) {
			return false;
		}
		LinkedHashSet<Literal> bucket = dynamicExactIndex.get(key);
		return bucket != null && bucket.contains(candidate);
	}

	private int bucketSize(LinkedHashSet<Literal> bucket) {
		return bucket == null ? 0 : bucket.size();
	}

	private String predicateKey(PredicateIndicator indicator) {
		return indicator.toString();
	}

	private LinkedHashSet<Literal> exactBucket(
		Map<String, LinkedHashSet<Literal>> targetExactIndex,
		Literal literal
	) {
		String key = exactKey(literal);
		if (key == null) {
			return null;
		}
		return targetExactIndex.get(key);
	}

	private String exactKeyIfBound(Literal literal, Unifier unifier) {
		if (literal == null) {
			return null;
		}
		List<Term> terms = literal.getTerms();
		if (terms == null) {
			return predicateKey(literal.getPredicateIndicator());
		}
		List<String> values = new ArrayList<>();
		for (Term term : terms) {
			Term bound = boundTerm(term, unifier);
			if (bound == null) {
				return null;
			}
			values.add(bound.toString());
		}
		return predicateKey(literal.getPredicateIndicator()) + "|" + String.join("|", values);
	}

	private String exactKey(Literal literal) {
		if (literal == null) {
			return null;
		}
		List<Term> terms = literal.getTerms();
		if (terms == null || terms.isEmpty()) {
			return predicateKey(literal.getPredicateIndicator());
		}
		List<String> values = new ArrayList<>();
		for (Term term : terms) {
			if (term == null || term.isVar()) {
				return null;
			}
			values.add(term.toString());
		}
		return predicateKey(literal.getPredicateIndicator()) + "|" + String.join("|", values);
	}

	private void loadStaticBeliefs() {
		if (!Files.exists(staticBeliefsPath)) {
			return;
		}
		try (BufferedReader reader = Files.newBufferedReader(
			staticBeliefsPath,
			StandardCharsets.UTF_8
		)) {
			String line;
			while ((line = reader.readLine()) != null) {
				String fact = line.trim();
				if (!fact.isEmpty() && !fact.startsWith("#")) {
					Literal literal = Literal.parseLiteral(fact);
					if (super.add(literal)) {
						indexStaticLiteral(literal);
					}
				}
			}
		} catch (IOException error) {
			throw new RuntimeException(
				"Failed to load Jason static beliefs from "
					+ staticBeliefsPath.toAbsolutePath(),
				error
			);
		}
	}

	private void loadInitialDynamicBeliefs() {
		if (!Files.exists(initialDynamicBeliefsPath)) {
			return;
		}
		try (BufferedReader reader = Files.newBufferedReader(
			initialDynamicBeliefsPath,
			StandardCharsets.UTF_8
		)) {
			String line;
			while ((line = reader.readLine()) != null) {
				String fact = line.trim();
				if (!fact.isEmpty() && !fact.startsWith("#")) {
					applyDynamicAddition(fact);
				}
			}
		} catch (IOException error) {
			throw new RuntimeException(
				"Failed to load Jason initial dynamic beliefs from "
					+ initialDynamicBeliefsPath.toAbsolutePath(),
				error
			);
		}
	}
}
""".strip() + "\n"


def _render_temporal_monitor_config(
	dfa_payload: Mapping[str, Any],
	*,
	goal_name: str,
	initial_facts: Sequence[str] | None = None,
) -> str:
	"""Render a query-local deterministic DFA monitor consumed by the Java runtime."""

	initial_state = str(dfa_payload.get("initial_state") or "").strip()
	if not initial_state:
		raise JasonValidationError("Temporal DFA monitor requires an initial state.")
	accepting_states = tuple(
		str(state).strip()
		for state in tuple(dfa_payload.get("accepting_states") or ())
		if str(state).strip()
	)
	transitions: list[tuple[str, str, str]] = []
	states = {initial_state, *accepting_states}
	for raw_transition in tuple(dfa_payload.get("guarded_transitions") or ()):
		if not isinstance(raw_transition, Mapping):
			raise JasonValidationError("Temporal DFA transition must be a JSON object.")
		source = str(raw_transition.get("source_state") or "").strip()
		target = str(raw_transition.get("target_state") or "").strip()
		guard = _runtime_monitor_guard_text(
			str(raw_transition.get("raw_label") or "true")
		)
		if not source or not target or "\t" in guard or "\n" in guard:
			raise JasonValidationError("Temporal DFA transition is malformed.")
		states.update((source, target))
		transitions.append((source, target, guard))
	current_state = (
		_initial_temporal_monitor_state(dfa_payload, initial_facts=initial_facts)
		if initial_facts is not None
		else initial_state
	)
	lines = ["schema_version\t1", f"initial\t{current_state}"]
	lines.extend(f"accepting\t{state}" for state in accepting_states)
	lines.extend(
		f"state\t{state}\t{dfa_monitor_state_belief(goal_name, state)}"
		for state in sorted(states)
	)
	lines.append(f"accepting_belief\t{dfa_monitor_accepting_belief(goal_name)}")
	lines.extend(
		f"transition\t{source}\t{target}\t{guard}"
		for source, target, guard in transitions
	)
	return "\n".join(lines) + "\n"


def _temporal_monitor_initial_beliefs(
	dfa_payload: Mapping[str, Any],
	*,
	goal_name: str,
	initial_facts: Sequence[str],
) -> tuple[str, ...]:
	state = _initial_temporal_monitor_state(dfa_payload, initial_facts=initial_facts)
	accepting = {
		str(item).strip()
		for item in tuple(dfa_payload.get("accepting_states") or ())
		if str(item).strip()
	}
	beliefs = [dfa_monitor_state_belief(goal_name, state)]
	if state in accepting:
		beliefs.append(dfa_monitor_accepting_belief(goal_name))
	return tuple(beliefs)


def _initial_temporal_monitor_state(
	dfa_payload: Mapping[str, Any],
	*,
	initial_facts: Sequence[str],
) -> str:
	initial_state = str(dfa_payload.get("initial_state") or "").strip()
	world = {str(fact).strip() for fact in initial_facts if str(fact).strip()}
	matches = [
		str(transition.get("target_state") or "").strip()
		for transition in tuple(dfa_payload.get("guarded_transitions") or ())
		if isinstance(transition, Mapping)
		and str(transition.get("source_state") or "").strip() == initial_state
		and _runtime_monitor_guard_holds(
			str(transition.get("raw_label") or "true"),
			world=world,
		)
	]
	if len(matches) != 1 or not matches[0]:
		raise JasonValidationError(
			"Temporal DFA must have exactly one transition for the initial valuation.",
			metadata={"initial_state": initial_state, "matching_targets": matches},
		)
	return matches[0]


def _runtime_monitor_guard_holds(raw_guard: str, *, world: set[str]) -> bool:
	guard = str(raw_guard or "").strip()
	if guard.lower() == "true":
		return True
	if not guard or guard.lower() == "false":
		return False
	for raw_literal in guard.split("&"):
		literal = raw_literal.strip()
		negative = False
		for prefix in ("not ", "!", "~"):
			if literal.lower().startswith(prefix):
				negative = True
				literal = literal[len(prefix) :].strip()
				break
		atom = _render_runtime_monitor_atom(literal)
		if negative == (atom in world):
			return False
	return True


def _runtime_monitor_guard_text(raw_guard: str) -> str:
	"""Render one conjunctive PDDL guard in the runtime AgentSpeak vocabulary."""

	guard = str(raw_guard or "").strip()
	if guard.lower() in {"true", "false"}:
		return guard.lower()
	formatted: list[str] = []
	for raw_literal in guard.split("&"):
		literal = raw_literal.strip()
		negative = False
		for prefix in ("not ", "!", "~"):
			if literal.lower().startswith(prefix):
				negative = True
				literal = literal[len(prefix) :].strip()
				break
		atom = _render_runtime_monitor_atom(literal)
		formatted.append(f"not {atom}" if negative else atom)
	return " & ".join(formatted)


def _render_runtime_monitor_atom(atom: str) -> str:
	"""Render DFA atoms while preserving numeric equality values as integers."""

	text = str(atom or "").strip()
	if "(" not in text or not text.endswith(")"):
		return sanitize_identifier(text)
	predicate, raw_args = text.split("(", 1)
	arguments = tuple(
		argument.strip()
		for argument in raw_args[:-1].split(",")
		if argument.strip()
	)
	rendered_arguments = tuple(
		argument
		if re.fullmatch(r"[+-]?\d+", argument)
		else _render_runtime_term(argument)
		for argument in arguments
	)
	return f"{sanitize_identifier(predicate)}({','.join(rendered_arguments)})"


def _build_environment_java_source(
	*,
	class_name: str,
	action_schemas: Sequence[RuntimeActionSchema],
	seed_facts_file_name: str,
	initial_percepts_file_name: str = "initial_percepts.txt",
	plan_trace_file_name: str = "jason_plan.plan",
	pddl_symbol_map_file_name: str = "pddl_symbol_map.tsv",
) -> str:
	action_lines = "\n\t\t".join(
		_render_action_registration(schema)
		for schema in tuple(action_schemas or ())
	)
	if not action_lines:
		action_lines = "// no action schemas"
	initial_percepts_file = _java_quote(initial_percepts_file_name)
	plan_trace_file = _java_quote(plan_trace_file_name)
	pddl_symbol_map_file = _java_quote(pddl_symbol_map_file_name)
	return f"""
import jason.asSyntax.Structure;
import jason.environment.Environment;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class {class_name} extends Environment {{

	private static final class Pattern {{
		final String predicate;
		final boolean positive;
		final String[] args;

		Pattern(String predicate, boolean positive, String[] args) {{
			this.predicate = predicate;
			this.positive = positive;
			this.args = args;
		}}
	}}

	private static final class NumericTerm {{
		final String kind;
		final String value;
		final String[] args;

		NumericTerm(String kind, String value, String[] args) {{
			this.kind = kind;
			this.value = value;
			this.args = args;
		}}
	}}

	private static final class NumericCondition {{
		final String comparator;
		final NumericTerm left;
		final NumericTerm right;

		NumericCondition(String comparator, NumericTerm left, NumericTerm right) {{
			this.comparator = comparator;
			this.left = left;
			this.right = right;
		}}
	}}

	private static final class NumericEffect {{
		final String operator;
		final String predicate;
		final String[] args;
		final NumericTerm amount;

		NumericEffect(
			String operator,
			String predicate,
			String[] args,
			NumericTerm amount
		) {{
			this.operator = operator;
			this.predicate = predicate;
			this.args = args;
			this.amount = amount;
		}}
	}}

	private static final class ActionSchema {{
		final String name;
		final String sourceName;
		final String[] parameters;
		final Pattern[] preconditions;
		final Pattern[] effects;
		final NumericCondition[] numericPreconditions;
		final NumericEffect[] numericEffects;

		ActionSchema(
			String name,
			String sourceName,
			String[] parameters,
			Pattern[] preconditions,
			Pattern[] effects,
			NumericCondition[] numericPreconditions,
			NumericEffect[] numericEffects
		) {{
			this.name = name;
			this.sourceName = sourceName;
			this.parameters = parameters;
			this.preconditions = preconditions;
			this.effects = effects;
			this.numericPreconditions = numericPreconditions;
			this.numericEffects = numericEffects;
		}}
	}}

	private static final class EffectDelta {{
		final Set<String> added;
		final Set<String> removed;

		EffectDelta(Set<String> added, Set<String> removed) {{
			this.added = added;
			this.removed = removed;
		}}

		boolean changed() {{
			return !added.isEmpty() || !removed.isEmpty();
		}}
	}}

	private static final class MonitorTransition {{
		final String source;
		final String target;
		final String guard;

		MonitorTransition(String source, String target, String guard) {{
			this.source = source;
			this.target = target;
			this.guard = guard;
		}}
	}}

	private final Set<String> world = new LinkedHashSet<>();
	private final Map<String, ActionSchema> actions = new HashMap<>();
	private final Map<String, String> pddlSymbols = new HashMap<>();
	private final Map<String, List<MonitorTransition>> monitorTransitions = new HashMap<>();
	private final Map<String, String> monitorStateBeliefs = new HashMap<>();
	private final Set<String> monitorAcceptingStates = new LinkedHashSet<>();
	private final StringBuilder planTraceBuffer = new StringBuilder();
	private boolean planTraceDirty = false;
	private final Path initialPerceptsPath = Paths.get({initial_percepts_file});
	private final Path staticBeliefsPath = Paths.get("static_beliefs.txt");
	private final Path planTracePath = Paths.get({plan_trace_file});
	private final Path pddlSymbolMapPath = Paths.get({pddl_symbol_map_file});
	private final Path temporalMonitorPath = Paths.get("temporal_dfa_monitor.tsv");
	private String monitorState = null;
	private String monitorAcceptingBelief = null;
	private boolean temporalMonitorEnabled = false;
	private final boolean planTraceEnabled = Boolean.parseBoolean(
		System.getProperty("jason.pipeline.planTraceEnabled", "true")
	);
	private final int actionTraceLimit = Integer.getInteger(
		"jason.pipeline.actionTraceLimit",
		3
	);
	private final int actionTraceInterval = Integer.getInteger(
		"jason.pipeline.actionTraceInterval",
		100000
	);
	private int actionCount = 0;

	@Override
	public synchronized void init(String[] args) {{
		super.init(args);
		seedInitialFacts();
		loadPddlSymbolMap();
		resetPlanTrace();
		loadActions();
		loadTemporalMonitor();
		System.out.println("runtime env ready");
	}}

	@Override
	public synchronized void stop() {{
		try {{
			flushPlanTrace();
		}} finally {{
			super.stop();
		}}
	}}

	@Override
	public synchronized boolean executeAction(String agName, Structure action) {{
		if ("true".equals(action.getFunctor()) && action.getArity() == 0) {{
			return true;
		}}
		if ("runtime_summary".equals(action.getFunctor()) && action.getArity() == 0) {{
			printRuntimeSummary();
			return true;
		}}
		ActionSchema schema = actions.get(action.getFunctor());
		if (schema == null) {{
			System.out.println("runtime env unknown action " + action);
			return false;
		}}
		if (action.getArity() != schema.parameters.length) {{
			System.out.println(
				"runtime env action failed "
					+ renderTraceAction(schema.sourceName, action)
					+ " reason=arity"
			);
			return false;
		}}

		Map<String, String> bindings = new HashMap<>();
		for (int i = 0; i < schema.parameters.length; i++) {{
			String parameter = canonical(schema.parameters[i]);
			String value = canonical(action.getTerm(i).toString());
			bindings.put(parameter, value);
			if (parameter.startsWith("?")) {{
				bindings.put(parameter.substring(1), value);
			}}
		}}

		if (
			!checkPreconditions(schema.preconditions, bindings)
			|| !checkNumericPreconditions(schema.numericPreconditions, bindings)
		) {{
			System.out.println(
				"runtime env action failed "
					+ renderTraceAction(schema.sourceName, action)
					+ " reason=precondition"
			);
			return false;
		}}

		EffectDelta delta = applyEffects(schema, bindings);
		boolean temporalMonitorValid = advanceTemporalMonitor(delta.removed, delta.added);
		JasonPipelineIndexedBeliefBase.applyDynamicDelta(
			delta.removed,
			delta.added
		);
		if (delta.changed()) {{
			informAgsEnvironmentChanged();
		}}
		actionCount += 1;
		recordPlanAction(schema, action);
		traceSuccessfulAction(schema, action);
		if (!temporalMonitorValid) {{
			System.out.println("runtime env temporal monitor failed state=" + monitorState);
			return false;
		}}
		return true;
	}}

	private void loadTemporalMonitor() {{
		monitorTransitions.clear();
		monitorStateBeliefs.clear();
		monitorAcceptingStates.clear();
		monitorState = null;
		monitorAcceptingBelief = null;
		temporalMonitorEnabled = false;
		if (!Files.exists(temporalMonitorPath)) {{
			return;
		}}
		try (BufferedReader reader = Files.newBufferedReader(
			temporalMonitorPath,
			StandardCharsets.UTF_8
		)) {{
			String line;
			while ((line = reader.readLine()) != null) {{
				String trimmed = line.trim();
				if (trimmed.isEmpty() || trimmed.startsWith("#")) {{
					continue;
				}}
				String[] parts = trimmed.split("\\t", 4);
				if (parts.length >= 2 && "initial".equals(parts[0])) {{
					monitorState = parts[1];
				}} else if (parts.length >= 2 && "accepting".equals(parts[0])) {{
					monitorAcceptingStates.add(parts[1]);
				}} else if (parts.length >= 3 && "state".equals(parts[0])) {{
					monitorStateBeliefs.put(parts[1], parts[2]);
				}} else if (
					parts.length >= 2 && "accepting_belief".equals(parts[0])
				) {{
					monitorAcceptingBelief = parts[1];
				}} else if (parts.length == 4 && "transition".equals(parts[0])) {{
					monitorTransitions
						.computeIfAbsent(parts[1], ignored -> new ArrayList<>())
						.add(new MonitorTransition(parts[1], parts[2], parts[3]));
				}}
			}}
			temporalMonitorEnabled = monitorState != null && monitorAcceptingBelief != null;
		}} catch (IOException error) {{
			throw new RuntimeException(
				"Failed to load temporal DFA monitor from "
					+ temporalMonitorPath.toAbsolutePath(),
				error
			);
		}}
	}}

	private boolean advanceTemporalMonitor(Set<String> removed, Set<String> added) {{
		if (!temporalMonitorEnabled) {{
			return true;
		}}
		List<MonitorTransition> matches = new ArrayList<>();
		for (MonitorTransition transition : monitorTransitions.getOrDefault(
			monitorState,
			List.of()
		)) {{
			if (monitorGuardHolds(transition.guard)) {{
				matches.add(transition);
			}}
		}}
		if (matches.size() != 1) {{
			removeMonitorBeliefs(removed);
			monitorState = null;
			return false;
		}}
		String previousState = monitorState;
		removeMonitorBeliefs(removed);
		monitorState = matches.get(0).target;
		String stateBelief = monitorStateBeliefs.get(monitorState);
		if (stateBelief != null) {{
			added.add(stateBelief);
			world.add(stateBelief);
		}}
		if (monitorAcceptingStates.contains(monitorState)) {{
			added.add(monitorAcceptingBelief);
			world.add(monitorAcceptingBelief);
		}}
		System.out.println(
			"runtime env temporal monitor " + previousState + " -> " + monitorState
		);
		return true;
	}}

	private void removeMonitorBeliefs(Set<String> removed) {{
		String stateBelief = monitorStateBeliefs.get(monitorState);
		if (stateBelief != null) {{
			removed.add(stateBelief);
			world.remove(stateBelief);
		}}
		if (monitorAcceptingBelief != null) {{
			removed.add(monitorAcceptingBelief);
			world.remove(monitorAcceptingBelief);
		}}
	}}

	private boolean monitorGuardHolds(String rawGuard) {{
		String guard = rawGuard == null ? "" : rawGuard.trim();
		if ("true".equalsIgnoreCase(guard)) {{
			return true;
		}}
		if (guard.isEmpty() || "false".equalsIgnoreCase(guard)) {{
			return false;
		}}
		for (String rawLiteral : guard.split("&")) {{
			String literal = rawLiteral.trim();
			boolean negative = false;
			if (literal.startsWith("~") || literal.startsWith("!")) {{
				negative = true;
				literal = literal.substring(1).trim();
			}} else if (literal.toLowerCase().startsWith("not ")) {{
				negative = true;
				literal = literal.substring(4).trim();
			}}
			String atom = normalizeMonitorAtom(literal);
			boolean holds = world.contains(atom);
			if (negative == holds) {{
				return false;
			}}
		}}
		return true;
	}}

	private String normalizeMonitorAtom(String atom) {{
		return atom == null ? "" : atom.replaceAll("\\s+", "");
	}}

	private void seedInitialFacts() {{
		world.clear();
		loadFactsIntoWorld(staticBeliefsPath);
		loadFactsIntoWorld(initialPerceptsPath);
	}}

	private void loadFactsIntoWorld(Path factsPath) {{
		if (!Files.exists(factsPath)) {{
			return;
		}}
		try (BufferedReader reader = Files.newBufferedReader(
			factsPath,
			StandardCharsets.UTF_8
		)) {{
			String line;
			while ((line = reader.readLine()) != null) {{
				String fact = line.trim();
				if (!fact.isEmpty() && !fact.startsWith("#")) {{
					world.add(fact);
				}}
			}}
		}} catch (IOException error) {{
			throw new RuntimeException(
				"Failed to load Jason initial facts from " + factsPath.toAbsolutePath(),
				error
			);
		}}
	}}

	private void loadPddlSymbolMap() {{
		pddlSymbols.clear();
		if (!Files.exists(pddlSymbolMapPath)) {{
			return;
		}}
		try (BufferedReader reader = Files.newBufferedReader(
			pddlSymbolMapPath,
			StandardCharsets.UTF_8
		)) {{
			String line;
			while ((line = reader.readLine()) != null) {{
				String trimmed = line.trim();
				if (trimmed.isEmpty() || trimmed.startsWith("#")) {{
					continue;
				}}
				String[] parts = trimmed.split("\\t", 2);
				if (parts.length == 2 && !parts[0].isEmpty()) {{
					pddlSymbols.put(parts[0], parts[1]);
				}}
			}}
		}} catch (IOException error) {{
			throw new RuntimeException(
				"Failed to load Jason PDDL symbol map from " + pddlSymbolMapPath.toAbsolutePath(),
				error
			);
		}}
	}}

	private void resetPlanTrace() {{
		planTraceBuffer.setLength(0);
		planTraceDirty = false;
		if (!planTraceEnabled) {{
			return;
		}}
		try {{
			Files.write(planTracePath, new byte[0]);
		}} catch (IOException error) {{
			throw new RuntimeException(
				"Failed to initialize Jason plan trace at " + planTracePath.toAbsolutePath(),
				error
			);
		}}
	}}

	private void loadActions() {{
		actions.clear();
		{action_lines}
	}}

	private void register(ActionSchema schema) {{
		actions.put(schema.name, schema);
	}}

	private boolean checkPreconditions(Pattern[] preconditions, Map<String, String> bindings) {{
		for (Pattern pattern : preconditions) {{
			String grounded = ground(pattern.predicate, pattern.args, bindings);
			boolean holds = pattern.positive ? world.contains(grounded) : !world.contains(grounded);
			if (!holds) {{
				return false;
			}}
		}}
		return true;
	}}

	private boolean checkNumericPreconditions(
		NumericCondition[] preconditions,
		Map<String, String> bindings
	) {{
		for (NumericCondition condition : preconditions) {{
			Long left = evaluateNumericTerm(condition.left, bindings);
			Long right = evaluateNumericTerm(condition.right, bindings);
			if (left == null || right == null) {{
				return false;
			}}
			if (!compareNumeric(left.longValue(), right.longValue(), condition.comparator)) {{
				return false;
			}}
		}}
		return true;
	}}

	private boolean compareNumeric(long left, long right, String comparator) {{
		if (">".equals(comparator)) {{
			return left > right;
		}}
		if (">=".equals(comparator)) {{
			return left >= right;
		}}
		if ("<".equals(comparator)) {{
			return left < right;
		}}
		if ("<=".equals(comparator)) {{
			return left <= right;
		}}
		if ("=".equals(comparator)) {{
			return left == right;
		}}
		return false;
	}}

	private EffectDelta applyEffects(ActionSchema schema, Map<String, String> bindings) {{
		Set<String> added = new LinkedHashSet<>();
		Set<String> removed = new LinkedHashSet<>();
		for (Pattern pattern : schema.effects) {{
			if (pattern.positive) {{
				continue;
			}}
			String grounded = ground(pattern.predicate, pattern.args, bindings);
			if (world.remove(grounded) && !added.remove(grounded)) {{
				removed.add(grounded);
			}}
		}}
		for (Pattern pattern : schema.effects) {{
			if (!pattern.positive) {{
				continue;
			}}
			String grounded = ground(pattern.predicate, pattern.args, bindings);
			if (world.add(grounded) && !removed.remove(grounded)) {{
				added.add(grounded);
			}}
		}}
		applyNumericEffects(schema.numericEffects, bindings, added, removed);
		return new EffectDelta(added, removed);
	}}

	private void applyNumericEffects(
		NumericEffect[] effects,
		Map<String, String> bindings,
		Set<String> added,
		Set<String> removed
	) {{
		for (NumericEffect effect : effects) {{
			Long current = currentNumericValue(effect.predicate, effect.args, bindings);
			Long amount = evaluateNumericTerm(effect.amount, bindings);
			if (current == null || amount == null) {{
				throw new RuntimeException(
					"Missing numeric fluent while applying " + effect.operator
				);
			}}
			long next = current.longValue();
			if ("increase".equals(effect.operator)) {{
				next += amount.longValue();
			}} else if ("decrease".equals(effect.operator)) {{
				next -= amount.longValue();
			}} else {{
				throw new RuntimeException("Unsupported numeric effect " + effect.operator);
			}}
			String oldFact = groundNumericFact(effect.predicate, effect.args, bindings, current);
			String newFact = groundNumericFact(effect.predicate, effect.args, bindings, next);
			if (world.remove(oldFact) && !added.remove(oldFact)) {{
				removed.add(oldFact);
			}}
			if (world.add(newFact) && !removed.remove(newFact)) {{
				added.add(newFact);
			}}
		}}
	}}

	private Long evaluateNumericTerm(NumericTerm term, Map<String, String> bindings) {{
		if ("constant".equals(term.kind)) {{
			try {{
				return Long.valueOf(term.value);
			}} catch (NumberFormatException error) {{
				return null;
			}}
		}}
		return currentNumericValue(term.value, term.args, bindings);
	}}

	private Long currentNumericValue(
		String predicate,
		String[] args,
		Map<String, String> bindings
	) {{
		String prefix = numericFactPrefix(predicate, args, bindings);
		Long value = null;
		for (String fact : world) {{
			if (!fact.startsWith(prefix) || !fact.endsWith(")")) {{
				continue;
			}}
			String rawValue = fact.substring(prefix.length(), fact.length() - 1);
			try {{
				long parsed = Long.parseLong(rawValue);
				if (value != null) {{
					return null;
				}}
				value = Long.valueOf(parsed);
			}} catch (NumberFormatException error) {{
				return null;
			}}
		}}
		return value;
	}}

	private String groundNumericFact(
		String predicate,
		String[] args,
		Map<String, String> bindings,
		long value
	) {{
		return numericFactPrefix(predicate, args, bindings) + value + ")";
	}}

	private String numericFactPrefix(
		String predicate,
		String[] args,
		Map<String, String> bindings
	) {{
		StringBuilder builder = new StringBuilder(predicate);
		builder.append("(");
		for (int i = 0; i < args.length; i++) {{
			if (i > 0) {{
				builder.append(",");
			}}
			builder.append(renderTerm(resolveToken(args[i], bindings)));
		}}
		if (args.length > 0) {{
			builder.append(",");
		}}
		return builder.toString();
	}}

	private String ground(String predicate, String[] args, Map<String, String> bindings) {{
		if (args.length == 0) {{
			return predicate;
		}}
		StringBuilder builder = new StringBuilder(predicate);
		builder.append("(");
		for (int i = 0; i < args.length; i++) {{
			if (i > 0) {{
				builder.append(",");
			}}
			builder.append(renderTerm(resolveToken(args[i], bindings)));
		}}
		builder.append(")");
		return builder.toString();
	}}

	private String resolveToken(String rawToken, Map<String, String> bindings) {{
		String token = canonical(rawToken);
		if (bindings.containsKey(token)) {{
			return bindings.get(token);
		}}
		if (token.startsWith("?")) {{
			String bare = token.substring(1);
			if (bindings.containsKey(bare)) {{
				return bindings.get(bare);
			}}
		}}
		return token;
	}}

	private String canonical(String token) {{
		String value = token == null ? "" : token.trim();
		if (value.length() >= 2) {{
			boolean quoted =
				(value.startsWith("\\\"") && value.endsWith("\\\""))
				|| (value.startsWith("'") && value.endsWith("'"));
			if (quoted) {{
				value = value.substring(1, value.length() - 1);
			}}
		}}
		return value;
	}}

	private String renderTerm(String token) {{
		String value = canonical(token);
		if (value.matches("[a-z][a-z0-9_]*")) {{
			return value;
		}}
		return "\\\"" + value.replace("\\\\", "\\\\\\\\").replace("\\\"", "\\\\\\\"") + "\\\"";
	}}

	private String renderTraceAction(String sourceName, Structure action) {{
		if (action.getArity() == 0) {{
			return sourceName + "()";
		}}
		String[] args = new String[action.getArity()];
		for (int i = 0; i < action.getArity(); i++) {{
			args[i] = canonical(action.getTerm(i).toString());
		}}
		return sourceName + "(" + String.join(",", args) + ")";
	}}

	private void recordPlanAction(ActionSchema schema, Structure action) {{
		if (!planTraceEnabled) {{
			return;
		}}
		appendPddlPlanAction(schema.sourceName, action);
		planTraceBuffer.append(System.lineSeparator());
		planTraceDirty = true;
	}}

	private void appendPddlPlanAction(String sourceName, Structure action) {{
		planTraceBuffer.append("(");
		planTraceBuffer.append(sourceName);
		for (int i = 0; i < action.getArity(); i++) {{
			planTraceBuffer.append(" ");
			planTraceBuffer.append(toPddlSymbol(canonical(action.getTerm(i).toString())));
		}}
		planTraceBuffer.append(")");
	}}

	private String toPddlSymbol(String canonicalToken) {{
		String value = pddlSymbols.get(canonicalToken);
		return value == null ? canonicalToken : value;
	}}

	private void traceSuccessfulAction(ActionSchema schema, Structure action) {{
		if (actionCount <= actionTraceLimit) {{
			System.out.println(
				"runtime env action success " + renderTraceAction(schema.sourceName, action)
			);
			return;
		}}
		if (actionTraceInterval > 0 && actionCount % actionTraceInterval == 0) {{
			printRuntimeSummary();
		}}
	}}

	private void printRuntimeSummary() {{
		flushPlanTrace();
		System.out.println("runtime env action count " + actionCount);
	}}

	private void flushPlanTrace() {{
		if (!planTraceEnabled) {{
			return;
		}}
		if (!planTraceDirty && Files.exists(planTracePath)) {{
			return;
		}}
		try {{
			Files.write(
				planTracePath,
				planTraceBuffer.toString().getBytes(StandardCharsets.UTF_8)
			);
			planTraceDirty = false;
		}} catch (IOException error) {{
			throw new RuntimeException(
				"Failed to write Jason plan trace to " + planTracePath.toAbsolutePath(),
				error
			);
		}}
	}}

}}
""".strip() + "\n"


def _render_action_registration(schema: RuntimeActionSchema) -> str:
	parameters = ", ".join(_java_quote(parameter) for parameter in schema.parameters)
	preconditions = ", ".join(_render_pattern_java(pattern) for pattern in schema.preconditions)
	effects = ", ".join(_render_pattern_java(pattern) for pattern in schema.effects)
	numeric_preconditions = ", ".join(
		_render_numeric_condition_java(condition)
		for condition in schema.numeric_preconditions
	)
	numeric_effects = ", ".join(
		_render_numeric_effect_java(effect)
		for effect in schema.numeric_effects
	)
	return (
		"register(new ActionSchema("
		f"{_java_quote(schema.functor)}, "
		f"{_java_quote(schema.source_name)}, "
		f"new String[]{{{parameters}}}, "
		f"new Pattern[]{{{preconditions}}}, "
		f"new Pattern[]{{{effects}}}, "
		f"new NumericCondition[]{{{numeric_preconditions}}}, "
		f"new NumericEffect[]{{{numeric_effects}}}"
		"));"
	)


def _render_pattern_java(pattern: PredicatePattern) -> str:
	args = ", ".join(_java_quote(argument) for argument in pattern.args)
	return (
		"new Pattern("
		f"{_java_quote(pattern.predicate)}, "
		f"{str(pattern.positive).lower()}, "
		f"new String[]{{{args}}}"
		")"
	)


def _render_numeric_condition_java(condition: RuntimeNumericCondition) -> str:
	return (
		"new NumericCondition("
		f"{_java_quote(condition.comparator)}, "
		f"{_render_numeric_term_java(condition.left)}, "
		f"{_render_numeric_term_java(condition.right)}"
		")"
	)


def _render_numeric_effect_java(effect: RuntimeNumericEffect) -> str:
	args = ", ".join(_java_quote(argument) for argument in effect.args)
	return (
		"new NumericEffect("
		f"{_java_quote(effect.operator)}, "
		f"{_java_quote(effect.function)}, "
		f"new String[]{{{args}}}, "
		f"{_render_numeric_term_java(effect.amount)}"
		")"
	)


def _render_numeric_term_java(term: RuntimeNumericTerm) -> str:
	args = ", ".join(_java_quote(argument) for argument in term.args)
	return (
		"new NumericTerm("
		f"{_java_quote(term.kind)}, "
		f"{_java_quote(term.value)}, "
		f"new String[]{{{args}}}"
		")"
	)


def _java_quote(value: str) -> str:
	escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
	return f'"{escaped}"'


def _logging_properties() -> str:
	return "\n".join(
		(
			"handlers= java.util.logging.ConsoleHandler",
			".level = INFO",
			"java.util.logging.ConsoleHandler.level = FINE",
			"java.util.logging.ConsoleHandler.formatter = jason.runtime.MASConsoleLogFormatter",
			"java.level=OFF",
			"javax.level=OFF",
			"sun.level=OFF",
			"jade.level=OFF",
			"",
		),
	)


def _resolve_jason_classpath(artifact: str) -> str:
	override = os.getenv("JASON_CLASSPATH")
	if override:
		return override
	maven = shutil.which("mvn")
	if not maven:
		raise JasonValidationError(
			"Jason validation requires Maven to resolve the Jason runtime classpath.",
			metadata={"artifact": artifact},
		)
	group_id, artifact_id, version = artifact.split(":", 2)
	with tempfile.TemporaryDirectory(prefix="jason-classpath-") as tmp_dir:
		tmp_path = Path(tmp_dir)
		pom_path = tmp_path / "pom.xml"
		classpath_path = tmp_path / "classpath.txt"
		pom_path.write_text(
			f"""
<project xmlns="http://maven.apache.org/POM/4.0.0"
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
	xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
	<modelVersion>4.0.0</modelVersion>
	<groupId>local</groupId>
	<artifactId>jason-runtime-classpath</artifactId>
	<version>1.0</version>
	<dependencies>
		<dependency>
			<groupId>{group_id}</groupId>
			<artifactId>{artifact_id}</artifactId>
			<version>{version}</version>
		</dependency>
	</dependencies>
</project>
""".strip()
			+ "\n",
			encoding="utf-8",
		)
		completed = subprocess.run(
			[
				maven,
				"-q",
				"-f",
				str(pom_path),
				"dependency:build-classpath",
				f"-Dmdep.outputFile={classpath_path}",
			],
			text=True,
			capture_output=True,
			check=False,
		)
		if completed.returncode != 0:
			raise JasonValidationError(
				"Maven failed to resolve the Jason runtime classpath.",
				metadata={
					"artifact": artifact,
					"stdout": completed.stdout,
					"stderr": completed.stderr,
					"return_code": completed.returncode,
				},
			)
		classpath = classpath_path.read_text(encoding="utf-8").strip()
		if not classpath:
			raise JasonValidationError(
				"Maven returned an empty Jason runtime classpath.",
				metadata={"artifact": artifact},
			)
		return classpath


def _run_process_streamed(
	command: Sequence[str],
	*,
	cwd: Path,
	stdout_path: Path,
	stderr_path: Path,
	timeout_seconds: int,
) -> StreamedProcessResult:
	"""Run a process with stdout/stderr streamed directly to files."""

	with stdout_path.open("w", encoding="utf-8") as stdout_handle:
		with stderr_path.open("w", encoding="utf-8") as stderr_handle:
			try:
				completed = subprocess.run(
					tuple(str(item) for item in command),
					cwd=cwd,
					stdout=stdout_handle,
					stderr=stderr_handle,
					check=False,
					timeout=timeout_seconds,
				)
			except subprocess.TimeoutExpired:
				return StreamedProcessResult(exit_code=None, timed_out=True)
	return StreamedProcessResult(exit_code=completed.returncode, timed_out=False)


def _jason_java_stack_option(value: str | None = None) -> str:
	"""Return the Java stack option used when Jason parses large ASL programs."""

	stack_size = str(
		value if value is not None else os.getenv("JASON_JAVA_STACK_SIZE", ""),
	).strip()
	if not stack_size:
		stack_size = _DEFAULT_JASON_JAVA_STACK_SIZE
	if stack_size.startswith("-Xss"):
		return stack_size
	return f"-Xss{stack_size}"


def _normalize_plan_verifier_command(
	command: Sequence[str] | str | None,
) -> tuple[str, ...] | None:
	"""Normalize a user-provided VAL or IPC verifier command."""

	if command is None:
		return None
	if isinstance(command, str):
		items = tuple(shlex.split(command))
	else:
		items = tuple(str(item) for item in command)
	return items or None


def _discover_plan_verifier_command() -> tuple[str, ...] | None:
	"""Find a VAL or IPC-style PDDL plan verifier without hardcoding a local path."""

	for env_name in ("VAL_VALIDATE_BIN", "VAL_BIN", "IPC_VALIDATE_BIN"):
		value = os.getenv(env_name)
		if value:
			return _normalize_plan_verifier_command(value)
	for executable in ("Validate", "validate", "VAL"):
		path = shutil.which(executable)
		if path:
			return (path,)
	return None


def _plan_verifier_not_attempted(*, stdout_path: Path, stderr_path: Path) -> PlanVerifierResult:
	return PlanVerifierResult(
		attempted=False,
		available=False,
		success=None,
		command=(),
		exit_code=None,
		timed_out=False,
		stdout="",
		stderr="",
		artifacts={
			"stdout": str(stdout_path),
			"stderr": str(stderr_path),
		},
	)


def _run_plan_verifier(
	*,
	explicit_command: Sequence[str],
	require_verifier: bool,
	domain_file: Path,
	problem_file: Path,
	plan_file: Path,
	output_dir: Path,
	stdout_path: Path,
	stderr_path: Path,
	timeout_seconds: int,
) -> PlanVerifierResult:
	"""Validate a Jason-exported PDDL plan trace with VAL or an IPC verifier."""

	command_prefix = explicit_command or _discover_plan_verifier_command()
	if command_prefix is None:
		error = "No VAL/IPC plan verifier found on PATH or in VAL_VALIDATE_BIN/VAL_BIN."
		if require_verifier:
			stdout_path.write_text("", encoding="utf-8")
			stderr_path.write_text(error + "\n", encoding="utf-8")
			return PlanVerifierResult(
				attempted=False,
				available=False,
				success=None,
				command=(),
				exit_code=None,
				timed_out=False,
				stdout="",
				stderr=error,
				artifacts={
					"stdout": str(stdout_path),
					"stderr": str(stderr_path),
				},
				error=error,
			)
		return _plan_verifier_not_attempted(
			stdout_path=stdout_path,
			stderr_path=stderr_path,
		)
	executable = str(tuple(command_prefix)[0])
	if shutil.which(executable) is None and not Path(executable).exists():
		error = f"Plan verifier executable is not available: {executable}"
		stdout_path.write_text("", encoding="utf-8")
		stderr_path.write_text(error + "\n", encoding="utf-8")
		return PlanVerifierResult(
			attempted=False,
			available=False,
			success=None,
			command=tuple(command_prefix),
			exit_code=None,
			timed_out=False,
			stdout="",
			stderr=error,
			artifacts={
				"stdout": str(stdout_path),
				"stderr": str(stderr_path),
			},
			error=error,
		)
	if not plan_file.exists():
		error = f"Jason did not export a PDDL plan trace: {plan_file}"
		stdout_path.write_text("", encoding="utf-8")
		stderr_path.write_text(error + "\n", encoding="utf-8")
		return PlanVerifierResult(
			attempted=False,
			available=True,
			success=False,
			command=tuple(command_prefix),
			exit_code=None,
			timed_out=False,
			stdout="",
			stderr=error,
			artifacts={
				"stdout": str(stdout_path),
				"stderr": str(stderr_path),
			},
			error=error,
		)
	command = (
		*tuple(command_prefix),
		str(domain_file),
		str(problem_file),
		str(plan_file),
	)
	process_result = _run_process_streamed(
		command,
		cwd=output_dir,
		stdout_path=stdout_path,
		stderr_path=stderr_path,
		timeout_seconds=max(1, int(timeout_seconds)),
	)
	stdout_excerpt = _bounded_file_excerpt(stdout_path, _PLAN_VERIFIER_OUTPUT_EXCERPT_MAX_CHARS)
	stderr_excerpt = _bounded_file_excerpt(stderr_path, _PLAN_VERIFIER_OUTPUT_EXCERPT_MAX_CHARS)
	output_text = f"{stdout_excerpt}\n{stderr_excerpt}"
	success = _plan_verifier_output_success(
		exit_code=process_result.exit_code,
		timed_out=process_result.timed_out,
		output=output_text,
	)
	error = None
	if process_result.timed_out:
		error = f"Plan verifier exceeded {timeout_seconds} seconds."
	elif not success:
		error = "Plan verifier did not accept the exported PDDL plan trace."
	return PlanVerifierResult(
		attempted=True,
		available=True,
		success=success,
		command=command,
		exit_code=process_result.exit_code,
		timed_out=process_result.timed_out,
		stdout=stdout_excerpt,
		stderr=stderr_excerpt,
		artifacts={
			"stdout": str(stdout_path),
			"stderr": str(stderr_path),
		},
		error=error,
	)


def _plan_verifier_output_success(
	*,
	exit_code: int | None,
	timed_out: bool,
	output: str,
) -> bool:
	"""Interpret VAL/IPC verifier output without depending on one exact binary."""

	if timed_out or exit_code != 0:
		return False
	lower_output = str(output or "").lower()
	if any(marker in lower_output for marker in _PLAN_VERIFIER_FAILURE_MARKERS):
		return False
	return any(marker in lower_output for marker in _PLAN_VERIFIER_SUCCESS_MARKERS)


def _bounded_file_excerpt(path: Path, max_chars: int) -> str:
	if not path.exists():
		return ""
	text = path.read_text(encoding="utf-8", errors="replace")
	if len(text) <= max_chars:
		return text
	return text[:max_chars] + "\n... [output truncated; full log is in the artifact file] ...\n"


def _scan_runtime_output_files(
	*,
	stdout_path: Path,
	stderr_path: Path,
	excerpt_char_limit: int = _RUNTIME_OUTPUT_EXCERPT_MAX_CHARS,
	action_path_limit: int = _RUNTIME_ACTION_PATH_MAX_ITEMS,
) -> RuntimeOutputSummary:
	"""Scan Jason output artifacts without loading complete logs into memory."""

	stdout_scan = _scan_runtime_output_file(
		stdout_path,
		excerpt_char_limit=excerpt_char_limit,
		action_path_limit=action_path_limit,
	)
	stderr_scan = _scan_runtime_output_file(
		stderr_path,
		excerpt_char_limit=excerpt_char_limit,
		action_path_limit=action_path_limit,
	)
	action_path = (*stdout_scan.action_path, *stderr_scan.action_path)
	action_count = stdout_scan.action_count + stderr_scan.action_count
	action_path_truncated = (
		stdout_scan.action_path_truncated
		or stderr_scan.action_path_truncated
		or action_count > len(action_path)
	)
	marker_lines = (*stdout_scan.marker_lines, *stderr_scan.marker_lines)
	return RuntimeOutputSummary(
		stdout_excerpt=stdout_scan.excerpt,
		stderr_excerpt=stderr_scan.excerpt,
		marker_output="\n".join(marker_lines),
		action_path=action_path,
		action_count=action_count,
		action_path_truncated=action_path_truncated,
		stdout_truncated=stdout_scan.truncated,
		stderr_truncated=stderr_scan.truncated,
		has_execute_success=stdout_scan.has_execute_success or stderr_scan.has_execute_success,
	)


def _scan_runtime_output_file(
	path: Path,
	*,
	excerpt_char_limit: int,
	action_path_limit: int,
) -> _SingleOutputScan:
	"""Scan one Jason output stream, keeping only bounded diagnostic data."""

	excerpt_parts: list[str] = []
	marker_lines: list[str] = []
	action_path: list[str] = []
	action_count = 0
	remaining_excerpt_chars = max(0, int(excerpt_char_limit))
	truncated = False
	has_execute_success = False

	if not path.exists():
		return _SingleOutputScan(
			excerpt="",
			marker_lines=(),
			action_path=(),
			action_count=0,
			truncated=False,
			action_path_truncated=False,
			has_execute_success=False,
		)

	with path.open("r", encoding="utf-8", errors="replace") as handle:
		for line in handle:
			if remaining_excerpt_chars > 0:
				excerpt_parts.append(line[:remaining_excerpt_chars])
				if len(line) > remaining_excerpt_chars:
					truncated = True
				remaining_excerpt_chars -= min(len(line), remaining_excerpt_chars)
			elif line:
				truncated = True

			if "execute success" in line:
				has_execute_success = True
			if any(marker in line for marker in _ADAPTER_MARKERS):
				marker_lines.append(line.rstrip("\n"))
			if _ACTION_SUCCESS_MARKER in line:
				action_count += 1
				if len(action_path) < action_path_limit:
					action_path.append(line.split(_ACTION_SUCCESS_MARKER, 1)[1].strip())
			if _ACTION_COUNT_MARKER in line:
				count_text = line.split(_ACTION_COUNT_MARKER, 1)[1].strip()
				if count_text.isdigit():
					action_count = max(action_count, int(count_text))

	if truncated:
		excerpt_parts.append("\n... [output truncated; full log is in the artifact file] ...\n")
	return _SingleOutputScan(
		excerpt="".join(excerpt_parts),
		marker_lines=tuple(marker_lines),
		action_path=tuple(action_path),
		action_count=action_count,
		truncated=truncated,
		action_path_truncated=action_count > len(action_path),
		has_execute_success=has_execute_success,
	)


def _empty_runtime_output_summary() -> RuntimeOutputSummary:
	return RuntimeOutputSummary(
		stdout_excerpt="",
		stderr_excerpt="",
		marker_output="",
		action_path=(),
		action_count=0,
		action_path_truncated=False,
		stdout_truncated=False,
		stderr_truncated=False,
		has_execute_success=False,
	)


def _extract_action_path(output: str) -> tuple[str, ...]:
	actions: list[str] = []
	for line in str(output or "").splitlines():
		marker = "runtime env action success "
		if marker not in line:
			continue
		actions.append(line.split(marker, 1)[1].strip())
	return tuple(actions)


def _decode_timeout_output(value: str | bytes | None) -> str:
	if value is None:
		return ""
	if isinstance(value, bytes):
		return value.decode("utf-8", errors="replace")
	return str(value)


def _artifact_paths(
	*,
	agentspeak_path: Path,
	mas2j_path: Path,
	environment_java_path: Path,
	belief_base_java_path: Path,
	initial_facts_path: Path,
	initial_percepts_path: Path,
	static_beliefs_path: Path,
	pddl_symbol_map_path: Path,
	temporal_monitor_path: Path,
	plan_trace_path: Path,
	committed_plan_trace_path: Path,
	plan_verifier_stdout_path: Path,
	plan_verifier_stderr_path: Path,
	stdout_path: Path,
	stderr_path: Path,
	result_path: Path,
) -> dict[str, str]:
	return {
		"agentspeak": str(agentspeak_path),
		"mas2j": str(mas2j_path),
		"environment_java": str(environment_java_path),
		"belief_base_java": str(belief_base_java_path),
		"initial_facts": str(initial_facts_path),
		"initial_percepts": str(initial_percepts_path),
		"static_beliefs": str(static_beliefs_path),
		"pddl_symbol_map": str(pddl_symbol_map_path),
		"temporal_dfa_monitor": str(temporal_monitor_path),
		"plan_trace": str(plan_trace_path),
		"committed_plan_trace": str(committed_plan_trace_path),
		"plan_verifier_stdout": str(plan_verifier_stdout_path),
		"plan_verifier_stderr": str(plan_verifier_stderr_path),
		"stdout": str(stdout_path),
		"stderr": str(stderr_path),
		"result": str(result_path),
	}
