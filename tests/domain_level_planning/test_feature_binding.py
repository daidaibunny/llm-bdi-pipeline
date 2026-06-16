from __future__ import annotations

from pathlib import Path

from domain_level_planning import (
	SketchCompilationTarget,
	bind_goal_aligned_action_effect_candidates,
	bind_recoverable_dlplan_features,
	bind_unique_action_effect_candidates,
	compile_bound_sketch_to_asl_library,
	parse_dlplan_policy,
)
from plan_library.rendering import render_plan_library_asl
from utils.pddl_parser import PDDLParser


def test_bind_goal_aligned_role_count_to_lifted_subgoal_context(tmp_path: Path) -> None:
	domain = _write_domain(tmp_path)
	policy = parse_dlplan_policy(
		"""
		(:policy
		(:booleans )
		(:numericals
		 (f1 "n_count(c_equal(r_primitive(on,0,1),r_primitive(on_g,0,1)))")
		)
		(:rule (:conditions ) (:effects (:e_n_inc f1)))
		)
		""",
	)

	report = bind_recoverable_dlplan_features(
		policy=policy,
		domain=PDDLParser.parse_domain(domain),
	)

	assert report.unsupported_features == {}

	plan_library = compile_bound_sketch_to_asl_library(
		domain_name="generic-blocks",
		policy=policy,
		target=SketchCompilationTarget(symbol="g", recurse=True),
		feature_bindings=report.bindings,
	)
	asl = render_plan_library_asl(plan_library)

	assert "+!g : goal_on(X0, X1) & not on(X0, X1) <-" in asl
	assert "\t!on(X0, X1);" in asl
	assert "\t!g." in asl


def test_bind_primitive_concept_count_to_lifted_subgoal(tmp_path: Path) -> None:
	domain = _write_domain(tmp_path)
	policy = parse_dlplan_policy(
		"""
		(:policy
		(:booleans )
		(:numericals (f1 "n_count(c_primitive(clear,0))"))
		(:rule (:conditions (:c_n_eq f1)) (:effects (:e_n_inc f1)))
		)
		""",
	)

	report = bind_recoverable_dlplan_features(
		policy=policy,
		domain=PDDLParser.parse_domain(domain),
	)
	plan_library = compile_bound_sketch_to_asl_library(
		domain_name="generic-blocks",
		policy=policy,
		target=SketchCompilationTarget(symbol="clear", arguments=("X0",), recurse=False),
		feature_bindings=report.bindings,
	)
	asl = render_plan_library_asl(plan_library)

	assert report.unsupported_features == {}
	assert "+!clear(X0) : not clear(X0) <-" in asl
	assert "\t!clear(X0)." in asl


def test_bind_primitive_role_count_to_lifted_subgoal(tmp_path: Path) -> None:
	domain = _write_domain(tmp_path)
	policy = parse_dlplan_policy(
		"""
		(:policy
		(:booleans )
		(:numericals (f1 "n_count(r_primitive(on,0,1))"))
		(:rule (:conditions (:c_n_eq f1)) (:effects (:e_n_inc f1)))
		)
		""",
	)

	report = bind_recoverable_dlplan_features(
		policy=policy,
		domain=PDDLParser.parse_domain(domain),
	)
	plan_library = compile_bound_sketch_to_asl_library(
		domain_name="generic-blocks",
		policy=policy,
		target=SketchCompilationTarget(symbol="g", recurse=False),
		feature_bindings=report.bindings,
	)
	asl = render_plan_library_asl(plan_library)

	assert report.unsupported_features == {}
	assert "+!g : not on(X0, X1) <-" in asl
	assert "\t!on(X0, X1)." in asl


