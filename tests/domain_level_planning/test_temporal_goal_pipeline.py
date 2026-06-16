from __future__ import annotations

import json
from pathlib import Path

from domain_level_planning import (
	build_domain_level_temporal_artifact,
	execute_dfa_progress_step,
	persist_domain_level_temporal_artifact,
)
from plan_library.rendering import render_plan_library_asl


class FakeDFABuilder:
	def build(self, record):
		return {
			"formula": record.ltlf_formula,
			"initial_state": "q0",
			"accepting_states": ["q1"],
			"guarded_transitions": [
				{"source_state": "q0", "target_state": "q1", "raw_label": "done"},
			],
		}


class FakeUnsupportedDFABuilder:
	def build(self, record):
		return {
			"formula": record.ltlf_formula,
			"initial_state": "q0",
			"accepting_states": ["q1"],
			"guarded_transitions": [
				{"source_state": "q0", "target_state": "q1", "raw_label": "not done"},
			],
		}


class FakeBranchingDFABuilder:
	def build(self, record):
		return {
			"formula": record.ltlf_formula,
			"initial_state": "q0",
			"accepting_states": ["q1"],
			"guarded_transitions": [
				{"source_state": "q0", "target_state": "q1", "raw_label": "done"},
				{"source_state": "q0", "target_state": "q0", "raw_label": "ready"},
			],
		}


def test_temporal_goal_artifact_keeps_dfa_query_specific_and_library_domain_level(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_tiny_domain_and_problem(tmp_path)
	query_dataset = _write_query_dataset(tmp_path)

	artifact = build_domain_level_temporal_artifact(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		query_dataset=query_dataset,
		query_domain="tiny",
		query_ids=("query_1",),
		dfa_builder=FakeDFABuilder(),
	)
	asl = render_plan_library_asl(artifact.plan_library)

	assert artifact.domain_name == "tiny"
	assert artifact.query_domain == "tiny"
	assert artifact.synthesis_result.report["domain_level_contract"]["passed"] is True
	assert set(artifact.dfa_metadata) == {"query_1"}
	assert artifact.dfa_progress_requests["query_1"][0].goal_facts == ("goal_done",)
	assert artifact.dfa_progress_requests["query_1"][0].body_steps[0].symbol == "done"
	assert "+!g : goal_done & not done <-" in asl
	assert "transition_" not in asl
	assert "achieve_" not in asl
	assert "dfa_state" not in asl

	execution = execute_dfa_progress_step(
		plan_library=artifact.plan_library,
		domain_file=domain_file,
		domain_key="tiny",
		dfa_payload=artifact.dfa_metadata["query_1"],
		current_dfa_state="q0",
		current_state=frozenset({"ready"}),
	)

	assert execution.progressed is True
	assert execution.target_dfa_state == "q1"
	assert execution.execution is not None
	assert execution.execution.steps == ("finish",)


def test_temporal_goal_artifact_persistence_writes_controller_requests(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_tiny_domain_and_problem(tmp_path)
	query_dataset = _write_query_dataset(tmp_path)
	artifact = build_domain_level_temporal_artifact(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		query_dataset=query_dataset,
		query_domain="tiny",
		query_ids=("query_1",),
		dfa_builder=FakeDFABuilder(),
	)

	paths = persist_domain_level_temporal_artifact(
		artifact_root=tmp_path / "artifact",
		artifact=artifact,
	)

	assert Path(paths["plan_library_asl"]).exists()
	assert Path(paths["dfa_progress_requests"]).exists()
	requests = json.loads(Path(paths["dfa_progress_requests"]).read_text(encoding="utf-8"))
	metadata = json.loads(Path(paths["artifact_metadata"]).read_text(encoding="utf-8"))

	assert requests["query_1"][0]["goal_facts"] == ["goal_done"]
	assert requests["query_1"][0]["achievement_subgoals"] == [
		{"kind": "subgoal", "symbol": "done", "arguments": []},
	]
	assert Path(paths["dfa_progress_diagnostics"]).exists()
	diagnostics = json.loads(
		Path(paths["dfa_progress_diagnostics"]).read_text(encoding="utf-8"),
	)
	assert diagnostics["query_1"][0]["diagnostic"]["supported"] is True
	assert "request_object" not in diagnostics["query_1"][0]["diagnostic"]
	assert metadata["domain_level_library_plan_count"] == len(artifact.plan_library.plans)
	assert metadata["dfa_progress_request_count"] == 1


def test_temporal_goal_artifact_records_rejected_dfa_guard_diagnostics(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_tiny_domain_and_problem(tmp_path)
	query_dataset = _write_query_dataset(tmp_path)
	artifact = build_domain_level_temporal_artifact(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		query_dataset=query_dataset,
		query_domain="tiny",
		query_ids=("query_1",),
		dfa_builder=FakeUnsupportedDFABuilder(),
	)

	assert artifact.dfa_progress_requests["query_1"] == ()
	diagnostics = artifact.dfa_progress_diagnostics["query_1"]
	assert len(diagnostics) == 1
	assert diagnostics[0]["source_state"] == "q0"
	assert diagnostics[0]["target_state"] == "q1"
	assert diagnostics[0]["diagnostic"]["supported"] is False
	assert diagnostics[0]["diagnostic"]["rejection_reason"] == (
		"unsupported_negative_or_disjunctive_guard"
	)

	paths = persist_domain_level_temporal_artifact(
		artifact_root=tmp_path / "unsupported-artifact",
		artifact=artifact,
	)
	persisted = json.loads(
		Path(paths["dfa_progress_diagnostics"]).read_text(encoding="utf-8"),
	)
	assert persisted["query_1"][0]["diagnostic"]["rejection_reason"] == (
		"unsupported_negative_or_disjunctive_guard"
	)


def test_temporal_goal_artifact_diagnostics_follow_progress_transitions_only(
	tmp_path: Path,
) -> None:
	domain_file, problem_file = _write_tiny_domain_and_problem(tmp_path)
	query_dataset = _write_query_dataset(tmp_path)
	artifact = build_domain_level_temporal_artifact(
		domain_file=domain_file,
		training_problem_files=(problem_file,),
		query_dataset=query_dataset,
		query_domain="tiny",
		query_ids=("query_1",),
		dfa_builder=FakeBranchingDFABuilder(),
	)

	assert [request.target_state for request in artifact.dfa_progress_requests["query_1"]] == [
		"q1",
	]
	assert [
		diagnostic["target_state"]
		for diagnostic in artifact.dfa_progress_diagnostics["query_1"]
	] == ["q1"]


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


def _write_query_dataset(tmp_path: Path) -> Path:
	query_dataset = tmp_path / "queries_LTLf.json"
	query_dataset.write_text(
		json.dumps(
			{
				"domains": {
					"tiny": {
						"cases": {
							"query_1": {
								"instruction": "Eventually finish.",
								"problem_file": "problem.pddl",
								"ltlf_formula": "F(done)",
							},
						},
					},
				},
			},
		),
		encoding="utf-8",
	)
	return query_dataset
