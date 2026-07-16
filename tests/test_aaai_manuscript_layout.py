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
	page_top_float_files = {"main.tex", "evaluation.tex"}
	assert all(
		placement == "htbp"
		or (filename in page_top_float_files and placement == "t!")
		for filename, placement in placements
	), placements
	assert placements.count(("main.tex", "t!")) == 1
	assert placements.count(("evaluation.tex", "t!")) == 1
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
		"\\paragraph{End-to-end temporal validation.}",
	)
	assert evaluation_source.index("\\input{sections/result_profile_table}") > (
		temporal_results_position
	)
	assert "\\input{sections/result_domain_table}" not in evaluation_source
	assert "\\input{sections/result_domain_table}" in supplement_source


def test_result_floats_are_flushed_before_the_conclusion() -> None:
	main_source = (LATEX_ROOT / "main.tex").read_text(encoding="utf-8")

	barrier_position = main_source.index("\\FloatBarrier")
	conclusion_position = main_source.index("\\section{Conclusion}")
	bibliography_position = main_source.index("\\bibliography{references}")

	assert barrier_position < conclusion_position < bibliography_position


def test_manuscript_explains_witness_backed_teg_benchmark_construction() -> None:
	evaluation_source = (LATEX_ROOT / "sections/evaluation.tex").read_text(
		encoding="utf-8",
	)
	evaluation_text = " ".join(evaluation_source.split())
	supplement_source = (
		LATEX_ROOT / "sections/technical_appendix_content.tex"
	).read_text(encoding="utf-8")
	outline_source = (
		PROJECT_ROOT / "docs" / "aaai_paper_narrative_outline.md"
	).read_text(encoding="utf-8")

	for required_main_claim in (
		"\\paragraph{Temporal benchmark construction.}",
		"ignores the original achievement goal",
		"rollouts of at most three actions",
		"alpha-normalized semantic-signature",
		"one witness-backed query for each of the 1,228 test problems",
		"475 distinct translation inputs",
		"Technical Supplement, Sec.~4.1",
	):
		assert required_main_claim in evaluation_text

	for required_supplement_contract in (
		"\\label{app:teg-dataset}",
		"\\mathcal B_i=\\langle D,P_i,q_i,T_i,\\theta_i,\\pi_i\\rangle",
		"retained only as provenance",
		"\\label{alg:teg-benchmark-construction}",
		"\\label{tab:teg-construction-profiles}",
		"\\label{tab:teg-construction-bounds}",
		"Failure means no witness was found under these bounds",
		"\\path{src/temporal_input/nl_benchmark.py}",
		"\\path{src/temporal_input/translation_worklist.py}",
	):
		assert required_supplement_contract in supplement_source

	assert "bounded legal non-repeating rollouts" in outline_source
	assert "Keep the frozen\nprompt in Sec. 4.2" in outline_source
	assert "PDDL provenance in Sec. 4.3" in outline_source


