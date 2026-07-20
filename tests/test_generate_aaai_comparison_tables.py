from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

from scripts.generate_aaai_comparison_tables import build_comparison_dataset
from scripts.generate_aaai_comparison_tables import build_paired_ablation_dataset
from scripts.generate_aaai_comparison_tables import child_revision_contract_sha256
from scripts.generate_aaai_comparison_tables import render_atomic_table
from scripts.generate_aaai_comparison_tables import render_comparison_macros
from scripts.generate_aaai_comparison_tables import render_external_table
from scripts.generate_aaai_comparison_tables import render_temporal_table
from scripts.run_certificate_challenge_matrix import CHALLENGE_CASES
from scripts.run_certificate_challenge_matrix import METAMORPHIC_CASES


ATOMIC_VARIANTS = (
	("validated_evidence_adapter", "Evidence Only"),
	("action_only_closure", "Direct Producers"),
	("maximal_certified_program", "Maximum Feasible"),
	("full", "Full GP2PL"),
)
TEMPORAL_VARIANTS = (
	("dfa_aware_unprotected", "Unprotected Serialization"),
	("certified_flat", "Certified Flat"),
	("certified_balanced", "Certified Balanced"),
	("completion_boundary_monitor", "Module-Return Monitor"),
)
BENCHMARK_HASH = "a" * 64
ENHSP_REVISION = "537bed55a60d9456975c56afbadd50fc8acb1dc9"
FOND4LTLF_REVISION = "011d9d9a5bfd6406d2c358faf8f63167f6c839bb"


def test_registered_published_moose_reference_matches_arxiv_v1_table_four() -> None:
	project_root = Path(__file__).resolve().parents[1]
	reference_file = (
		project_root
		/ "paper_artifacts/gp2pl_evaluation/v1/moose_published_reference.json"
	)
	payload = json.loads(
		reference_file.read_text(encoding="utf-8"),
	)

	assert payload["source"]["arxiv_version"] == "2511.11095v1"
	assert payload["source"]["table"] == "Table 4"
	assert payload["published_results"]["seed_count"] == 5
	assert payload["published_results"]["case_count_per_seed"] == 1080
	assert payload["published_results"]["mean_solved_count"] == 1079.6
	assert payload["published_results"]["runtime_comparison_allowed"] is False
	assert {
		row["domain"]: row["mean_solved_count"]
		for row in payload["published_results"]["domains"]
	} == {
		"barman": 90.0,
		"ferry": 90.0,
		"gripper": 90.0,
		"logistics": 89.6,
		"miconic": 90.0,
		"rovers": 90.0,
		"satellite": 90.0,
		"transport": 90.0,
		"numeric-ferry": 90.0,
		"numeric-miconic": 90.0,
		"numeric-minecraft": 90.0,
		"numeric-transport": 90.0,
	}
	assert payload["scope_contracts"]["original_moose"]["case_contract"] == {
		"count": 1080,
		"sha256": "b99b12be1bcbe05983b0727dea0517a671530a55c686068e12908bb12eefb8f1",
	}
	assert payload["scope_contracts"]["gp2pl_extension"]["case_contract"] == {
		"count": 148,
		"sha256": "ae3ccea2e2f30093ff13fca34ba31451087fdcb78ffab18fc7ddd473ebb8ab5d",
	}
	assert payload["scope_contracts"]["selected_union"]["case_contract"] == {
		"count": 1228,
		"sha256": "3b3d38e19e5e885c3ad15658baf77a26a1aad6cc8a369dfc1284c653a4e385ec",
	}
	manifest = json.loads(
		(reference_file.parent / "manifest.json").read_text(encoding="utf-8"),
	)
	assert manifest["files"][reference_file.name] == hashlib.sha256(
		reference_file.read_bytes(),
	).hexdigest()


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
	assert "--published-moose-reference" in completed.stdout
	assert "--raw-moose-extension-summary" in completed.stdout
	assert "--raw-moose-summary" not in completed.stdout


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


