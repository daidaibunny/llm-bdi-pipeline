from __future__ import annotations

import json
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
	assert placements.count(("evaluation.tex", "t!")) == 0
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


def test_every_table_uses_the_full_htbp_placement_set() -> None:
	table_pattern = re.compile(
		r"\\begin\{(?P<environment>table\*?)\}"
		r"(?:\[(?P<placement>[^]]*)])?",
	)
	tables: list[tuple[str, str, str | None]] = []
	for source_path in _manuscript_sources():
		source = source_path.read_text(encoding="utf-8")
		tables.extend(
			(
				source_path.name,
				match.group("environment"),
				match.group("placement"),
			)
			for match in table_pattern.finditer(source)
		)

	assert tables
	assert all(placement == "htbp" for _, _, placement in tables), tables


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


def test_temporal_result_summary_is_prose_and_details_stay_in_supplement() -> None:
	evaluation_source = (LATEX_ROOT / "sections/evaluation.tex").read_text(
		encoding="utf-8",
	)
	supplement_source = (
		LATEX_ROOT / "sections/technical_appendix_content.tex"
	).read_text(encoding="utf-8")
	evaluation_text = " ".join(evaluation_source.split())
	assert "\\input{sections/result_temporal_summary_table}" not in evaluation_source
	assert (
		"controlled-language specifications are valid and DFA-language equivalent"
		in evaluation_text
	)
	assert "pass neutral-goal VAL and both DFA trace oracles" in evaluation_text
	assert "\\input{sections/result_profile_table}" not in evaluation_source
	assert "\\input{sections/result_profile_table}" in supplement_source
	assert "\\input{sections/result_domain_table}" not in evaluation_source
	assert "\\input{sections/result_domain_table}" in supplement_source


def test_result_floats_are_flushed_before_the_conclusion() -> None:
	main_source = (LATEX_ROOT / "main.tex").read_text(encoding="utf-8")

	barrier_position = main_source.index("\\FloatBarrier")
	conclusion_position = main_source.index(
		"\\section{Conclusion and Future Work}",
	)
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
		"$F(A\\land B)$",
		"$F(A\\land\\neg B)$",
		"$F(A\\land X(F(B)))$",
		"$F(A\\land X(F(B\\land X(F(C)))))$",
		"strong $A\\,U\\,B$",
		"one witness-backed query per held-out problem",
		"1,228 queries over 475 distinct translation inputs",
	):
		assert required_main_claim in evaluation_text
	for construction_detail in (
		"rollouts of at most three actions",
		"semantic-signature use",
		"symbol-independent tie-break",
		"it invokes no planner",
	):
		assert construction_detail not in evaluation_text

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
		"semantic-signature use",
		"spelling-independent SHA-256",
		"No classical or generalized planner is called",
	):
		assert required_supplement_contract in supplement_source

	assert "Rollout depth, event extraction, profile/signature balancing" in (
		outline_source
	)
	assert "belong\nonly in Technical Supplement, Sec. 4.1" in outline_source
	assert "Keep the frozen\nprompt in Sec. 4.2" in outline_source
	assert "PDDL provenance in Sec. 4.3" in outline_source


def test_manuscript_formalizes_ltlf_syntax_semantics_and_scope_boundaries() -> None:
	background_source = (LATEX_ROOT / "sections/background.tex").read_text(
		encoding="utf-8",
	)
	background_text = " ".join(background_source.split())
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
	assert "negation restricted to atoms" in background_text
	assert "signed transition obligation" in background_text
	assert "each cube as a separate conjunctive guard" not in background_text
	assert "explicit disjunction inside one guard" not in background_text
	for semantic_clause in (
		"\\xi,i\\models X\\varphi",
		"\\xi,i\\models F\\varphi",
		"\\xi,i\\models \\varphi U\\psi",
	):
		assert semantic_clause in supplement_source
	assert "a\\in\\mathit{val}_q(s)" in supplement_source
	assert "\\mu_q(a)=p(\\bar t)" in supplement_source
	assert "\\mu_q(a)=[f(\\bar t)=c]" in supplement_source


