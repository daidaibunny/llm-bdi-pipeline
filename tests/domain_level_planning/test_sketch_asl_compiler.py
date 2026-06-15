from __future__ import annotations

import pytest

from domain_level_planning import (
	SketchCompilationTarget,
	SketchFeatureBinding,
	compile_bound_sketch_to_asl_library,
	parse_dlplan_policy,
)
from plan_library.models import AgentSpeakBodyStep
from plan_library.rendering import render_plan_library_asl


def test_compile_bound_sketch_to_asl_uses_explicit_feature_bindings() -> None:
	policy = parse_dlplan_policy(
		"""
		(:policy
		(:booleans )
		(:numericals (f1 "n_count(c_primitive(done,0))"))
		(:rule (:conditions (:c_n_eq f1)) (:effects (:e_n_inc f1)))
		)
		""",
	)

	plan_library = compile_bound_sketch_to_asl_library(
		domain_name="generic",
		policy=policy,
		feature_bindings={
			"f1": SketchFeatureBinding(
				condition_contexts={
					"c_n_eq": ("goal_done(X)", "not done(X)"),
				},
				effect_body={
					"e_n_inc": (AgentSpeakBodyStep("subgoal", "done", ("X",)),),
				},
			),
		},
	)

	asl = render_plan_library_asl(plan_library)

	assert "+!g : goal_done(X) & not done(X) <-" in asl
	assert "\t!done(X);" in asl
	assert "\t!g." in asl
	assert "!achieve_" not in asl
	assert "!transition_" not in asl
	assert "dfa_state" not in asl


def test_compile_bound_sketch_to_asl_can_target_lifted_atomic_module() -> None:
	policy = parse_dlplan_policy(
		"""
		(:policy
		(:booleans )
		(:numericals (f1 "n_count(c_primitive(done,0))"))
		(:rule (:conditions (:c_n_gt f1)) (:effects (:e_n_dec f1)))
		)
		""",
	)

	plan_library = compile_bound_sketch_to_asl_library(
		domain_name="generic",
		policy=policy,
		target=SketchCompilationTarget(symbol="done", arguments=("X",), recurse=False),
		feature_bindings={
			"f1": SketchFeatureBinding(
				condition_contexts={
					"c_n_gt": ("needed(X)", "not done(X)"),
				},
				effect_body={
					"e_n_dec": (AgentSpeakBodyStep("primitive_action", "mark", ("X",)),),
				},
			),
		},
	)

	asl = render_plan_library_asl(plan_library)

	assert "+!done(X) : needed(X) & not done(X) <-" in asl
	assert "\tmark(X)." in asl
	assert "\t!done(X)" not in asl
	assert plan_library.metadata["target"] == {
		"symbol": "done",
		"arguments": ["X"],
		"recurse": False,
	}


def test_compile_bound_sketch_requires_explicit_feature_bindings() -> None:
	policy = parse_dlplan_policy(
		"""
		(:policy
		(:booleans )
		(:numericals (f1 "n_count(c_primitive(done,0))"))
		(:rule (:conditions (:c_n_gt f1)) (:effects (:e_n_dec f1)))
		)
		""",
	)

	with pytest.raises(ValueError, match="No ASL binding"):
		compile_bound_sketch_to_asl_library(
			domain_name="generic",
			policy=policy,
			feature_bindings={},
		)


def test_compile_bound_sketch_rejects_ambiguous_target_arguments() -> None:
	policy = parse_dlplan_policy("(:policy (:booleans ) (:numericals ))")

	with pytest.raises(ValueError, match="either target or top_level_goal"):
		compile_bound_sketch_to_asl_library(
			domain_name="generic",
			policy=policy,
			target=SketchCompilationTarget(symbol="done", arguments=("X",)),
			top_level_goal="g",
			feature_bindings={},
		)
