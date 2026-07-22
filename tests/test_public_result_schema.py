from __future__ import annotations

from scripts.public_result_schema import outcome_only_payload


def test_outcome_only_payload_removes_execution_process_metadata() -> None:
	payload = outcome_only_payload(
		{
			"status": "valid",
			"compiler_lock_wait_seconds": 1.0,
			"infrastructure_retry": {
				"primary_status": "planner_failed",
				"retry_num_workers": 1,
			},
			"planner_exit_code": 0,
			"repair_num_workers": 1,
			"runtime_lock_wait_seconds": 2.0,
		},
	)

	assert payload == {"status": "valid"}
