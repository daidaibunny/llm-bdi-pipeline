from __future__ import annotations

import json
from pathlib import Path
import statistics
from typing import Any
from typing import Callable

import pytest
from PIL import Image
from PIL import ImageChops

from scripts.generate_aaai_figures import ATOMIC_VARIANTS
from scripts.generate_aaai_figures import BENCHMARK_GROUPS
from scripts.generate_aaai_figures import DOMAIN_ORDER
from scripts.generate_aaai_figures import FIGURE_HEIGHT_INCHES
from scripts.generate_aaai_figures import FIGURE_DPI
from scripts.generate_aaai_figures import FIGURE_WIDTH_INCHES
from scripts.generate_aaai_figures import PROJECT_ROOT
from scripts.generate_aaai_figures import TEMPORAL_VARIANTS
from scripts.generate_aaai_figures import build_figure_dataset
from scripts.generate_aaai_figures import build_five_seed_figure_dataset
from scripts.generate_aaai_figures import build_frozen_ablation_figure_dataset
from scripts.generate_aaai_figures import cumulative_solved_fraction
from scripts.generate_aaai_figures import generate_empirical_figure
from scripts.generate_aaai_figures import generate_five_seed_empirical_figure
from scripts.generate_aaai_figures import generate_frozen_ablation_figure
from scripts.generate_aaai_figures import _step_values_at


def test_build_figure_dataset_uses_paired_atomic_and_temporal_matrix() -> None:
	payload = _complete_paired_payload()

	dataset = build_figure_dataset(payload)

	first_domain = DOMAIN_ORDER[0]
	assert dataset["atomic_domain_coverage"][first_domain]["evidence_adapter"] == [
		50.0,
		50.0,
		50.0,
		50.0,
		50.0,
	]
	assert dataset["atomic_domain_coverage"][first_domain]["full"] == [
		100.0,
		100.0,
		100.0,
		100.0,
		100.0,
	]
	full_points = dataset["atomic_tradeoff"]["full"]
	assert len(full_points) == 5
	assert full_points[0]["selected_branch_count"] == 640
	assert full_points[0]["coverage_percent"] == 100.0
	assert dataset["temporal_curves"]["completion_boundary_monitor"][
		"final_percent"
	] == pytest.approx(100.0)


def test_build_frozen_ablation_figure_dataset_recomputes_paired_results() -> None:
	payload = _complete_frozen_ablation_payload()

	dataset = build_frozen_ablation_figure_dataset(payload)

	first_domain = DOMAIN_ORDER[0]
	assert dataset["atomic_domain_coverage"][first_domain]["evidence_adapter"] == [
		50.0,
		50.0,
		50.0,
		50.0,
		50.0,
	]
	assert dataset["atomic_domain_coverage"][first_domain]["full"] == [
		100.0,
		100.0,
		100.0,
		100.0,
		100.0,
	]
	assert dataset["atomic_tradeoff_summary"]["full"] == {
		"branch_mean": 160.0,
		"branch_sd": 4.0,
		"coverage_mean": 100.0,
		"coverage_sd": 0.0,
	}
	assert dataset["atomic_affected_domains"] == list(DOMAIN_ORDER)
	assert dataset["atomic_unchanged_domains"] == []
	assert dataset["atomic_focus_domain"] == "blocksworld-tower"
	assert dataset["atomic_focus_curves"]["validated_evidence_adapter"][
		"solved_count"
	] == 5
	assert dataset["atomic_focus_curves"]["full"]["solved_count"] == 10
	assert dataset["atomic_focus_curves"]["full"]["sample_count"] == 10
	assert dataset["temporal_curves"]["certified_balanced"][
		"final_percent"
	] == pytest.approx(100.0)
	assert dataset["atomic_case_count"] == 160
	assert dataset["temporal_case_count"] == 16


@pytest.mark.parametrize(
	("mutator", "message"),
	(
		(
			lambda payload: payload.update({"artifact_kind": "wrong"}),
			"artifact",
		),
		(
			lambda payload: payload["protocol"]["atomic_pairing"].update(
				{"paired": False},
			),
			"atomic pairing",
		),
		(
			lambda payload: payload["atomic_records"].pop(),
			"atomic record matrix",
		),
		(
			lambda payload: payload["temporal_records"][0].update(
				{"valid": True, "val_success": False},
			),
			"temporal validity",
		),
	),
)
def test_build_frozen_ablation_figure_dataset_rejects_unpaired_or_inconsistent_data(
	mutator: Callable[[dict[str, Any]], None],
	message: str,
) -> None:
	payload = _complete_frozen_ablation_payload()
	mutator(payload)

	with pytest.raises(ValueError, match=message):
		build_frozen_ablation_figure_dataset(payload)


