from __future__ import annotations

import json

import pytest

from temporal_specification.prompts import (
	BASELINE_PROMPT_CONFIG,
	FULL_PROMPT_CONFIG,
	PROMPT_COMPONENTS,
	PromptConfig,
	ablation_config,
	build_lifted_ltlf_system_prompt,
	build_lifted_ltlf_user_prompt,
	build_retry_user_message,
)


@pytest.fixture
def catalog() -> dict[str, object]:
	return {
		"schema_version": 1,
		"domain": "numeric-example",
		"type_parents": {"vehicle": "object", "truck": "vehicle"},
		"constants": [{"name": "depot-a", "pddl_type": "location"}],
		"predicates": [
			{"name": "at", "argument_types": ["vehicle", "location"]},
			{"name": "loaded", "argument_types": ["vehicle"]},
		],
		"numeric_functions": [
			{"name": "fuel-level", "argument_types": ["vehicle"]},
		],
	}


@pytest.fixture
def sample() -> dict[str, object]:
	return {
		"sample_id": "numeric_example_p01",
		"domain": "numeric-example",
		"problem_file": "src/domains/numeric-example/test/p01.pddl",
		"catalog_file": "domains/numeric-example/catalog.json",
		"status": "constructed_temporal_query",
		"profile": "ordered_two_milestone",
		"construction_tier": "primary",
		"parameter_semantics": "externally_bound",
		"source_text": (
			"Given parameter X of PDDL type truck and parameter Y of PDDL type "
			"location, ensure that predicate loaded holds for argument X, and at a "
			"strictly later state numeric function fuel-level for argument X equals 1."
		),
		"declared_parameters": [
			{"name": "X", "pddl_type": "truck"},
			{"name": "Y", "pddl_type": "location"},
		],
		"constraints": [
			{"operator": "not_equal", "left": "X", "right": "Y"},
		],
		"semantic_signature": "must-not-reach-the-model",
		"assignment": {"X": "truck7", "Y": "loc9"},
		"witness_actions": ["(drive truck7 loc8 loc9)"],
	}


def test_full_system_prompt_defines_propositionalized_lifted_output(
	catalog: dict[str, object],
) -> None:
	prompt = build_lifted_ltlf_system_prompt(catalog)

	assert "numeric-example" in prompt
	assert "at(vehicle, location)" in prompt
	assert "fuel-level(vehicle)" in prompt
	assert "depot-a : location" in prompt
	assert "F(a0 & X(F(a1)))" in prompt
	assert '"symbol": "a0"' in prompt
	assert '"kind": "predicate"' in prompt
	assert '"args": ["<declared parameter or domain constant>"]' in prompt
	assert '"kind": "numeric_equality"' in prompt
	assert "Do not ground" in prompt
	assert "binding" not in prompt.lower()
	assert "parameterized formula schema" in prompt
	assert "later invocation supplies" in prompt
	assert "not an LTLf quantifier" in prompt
	for foreign_domain_symbol in ("holding", "on(X,Y)", "contains(X,Y)"):
		assert foreign_domain_symbol not in prompt


def test_system_prompt_is_equivariant_under_catalogue_symbol_renaming() -> None:
	original = {
		"domain": "domain_alpha",
		"type_parents": {"type_child_alpha": "type_root_alpha"},
		"constants": [{"name": "constant_alpha", "pddl_type": "type_child_alpha"}],
		"predicates": [
			{"name": "predicate_alpha", "argument_types": ["type_child_alpha"]},
		],
		"numeric_functions": [
			{"name": "function_alpha", "argument_types": ["type_child_alpha"]},
		],
	}
	renamed = {
		"domain": "domain_beta",
		"type_parents": {"type_child_beta": "type_root_beta"},
		"constants": [{"name": "constant_beta", "pddl_type": "type_child_beta"}],
		"predicates": [
			{"name": "predicate_beta", "argument_types": ["type_child_beta"]},
		],
		"numeric_functions": [
			{"name": "function_beta", "argument_types": ["type_child_beta"]},
		],
	}

	renamed_prompt = build_lifted_ltlf_system_prompt(renamed)
	for beta, alpha in (
		("predicate_beta", "predicate_alpha"),
		("function_beta", "function_alpha"),
		("constant_beta", "constant_alpha"),
		("type_child_beta", "type_child_alpha"),
		("type_root_beta", "type_root_alpha"),
		("domain_beta", "domain_alpha"),
	):
		renamed_prompt = renamed_prompt.replace(beta, alpha)

	assert renamed_prompt == build_lifted_ltlf_system_prompt(original)