def test_binding_diagnostics_explain_supported_feature_bindings(
	tmp_path: Path,
) -> None:
	domain = _write_domain(tmp_path)
	policy = parse_dlplan_policy(
		"""
		(:policy
		(:booleans )
		(:numericals (f1 "n_count(r_primitive(on,0,1))"))
		(:rule (:conditions (:c_n_eq f1)) (:effects (:e_n_inc f1)))
		)
		""",
	)

	report = bind_recoverable_dlplan_features(
		policy=policy,
		domain=PDDLParser.parse_domain(domain),
	)

	diagnostic = report.feature_diagnostics["f1"]
	assert diagnostic.feature_id == "f1"
	assert diagnostic.status == "bound"
	assert diagnostic.binding_kind == "primitive_role_count"
	assert diagnostic.condition_operators == ("c_n_eq", "c_n_gt")
	assert diagnostic.effect_operators == ("e_n_bot", "e_n_inc")
	assert diagnostic.action_candidate_count == 1
	assert diagnostic.rejection_reason is None
	assert diagnostic.to_dict() == {
		"feature_id": "f1",
		"expression": "n_count(r_primitive(on,0,1))",
		"status": "bound",
		"binding_kind": "primitive_role_count",
		"condition_operators": ("c_n_eq", "c_n_gt"),
		"effect_operators": ("e_n_bot", "e_n_inc"),
		"action_candidate_count": 1,
		"promoted_effect_operators": (),
		"rejection_reason": None,
	}


def test_primitive_role_count_reports_decreasing_action_candidates(
	tmp_path: Path,
) -> None:
	domain = _write_domain(tmp_path)
	policy = parse_dlplan_policy(
		"""
		(:policy
		(:booleans )
		(:numericals (f1 "n_count(r_primitive(on,0,1))"))
		(:rule (:conditions (:c_n_gt f1)) (:effects (:e_n_dec f1)))
		)
		""",
	)

	report = bind_recoverable_dlplan_features(
		policy=policy,
		domain=PDDLParser.parse_domain(domain),
	)

	candidates = report.action_effect_candidates["f1"]
	assert tuple(candidate.action_name for candidate in candidates) == ("remove",)
	assert candidates[0].operator == "e_n_dec"
	assert candidates[0].effect_predicate == "on"
	assert candidates[0].context == ("on(X, Y)", "clear(X)")
	assert candidates[0].body[0].arguments == ("X", "Y")


def test_bind_nullary_boolean_feature_to_lifted_subgoal(tmp_path: Path) -> None:
	domain = _write_domain(tmp_path)
	policy = parse_dlplan_policy(
		"""
		(:policy
		(:booleans (f1 "b_nullary(handempty)"))
		(:numericals )
		(:rule (:conditions (:c_b_neg f1)) (:effects (:e_b_pos f1)))
		)
		""",
	)

	report = bind_recoverable_dlplan_features(
		policy=policy,
		domain=PDDLParser.parse_domain(domain),
	)
	plan_library = compile_bound_sketch_to_asl_library(
		domain_name="generic-blocks",
		policy=policy,
		target=SketchCompilationTarget(symbol="g", recurse=False),
		feature_bindings=report.bindings,
	)
	asl = render_plan_library_asl(plan_library)

	assert report.unsupported_features == {}
	assert "+!g : not handempty <-" in asl
	assert "\t!handempty." in asl


def test_nullary_boolean_feature_reports_delete_action_candidates(
	tmp_path: Path,
) -> None:
	domain = _write_domain(tmp_path)
	policy = parse_dlplan_policy(
		"""
		(:policy
		(:booleans (f1 "b_nullary(handempty)"))
		(:numericals )
		(:rule (:conditions (:c_b_pos f1)) (:effects (:e_b_neg f1)))
		)
		""",
	)

	report = bind_recoverable_dlplan_features(
		policy=policy,
		domain=PDDLParser.parse_domain(domain),
	)

	candidates = report.action_effect_candidates["f1"]
	assert tuple(candidate.action_name for candidate in candidates) == ("pick",)
	assert candidates[0].operator == "e_b_neg"
	assert candidates[0].effect_predicate == "handempty"
	assert candidates[0].context == ("handempty", "clear(X)")
	assert candidates[0].body[0].arguments == ("X",)


