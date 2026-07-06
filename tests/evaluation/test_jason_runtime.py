from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

from evaluation.jason_runtime import JasonPlanLibraryRunner
from evaluation.jason_runtime.environment_adapter import JasonEnvironmentRuntimeAdapter
from evaluation.jason_runtime.runner import _build_environment_java_source
from evaluation.jason_runtime.runner import _build_indexed_belief_base_java_source
from evaluation.jason_runtime.runner import _build_runner_mas2j
from evaluation.jason_runtime.runner import _normalize_plan_verifier_command
from evaluation.jason_runtime.runner import _parse_pddl_patterns
from evaluation.jason_runtime.runner import _plan_verifier_output_success
from evaluation.jason_runtime.runner import _plan_verifier_not_attempted
from evaluation.jason_runtime.runner import _render_pddl_symbol_map
from evaluation.jason_runtime.runner import _run_plan_verifier
from evaluation.jason_runtime.runner import _run_process_streamed
from evaluation.jason_runtime.runner import _runtime_action_schema
from evaluation.jason_runtime.runner import _seed_facts
from evaluation.jason_runtime.runner import _scan_runtime_output_files
from evaluation.jason_runtime.runner import _split_seed_facts_for_jason_runtime
from utils.pddl_parser import PDDLAction
from utils.pddl_parser import PDDLDomain
from utils.pddl_parser import PDDLFact
from utils.pddl_parser import PDDLProblem


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
	assert schema.source_name == "pick-up"
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
	assert 'Paths.get("initial_percepts.txt")' in source
	assert 'Paths.get("jason_plan.plan")' in source
	assert 'Paths.get("pddl_symbol_map.tsv")' in source
	assert "Files.readAllLines(seedFactsPath, StandardCharsets.UTF_8)" in source
	assert "Files.readAllLines(initialPerceptsPath, StandardCharsets.UTF_8)" in source
	assert 'world.add("ready")' not in source
	assert "Boolean.parseBoolean(" in source
	assert '"jason.pipeline.planTraceEnabled"' in source
	assert 'System.getProperty("jason.pipeline.planTraceEnabled", "true")' in source
	assert "recordPlanAction(schema, action);" in source
	assert "private void flushPlanTrace()" in source
	assert "syncInitialPercepts();" in source
	assert "EffectDelta delta = applyEffects(schema.effects, bindings);" in source
	assert "syncPerceptDelta(delta);" in source
	assert "removePercept(Literal.parseLiteral(atom));" in source
	assert '"runtime_summary".equals(action.getFunctor())' in source
	assert "runtime env action count " in source
	assert "actionTraceLimit" in source
	assert '"jason.pipeline.actionTraceLimit",\n\t\t3' in source
	assert "import java.util.Arrays;" not in source
	assert "Arrays.stream" not in source
	assert "new StringBuilder(predicate)" in source
	assert "traceSuccessfulAction(schema, action);" in source
	assert "traceSuccessfulAction(String tracedAction)" not in source


def test_plan_verifier_command_normalization_and_not_configured_result(tmp_path: Path) -> None:
	assert _normalize_plan_verifier_command(None) is None
	assert _normalize_plan_verifier_command("Validate -v {domain_file}") == (
		"Validate",
		"-v",
		"{domain_file}",
	)
	assert _normalize_plan_verifier_command(("Validate", "{plan_file}")) == (
		"Validate",
		"{plan_file}",
	)

	result = _plan_verifier_not_attempted(
		stdout_path=tmp_path / "plan_verifier_stdout.txt",
		stderr_path=tmp_path / "plan_verifier_stderr.txt",
	)

	assert result.attempted is False
	assert result.available is False
	assert result.success is None
	assert result.error is None
	assert result.to_dict()["artifacts"]["stdout"].endswith("plan_verifier_stdout.txt")