def test_main_and_supplement_use_the_approved_table_split() -> None:
	method_source = (LATEX_ROOT / "sections/method.tex").read_text(encoding="utf-8")
	evaluation_source = (LATEX_ROOT / "sections/evaluation.tex").read_text(
		encoding="utf-8",
	)
	supplement_source = (
		LATEX_ROOT / "sections/technical_appendix_content.tex"
	).read_text(encoding="utf-8")

	assert "\\label{tab:supported-fragment}" not in method_source
	assert "\\label{tab:compiler-obligations}" not in method_source
	assert "\\label{tab:supported-fragment}" in supplement_source
	assert "\\label{tab:compiler-obligations}" in supplement_source
	assert "\\input{sections/result_five_seed_atomic_table}" in evaluation_source
	assert "\\input{sections/result_profile_table}" not in evaluation_source
	assert "\\input{sections/result_moose_reference_table}" not in evaluation_source
	assert (
		"\\input{sections/result_same_scope_evidence_table}" in evaluation_source
	)
	assert "\\input{sections/result_external_reference_table}" not in (
		evaluation_source
	)
	assert "\\input{sections/result_five_seed_atomic_domain_table}" not in (
		evaluation_source
	)
	assert "\\input{sections/result_domain_table}" not in evaluation_source
	assert "\\input{sections/result_five_seed_atomic_domain_table}" in (
		supplement_source
	)
	assert "\\input{sections/result_domain_table}" in supplement_source
	assert "\\input{sections/result_profile_table}" in supplement_source
	assert "\\input{sections/result_moose_reference_table}" in supplement_source
	assert "\\input{sections/result_external_reference_table}" in supplement_source


def test_same_scope_evidence_table_matches_frozen_case_records() -> None:
	raw = json.loads(
		(
			PROJECT_ROOT
			/ "paper_artifacts/gp2pl_evaluation/v1/"
			"raw_moose_extension_five_seed_summary.json"
		).read_text(encoding="utf-8"),
	)
	paired = json.loads(
		(
			PROJECT_ROOT
			/ "paper_artifacts/gp2pl_evaluation/v1/paired_ablation_results.json"
		).read_text(encoding="utf-8"),
	)
	raw_records = tuple(raw["records"])
	raw_keys = {(int(record["seed"]), str(record["case_id"])) for record in raw_records}
	full_records = {
		(int(record["seed"]), str(record["case_id"])): record
		for record in paired["atomic_records"]
		if record["variant"] == "full"
	}
	assert len(raw_keys) == len(raw_records) == 740
	assert raw_keys <= set(full_records)

	raw_valid = int(raw["aggregate"]["pooled_valid_count"])
	full_valid = sum(bool(full_records[key]["valid"]) for key in raw_keys)
	table = (
		LATEX_ROOT / "sections/result_same_scope_evidence_table.tex"
	).read_text(encoding="utf-8")
	assert f"Raw MOOSE evidence & {raw_valid}/740 & 15.8" in table
	assert f"\\resultselected{{{full_valid}/740}}" in table
	assert "\\resultselected{Full GP2PL}" in table
	assert raw_valid == 117
	assert full_valid == 720


def test_main_paper_uses_overview_and_local_method_cases_without_result_figure() -> None:
	main_source = (LATEX_ROOT / "main.tex").read_text(encoding="utf-8")
	method_source = (LATEX_ROOT / "sections/method.tex").read_text(encoding="utf-8")
	evaluation_source = (LATEX_ROOT / "sections/evaluation.tex").read_text(
		encoding="utf-8",
	)

	assert (
		"\\providecommand{\\gpplfigureonepath}{figures/fig1_architecture.png}"
		in main_source
	)
	assert (
		"\\providecommand{\\gpplfiguretwopath}{figures/fig2_compiler_stages.pdf}"
		in main_source
	)
	assert (
		"\\providecommand{\\gpplatomiccasepath}{figures/fig3_atomic_case.pdf}"
		in main_source
	)
	assert "\\gppltemporalcasepath" not in main_source
	assert "fig4_temporal_case.pdf" not in main_source
	assert "\\gpplfigurethreepath" not in main_source
	assert r"\newcommand{\resultbest}[1]{\textbf{#1}}" in main_source
	assert r"\newcommand{\resultselected}[1]" in main_source
	figure_one_position = main_source.index("\\label{fig:architecture}")
	figure_two_position = main_source.index("\\label{fig:compiler-stages}")
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
	assert "\\IfFileExists{\\gpplatomiccasepath}" in method_source
	assert "\\label{fig:atomic-case}" in method_source
	assert "\\label{fig:temporal-case}" not in method_source
	assert "\\gpplfigurethreepath" not in evaluation_source
	assert "\\label{fig:evaluation-summary}" not in evaluation_source


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
	introduction_text = " ".join(introduction_source.split())

	assert "In Blocks World" in introduction_text
	assert introduction_source.index("Blocks World") < introduction_source.index(
		"\\texttt{on(X,Y)}",
	)
	assert "destination block is clear" in introduction_text
	assert "F(\\mathit{on}" not in introduction_text
	assert "GP2PL makes three contributions" in introduction_text
	for contribution_marker in (
		"it compiles singleton-goal evidence",
		"it accepts only branches",
		"it appends preservation-safe finite-trace controllers",
	):
		assert contribution_marker in introduction_text
	assert "policy evidence\ncontrollers" not in introduction_source


