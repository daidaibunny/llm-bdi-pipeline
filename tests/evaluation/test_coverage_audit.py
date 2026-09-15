def test_unknown_bounds_do_not_drop_unsolved_obligations():
	from evaluation.coverage_audit import metric_bounds
	assert metric_bounds({"pass": 3, "fail": 1, "unknown": 2, "total": 6}) == {
		"lower": 0.5, "upper": 5 / 6,
	}
	assert metric_bounds({"pass": 0, "fail": 0, "unknown": 0, "total": 0}) is None


def test_goal_population_deduplicates_overlapping_atoms_and_includes_numeric():
	from evaluation.coverage_audit import problem_targets
	from utils.pddl_parser import (PDDLFact, PDDLNumericCondition,
		PDDLNumericExpression, PDDLProblem)
	problem = PDDLProblem("p", "d", [], {}, [],
		[PDDLFact("p", ["a"]), PDDLFact("p", ["a"])], [],
		[PDDLNumericCondition("=", PDDLNumericExpression("fluent", "fuel", ["v"]),
			PDDLNumericExpression("constant", "0"))])
	assert [(call.symbol, call.arguments) for call in problem_targets(problem)] == [
		("fuel", ("v", "0")), ("p", ("a",)),
	]