def test_generate_frozen_ablation_figure_writes_600_dpi_png_and_outcome_metadata(
	tmp_path: Path,
) -> None:
	input_file = tmp_path / "paired_ablation_results.json"
	output_file = tmp_path / "fig3_evaluation.png"
	input_file.write_text(
		json.dumps(_complete_frozen_ablation_payload()),
		encoding="utf-8",
	)

	metadata = generate_frozen_ablation_figure(
		ablation_results_file=input_file,
		output_file=output_file,
	)

	with Image.open(output_file) as figure:
		assert figure.format == "PNG"
		assert figure.size == (4200, 1700)
		assert figure.info["dpi"] == pytest.approx((600.0, 600.0), abs=0.1)
		difference = ImageChops.difference(
			figure.convert("RGB"),
			Image.new("RGB", figure.size, "white"),
		).convert("L")
		content_bounds = difference.point(
			lambda value: 255 if value > 8 else 0,
		).getbbox()
		assert content_bounds is not None
		assert figure.height - content_bounds[3] <= 72
	assert output_file.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
	assert FIGURE_DPI == 600
	assert metadata["artifact_kind"] == "gp2pl_ablation_empirical_figure"
	assert metadata["atomic_seed_count"] == 5
	assert metadata["atomic_domain_count"] == 16
	assert metadata["atomic_case_count"] == 160
	assert metadata["temporal_case_count"] == 16
	assert metadata["pixel_width"] == 4200
	assert metadata["pixel_height"] == 1700
	assert metadata["dpi"] == 600
	assert metadata["manuscript_width_fraction"] == pytest.approx(2.0 / 3.0)
	assert metadata["effective_minimum_text_size_points"] >= 7.0
	assert metadata["color_mode"] == "colorblind-safe with redundant encodings"
	assert metadata["atomic_focus_domain"] == "blocksworld-tower"


def test_registered_figure_three_has_the_frozen_result_shape() -> None:
	figure_file = (
		PROJECT_ROOT
		/ "latex_code/aamas_method_paper/figures/fig3_evaluation.png"
	)
	metadata_file = figure_file.with_suffix(".metadata.json")
	metadata = json.loads(metadata_file.read_text(encoding="utf-8"))

	with Image.open(figure_file) as figure:
		assert figure.size == (4200, 1700)
		assert figure.info["dpi"] == pytest.approx((600.0, 600.0), abs=0.1)
	assert metadata["atomic_case_count"] == 6140
	assert metadata["temporal_case_count"] == 1228
	assert metadata["atomic_focus_domain"] == "blocksworld-tower"


def test_cumulative_solved_fraction_keeps_failures_in_denominator() -> None:
	x_values, y_values = cumulative_solved_fraction(
		(
			_temporal_result("s1", duration=1.0, success=True),
			_temporal_result("s2", duration=10.0, success=False),
			_temporal_result("s3", duration=100.0, success=True),
		),
		timeout_seconds=1800,
	)

	assert x_values[-1] == 1800.0
	assert y_values[-1] == pytest.approx(200.0 / 3.0)
	assert max(y_values) < 100.0


def test_step_values_at_uses_right_continuous_value_for_shared_checkpoints() -> None:
	values = _step_values_at(
		(0.1, 1.0, 1.0, 1800.0),
		(0.0, 25.0, 50.0, 50.0),
		(0.5, 1.0, 10.0, 1800.0),
	)

	assert values == (0.0, 50.0, 50.0, 50.0)


@pytest.mark.parametrize(
	("mutator", "message"),
	(
		(lambda payload: payload.update({"paired_inputs_verified": False}), "not paired"),
		(lambda payload: payload.update({"registered_seeds": [0, 1]}), "seeds"),
		(lambda payload: payload["atomic_runs"].pop(), "atomic matrix"),
		(lambda payload: payload["temporal_runs"].pop(), "temporal matrix"),
	),
)
def test_build_figure_dataset_rejects_incomplete_or_unpaired_inputs(
	mutator: Callable[[dict[str, Any]], None],
	message: str,
) -> None:
	payload = _complete_paired_payload()
	mutator(payload)

	with pytest.raises(ValueError, match=message):
		build_figure_dataset(payload)