def test_generator_assisted_onboarding_is_bounded_by_the_existing_contract() -> None:
	main_source = (LATEX_ROOT / "main.tex").read_text(encoding="utf-8")
	main_text = " ".join(main_source.split())
	method_source = (LATEX_ROOT / "sections/method.tex").read_text(encoding="utf-8")
	supplement_source = (
		LATEX_ROOT / "sections/technical_appendix_content.tex"
	).read_text(encoding="utf-8")
	supplement_text = " ".join(supplement_source.split())
	outline_source = (
		PROJECT_ROOT / "docs" / "aaai_paper_narrative_outline.md"
	).read_text(encoding="utf-8")
	decisions_source = (
		PROJECT_ROOT / "docs" / "research_pipeline_decisions.md"
	).read_text(encoding="utf-8")

	assert "pinned PDDL generators" in main_text
	assert "held-out-disjoint instances" in main_text
	assert "scalable domain onboarding" in main_text
	assert "fail-closed certification" in main_text
	assert "An evidence provider is admissible" in method_source
	for reproducibility_requirement in (
		"generator revision and digest",
		"complete output",
		"content hashes must be disjoint",
		"held-out set must be sealed before evidence learning",
		"every compiler gate remains unchanged",
	):
		assert reproducibility_requirement in supplement_text
	assert "generator-assisted domain onboarding" in outline_source
	assert "pinned parameterized PDDL problem generator" in decisions_source


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
	assert (
		"\\ENSURE Certified lifted atomic module core $\\mathcal M_D$"
		in supplement_source
	)
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

	assert "\\subsection{Evidence Normalization and Canonical Lifting}" in method_source
	assert "E=\\operatorname{Lift}_D(E_0)" in method_source
	assert "Compile the Certified Lifted Atomic Module Core" in supplement_source
	assert "E_0\\leftarrow\\textsc{NormalizeEvidence}" in supplement_source
	assert "E\\leftarrow\\textsc{CanonicalLift}(E_0,D)" in supplement_source
	assert "\\textsc{LiftSchemas}" in method_source
	assert "definition}[Canonical lifting]" in supplement_source
	assert "preserves repeated-variable sharing" in method_source
	assert "preserves repeated-variable sharing" in supplement_source
	assert "constants declared by $D$ remain constants" in " ".join(
		supplement_source.split(),
	)
	assert "`E_0` is the provider-normalized evidence program" in decisions_source
	assert "`E = CanonicalLift_D(E_0)`" in decisions_source
	assert "`E = CanonicalLift_D(E_0)`" in outline_source


def test_main_method_retains_load_bearing_compiler_conditions() -> None:
	method_source = (LATEX_ROOT / "sections/method.tex").read_text(encoding="utf-8")
	method_text = " ".join(method_source.split())
	supplement_source = (
		LATEX_ROOT / "sections/technical_appendix_content.tex"
	).read_text(encoding="utf-8")
	supplement_text = " ".join(supplement_source.split())

	for finite_generation_condition in (
		"alpha-normalized regression state",
		"before repeating such a state",
		"without an arbitrary action-depth constant",
		"evidence macros are never truncated",
	):
		assert finite_generation_condition in method_text

	for coverage_condition in (
		"the same $\\mustadd$",
		"no additional $\\maydelete$",
		"equivalent numeric and keyed-resource summaries",
		"target-preserving resource-discharge alternative",
	):
		assert coverage_condition in method_text

	for joint_guard_condition in (
		"callable from every positive occurrence it establishes",
		"retains every query variable",
	):
		assert joint_guard_condition in method_text
		assert joint_guard_condition in supplement_text

	assert (
		"$\\rho_{\\mathrm{num}}="
		"\\langle n_{\\mathrm{miss}},d_{\\mathrm{target}}\\rangle$"
		in method_text
	)
	assert "common to every non-progress self-loop guard" in method_text


