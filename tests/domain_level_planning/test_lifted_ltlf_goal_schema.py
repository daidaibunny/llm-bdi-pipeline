from __future__ import annotations

import json

import pytest

from domain_level_planning.lifted_ltlf_goal_schema import load_lifted_ltlf_goal_dataset
from domain_level_planning.lifted_ltlf_goal_schema import parse_lifted_ltlf_goal_dataset


def test_parse_lifted_ltlf_goal_dataset_accepts_bindings(tmp_path) -> None:
	payload = {
		"schema_version": 1,
		"goal_specification_kind": "temporal_extended_goal",
		"temporal_logic": "LTLf",
		"domain": "blocks",
		"cases": {
			"query_1": {
				"goal_name": "g_query_1",
				"problem_file": "p01.pddl",
				"source_text": "Build X on Y, then clear X.",
				"ltlf_formula": "F(on(X,Y) & X(F(clear(X))))",
				"atoms": [
					{"symbol": "on_X_Y", "predicate": "on", "args": ["X", "Y"]},
					{"symbol": "clear_X", "predicate": "clear", "args": ["X"]},
				],
				"bindings": {"X": "b4", "Y": "b2"},
				"atom_vocabulary": "pddl_fluents",
				"status": "supported",
			},
		},
	}
	path = tmp_path / "ltlf.json"
	path.write_text(json.dumps(payload), encoding="utf-8")

	dataset = load_lifted_ltlf_goal_dataset(path)

	assert dataset.domain == "blocks"
	assert dataset.cases[0].query_id == "query_1"
	assert dataset.cases[0].goal_name == "g_query_1"
	assert dataset.cases[0].bindings == {"X": "b4", "Y": "b2"}
	assert [atom.predicate for atom in dataset.cases[0].atoms] == ["on", "clear"]


def test_parse_lifted_ltlf_goal_dataset_accepts_atemporal_achievement_goal() -> None:
	dataset = parse_lifted_ltlf_goal_dataset(
		{
			"schema_version": 1,
			"goal_specification_kind": "achievement_goal",
			"temporal_logic": "LTLf",
			"domain": "blocks",
			"cases": {
				"query_1": {
					"source_text": "Put X on Y.",
					"ltlf_formula": "on(X,Y)",
					"atoms": [
						{"symbol": "on_x_y", "predicate": "on", "args": ["X", "Y"]},
					],
				},
			},
		},
	)

	assert dataset.goal_specification_kind == "achievement_goal"
	assert dataset.cases[0].ltlf_formula == "on(X,Y)"


@pytest.mark.parametrize(
	("goal_specification_kind", "formula", "message"),
	(
		(
			"achievement_goal",
			"F(on(X,Y))",
			"achievement_goal cases must not contain temporal operators",
		),
		(
			"temporal_extended_goal",
			"on(X,Y)",
			"temporal_extended_goal cases must contain at least one temporal operator",
		),
	),
)
def test_parse_lifted_ltlf_goal_dataset_rejects_kind_formula_mismatch(
	goal_specification_kind: str,
	formula: str,
	message: str,
) -> None:
	with pytest.raises(ValueError, match=message):
		parse_lifted_ltlf_goal_dataset(
			{
				"schema_version": 1,
				"goal_specification_kind": goal_specification_kind,
				"temporal_logic": "LTLf",
				"domain": "blocks",
				"cases": {
					"query_1": {
						"ltlf_formula": formula,
						"atoms": [],
					},
				},
			},
		)


def test_parse_lifted_ltlf_goal_dataset_reports_schema_errors() -> None:
	with pytest.raises(ValueError, match="temporal_logic must be LTLf"):
		parse_lifted_ltlf_goal_dataset(
			{
				"schema_version": 1,
				"goal_specification_kind": "temporal_extended_goal",
				"temporal_logic": "LTL",
				"domain": "blocks",
				"cases": {},
			},
		)

	with pytest.raises(ValueError, match="query_1 is missing ltlf_formula"):
		parse_lifted_ltlf_goal_dataset(
			{
				"schema_version": 1,
				"goal_specification_kind": "temporal_extended_goal",
				"temporal_logic": "LTLf",
				"domain": "blocks",
				"cases": {"query_1": {"source_text": "x"}},
			},
		)
