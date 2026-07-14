from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.generate_aaai_comparison_tables import build_comparison_dataset
from scripts.generate_aaai_comparison_tables import render_atomic_table
from scripts.generate_aaai_comparison_tables import render_external_table
from scripts.generate_aaai_comparison_tables import render_temporal_table
from scripts.run_certificate_challenge_matrix import CHALLENGE_CASES
from scripts.run_certificate_challenge_matrix import METAMORPHIC_CASES


ATOMIC_VARIANTS = (
	("validated_evidence_adapter", "Evidence Only"),
	("action_only_closure", "Action Closure"),
	("maximal_certified_program", "Maximal Certified"),
	("full", "Full GP2PL"),
)
TEMPORAL_VARIANTS = (
	("dfa_aware_unprotected", "Unprotected DFA"),
	("certified_flat", "Certified Flat"),
	("certified_balanced", "Certified Balanced"),
	("completion_boundary_monitor", "Completion Monitor"),
)
BENCHMARK_HASH = "a" * 64
ENHSP_REVISION = "537bed55a60d9456975c56afbadd50fc8acb1dc9"
FOND4LTLF_REVISION = "011d9d9a5bfd6406d2c358faf8f63167f6c839bb"


def test_comparison_table_cli_runs_from_script_path() -> None:
	project_root = Path(__file__).resolve().parents[1]
	completed = subprocess.run(
		[
			sys.executable,
			str(project_root / "scripts/generate_aaai_comparison_tables.py"),
			"--help",
		],
		cwd=project_root,
		check=False,
		capture_output=True,
		text=True,
	)

	assert completed.returncode == 0, completed.stderr
	assert "Validate final comparison artifacts" in completed.stdout


def test_build_comparison_dataset_aggregates_registered_matrix(tmp_path: Path) -> None:
	paired = _write_json(tmp_path / "paired.json", _paired_fixture())
	raw_summaries = tuple(
		(seed, _write_json(tmp_path / f"raw-{seed}.json", _raw_fixture(seed)))
		for seed in range(5)
	)
	instance_summary = _write_json(tmp_path / "instances.json", _instance_fixture())
	direct_summary = _write_json(tmp_path / "direct.json", _direct_fixture())
	challenge_summary = _write_json(tmp_path / "challenge.json", _challenge_fixture())

	result = build_comparison_dataset(
		paired_results_file=paired,
		raw_moose_summaries=raw_summaries,
		instance_reference_summary_file=instance_summary,
		direct_temporal_summary_file=direct_summary,
		challenge_summary_file=challenge_summary,
	)

	assert [row["method"] for row in result["atomic"]] == [
		name for _variant, name in ATOMIC_VARIANTS
	]
	assert result["atomic"][0]["compiled_count"] == 5
	assert result["atomic"][0]["compiled_total"] == 5
	assert result["atomic"][0]["covered_target_count"] == 5
	assert result["atomic"][0]["producible_target_count"] == 10
	assert result["atomic"][0]["valid_trace_count"] == 5
	assert result["atomic"][0]["test_count"] == 10
	assert result["atomic"][0]["mean_branch_count"] == 1
	assert result["atomic"][3]["mean_branch_count"] == 4
	assert result["atomic_joint_action_case_count"] == 5

	assert [row["method"] for row in result["temporal"]] == [
		name for _variant, name in TEMPORAL_VARIANTS
	]
	assert result["temporal"][0]["valid_trace_count"] == 1
	assert result["temporal"][2]["valid_trace_count"] == 2
	assert result["temporal_joint_action_case_count"] == 1
	assert result["temporal"][2]["median_joint_action_count"] == 3

	external = {row["method"]: row for row in result["external"]}
	assert external["Raw MOOSE"]["valid_trace_count"] == 5
	assert external["Raw MOOSE"]["case_count"] == 10
	assert external["Raw MOOSE"]["par2_seconds"] == 1800.5
	assert external["LAMA"]["valid_trace_count"] == 1
	assert external["MRP+HJ"]["valid_trace_count"] == 1
	assert external["FOND4LTLf + LAMA"]["supported_case_count"] == 1
	assert external["FOND4LTLf + LAMA"]["unsupported_case_count"] == 1
	assert result["challenges"]["success_count"] == 13


