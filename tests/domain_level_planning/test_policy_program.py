from __future__ import annotations

from domain_level_planning.gp_backends import parse_dlplan_policy
from domain_level_planning.policy_program import (
	LearnedPolicyRule,
	LiftedPolicyProgram,
	policy_program_from_sketch_policy,
)


def test_dlplan_sketch_policy_becomes_policy_first_program() -> None:
	policy = parse_dlplan_policy(
		"""
		(:policy
		(:booleans
		 (b_empty "b_nullary(handempty)")
		)
		(:numericals
		 (n_on "n_count(c_equal(r_primitive(on,0,1),r_primitive(on_g,0,1)))")
		)
		(:rule (:conditions (:c_b_pos b_empty) (:c_n_eq n_on))
		 (:effects (:e_n_inc n_on)))
		)
		""",
	)

	program = policy_program_from_sketch_policy(
		policy=policy,
		domain_name="blocks",
		source_name="kr2025-smoke",
		backend_name="learner-policies-from-examples",
		policy_file="tmp/sketch_minimized_0.txt",
	)

	assert program.domain_name == "blocks"
	assert program.backend_name == "learner-policies-from-examples"
	assert program.representation == "dlplan_qualitative_policy"
	assert program.is_learned_policy is True
	features_by_id = {feature.identifier: feature for feature in program.features}
	assert tuple(features_by_id) == ("b_empty", "n_on")
	assert features_by_id["n_on"].expression == (
		"n_count(c_equal(r_primitive(on,0,1),r_primitive(on_g,0,1)))"
	)
	assert program.rules == (
		LearnedPolicyRule(
			name="kr2025_smoke_rule_1",
			conditions=(("b_empty", "c_b_pos"), ("n_on", "c_n_eq")),
			effects=(("n_on", "e_n_inc"),),
			source_rule=(
				"(:rule (:conditions (:c_b_pos b_empty) (:c_n_eq n_on)) "
				"(:effects (:e_n_inc n_on)))"
			),
		),
	)
	assert program.progress_certificate["termination_basis"] == (
		"external_backend_policy_verification"
	)
	assert program.provenance["policy_file"] == "tmp/sketch_minimized_0.txt"


def test_policy_program_dict_is_stable_for_artifact_reports() -> None:
	program = LiftedPolicyProgram(
		domain_name="demo",
		backend_name="manual",
		source_name="unit",
		representation="dlplan_qualitative_policy",
		features=(),
		rules=(),
		modules=(),
		progress_certificate={"termination_basis": "unit"},
		provenance={"paper_basis": "test"},
	)

	assert program.to_dict() == {
		"domain_name": "demo",
		"backend_name": "manual",
		"source_name": "unit",
		"representation": "dlplan_qualitative_policy",
		"is_learned_policy": True,
		"features": [],
		"rules": [],
		"modules": [],
		"progress_certificate": {"termination_basis": "unit"},
		"provenance": {"paper_basis": "test"},
	}
