from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.merge_external_reference_retries import merge_infrastructure_retries


def test_merge_replaces_only_achievement_infrastructure_failures() -> None:
	merged = merge_infrastructure_retries(
		_achievement_primary(),
		_achievement_retry(),
		kind="achievement",
		primary_sha256="a" * 64,
		retry_sha256="b" * 64,
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
	assert provenance["primary_summary_sha256"] == "a" * 64
	assert merged["results"][1]["infrastructure_retry"]["primary_status"] == (
		"runner_error"
	)


def test_merge_requires_exact_infrastructure_retry_case_set() -> None:
	retry = _achievement_retry()
	retry["results"].append(
		{
			**deepcopy(retry["results"][0]),
			"problem_file": "/local/p3.pddl",
			"problem_sha256": "3" * 64,
		},
	)

	with pytest.raises(ValueError, match="retry case set"):
		merge_infrastructure_retries(
			_achievement_primary(),
			retry,
			kind="achievement",
			primary_sha256="a" * 64,
			retry_sha256="b" * 64,
		)


def test_merge_rejects_changed_retry_input_fingerprint() -> None:
	retry = _achievement_retry()
	retry["results"][0]["problem_sha256"] = "x" * 64

	with pytest.raises(ValueError, match="input fingerprint"):
		merge_infrastructure_retries(
			_achievement_primary(),
			retry,
			kind="achievement",
			primary_sha256="a" * 64,
			retry_sha256="b" * 64,
		)


def test_merge_recomputes_direct_metrics_after_scientific_failure() -> None:
	merged = merge_infrastructure_retries(
		_direct_primary(),
		_direct_retry(),
		kind="direct_temporal",
		primary_sha256="c" * 64,
		retry_sha256="d" * 64,
	)

	assert merged["success"] is True
	assert merged["infrastructure_failure_count"] == 0
	assert merged["metrics"]["case_count"] == 2
	assert merged["metrics"]["supported_case_count"] == 1
	assert merged["metrics"]["unsupported_case_count"] == 1
	assert merged["metrics"]["valid_trace_count"] == 0
	assert merged["results"][0]["status"] == "planner_failed"


def _revision(commit: str) -> dict[str, object]:
	return {
		"available": True,
		"commit": commit,
		"tracked_changes": False,
		"untracked_files": False,
	}


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
			"artifact_sha256": "m" * 64,
			"docker_image": "moose-exact-ubuntu22:local",
			"git_revision": "g" * 40,
		},
		"enhsp": {
			"configuration": "sat-hmrphj",
			"git_revision": "e" * 40,
			"jar_sha256": "j" * 64,
		},
	}


def _achievement_record(problem: str, *, status: str, valid: bool) -> dict[str, object]:
	return {
		"method": "LAMA",
		"variant": "lama",
		"domain": "toy",
		"domain_sha256": "d" * 64,
		"problem_file": f"/machine/{problem}.pddl",
		"problem_sha256": problem[-1] * 64,
		"status": status,
		"plan_verifier_success": valid,
		"elapsed_seconds": 1.0,
		"action_count": 1 if valid else 0,
	}


def _achievement_primary() -> dict[str, object]:
	return {
		"artifact_kind": "external_achievement_planning_references",
		"run_id": "primary-c",
		"success": False,
		"infrastructure_failure_count": 1,
		"source_revision": _revision("1" * 40),
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
		"run_id": "retry-c",
		"success": True,
		"infrastructure_failure_count": 0,
		"source_revision": _revision("2" * 40),
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
			"git_revision": "f" * 40,
			"release": "v0.0.4",
			"executable_sha256": "x" * 64,
			"isolation_wrapper_sha256": "w" * 64,
		},
		"mona": {"version": "1.4-18", "executable_sha256": "n" * 64},
		"lama": {
			"moose_artifact_sha256": "m" * 64,
			"moose_git_revision": "g" * 40,
			"docker_image": "moose-exact-ubuntu22:local",
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
		"domain": "toy",
		"sample_id": sample_id,
		"profile": "eventually",
		"domain_sha256": "d" * 64,
		"problem_file": f"/machine/{sample_id}.pddl",
		"problem_sha256": sample_id[-1] * 64,
		"status": status,
		"supported": supported,
		"success": success,
		"elapsed_seconds": 2.0,
		"action_count": 1 if success else 0,
	}


def _direct_primary() -> dict[str, object]:
	return {
		"artifact_kind": "direct_temporal_planning_reference",
		"run_id": "primary-d",
		"success": False,
		"infrastructure_failure_count": 1,
		"selected_case_count": 2,
		"benchmark_sha256": "b" * 64,
		"source_revision": _revision("1" * 40),
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
		"run_id": "retry-d",
		"success": True,
		"infrastructure_failure_count": 0,
		"selected_case_count": 1,
		"benchmark_sha256": "b" * 64,
		"source_revision": _revision("2" * 40),
		"parameters": _direct_parameters(1),
		"toolchain": _direct_toolchain(),
		"results": [record],
	}