def test_build_comparison_dataset_rejects_incomplete_atomic_pairing(
	tmp_path: Path,
) -> None:
	payload = _paired_fixture()
	payload["atomic_runs"] = payload["atomic_runs"][:-1]
	paired = _write_json(tmp_path / "paired.json", payload)

	with pytest.raises(ValueError, match="atomic run matrix"):
		build_comparison_dataset(
			paired_results_file=paired,
			raw_moose_summaries=tuple(
				(seed, _write_json(tmp_path / f"raw-{seed}.json", _raw_fixture(seed)))
				for seed in range(5)
			),
			instance_reference_summary_file=_write_json(
				tmp_path / "instances.json",
				_instance_fixture(),
			),
			direct_temporal_summary_file=_write_json(
				tmp_path / "direct.json",
				_direct_fixture(),
			),
			challenge_summary_file=_write_json(
				tmp_path / "challenge.json",
				_challenge_fixture(),
			),
		)


def test_build_comparison_dataset_rejects_nonregistered_resource_protocol(
	tmp_path: Path,
) -> None:
	paired_payload = _paired_fixture()
	paired_payload["num_workers"] = 12

	with pytest.raises(ValueError, match="registered worker count"):
		build_comparison_dataset(
			paired_results_file=_write_json(
				tmp_path / "paired.json",
				paired_payload,
			),
			raw_moose_summaries=tuple(
				(seed, _write_json(tmp_path / f"raw-{seed}.json", _raw_fixture(seed)))
				for seed in range(5)
			),
			instance_reference_summary_file=_write_json(
				tmp_path / "instances.json",
				_instance_fixture(),
			),
			direct_temporal_summary_file=_write_json(
				tmp_path / "direct.json",
				_direct_fixture(),
			),
			challenge_summary_file=_write_json(
				tmp_path / "challenge.json",
				_challenge_fixture(),
			),
		)


def test_build_comparison_dataset_rejects_external_resource_protocol_drift(
	tmp_path: Path,
) -> None:
	raw_summaries = []
	for seed in range(5):
		payload = _raw_fixture(seed)
		if seed == 2:
			payload["parameters"]["max_rss_gb"] = 16.0
		raw_summaries.append(
			(seed, _write_json(tmp_path / f"raw-{seed}.json", payload)),
		)

	with pytest.raises(ValueError, match="Raw MOOSE seed 2.*memory limit"):
		build_comparison_dataset(
			paired_results_file=_write_json(
				tmp_path / "paired.json",
				_paired_fixture(),
			),
			raw_moose_summaries=tuple(raw_summaries),
			instance_reference_summary_file=_write_json(
				tmp_path / "instances.json",
				_instance_fixture(),
			),
			direct_temporal_summary_file=_write_json(
				tmp_path / "direct.json",
				_direct_fixture(),
			),
			challenge_summary_file=_write_json(
				tmp_path / "challenge.json",
				_challenge_fixture(),
			),
		)


def test_build_comparison_dataset_accepts_mixed_clean_source_revisions(
	tmp_path: Path,
) -> None:
	challenge = _challenge_fixture()
	challenge["source_revision"] = {
		**challenge["source_revision"],
		"commit": "fedcba9876543210",
	}

	result = build_comparison_dataset(
		paired_results_file=_write_json(
			tmp_path / "paired.json",
			_paired_fixture(),
		),
		raw_moose_summaries=tuple(
			(seed, _write_json(tmp_path / f"raw-{seed}.json", _raw_fixture(seed)))
			for seed in range(5)
		),
		instance_reference_summary_file=_write_json(
			tmp_path / "instances.json",
			_instance_fixture(),
		),
		direct_temporal_summary_file=_write_json(
			tmp_path / "direct.json",
			_direct_fixture(),
		),
		challenge_summary_file=_write_json(
			tmp_path / "challenge.json",
			challenge,
		),
	)

	assert result["external"]


