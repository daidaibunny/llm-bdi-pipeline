from __future__ import annotations

import json
from pathlib import Path

from scripts.freeze_paired_ablation_results import write_paired_ablation_files
from scripts.generate_aaai_comparison_tables import render_comparison_macros


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = PROJECT_ROOT / "paper_artifacts/gp2pl_evaluation/v1"
RESULT_FILE = RELEASE_ROOT / "paired_ablation_results.json"


def test_registered_paired_ablation_is_complete_portable_and_manifested() -> None:
	result = json.loads(RESULT_FILE.read_text(encoding="utf-8"))

	assert result["artifact_kind"] == "gp2pl_paired_ablation_results"
	assert len(result["atomic_records"]) == 24560
	assert len(result["temporal_records"]) == 4912
	assert [row["valid_trace_count"] for row in result["atomic"]] == [
		5420,
		5419,
		6059,
		6059,
	]
	assert [row["valid_trace_count"] for row in result["temporal"]] == [
		1113,
		1228,
		1228,
		1212,
	]
	assert [row["maximum_trigger_fanout"] for row in result["temporal"]] == [
		3,
		3,
		2,
		2,
	]
	assert "/Users/" not in RESULT_FILE.read_text(encoding="utf-8")
	manifest = json.loads((RELEASE_ROOT / "manifest.json").read_text(encoding="utf-8"))
	assert manifest["paired_ablation_atomic_record_count"] == 24560
	assert manifest["paired_ablation_temporal_record_count"] == 4912
	macros = render_comparison_macros(result)
	assert r"\newcommand{\TemporalCrossSeedCount}{5}" in macros
	assert r"\newcommand{\TemporalCrossSeedEvaluationCount}{6,140}" in macros
	assert r"\newcommand{\TemporalCrossSeedValidCount}{6,140}" in macros
	assert r"\newcommand{\TemporalCrossSeedMeanParTwoSeconds}{5.36}" in macros
	assert r"\newcommand{\TemporalCrossSeedParTwoSDSeconds}{0.27}" in macros


def test_write_paired_ablation_files_updates_tables_macros_and_manifest(
	tmp_path: Path,
) -> None:
	release_root = tmp_path / "release"
	latex_root = tmp_path / "latex"
	release_root.mkdir()
	(release_root / "manifest.json").write_text(
		json.dumps({"files": {}}),
		encoding="utf-8",
	)
	result = {
		"artifact_kind": "gp2pl_paired_ablation_results",
		"atomic_joint_action_case_count": 1,
		"temporal_joint_action_case_count": 1,
		"challenges": {"case_count": 13, "success_count": 13},
		"atomic": [
			{
				"variant": "validated_evidence_adapter",
				"method": "Evidence Only",
				"compiled_count": 1,
				"compiled_total": 1,
				"covered_target_count": 1,
				"producible_target_count": 2,
				"valid_trace_count": 1,
				"test_count": 2,
				"mean_branch_count": 3.0,
				"sd_branch_count": 0.0,
				"mean_library_kib": 4.0,
				"sd_library_kib": 0.0,
				"mean_compile_seconds": 5.0,
				"sd_compile_seconds": 0.0,
			},
		],
		"temporal": [
			{
				"variant": "certified_balanced",
				"method": "Certified Balanced",
				"compiled_count": 2,
				"test_count": 2,
				"valid_trace_count": 2,
				"par2_seconds": 6.0,
				"median_joint_action_count": 1.0,
				"median_controller_plan_count": 7.0,
				"maximum_trigger_fanout": 2,
			},
		],
	}
	output_json = release_root / "paired_ablation_results.json"

	write_paired_ablation_files(
		result,
		output_json=output_json,
		latex_output_dir=latex_root,
		update_manifest=True,
	)

	assert output_json.is_file()
	assert (latex_root / "result_atomic_comparison_table.tex").is_file()
	assert (latex_root / "result_temporal_comparison_table.tex").is_file()
	assert (latex_root / "result_comparison_macros.tex").is_file()
	manifest = json.loads(
		(release_root / "manifest.json").read_text(encoding="utf-8"),
	)
	assert manifest["paired_ablation_atomic_record_count"] == 2
	assert manifest["paired_ablation_temporal_record_count"] == 2
	assert json.loads(output_json.read_text(encoding="utf-8")) == result