def test_generate_empirical_figure_writes_vector_pdf_and_outcome_metadata(
	tmp_path: Path,
) -> None:
	input_file = tmp_path / "paired_results.json"
	output_file = tmp_path / "fig2_evaluation.pdf"
	input_file.write_text(
		json.dumps(_complete_paired_payload()),
		encoding="utf-8",
	)

	metadata = generate_empirical_figure(
		paired_results_file=input_file,
		output_file=output_file,
	)

	pdf_bytes = output_file.read_bytes()
	assert pdf_bytes.startswith(b"%PDF")
	assert FIGURE_WIDTH_INCHES == 7.0
	assert FIGURE_HEIGHT_INCHES == 4.25
	assert b"/MediaBox [ 0 0 504 306 ]" in pdf_bytes
	assert b"DejaVuSans" not in pdf_bytes
	assert b"Helvetica" in pdf_bytes
	assert metadata["artifact_kind"] == "gp2pl_empirical_figure"
	assert metadata["atomic_seed_count"] == 5
	assert metadata["atomic_domain_count"] == 16
	assert metadata["temporal_sample_count"] == 3
	assert metadata["figure_width_inches"] == 7.0
	assert metadata["figure_height_inches"] == 4.25
	assert metadata["font_family"] == "Helvetica"
	assert metadata["minimum_text_size_points"] == 9.0
	assert metadata["color_mode"] == "colorblind-safe with redundant encodings"
	assert output_file.with_suffix(".metadata.json").is_file()


def test_manuscript_uses_tables_in_main_and_moves_detailed_views_to_supplement() -> None:
	main_text = (PROJECT_ROOT / "latex_code/aamas_method_paper/main.tex").read_text()
	evaluation_text = (
		PROJECT_ROOT / "latex_code/aamas_method_paper/sections/evaluation.tex"
	).read_text()
	supplement_text = (
		PROJECT_ROOT
		/ "latex_code/aamas_method_paper/sections/technical_appendix_content.tex"
	).read_text()

	assert "\\gpplfigurethreepath" not in main_text
	assert "\\gpplfigurethreepath" not in evaluation_text
	assert "\\label{fig:evaluation-summary}" not in evaluation_text
	for table_input in ("\\input{sections/result_five_seed_atomic_table}",):
		assert table_input in evaluation_text
		assert table_input not in supplement_text
	assert "\\input{sections/result_temporal_summary_table}" not in evaluation_text
	for table_input in (
		"\\input{sections/result_five_seed_atomic_domain_table}",
		"\\input{sections/result_domain_table}",
		"\\input{sections/result_profile_table}",
		"\\input{sections/result_moose_reference_table}",
	):
		assert table_input not in evaluation_text
		assert table_input in supplement_text
	assert "\\clearpage" not in evaluation_text
	assert "supplementary diagnostic artifact" in supplement_text
	result_float_specs = {
		"result_five_seed_atomic_table.tex": "\\begin{table}[htbp]",
		"result_five_seed_atomic_domain_table.tex": "\\begin{table*}[htbp]",
		"result_profile_table.tex": "\\begin{table}[htbp]",
		"result_domain_table.tex": "\\begin{table}[htbp]",
	}
	for filename, expected_float in result_float_specs.items():
		float_text = (
			PROJECT_ROOT / "latex_code/aamas_method_paper/sections" / filename
		).read_text()
		assert expected_float in float_text
		assert "[H]" not in float_text


def test_generate_empirical_figure_fails_closed_with_diagnostic(
	tmp_path: Path,
) -> None:
	payload = _complete_paired_payload()
	payload["infrastructure_complete"] = False
	input_file = tmp_path / "paired_results.json"
	output_file = tmp_path / "fig2_evaluation.pdf"
	input_file.write_text(json.dumps(payload), encoding="utf-8")

	with pytest.raises(ValueError, match="infrastructure"):
		generate_empirical_figure(
			paired_results_file=input_file,
			output_file=output_file,
		)

	assert not output_file.exists()
	diagnostic = json.loads(output_file.with_suffix(".diagnostic.json").read_text())
	assert diagnostic["success"] is False
	assert "infrastructure" in diagnostic["error"]


