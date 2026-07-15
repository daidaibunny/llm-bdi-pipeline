from __future__ import annotations

from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LATEX_ROOT = PROJECT_ROOT / "latex_code/aamas_method_paper"


def _manuscript_sources() -> tuple[Path, ...]:
	return tuple(sorted(LATEX_ROOT.rglob("*.tex")))


def test_manuscript_uses_the_official_aaai_2027_style() -> None:
	assert (LATEX_ROOT / "aaai2027.sty").is_file()
	assert (LATEX_ROOT / "aaai2027.bst").is_file()
	for source_path in (
		LATEX_ROOT / "main.tex",
		LATEX_ROOT / "technical_appendix.tex",
		LATEX_ROOT / "sections/reproducibility_checklist.tex",
	):
		source = source_path.read_text(encoding="utf-8")
		assert "\\usepackage[submission]{aaai2027}" in source
		assert "aaai2026" not in source
		for forbidden_font_package in ("times", "helvet", "courier"):
			assert f"\\usepackage{{{forbidden_font_package}}}" not in source
	for source_path in (
		LATEX_ROOT / "main.tex",
		LATEX_ROOT / "technical_appendix.tex",
	):
		assert "/TemplateVersion (2027.1)" in source_path.read_text(
			encoding="utf-8",
		)


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
	supplement_source = (
		LATEX_ROOT / "sections/technical_appendix_content.tex"
	).read_text(encoding="utf-8")
	temporal_results_position = evaluation_source.index(
		"\\subsection{End-to-End Temporal Results}",
	)
	assert evaluation_source.index("\\input{sections/result_profile_table}") > (
		temporal_results_position
	)
	assert "\\input{sections/result_domain_table}" not in evaluation_source
	assert "\\input{sections/result_domain_table}" in supplement_source


def test_main_and_supplement_use_the_approved_table_split() -> None:
	method_source = (LATEX_ROOT / "sections/method.tex").read_text(encoding="utf-8")
	evaluation_source = (LATEX_ROOT / "sections/evaluation.tex").read_text(
		encoding="utf-8",
	)
	supplement_source = (
		LATEX_ROOT / "sections/technical_appendix_content.tex"
	).read_text(encoding="utf-8")

	assert "\\label{tab:supported-fragment}" in method_source
	assert "\\label{tab:compiler-obligations}" in method_source
	assert "\\input{sections/result_five_seed_atomic_table}" in evaluation_source
	assert "\\input{sections/result_profile_table}" in evaluation_source
	assert "\\input{sections/result_five_seed_atomic_domain_table}" not in (
		evaluation_source
	)
	assert "\\input{sections/result_domain_table}" not in evaluation_source
	assert "\\input{sections/result_five_seed_atomic_domain_table}" in (
		supplement_source
	)
	assert "\\input{sections/result_domain_table}" in supplement_source


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
	abstract_end_position = main_source.index("\\end{abstract}")
	introduction_position = main_source.index("\\section{Introduction}")
	example_position = main_source.index("Singleton-goal evidence for")
	background_position = main_source.index("\\input{sections/background}")
	assert abstract_end_position < introduction_position < example_position
	assert example_position < figure_one_position
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


def test_manuscript_distinguishes_atomic_core_query_plans_and_library() -> None:
	main_source = (LATEX_ROOT / "main.tex").read_text(encoding="utf-8")
	background_source = (LATEX_ROOT / "sections/background.tex").read_text(
		encoding="utf-8",
	)
	method_source = (LATEX_ROOT / "sections/method.tex").read_text(encoding="utf-8")
	supplement_source = (
		LATEX_ROOT / "sections/technical_appendix_content.tex"
	).read_text(encoding="utf-8")

	assert "certified atomic module core $\\mathcal{M}_D$" in background_source
	assert "query-local plan set $\\mathcal{Q}_q$" in background_source
	assert "\\mathcal{L}_D^{[k]}" in background_source
	assert "\\mathcal{L}_D^{[0]}=\\mathcal{M}_D" in background_source
	assert "\\bigcup_{i=1}^{k}\\mathcal{Q}_{q_i}" in background_source
	assert "\\mathcal{L}_D^{(q)}" not in background_source
	assert "\\mathcal L_D^{(q)}" not in method_source
	assert "\\mathcal L_D^{(q)}" not in supplement_source
	assert "\\ENSURE Certified atomic module core $\\mathcal M_D$" in method_source
	assert "selected atomic core $\\mathcal M_D$" in method_source
	assert "query-local plan set $\\mathcal Q_q$" in method_source
	assert "The certified atomic module core is the feasible selected set" in (
		supplement_source
	)
	assert "$\\mathcal M_D:=S$" in supplement_source
	assert "does not define the core" in supplement_source
	assert re.search(
		r"maintained domain library\s+\$\\mathcal L_D\^\{\[k\]\}\$",
		supplement_source,
	)

	figure_caption = re.search(
		r"\\caption\{GP2PL compiles(.*?)\}\s*"
		r"\\label\{fig:architecture\}",
		main_source,
		re.DOTALL,
	)
	assert figure_caption is not None
	caption_text = " ".join(figure_caption.group(1).split())
	assert "atomic module core" in caption_text
	assert "$\\mathcal M_D=\\mathcal L_D^{[0]}$" in caption_text
	assert "controller plans" in caption_text
	assert "$\\mathcal Q_q$" in caption_text
	assert "one maintained BDI library" in caption_text
	assert "$\\mathcal L_D^{[k+1]}=\\mathcal L_D^{[k]}\\cup\\mathcal Q_q$" in caption_text


def test_figure_design_separates_target_generation_from_set_level_call_closure() -> None:
	main_source = (LATEX_ROOT / "main.tex").read_text(encoding="utf-8")
	outline_source = (
		PROJECT_ROOT / "docs" / "aaai_paper_narrative_outline.md"
	).read_text(encoding="utf-8")

	assert "`Singleton-goal policy evidence E`" in outline_source
	assert "`(1) Construct + certify core once`" in outline_source
	assert "relevant slice of $T_D(E)$" in outline_source
	assert "`producer preconditions`" in outline_source
	assert "`precondition repair via clear/1`" in outline_source
	assert "set-level constraint" in outline_source
	assert "\\operatorname{call}(S)" in outline_source
	assert "subseteq_{\\mathrm{type}}" in outline_source

	figure_two_caption = re.search(
		r"\\caption\{Certified lifting(.*?)\}\s*"
		r"\\label\{fig:policy-lifting-example\}",
		main_source,
		re.DOTALL,
	)
	assert figure_two_caption is not None
	caption_text = " ".join(figure_two_caption.group(1).split())
	assert "each candidate is checked" in caption_text
	assert "set satisfying evidence coverage and internal-call closure" in caption_text
	assert "candidates pass binding, executability, achievement, internal-call closure" not in (
		caption_text
	)


def test_main_paper_keeps_serialization_details_in_the_supplement() -> None:
	main_paper_sources = (
		LATEX_ROOT / "main.tex",
		LATEX_ROOT / "sections/background.tex",
		LATEX_ROOT / "sections/related_work.tex",
		LATEX_ROOT / "sections/method.tex",
		LATEX_ROOT / "sections/evaluation.tex",
	)
	combined_source = "\n".join(
		path.read_text(encoding="utf-8") for path in main_paper_sources
	)
	for engineering_phrase in (
		"serialized artifact has exactly eight fields",
		"exact eight-key JSON",
		"six-worker MOOSE configuration",
		"the 12-worker run takes",
		"fixed seed-0 library snapshot",
	):
		assert engineering_phrase not in combined_source