def test_build_comparison_dataset_rejects_child_run_protocol_drift(
	tmp_path: Path,
) -> None:
	paired_payload = _paired_fixture()
	paired_payload["atomic_runs"][0]["summary"]["settings"]["timeout_seconds"] = 300

	with pytest.raises(ValueError, match="atomic child run.*registered timeout"):
		build_comparison_dataset(
			paired_results_file=_write_json(
				tmp_path / "paired.json",
				paired_payload,
			),
			raw_moose_summaries=tuple(
				(seed, _write_json(tmp_path / f"raw-{seed}.json", _raw_fixture(seed)))
				for seed in range(5)
			),
			instance_reference_summary_file=_write_json(
				tmp_path / "instances.json",
				_instance_fixture(),
			),
			direct_temporal_summary_file=_write_json(
				tmp_path / "direct.json",
				_direct_fixture(),
			),
			challenge_summary_file=_write_json(
				tmp_path / "challenge.json",
				_challenge_fixture(),
			),
		)


def test_build_comparison_dataset_rejects_shared_wrong_temporal_benchmark(
	tmp_path: Path,
) -> None:
	paired_payload = _paired_fixture()
	for run in paired_payload["temporal_runs"]:
		run["benchmark_sha256"] = "wrong-benchmark"

	with pytest.raises(ValueError, match="registered temporal benchmark"):
		build_comparison_dataset(
			paired_results_file=_write_json(
				tmp_path / "paired.json",
				paired_payload,
			),
			raw_moose_summaries=tuple(
				(seed, _write_json(tmp_path / f"raw-{seed}.json", _raw_fixture(seed)))
				for seed in range(5)
			),
			instance_reference_summary_file=_write_json(
				tmp_path / "instances.json",
				_instance_fixture(),
			),
			direct_temporal_summary_file=_write_json(
				tmp_path / "direct.json",
				_direct_fixture(),
			),
			challenge_summary_file=_write_json(
				tmp_path / "challenge.json",
				_challenge_fixture(),
			),
		)


def test_build_comparison_dataset_rejects_unpinned_external_toolchain(
	tmp_path: Path,
) -> None:
	direct = _direct_fixture()
	direct["toolchain"]["fond4ltlf"]["git_revision"] = "wrong"

	with pytest.raises(ValueError, match="pinned FOND4LTLf revision"):
		build_comparison_dataset(
			paired_results_file=_write_json(
				tmp_path / "paired.json",
				_paired_fixture(),
			),
			raw_moose_summaries=tuple(
				(seed, _write_json(tmp_path / f"raw-{seed}.json", _raw_fixture(seed)))
				for seed in range(5)
			),
			instance_reference_summary_file=_write_json(
				tmp_path / "instances.json",
				_instance_fixture(),
			),
			direct_temporal_summary_file=_write_json(
				tmp_path / "direct.json",
				direct,
			),
			challenge_summary_file=_write_json(
				tmp_path / "challenge.json",
				_challenge_fixture(),
			),
		)


def test_build_comparison_dataset_rejects_mixed_moose_artifacts(
	tmp_path: Path,
) -> None:
	raw_summaries = []
	for seed in range(5):
		payload = _raw_fixture(seed)
		if seed == 2:
			payload["toolchain"]["moose"]["artifact_sha256"] = "x" * 64
		raw_summaries.append(
			(seed, _write_json(tmp_path / f"raw-{seed}.json", payload)),
		)

	with pytest.raises(ValueError, match="same MOOSE artifact"):
		build_comparison_dataset(
			paired_results_file=_write_json(
				tmp_path / "paired.json",
				_paired_fixture(),
			),
			raw_moose_summaries=tuple(raw_summaries),
			instance_reference_summary_file=_write_json(
				tmp_path / "instances.json",
				_instance_fixture(),
			),
			direct_temporal_summary_file=_write_json(
				tmp_path / "direct.json",
				_direct_fixture(),
			),
			challenge_summary_file=_write_json(
				tmp_path / "challenge.json",
				_challenge_fixture(),
			),
		)


def test_build_comparison_dataset_rejects_wrong_direct_temporal_benchmark(
	tmp_path: Path,
) -> None:
	direct = _direct_fixture()
	direct["benchmark_sha256"] = "wrong"

	with pytest.raises(ValueError, match="direct temporal benchmark hash"):
		build_comparison_dataset(
			paired_results_file=_write_json(
				tmp_path / "paired.json",
				_paired_fixture(),
			),
			raw_moose_summaries=tuple(
				(seed, _write_json(tmp_path / f"raw-{seed}.json", _raw_fixture(seed)))
				for seed in range(5)
			),
			instance_reference_summary_file=_write_json(
				tmp_path / "instances.json",
				_instance_fixture(),
			),
			direct_temporal_summary_file=_write_json(
				tmp_path / "direct.json",
				direct,
			),
			challenge_summary_file=_write_json(
				tmp_path / "challenge.json",
				_challenge_fixture(),
			),
		)