def test_build_five_seed_figure_dataset_uses_every_domain_and_group() -> None:
	result = _complete_five_seed_figure_inputs()

	dataset = build_five_seed_figure_dataset(result)

	assert dataset["domain_coverage"]["logistics"] == [
		100.0,
		100.0,
		0.0,
		100.0,
		100.0,
	]
	assert set(dataset["group_curves"]) == {
		group_key for group_key, _label, _domains in BENCHMARK_GROUPS
	}
	assert dataset["group_curves"]["numeric"]["final_percent"] == 100.0
	assert dataset["pooled_success_count"] == 79
	assert dataset["pooled_evaluation_count"] == 80


def test_build_five_seed_figure_dataset_rejects_unverified_success() -> None:
	result = _complete_five_seed_figure_inputs()
	result["case_records"][0]["val_success"] = False

	with pytest.raises(ValueError, match="VAL acceptance"):
		build_five_seed_figure_dataset(result)


def test_build_five_seed_figure_dataset_rejects_worker_protocol_mismatch() -> None:
	result = _complete_five_seed_figure_inputs()
	result["protocol"]["validation_workers"] = 6

	with pytest.raises(ValueError, match="validation worker"):
		build_five_seed_figure_dataset(result)


def test_generate_five_seed_empirical_figure_writes_real_result_shape(
	tmp_path: Path,
) -> None:
	result = _complete_five_seed_figure_inputs()
	results_file = tmp_path / "five_seed_results.json"
	results_file.write_text(json.dumps(result), encoding="utf-8")
	output_file = tmp_path / "fig2_evaluation.pdf"

	metadata = generate_five_seed_empirical_figure(
		five_seed_results_file=results_file,
		output_file=output_file,
	)

	pdf_bytes = output_file.read_bytes()
	assert pdf_bytes.startswith(b"%PDF")
	assert b"/MediaBox [ 0 0 504 306 ]" in pdf_bytes
	assert b"DejaVuSans" not in pdf_bytes
	assert b"Helvetica" in pdf_bytes
	assert metadata["artifact_kind"] == "gp2pl_five_seed_empirical_figure"
	assert metadata["domain_count"] == 16
	assert metadata["seed_count"] == 5
	assert metadata["pooled_success_count"] == 79
	assert metadata["runtime_measure"] == "case_records.jason_run_seconds"
	assert metadata["figure_height_inches"] == FIGURE_HEIGHT_INCHES
	assert metadata["font_family"] == "Helvetica"
	assert metadata["minimum_text_size_points"] == 9.0
	assert metadata["color_mode"] == "colorblind-safe with redundant encodings"


