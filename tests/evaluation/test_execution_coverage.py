from dataclasses import dataclass
import pytest

from evaluation.execution_coverage import Call, GroundBranch, Step, analyze_library


@dataclass
class Model:
	plans: tuple[GroundBranch, ...]

	def branches(self, goal, state):
		return tuple(p for p in self.plans if p.goal == goal)

	def execute(self, action, state):
		return 1 if action == Call("set_p") else None

	def satisfied(self, goal, state):
		return goal == Call("p") and state == 1


def test_duplicate_plans_do_not_double_count_coverage():
	goal = Call("p")
	plans = tuple(
		GroundBranch(name, goal, (Step("action", Call("set_p")),))
		for name in ("first", "overlapping")
	)
	result = analyze_library(Model(plans), ((goal, 0),))
	assert result.coverage == {"pass": 1, "fail": 0, "unknown": 0, "total": 1}
	assert result.correctness == {"pass": 2, "fail": 0, "unknown": 0, "total": 2}
	assert result.action_trace(0) == (Call("set_p"),)


def test_recursive_completion_uses_the_changed_state():
	goal = Call("p")
	recurse = GroundBranch("recursive", goal, (
		Step("action", Call("set_p")), Step("subgoal", goal),
	))
	base = GroundBranch("base", goal, ())
	model = Model((recurse, base))
	result = analyze_library(model, ((goal, 0),))
	assert result.root_statuses == ("pass",)
	assert result.correctness["pass"] == 1
	assert result.correctness["fail"] == 1
	assert result.action_trace(0) == (Call("set_p"),)


def test_unsupported_object_equality_is_not_silently_ignored(tmp_path):
	from evaluation.coverage_model import PDDLExecutionModel
	from evaluation.execution_coverage import UnsupportedModel
	from plan_library.models import PlanLibrary

	domain = tmp_path / "domain.pddl"
	problem = tmp_path / "problem.pddl"
	domain.write_text("""(define (domain test) (:requirements :strips :equality)
	 (:predicates (done)) (:action finish :parameters (?x ?y)
	 :precondition (= ?x ?y) :effect (done)))""")
	problem.write_text("""(define (problem p) (:domain test)
	 (:objects a b) (:init) (:goal (done)))""")
	with pytest.raises(UnsupportedModel, match="equality"):
		PDDLExecutionModel(domain, problem, PlanLibrary.from_dict({"plans": []}))


def test_a_cycle_without_a_base_case_is_not_a_proof():
	goal = Call("p")
	branch = GroundBranch("cycle", goal, (Step("subgoal", goal),))
	result = analyze_library(Model((branch,)), ((goal, 0),))
	assert result.complete
	assert result.root_statuses == ("fail",)
	assert result.correctness["fail"] == 1


def test_incomplete_analysis_is_unknown_not_failure():
	goal = Call("p")
	branch = GroundBranch("set", goal, (Step("action", Call("set_p")),))
	result = analyze_library(Model((branch,)), ((goal, 0),), max_configurations=1)
	assert not result.complete
	assert result.root_statuses == ("unknown",)
	assert result.correctness["unknown"] == 1


def test_pddl_adapter_checks_types_bindings_and_action_effects(tmp_path):
	from evaluation.coverage_model import PDDLExecutionModel
	from plan_library.models import PlanLibrary

	domain = tmp_path / "domain.pddl"
	problem = tmp_path / "problem.pddl"
	domain.write_text("""(define (domain test)
	 (:requirements :strips :typing) (:types item - object)
	 (:predicates (ready ?x - item) (done ?x - item))
	 (:action finish :parameters (?x - item) :precondition (ready ?x)
	  :effect (and (not (ready ?x)) (done ?x))))""")
	problem.write_text("""(define (problem p) (:domain test)
	 (:objects a b - item) (:init (ready a)) (:goal (done a)))""")
	plan = {"plan_name": "finish", "trigger": {"event_type": "achievement",
		"symbol": "done", "arguments": ["X"]},
		"context": ["ready(X)", "obj_tp(X, item)"],
		"body": [{"kind": "action", "symbol": "finish", "arguments": ["X"]}]}
	model = PDDLExecutionModel(domain, problem,
		PlanLibrary.from_dict({"domain_name": "test", "plans": [plan]}))
	result = analyze_library(model, ((Call("done", ("a",)), model.initial),
		(Call("done", ("b",)), model.initial)))
	assert result.root_statuses == ("pass", "fail")
	assert result.correctness == {"pass": 1, "fail": 0, "unknown": 0, "total": 1}
	assert result.action_trace(0) == (Call("finish", ("a",)),)
	assert model.execute(Call("finish", ("missing",)), model.initial) is None