def test_figure_design_separates_high_level_stages_from_local_cases() -> None:
	main_source = (LATEX_ROOT / "main.tex").read_text(encoding="utf-8")
	method_source = (LATEX_ROOT / "sections/method.tex").read_text(encoding="utf-8")
	outline_source = (
		PROJECT_ROOT / "docs" / "aaai_paper_narrative_outline.md"
	).read_text(encoding="utf-8")

	assert "Figure 2: Inside the Two GP2PL Compiler Stages" in outline_source
	assert "Figure 3: Selected Atomic-Core Execution Case" in outline_source
	assert "Figure 4: Temporal Composition Case" not in outline_source
	normalized_outline = " ".join(outline_source.split())
	assert "producible target universe" in normalized_outline
	assert "`!clear(y) -> !clear(z)" in normalized_outline
	assert "selected variable-level fragments" in normalized_outline
	assert "$\\mathcal M_D=\\mathcal L_D^{[0]}$" in outline_source

	figure_two_caption = re.search(
		r"\\caption\{Inside the two GP2PL compiler stages(.*?)\}\s*"
		r"\\label\{fig:compiler-stages\}",
		main_source,
		re.DOTALL,
	)
	assert figure_two_caption is not None
	caption_text = " ".join(figure_two_caption.group(1).split())
	assert "query-independent" in caption_text
	assert "query-specific" in caption_text
	assert "MONA-derived conjunctive progress guard" in caption_text
	assert "balanced transition-repair tree" in caption_text
	assert "Blocks World" in method_source
	assert "\\texttt{clear/1} module recurs" in method_source
	assert "preservation-safe order" in method_source
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
	atomic_table_source = (
		LATEX_ROOT / "sections/result_five_seed_atomic_table.tex"
	).read_text(encoding="utf-8")
	evaluation_text = " ".join(
		(evaluation_source + atomic_table_source).split(),
	)
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
		"All-seed complete (14)",
		"Variation is confined to Logistics and Depots",
		"exact finite-trace language equivalence",
		"requires controller compilation, Jason completion",
	):
		assert scientific_result in evaluation_text

	for archived_detail in (
		"There are no timeouts or nonzero exits",
		"Internal MOOSE workers",
		"Depots \\texttt{p12} and \\texttt{p20}",
		"Thirteen registered challenge cases all pass",
	):
		assert archived_detail in supplement_source


def test_evaluation_protocol_facts_are_not_repeated_in_table_captions() -> None:
	evaluation_source = (LATEX_ROOT / "sections/evaluation.tex").read_text(
		encoding="utf-8",
	)
	table_sources = "\n".join(
		path.read_text(encoding="utf-8")
		for path in (
			LATEX_ROOT / "sections/result_atomic_comparison_table.tex",
			LATEX_ROOT / "sections/result_temporal_comparison_table.tex",
			LATEX_ROOT / "sections/result_same_scope_evidence_table.tex",
		)
	)
	evaluation_text = " ".join(evaluation_source.split())
	table_text = " ".join(table_sources.split())

	for required_protocol_fact in (
		"Atomic variants share each seed's evidence",
		"Temporal variants share the same atomic core, binding, and DFA",
		"Atomic success requires Jason completion and original-goal VAL",
		"Translation success requires exact finite-trace language equivalence",
		"Temporal success requires controller compilation, Jason completion",
		"all failures remain in the denominator",
	):
		assert required_protocol_fact in evaluation_text
	for duplicated_caption_fact in (
		"Valid requires Jason",
		"identical DFA, binding, and atomic-library inputs",
		"Query validity additionally requires controller compilation",
		"Every valid plan passes original-goal VAL",
	):
		assert duplicated_caption_fact not in table_text


