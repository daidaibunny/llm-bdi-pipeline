from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.merge_external_reference_retries import merge_infrastructure_retries


def test_merge_replaces_only_achievement_infrastructure_failures() -> None:
	merged = merge_infrastructure_retries(
		_achievement_primary(),
		_achievement_retry(),
		kind="achievement",
	)

	assert merged["success"] is True
	assert merged["infrastructure_failure_count"] == 0
	assert merged["metrics"]["case_count"] == 2
	assert merged["metrics"]["valid_trace_count"] == 2
	assert [record["status"] for record in merged["results"]] == ["valid", "valid"]
	provenance = merged["infrastructure_repair"]
	assert provenance["replaced_case_count"] == 1
	assert provenance["primary_num_workers"] == 20
	assert provenance["retry_num_workers"] == 1
	assert provenance["runtime_comparison_allowed"] is True
	assert provenance["hardware_equivalence_confirmed_by_experiment_owner"] is True
	assert provenance["semantic_inputs_verified"] is True
	assert merged["results"][1]["infrastructure_retry"]["primary_status"] == (
		"runner_error"
	)


def test_merge_requires_exact_infrastructure_retry_case_set() -> None:
	retry = _achievement_retry()
	retry["results"].append(
		{
			**deepcopy(retry["results"][0]),
			"problem_file": "/local/p3.pddl",
		},
	)

	with pytest.raises(ValueError, match="retry case set"):
		merge_infrastructure_retries(
			_achievement_primary(),
			retry,
			kind="achievement",
		)


def test_merge_rejects_changed_retry_semantic_input() -> None:
	retry = _achievement_retry()
	retry["results"][0]["method"] = "different"

	with pytest.raises(ValueError, match="semantic input"):
		merge_infrastructure_retries(
			_achievement_primary(),
			retry,
			kind="achievement",
		)


def test_merge_recomputes_direct_metrics_after_scientific_failure() -> None:
	merged = merge_infrastructure_retries(
		_direct_primary(),
		_direct_retry(),
		kind="direct_temporal",
	)

	assert merged["success"] is True
	assert merged["infrastructure_failure_count"] == 0
	assert merged["metrics"]["case_count"] == 2
	assert merged["metrics"]["supported_case_count"] == 1
	assert merged["metrics"]["unsupported_case_count"] == 1
	assert merged["metrics"]["valid_trace_count"] == 0
	assert merged["results"][0]["status"] == "planner_failed"


def test_merge_accepts_different_install_paths_for_same_tool_versions() -> None:
	primary = _direct_primary()
	retry = _direct_retry()
	primary["toolchain"]["fond4ltlf"]["executable"] = "/primary/fond4ltlf"
	retry["toolchain"]["fond4ltlf"]["executable"] = "/retry/fond4ltlf"

	merged = merge_infrastructure_retries(
		primary,
		retry,
		kind="direct_temporal",
	)

	verification = merged["infrastructure_repair"]["toolchain_verification"]
	assert verification["semantic_identity"] == "declared_versions_and_configurations"


def test_merge_rejects_changed_direct_tool_version() -> None:
	primary = _direct_primary()
	retry = _direct_retry()
	retry["toolchain"]["mona"]["version"] = "different"

	with pytest.raises(ValueError, match="external toolchain"):
		merge_infrastructure_retries(
			primary,
			retry,
			kind="direct_temporal",
		)


def _achievement_parameters(num_workers: int) -> dict[str, object]:
	return {
		"num_workers": num_workers,
		"timeout_seconds": 1800,
		"max_rss_gb": 8.0,
		"plan_verifier_timeout_seconds": 1800,
		"plan_verifier_command": "bash /machine/validate_with_docker_val.sh",
		"moose_runtime_backend": "sandbox",
		"moose_runtime_max_parallelism": num_workers,
		"moose_runtime_lock_scope": "none",
	}


def _achievement_toolchain() -> dict[str, object]:
	return {
		"moose": {
			"docker_image": "moose-exact-ubuntu22:local",
			"runtime_backend": "sandbox",
		},
		"enhsp": {
			"configuration": "sat-hmrphj",
		},
	}


