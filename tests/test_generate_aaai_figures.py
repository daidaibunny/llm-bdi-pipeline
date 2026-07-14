from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from typing import Callable

import pytest

from scripts.generate_aaai_figures import ATOMIC_VARIANTS
from scripts.generate_aaai_figures import DOMAIN_ORDER
from scripts.generate_aaai_figures import FIGURE_HEIGHT_INCHES
from scripts.generate_aaai_figures import FIGURE_WIDTH_INCHES
from scripts.generate_aaai_figures import PROJECT_ROOT
from scripts.generate_aaai_figures import TEMPORAL_VARIANTS
from scripts.generate_aaai_figures import build_figure_dataset
from scripts.generate_aaai_figures import cumulative_solved_fraction
from scripts.generate_aaai_figures import generate_empirical_figure
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
		(
			lambda payload: payload["atomic_runs"][0]["summary"]["source_revision"].update(
				{"commit": "different"},
			),
			"source revision",
		),
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


def test_generate_empirical_figure_writes_vector_pdf_and_provenance(
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
	assert FIGURE_HEIGHT_INCHES == 3.0
	assert b"/MediaBox [ 0 0 504 216 ]" in pdf_bytes
	assert b"DejaVuSans-Bold" not in pdf_bytes
	assert metadata["artifact_kind"] == "gp2pl_empirical_figure"
	assert metadata["source_sha256"]
	assert metadata["atomic_seed_count"] == 5
	assert metadata["atomic_domain_count"] == 16
	assert metadata["temporal_sample_count"] == 3
	assert metadata["figure_width_inches"] == 7.0
	assert metadata["figure_height_inches"] == 3.0
	assert output_file.with_suffix(".metadata.json").is_file()


def test_manuscript_places_gated_empirical_figure_after_protocol() -> None:
	main_text = (PROJECT_ROOT / "latex_code/aamas_method_paper/main.tex").read_text()
	evaluation_text = (
		PROJECT_ROOT / "latex_code/aamas_method_paper/sections/evaluation.tex"
	).read_text()

	assert (
		"\\providecommand{\\gpplfiguretwopath}{figures/fig2_evaluation.pdf}"
		in main_text
	)
	figure_position = evaluation_text.index("\\begin{figure*}[t]")
	assert evaluation_text.index("\\paragraph{Validation and measures.}") < figure_position
	assert figure_position < evaluation_text.index(
		"\\input{sections/result_profile_table}",
	)
	assert "\\IfFileExists{\\gpplfiguretwopath}" in evaluation_text
	assert "\\includegraphics[width=\\textwidth]{\\gpplfiguretwopath}" in (
		evaluation_text
	)
	assert "\\label{fig:evaluation-summary}" in evaluation_text


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
