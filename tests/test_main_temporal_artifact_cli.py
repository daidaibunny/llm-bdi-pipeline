from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_main_compiles_moose_atomic_library(tmp_path: Path) -> None:
	policy_file = tmp_path / "ferry-seed0.model.readable"
	output_root = tmp_path / "moose-library"
	policy_file.write_text(
		"""
		precedence : (1, 1, 0, 0)
		      vars : car0 location0
		    s_cond : (at-ferry location0) (on car0)
		    g_cond : (at car0 location0)
		   actions : (debark car0 location0)
		""",
		encoding="utf-8",
	)

	completed = subprocess.run(
		[
			sys.executable,
			str(PROJECT_ROOT / "src" / "main.py"),
			"compile-moose-atomic-library",
			"--policy-file",
			str(policy_file),
			"--domain-name",
			"ferry",
			"--output-root",
			str(output_root),
		],
		cwd=PROJECT_ROOT,
		check=True,
		capture_output=True,
		text=True,
	)
	result = json.loads(completed.stdout)
	asl = Path(result["artifact_paths"]["plan_library_asl"]).read_text(encoding="utf-8")

	assert result["success"] is True
	assert result["plan_count"] == 1
	assert "+!at(Car0, Location0)" in asl
	assert "achieve_" not in asl
	assert "transition_" not in asl
	assert "dfa_state" not in asl


def test_main_appends_lifted_temporal_goal_to_existing_library(
	tmp_path: Path,
) -> None:
	domain_file, _ = _write_tiny_domain_and_problem(tmp_path)
	library_file = _write_atomic_library_json(tmp_path)
	goal_json = _write_lifted_ltlf_goal_json(tmp_path)
	output_root = tmp_path / "temporal-append"

	completed = subprocess.run(
		[
			sys.executable,
			str(PROJECT_ROOT / "src" / "main.py"),
			"append-lifted-temporal-goal",
			"--domain-file",
			str(domain_file),
			"--plan-library-file",
			str(library_file),
			"--ltlf-goal-json",
			str(goal_json),
			"--query-id",
			"query_1",
			"--output-root",
			str(output_root),
		],
		cwd=PROJECT_ROOT,
		check=True,
		capture_output=True,
		text=True,
	)
	result = json.loads(completed.stdout)
	asl = Path(result["artifact_paths"]["plan_library_asl"]).read_text(encoding="utf-8")
	metadata = json.loads(
		Path(result["artifact_paths"]["artifact_metadata"]).read_text(encoding="utf-8"),
	)

	assert result["success"] is True
	assert result["appended_query_count"] == 1
	assert metadata["query_ids"] == ["query_1"]
	assert "teg_state(g_query_1, state_1)." in asl
	assert "+!g_query_1 : teg_state(g_query_1, state_1) & not done <-" in asl
	assert "\t!done;" in asl
	assert "\t-teg_state(g_query_1, state_1);" in asl
	assert "\t+teg_state(g_query_1, state_2);" in asl
	assert "\t!g_query_1." in asl
	assert "achieve_" not in asl
	assert "transition_" not in asl
	assert "dfa_state" not in asl