def test_binding_reports_unsupported_complex_dlplan_features(tmp_path: Path) -> None:
	domain = _write_domain(tmp_path)
	policy = parse_dlplan_policy(
		"""
		(:policy
		(:booleans )
		(:numericals
		 (f137 "n_concept_distance(c_one_of(b1),r_restrict(r_primitive(on,0,1),c_one_of(b2)),c_primitive(on-table,0))")
		)
		(:rule (:conditions (:c_n_gt f137)) (:effects (:e_n_dec f137)))
		)
		""",
	)

	report = bind_recoverable_dlplan_features(
		policy=policy,
		domain=PDDLParser.parse_domain(domain),
	)

	assert report.bindings == {}
	assert report.unsupported_features == {
		"f137": (
			"n_concept_distance(c_one_of(b1),r_restrict(r_primitive(on,0,1),"
			"c_one_of(b2)),c_primitive(on-table,0))"
		),
	}
	diagnostic = report.feature_diagnostics["f137"]
	assert diagnostic.status == "unsupported"
	assert diagnostic.binding_kind == "unsupported"
	assert diagnostic.condition_operators == ()
	assert diagnostic.effect_operators == ()
	assert diagnostic.action_candidate_count == 0
	assert diagnostic.rejection_reason == (
		"unsupported_dlplan_feature_expression_or_domain_vocabulary"
	)


def test_binding_reports_action_candidates_for_decreasing_primitive_counts(
	tmp_path: Path,
) -> None:
	domain = _write_domain(tmp_path, include_place=True)
	policy = parse_dlplan_policy(
		"""
		(:policy
		(:booleans )
		(:numericals (f1 "n_count(c_primitive(holding,0))"))
		(:rule (:conditions (:c_n_gt f1)) (:effects (:e_n_dec f1)))
		)
		""",
	)

	report = bind_recoverable_dlplan_features(
		policy=policy,
		domain=PDDLParser.parse_domain(domain),
	)

	candidates = report.action_effect_candidates["f1"]
	assert tuple(candidate.action_name for candidate in candidates) == (
		"drop",
		"place",
	)
	assert candidates[0].operator == "e_n_dec"
	assert candidates[0].effect_predicate == "holding"
	assert candidates[0].context == ("holding(X)",)
	assert candidates[0].body[0].symbol == "drop"
	assert candidates[1].context == ("holding(X)", "clear(Y)")
	assert candidates[1].body[0].arguments == ("X", "Y")


def test_unique_action_candidate_can_be_promoted_to_executable_binding(
	tmp_path: Path,
) -> None:
	domain = _write_domain(tmp_path, include_place=False)
	policy = parse_dlplan_policy(
		"""
		(:policy
		(:booleans )
		(:numericals (f1 "n_count(c_primitive(holding,0))"))
		(:rule (:conditions (:c_n_gt f1)) (:effects (:e_n_dec f1)))
		)
		""",
	)

	report = bind_unique_action_effect_candidates(
		bind_recoverable_dlplan_features(
			policy=policy,
			domain=PDDLParser.parse_domain(domain),
		),
	)
	plan_library = compile_bound_sketch_to_asl_library(
		domain_name="generic-blocks",
		policy=policy,
		target=SketchCompilationTarget(symbol="g", recurse=False),
		feature_bindings=report.bindings,
	)
	asl = render_plan_library_asl(plan_library)

	assert "+!g : holding(X) <-" in asl
	assert "\tdrop(X)." in asl


def test_multiple_action_candidates_remain_ambiguous_instead_of_guessing(
	tmp_path: Path,
) -> None:
	domain = _write_domain(tmp_path, include_place=True)
	policy = parse_dlplan_policy(
		"""
		(:policy
		(:booleans )
		(:numericals (f1 "n_count(c_primitive(holding,0))"))
		(:rule (:conditions (:c_n_gt f1)) (:effects (:e_n_dec f1)))
		)
		""",
	)

	report = bind_unique_action_effect_candidates(
		bind_recoverable_dlplan_features(
			policy=policy,
			domain=PDDLParser.parse_domain(domain),
		),
	)

	assert len(report.action_effect_candidates["f1"]) == 2
	feature_binding = report.bindings["f1"]
	assert "e_n_dec" not in feature_binding.effect_body
	diagnostic = report.feature_diagnostics["f1"]
	assert diagnostic.status == "bound"
	assert diagnostic.action_candidate_count == 2
	assert diagnostic.promoted_effect_operators == ()