def test_build_comparison_dataset_rejects_mislabeled_raw_moose_seed(
	tmp_path: Path,
) -> None:
	raw_summaries = []
	for seed in range(5):
		payload = _raw_fixture(seed)
		if seed == 3:
			payload["model_batch_manifest"]["settings"]["random_seed"] = 4
		raw_summaries.append(
			(seed, _write_json(tmp_path / f"raw-{seed}.json", payload)),
		)

	with pytest.raises(ValueError, match="Raw MOOSE seed 3.*training seed"):
		build_comparison_dataset(
			paired_results_file=_write_json(
				tmp_path / "paired.json",
				_paired_fixture(),
			),
			raw_moose_summaries=tuple(raw_summaries),
			instance_reference_summary_file=_write_json(
				tmp_path / "instances.json",
				_instance_fixture(),
			),
			direct_temporal_summary_file=_write_json(
				tmp_path / "direct.json",
				_direct_fixture(),
			),
			challenge_summary_file=_write_json(
				tmp_path / "challenge.json",
				_challenge_fixture(),
			),
		)


def test_build_comparison_dataset_rejects_raw_moose_from_different_seed_batch(
	tmp_path: Path,
) -> None:
	raw_summaries = []
	for seed in range(5):
		payload = _raw_fixture(seed)
		if seed == 2:
			payload["model_batch_manifest"]["sha256"] = "f" * 64
		raw_summaries.append(
			(seed, _write_json(tmp_path / f"raw-{seed}.json", payload)),
		)

	with pytest.raises(ValueError, match="Raw MOOSE seed 2.*paired model batch"):
		build_comparison_dataset(
			paired_results_file=_write_json(
				tmp_path / "paired.json",
				_paired_fixture(),
			),
			raw_moose_summaries=tuple(raw_summaries),
			instance_reference_summary_file=_write_json(
				tmp_path / "instances.json",
				_instance_fixture(),
			),
			direct_temporal_summary_file=_write_json(
				tmp_path / "direct.json",
				_direct_fixture(),
			),
			challenge_summary_file=_write_json(
				tmp_path / "challenge.json",
				_challenge_fixture(),
			),
		)


def test_build_comparison_dataset_rejects_changed_raw_moose_artifacts(
	tmp_path: Path,
) -> None:
	raw_summaries = []
	for seed in range(5):
		payload = _raw_fixture(seed)
		if seed == 2:
			payload["model_batch_manifest"]["artifact_sha256"] = "f" * 64
		raw_summaries.append(
			(seed, _write_json(tmp_path / f"raw-{seed}.json", payload)),
		)

	with pytest.raises(ValueError, match="Raw MOOSE seed 2.*evidence artifacts"):
		build_comparison_dataset(
			paired_results_file=_write_json(
				tmp_path / "paired.json",
				_paired_fixture(),
			),
			raw_moose_summaries=tuple(raw_summaries),
			instance_reference_summary_file=_write_json(
				tmp_path / "instances.json",
				_instance_fixture(),
			),
			direct_temporal_summary_file=_write_json(
				tmp_path / "direct.json",
				_direct_fixture(),
			),
			challenge_summary_file=_write_json(
				tmp_path / "challenge.json",
				_challenge_fixture(),
			),
		)


def test_build_comparison_dataset_rejects_duplicate_temporal_sample_ids(
	tmp_path: Path,
) -> None:
	paired = _paired_fixture()
	for run in paired["temporal_runs"]:
		run["results"].append(dict(run["results"][0]))

	with pytest.raises(ValueError, match="duplicate temporal result sample"):
		build_comparison_dataset(
			paired_results_file=_write_json(tmp_path / "paired.json", paired),
			raw_moose_summaries=tuple(
				(seed, _write_json(tmp_path / f"raw-{seed}.json", _raw_fixture(seed)))
				for seed in range(5)
			),
			instance_reference_summary_file=_write_json(
				tmp_path / "instances.json",
				_instance_fixture(),
			),
			direct_temporal_summary_file=_write_json(
				tmp_path / "direct.json",
				_direct_fixture(),
			),
			challenge_summary_file=_write_json(
				tmp_path / "challenge.json",
				_challenge_fixture(),
			),
		)


