"""Run current PDDL-only AgentSpeak(L) libraries in the Jason interpreter."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from domain_level_planning.pddl_types import object_type_atoms
from domain_level_planning.pddl_types import parameter_name
from plan_library.rendering import sanitize_identifier
from utils.pddl_parser import PDDLAction
from utils.pddl_parser import PDDLParser

from .environment_adapter import Stage6EnvironmentAdapter
from .environment_adapter import build_environment_adapter


_RUNTIME_OUTPUT_EXCERPT_MAX_CHARS = 20_000
_RUNTIME_ACTION_PATH_MAX_ITEMS = 1_000
_ACTION_SUCCESS_MARKER = "runtime env action success "
_ADAPTER_MARKERS = (
	"runtime env ready",
	"runtime env action failed",
	"runtime env unknown action",
	"runtime env compile failed",
	"execute success",
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
class RuntimeActionSchema:
	"""PDDL action schema lowered to the Jason Java environment."""

	functor: str
	source_name: str
	parameters: tuple[str, ...]
	preconditions: tuple[PredicatePattern, ...]
	effects: tuple[PredicatePattern, ...]


@dataclass(frozen=True)
class StreamedProcessResult:
	"""Result for a subprocess whose stdout/stderr were streamed to files."""

	exit_code: int | None
	timed_out: bool


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
		timeout_seconds: int = 60,
		environment_adapter: Stage6EnvironmentAdapter | None = None,
		jason_classpath: str | None = None,
	) -> None:
		self.timeout_seconds = timeout_seconds
		self.environment_adapter = environment_adapter or build_environment_adapter()
		self.jason_classpath = jason_classpath

	def validate(
		self,
		*,
		domain_file: str | Path,
		problem_file: str | Path,
		plan_library_asl: str | Path,
		goal_name: str,
		output_dir: str | Path,
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
		domain = PDDLParser.parse_domain(domain_path)
		seed_facts = _seed_facts(domain_file=domain_path, problem_file=problem_path)
		action_schemas = tuple(_runtime_action_schema(action) for action in domain.actions)
		timing_profile["parse_seconds"] = time.perf_counter() - parse_start

		if not action_schemas:
			raise JasonValidationError(
				"Jason validation requires at least one PDDL action schema.",
				metadata={"domain_file": str(domain_path)},
			)

		resolve_start = time.perf_counter()
		java_bin = shutil.which("java")
		javac_bin = shutil.which("javac")
		if not java_bin or not javac_bin:
			raise JasonValidationError(
				"Jason validation requires both java and javac on PATH.",
				metadata={"java": java_bin, "javac": javac_bin},
			)
		classpath = self.jason_classpath or _resolve_jason_classpath(
			self.default_jason_maven_artifact,
		)
		timing_profile["runtime_resolution_seconds"] = time.perf_counter() - resolve_start

		materialize_start = time.perf_counter()
		runner_asl = _build_runner_asl(
			plan_library_asl=library_path.read_text(encoding="utf-8"),
			goal_name=goal_name,
		)
		runner_mas2j = _build_runner_mas2j(domain.name)
		environment_java = _build_environment_java_source(
			class_name=self.environment_class_name,
			action_schemas=action_schemas,
			seed_facts_file_name="initial_facts.txt",
		)
		logging_properties = _logging_properties()

		agentspeak_path = output_path / "agentspeak_generated.asl"
		mas2j_path = output_path / "jason_runner.mas2j"
		environment_java_path = output_path / f"{self.environment_class_name}.java"
		initial_facts_path = output_path / "initial_facts.txt"
		logging_path = output_path / "logging.properties"
		stdout_path = output_path / "jason_stdout.txt"
		stderr_path = output_path / "jason_stderr.txt"
		result_path = output_path / "jason_validation.json"

		agentspeak_path.write_text(runner_asl, encoding="utf-8")
		mas2j_path.write_text(runner_mas2j, encoding="utf-8")
		environment_java_path.write_text(environment_java, encoding="utf-8")
		initial_facts_path.write_text(
			"\n".join(seed_facts) + ("\n" if seed_facts else ""),
			encoding="utf-8",
		)
		logging_path.write_text(logging_properties, encoding="utf-8")
		timing_profile["materialize_seconds"] = time.perf_counter() - materialize_start

		compile_start = time.perf_counter()
		compile_process = subprocess.run(
			[
				javac_bin,
				"-cp",
				classpath,
				environment_java_path.name,
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
				artifacts=_artifact_paths(
					agentspeak_path=agentspeak_path,
					mas2j_path=mas2j_path,
					environment_java_path=environment_java_path,
					initial_facts_path=initial_facts_path,
					stdout_path=stdout_path,
					stderr_path=stderr_path,
					result_path=result_path,
				),
				timing_profile=timing_profile,
				output_summary=_empty_runtime_output_summary().to_dict(),
				error=error,
			)
			result_path.write_text(json.dumps(result.to_dict(), indent=2) + "\n", encoding="utf-8")
			return result

		run_start = time.perf_counter()
		run_classpath = os.pathsep.join((classpath, str(output_path)))
		cmd = [
			java_bin,
			"-Djava.awt.headless=true",
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
		success = (
			not timed_out
			and exit_code == 0
			and adapter_result.success
			and output_summary.has_execute_success
		)
		status = "success" if success else "failed"
		error_message = None
		if timed_out:
			status = "timeout"
			error_message = f"Jason validation exceeded {self.timeout_seconds} seconds."
		elif exit_code != 0:
			error_message = f"Jason process exited with code {exit_code}."
		elif not adapter_result.success:
			error_message = adapter_result.error

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
			artifacts=_artifact_paths(
				agentspeak_path=agentspeak_path,
				mas2j_path=mas2j_path,
				environment_java_path=environment_java_path,
				initial_facts_path=initial_facts_path,
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


def _seed_facts(*, domain_file: Path, problem_file: Path) -> tuple[str, ...]:
	domain = PDDLParser.parse_domain(domain_file)
	problem = PDDLParser.parse_problem(problem_file)
	facts = [
		_call(fact.predicate, fact.args)
		for fact in problem.init_facts
		if fact.is_positive
	]
	facts.extend(object_type_atoms(problem, domain.types))
	return tuple(dict.fromkeys(_render_runtime_atom(fact) for fact in facts))


def _runtime_action_schema(action: PDDLAction) -> RuntimeActionSchema:
	return RuntimeActionSchema(
		functor=sanitize_identifier(action.name),
		source_name=sanitize_identifier(action.name),
		parameters=tuple(
			sanitize_identifier(parameter_name(parameter).lstrip("?"))
			for parameter in tuple(action.parameters or ())
		),
		preconditions=tuple(_parse_pddl_patterns(action.preconditions)),
		effects=tuple(_parse_pddl_patterns(action.effects)),
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
		"    agents: agentspeak_generated;\n"
		"    aslSourcePath: \".\";\n"
		"}\n"
	)


def _build_environment_java_source(
	*,
	class_name: str,
	action_schemas: Sequence[RuntimeActionSchema],
	seed_facts_file_name: str,
) -> str:
	action_lines = "\n\t\t".join(
		_render_action_registration(schema)
		for schema in tuple(action_schemas or ())
	)
	if not action_lines:
		action_lines = "// no action schemas"
	seed_file = _java_quote(seed_facts_file_name)
	return f"""
