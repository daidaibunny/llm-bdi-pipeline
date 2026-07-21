from __future__ import annotations

from pathlib import Path

from scripts.generate_aaai_method_figures import FIGURE_ONE_HEIGHT_INCHES
from scripts.generate_aaai_method_figures import FIGURE_ONE_WIDTH_INCHES
from scripts.generate_aaai_method_figures import FIGURE_TWO_HEIGHT_INCHES
from scripts.generate_aaai_method_figures import FIGURE_TWO_WIDTH_INCHES
from scripts.generate_aaai_method_figures import generate_method_figures


def test_generate_method_figures_preserves_locked_overview_and_verified_method_figure(
	tmp_path: Path,
) -> None:
	metadata = generate_method_figures(output_dir=tmp_path)

	figure_one = tmp_path / "fig1_architecture.png"
	figure_two = tmp_path / "fig2_policy_lifting.pdf"
	assert figure_one.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
	assert figure_two.read_bytes().startswith(b"%PDF")
	assert FIGURE_ONE_WIDTH_INCHES == 3.25
	assert FIGURE_ONE_HEIGHT_INCHES == 1.60
	assert FIGURE_TWO_WIDTH_INCHES == 7.0
	assert FIGURE_TWO_HEIGHT_INCHES == 3.45

	assert metadata["color_mode"] == (
		"locked_rgb_overview_and_generated_cmyk_method_figure"
	)
	assert metadata["minimum_text_size_points"] == 9.0
	assert metadata["figure_one"]["semantic_role"] == "problem_overview"
	assert metadata["figure_one"]["source_kind"] == "locked_final_artwork"
	assert metadata["figure_one"]["pixel_size"] == [2558, 1257]
	assert metadata["figure_one"]["dpi"] == 330
	assert metadata["figure_two"]["semantic_role"] == (
		"worked_policy_lifting_example"
	)
	assert metadata["figure_two"]["source_sha256"] == {
		"domain_pddl": metadata["figure_two"]["source_sha256"]["domain_pddl"],
		"evidence_policy": metadata["figure_two"]["source_sha256"][
			"evidence_policy"
		],
		"agentspeak_library": metadata["figure_two"]["source_sha256"][
			"agentspeak_library"
		],
	}
	assert all(
		len(digest) == 64
		for digest in metadata["figure_two"]["source_sha256"].values()
	)