def test_numeric_recursion_uses_exact_values_and_never_clips(tmp_path):
	from evaluation.coverage_model import PDDLExecutionModel
	from plan_library.models import PlanLibrary

	domain = tmp_path / "domain.pddl"
	problem = tmp_path / "problem.pddl"
	domain.write_text("""(define (domain counter) (:requirements :strips :fluents)
	 (:predicates (unused)) (:functions (count))
	 (:action dec :parameters () :precondition (> (count) 0)
	  :effect (decrease (count) 1)))""")
	problem.write_text("""(define (problem p) (:domain counter)
	 (:objects) (:init (= (count) 2)) (:goal (= (count) 0)))""")
	plans = [
		{"plan_name": "step", "trigger": {"symbol": "count", "arguments": ["0"]},
		 "context": ["count(N)", "N > 0"], "body": [
			 {"kind": "action", "symbol": "dec"},
			 {"kind": "subgoal", "symbol": "count", "arguments": ["0"]}]},
		{"plan_name": "base", "trigger": {"symbol": "count", "arguments": ["0"]},
		 "context": ["count(N)", "N == 0"], "body": []},
	]
	model = PDDLExecutionModel(domain, problem, PlanLibrary.from_dict({"plans": plans}))
	result = analyze_library(model, ((Call("count", ("0",)), model.initial),))
	assert result.root_statuses == ("pass",)
	assert result.action_trace(0) == (Call("dec"), Call("dec"))
	assert result.correctness["pass"] == 1


def test_witness_checker_rejects_an_invented_return_state():
	from dataclasses import replace
	from evaluation.execution_coverage import validate_proof
	goal = Call("p")
	branch = GroundBranch("set", goal, (Step("action", Call("set_p")),))
	model = Model((branch,))
	proof = analyze_library(model, ((goal, 0),)).root_proofs[0]
	assert validate_proof(model, proof) == (Call("set_p"),)
	with pytest.raises(ValueError, match="return"):
		validate_proof(model, replace(proof, end=0))


def test_subgoal_returns_are_not_replaced_by_independent_success_rates():
	class StatefulModel(Model):
		def execute(self, action, state):
			return {"set_p": 1, "consume_p": 2, "keep_p": 3}.get(action.symbol)

		def satisfied(self, goal, state):
			return state in ({"p": {1, 3}, "q": {2, 3}, "g": {3}}[goal.symbol])

	plans = (
		GroundBranch("root", Call("g"),
			(Step("subgoal", Call("p")), Step("subgoal", Call("q")))),
		GroundBranch("p", Call("p"), (Step("action", Call("set_p")),)),
		GroundBranch("q_bad", Call("q"), (Step("action", Call("consume_p")),)),
		GroundBranch("q_good", Call("q"), (Step("action", Call("keep_p")),)),
	)
	assert analyze_library(StatefulModel(plans[:-1]), ((Call("g"), 0),)).complete
	assert analyze_library(StatefulModel(plans[:-1]), ((Call("g"), 0),)).root_statuses == (
		"fail",)
	result = analyze_library(StatefulModel(plans), ((Call("g"), 0),))
	assert result.action_trace(0) == (Call("set_p"), Call("keep_p"))


def test_duplicate_requests_and_absent_contexts_have_correct_denominators():
	goal = Call("p")
	result = analyze_library(Model(()), ((goal, 0), (goal, 0)))
	assert result.coverage == {"pass": 0, "fail": 1, "unknown": 0, "total": 1}
	assert result.correctness["total"] == 0
	assert result.complete


def test_partial_root_binding_enumeration_does_not_claim_a_known_denominator():
	from evaluation.execution_coverage import AnalysisLimit
	class Limited(Model):
		def branches(self, goal, state):
			raise AnalysisLimit("binding_join_limit")
	result = analyze_library(Limited(()), ((Call("p"), 0),))
	assert result.root_statuses == ("unknown",)
	assert not result.root_enumeration_complete
