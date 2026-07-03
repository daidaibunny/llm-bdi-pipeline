from __future__ import annotations

import json
from pathlib import Path

from execution_logging.execution_logger import ExecutionLogger


def test_execution_logger_records_temporal_append_pipeline(tmp_path: Path) -> None:
	logger = ExecutionLogger(logs_dir=tmp_path, run_origin="tests")

	logger.start_pipeline(
		"Build X on Y, then clear X.",
		mode="temporal_goal_append",
		domain_file="/tmp/domain.pddl",
		problem_file="/tmp/problem.pddl",
		domain_name="blocks",
		problem_name="p01",
	)
	logger.log_input_artifact(
		{
			"schema_version": 1,
			"goal_name": "g_query_1",
			"ltlf_formula": "F(on(X,Y) & X(F(clear(X))))",
		},
		status="success",
		metadata={"source": "external_input_module"},
	)
	logger.log_dfa_validation(
		{
			"valid": True,
			"errors": [],
			"transition_count": 2,
		},
		status="success",
	)
	logger.log_agentspeak_append(
		{
			"goal_name": "g_query_1",
			"appended_plan_count": 3,
		},
		status="success",
	)
	log_path = logger.end_pipeline(success=True)

	execution = json.loads((log_path.parent / "execution.json").read_text(encoding="utf-8"))
	text_log = log_path.read_text(encoding="utf-8")

	assert execution["mode"] == "temporal_goal_append"
	assert execution["input_artifact"]["metadata"]["source"] == "external_input_module"
	assert execution["dfa_validation"]["artifacts"]["valid"] is True
	assert execution["agentspeak_append"]["artifacts"]["goal_name"] == "g_query_1"
	assert "TEMPORAL GOAL APPEND" in text_log
	assert "DFA VALIDATION" in text_log
	assert "AGENTSPEAK APPEND" in text_log


def test_execution_logger_externalizes_large_llm_payloads(tmp_path: Path) -> None:
	logger = ExecutionLogger(logs_dir=tmp_path, run_origin="tests")
	logger.start_pipeline(
		"query",
		mode="input_handoff_validation",
		domain_file="/tmp/domain.pddl",
		domain_name="blocks",
	)
	logger.log_input_artifact(
		{"ltlf_formula": "F(done(X))"},
		status="failed",
		error="non-singleton transition",
		llm={
			"model": "external-sota-model",
			"prompt": {"system": "s" * 5000, "user": "u" * 5000},
			"response": "r" * 8000,
		},
	)
	log_path = logger.end_pipeline(success=False)
	execution = json.loads((log_path.parent / "execution.json").read_text(encoding="utf-8"))

	llm = execution["input_artifact"]["llm"]
	assert "prompt" not in llm
	assert "response" not in llm
	assert llm["prompt_file"].endswith("input_artifact_llm_prompt.json")
	assert llm["response_file"].endswith("input_artifact_llm_response.txt")
	assert (log_path.parent / llm["prompt_file"]).exists()
	assert (log_path.parent / llm["response_file"]).exists()