def test_system_prompt_restricts_benchmark_v1_operators(
	catalog: dict[str, object],
) -> None:
	prompt = build_lifted_ltlf_system_prompt(catalog)

	assert "F, X, U, &, and !" in prompt
	for forbidden in ("disjunction |", "global G", "release R", "weak-next WX"):
		assert forbidden in prompt
	for profile_formula in (
		"F(a0 & a1)",
		"F(a0 & !a1)",
		"F(a0 & X(F(a1)))",
		"F(a0 & X(F(a1 & X(F(a2)))))",
		"a0 U a1",
	):
		assert profile_formula in prompt


def test_user_prompt_exposes_only_public_translation_inputs(
	sample: dict[str, object],
) -> None:
	prompt = build_lifted_ltlf_user_prompt(sample)

	assert "numeric_example_p01" in prompt
	assert str(sample["source_text"]) in prompt
	assert '"name": "X"' in prompt
	assert '"pddl_type": "truck"' in prompt
	assert '"operator": "not_equal"' in prompt
	assert "externally_bound" in prompt
	for hidden_value in (
		"ordered_two_milestone",
		"primary",
		"must-not-reach-the-model",
		"truck7",
		"loc9",
		"drive",
		"problem_file",
	):
		assert hidden_value not in prompt


def test_user_prompt_rejects_non_constructed_rows(sample: dict[str, object]) -> None:
	invalid = {**sample, "status": "source_witness_not_found"}

	with pytest.raises(ValueError, match="constructed_temporal_query"):
		build_lifted_ltlf_user_prompt(invalid)


def test_prompt_components_remain_ablatable(catalog: dict[str, object]) -> None:
	full = build_lifted_ltlf_system_prompt(catalog, FULL_PROMPT_CONFIG)
	baseline = build_lifted_ltlf_system_prompt(catalog, BASELINE_PROMPT_CONFIG)

	assert FULL_PROMPT_CONFIG.name == "full"
	assert BASELINE_PROMPT_CONFIG.name == "baseline"
	assert set(PROMPT_COMPONENTS) == {
		"normal_form",
		"few_shot",
		"variable_rules",
		"operator_whitelist",
		"error_guidance",
	}
	assert len(full) > len(baseline)
	assert "BENCHMARK-V1 TEMPORAL STRUCTURES" in full
	assert "BENCHMARK-V1 TEMPORAL STRUCTURES" not in build_lifted_ltlf_system_prompt(
		catalog,
		ablation_config("normal_form"),
	)
	assert PromptConfig.from_name("no_few_shot") == ablation_config("few_shot")


def test_retry_message_preserves_output_contract_without_backend_advice() -> None:
	feedback = {
		"previous_ltlf": "F(a0 | a1)",
		"error_type": "E_UNSUPPORTED_OPERATOR",
		"error_detail": "disjunction is outside benchmark version 1",
		"hint": "Use only F, X, U, &, and !.",
		"attempt": 2,
	}
	message = build_retry_user_message(feedback)
	embedded = json.loads(message[message.index("{") : message.rindex("}") + 1])

	assert embedded == feedback
	assert "same eight-key JSON schema" in message
	assert "binding" not in message.lower()
	assert "simplify" not in message.lower()
	assert "MONA" not in message