def test_manuscript_formalizes_ltlf_syntax_semantics_and_scope_boundaries() -> None:
	background_source = (LATEX_ROOT / "sections/background.tex").read_text(
		encoding="utf-8",
	)
	background_text = " ".join(background_source.split())
	method_source = (LATEX_ROOT / "sections/method.tex").read_text(encoding="utf-8")
	supplement_source = (
		LATEX_ROOT / "sections/technical_appendix_content.tex"
	).read_text(encoding="utf-8")

	for scope_symbol in (
		"\\Phi_{\\mathrm{syn}}",
		"\\Phi_{\\mathrm{bench}}",
		"\\Phi_{\\mathrm{cert}}",
	):
		assert scope_symbol in background_source
		assert scope_symbol in supplement_source
	assert "Negation is restricted to atoms" in background_text
	assert "several valuation cubes" in background_text
	assert "not one disjunctive guard" in background_text
	for semantic_clause in (
		"\\xi,i\\models X\\varphi",
		"\\xi,i\\models F\\varphi",
		"\\xi,i\\models \\varphi U\\psi",
	):
		assert semantic_clause in supplement_source
	assert "a\\in\\mathit{val}_q(s)" in method_source
	assert "\\mu_q(a)=p(\\bar t)" in method_source
	assert "\\mu_q(a)=[f(\\bar t)=c]" in method_source


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
		"\\providecommand{\\gpplfigureonepath}{figures/fig1_architecture.png}"
		in main_source
	)
	assert (
		"\\providecommand{\\gpplfiguretwopath}{figures/fig2_policy_lifting.pdf}"
		in main_source
	)
	assert (
		"\\providecommand{\\gpplfigurethreepath}{figures/fig3_evaluation.png}"
		in main_source
	)
	assert r"\newcommand{\resultbest}[1]{\textbf{#1}}" in main_source
	assert r"\newcommand{\resultselected}[1]" in main_source
	figure_one_position = main_source.index("\\label{fig:architecture}")
	figure_two_position = main_source.index("\\label{fig:policy-lifting-example}")
	abstract_end_position = main_source.index("\\end{abstract}")
	introduction_position = main_source.index("\\section{Introduction}")
	example_position = main_source.index("Blocks World")
	background_position = main_source.index("\\input{sections/background}")
	assert abstract_end_position < introduction_position < example_position
	assert example_position < figure_one_position
	assert figure_one_position < figure_two_position < background_position
	assert "\\begin{figure}[htbp]" in main_source
	assert "\\begin{figure*}[t!]" in main_source
	assert "\\IfFileExists{\\gpplfigureonepath}" in main_source
	assert "\\IfFileExists{\\gpplfiguretwopath}" in main_source
	assert "Figure 1 artwork placeholder" in main_source
	assert "Figure 2 artwork placeholder" in main_source
	assert "\\IfFileExists{\\gpplfigurethreepath}" in evaluation_source
	assert "\\includegraphics[width=\\textwidth]{\\gpplfigurethreepath}" in (
		evaluation_source
	)
	assert "\\label{fig:evaluation-summary}" in evaluation_source


def test_abstract_uses_paper_level_granularity() -> None:
	main_source = (LATEX_ROOT / "main.tex").read_text(encoding="utf-8")
	abstract_match = re.search(
		r"\\begin\{abstract\}(?P<body>.*?)\\end\{abstract\}",
		main_source,
		re.DOTALL,
	)
	assert abstract_match is not None
	abstract_source = abstract_match.group("body")
	abstract_words = re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", abstract_source)

	assert len(abstract_words) <= 180
	for required_summary in (
		"representation gap",
		"certified BDI plan libraries",
		"finite-trace temporal goals",
		"supported fragment",
		"independently validated accepting traces",
	):
		assert required_summary in abstract_source
	for implementation_level_term in (
		"candidate-construction grammar",
		"target-preserving resource discharge",
		"primitive-step monitoring",
		"Clingo",
		"ltlf2dfa",
	):
		assert implementation_level_term not in abstract_source


def test_introduction_explains_blocks_before_using_symbolic_example() -> None:
	main_source = (LATEX_ROOT / "main.tex").read_text(encoding="utf-8")
	introduction_source = main_source[
		main_source.index("\\section{Introduction}") : main_source.index(
			"\\input{sections/background}",
		)
	]

	assert "Blocks World is a standard planning domain" in introduction_source
	assert introduction_source.index("Blocks World") < introduction_source.index(
		"\\texttt{on(X,Y)}",
	)
	assert "destination block is clear" in introduction_source
	assert "F(\\mathit{on}" not in introduction_source
	assert "GP2PL makes three contributions" in introduction_source


