from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from evaluation.jason_runtime import JasonPlanLibraryRunner
from evaluation.jason_runtime.environment_adapter import JasonEnvironmentRuntimeAdapter
from evaluation.jason_runtime.runner import _build_environment_java_source
from evaluation.jason_runtime.runner import _parse_pddl_patterns
from evaluation.jason_runtime.runner import _runtime_action_schema
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
	assert "execute success" in f"{result.stdout}\n{result.stderr}"
	assert Path(result.artifacts["agentspeak"]).exists()
	assert Path(result.artifacts["initial_facts"]).read_text(encoding="utf-8") == "ready\n"
	assert 'world.add("ready")' not in Path(result.artifacts["environment_java"]).read_text(
		encoding="utf-8",
	)