def test_build_comparison_dataset_rejects_duplicate_challenge_cases(
	tmp_path: Path,
) -> None:
	challenge = _challenge_fixture()
	challenge["records"][-1] = dict(challenge["records"][0])

	with pytest.raises(ValueError, match="challenge matrix.*unique registered cases"):
		build_comparison_dataset(
			paired_results_file=_write_json(
				tmp_path / "paired.json",
				_paired_fixture(),
			),
			raw_moose_summaries=tuple(
				(seed, _write_json(tmp_path / f"raw-{seed}.json", _raw_fixture(seed)))
				for seed in range(5)
			),
			instance_reference_summary_file=_write_json(
				tmp_path / "instances.json",
				_instance_fixture(),
			),
			direct_temporal_summary_file=_write_json(
				tmp_path / "direct.json",
				_direct_fixture(),
			),
			challenge_summary_file=_write_json(
				tmp_path / "challenge.json",
				challenge,
			),
		)

def test_build_comparison_dataset_rejects_shared_atomic_case_omission(
	tmp_path: Path,
) -> None:
	payload = _paired_fixture()
	for run in payload["atomic_runs"]:
		run["summary"]["validations"] = run["summary"]["validations"][:1]
	paired = _write_json(tmp_path / "paired.json", payload)

	with pytest.raises(ValueError, match="registered achievement case set"):
		build_comparison_dataset(
			paired_results_file=paired,
			raw_moose_summaries=tuple(
				(seed, _write_json(tmp_path / f"raw-{seed}.json", _raw_fixture(seed)))
				for seed in range(5)
			),
			instance_reference_summary_file=_write_json(
				tmp_path / "instances.json",
				_instance_fixture(),
			),
			direct_temporal_summary_file=_write_json(
				tmp_path / "direct.json",
				_direct_fixture(),
			),
			challenge_summary_file=_write_json(
				tmp_path / "challenge.json",
				_challenge_fixture(),
			),
		)


def test_build_comparison_dataset_rejects_shared_temporal_case_omission(
	tmp_path: Path,
) -> None:
	payload = _paired_fixture()
	for run in payload["temporal_runs"]:
		run["results"] = run["results"][:1]
	paired = _write_json(tmp_path / "paired.json", payload)

	with pytest.raises(ValueError, match="registered temporal case set"):
		build_comparison_dataset(
			paired_results_file=paired,
			raw_moose_summaries=tuple(
				(seed, _write_json(tmp_path / f"raw-{seed}.json", _raw_fixture(seed)))
				for seed in range(5)
			),
			instance_reference_summary_file=_write_json(
				tmp_path / "instances.json",
				_instance_fixture(),
			),
			direct_temporal_summary_file=_write_json(
				tmp_path / "direct.json",
				_direct_fixture(),
			),
			challenge_summary_file=_write_json(
				tmp_path / "challenge.json",
				_challenge_fixture(),
			),
		)


def test_build_comparison_dataset_rejects_raw_moose_case_omission(
	tmp_path: Path,
) -> None:
	raw_summaries = []
	for seed in range(5):
		payload = _raw_fixture(seed)
		payload["results"] = payload["results"][:1]
		raw_summaries.append(
			(seed, _write_json(tmp_path / f"raw-{seed}.json", payload)),
		)

	with pytest.raises(ValueError, match="Raw MOOSE seed 0 case set"):
		build_comparison_dataset(
			paired_results_file=_write_json(
				tmp_path / "paired.json",
				_paired_fixture(),
			),
			raw_moose_summaries=tuple(raw_summaries),
			instance_reference_summary_file=_write_json(
				tmp_path / "instances.json",
				_instance_fixture(),
			),
			direct_temporal_summary_file=_write_json(
				tmp_path / "direct.json",
				_direct_fixture(),
			),
			challenge_summary_file=_write_json(
				tmp_path / "challenge.json",
				_challenge_fixture(),
			),
		)