def test_pddl_symbol_map_restores_original_object_names() -> None:
	domain = PDDLDomain(
		name="tiny",
		requirements=[],
		types=[],
		constants=["depot-1"],
		constant_types={},
		predicates=[],
		actions=[],
	)
	problem = PDDLProblem(
		name="tiny-problem",
		domain_name="tiny",
		objects=["block-1"],
		object_types={},
		init_facts=[PDDLFact("ready-at", ["block-1", "depot-1"])],
		goal_facts=[PDDLFact("done-at", ["block-1"])],
	)

	symbol_map = _render_pddl_symbol_map(domain=domain, problem=problem)

	assert "block_1\tblock-1\n" in symbol_map
	assert "depot_1\tdepot-1\n" in symbol_map


def test_plan_verifier_accepts_fake_val_output(tmp_path: Path) -> None:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	plan_file = tmp_path / "plan.plan"
	verifier = tmp_path / "fake_validate.py"
	stdout_path = tmp_path / "verifier.stdout.txt"
	stderr_path = tmp_path / "verifier.stderr.txt"
	domain_file.write_text("(define (domain tiny))\n", encoding="utf-8")
	problem_file.write_text("(define (problem tiny-problem) (:domain tiny))\n", encoding="utf-8")
	plan_file.write_text("(finish)\n", encoding="utf-8")
	verifier.write_text(
		"import sys\n"
		"print('Plan valid')\n"
		"print('|'.join(sys.argv[1:]))\n",
		encoding="utf-8",
	)

	result = _run_plan_verifier(
		explicit_command=(sys.executable, str(verifier)),
		require_verifier=True,
		domain_file=domain_file,
		problem_file=problem_file,
		plan_file=plan_file,
		output_dir=tmp_path,
		stdout_path=stdout_path,
		stderr_path=stderr_path,
		timeout_seconds=10,
	)

	assert result.success is True
	assert result.attempted is True
	assert result.available is True
	assert result.command[-3:] == (str(domain_file), str(problem_file), str(plan_file))
	assert "Plan valid" in result.stdout


def test_plan_verifier_output_rejects_explicit_failure() -> None:
	assert _plan_verifier_output_success(
		exit_code=0,
		timed_out=False,
		output="Plan valid",
	)
	assert not _plan_verifier_output_success(
		exit_code=0,
		timed_out=False,
		output="Plan failed: goal not satisfied",
	)


def test_runner_uses_project_indexed_belief_base() -> None:
	mas2j = _build_runner_mas2j("tiny")

	assert "beliefBaseClass JasonPipelineIndexedBeliefBase" in mas2j


def test_indexed_belief_base_indexes_bound_context_arguments() -> None:
	source = _build_indexed_belief_base_java_source()

	assert "extends DefaultBeliefBase" in source
	assert "getCandidateBeliefs(Literal literal, Unifier unifier)" in source
	assert "Literal contains(Literal literal)" in source
	assert "staticExactIndex" in source
	assert "dynamicExactIndex" in source
	assert "staticIndex" in source
	assert "dynamicIndex" in source
	assert "static_beliefs.txt" in source
	assert "loadStaticBeliefs();" in source
	assert "Literal liveCandidate = super.contains(candidate)" in source
	assert "return candidateIterator(staticExactMatches, dynamicExactMatches);" in source
	assert "private Literal nextLiveDynamic()" in source
	assert "return super.contains(candidate);" in source
	assert "candidates.addAll(staticBucket);" not in source
	assert "indexStaticLiteral(literal);" in source
	assert "indexDynamicLiteral(literal);" in source
	assert "term.capply(unifier)" in source
	assert "exactKeyIfBound(literal, unifier)" in source
	assert "bucketSize(staticBucket) + bucketSize(dynamicBucket)" in source
	assert "Collections.emptyIterator()" in source
	assert "deindexDynamicLiteral(literal)" in source
	assert "deindexStaticLiteral(literal)" in source
	assert "removeArgumentIndexLiteral" in source
	assert "public boolean remove(Literal literal)" in source
	assert "rebuildIndex();" not in source