def test_manuscript_typography_distinguishes_prose_code_and_formal_notation() -> None:
	authored_sources = (
		LATEX_ROOT / "main.tex",
		LATEX_ROOT / "technical_appendix.tex",
		LATEX_ROOT / "sections/background.tex",
		LATEX_ROOT / "sections/related_work.tex",
		LATEX_ROOT / "sections/method.tex",
		LATEX_ROOT / "sections/evaluation.tex",
		LATEX_ROOT / "sections/technical_appendix_content.tex",
	)
	combined_source = "\n".join(
		path.read_text(encoding="utf-8") for path in authored_sources
	)

	assert "LTLf2DFA" in combined_source
	assert "\\texttt{ltlf2dfa}" not in combined_source
	assert "\\newcommand{\\mayadd}{\\ensuremath{\\mathrm{MayAdd}}}" in (
		LATEX_ROOT / "main.tex"
	).read_text(encoding="utf-8")
	assert "\\operatorname{realizes}_D" in combined_source
	assert "\\operatorname{covers}_D" in combined_source
	for inappropriate_style in (
		"\\emph{",
		"\\textit{",
		"\\mathsf{",
	):
		assert inappropriate_style not in combined_source


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
	assert "\\ENSURE Certified lifted atomic module core $\\mathcal M_D$" in method_source
	assert "selected atomic core $\\mathcal M_D$" in method_source
	assert "query-local plan set $\\mathcal Q_q$" in method_source
	assert "The certified atomic module core is selected directly as" in (
		supplement_source
	)
	assert "\\mathcal M_D=" in supplement_source
	assert "\\operatorname*{lexargmin}" in supplement_source
	assert "does not define the core" in supplement_source
	assert re.search(
		r"maintained domain library\s+\$\\mathcal L_D\^\{\[k\]\}\$",
		supplement_source,
	)

	figure_caption = re.search(
		r"\\caption\{GP2PL separates(.*?)\}\s*"
		r"\\label\{fig:architecture\}",
		main_source,
		re.DOTALL,
	)
	assert figure_caption is not None
	caption_text = " ".join(figure_caption.group(1).split())
	assert "$\\mathcal E_{\\mathrm{raw}}$" in caption_text
	assert "$\\mathcal I_{\\mathrm{train}}$" in caption_text
	assert "Validated policy lifting" in caption_text
	assert "$\\mathcal M_D=\\mathcal L_D^{[0]}$" in caption_text
	assert "DFA-guided temporal compilation" in caption_text
	assert "$\\widehat{\\tau}_q$" in caption_text
	assert "$\\mathcal Q_q$" in caption_text
	assert "sole maintained library" in caption_text
	assert "$\\mathcal L_D^{[k+1]}=\\mathcal L_D^{[k]}\\cup\\mathcal Q_q$" in caption_text


def test_atomic_compilation_makes_canonical_lifting_explicit() -> None:
	method_source = (LATEX_ROOT / "sections/method.tex").read_text(encoding="utf-8")
	supplement_source = (
		LATEX_ROOT / "sections/technical_appendix_content.tex"
	).read_text(encoding="utf-8")
	decisions_source = (
		PROJECT_ROOT / "docs" / "research_pipeline_decisions.md"
	).read_text(encoding="utf-8")
	outline_source = (
		PROJECT_ROOT / "docs" / "aaai_paper_narrative_outline.md"
	).read_text(encoding="utf-8")

	assert "Compile the Certified Lifted Atomic Module Core" in method_source
	assert "E_0\\leftarrow\\textsc{NormalizeEvidence}" in method_source
	assert "E\\leftarrow\\textsc{CanonicalLift}(E_0,D)" in method_source
	assert "\\textsc{LiftSchemas}" in method_source
	assert "definition}[Canonical lifting]" in supplement_source
	assert "preserves repeated-variable sharing" in supplement_source
	assert "constants declared by $D$ remain constants" in " ".join(
		supplement_source.split(),
	)
	assert "`E_0` is the provider-normalized evidence program" in decisions_source
	assert "`E = CanonicalLift_D(E_0)`" in decisions_source
	assert "`E = CanonicalLift_D(E_0)`" in outline_source


def test_figure_design_separates_target_generation_from_set_level_call_closure() -> None:
	main_source = (LATEX_ROOT / "main.tex").read_text(encoding="utf-8")
	outline_source = (
		PROJECT_ROOT / "docs" / "aaai_paper_narrative_outline.md"
	).read_text(encoding="utf-8")

	assert "`Singleton-goal policy evidence E`" in outline_source
	assert "`(1) Lift + certify core once`" in outline_source
	normalized_outline = " ".join(outline_source.split())
	assert "relevant slice of `$T_D(E)" in normalized_outline
	assert "`producer preconditions`" in outline_source
	assert "recursive preparation via clear/1" in normalized_outline
	assert "every !goal resolves inside $\\mathcal M_D$" in outline_source
	assert "$\\mathcal M_D=\\mathcal L_D^{[0]}$" in outline_source
	assert "$\\operatorname{Closed}_D(\\mathcal L_D^{[k+1]})$" in outline_source

	figure_two_caption = re.search(
		r"\\caption\{Certified lifting(.*?)\}\s*"
		r"\\label\{fig:policy-lifting-example\}",
		main_source,
		re.DOTALL,
	)
	assert figure_two_caption is not None
	caption_text = " ".join(figure_two_caption.group(1).split())
	assert "canonically lifts singleton-goal evidence" in caption_text
	assert "internally closed atomic core" in caption_text
	assert "balanced query-local controller" in caption_text
	assert "without relearning the core" in caption_text
	assert (LATEX_ROOT / "figures/fig2_policy_lifting.pdf").is_file()
	assert "\\begin{figure*}[t!]" in main_source


