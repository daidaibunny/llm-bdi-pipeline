from __future__ import annotations

from pathlib import Path

import pytest

from domain_level_planning.paper_backend_audit import audit_learned_policy_for_asl_binding
from utils.pddl_parser import PDDLParser


def test_audit_reports_learned_policy_binding_readiness(tmp_path: Path) -> None:
	domain_file = _write_domain(tmp_path)
	policy_file = tmp_path / "policy.txt"
	policy_file.write_text(
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
		encoding="utf-8",
	)

	report, policy, binding_report = audit_learned_policy_for_asl_binding(
		source_name="learner-sketches:test",
		policy_file=policy_file,
		domain=PDDLParser.parse_domain(domain_file),
	)

	assert report.source_name == "learner-sketches:test"
	assert report.feature_count == 2
	assert report.rule_count == 1
	assert report.bound_feature_count == 2
	assert report.unsupported_features == {}
	assert report.action_effect_candidate_count == 1
	assert report.executable_effect_count >= 2
	assert report.ready_for_executable_asl is True
	report_dict = report.to_dict()
	assert report_dict["feature_binding_diagnostics"] == (
		{
			"feature_id": "f_on",
			"expression": "n_count(c_equal(r_primitive(on,0,1),r_primitive(on_g,0,1)))",
			"status": "bound",
			"binding_kind": "goal_aligned_role_count",
			"condition_operators": ("c_n_eq", "c_n_gt"),
			"effect_operators": ("e_n_bot", "e_n_inc"),
			"action_candidate_count": 0,
			"action_candidates": (),
			"promoted_effect_operators": (),
			"rejection_reason": None,
		},
		{
			"feature_id": "f_holding",
			"expression": "n_count(c_primitive(holding,0))",
			"status": "bound",
			"binding_kind": "primitive_concept_count",
			"condition_operators": ("c_n_eq", "c_n_gt"),
			"effect_operators": ("e_n_bot", "e_n_inc", "e_n_dec"),
			"action_candidate_count": 1,
			"action_candidates": (
				{
					"feature_id": "f_holding",
					"operator": "e_n_dec",
					"effect_predicate": "holding",
					"action_name": "place",
					"context": ("holding(X)", "clear(Y)"),
					"body": (
						{
							"kind": "primitive_action",
							"symbol": "place",
							"arguments": ["X", "Y"],
						},
					),
					"add_effects": (
						{
							"predicate": "on",
							"arguments": ("X", "Y"),
						},
						{
							"predicate": "handempty",
							"arguments": (),
						},
					),
				},
			),
			"promoted_effect_operators": ("e_n_dec",),
			"rejection_reason": None,
		},
	)
	assert tuple(policy.features) == ("f_on", "f_holding")
	assert tuple(binding_report.bindings) == ("f_on", "f_holding")


def test_audit_rejects_unbound_paper_policy_as_not_executable(tmp_path: Path) -> None:
	domain_file = _write_domain(tmp_path)
	policy_file = tmp_path / "unsupported-policy.txt"
	policy_file.write_text(
		"""
		(:policy
		(:booleans )
		(:numericals
		 (f_bad "n_concept_distance(c_one_of(a),r_primitive(on,0,1),c_primitive(clear,0))")
		)
		(:rule (:conditions (:c_n_gt f_bad)) (:effects (:e_n_dec f_bad)))
		)
		""",
		encoding="utf-8",
	)

	report, _, _ = audit_learned_policy_for_asl_binding(
		source_name="learner-sketches:unsupported",
		policy_file=policy_file,
		domain=PDDLParser.parse_domain(domain_file),
	)

	assert report.feature_count == 1
	assert report.rule_count == 1
	assert report.bound_feature_count == 0
	assert report.unsupported_features == {
		"f_bad": "n_concept_distance(c_one_of(a),r_primitive(on,0,1),c_primitive(clear,0))",
	}
	assert report.ready_for_executable_asl is False
	assert report.to_dict()["feature_binding_diagnostics"] == (
		{
			"feature_id": "f_bad",
			"expression": (
				"n_concept_distance(c_one_of(a),r_primitive(on,0,1),"
				"c_primitive(clear,0))"
			),
			"status": "unsupported",
			"binding_kind": "unsupported",
			"condition_operators": (),
			"effect_operators": (),
			"action_candidate_count": 0,
			"action_candidates": (),
			"promoted_effect_operators": (),
			"rejection_reason": (
				"object_specific_dlplan_feature_requires_principled_lifting"
			),
		},
	)