def test_build_comparison_dataset_rejects_instance_reference_case_omission(
	tmp_path: Path,
) -> None:
	instance = _instance_fixture()
	instance["results"] = instance["results"][:1]

	with pytest.raises(ValueError, match="MRP\\+HJ case set"):
		build_comparison_dataset(
			paired_results_file=_write_json(
				tmp_path / "paired.json",
				_paired_fixture(),
			),
			raw_moose_summaries=tuple(
				(seed, _write_json(tmp_path / f"raw-{seed}.json", _raw_fixture(seed)))
				for seed in range(5)
			),
			instance_reference_summary_file=_write_json(
				tmp_path / "instances.json",
				instance,
			),
			direct_temporal_summary_file=_write_json(
				tmp_path / "direct.json",
				_direct_fixture(),
			),
			challenge_summary_file=_write_json(
				tmp_path / "challenge.json",
				_challenge_fixture(),
			),
		)


def test_build_comparison_dataset_rejects_direct_temporal_case_omission(
	tmp_path: Path,
) -> None:
	direct = _direct_fixture()
	direct["results"] = direct["results"][:1]
	direct["selected_case_count"] = 1

	with pytest.raises(ValueError, match="direct temporal case set"):
		build_comparison_dataset(
			paired_results_file=_write_json(
				tmp_path / "paired.json",
				_paired_fixture(),
			),
			raw_moose_summaries=tuple(
				(seed, _write_json(tmp_path / f"raw-{seed}.json", _raw_fixture(seed)))
				for seed in range(5)
			),
			instance_reference_summary_file=_write_json(
				tmp_path / "instances.json",
				_instance_fixture(),
			),
			direct_temporal_summary_file=_write_json(
				tmp_path / "direct.json",
				direct,
			),
			challenge_summary_file=_write_json(
				tmp_path / "challenge.json",
				_challenge_fixture(),
			),
		)

def test_comparison_tables_use_short_descriptive_headers(tmp_path: Path) -> None:
	result = build_comparison_dataset(
		paired_results_file=_write_json(tmp_path / "paired.json", _paired_fixture()),
		raw_moose_summaries=tuple(
			(seed, _write_json(tmp_path / f"raw-{seed}.json", _raw_fixture(seed)))
			for seed in range(5)
		),
		instance_reference_summary_file=_write_json(
			tmp_path / "instances.json",
			_instance_fixture(),
		),
		direct_temporal_summary_file=_write_json(
			tmp_path / "direct.json",
			_direct_fixture(),
		),
		challenge_summary_file=_write_json(
			tmp_path / "challenge.json",
			_challenge_fixture(),
		),
	)

	atomic = render_atomic_table(result)
	temporal = render_temporal_table(result)
	external = render_external_table(result)
	combined = atomic + temporal + external

	assert "Method & Compiled & Targets & Valid & Branches & KiB & Compile s" in atomic
	assert "Method & Built & Valid & PAR-2 s & Actions & Plans & Fan-out" in temporal
	assert "Method & Scope & Valid & Unsupported & PAR-2 s" in external
	assert "Evidence Only" in atomic
	assert "Certified Balanced" in temporal
	assert "FOND4LTLf + LAMA" in external
	assert "C0" not in combined
	assert "T0" not in combined
	for table in (atomic, temporal, external):
		assert "\\begin{table*}[htbp]" in table
		assert "\\small" in table
		assert "\\footnotesize" not in table
		assert table.index("\\caption{") > table.index("\\end{tabular}")