def test_manuscript_uses_library_centered_closure_and_selection_notation() -> None:
	method_source = (LATEX_ROOT / "sections/method.tex").read_text(encoding="utf-8")
	supplement_source = (
		LATEX_ROOT / "sections/technical_appendix_content.tex"
	).read_text(encoding="utf-8")
	decisions_source = (
		PROJECT_ROOT / "docs" / "research_pipeline_decisions.md"
	).read_text(encoding="utf-8")
	outline_source = (
		PROJECT_ROOT / "docs" / "aaai_paper_narrative_outline.md"
	).read_text(encoding="utf-8")
	formal_source = "\n".join(
		(method_source, supplement_source, decisions_source, outline_source),
	)

	assert "\\operatorname{Closed}_D(\\mathcal M_D)" in formal_source
	assert "\\operatorname{Closed}_D(\\mathcal L_D^{[k]})" in supplement_source
	assert "\\operatorname{Closed}_D(\\mathcal L_D^{[k+1]})" in supplement_source
	assert "\\mathcal M_D=\\operatorname*{lexargmin}" in method_source
	assert "\\mathcal L_D^{[0]}=\\mathcal M_D" in supplement_source

	for obsolete_notation in (
		"\\operatorname{head}",
		"\\operatorname{call}",
		"S^\\star",
		"S*",
		"\\kappa_S",
		"kappa_S",
		"call(S)",
		"head(S)",
	):
		assert obsolete_notation not in formal_source


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


def test_main_results_report_scientific_aggregates_not_run_bookkeeping() -> None:
	evaluation_source = (LATEX_ROOT / "sections/evaluation.tex").read_text(
		encoding="utf-8",
	)
	evaluation_text = " ".join(evaluation_source.split())
	supplement_source = (
		LATEX_ROOT / "sections/technical_appendix_content.tex"
	).read_text(encoding="utf-8")

	for engineering_detail in (
		"The five independently compiled atomic cores solve, for seeds 0--4",
		"\\AtomicSeedZeroSuccessCount{}",
		"with no timeout or nonzero exit",
		"Each seed runs with one internal worker",
		"pairing established by input fingerprints",
		"References receive 30 minutes and 8~GB per instance",
		"\\texttt{p12}",
		"\\texttt{p20}",
		"committed trace",
		"All 13 rejection and",
		"all 14 labelled and both initial-state cases",
	):
		assert engineering_detail not in evaluation_text

	for scientific_result in (
		"Across five independently compiled atomic cores",
		"Fourteen of the sixteen domains are complete",
		"Variation is concentrated in Logistics and Depots",
		"exact finite-trace language equivalence",
		"success requires Jason completion",
	):
		assert scientific_result in evaluation_text

	for archived_detail in (
		"There are no timeouts or nonzero exits",
		"Internal MOOSE workers",
		"Depots \\texttt{p12} and \\texttt{p20}",
		"Thirteen registered challenge cases all pass",
	):
		assert archived_detail in supplement_source