def _complete_frozen_ablation_payload() -> dict[str, Any]:
	atomic_records: list[dict[str, Any]] = []
	atomic_seed_results: list[dict[str, Any]] = []
	atomic_summaries: list[dict[str, Any]] = []
	atomic_case_count_per_seed = 2 * len(DOMAIN_ORDER)
	for variant_index, (variant, method) in enumerate(ATOMIC_VARIANTS, start=1):
		variant_records: list[dict[str, Any]] = []
		seed_valid_counts: list[int] = []
		for seed in range(5):
			seed_records: list[dict[str, Any]] = []
			for domain in DOMAIN_ORDER:
				for case_index in (1, 2):
					valid = variant in {"maximal_certified_program", "full"}
					if variant in {
						"validated_evidence_adapter",
						"action_only_closure",
					}:
						valid = case_index == 1
					record = {
						"seed": seed,
						"variant": variant,
						"method": method,
						"case_id": f"{domain}:p{case_index:02d}.pddl",
						"domain": domain,
						"test": f"p{case_index:02d}",
						"status": "success" if valid else "failed",
						"valid": valid,
						"jason_success": valid,
						"val_attempted": valid,
						"val_success": valid,
						"timed_out": False,
						"duration_seconds": float(case_index + seed),
						"action_count": case_index if valid else None,
						"observed_action_prefix_count": 0,
					}
					atomic_records.append(record)
					variant_records.append(record)
					seed_records.append(record)
			seed_valid_count = sum(record["valid"] for record in seed_records)
			seed_valid_counts.append(seed_valid_count)
			atomic_seed_results.append(
				{
					"seed": seed,
					"variant": variant,
					"method": method,
					"case_count": len(seed_records),
					"valid_count": seed_valid_count,
					"status_counts": {},
				},
			)
		atomic_summaries.append(
			{
				"variant": variant,
				"method": method,
				"compiled_count": 80,
				"compiled_total": 80,
				"covered_target_count": 365,
				"producible_target_count": 365,
				"valid_trace_count": sum(seed_valid_counts),
				"test_count": len(variant_records),
				"mean_branch_count": 40.0 * variant_index,
				"sd_branch_count": float(variant_index),
				"mean_library_kib": 100.0 + variant_index,
				"sd_library_kib": 1.0,
				"mean_compile_seconds": float(variant_index),
				"sd_compile_seconds": 0.1,
			},
		)

	temporal_records: list[dict[str, Any]] = []
	temporal_summaries: list[dict[str, Any]] = []
	temporal_case_count = len(DOMAIN_ORDER)
	for variant_index, (variant, method) in enumerate(TEMPORAL_VARIANTS, start=1):
		variant_records: list[dict[str, Any]] = []
		for case_index, domain in enumerate(DOMAIN_ORDER, start=1):
			valid = variant != "dfa_aware_unprotected" or case_index % 2 == 0
			record = {
				"variant": variant,
				"method": method,
				"sample_id": f"{domain}_p01",
				"domain": domain,
				"profile": "eventual_conjunction",
				"status": "success" if valid else "jason_failed",
				"valid": valid,
				"jason_status": "success" if valid else "failed",
				"jason_timed_out": False,
				"duration_seconds": float(case_index),
				"action_count": 1 if valid else None,
				"observed_action_prefix_count": 0,
				"controller_plan_count": 4 + variant_index,
				"max_trigger_fanout": 2 if variant_index >= 3 else 3,
				"trigger_fanout_scope": "transition_repair_controller",
				"val_attempted": valid,
				"val_success": valid,
				"gold_accepted": valid,
				"prediction_accepted": valid,
				}
			temporal_records.append(record)
			variant_records.append(record)
		temporal_summaries.append(
			{
				"variant": variant,
				"method": method,
				"compiled_count": temporal_case_count,
				"test_count": temporal_case_count,
				"valid_trace_count": sum(record["valid"] for record in variant_records),
				"par2_seconds": 10.0,
				"median_joint_action_count": 1.0,
				"median_controller_plan_count": float(4 + variant_index),
				"maximum_trigger_fanout": 2 if variant_index >= 3 else 3,
			},
		)

	return {
		"schema_version": 1,
		"artifact_kind": "gp2pl_paired_ablation_results",
		"atomic": atomic_summaries,
		"atomic_records": atomic_records,
		"atomic_seed_results": atomic_seed_results,
		"temporal": temporal_summaries,
		"temporal_records": temporal_records,
		"protocol": {
			"registered_seeds": [0, 1, 2, 3, 4],
			"num_workers": 6,
			"timeout_seconds": 1800,
			"jason_java_stack_size": "64m",
			"atomic_pairing": {
				"paired": True,
				"seed_domain_group_count": 80,
			},
			"temporal_pairing": {
				"paired": True,
				"sample_count": temporal_case_count,
				"domain_count": len(DOMAIN_ORDER),
			},
			"case_contract": {
				"achievement": {"count": atomic_case_count_per_seed},
				"temporal": {"count": temporal_case_count},
			},
		},
	}