def test_runtime_seed_facts_split_static_beliefs_from_dynamic_percepts() -> None:
	action = PDDLAction(
		name="move",
		parameters=["?from", "?to"],
		preconditions="(and (edge ?from ?to) (at ?from))",
		effects="(and (at ?to) (not (at ?from)))",
	)

	initial_percepts, static_beliefs = _split_seed_facts_for_jason_runtime(
		seed_facts=("edge(a,b)", "at(a)", "obj_tp(a,floor)"),
		action_schemas=(_runtime_action_schema(action),),
	)

	assert initial_percepts == ("at(a)",)
	assert static_beliefs == ("edge(a,b)", "obj_tp(a,floor)")


def test_runtime_seed_facts_include_obj_tp_type_closure(tmp_path: Path) -> None:
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text(
		"""
		(define (domain logistics-fragment)
		 (:requirements :strips :typing)
		 (:types locatable vehicle - object truck - vehicle package - locatable location)
		 (:predicates (at ?x - locatable ?l - location))
		 (:action move
		  :parameters (?t - truck ?from - location ?to - location)
		  :precondition (at ?t ?from)
		  :effect (and (not (at ?t ?from)) (at ?t ?to))
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file = tmp_path / "problem.pddl"
	problem_file.write_text(
		"""
		(define (problem p1)
		 (:domain logistics-fragment)
		 (:objects truck-0 - truck package-0 - package loc-0 loc-1 - location)
		 (:init (at truck-0 loc-0) (at package-0 loc-1))
		 (:goal (and (at truck-0 loc-1)))
		)
		""",
		encoding="utf-8",
	)

	facts = _seed_facts(domain_file=domain_file, problem_file=problem_file)

	assert "obj_tp(truck_0,truck)" in facts
	assert "obj_tp(truck_0,vehicle)" in facts
	assert "obj_tp(package_0,package)" in facts
	assert "obj_tp(package_0,locatable)" in facts
	assert "obj_tp(loc_0,location)" in facts
	assert "type_truck(truck_0)" not in facts


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


def test_runtime_output_scan_reads_bounded_trace_count_summary(tmp_path: Path) -> None:
	stdout_path = tmp_path / "stdout.txt"
	stderr_path = tmp_path / "stderr.txt"
	stdout_path.write_text(
		"\n".join(
			(
				"runtime env ready",
				"runtime env action success move(a,b)",
				"runtime env action success move(b,c)",
				"runtime env action count 100000",
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
		excerpt_char_limit=200,
		action_path_limit=10,
	)

	assert summary.action_count == 100000
	assert summary.action_path == ("move(a,b)", "move(b,c)")
	assert summary.action_path_truncated is True
	assert summary.has_execute_success is True


def test_runtime_output_scan_defaults_to_three_action_paths(tmp_path: Path) -> None:
	stdout_path = tmp_path / "stdout.txt"
	stderr_path = tmp_path / "stderr.txt"
	stdout_path.write_text(
		"\n".join(
			(
				"runtime env ready",
				"runtime env action success step1",
				"runtime env action success step2",
				"runtime env action success step3",
				"runtime env action success step4",
				"runtime env action count 4",
				"execute success",
			),
		)
		+ "\n",
		encoding="utf-8",
	)
	stderr_path.write_text("", encoding="utf-8")

	summary = _scan_runtime_output_files(stdout_path=stdout_path, stderr_path=stderr_path)

	assert summary.action_count == 4
	assert summary.action_path == ("step1", "step2", "step3")
	assert summary.action_path_truncated is True


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
	assert result.plan_verifier["attempted"] is False
	assert Path(result.artifacts["agentspeak"]).exists()
	assert Path(result.artifacts["plan_trace"]).exists()
	assert Path(result.artifacts["plan_trace"]).read_text(encoding="utf-8") == "(finish)\n"
	assert Path(result.artifacts["initial_facts"]).read_text(encoding="utf-8") == "ready\n"
	assert 'world.add("ready")' not in Path(result.artifacts["environment_java"]).read_text(
		encoding="utf-8",
	)