def test_temporal_method_is_separated_from_evaluation_protocol() -> None:
	method_source = (LATEX_ROOT / "sections/method.tex").read_text(encoding="utf-8")
	evaluation_source = (LATEX_ROOT / "sections/evaluation.tex").read_text(
		encoding="utf-8",
	)
	temporal_method = method_source.split(
		"\\section{DFA-Guided Composition of Temporally Extended Goals}",
		maxsplit=1,
	)[1].split("\\section{Conditional Guarantees}", maxsplit=1)[0]
	temporal_text = " ".join(temporal_method.split())
	evaluation_text = " ".join(evaluation_source.split())

	for evaluation_only_term in (
		"Jason",
		"VAL",
		"released benchmark",
		"evaluation distribution",
		"direct linear rendering",
		"runtime binding",
	):
		assert evaluation_only_term not in temporal_text

	for required_method_term in (
		"preservation portfolio",
		"threat-induced precedence graph",
		"balanced binary transition-repair tree",
	):
		assert required_method_term in temporal_text

	for required_evaluation_term in (
		"Certified Flat",
		"Certified Balanced",
		"Module-Return Monitor",
		"Jason completion",
		"neutral-goal VAL",
	):
		assert required_evaluation_term in evaluation_text


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
	method_text = " ".join(method_source.split())

	assert "raw artifact $\\mathcal E_{\\mathrm{raw}}$" in method_text
	assert "\\mathcal C^{\\checkmark}_{D,E}" in method_source
	assert "\\mathfrak G" in method_source
	assert "\\operatorname{Inst}_D" in method_source
	assert "\\mathcal G_D^{\\mathrm{prod}}(T)" in method_source
	assert "\\mathfrak F_{D,E}" in method_source
	assert "\\operatorname{covers}_D(b,e)" in supplement_source
	assert "\\operatorname{realizes}_D(b,c)" in supplement_source
	assert (
		"\\tau_q=\\langle\\iota_q,\\varphi_q,\\mu_q,\\Theta_q,\\Gamma_q\\rangle"
		in supplement_source
	)
	assert "\\widehat\\tau_q=(\\tau_q,\\theta_q)" in supplement_source
	assert "\\theta_q:\\bar X_q\\rightarrow O_I" in supplement_source
	assert "I=\\langle D,O_I,s_I^0,G_I\\rangle" in background_source
	assert "\\mathcal D_q=" in supplement_source
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

	assert "candidate grammars" in main_source


def test_manuscript_contains_no_silently_unescaped_latex_commands() -> None:
	broken_command = re.compile(r"(?<!\\)(?:cite|texttt)\{")
	for source_path in _manuscript_sources():
		source = source_path.read_text(encoding="utf-8")
		assert broken_command.search(source) is None, source_path


def test_conclusion_and_future_work_states_the_supported_claim_boundary(
) -> None:
	main_source = (LATEX_ROOT / "main.tex").read_text(encoding="utf-8")
	evaluation_source = (LATEX_ROOT / "sections/evaluation.tex").read_text(
		encoding="utf-8",
	)
	combined = " ".join((main_source + evaluation_source).split())

	assert r"\section{Conclusion and Future Work}" in main_source
	assert r"\section{Limitations}" not in main_source
	assert r"\section{Conclusion}" not in main_source
	for required_boundary in (
		r"arbitrary PDDL--\ltlf{} strategy synthesis",
		"arithmetic outside the bounded-integer fragment",
		"formulae outside the declared",
		"uncertified recursive or interference repair",
		"pinned PDDL generators",
		"held-out-disjoint instances",
		"scalable domain onboarding",
	):
		assert required_boundary in combined


def test_paired_result_reporting_respects_the_atomic_case_cluster() -> None:
	evaluation_source = (LATEX_ROOT / "sections/evaluation.tex").read_text(
		encoding="utf-8",
	)
	supplement_source = (
		LATEX_ROOT / "sections/technical_appendix_content.tex"
	).read_text(encoding="utf-8")
	combined = " ".join((evaluation_source + supplement_source).split())

	assert "130 nonzero case-level differences" in combined
	assert r"1.47\times10^{-39}" not in combined
	assert "two-sided exact sign test" not in combined
	assert "five seeded outcomes within each identifier" in combined
	assert "held-out case identifiers under five evidence seeds" in combined
	assert "case-level $p$-value" in combined
	assert r"p=\AtomicDirectToMaximumExactP{}" not in combined
	assert r"p=\TemporalUnprotectedToFlatExactP{}" not in combined


def test_evaluation_reports_costs_and_scope_without_unmeasured_amortization() -> None:
	evaluation_source = (LATEX_ROOT / "sections/evaluation.tex").read_text(
		encoding="utf-8",
	)
	same_scope_table = (
		LATEX_ROOT / "sections/result_same_scope_evidence_table.tex"
	).read_text(encoding="utf-8")
	evaluation_text = " ".join((evaluation_source + same_scope_table).split())

	assert "amortized compilation" not in evaluation_text
	assert "10.42-percentage-point gain" in evaluation_text
	assert "9.28-percentage-point gain" in evaluation_text
	assert "720/740" in evaluation_text
	assert "117/740" in evaluation_text
