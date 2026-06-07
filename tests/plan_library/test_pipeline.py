from __future__ import annotations

import json
import os
from pathlib import Path

from plan_library import PlanLibraryGenerationPipeline


class FakeDFABuilder:
	def build(self, record):
		return {
			"initial_state": f"{record.instruction_id}_q0",
			"accepting_states": [f"{record.instruction_id}_q1"],
			"guarded_transitions": [
				{
					"source_state": f"{record.instruction_id}_q0",
					"target_state": f"{record.instruction_id}_q1",
					"raw_label": "do_put_on_b1_b2",
				},
			],
		}


def test_plan_library_generation_pipeline_persists_dfa_artifacts(tmp_path: Path) -> None:
	domain_file = _write_blocks_domain(tmp_path)
	_write_blocks_problem(tmp_path, "p01.pddl")
	query_dataset = _write_query_dataset(tmp_path)
	fast_downward = _write_fake_fast_downward(tmp_path)
	pipeline = PlanLibraryGenerationPipeline(
		domain_file=str(domain_file),
		query_dataset=str(query_dataset),
		query_domain="blocksworld",
		query_ids=("query_1",),
		dfa_builder=FakeDFABuilder(),
		fast_downward_executable=str(fast_downward),
	)

	result = pipeline.build_library_bundle(output_root=str(tmp_path / "artifact_bundle"))

	assert result["success"] is True
	artifact_paths = result["artifact_paths"]
	assert Path(artifact_paths["query_sequence"]).exists()
	assert Path(artifact_paths["temporal_specifications"]).exists()
	assert Path(artifact_paths["plan_library"]).exists()
	assert Path(artifact_paths["generation_summary"]).exists()
	assert Path(artifact_paths["library_validation"]).exists()
	assert Path(artifact_paths["dfa_metadata"]).exists()
	assert Path(artifact_paths["plan_library_asl"]).exists()

	query_sequence = json.loads(Path(artifact_paths["query_sequence"]).read_text())
	temporal_specifications = json.loads(Path(artifact_paths["temporal_specifications"]).read_text())
	plan_library = json.loads(Path(artifact_paths["plan_library"]).read_text())
	generation_summary = json.loads(Path(artifact_paths["generation_summary"]).read_text())
	library_validation = json.loads(Path(artifact_paths["library_validation"]).read_text())
	asl = Path(artifact_paths["plan_library_asl"]).read_text()

	assert query_sequence[0]["instruction_id"] == "query_1"
	assert temporal_specifications[0]["problem_file"] == "p01.pddl"
	assert plan_library["plans"][0]["source_instruction_ids"] == ["query_1"]
	assert generation_summary["dfa_count"] == 1
	assert generation_summary["plans_generated"] == 2
	assert library_validation["passed"] is True
	assert "dfa_state" not in asl
	assert "+!g : on(b1, b2) <-" in asl
	assert "+!g : not on(b1, b2) <-" in asl
	assert "!achieve_" not in asl
	assert "\tstack(b1, b2);" in asl


def test_plan_library_generation_pipeline_filters_selected_query_ids(tmp_path: Path) -> None:
	domain_file = _write_blocks_domain(tmp_path)
	_write_blocks_problem(tmp_path, "p01.pddl")
	_write_blocks_problem(tmp_path, "p02.pddl")
	query_dataset = _write_query_dataset(tmp_path)
	fast_downward = _write_fake_fast_downward(tmp_path)
	pipeline = PlanLibraryGenerationPipeline(
		domain_file=str(domain_file),
		query_dataset=str(query_dataset),
		query_domain="blocksworld",
		query_ids=("query_2", "query_1", "query_2"),
		dfa_builder=FakeDFABuilder(),
		fast_downward_executable=str(fast_downward),
	)

	result = pipeline.build_library_bundle(output_root=str(tmp_path / "artifact_bundle"))

	assert result["success"] is True
	query_sequence = json.loads(Path(result["artifact_paths"]["query_sequence"]).read_text())
	assert [record["instruction_id"] for record in query_sequence] == ["query_2", "query_1"]


def test_plan_library_generation_pipeline_scopes_default_artifact_root_by_query_selection(
	tmp_path: Path,
) -> None:
	domain_file = _write_blocks_domain(tmp_path)
	pipeline = PlanLibraryGenerationPipeline(
		domain_file=str(domain_file),
		query_domain="blocksworld",
		query_ids=("query_1",),
		dfa_builder=FakeDFABuilder(),
	)

	assert pipeline._default_artifact_root("blocksworld").name == "query_1"


def _write_blocks_domain(tmp_path: Path) -> Path:
	domain_file = tmp_path / "domain.pddl"
	domain_file.write_text(
		"""
		(define (domain BLOCKS)
		 (:requirements :strips :typing)
		 (:types block)
		 (:predicates
		  (on ?x - block ?y - block)
		  (ontable ?x - block)
		  (clear ?x - block)
		  (handempty)
		  (holding ?x - block)
			 )
			 (:action stack
			  :parameters (?x - block ?y - block)
			  :precondition (and (clear ?x) (clear ?y))
			  :effect (and (on ?x ?y))
			 )
			)
		""",
		encoding="utf-8",
	)
	return domain_file


def _write_blocks_problem(tmp_path: Path, name: str) -> Path:
	problem_file = tmp_path / name
	problem_file.write_text(
		"""
		(define (problem p1)
		 (:domain BLOCKS)
		 (:objects b1 b2 - block)
		 (:init (clear b1) (clear b2))
		 (:goal (and (on b1 b2)))
		)
		""",
		encoding="utf-8",
	)
	return problem_file


def _write_fake_fast_downward(tmp_path: Path) -> Path:
	driver = tmp_path / "fake-fast-downward.py"
	driver.write_text(
		"""#!/usr/bin/env python3
import sys
from pathlib import Path

plan_file = Path(sys.argv[sys.argv.index("--plan-file") + 1])
plan_file.write_text("(stack b1 b2)\\n; cost = 1\\n", encoding="utf-8")
sys.exit(0)
""",
		encoding="utf-8",
	)
	os.chmod(driver, 0o755)
	return driver


def _write_query_dataset(tmp_path: Path) -> Path:
	query_dataset = tmp_path / "queries_LTLf.json"
	query_dataset.write_text(
		json.dumps(
			{
				"domains": {
					"blocksworld": {
						"cases": {
							"query_1": {
								"instruction": "Put b1 on b2.",
								"problem_file": "p01.pddl",
								"ltlf_formula": "do_put_on(b1, b2)",
							},
							"query_2": {
								"instruction": "Put b3 on b4.",
								"problem_file": "p02.pddl",
								"ltlf_formula": "do_put_on(b3, b4)",
							},
						},
					},
				},
			},
		),
		encoding="utf-8",
	)
	return query_dataset