def _complete_paired_payload() -> dict[str, Any]:
	atomic_runs = []
	for seed in range(5):
		for variant_index, (variant, method) in enumerate(ATOMIC_VARIANTS, start=1):
			domains = {}
			for domain in DOMAIN_ORDER:
				valid_count = 1 if variant == "validated_evidence_adapter" else 2
				domains[domain] = {
					"library_metrics": {
						"selected_branch_count": variant_index * 10,
					},
					"execution_metrics": {
						"test_count": 2,
						"valid_trace_count": valid_count,
					},
				}
			atomic_runs.append(
				{
					"seed": seed,
					"variant": variant,
					"method": method,
					"domains": domains,
					"summary": {
						"source_revision": _clean_revision(),
						"settings": _execution_settings(),
					},
				},
			)
	temporal_runs = []
	for variant_index, (variant, method) in enumerate(TEMPORAL_VARIANTS, start=1):
		results = [
			_temporal_result("s1", duration=0.5, success=True),
			_temporal_result("s2", duration=5.0, success=variant_index >= 2),
			_temporal_result("s3", duration=50.0, success=variant_index >= 4),
		]
		temporal_runs.append(
			{
				"variant": variant,
				"method": method,
				"source_revision": _clean_revision(),
				"parameters": {
					**_execution_settings(),
					"jason_timeout_seconds": 1800,
				},
				"results": results,
			},
		)
	return {
		"success": True,
		"infrastructure_complete": True,
		"paired_inputs_verified": True,
		"paper_matrix_complete": True,
		"atomic_pairing": {"paired": True},
		"temporal_pairing": {"paired": True, "sample_count": 3},
		"source_revision": _clean_revision(),
		"seed_batch_manifests": {
			str(seed): {
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
		"domains": list(DOMAIN_ORDER),
		"registered_seeds": [0, 1, 2, 3, 4],
		"num_workers": 6,
		"timeout_seconds": 1800,
		"jason_java_stack_size": "64m",
		"atomic_runs": atomic_runs,
		"temporal_runs": temporal_runs,
	}


def _temporal_result(
	sample_id: str,
	*,
	duration: float,
	success: bool,
) -> dict[str, object]:
	return {
		"sample_id": sample_id,
		"duration_seconds": duration,
		"success": success,
		"status": "success" if success else "failed",
		"jason_status": "success" if success else "failed",
		"execution_validation": {
			"success": success,
			"replay_valid": success,
			"val_attempted": success,
			"val_success": success,
			"gold_accepted": success,
			"prediction_accepted": success,
		},
	}


def _clean_revision() -> dict[str, object]:
	return {
		"commit": "0123456789abcdef",
		"tracked_changes": False,
		"untracked_files": False,
	}


def _execution_settings() -> dict[str, object]:
	return {
		"num_workers": 6,
		"timeout_seconds": 1800,
		"plan_verifier_timeout_seconds": 1800,
		"jason_java_stack_size": "64m",
	}


def _complete_five_seed_figure_inputs() -> dict[str, Any]:
	domain_rows: list[dict[str, Any]] = []
	for domain in DOMAIN_ORDER:
		success_counts = [1, 1, 1, 1, 1]
		if domain == "logistics":
			success_counts = [1, 1, 0, 1, 1]
		domain_rows.append(
			{
				"domain": domain,
				"test_count": 1,
				"success_counts": success_counts,
				"success_rates": [float(value) for value in success_counts],
				"mean_success_rate": sum(success_counts) / 5,
				"sample_sd_success_rate": statistics.stdev(success_counts),
			},
		)
	seed_results: list[dict[str, Any]] = []
	case_records: list[dict[str, Any]] = []
	for seed in range(5):
		valid_count = 0
		for index, domain in enumerate(DOMAIN_ORDER, start=1):
			success = not (domain == "logistics" and seed == 2)
			valid_count += int(success)
			case_records.append(
				{
					"seed": seed,
					"domain": domain,
					"test_id": "p01",
					"status": "success" if success else "failed",
					"valid": success,
					"jason_run_seconds": float(index + seed + 1),
					"action_count": 1 if success else None,
					"timed_out": False,
					"val_success": success,
				},
			)
		seed_results.append(
			{
				"seed": seed,
				"success_count": valid_count,
				"evaluation_count": len(DOMAIN_ORDER),
			},
		)
	return {
		"artifact_kind": "gp2pl_five_seed_full_compiler_submission_result",
		"schema_version": 1,
		"protocol": {
			"method": "Full GP2PL",
			"compiler_variant": "full",
			"atomic_library_mode": "validated-policy-lifting",
			"seeds": [0, 1, 2, 3, 4],
			"domain_count": 16,
			"case_count_per_seed": 16,
			"validation_workers": 8,
			"independent_seed_runs": True,
			"evidence_union": False,
			"best_seed_selection": False,
			"success_contract": "Jason completion plus original-goal VAL acceptance",
		},
		"aggregate": {
			"pooled_success_count": 79,
			"pooled_evaluation_count": 80,
			"mean_success_rate": 79 / 80,
			"sample_sd_success_rate": statistics.stdev(
				[1.0, 1.0, 15 / 16, 1.0, 1.0],
			),
		},
		"seed_results": seed_results,
		"domains": domain_rows,
		"case_records": case_records,
	}