def test_main_can_append_multiple_queries_to_same_domain_library(
	tmp_path: Path,
) -> None:
	domain_file, _ = _write_tiny_domain_and_problem(tmp_path)
	library_file = _write_atomic_library_json(tmp_path)
	goal_json = tmp_path / "lifted_ltlf_goals.json"
	goal_json.write_text(
		json.dumps(
			{
				"schema_version": 1,
				"goal_specification_kind": "temporal_extended_goal",
				"temporal_logic": "LTLf",
				"domain": "tiny",
				"cases": {
					"query_1": {
						"goal_name": "g_query_1",
						"problem_file": "problem.pddl",
						"source_text": "Eventually finish.",
						"ltlf_formula": "F(done)",
						"atoms": ["done"],
						"bindings": {},
						"atom_vocabulary": "pddl_fluents",
						"status": "supported",
					},
					"query_2": {
						"goal_name": "g_query_2",
						"problem_file": "problem.pddl",
						"source_text": "Eventually be ready.",
						"ltlf_formula": "F(ready)",
						"atoms": ["ready"],
						"bindings": {},
						"atom_vocabulary": "pddl_fluents",
						"status": "supported",
					},
				},
			},
		),
		encoding="utf-8",
	)
	output_root = tmp_path / "domain-library"

	first = subprocess.run(
		[
			sys.executable,
			str(PROJECT_ROOT / "src" / "main.py"),
			"append-lifted-temporal-goal",
			"--domain-file",
			str(domain_file),
			"--plan-library-file",
			str(library_file),
			"--ltlf-goal-json",
			str(goal_json),
			"--query-id",
			"query_1",
			"--output-root",
			str(output_root),
		],
		cwd=PROJECT_ROOT,
		check=True,
		capture_output=True,
		text=True,
	)
	first_result = json.loads(first.stdout)
	second = subprocess.run(
		[
			sys.executable,
			str(PROJECT_ROOT / "src" / "main.py"),
			"append-lifted-temporal-goal",
			"--domain-file",
			str(domain_file),
			"--plan-library-file",
			first_result["artifact_paths"]["plan_library"],
			"--ltlf-goal-json",
			str(goal_json),
			"--query-id",
			"query_2",
			"--output-root",
			str(output_root),
		],
		cwd=PROJECT_ROOT,
		check=True,
		capture_output=True,
		text=True,
	)
	second_result = json.loads(second.stdout)
	library_json = json.loads(
		Path(second_result["artifact_paths"]["plan_library"]).read_text(encoding="utf-8"),
	)
	asl = Path(second_result["artifact_paths"]["plan_library_asl"]).read_text(encoding="utf-8")

	assert "teg_state(g_query_1, state_1)." in asl
	assert "teg_state(g_query_2, state_1)." in asl
	assert "+!g_query_1 : teg_state(g_query_1, state_1) & not done <-" in asl
	assert "+!g_query_2 : teg_state(g_query_2, state_1) & not ready <-" in asl
	assert [
		record["goal_name"]
		for record in library_json["metadata"]["temporal_goal_append_history"]
	] == ["g_query_1", "g_query_2"]
	assert second_result["plan_count"] == 5


def _write_tiny_domain_and_problem(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	domain_file.write_text(
		"""
		(define (domain tiny)
		 (:requirements :strips)
		 (:predicates (ready) (done))
		 (:action finish
		  :parameters ()
		  :precondition (ready)
		  :effect (and (not (ready)) (done))
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem tiny-p1)
		 (:domain tiny)
		 (:objects)
		 (:init (ready))
		 (:goal (and (done)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_atomic_library_json(tmp_path: Path) -> Path:
	library_file = tmp_path / "plan_library.json"
	library_file.write_text(
		json.dumps(
			{
				"domain_name": "tiny",
				"initial_beliefs": [],
				"metadata": {"atomic_template_backend": "test"},
				"plans": [
					{
						"plan_name": "done_via_finish",
						"trigger": {
							"event_type": "achievement_goal",
							"symbol": "done",
							"arguments": [],
						},
						"context": ["ready"],
						"body": [
							{"kind": "action", "symbol": "finish", "arguments": []},
						],
						"source_instruction_ids": [],
						"binding_certificate": [],
					},
				],
			},
		),
		encoding="utf-8",
	)
	return library_file


def _write_lifted_ltlf_goal_json(tmp_path: Path) -> Path:
	goal_json = tmp_path / "lifted_ltlf_goals.json"
	goal_json.write_text(
		json.dumps(
			{
				"schema_version": 1,
				"goal_specification_kind": "temporal_extended_goal",
				"temporal_logic": "LTLf",
				"domain": "tiny",
				"cases": {
					"query_1": {
						"goal_name": "g_query_1",
						"problem_file": "problem.pddl",
						"source_text": "Eventually finish.",
						"ltlf_formula": "F(done)",
						"atoms": ["done"],
						"bindings": {},
						"atom_vocabulary": "pddl_fluents",
						"status": "supported",
					},
				},
			},
		),
		encoding="utf-8",
	)
	return goal_json
