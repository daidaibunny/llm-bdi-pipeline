from __future__ import annotations

import pytest

from temporal_specification.prediction_validation import PredictionValidationError
from temporal_specification.prediction_validation import validate_prediction_payload


CATALOG = {
	"schema_version": 1,
	"domain": "tiny",
	"predicates": [
		{"name": "ready", "argument_types": ["item"]},
		{"name": "at", "argument_types": ["item", "place"]},
	],
	"numeric_functions": [
		{"name": "fuel", "argument_types": ["vehicle"]},
	],
	"constants": [{"name": "depot", "pddl_type": "place"}],
	"type_parents": {
		"special_item": "item",
		"item": "object",
		"vehicle": "object",
		"place": "object",
	},
}


def test_validate_prediction_payload_accepts_exact_lifted_contract() -> None:
	expected = {
		"sample_id": "tiny_1",
		"declared_parameters": [
			{"name": "X", "pddl_type": "special_item"},
		],
		"constraints": [],
	}
	payload = {
		"schema_version": 1,
		"sample_id": "tiny_1",
		"temporal_logic": "LTLf",
		"ltlf_formula": "F(a0 & X(F(a1)))",
		"atoms": [
			{
				"symbol": "a0",
				"kind": "predicate",
				"predicate": "ready",
				"args": ["X"],
			},
			{
				"symbol": "a1",
				"kind": "predicate",
				"predicate": "at",
				"args": ["X", "depot"],
			},
		],
		"declared_parameters": expected["declared_parameters"],
		"constraints": [],
		"status": "supported",
	}

	validated = validate_prediction_payload(
		payload,
		expected_sample=expected,
		catalog=CATALOG,
	)

	assert validated.sample_id == "tiny_1"
	assert validated.ltlf_formula == "F(a0 & X(F(a1)))"
	assert [atom.semantic_key for atom in validated.atoms] == [
		("predicate", "ready", ("X",), None),
		("predicate", "at", ("X", "depot"), None),
	]


def test_validate_prediction_payload_accepts_numeric_equality() -> None:
	expected = {
		"sample_id": "numeric_1",
		"declared_parameters": [{"name": "V", "pddl_type": "vehicle"}],
		"constraints": [],
	}
	payload = {
		"schema_version": 1,
		"sample_id": "numeric_1",
		"temporal_logic": "LTLf",
		"ltlf_formula": "F(a0)",
		"atoms": [
			{
				"symbol": "a0",
				"kind": "numeric_equality",
				"function": "fuel",
				"args": ["V"],
				"value": 0,
			},
		],
		"declared_parameters": expected["declared_parameters"],
		"constraints": [],
		"status": "supported",
	}

	validated = validate_prediction_payload(
		payload,
		expected_sample=expected,
		catalog=CATALOG,
	)

	assert validated.atoms[0].semantic_key == (
		"numeric_equality",
		"fuel",
		("V",),
		0,
	)


def test_validate_prediction_payload_accepts_atemporal_achievement_formula() -> None:
	expected = {
		"sample_id": "achievement_1",
		"declared_parameters": [{"name": "X", "pddl_type": "item"}],
		"constraints": [],
	}
	payload = {
		"schema_version": 1,
		"sample_id": "achievement_1",
		"temporal_logic": "LTLf",
		"ltlf_formula": "a0",
		"atoms": [
			{
				"symbol": "a0",
				"kind": "predicate",
				"predicate": "ready",
				"args": ["X"],
			},
		],
		"declared_parameters": expected["declared_parameters"],
		"constraints": [],
		"status": "supported",
	}

	validated = validate_prediction_payload(
		payload,
		expected_sample=expected,
		catalog=CATALOG,
	)

	assert validated.ltlf_formula == "a0"


@pytest.mark.parametrize(
	"formula",
	(
		"!(F(a0))",
		"!!a0",
	),
)
def test_validate_prediction_payload_rejects_non_literal_negation(formula: str) -> None:
	expected = {
		"sample_id": "tiny_1",
		"declared_parameters": [{"name": "X", "pddl_type": "item"}],
		"constraints": [],
	}
	payload = {
		"schema_version": 1,
		"sample_id": "tiny_1",
		"temporal_logic": "LTLf",
		"ltlf_formula": formula,
		"atoms": [
			{
				"symbol": "a0",
				"kind": "predicate",
				"predicate": "ready",
				"args": ["X"],
			},
		],
		"declared_parameters": expected["declared_parameters"],
		"constraints": [],
		"status": "supported",
	}

	with pytest.raises(PredictionValidationError) as raised:
		validate_prediction_payload(
			payload,
			expected_sample=expected,
			catalog=CATALOG,
		)

	assert raised.value.code.value == "E_UNSUPPORTED_OPERATOR"


@pytest.mark.parametrize(
	("mutator", "error_code"),
	[
		(lambda payload: payload.update({"explanation": "extra"}), "E_JSON_FORMAT"),
		(lambda payload: payload.update({"sample_id": "wrong"}), "E_JSON_FORMAT"),
		(lambda payload: payload["atoms"][0].update({"predicate": "unknown"}), "E_UNKNOWN_SYMBOL"),
		(lambda payload: payload["atoms"][0].update({"args": ["object7"]}), "E_UNKNOWN_SYMBOL"),
		(lambda payload: payload.update({"ltlf_formula": "G(a0)"}), "E_UNSUPPORTED_OPERATOR"),
		(lambda payload: payload.update({"ltlf_formula": "F(a1)"}), "E_FORMULA_ATOM_MISMATCH"),
	],
)
def test_validate_prediction_payload_fails_closed(mutator, error_code: str) -> None:
	expected = {
		"sample_id": "tiny_1",
		"declared_parameters": [{"name": "X", "pddl_type": "item"}],
		"constraints": [],
	}
	payload = {
		"schema_version": 1,
		"sample_id": "tiny_1",
		"temporal_logic": "LTLf",
		"ltlf_formula": "F(a0)",
		"atoms": [
			{
				"symbol": "a0",
				"kind": "predicate",
				"predicate": "ready",
				"args": ["X"],
			},
		],
		"declared_parameters": expected["declared_parameters"],
		"constraints": [],
		"status": "supported",
	}
	mutator(payload)

	with pytest.raises(PredictionValidationError) as raised:
		validate_prediction_payload(
			payload,
			expected_sample=expected,
			catalog=CATALOG,
		)

	assert raised.value.code.value == error_code