def test_manuscript_uses_one_canonical_formal_vocabulary() -> None:
	main_source = (LATEX_ROOT / "main.tex").read_text(encoding="utf-8")
	background_source = (LATEX_ROOT / "sections/background.tex").read_text(
		encoding="utf-8",
	)
	method_source = (LATEX_ROOT / "sections/method.tex").read_text(encoding="utf-8")
	supplement_source = (
		LATEX_ROOT / "sections/technical_appendix_content.tex"
	).read_text(encoding="utf-8")
	formal_source = "\n".join((background_source, method_source, supplement_source))

	assert "raw provider artifact $\\mathcal E_{\\mathrm{raw}}$" in method_source
	assert "\\mathcal C^{\\checkmark}_{D,E}" in method_source
	assert "\\mathfrak G" in method_source
	assert "\\operatorname{Inst}_D" in method_source
	assert "\\mathcal G_D^{\\mathrm{prod}}(T)" in method_source
	assert "\\mathfrak F_{D,E}" in method_source
	assert "\\operatorname{covers}_D(b,e)" in supplement_source
	assert "\\operatorname{realizes}_D(b,c)" in supplement_source
	assert (
		"\\tau_q=\\langle\\iota_q,\\varphi_q,\\mu_q,\\Theta_q,\\Gamma_q\\rangle"
		in method_source
	)
	assert "\\widehat\\tau_q=(\\tau_q,\\theta_q)" in method_source
	assert "\\theta_q:\\bar X_q\\rightarrow O_I" in method_source
	assert "I=\\langle D,O_I,s_I^0,G_I\\rangle" in background_source
	assert "\\mathcal D_q=" in method_source
	assert "\\mathcal O_\\chi=" in method_source
	assert "\\Pi_{\\chi,i}" in method_source
	assert "\\prec_\\chi" in method_source
	assert "\\boldsymbol\\ell_\\chi" in method_source
	assert "\\mathcal R_{q_s,\\chi}" in method_source
	assert "\\rho_b,\\kappa_{\\mathcal M},\\mathcal G_b^{\\mathrm{res}}" in (
		supplement_source
	)
	assert "\\mathit{val}_q" in formal_source
	assert "d_q(z)" in formal_source
	assert "\\mathcal W_{q_s},\\mathcal I_{q_s}" in supplement_source
	assert "\\rho_{\\mathrm{num}},b_\\chi^{\\mathrm{joint}}" in supplement_source
	assert "\\operatorname{Pass}_{q_s,\\chi}" in supplement_source
	assert "conditional module-completion summary" in formal_source
	assert "target-preserving resource discharge" in formal_source

	for ambiguous_term in (
		"provider output $A$",
		"$\\mathcal C_D^{\\checkmark}$",
		"Action Closure",
		"Maximal Certified",
		"Unprotected DFA",
		"Completion Monitor",
		"progress objective be",
		"Existential preparation projection",
		"Numeric and Whole-Guard Certificates",
		"Cyclic Threats and Enforced Portfolios",
		"schema closure",
		"PDDL schema construction",
		"schema-producer refinement",
		"completion portfolios",
		"observation-boundary assumption",
		"producer-exit obligation",
		"Feasible candidate family",
		"resource debt",
		"validation wrappers",
	):
		assert ambiguous_term not in formal_source

	assert "candidate-construction grammar" in main_source


def test_manuscript_contains_no_silently_unescaped_latex_commands() -> None:
	broken_command = re.compile(r"(?<!\\)(?:cite|texttt)\{")
	for source_path in _manuscript_sources():
		source = source_path.read_text(encoding="utf-8")
		assert broken_command.search(source) is None, source_path


def test_main_paper_states_the_complete_claim_boundary_in_one_limitations_section(
) -> None:
	main_source = (LATEX_ROOT / "main.tex").read_text(encoding="utf-8")
	evaluation_source = (LATEX_ROOT / "sections/evaluation.tex").read_text(
		encoding="utf-8",
	)
	combined = " ".join((main_source + evaluation_source).split())

	limitations_position = main_source.index(r"\section{Limitations}")
	conclusion_position = main_source.index(r"\section{Conclusion}")
	assert limitations_position < conclusion_position
	for required_boundary in (
		"only experimentally instantiated evidence provider",
		"candidate generation is incomplete",
		"type-compatible resolution",
		"witness-backed short-horizon queries",
		"controlled utterances",
		"fixed seed-0 atomic core",
		r"arbitrary PDDL--\ltlf{} strategy synthesis",
	):
		assert required_boundary in combined


def test_paired_result_inference_respects_the_atomic_case_cluster() -> None:
	evaluation_source = (LATEX_ROOT / "sections/evaluation.tex").read_text(
		encoding="utf-8",
	)
	supplement_source = (
		LATEX_ROOT / "sections/technical_appendix_content.tex"
	).read_text(encoding="utf-8")
	combined = " ".join((evaluation_source + supplement_source).split())

	assert "130 nonzero case-level differences" in combined
	assert r"1.47\times10^{-39}" in combined
	assert "five seeded outcomes for each held-out case identifier" in combined
	assert "case-level $p$-value" in combined
	assert r"p=\AtomicDirectToMaximumExactP{}" not in combined
	assert r"p=\TemporalUnprotectedToFlatExactP{}" not in combined


def test_evaluation_reports_costs_and_scope_without_unmeasured_amortization() -> None:
	evaluation_source = (LATEX_ROOT / "sections/evaluation.tex").read_text(
		encoding="utf-8",
	)
	evaluation_text = " ".join(evaluation_source.split())

	assert "amortized compilation" not in evaluation_text
	assert "10.42 percentage points" in evaluation_text
	assert "fivefold" in evaluation_text
	assert "113 of the 114 net temporal gains" in evaluation_text
	assert "720/740" in evaluation_text
	assert "117/740" in evaluation_text