def _paired_fixture() -> dict[str, object]:
	atomic_runs = []
	for seed in range(5):
		for index, (variant, method) in enumerate(ATOMIC_VARIANTS, start=1):
			validations = [
				_validation("p1", valid=True, actions=index),
				_validation("p2", valid=variant == "full", actions=index + 1),
			]
			atomic_runs.append(
				{
					"seed": seed,
					"variant": variant,
					"method": method,
					"domains": {
						"toy": {
							"compile_success": True,
							"compile_seconds": float(index),
							"readable_policy_sha256": f"raw-{seed}",
							"evidence_program_fingerprint": f"normalized-{seed}",
							"library_metrics": {
								"covered_target_count": 1 if index == 1 else 2,
								"producible_target_count": 2,
								"selected_branch_count": index,
								"context_literal_count": index * 2,
								"body_step_count": index * 3,
								"asl_bytes": index * 1024,
							},
						},
					},
					"summary": {
						"validations": validations,
						"source_revision": _clean_revision(),
						"settings": {
							"num_workers": 6,
							"timeout_seconds": 1800,
							"plan_verifier_timeout_seconds": 1800,
							"jason_java_stack_size": "64m",
						},
					},
				},
			)
	temporal_runs = []
	for index, (variant, method) in enumerate(TEMPORAL_VARIANTS, start=1):
		results = [
			_temporal_result("s1", valid=True, actions=index),
			_temporal_result("s2", valid=index >= 3, actions=index + 1),
		]
		temporal_runs.append(
			{
				"variant": variant,
				"method": method,
				"benchmark_sha256": BENCHMARK_HASH,
				"atomic_library_inputs": {
					"toy": {
						"plan_library_json_sha256": "json",
						"plan_library_asl_sha256": "asl",
					},
				},
				"source_revision": _clean_revision(),
				"parameters": {
					"num_workers": 6,
					"jason_timeout_seconds": 1800,
					"plan_verifier_timeout_seconds": 1800,
					"jason_java_stack_size": "64m",
				},
				"results": results,
			},
		)
	return {
		"success": True,
		"infrastructure_complete": True,
		"paired_inputs_verified": True,
		"source_revision": _clean_revision(),
		"domains": ["toy"],
		"registered_seeds": [0, 1, 2, 3, 4],
		"paper_matrix_complete": True,
		"seed_batch_manifests": {
			str(seed): {
				"sha256": str(seed) * 64,
				"artifact_sha256": (str(seed) or "0") * 64,
				"settings": {
					"random_seed": seed,
					"num_workers": 1,
					"num_permutations": 3,
					"goal_max_size": 1,
					"train_timeout_seconds": 43200,
					"max_rss_gb": 16.0,
				},
			}
			for seed in range(5)
		},
		"num_workers": 6,
		"timeout_seconds": 1800,
		"jason_java_stack_size": "64m",
		"case_contract": {
			"achievement": _case_set_contract(("toy:p1.pddl", "toy:p2.pddl")),
			"temporal": {
				**_case_set_contract(("s1", "s2")),
				"benchmark_sha256": BENCHMARK_HASH,
			},
			"external": {
				"raw_moose": _case_set_contract(("toy:p1.pddl", "toy:p2.pddl")),
				"lama": _case_set_contract(("toy:p1.pddl",)),
				"enhsp_hmrphj": _case_set_contract(("toy:n1.pddl",)),
			},
		},
		"atomic_pairing": {"paired": True},
		"temporal_pairing": {"paired": True},
		"atomic_runs": atomic_runs,
		"temporal_runs": temporal_runs,
	}


def _validation(problem: str, *, valid: bool, actions: int) -> dict[str, object]:
	return {
		"domain": "toy",
		"problem_file": f"/test/{problem}.pddl",
		"success": valid,
		"plan_verifier_success": valid,
		"status": "success" if valid else "failed",
		"duration_seconds": 1.0 if valid else 1800.0,
		"action_count": actions,
	}


def _temporal_result(sample: str, *, valid: bool, actions: int) -> dict[str, object]:
	return {
		"sample_id": sample,
		"status": "success" if valid else "jason_failed",
		"success": valid,
		"jason_status": "success" if valid else "failed",
		"duration_seconds": 2.0 if valid else 1800.0,
		"action_count": actions,
		"controller_plan_count": 3,
		"max_trigger_fanout": 2,
		"append_seconds": 0.1,
		"execution_validation": {
			"val_attempted": valid,
			"val_success": valid,
			"gold_accepted": valid,
			"prediction_accepted": valid,
		},
	}


