from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path

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


def test_merge_accepts_launchers_that_differ_only_by_install_prefix(
	tmp_path: Path,
) -> None:
	primary = _direct_primary()
	retry = _direct_retry()
	_configure_path_embedded_launcher_pair(primary, retry, tmp_path=tmp_path)

	merged = merge_infrastructure_retries(
		primary,
		retry,
		kind="direct_temporal",
		primary_sha256="c" * 64,
		retry_sha256="d" * 64,
	)

	verification = merged["infrastructure_repair"]["toolchain_verification"]
	assert verification["semantic_identity"] == (
		"exact_pinned_revisions_and_versions"
	)
	for launcher in ("fond4ltlf", "mona"):
		assert verification["path_embedded_launchers"][launcher]["equivalence"] == (
			"absolute_install_prefix_rewrite"
		)
		assert verification["path_embedded_launchers"][launcher][
			"retry_file_sha256_verified"
		] is True


def test_merge_rejects_unexplained_direct_launcher_hash_change(
	tmp_path: Path,
) -> None:
	primary = _direct_primary()
	retry = _direct_retry()
	_configure_path_embedded_launcher_pair(primary, retry, tmp_path=tmp_path)
	primary["toolchain"]["mona"]["executable_sha256"] = "0" * 64

	with pytest.raises(ValueError, match="MONA launcher fingerprint"):
		merge_infrastructure_retries(
			primary,
			retry,
			kind="direct_temporal",
			primary_sha256="c" * 64,
			retry_sha256="d" * 64,
		)


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


def _configure_path_embedded_launcher_pair(
	primary: dict[str, object],
	retry: dict[str, object],
	*,
	tmp_path: Path,
) -> None:
	primary_toolchain = primary["toolchain"]
	retry_toolchain = retry["toolchain"]
	assert isinstance(primary_toolchain, dict)
	assert isinstance(retry_toolchain, dict)
	primary_fond = primary_toolchain["fond4ltlf"]
	retry_fond = retry_toolchain["fond4ltlf"]
	primary_mona = primary_toolchain["mona"]
	retry_mona = retry_toolchain["mona"]
	assert isinstance(primary_fond, dict)
	assert isinstance(retry_fond, dict)
	assert isinstance(primary_mona, dict)
	assert isinstance(retry_mona, dict)

	primary_fond_root = Path("/remote/project/.external/fond4ltlf-0.0.4")
	retry_fond_root = tmp_path / "local/project/.external/fond4ltlf-0.0.4"
	retry_fond_executable = retry_fond_root / ".venv/bin/fond4ltlf"
	retry_fond_executable.parent.mkdir(parents=True)
	fond_bytes = f"#!{retry_fond_root}/.venv/bin/python\nentrypoint\n".encode()
	retry_fond_executable.write_bytes(fond_bytes)
	primary_fond_bytes = fond_bytes.replace(
		str(retry_fond_root).encode(),
		str(primary_fond_root).encode(),
	)
	primary_fond.update(
		{
			"root": str(primary_fond_root),
			"executable": str(primary_fond_root / ".venv/bin/fond4ltlf"),
			"executable_sha256": hashlib.sha256(primary_fond_bytes).hexdigest(),
		},
	)
	retry_fond.update(
		{
			"root": str(retry_fond_root),
			"executable": str(retry_fond_executable),
			"executable_sha256": hashlib.sha256(fond_bytes).hexdigest(),
		},
	)

	primary_mona_root = Path("/remote/project/.external/mona-1.4")
	retry_mona_root = tmp_path / "local/project/.external/mona-1.4"
	retry_mona_executable = retry_mona_root / "Front/mona"
	retry_mona_executable.parent.mkdir(parents=True)
	mona_bytes = f"root={retry_mona_root}\nexec .libs/mona\n".encode()
	retry_mona_executable.write_bytes(mona_bytes)
	primary_mona_bytes = mona_bytes.replace(
		str(retry_mona_root).encode(),
		str(primary_mona_root).encode(),
	)
	primary_mona.update(
		{
			"executable": str(primary_mona_root / "Front/mona"),
			"executable_sha256": hashlib.sha256(primary_mona_bytes).hexdigest(),
		},
	)
	retry_mona.update(
		{
			"executable": str(retry_mona_executable),
			"executable_sha256": hashlib.sha256(mona_bytes).hexdigest(),
		},
	)
