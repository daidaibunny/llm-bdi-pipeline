from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.merge_direct_temporal_domain_results import merge_domain_results


def test_merge_replaces_one_complete_domain_and_recomputes_metrics() -> None:
	base = _summary(
		domains=("alpha", "beta"),
		records=(
			_record("alpha_1", domain="alpha", status="planner_failed"),
			_record("alpha_2", domain="alpha", status="no_plan"),
			_record("beta_1", domain="beta", status="valid"),
		),
		run_id="base",
	)
	replacement = _summary(
		domains=("alpha",),
		records=(
			_record("alpha_1", domain="alpha", status="valid"),
			_record("alpha_2", domain="alpha", status="valid"),
		),
		run_id="replacement",
	)

	merged = merge_domain_results(base, replacement)

	assert merged["selected_case_count"] == 3
	assert merged["metrics"]["valid_trace_count"] == 3
	assert merged["infrastructure_failure_count"] == 0
	assert merged["success"] is True
	assert [record["sample_id"] for record in merged["results"]] == [
		"alpha_1",
		"alpha_2",
		"beta_1",
	]
	assert merged["domain_rerun"]["replacement_domain"] == "alpha"
	assert merged["domain_rerun"]["replaced_case_count"] == 2


def test_merge_rejects_partial_domain_replacement() -> None:
	base = _summary(
		domains=("alpha",),
		records=(
			_record("alpha_1", domain="alpha", status="planner_failed"),
			_record("alpha_2", domain="alpha", status="no_plan"),
		),
		run_id="base",
	)
	replacement = _summary(
		domains=("alpha",),
		records=(_record("alpha_1", domain="alpha", status="valid"),),
		run_id="replacement",
	)

	with pytest.raises(ValueError, match="complete base domain case set"):
		merge_domain_results(base, replacement)


def test_merge_rejects_changed_temporal_input() -> None:
	base = _summary(
		domains=("alpha",),
		records=(_record("alpha_1", domain="alpha", status="planner_failed"),),
		run_id="base",
	)
	replacement = _summary(
		domains=("alpha",),
		records=(_record("alpha_1", domain="alpha", status="valid"),),
		run_id="replacement",
	)
	replacement["results"][0]["tide_temporal_goal"] = "(eventually (other))"

	with pytest.raises(ValueError, match="semantic input changed"):
		merge_domain_results(base, replacement)


def test_merge_rejects_changed_tide_toolchain() -> None:
	base = _summary(
		domains=("alpha",),
		records=(_record("alpha_1", domain="alpha", status="planner_failed"),),
		run_id="base",
	)
	replacement = deepcopy(base)
	replacement["run_id"] = "replacement"
	replacement["toolchain"]["tide"]["pinned_revision"] = "different"

	with pytest.raises(ValueError, match="TIDE toolchain"):
		merge_domain_results(base, replacement)


def _record(sample_id: str, *, domain: str, status: str) -> dict[str, object]:
	valid = status == "valid"
	return {
		"sample_id": sample_id,
		"domain": domain,
		"profile": "ordered_two_milestone",
		"method": "TIDE + LAMA",
		"variant": "tide_lama",
		"domain_sha256": "domain-sha",
		"problem_sha256": f"{sample_id}-sha",
		"tide_temporal_goal": "(eventually (done))",
		"status": status,
		"supported": True,
		"success": valid,
		"elapsed_seconds": 2.0,
		"action_count": 1 if valid else 0,
	}


def _summary(
	*,
	domains: tuple[str, ...],
	records: tuple[dict[str, object], ...],
	run_id: str,
) -> dict[str, object]:
	return {
		"artifact_kind": "direct_temporal_planning_reference",
		"schema_version": 1,
		"run_id": run_id,
		"benchmark_id": "benchmark-v1",
		"benchmark_sha256": "benchmark-sha",
		"method": "TIDE + LAMA",
		"variant": "tide_lama",
		"domains": list(domains),
		"selected_case_count": len(records),
		"started_at": "2026-01-01T00:00:00",
		"finished_at": "2026-01-01T00:01:00",
		"source_revision": {"commit": run_id},
		"parameters": {
			"num_workers": 12,
			"timeout_seconds_total_compile_and_plan": 1800,
			"max_rss_gb": 8,
			"plan_verifier_timeout_seconds": 1800,
			"tide_internal_runs_per_case": 1,
			"tide_subproblem_timeout_ms": 60_000,
			"tide_configuration": (
				"feedback+trace-heuristic+prefix-cache+lama-first"
			),
		},
		"toolchain": {
			"mona": {"version": "1.4-18"},
			"tide": {
				"pinned_revision": "tide-revision",
				"configuration": {"search": "lama-first"},
			},
		},
		"results": [deepcopy(record) for record in records],
		"infrastructure_failure_count": 0,
		"success": True,
	}
