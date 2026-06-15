from __future__ import annotations

from pathlib import Path

from domain_level_planning.sketch_pipeline import compile_learner_sketch_policy_to_asl
from plan_library.rendering import render_plan_library_asl


def test_compile_learner_sketch_policy_to_executable_lifted_asl(tmp_path: Path) -> None:
	domain_file = tmp_path / "domain.pddl"
	policy_file = tmp_path / "sketch.txt"
	domain_file.write_text(
		"""
		(define (domain generic-blocks)
		 (:requirements :strips)
		 (:predicates
		  (clear ?x)
		  (holding ?x)
		  (on ?x ?y)
		 )
		 (:action stack
		  :parameters (?x ?y)
		  :precondition (and (holding ?x) (clear ?y))
		  :effect (and (on ?x ?y) (not (holding ?x)))
		 )
		)
		""",
		encoding="utf-8",
	)
	policy_file.write_text(
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
		encoding="utf-8",
	)

	result = compile_learner_sketch_policy_to_asl(
		domain_file=domain_file,
		policy_file=policy_file,
		domain_name="generic-blocks",
	)
	asl = render_plan_library_asl(result.plan_library)

	assert result.unsupported_features == {}
	assert "+!g : goal_on(X0, X1) & not on(X0, X1) & holding(X0) & clear(X1) <-" in asl
	assert "\tstack(X0, X1);" in asl
	assert "!achieve_" not in asl
	assert "!transition_" not in asl