def test_goal_aligned_feature_effect_disambiguates_action_candidates(
	tmp_path: Path,
) -> None:
	domain = _write_domain(tmp_path, include_place=True)
	policy = parse_dlplan_policy(
		"""
		(:policy
		(:booleans )
		(:numericals
		 (f_on "n_count(c_equal(r_primitive(on,0,1),r_primitive(on_g,0,1)))")
		 (f_holding "n_count(c_primitive(holding,0))")
		)
		(:rule (:conditions )
		 (:effects (:e_n_inc f_on) (:e_n_dec f_holding)))
		)
		""",
	)

	report = bind_goal_aligned_action_effect_candidates(
		policy=policy,
		report=bind_recoverable_dlplan_features(
			policy=policy,
			domain=PDDLParser.parse_domain(domain),
		),
	)
	plan_library = compile_bound_sketch_to_asl_library(
		domain_name="generic-blocks",
		policy=policy,
		target=SketchCompilationTarget(symbol="g", recurse=False),
		feature_bindings=report.bindings,
	)
	asl = render_plan_library_asl(plan_library)

	assert "+!g : goal_on(X0, X1) & not on(X0, X1) & holding(X0) & clear(X1) <-" in asl
	assert "\t!on(X0, X1);" in asl
	assert "\tplace(X0, X1)." in asl
	assert "\tdrop(X)" not in asl


def test_goal_aligned_feature_prior_disambiguates_auxiliary_effect_rules(
	tmp_path: Path,
) -> None:
	domain = _write_domain(tmp_path, include_place=True)
	policy = parse_dlplan_policy(
		"""
		(:policy
		(:booleans )
		(:numericals
		 (f_on "n_count(c_equal(r_primitive(on,0,1),r_primitive(on_g,0,1)))")
		 (f_holding "n_count(c_primitive(holding,0))")
		)
		(:rule (:conditions (:c_n_gt f_holding) (:c_n_gt f_on))
		 (:effects (:e_n_dec f_holding)))
		)
		""",
	)

	report = bind_goal_aligned_action_effect_candidates(
		policy=policy,
		report=bind_recoverable_dlplan_features(
			policy=policy,
			domain=PDDLParser.parse_domain(domain),
		),
	)
	plan_library = compile_bound_sketch_to_asl_library(
		domain_name="generic-blocks",
		policy=policy,
		target=SketchCompilationTarget(symbol="g", recurse=False),
		feature_bindings=report.bindings,
	)
	asl = render_plan_library_asl(plan_library)

	assert "+!g : goal_on(X0, X1) & not on(X0, X1) & holding(X0) & clear(X1) <-" in asl
	assert "\tplace(X0, X1)." in asl
	assert "\tdrop(X0)" not in asl


def _write_domain(tmp_path: Path, *, include_place: bool = True) -> Path:
	domain = tmp_path / "domain.pddl"
	place_action = (
		"""
		 (:action place
		  :parameters (?x - block ?y - block)
		  :precondition (and (holding ?x) (clear ?y))
		  :effect (and (on ?x ?y) (handempty) (not (holding ?x)))
		 )
		"""
		if include_place
		else ""
	)
	domain.write_text(
		f"""
		(define (domain generic-blocks)
		 (:requirements :strips :typing)
		 (:types block)
		 (:predicates
		  (clear ?x - block)
		  (on ?x - block ?y - block)
		  (handempty)
		  (holding ?x - block)
		 )
		 (:action noop
		  :parameters ()
		  :precondition (handempty)
		  :effect (handempty)
		 )
		 (:action drop
		  :parameters (?x - block)
		  :precondition (holding ?x)
		  :effect (and (handempty) (not (holding ?x)))
		 )
		 (:action pick
		  :parameters (?x - block)
		  :precondition (and (handempty) (clear ?x))
		  :effect (and (holding ?x) (not (handempty)))
		 )
		 (:action remove
		  :parameters (?x - block ?y - block)
		  :precondition (and (on ?x ?y) (clear ?x))
		  :effect (and (clear ?y) (not (on ?x ?y)))
		 )
		 {place_action}
		)
		""",
		encoding="utf-8",
	)
	return domain