def _achievement_record(problem: str, *, status: str, valid: bool) -> dict[str, object]:
	return {
		"method": "LAMA",
		"variant": "lama",
		"domain": "toy",
		"problem_file": f"/machine/{problem}.pddl",
		"status": status,
		"plan_verifier_success": valid,
		"elapsed_seconds": 1.0,
		"action_count": 1 if valid else 0,
	}


def _achievement_primary() -> dict[str, object]:
	return {
		"artifact_kind": "external_achievement_planning_references",
		"success": False,
		"infrastructure_failure_count": 1,
		"parameters": _achievement_parameters(20),
		"toolchain": _achievement_toolchain(),
		"results": [
			_achievement_record("p1", status="valid", valid=True),
			_achievement_record("p2", status="runner_error", valid=False),
		],
	}


def _achievement_retry() -> dict[str, object]:
	record = _achievement_record("p2", status="valid", valid=True)
	record["problem_file"] = "/local/p2.pddl"
	return {
		"artifact_kind": "external_achievement_planning_references",
		"success": True,
		"infrastructure_failure_count": 0,
		"parameters": _achievement_parameters(1),
		"toolchain": _achievement_toolchain(),
		"results": [record],
	}

def _direct_parameters(num_workers: int) -> dict[str, object]:
	return {
		"num_workers": num_workers,
		"timeout_seconds_total_compile_and_plan": 1800,
		"max_rss_gb": 8.0,
		"plan_verifier_timeout_seconds": 1800,
		"plan_verifier_command": "bash /machine/validate_with_docker_val.sh",
		"fond4ltlf_compiler_isolation": "per_case_mona_workspace",
		"fond4ltlf_compiler_max_parallelism": num_workers,
		"fond4ltlf_compiler_lock_scope": "none",
		"moose_runtime_backend": "sandbox",
		"moose_runtime_max_parallelism": num_workers,
		"moose_runtime_lock_scope": "none",
	}


def _direct_toolchain() -> dict[str, object]:
	return {
		"fond4ltlf": {
			"release": "v0.0.4",
		},
		"mona": {"version": "1.4-18"},
		"lama": {
			"docker_image": "moose-exact-ubuntu22:local",
			"runtime_backend": "sandbox",
		},
	}


def _direct_record(
	sample_id: str,
	*,
	status: str,
	supported: bool,
	success: bool,
) -> dict[str, object]:
	return {
		"method": "FOND4LTLf + LAMA",
		"variant": "direct_temporal",
		"domain": "toy",
		"sample_id": sample_id,
		"profile": "eventually",
		"grounded_formula": "F(done)",
		"problem_file": f"/machine/{sample_id}.pddl",
		"status": status,
		"supported": supported,
		"success": success,
		"elapsed_seconds": 2.0,
		"action_count": 1 if success else 0,
	}


def _direct_primary() -> dict[str, object]:
	return {
		"artifact_kind": "direct_temporal_planning_reference",
		"success": False,
		"infrastructure_failure_count": 1,
		"selected_case_count": 2,
		"benchmark_id": "benchmark-v1",
		"parameters": _direct_parameters(20),
		"toolchain": _direct_toolchain(),
		"results": [
			_direct_record(
				"s1",
				status="planner_runner_error",
				supported=True,
				success=False,
			),
			_direct_record(
				"s2",
				status="unsupported_numeric_pddl",
				supported=False,
				success=False,
			),
		],
	}


def _direct_retry() -> dict[str, object]:
	record = _direct_record(
		"s1",
		status="planner_failed",
		supported=True,
		success=False,
	)
	record["problem_file"] = "/local/s1.pddl"
	return {
		"artifact_kind": "direct_temporal_planning_reference",
		"success": True,
		"infrastructure_failure_count": 0,
		"selected_case_count": 1,
		"benchmark_id": "benchmark-v1",
		"parameters": _direct_parameters(1),
		"toolchain": _direct_toolchain(),
		"results": [record],
	}
