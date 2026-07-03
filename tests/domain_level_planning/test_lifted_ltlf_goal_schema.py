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
