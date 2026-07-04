from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

from evaluation.jason_runtime import JasonPlanLibraryRunner
from evaluation.jason_runtime.environment_adapter import JasonEnvironmentRuntimeAdapter
from evaluation.jason_runtime.runner import _build_environment_java_source
from evaluation.jason_runtime.runner import _parse_pddl_patterns
from evaluation.jason_runtime.runner import _run_process_streamed
from evaluation.jason_runtime.runner import _runtime_action_schema
from evaluation.jason_runtime.runner import _scan_runtime_output_files
from utils.pddl_parser import PDDLAction


def test_environment_adapter_requires_ready_and_success_markers() -> None:
	adapter = JasonEnvironmentRuntimeAdapter()

	success = adapter.validate(stdout="runtime env ready\n", stderr="[a] execute success\n")
	failure = adapter.validate(stdout="runtime env ready\nruntime env unknown action move(a)\n", stderr="")

	assert success.success is True
	assert failure.success is False
	assert failure.error == "environment reported action/runtime failure"


def test_pddl_action_schema_is_sanitized_for_jason_environment() -> None:
	action = PDDLAction(
		name="pick-up",
		parameters=["?x - block"],
		preconditions="(and (clear ?x) (not (holding ?x)))",
		effects="(and (holding ?x) (not (clear ?x)))",
	)

	schema = _runtime_action_schema(action)

	assert schema.functor == "pick_up"
	assert schema.parameters == ("x",)
	assert [(item.predicate, item.args, item.positive) for item in schema.preconditions] == [
		("clear", ("x",), True),
		("holding", ("x",), False),
	]
	assert [(item.predicate, item.args, item.positive) for item in schema.effects] == [
		("holding", ("x",), True),
		("clear", ("x",), False),
	]


def test_parse_pddl_patterns_supports_zero_arity_literals() -> None:
	patterns = _parse_pddl_patterns("(and (handempty) (not (holding ?x)))")

	assert [(item.predicate, item.args, item.positive) for item in patterns] == [
		("handempty", (), True),
		("holding", ("x",), False),
	]


def test_environment_source_loads_initial_facts_from_data_file() -> None:
	action = PDDLAction(
		name="finish",
		parameters=[],
		preconditions="(ready)",
		effects="(and (done) (not (ready)))",
	)

	source = _build_environment_java_source(
		class_name="JasonPipelineEnvironment",
		action_schemas=(_runtime_action_schema(action),),
		seed_facts_file_name="initial_facts.txt",
	)

	assert 'Paths.get("initial_facts.txt")' in source
	assert "Files.readAllLines(seedFactsPath, StandardCharsets.UTF_8)" in source
	assert 'world.add("ready")' not in source
	assert "syncInitialPercepts();" in source
	assert "EffectDelta delta = applyEffects(schema.effects, bindings);" in source
	assert "syncPerceptDelta(delta);" in source
	assert "removePercept(Literal.parseLiteral(atom));" in source


def test_streamed_process_writes_stdout_and_stderr_to_files(tmp_path: Path) -> None:
	stdout_path = tmp_path / "stdout.txt"
	stderr_path = tmp_path / "stderr.txt"

	result = _run_process_streamed(
		(
			sys.executable,
			"-c",
			"import sys; print('runtime env ready'); print('execute success', file=sys.stderr)",
		),
		cwd=tmp_path,
		stdout_path=stdout_path,
		stderr_path=stderr_path,
		timeout_seconds=10,
	)

	assert result.exit_code == 0
	assert result.timed_out is False
	assert stdout_path.read_text(encoding="utf-8") == "runtime env ready\n"
	assert stderr_path.read_text(encoding="utf-8") == "execute success\n"


def test_runtime_output_scan_keeps_bounded_excerpt_and_true_action_count(tmp_path: Path) -> None:
	stdout_path = tmp_path / "stdout.txt"
	stderr_path = tmp_path / "stderr.txt"
	stdout_path.write_text(
		"\n".join(
			(
				"runtime env ready",
				"runtime env action success move(a,b)",
				"runtime env action success move(b,c)",
				"runtime env action success move(c,d)",
				"execute success",
			),
		)
		+ "\n",
		encoding="utf-8",
	)
	stderr_path.write_text("", encoding="utf-8")

	summary = _scan_runtime_output_files(
		stdout_path=stdout_path,
		stderr_path=stderr_path,
		excerpt_char_limit=20,
		action_path_limit=2,
	)

	assert summary.action_count == 3
	assert summary.action_path == ("move(a,b)", "move(b,c)")
	assert summary.action_path_truncated is True
	assert summary.stdout_truncated is True
	assert "runtime env ready" in summary.marker_output
	assert "execute success" in summary.marker_output
	assert summary.has_execute_success is True


@pytest.mark.skipif(
	not (shutil.which("java") and shutil.which("javac") and shutil.which("mvn")),
	reason="real Jason validation requires java, javac, and Maven",
)
def test_jason_runner_executes_tiny_pddl_environment(tmp_path: Path) -> None:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	library_file = tmp_path / "plan_library.asl"
	output_dir = tmp_path / "jason"
	domain_file.write_text(
		"""
(define (domain tiny)
  (:requirements :strips)
  (:predicates (ready) (done))
  (:action finish
    :parameters ()
    :precondition (ready)
    :effect (and (done) (not (ready))))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
(define (problem tiny-problem)
  (:domain tiny)
  (:init (ready))
  (:goal (and (done)))
)
""".strip()
		+ "\n",
		encoding="utf-8",
	)
	library_file.write_text(
		"""
/* Generated AgentSpeak(L) Plan Library */
/* Domain: tiny */

+!done : done <-
	true.

+!done : ready <-
	finish.

+!g_query : not done <-
	!done;
	!g_query.

+!g_query : done <-
	true.
""".strip()
		+ "\n",
		encoding="utf-8",
	)

	result = JasonPlanLibraryRunner(timeout_seconds=20).validate(
		domain_file=domain_file,
		problem_file=problem_file,
		plan_library_asl=library_file,
		goal_name="g_query",
		output_dir=output_dir,
	)

	assert result.success is True, result.to_dict()
	assert result.action_path == ("finish()",)
	assert result.action_count == 1
	assert "execute success" in f"{result.stdout}\n{result.stderr}"
	assert result.output_summary["stdout_truncated"] is False
	assert result.output_summary["stderr_truncated"] is False
	assert Path(result.artifacts["agentspeak"]).exists()
	assert Path(result.artifacts["initial_facts"]).read_text(encoding="utf-8") == "ready\n"
	assert 'world.add("ready")' not in Path(result.artifacts["environment_java"]).read_text(
		encoding="utf-8",
	)
