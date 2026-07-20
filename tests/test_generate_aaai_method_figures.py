from __future__ import annotations

from pathlib import Path

from scripts.generate_aaai_method_figures import FIGURE_ONE_HEIGHT_INCHES
from scripts.generate_aaai_method_figures import FIGURE_ONE_WIDTH_INCHES
from scripts.generate_aaai_method_figures import FIGURE_TWO_HEIGHT_INCHES
from scripts.generate_aaai_method_figures import FIGURE_TWO_WIDTH_INCHES
from scripts.generate_aaai_method_figures import LOCKED_FIGURE_ONE_SHA256
from scripts.generate_aaai_method_figures import generate_method_figures


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LATEX_ROOT = PROJECT_ROOT / "latex_code/aamas_method_paper"


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
	assert metadata["figure_one"]["sha256"] == LOCKED_FIGURE_ONE_SHA256
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

	figure_one_labels = set(metadata["figure_one"]["labels"])
	assert "Domain" in figure_one_labels
	assert "Singleton-goal Evidence" in figure_one_labels
	assert "Maintained BDI Plan Library" in figure_one_labels
	assert "MOOSE" not in figure_one_labels
	assert "PDDL" not in figure_one_labels
	assert "Clingo" not in figure_one_labels


def test_manuscript_separates_compiler_overview_and_local_cases() -> None:
	main_text = (LATEX_ROOT / "main.tex").read_text(encoding="utf-8")
	method_text = (LATEX_ROOT / "sections/method.tex").read_text(encoding="utf-8")
	evaluation_text = (LATEX_ROOT / "sections/evaluation.tex").read_text(
		encoding="utf-8",
	)
	supplement_text = (
		LATEX_ROOT / "sections/technical_appendix_content.tex"
	).read_text(encoding="utf-8")

	assert "figures/fig1_architecture.png" in main_text
	assert "\\label{fig:architecture}" in main_text
	assert "figures/fig2_compiler_stages.pdf" in main_text
	assert "\\label{fig:compiler-stages}" in main_text
	assert "\\label{fig:atomic-case}" in method_text
	assert "\\label{fig:temporal-case}" not in method_text
	assert "fig4_temporal_case.pdf" not in main_text
	assert "\\label{fig:evaluation-summary}" not in evaluation_text
	assert "\\gpplfigurethreepath" not in evaluation_text
	assert "\\begin{minipage}" not in main_text
	assert "\\mathcal Q_q" in method_text
	assert "\\label{alg:temporal}" not in method_text
	assert "\\label{alg:temporal}" in supplement_text


def test_method_figure_generator_uses_canonical_formal_vocabulary() -> None:
	source = (
		PROJECT_ROOT / "scripts/generate_aaai_method_figures.py"
	).read_text(encoding="utf-8")

	for required_term in (
		"producible-target\\nexpansion",
		"$T_D(E)$",
		"$\\\\mathcal{C}^{\\\\checkmark}_{D,E}$",
		"Candidate soundness certificate",
		"internal-call closure",
		"$\\\\mathcal{M}_D=S^\\\\star$",
	):
		assert required_term in source

	for ambiguous_term in (
		"schema closure",
		"$T=\\\\mathrm{closure}_D(E)$",
		"resource restoration",
		"$\\\\mathcal{C}^{\\\\mathrm{cert}}_D$",
	):
		assert ambiguous_term not in source
