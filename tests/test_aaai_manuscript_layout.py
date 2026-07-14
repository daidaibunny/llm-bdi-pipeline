from __future__ import annotations

from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LATEX_ROOT = PROJECT_ROOT / "latex_code/aamas_method_paper"


def _manuscript_sources() -> tuple[Path, ...]:
	return tuple(sorted(LATEX_ROOT.rglob("*.tex")))


def test_figures_and_tables_use_flexible_aaai_placement_without_forced_flushes() -> None:
	float_pattern = re.compile(
		r"\\begin\{(?:(?:figure|table)\*?|algorithm)\}"
		r"\[(?P<placement>[^]]+)]",
	)
	placements: list[tuple[str, str]] = []
	combined_source = ""
	for source_path in _manuscript_sources():
		source = source_path.read_text(encoding="utf-8")
		combined_source += source
		placements.extend(
			(source_path.name, match.group("placement"))
			for match in float_pattern.finditer(source)
		)

	assert placements
	assert all(placement == "htbp" for _filename, placement in placements), placements
	for forbidden_command in (
		"\\clearpage",
		"\\newpage",
		"\\pagebreak",
		"\\@fptop",
		"\\@dblfptop",
	):
		assert forbidden_command not in combined_source
	for undersized_command in ("\\tiny", "\\scriptsize", "\\footnotesize"):
		assert undersized_command not in combined_source


def test_tables_use_at_least_nine_point_text_and_place_captions_below() -> None:
	table_pattern = re.compile(
		r"\\begin\{table\*?\}\[htbp](?P<body>.*?)\\end\{table\*?\}",
		re.DOTALL,
	)
	tables: list[tuple[str, str]] = []
	for source_path in _manuscript_sources():
		source = source_path.read_text(encoding="utf-8")
		tables.extend(
			(source_path.name, match.group("body"))
			for match in table_pattern.finditer(source)
		)

	assert tables
	for filename, table_body in tables:
		for undersized_command in ("\\tiny", "\\scriptsize", "\\footnotesize"):
			assert undersized_command not in table_body, (
				filename,
				undersized_command,
			)
		assert table_body.index("\\caption{") > table_body.rindex("\\end{tabular}")
		assert table_body.index("\\label{") > table_body.index("\\caption{")


def test_figures_avoid_minipages_and_place_captions_below_content() -> None:
	figure_pattern = re.compile(
		r"\\begin\{figure\*?\}\[htbp](?P<body>.*?)\\end\{figure\*?\}",
		re.DOTALL,
	)
	figures: list[tuple[str, str]] = []
	for source_path in _manuscript_sources():
		source = source_path.read_text(encoding="utf-8")
		figures.extend(
			(source_path.name, match.group("body"))
			for match in figure_pattern.finditer(source)
		)

	assert figures
	for filename, figure_body in figures:
		assert "\\begin{minipage}" not in figure_body, filename
		content_markers = (
			figure_body.rfind("\\includegraphics"),
			figure_body.rfind("\\end{tabular}"),
		)
		assert figure_body.index("\\caption{") > max(content_markers)
		assert figure_body.index("\\label{") > figure_body.index("\\caption{")


def test_manuscript_uses_required_caption_package_without_float_overrides() -> None:
	root_sources = (
		LATEX_ROOT / "main.tex",
		LATEX_ROOT / "technical_appendix.tex",
	)
	for source_path in root_sources:
		source = source_path.read_text(encoding="utf-8")
		assert "\\usepackage{caption}" in source
		for forbidden_package in (
			"dblfloatfix",
			"float",
			"placeins",
			"stfloats",
			"subcaption",
		):
			assert f"\\usepackage{{{forbidden_package}}}" not in source


def test_temporal_result_tables_follow_their_result_subsection() -> None:
	evaluation_source = (LATEX_ROOT / "sections/evaluation.tex").read_text(
		encoding="utf-8",
	)
	temporal_results_position = evaluation_source.index(
		"\\subsection{End-to-End Temporal Results}",
	)
	for table_input in (
		"\\input{sections/result_profile_table}",
		"\\input{sections/result_domain_table}",
	):
		assert evaluation_source.index(table_input) > temporal_results_position


def test_main_paper_reserves_the_three_figure_program_in_order() -> None:
	main_source = (LATEX_ROOT / "main.tex").read_text(encoding="utf-8")
	evaluation_source = (LATEX_ROOT / "sections/evaluation.tex").read_text(
		encoding="utf-8",
	)

	assert (
		"\\providecommand{\\gpplfigureonepath}{figures/fig1_architecture.pdf}"
		in main_source
	)
	assert (
		"\\providecommand{\\gpplfiguretwopath}{figures/fig2_policy_lifting.pdf}"
		in main_source
	)
	assert (
		"\\providecommand{\\gpplfigurethreepath}{figures/fig2_evaluation.pdf}"
		in main_source
	)
	figure_one_position = main_source.index("\\label{fig:architecture}")
	figure_two_position = main_source.index("\\label{fig:policy-lifting-example}")
	background_position = main_source.index("\\input{sections/background}")
	assert figure_one_position < figure_two_position < background_position
	assert "\\begin{figure}[htbp]" in main_source
	assert "\\begin{figure*}[htbp]" in main_source
	assert "\\IfFileExists{\\gpplfigureonepath}" in main_source
	assert "\\IfFileExists{\\gpplfiguretwopath}" in main_source
	assert "Figure 1 artwork placeholder" in main_source
	assert "Figure 2 artwork placeholder" in main_source
	assert "\\IfFileExists{\\gpplfigurethreepath}" in evaluation_source
	assert "\\includegraphics[width=\\textwidth]{\\gpplfigurethreepath}" in (
		evaluation_source
	)
	assert "\\label{fig:evaluation-summary}" in evaluation_source