def test_audit_rejects_policy_with_bound_features_but_uncompiled_rule(
	tmp_path: Path,
) -> None:
	domain_file = _write_domain(tmp_path)
	policy_file = tmp_path / "uncompiled-rule-policy.txt"
	policy_file.write_text(
		"""
		(:policy
		(:booleans )
		(:numericals
		 (f_on "n_count(c_equal(r_primitive(on,0,1),r_primitive(on_g,0,1)))")
		)
		(:rule (:conditions (:c_n_lt f_on)) (:effects (:e_n_inc f_on)))
		)
		""",
		encoding="utf-8",
	)

	report, _, _ = audit_learned_policy_for_asl_binding(
		source_name="learner-sketches:uncompiled-rule",
		policy_file=policy_file,
		domain=PDDLParser.parse_domain(domain_file),
	)

	assert report.unsupported_features == {}
	assert report.bound_feature_count == 1
	assert report.executable_effect_count > 0
	assert report.ready_for_executable_asl is False


def test_audit_applies_explicit_predicate_vocabulary_adapter(
	tmp_path: Path,
) -> None:
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text(
		"""
		(define (domain table-domain)
		 (:requirements :strips)
		 (:predicates
		  (ontable ?x)
		  (holding ?x)
		 )
		 (:action putdown
		  :parameters (?x)
		  :precondition (holding ?x)
		  :effect (and (ontable ?x) (not (holding ?x)))
		 )
		)
		""",
		encoding="utf-8",
	)
	policy_file = tmp_path / "external-policy.txt"
	policy_file.write_text(
		"""
		(:policy
		(:booleans )
		(:numericals (f_table "n_count(c_primitive(on-table,0))"))
		(:rule (:conditions ) (:effects (:e_n_inc f_table)))
		)
		""",
		encoding="utf-8",
	)

	report, policy, binding_report = audit_learned_policy_for_asl_binding(
		source_name="learner-sketches:vocab",
		policy_file=policy_file,
		domain=PDDLParser.parse_domain(domain_file),
		vocabulary_map={"on-table": "ontable"},
	)

	assert policy.features["f_table"] == "n_count(c_primitive(ontable,0))"
	assert report.vocabulary_adapter == {"on-table": "ontable"}
	assert report.unsupported_features == {}
	assert binding_report.feature_diagnostics["f_table"].status == "bound"


def test_audit_rejects_vocabulary_adapter_targets_outside_domain(
	tmp_path: Path,
) -> None:
	domain_file = _write_domain(tmp_path)
	policy_file = tmp_path / "external-policy.txt"
	policy_file.write_text(
		"""
		(:policy
		(:booleans )
		(:numericals (f_table "n_count(c_primitive(on-table,0))"))
		(:rule (:conditions ) (:effects (:e_n_inc f_table)))
		)
		""",
		encoding="utf-8",
	)

	with pytest.raises(ValueError, match="does not declare target predicate"):
		audit_learned_policy_for_asl_binding(
			source_name="learner-sketches:vocab",
			policy_file=policy_file,
			domain=PDDLParser.parse_domain(domain_file),
			vocabulary_map={"on-table": "ontable"},
		)


def _write_domain(tmp_path: Path) -> Path:
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text(
		"""
		(define (domain audit-blocks)
		 (:requirements :strips :typing)
		 (:types block)
		 (:predicates
		  (clear ?x - block)
		  (on ?x - block ?y - block)
		  (holding ?x - block)
		  (handempty)
		 )
		 (:action place
		  :parameters (?x - block ?y - block)
		  :precondition (and (holding ?x) (clear ?y))
		  :effect (and (on ?x ?y) (handempty) (not (holding ?x)))
		 )
		)
		""",
		encoding="utf-8",
	)
	return domain_file