def test_build_comparison_dataset_separates_published_moose_from_local_extension(
	tmp_path: Path,
) -> None:
	result = build_comparison_dataset(
		paired_results_file=_write_json(
			tmp_path / "paired.json",
			_paired_fixture(raw_moose_case_ids=_registered_raw_moose_case_ids()),
		),
		published_moose_reference_file=_write_json(
			tmp_path / "published-moose.json",
			_published_moose_fixture(),
		),
		raw_moose_extension_summaries=tuple(
			(
				seed,
				_write_json(
					tmp_path / f"extension-{seed}.json",
					_raw_extension_fixture(seed),
				),
			)
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

	moose_rows = [
		row for row in result["external"] if "MOOSE" in str(row["method"])
	]
	assert result["schema_version"] == 2
	assert len(result["provenance"]["raw_moose_extension_summaries"]) == 5
	assert "raw_moose_summaries" not in result["provenance"]
	assert moose_rows == [
		{
			"method": "MOOSE",
			"source": "Reported",
			"scope": "Original MOOSE domains, five seeds",
			"case_count": 1080,
			"supported_case_count": 1080,
			"unsupported_case_count": 0,
			"valid_trace_count": 1079.6,
			"seed_count": 5,
			"par2_seconds": None,
		},
		{
			"method": "Raw MOOSE extension",
			"source": "Measured",
			"scope": "Added domains, five seeds",
			"case_count": 148,
			"supported_case_count": 148,
			"unsupported_case_count": 0,
			"valid_trace_count": 148.0,
			"seed_count": 5,
			"coverage_sample_sd": 0.0,
			"par2_seconds": None,
		},
	]


def test_build_paired_ablation_dataset_requires_only_paired_and_challenge_inputs(
	tmp_path: Path,
) -> None:
	paired = _paired_fixture()
	result = build_paired_ablation_dataset(
		paired_results_file=_write_json(tmp_path / "paired.json", paired),
		challenge_summary_file=_write_json(
			tmp_path / "challenge.json",
			_challenge_fixture(),
		),
	)

	assert result["artifact_kind"] == "gp2pl_paired_ablation_results"
	assert [row["method"] for row in result["atomic"]] == [
		name for _variant, name in ATOMIC_VARIANTS
	]
	assert [row["method"] for row in result["temporal"]] == [
		name for _variant, name in TEMPORAL_VARIANTS
	]
	assert result["challenges"] == {"case_count": 13, "success_count": 13}
	assert len(result["atomic_records"]) == 40
	assert len(result["temporal_records"]) == 8
	assert len(result["atomic_seed_results"]) == 20
	assert len(result["temporal_breakdowns"]) == 4
	assert "/test/" not in json.dumps(result["atomic_records"])
	assert len(result["paired_contrasts"]["atomic"]) == 3
	assert len(result["paired_contrasts"]["temporal"]) == 3
	flat_to_balanced = result["paired_contrasts"]["temporal"][1]
	assert flat_to_balanced["left_only_valid_count"] == 0
	assert flat_to_balanced["right_only_valid_count"] == 1
	assert flat_to_balanced["exact_two_sided_p"] == 1.0
	assert result["provenance"]["paired_results_sha256"] == hashlib.sha256(
		(tmp_path / "paired.json").read_bytes(),
	).hexdigest()
	macros = render_comparison_macros(result)
	assert all(
		macro_name.isalpha()
		for macro_name in re.findall(r"\\newcommand\{\\([^}]+)\}", macros)
	)
	assert r"\newcommand{\AtomicEvidenceOnlyValidCount}{5}" in macros
	assert r"\newcommand{\AtomicAblationCaseCount}{10}" in macros
	assert r"\newcommand{\TemporalCertifiedBalancedValidCount}{2}" in macros
	assert r"\newcommand{\TemporalAblationCaseCount}{2}" in macros
	assert r"\newcommand{\TemporalCertifiedBalancedFanout}{2}" in macros
	assert r"\newcommand{\AtomicDirectToMaximumValidGain}{0}" in macros
	assert r"\newcommand{\TemporalFlatToBalancedValidGain}{1}" in macros
	assert r"\newcommand{\TemporalFlatToBalancedExactP}{1}" in macros


def test_build_comparison_dataset_rejects_unregistered_published_moose_source(
	tmp_path: Path,
) -> None:
	published = _published_moose_fixture()
	published["source"]["arxiv_version"] = "2511.11095v2"

	with pytest.raises(ValueError, match="published MOOSE.*2511.11095v1.*Table 4"):
		build_comparison_dataset(
			paired_results_file=_write_json(
				tmp_path / "paired.json",
				_paired_fixture(raw_moose_case_ids=_registered_raw_moose_case_ids()),
			),
			published_moose_reference_file=_write_json(
				tmp_path / "published-moose.json",
				published,
			),
			raw_moose_extension_summaries=tuple(
				(
					seed,
					_write_json(
						tmp_path / f"extension-{seed}.json",
						_raw_extension_fixture(seed),
					),
				)
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


def test_build_comparison_dataset_rejects_changed_published_moose_coverage(
	tmp_path: Path,
) -> None:
	published = _published_moose_fixture()
	published["published_results"]["domains"][0]["mean_solved_count"] = 89.0
	published["published_results"]["mean_solved_count"] = 1078.6

	with pytest.raises(ValueError, match="published MOOSE.*Table 4 coverage"):
		build_comparison_dataset(
			paired_results_file=_write_json(
				tmp_path / "paired.json",
				_paired_fixture(raw_moose_case_ids=_registered_raw_moose_case_ids()),
			),
			published_moose_reference_file=_write_json(
				tmp_path / "published-moose.json",
				published,
			),
			raw_moose_extension_summaries=tuple(
				(
					seed,
					_write_json(
						tmp_path / f"extension-{seed}.json",
						_raw_extension_fixture(seed),
					),
				)
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


def test_build_comparison_dataset_requires_twenty_workers_for_remote_references(
	tmp_path: Path,
) -> None:
	instance_payload = _instance_fixture()
	instance_payload["parameters"]["num_workers"] = 6

	with pytest.raises(ValueError, match="instance references.*20 workers"):
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
				instance_payload,
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


def test_build_comparison_dataset_validates_serial_infrastructure_repair(
	tmp_path: Path,
) -> None:
	instance = _instance_fixture()
	instance["infrastructure_repair"] = _repair_fixture(
		case_ids=("lama:toy:p1.pddl",),
	)
	instance["results"][0]["variant"] = "lama"
	instance["results"][0]["infrastructure_retry"] = {
		"primary_status": "runner_error",
	}

	result = build_comparison_dataset(
		paired_results_file=_write_json(tmp_path / "paired.json", _paired_fixture()),
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

	assert {row["method"] for row in result["external"]} >= {"LAMA", "MRP+HJ"}


def test_build_comparison_dataset_rejects_nonserial_infrastructure_repair(
	tmp_path: Path,
) -> None:
	instance = _instance_fixture()
	instance["infrastructure_repair"] = _repair_fixture(
		case_ids=("lama:toy:p1.pddl",),
	)
	instance["infrastructure_repair"]["retry_num_workers"] = 2
	instance["results"][0]["variant"] = "lama"
	instance["results"][0]["infrastructure_retry"] = {
		"primary_status": "runner_error",
	}

	with pytest.raises(ValueError, match="serial retry worker"):
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


def test_build_comparison_dataset_validates_direct_launcher_path_rewrite(
	tmp_path: Path,
) -> None:
	direct = _direct_fixture()
	direct["infrastructure_repair"] = _repair_fixture(case_ids=("s1",))
	direct["infrastructure_repair"]["toolchain_verification"] = (
		_direct_toolchain_repair_verification()
	)
	direct["results"][0]["infrastructure_retry"] = {
		"primary_status": "planner_runner_error",
	}

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
			direct,
		),
		challenge_summary_file=_write_json(
			tmp_path / "challenge.json",
			_challenge_fixture(),
		),
	)

	assert any(row["method"] == "FOND4LTLf + LAMA" for row in result["external"])


def test_build_comparison_dataset_rejects_unverified_direct_launcher_change(
	tmp_path: Path,
) -> None:
	direct = _direct_fixture()
	direct["infrastructure_repair"] = _repair_fixture(case_ids=("s1",))
	verification = _direct_toolchain_repair_verification()
	verification["path_embedded_launchers"]["mona"]["equivalence"] = "unverified"
	direct["infrastructure_repair"]["toolchain_verification"] = verification
	direct["results"][0]["infrastructure_retry"] = {
		"primary_status": "planner_runner_error",
	}

	with pytest.raises(ValueError, match="path-embedded launcher"):
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


def test_build_comparison_dataset_keeps_raw_moose_at_six_workers(
	tmp_path: Path,
) -> None:
	raw_summaries = []
	for seed in range(5):
		payload = _raw_fixture(seed)
		if seed == 2:
			payload["parameters"]["num_workers"] = 20
		raw_summaries.append(
			(seed, _write_json(tmp_path / f"raw-{seed}.json", payload)),
		)

	with pytest.raises(ValueError, match="Raw MOOSE seed 2.*6 workers"):
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


def test_build_comparison_dataset_accepts_hash_bound_method_source_equivalence(
	tmp_path: Path,
) -> None:
	paired = _paired_fixture()
	paired["atomic_runs"][0]["summary"]["source_revision"] = {
		"available": True,
		"commit": "fedcba9876543210",
		"tracked_changes": True,
		"untracked_files": False,
	}
	paired["method_source_equivalence"] = {
		"status": "confirmed",
		"basis": "experiment_owner_confirmed_no_method_code_changes",
		"child_revision_contract_sha256": child_revision_contract_sha256(paired),
	}

	result = build_comparison_dataset(
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

	assert result["atomic"]
	assert result["provenance"]["method_source_equivalence"] == paired[
		"method_source_equivalence"
	]


def test_build_comparison_dataset_rejects_stale_method_source_equivalence(
	tmp_path: Path,
) -> None:
	paired = _paired_fixture()
	paired["method_source_equivalence"] = {
		"status": "confirmed",
		"basis": "experiment_owner_confirmed_no_method_code_changes",
		"child_revision_contract_sha256": child_revision_contract_sha256(paired),
	}
	paired["temporal_runs"][0]["source_revision"]["commit"] = "fedcba9876543210"

	with pytest.raises(ValueError, match="does not cover child revisions"):
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
		paired_results_file=_write_json(
			tmp_path / "paired.json",
			_paired_fixture(raw_moose_case_ids=_registered_raw_moose_case_ids()),
		),
		published_moose_reference_file=_write_json(
			tmp_path / "published-moose.json",
			_published_moose_fixture(),
		),
		raw_moose_extension_summaries=tuple(
			(
				seed,
				_write_json(
					tmp_path / f"extension-{seed}.json",
					_raw_extension_fixture(seed),
				),
			)
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
	atomic_text = " ".join(atomic.split())

	assert "Method & Valid (\\%) & Branches & KiB" in atomic
	assert "Method & Valid & PAR-2 s & Plans & Fan-out" in temporal
	assert "Method & Source & Scope & Coverage & Unsupported & PAR-2 s" in external
	assert "MOOSE & Reported & Original MOOSE domains, five seeds" in external
	assert "1079.6/1080" in external
	assert "Raw MOOSE extension & Measured & Added domains, five seeds" in external
	assert "148 $\\pm$ 0/148" in external
	raw_extension_line = next(
		line for line in external.splitlines() if line.startswith("Raw MOOSE extension")
	)
	assert raw_extension_line.endswith("& 0 & -- \\\\")
	assert "Reported MOOSE coverage is copied from Table~4" in external
	assert "Evidence Only" in atomic
	assert "Certified Balanced" in temporal
	assert r"\resultbest{" in atomic
	assert r"\resultselected{Full GP2PL}" in atomic
	assert r"\resultbest{" in temporal
	assert r"\resultselected{Certified Balanced}" in temporal
	assert "Bold marks tied best coverage" in atomic_text
	assert "blue bold marks Full GP2PL" in atomic_text
	assert "Color is not used alone" in temporal
	assert "FOND4LTLf + LAMA" in external
	assert "C0" not in combined
	assert "T0" not in combined
	for table in (atomic, temporal):
		assert "\\begin{table}[htbp]" in table
		assert "\\small" in table
		assert "\\footnotesize" not in table
		assert table.index("\\caption{") > table.index("\\end{tabular}")
	assert "\\begin{table*}[htbp]" in external
	assert "\\small" in external
	assert "\\footnotesize" not in external
	assert external.index("\\caption{") > external.index("\\end{tabular}")


def _paired_fixture(
	*,
	raw_moose_case_ids: tuple[str, ...] = ("toy:p1.pddl", "toy:p2.pddl"),
) -> dict[str, object]:
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
				"raw_moose": _case_set_contract(raw_moose_case_ids),
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
		"parameters": _external_parameters(num_workers=6),
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


def _published_moose_fixture() -> dict[str, object]:
	project_root = Path(__file__).resolve().parents[1]
	return json.loads(
		(
			project_root
			/ "paper_artifacts/gp2pl_evaluation/v1/moose_published_reference.json"
		).read_text(encoding="utf-8"),
	)


def _raw_extension_fixture(seed: int) -> dict[str, object]:
	payload = _raw_fixture(seed)
	payload["results"] = [
		{
			**_external_result("Raw MOOSE", Path(case_id).stem, valid=True),
			"domain": case_id.partition(":")[0],
			"problem_file": f"/test/{case_id.partition(':')[2]}",
		}
		for case_id in _registered_raw_moose_extension_case_ids()
	]
	return payload


def _registered_raw_moose_case_ids() -> tuple[str, ...]:
	return _registered_domain_case_ids(
		(
			"barman",
			"ferry",
			"gripper",
			"logistics",
			"miconic",
			"rovers",
			"satellite",
			"transport",
			"numeric-ferry",
			"numeric-miconic",
			"numeric-minecraft",
			"numeric-transport",
			"blocksworld-clear",
			"blocksworld-on",
			"blocksworld-tower",
			"depots",
		),
	)


def _registered_raw_moose_extension_case_ids() -> tuple[str, ...]:
	return _registered_domain_case_ids(
		(
			"blocksworld-clear",
			"blocksworld-on",
			"blocksworld-tower",
			"depots",
		),
	)


def _registered_domain_case_ids(domains: tuple[str, ...]) -> tuple[str, ...]:
	project_root = Path(__file__).resolve().parents[1]
	return tuple(
		sorted(
			f"{domain}:{problem_file.name}"
			for domain in domains
			for problem_file in (project_root / "src/domains" / domain / "test").glob(
				"*.pddl",
			)
		),
	)


def _instance_fixture() -> dict[str, object]:
	return {
		"success": True,
		"source_revision": _clean_revision(),
		"variants": ["lama", "enhsp_hmrphj"],
		"parameters": _external_parameters(num_workers=20),
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
			"num_workers": 20,
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


def _repair_fixture(*, case_ids: tuple[str, ...]) -> dict[str, object]:
	encoded = json.dumps(sorted(case_ids), separators=(",", ":")).encode("utf-8")
	return {
		"strategy": "replace_exact_infrastructure_failures",
		"primary_summary_sha256": "a" * 64,
		"retry_summary_sha256": "b" * 64,
		"primary_source_revision": _clean_revision(),
		"retry_source_revision": {
			**_clean_revision(),
			"commit": "fedcba9876543210fedcba9876543210fedcba98",
		},
		"primary_num_workers": 20,
		"retry_num_workers": 1,
		"replaced_case_count": len(case_ids),
		"replaced_case_ids": list(case_ids),
		"replaced_case_set_sha256": hashlib.sha256(encoded).hexdigest(),
		"input_fingerprints_verified": True,
		"toolchain_verified": True,
		"resource_limits_verified": True,
		"hardware_equivalence_confirmed_by_experiment_owner": True,
		"runtime_measurement_excludes_queue_wait": True,
		"runtime_comparison_allowed": True,
	}


def _direct_toolchain_repair_verification() -> dict[str, object]:
	launcher = {
		"equivalence": "absolute_install_prefix_rewrite",
		"primary_sha256": "a" * 64,
		"retry_sha256": "b" * 64,
		"retry_file_sha256_verified": True,
		"replacement_count": 1,
	}
	return {
		"semantic_identity": "exact_pinned_revisions_and_versions",
		"semantic_identity_sha256": "c" * 64,
		"path_embedded_launchers": {
			"fond4ltlf": dict(launcher),
			"mona": dict(launcher),
		},
	}


def _external_parameters(*, num_workers: int) -> dict[str, object]:
	return {
		"num_workers": num_workers,
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