def _raw_fixture(seed: int) -> dict[str, object]:
	return {
		"success": True,
		"source_revision": _clean_revision(),
		"variants": ["raw_moose"],
		"parameters": _external_parameters(),
		"toolchain": _external_toolchain(),
		"model_batch_manifest": {
			"sha256": str(seed) * 64,
			"artifact_sha256": (str(seed) or "0") * 64,
			"timestamp_id": f"seed-{seed}",
			"settings": {
				"random_seed": seed,
				"num_workers": 1,
				"num_permutations": 3,
				"goal_max_size": 1,
				"train_timeout_seconds": 43200,
				"max_rss_gb": 16.0,
			},
		},
		"results": [
			_external_result("Raw MOOSE", "p1", valid=True),
			_external_result("Raw MOOSE", "p2", valid=False),
		],
		"seed": seed,
	}


def _instance_fixture() -> dict[str, object]:
	return {
		"success": True,
		"source_revision": _clean_revision(),
		"variants": ["lama", "enhsp_hmrphj"],
		"parameters": _external_parameters(),
		"toolchain": _external_toolchain(),
		"results": [
			_external_result("LAMA", "p1", valid=True),
			_external_result("MRP+HJ", "n1", valid=True),
		],
	}


def _external_result(method: str, problem: str, *, valid: bool) -> dict[str, object]:
	return {
		"method": method,
		"domain": "toy",
		"problem_file": f"/test/{problem}.pddl",
		"status": "valid" if valid else "timeout",
		"plan_verifier_success": valid,
		"elapsed_seconds": 1.0 if valid else 1800.0,
		"action_count": 1 if valid else None,
	}


def _direct_fixture() -> dict[str, object]:
	return {
		"success": True,
		"source_revision": _clean_revision(),
		"benchmark_sha256": BENCHMARK_HASH,
		"parameters": {
			"num_workers": 6,
			"timeout_seconds_total_compile_and_plan": 1800,
			"max_rss_gb": 8.0,
			"plan_verifier_timeout_seconds": 1800,
		},
		"toolchain": {
			"fond4ltlf": {
				"git_revision": FOND4LTLF_REVISION,
				"release": "v0.0.4",
				"executable_sha256": "f" * 64,
			},
			"mona": {"version": "1.4-18", "executable_sha256": "n" * 64},
			"lama": {"moose_artifact_sha256": "m" * 64},
		},
		"selected_case_count": 2,
		"results": [
			{
				"sample_id": "s1",
				"status": "success",
				"supported": True,
				"success": True,
				"elapsed_seconds": 2.0,
				"action_count": 1,
				"execution_validation": {
					"val_success": True,
					"gold_accepted": True,
					"prediction_accepted": True,
				},
			},
			{
				"sample_id": "s2",
				"status": "unsupported_numeric_pddl",
				"supported": False,
				"success": False,
			},
		],
	}


def _challenge_fixture() -> dict[str, object]:
	return {
		"success": True,
		"source_revision": _clean_revision(),
		"case_count": 13,
		"success_count": 13,
		"records": [
			{"node_id": case.node_id, "success": True}
			for case in (*CHALLENGE_CASES, *METAMORPHIC_CASES)
		],
	}


def _clean_revision() -> dict[str, object]:
	return {
		"available": True,
		"commit": "0123456789abcdef",
		"tracked_changes": False,
		"untracked_files": False,
	}


def _external_parameters() -> dict[str, object]:
	return {
		"num_workers": 6,
		"timeout_seconds": 1800,
		"max_rss_gb": 8.0,
		"plan_verifier_timeout_seconds": 1800,
	}


def _external_toolchain() -> dict[str, object]:
	return {
		"moose": {
			"artifact_sha256": "m" * 64,
			"docker_image": "moose-exact-ubuntu22:local",
			"docker_image_id": "sha256:" + "d" * 64,
		},
		"enhsp": {
			"git_revision": ENHSP_REVISION,
			"jar_sha256": "e" * 64,
			"configuration": "sat-hmrphj",
		},
	}


def _case_set_contract(case_ids: tuple[str, ...]) -> dict[str, object]:
	canonical = json.dumps(sorted(case_ids), separators=(",", ":")).encode("utf-8")
	return {
		"count": len(case_ids),
		"sha256": hashlib.sha256(canonical).hexdigest(),
	}


def _write_json(path: Path, payload: dict[str, object]) -> Path:
	path.write_text(json.dumps(payload), encoding="utf-8")
	return path
