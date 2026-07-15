from __future__ import annotations

from pathlib import Path

from scripts.generate_aaai_method_figures import FIGURE_ONE_HEIGHT_INCHES
from scripts.generate_aaai_method_figures import FIGURE_ONE_WIDTH_INCHES
from scripts.generate_aaai_method_figures import FIGURE_TWO_HEIGHT_INCHES
from scripts.generate_aaai_method_figures import FIGURE_TWO_WIDTH_INCHES
from scripts.generate_aaai_method_figures import generate_method_figures


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LATEX_ROOT = PROJECT_ROOT / "latex_code/aamas_method_paper"


def test_generate_method_figures_writes_vector_pdfs_with_verified_sources(
	tmp_path: Path,
) -> None:
	metadata = generate_method_figures(output_dir=tmp_path)

	figure_one = tmp_path / "fig1_architecture.pdf"
	figure_two = tmp_path / "fig2_policy_lifting.pdf"
	assert figure_one.read_bytes().startswith(b"%PDF")
	assert figure_two.read_bytes().startswith(b"%PDF")
	assert FIGURE_ONE_WIDTH_INCHES == 3.25
	assert FIGURE_ONE_HEIGHT_INCHES == 2.55
	assert FIGURE_TWO_WIDTH_INCHES == 7.0
	assert FIGURE_TWO_HEIGHT_INCHES == 3.45

	assert metadata["color_mode"] == "colorblind_safe_cmyk"
	assert metadata["minimum_text_size_points"] == 9.0
	assert metadata["figure_one"]["semantic_role"] == "problem_overview"
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

	figure_one_labels = set(metadata["figure_one"]["labels"])
	assert "Domain model" in figure_one_labels
	assert "Singleton-goal policy evidence" in figure_one_labels
	assert "One maintained plan library" in figure_one_labels
	assert "MOOSE" not in figure_one_labels
	assert "PDDL" not in figure_one_labels
	assert "Clingo" not in figure_one_labels


def test_manuscript_uses_overview_worked_example_and_empirical_figure() -> None:
	main_text = (LATEX_ROOT / "main.tex").read_text(encoding="utf-8")
	method_text = (LATEX_ROOT / "sections/method.tex").read_text(encoding="utf-8")
	evaluation_text = (LATEX_ROOT / "sections/evaluation.tex").read_text(
		encoding="utf-8",
	)

	assert "figures/fig1_architecture.pdf" in main_text
	assert "\\label{fig:architecture}" in main_text
	assert "figures/fig2_policy_lifting.pdf" in main_text
	assert "\\label{fig:policy-lifting-example}" in main_text
	assert "\\label{fig:evaluation-summary}" in evaluation_text
	assert "\\begin{minipage}" not in main_text
	assert "\\mathcal Q_q" in method_text
	assert "\\label{alg:temporal}" in method_text