import jason.asSyntax.Literal;
import jason.asSyntax.Structure;
import jason.environment.Environment;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Arrays;
import java.util.HashMap;
import java.util.LinkedHashSet;
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

	private static final class ActionSchema {{
		final String name;
		final String sourceName;
		final String[] parameters;
		final Pattern[] preconditions;
		final Pattern[] effects;

		ActionSchema(
			String name,
			String sourceName,
			String[] parameters,
			Pattern[] preconditions,
			Pattern[] effects
		) {{
			this.name = name;
			this.sourceName = sourceName;
			this.parameters = parameters;
			this.preconditions = preconditions;
			this.effects = effects;
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

	private final Set<String> world = new LinkedHashSet<>();
	private final Set<String> perceived = new LinkedHashSet<>();
	private final Map<String, ActionSchema> actions = new HashMap<>();
	private final Path seedFactsPath = Paths.get({seed_file});

	@Override
	public synchronized void init(String[] args) {{
		super.init(args);
		seedInitialFacts();
		loadActions();
		syncInitialPercepts();
		System.out.println("runtime env ready");
	}}

	@Override
	public synchronized boolean executeAction(String agName, Structure action) {{
		if ("true".equals(action.getFunctor()) && action.getArity() == 0) {{
			return true;
		}}
		ActionSchema schema = actions.get(action.getFunctor());
		if (schema == null) {{
			System.out.println("runtime env unknown action " + action);
			return false;
		}}
		String tracedAction = renderTraceAction(schema.sourceName, action);
		if (action.getArity() != schema.parameters.length) {{
			System.out.println("runtime env action failed " + tracedAction + " reason=arity");
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

		if (!checkPreconditions(schema.preconditions, bindings)) {{
			System.out.println("runtime env action failed " + tracedAction + " reason=precondition");
			return false;
		}}

		EffectDelta delta = applyEffects(schema.effects, bindings);
		syncPerceptDelta(delta);
		System.out.println("runtime env action success " + tracedAction);
		return true;
	}}

	private void seedInitialFacts() {{
		world.clear();
		try {{
			for (String line : Files.readAllLines(seedFactsPath, StandardCharsets.UTF_8)) {{
				String fact = line.trim();
				if (!fact.isEmpty() && !fact.startsWith("#")) {{
					world.add(fact);
				}}
			}}
		}} catch (IOException error) {{
			throw new RuntimeException(
				"Failed to load Jason initial facts from " + seedFactsPath.toAbsolutePath(),
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

	private EffectDelta applyEffects(Pattern[] effects, Map<String, String> bindings) {{
		Set<String> added = new LinkedHashSet<>();
		Set<String> removed = new LinkedHashSet<>();
		for (Pattern pattern : effects) {{
			if (pattern.positive) {{
				continue;
			}}
			String grounded = ground(pattern.predicate, pattern.args, bindings);
			if (world.remove(grounded) && !added.remove(grounded)) {{
				removed.add(grounded);
			}}
		}}
		for (Pattern pattern : effects) {{
			if (!pattern.positive) {{
				continue;
			}}
			String grounded = ground(pattern.predicate, pattern.args, bindings);
			if (world.add(grounded) && !removed.remove(grounded)) {{
				added.add(grounded);
			}}
		}}
		return new EffectDelta(added, removed);
	}}

	private String ground(String predicate, String[] args, Map<String, String> bindings) {{
		if (args.length == 0) {{
			return predicate;
		}}
		String[] groundedArgs = Arrays.stream(args)
			.map(arg -> renderTerm(resolveToken(arg, bindings)))
			.toArray(String[]::new);
		return predicate + "(" + String.join(",", groundedArgs) + ")";
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

	private void syncInitialPercepts() {{
		clearPercepts();
		perceived.clear();
		for (String atom : world) {{
			addPercept(Literal.parseLiteral(atom));
			perceived.add(atom);
		}}
		informAgsEnvironmentChanged();
	}}

	private void syncPerceptDelta(EffectDelta delta) {{
		if (!delta.changed()) {{
			return;
		}}
		for (String atom : delta.removed) {{
			if (perceived.remove(atom)) {{
				removePercept(Literal.parseLiteral(atom));
			}}
		}}
		for (String atom : delta.added) {{
			if (perceived.add(atom)) {{
				addPercept(Literal.parseLiteral(atom));
			}}
		}}
		informAgsEnvironmentChanged();
	}}
}}
""".strip() + "\n"


def _render_action_registration(schema: RuntimeActionSchema) -> str:
	parameters = ", ".join(_java_quote(parameter) for parameter in schema.parameters)
	preconditions = ", ".join(_render_pattern_java(pattern) for pattern in schema.preconditions)
	effects = ", ".join(_render_pattern_java(pattern) for pattern in schema.effects)
	return (
		"register(new ActionSchema("
		f"{_java_quote(schema.functor)}, "
		f"{_java_quote(schema.source_name)}, "
		f"new String[]{{{parameters}}}, "
		f"new Pattern[]{{{preconditions}}}, "
		f"new Pattern[]{{{effects}}}"
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
	initial_facts_path: Path,
	stdout_path: Path,
	stderr_path: Path,
	result_path: Path,
) -> dict[str, str]:
	return {
		"agentspeak": str(agentspeak_path),
		"mas2j": str(mas2j_path),
		"environment_java": str(environment_java_path),
		"initial_facts": str(initial_facts_path),
		"stdout": str(stdout_path),
		"stderr": str(stderr_path),
		"result": str(result_path),
	}
