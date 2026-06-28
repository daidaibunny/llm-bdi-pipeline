#!/usr/bin/env python3
"""
Build the final paper data package for the domain-level ASL method.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from domain_level_planning.experiments import (  # noqa: E402
	compare_domain_level_experiment_reports,
	format_comparison_latex_macros,
)
from domain_level_planning.architecture_contract import (  # noqa: E402
	architecture_gap_summary,
	domain_level_architecture_contract,
)
from scripts.generate_domain_level_baselines import (  # noqa: E402
	generate_classical_planner_baseline,
	generate_external_sketch_audit_baseline,
	generate_moose_status_baseline,
)
from scripts.run_domain_level_experiment_matrix import run_experiment_matrix  # noqa: E402


BLOCKS_POLICY = (
	".external/gp-backends/learner-sketches/learning/"
	"workspace-2024-09-24-tractable/blocks_4_on_2/output/sketch_minimized_2.txt"
)
BLOCKS_VOCAB = (
	"src/benchmark_data/external_vocab/"
	"learner_sketches_blocksworld_blocks_4_on_2.json"
)
MOOSE_BLOCKS_STATUS = ".external/moose/exact-runs/blocksworld-paper-params-probe/train-status.csv"
FINAL_PAPER_MANIFEST = PROJECT_ROOT / "paper_artifacts/final_paper_manifest.json"
FINAL_RESULT_MACROS = PROJECT_ROOT / "latex_code/aamas_method_paper/sections/result_macros.tex"
FINAL_PAPER_MAIN = PROJECT_ROOT / "latex_code/aamas_method_paper/main.tex"
RESULT_MACRO_START = "% BEGIN GENERATED RESULT MACROS"
RESULT_MACRO_END = "% END GENERATED RESULT MACROS"
LABWORKFLOW_TRAIN_PROBLEMS = ["src/domains/labworkflow/problems/p01.pddl"]
LABWORKFLOW_STRESS_PROBLEMS = [
	"src/domains/labworkflow/problems/p02.pddl",
	"src/domains/labworkflow/problems/p03.pddl",
	"src/domains/labworkflow/problems/p04.pddl",
	"src/domains/labworkflow/problems/p05.pddl",
	"src/domains/labworkflow/problems/p06.pddl",
]


def main() -> None:
	"""Create configs, baselines, experiment reports, and LaTeX result macros."""

	parser = argparse.ArgumentParser(
		description="Run the final paper data protocol for the ASL library paper.",
	)
	parser.add_argument(
		"--output-dir",
		type=Path,
		default=Path("tmp/paper-final"),
	)
	parser.add_argument(
		"--fast-downward",
		type=Path,
		default=PROJECT_ROOT / "fast-downward" / "fast-downward.py",
	)
	parser.add_argument("--planner-timeout-seconds", type=int, default=60)
	parser.add_argument(
		"--manifest",
		type=Path,
		default=FINAL_PAPER_MANIFEST,
		help="Tracked final-paper artifact manifest to enforce during validation.",
	)
	parser.add_argument(
		"--config-only",
		action="store_true",
		help="Write final configs only; do not generate baselines or run matrices.",
	)
	parser.add_argument(
		"--validate-only",
		action="store_true",
		help="Validate an existing final paper data package and exit.",
	)
	args = parser.parse_args()

	output_dir = args.output_dir.expanduser().resolve()
	manifest = load_final_paper_manifest(args.manifest)
	if args.validate_only:
		validation = validate_final_paper_package(output_dir, manifest=manifest)
		print(
			"validated final paper data package "
			f"{output_dir} checks={validation['check_count']}",
		)
		return

	_reset_managed_output(output_dir)
	package = write_final_paper_configs(output_dir, manifest=manifest)
	if args.config_only:
		print(f"wrote final paper configs under {output_dir}")
		return

	_write_backend_audit_logs(output_dir / "backend-audit")
	_generate_final_baselines(
		output_dir=output_dir,
		fast_downward=args.fast_downward,
		planner_timeout_seconds=args.planner_timeout_seconds,
	)
	results = _run_final_matrices(output_dir=output_dir, package=package)
	comparison = _write_final_comparison(output_dir=output_dir, matrix_results=results)
	validate_final_paper_package(output_dir, manifest=manifest)
	print(
		"wrote final paper data package "
		f"{output_dir} reports={comparison['report_count']} "
		f"baselines={comparison['baseline_count']}",
	)


def load_final_paper_manifest(
	manifest_file: str | Path = FINAL_PAPER_MANIFEST,
) -> dict[str, object]:
	"""Load the tracked final-paper artifact contract."""

	manifest_path = Path(manifest_file).expanduser()
	if not manifest_path.is_absolute():
		manifest_path = PROJECT_ROOT / manifest_path
	if not manifest_path.exists():
		raise FileNotFoundError(f"missing final paper artifact manifest: {manifest_path}")
	manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
	if int(manifest.get("schema_version") or 0) != 1:
		raise ValueError(
			"unsupported final paper artifact manifest schema_version: "
			f"{manifest.get('schema_version')!r}",
		)
	return dict(manifest)


def validate_final_paper_package(
	output_dir: Path,
	*,
	macro_file: Path | None = None,
	manifest: dict[str, object] | None = None,
	manifest_file: str | Path | None = FINAL_PAPER_MANIFEST,
) -> dict[str, object]:
	"""Validate the already-generated final paper data package."""

	output_dir = output_dir.expanduser().resolve()
	if manifest is None and manifest_file is not None:
		manifest = load_final_paper_manifest(manifest_file)
	comparison_file = output_dir / "comparison.json"
	if not comparison_file.exists():
		raise FileNotFoundError(f"missing final comparison file: {comparison_file}")
	comparison = json.loads(comparison_file.read_text(encoding="utf-8"))
	rows = tuple(dict(row) for row in tuple(comparison.get("paper_table_rows") or ()))
	library_rows = tuple(row for row in rows if row.get("row_type") == "library")
	baseline_rows = tuple(row for row in rows if row.get("row_type") == "baseline")
	checks: list[str] = []

	def require(condition: bool, message: str) -> None:
		if not condition:
			raise ValueError(message)
		checks.append(message)

	require(int(comparison.get("report_count") or 0) > 0, "comparison has reports")
	require(int(comparison.get("baseline_count") or 0) > 0, "comparison has baselines")
	require(bool(library_rows), "comparison has library rows")
	require(bool(baseline_rows), "comparison has baseline rows")
	require(
		all(str(row.get("runtime_planner") or "") == "none" for row in library_rows),
		"library rows use no runtime full-trace planner",
	)

	strict_rows = tuple(
		row
		for row in library_rows
		if str(row.get("label") or "").startswith("paper_external_sketch_")
	)
	require(bool(strict_rows), "strict paper-profile rows exist")
	require(
		all(bool(row.get("paper_profile_ready")) for row in strict_rows),
		"strict rows are paper-profile ready",
	)
	require(
		all(float(row.get("coverage_percent") or 0.0) == 100.0 for row in strict_rows),
		"strict rows solve all evaluated problems",
	)
	require(
		any(float(row.get("coverage_percent") or 0.0) < 100.0 for row in library_rows),
		"ablation rows include a coverage drop",
	)
	library_rows_by_label = {
		str(row.get("label") or ""): row for row in library_rows
	}
	lab_stress = library_rows_by_label.get("labworkflow_counterexample_refinement_stress")
	no_layer_c_stress = library_rows_by_label.get(
		"no_layer_c_with_refinement_labworkflow_stress",
	)
	no_refinement_stress = library_rows_by_label.get(
		"no_counterexample_refinement_labworkflow_stress",
	)
	require(lab_stress is not None, "Labworkflow Layer C stress row exists")
	require(
		str(lab_stress.get("solved") or "") == "5/5",
		"Labworkflow Layer C stress row solves all five held-out problems",
	)
	require(no_layer_c_stress is not None, "No-Layer-C stress ablation row exists")
	require(
		float(no_layer_c_stress.get("coverage_percent") or 0.0)
		< float(lab_stress.get("coverage_percent") or 0.0),
		"No-Layer-C stress ablation drops coverage",
	)
	require(
		no_refinement_stress is not None,
		"No-counterexample-refinement stress ablation row exists",
	)
	require(
		float(no_refinement_stress.get("coverage_percent") or 0.0)
		< float(lab_stress.get("coverage_percent") or 0.0),
		"No-counterexample-refinement stress ablation drops coverage",
	)
	require(
		any(
			str(row.get("runtime_planner") or "") == "offline_baseline_only"
			for row in baseline_rows
		),
		"classical planner baseline is labelled offline only",
	)
	require(
		any(
			str(row.get("runtime_planner") or "") == "not_runtime_executed"
			for row in baseline_rows
		),
		"raw external policy audit baseline is not runtime executed",
	)
	require(
		any("domain-level" in str(row.get("notes") or "") for row in baseline_rows),
		"baseline rows state domain-level or non-domain-level semantics",
	)
	if manifest is not None:
		_validate_manifest_contract(
			manifest=manifest,
			output_dir=output_dir,
			comparison=comparison,
			rows=rows,
			library_rows=library_rows,
			baseline_rows=baseline_rows,
			require=require,
		)

	current_gap_summary = architecture_gap_summary(
		domain_level_architecture_contract().gaps,
	)
	report_files: list[Path] = []
	report_files_by_matrix: dict[str, set[Path]] = {}
	for matrix_name in ("main", "ablation", "limitation"):
		summary_file = output_dir / f"{matrix_name}-matrix" / "matrix-summary.json"
		require(summary_file.exists(), f"{matrix_name} matrix summary exists")
		summary = json.loads(summary_file.read_text(encoding="utf-8"))
		require(
			int(summary.get("experiment_count") or 0) > 0,
			f"{matrix_name} matrix has experiments",
		)
		require(
			int(summary.get("failed_count") or 0) == 0,
			f"{matrix_name} matrix has no failed rows",
		)
		require(
			int(summary.get("succeeded_count") or 0)
			== int(summary.get("experiment_count") or 0),
			f"{matrix_name} matrix all rows succeeded",
		)
		for index, row in enumerate(tuple(summary.get("rows") or ()), start=1):
			report_file = row.get("report_file")
			require(
				bool(report_file),
				f"{matrix_name} matrix row {index} records report file",
			)
			report_path = Path(str(report_file)).expanduser()
			if not report_path.is_absolute():
				report_path = output_dir / f"{matrix_name}-matrix" / report_path
			require(
				report_path.exists(),
				f"{matrix_name} matrix report exists: {report_path.name}",
			)
			resolved_report_path = report_path.resolve()
			report_files.append(resolved_report_path)
			report_files_by_matrix.setdefault(matrix_name, set()).add(resolved_report_path)
		actual_report_files = {
			path.resolve()
			for path in (output_dir / f"{matrix_name}-matrix").glob("*.json")
			if path.name not in {"comparison.json", "matrix-summary.json"}
		}
		require(
			actual_report_files == report_files_by_matrix.get(matrix_name, set()),
			f"{matrix_name} matrix has no stale report files",
		)

	require(bool(report_files), "matrix summaries expose report files")
	for report_file in tuple(dict.fromkeys(report_files)):
		report = json.loads(report_file.read_text(encoding="utf-8"))
		synthesis_report = dict(report.get("synthesis_report") or {})
		require(
			synthesis_report.get("architecture_gap_summary") == current_gap_summary,
			f"report architecture contract is current: {report_file.name}",
		)
		generated_output_audit = dict(report.get("generated_output_audit") or {})
		require(
			bool(generated_output_audit.get("passed")),
			f"generated output audit passed: {report_file.name}",
		)
		require(
			bool(dict(report.get("coverage") or {}).get("solved_count") is not None),
			f"report records coverage: {report_file.name}",
		)

	macro_file = (
		macro_file.expanduser().resolve()
		if macro_file is not None
		else FINAL_RESULT_MACROS
	)
	require(macro_file.exists(), "LaTeX result macro file exists")
	expected_macros = format_comparison_latex_macros(comparison)
	actual_macros = macro_file.read_text(encoding="utf-8")
	require(actual_macros == expected_macros, "LaTeX result macros match comparison")
	require(FINAL_PAPER_MAIN.exists(), "LaTeX main file exists")
	main_macro_block = _extract_result_macro_block(
		FINAL_PAPER_MAIN.read_text(encoding="utf-8"),
	)
	require(
		main_macro_block == expected_macros,
		"LaTeX main generated result macro block matches comparison",
	)
	return {
		"check_count": len(checks),
		"comparison_file": str(comparison_file),
		"macro_file": str(macro_file),
		"checks": checks,
	}


def _validate_manifest_contract(
	*,
	manifest: dict[str, object],
	output_dir: Path,
	comparison: dict[str, object],
	rows: tuple[dict[str, object], ...],
	library_rows: tuple[dict[str, object], ...],
	baseline_rows: tuple[dict[str, object], ...],
	require,
) -> None:
	"""Validate generated artifacts against the tracked paper manifest."""

	require(bool(manifest.get("artifact_id")), "artifact manifest has an id")
	require(
		int(manifest.get("schema_version") or 0) == 1,
		"artifact manifest schema is supported",
	)
	commands = dict(manifest.get("commands") or {})
	for command_name in ("generate", "validate", "tests", "paper"):
		require(
			bool(str(commands.get(command_name) or "").strip()),
			f"artifact manifest records {command_name} command",
		)
	resource_policy = dict(manifest.get("resource_policy") or {})
	require(
		resource_policy.get("library_runtime_full_trace_planner") is False,
		"artifact manifest forbids library runtime full-trace planning",
	)
	require(
		resource_policy.get("external_generalized_planning_requires_resource_guard")
		is True,
		"artifact manifest requires guarded external learner runs",
	)
	if "external_generalized_planning_memory_limit_gib" in resource_policy:
		require(
			float(resource_policy["external_generalized_planning_memory_limit_gib"])
			<= 16.0,
			"artifact manifest keeps external learner memory limit at or below 16GiB",
		)
	_validate_manifest_external_setup(manifest=manifest, require=require)

	output_policy = dict(manifest.get("generated_output_policy") or {})
	tracked_contract = str(output_policy.get("tracked_contract") or "").strip()
	if tracked_contract:
		require(
			not tracked_contract.startswith("tmp/"),
			"artifact contract is tracked outside tmp",
		)
		require(
			(PROJECT_ROOT / tracked_contract).exists(),
			"tracked artifact contract file exists",
		)
	tracked_result_macros = str(
		output_policy.get("tracked_result_macros") or "",
	).strip()
	if tracked_result_macros:
		require(
			not tracked_result_macros.startswith("tmp/"),
			"artifact result macros are tracked outside tmp",
		)
		require(
			(PROJECT_ROOT / tracked_result_macros).exists(),
			"tracked artifact result macro file exists",
		)
	for generated_path in tuple(output_policy.get("do_not_track_generated_dirs") or ()):
		require(
			str(generated_path).startswith("tmp/"),
			f"generated output remains under tmp: {generated_path}",
		)

	artifact_manifest_copy = output_dir / "artifact-manifest.json"
	require(
		artifact_manifest_copy.exists(),
		"generated package includes artifact manifest copy",
	)
	require(
		json.loads(artifact_manifest_copy.read_text(encoding="utf-8")) == manifest,
		"generated artifact manifest copy matches tracked manifest",
	)

	for input_record in tuple(manifest.get("required_repository_inputs") or ()):
		record = dict(input_record)
		raw_path = str(record.get("path") or "")
		require(bool(raw_path), "artifact manifest input records have paths")
		resolved = PROJECT_ROOT / raw_path
		if str(record.get("kind") or "file") == "directory":
			require(resolved.is_dir(), f"artifact input directory exists: {raw_path}")
		else:
			require(resolved.is_file(), f"artifact input file exists: {raw_path}")
		if bool(record.get("tracked")):
			require(
				not raw_path.startswith(("tmp/", ".external/")),
				f"tracked artifact input is not generated/external: {raw_path}",
			)

	expected_package = dict(manifest.get("expected_package") or {})
	if expected_package:
		require(
			int(comparison.get("report_count") or 0)
			== int(expected_package.get("report_count") or 0),
			"artifact manifest report count matches comparison",
		)
		require(
			int(comparison.get("baseline_count") or 0)
			== int(expected_package.get("baseline_count") or 0),
			"artifact manifest baseline count matches comparison",
		)
		require(
			len(rows) == int(expected_package.get("paper_table_row_count") or 0),
			"artifact manifest paper-table row count matches comparison",
		)

	_validate_manifest_matrix_configs(
		manifest=manifest,
		output_dir=output_dir,
		require=require,
	)
	_validate_manifest_expected_rows(
		manifest=manifest,
		library_rows=library_rows,
		baseline_rows=baseline_rows,
		require=require,
	)


def _validate_manifest_external_setup(
	*,
	manifest: dict[str, object],
	require,
) -> None:
	"""Validate the reproducibility contract for external paper artifacts."""

	external_setup = dict(manifest.get("external_setup") or {})
	require(bool(external_setup), "artifact manifest records external setup")
	commands = dict(external_setup.get("commands") or {})
	for command_name in (
		"backend_status",
		"learner_sketches_commands",
		"learner_sketches_summary",
	):
		require(
			bool(str(commands.get(command_name) or "").strip()),
			f"artifact manifest records external setup command: {command_name}",
		)
	resource_guarded_commands = tuple(
		str(command)
		for command in tuple(external_setup.get("resource_guarded_command_generators") or ())
	)
	require(
		any("resource_guard.py" in command for command in resource_guarded_commands),
		"artifact manifest records guarded external learner command generator",
	)

	for pin_record in tuple(external_setup.get("pinned_repositories") or ()):
		record = dict(pin_record)
		name = str(record.get("name") or "").strip()
		raw_path = str(record.get("path") or "").strip()
		expected_commit = str(record.get("commit") or "").strip()
		require(bool(name), "external setup pin records backend name")
		require(bool(raw_path), f"external setup pin records path: {name}")
		require(bool(expected_commit), f"external setup pin records commit: {name}")
		if not bool(record.get("validate_head", True)):
			continue
		repository_path = Path(raw_path).expanduser()
		if not repository_path.is_absolute():
			repository_path = PROJECT_ROOT / repository_path
		require(
			repository_path.is_dir(),
			f"external pinned repository exists: {name}",
		)
		try:
			current_commit = subprocess.check_output(
				("git", "-C", str(repository_path), "rev-parse", "HEAD"),
				text=True,
				stderr=subprocess.DEVNULL,
			).strip()
		except (OSError, subprocess.CalledProcessError) as error:
			raise ValueError(f"cannot read external pin {name}: {error}") from error
		require(
			current_commit == expected_commit,
			f"external pinned repository head matches manifest: {name}",
		)


def _validate_manifest_matrix_configs(
	*,
	manifest: dict[str, object],
	output_dir: Path,
	require,
) -> None:
	matrix_configs = dict(manifest.get("matrix_configs") or {})
	for matrix_key, matrix_contract in matrix_configs.items():
		contract = dict(matrix_contract)
		config_file = output_dir / str(contract.get("file") or "")
		require(
			config_file.exists(),
			f"artifact matrix config exists: {matrix_key}",
		)
		config = json.loads(config_file.read_text(encoding="utf-8"))
		require(
			config.get("matrix_name") == contract.get("matrix_name"),
			f"artifact matrix name matches manifest: {matrix_key}",
		)
		expected_experiments = tuple(str(name) for name in contract.get("experiments") or ())
		actual_experiments = tuple(
			str(row.get("name") or "")
			for row in tuple(config.get("experiments") or ())
		)
		require(
			actual_experiments == expected_experiments,
			f"artifact matrix experiment order matches manifest: {matrix_key}",
		)


def _validate_manifest_expected_rows(
	*,
	manifest: dict[str, object],
	library_rows: tuple[dict[str, object], ...],
	baseline_rows: tuple[dict[str, object], ...],
	require,
) -> None:
	library_by_label = {
		str(row.get("label") or ""): row for row in library_rows
	}
	for expected_row in tuple(manifest.get("expected_library_rows") or ()):
		expected = dict(expected_row)
		label = str(expected.get("label") or "")
		require(label in library_by_label, f"expected library row exists: {label}")
		_actual_row_matches_expected(
			actual=library_by_label[label],
			expected=expected,
			row_name=label,
			require=require,
		)

	baseline_by_macro = {
		str(row.get("macro_id") or ""): row for row in baseline_rows
	}
	for expected_row in tuple(manifest.get("expected_baseline_rows") or ()):
		expected = dict(expected_row)
		macro_id = str(expected.get("macro_id") or "")
		require(macro_id in baseline_by_macro, f"expected baseline row exists: {macro_id}")
		_actual_row_matches_expected(
			actual=baseline_by_macro[macro_id],
			expected=expected,
			row_name=macro_id,
			require=require,
		)


def _actual_row_matches_expected(
	*,
	actual: dict[str, object],
	expected: dict[str, object],
	row_name: str,
	require,
) -> None:
	for key, expected_value in expected.items():
		if key in {"label", "macro_id"}:
			continue
		actual_value = actual.get(key)
		if isinstance(expected_value, float):
			require(
				abs(float(actual_value or 0.0) - expected_value) < 0.0001,
				f"artifact row {row_name} field {key} matches manifest",
			)
		else:
			require(
				actual_value == expected_value,
				f"artifact row {row_name} field {key} matches manifest",
			)


def _extract_result_macro_block(main_tex: str) -> str:
	"""Extract generated result macros embedded in the paper source."""

	start_index = main_tex.find(RESULT_MACRO_START)
	end_index = main_tex.find(RESULT_MACRO_END)
	if start_index < 0 or end_index < 0 or end_index <= start_index:
		raise ValueError("missing generated result macro block in LaTeX main file")
	block_start = start_index + len(RESULT_MACRO_START)
	return main_tex[block_start:end_index].strip() + "\n"


def _replace_result_macro_block(main_tex: str, macros: str) -> str:
	"""Replace the generated result macro block in the paper source."""

	start_index = main_tex.find(RESULT_MACRO_START)
	end_index = main_tex.find(RESULT_MACRO_END)
	if start_index < 0 or end_index < 0 or end_index <= start_index:
		raise ValueError("missing generated result macro block in LaTeX main file")
	replacement = (
		f"{RESULT_MACRO_START}\n"
		f"{macros.rstrip()}\n"
		f"{RESULT_MACRO_END}"
	)
	return (
		main_tex[:start_index]
		+ replacement
		+ main_tex[end_index + len(RESULT_MACRO_END):]
	)


def _reset_managed_output(output_dir: Path) -> None:
	"""Remove generated final-package paths before a fresh non-validate run."""

	for relative_path in (
		"backend-audit",
		"baseline-work",
		"baselines",
		"configs",
		"main-matrix",
		"ablation-matrix",
		"limitation-matrix",
	):
		path = output_dir / relative_path
		if path.exists():
			shutil.rmtree(path)
	comparison_file = output_dir / "comparison.json"
	if comparison_file.exists():
		comparison_file.unlink()
	manifest_file = output_dir / "artifact-manifest.json"
	if manifest_file.exists():
		manifest_file.unlink()


def write_final_paper_configs(
	output_dir: Path,
	*,
	manifest: dict[str, object] | None = None,
) -> dict[str, Path]:
	"""Write fixed final matrix configs and return their paths."""

	config_dir = output_dir / "configs"
	config_dir.mkdir(parents=True, exist_ok=True)
	configs = {
		"main": config_dir / "main-library-matrix.json",
		"ablation": config_dir / "ablation-matrix.json",
		"limitation": config_dir / "limitation-matrix.json",
	}
	_write_json(configs["main"], _main_library_config(output_dir))
	_write_json(configs["ablation"], _ablation_config(output_dir))
	_write_json(configs["limitation"], _limitation_config(output_dir))
	if manifest is not None:
		_write_json(output_dir / "artifact-manifest.json", manifest)
	return configs


def _main_library_config(output_dir: Path) -> dict[str, object]:
	return {
		"matrix_name": "paper-final-main-library",
		"experiments": [
			_blocksworld_paper_row(
				name="blocksworld-paper-external-on2-first20",
				eval_base="src/domains/blocksworld/problems",
				eval_count=20,
				max_steps=10000,
				max_depth=1000,
				timeout_seconds=180,
				evaluation_timeout_seconds=15,
				ablation_label="paper_external_sketch_first20",
				baseline_json=output_dir / "baselines" / "blocksworld-first20.json",
			),
			_blocksworld_paper_row(
				name="blocksworld-paper-external-on2-satisfiable-large",
				eval_base="src/domains/blocksworld/satisfiable-large",
				eval_count=10,
				max_steps=30000,
				max_depth=3000,
				timeout_seconds=900,
				evaluation_timeout_seconds=120,
				ablation_label="paper_external_sketch_satisfiable_large",
				baseline_json=output_dir / "baselines" / "blocksworld-satisfiable-large.json",
			),
			_blocksworld_paper_row(
				name="blocksworld-paper-external-on2-satisfiable-mixed-large",
				eval_base="src/domains/blocksworld/satisfiable-mixed-large",
				eval_count=10,
				max_steps=40000,
				max_depth=4000,
				timeout_seconds=1200,
				evaluation_timeout_seconds=60,
				ablation_label="paper_external_sketch_satisfiable_mixed_large",
				baseline_json=(
					output_dir / "baselines" / "blocksworld-satisfiable-mixed-large.json"
				),
			),
			{
				"name": "labworkflow-counterexample-refinement-stress",
				"domain_file": "src/domains/labworkflow/domain.pddl",
				"train_problems": LABWORKFLOW_TRAIN_PROBLEMS,
				"eval_problems": LABWORKFLOW_STRESS_PROBLEMS,
				"use_counterexample_refinement": True,
				"max_refinement_rounds": 1,
				"max_steps": 500,
				"max_depth": 100,
				"synthesis_profile": "bootstrap",
				"baseline_json": [
					str(output_dir / "baselines" / "labworkflow.json"),
				],
				"ablation_label": "labworkflow_counterexample_refinement_stress",
			},
		],
	}


def _ablation_config(output_dir: Path) -> dict[str, object]:
	return {
		"matrix_name": "paper-final-ablations",
		"experiments": [
			{
				"name": "blocksworld-no-external-sketch-first20",
				"domain_file": "src/domains/blocksworld/domain.pddl",
				"train_base": "src/domains/blocksworld/problems",
				"train_glob": "p*.pddl",
				"train_count": 1,
				"eval_base": "src/domains/blocksworld/problems",
				"eval_glob": "p*.pddl",
				"eval_count": 20,
				"timeout_seconds": 180,
				"synthesis_profile": "bootstrap",
				"ablation_label": "no_external_sketch_first20",
			},
			{
				"name": "labworkflow-no-layer-c-with-refinement-stress",
				"domain_file": "src/domains/labworkflow/domain.pddl",
				"train_problems": LABWORKFLOW_TRAIN_PROBLEMS,
				"eval_problems": LABWORKFLOW_STRESS_PROBLEMS,
				"use_counterexample_refinement": True,
				"max_refinement_rounds": 1,
				"disabled_synthesis_mechanisms": ["layer_c_ordering"],
				"max_steps": 500,
				"max_depth": 100,
				"synthesis_profile": "bootstrap",
				"ablation_label": "no_layer_c_with_refinement_labworkflow_stress",
			},
			{
				"name": "labworkflow-no-counterexample-refinement-stress",
				"domain_file": "src/domains/labworkflow/domain.pddl",
				"train_problems": LABWORKFLOW_TRAIN_PROBLEMS,
				"eval_problems": LABWORKFLOW_STRESS_PROBLEMS,
				"max_steps": 500,
				"max_depth": 100,
				"synthesis_profile": "bootstrap",
				"ablation_label": "no_counterexample_refinement_labworkflow_stress",
			},
			{
				"name": "transport-no-offline-trace-evidence-first10",
				"domain_file": "src/domains/transport/domain.pddl",
				"train_base": "src/domains/transport/problems",
				"train_glob": "pfile*.pddl",
				"train_count": 3,
				"eval_base": "src/domains/transport/problems",
				"eval_glob": "pfile*.pddl",
				"eval_count": 10,
				"max_steps": 20000,
				"max_depth": 2000,
				"timeout_seconds": 180,
				"evaluation_timeout_seconds": 5,
				"synthesis_profile": "bootstrap",
				"ablation_label": "no_offline_trace_evidence_transport",
			},
		],
	}


def _limitation_config(output_dir: Path) -> dict[str, object]:
	return {
		"matrix_name": "paper-final-limitations",
		"experiments": [
			{
				"name": "transport-bootstrap-train3-first10-limitation",
				"domain_file": "src/domains/transport/domain.pddl",
				"train_base": "src/domains/transport/problems",
				"train_glob": "pfile*.pddl",
				"train_count": 3,
				"eval_base": "src/domains/transport/problems",
				"eval_glob": "pfile*.pddl",
				"eval_count": 10,
				"max_steps": 20000,
				"max_depth": 2000,
				"timeout_seconds": 180,
				"evaluation_timeout_seconds": 5,
				"use_synthesis_planner_traces": True,
				"synthesis_planner_executable": "fast-downward/fast-downward.py",
				"synthesis_planner_timeout_seconds": 60,
				"synthesis_profile": "bootstrap",
				"ablation_label": "transport_initial_state_fragment",
			},
			{
				"name": "marsrover-trace-evidence-train1-first10",
				"domain_file": "src/domains/marsrover/domain.pddl",
				"train_base": "src/domains/marsrover/problems",
				"train_glob": "pfile*.pddl",
				"train_count": 1,
				"eval_base": "src/domains/marsrover/problems",
				"eval_glob": "pfile*.pddl",
				"eval_count": 10,
				"max_steps": 1000,
				"max_depth": 200,
				"timeout_seconds": 180,
				"evaluation_timeout_seconds": 15,
				"use_synthesis_planner_traces": True,
				"synthesis_planner_executable": (
					".external/gp-backends/h-policy-learner/testing/planners/"
					"lama/fast-downward/fast-downward.py"
				),
				"synthesis_planner_timeout_seconds": 60,
				"synthesis_profile": "bootstrap",
				"ablation_label": "marsrover_trace_evidence_fragment",
			},
		],
	}


def _blocksworld_paper_row(
	*,
	name: str,
	eval_base: str,
	eval_count: int,
	max_steps: int,
	max_depth: int,
	timeout_seconds: int,
	evaluation_timeout_seconds: int,
	ablation_label: str,
	baseline_json: Path,
) -> dict[str, object]:
	return {
		"name": name,
		"domain_file": "src/domains/blocksworld/domain.pddl",
		"train_base": "src/domains/blocksworld/problems",
		"train_glob": "p*.pddl",
		"train_count": 1,
		"eval_base": eval_base,
		"eval_glob": "p*.pddl",
		"eval_count": eval_count,
		"max_steps": max_steps,
		"max_depth": max_depth,
		"timeout_seconds": timeout_seconds,
		"evaluation_timeout_seconds": evaluation_timeout_seconds,
		"synthesis_profile": "paper",
		"external_sketch_policies": [f"blocks_4_on_2={BLOCKS_POLICY}"],
		"external_sketch_vocabularies": [f"blocks_4_on_2={BLOCKS_VOCAB}"],
		"baseline_json": [str(baseline_json)],
		"ablation_label": ablation_label,
	}


def _generate_final_baselines(
	*,
	output_dir: Path,
	fast_downward: Path,
	planner_timeout_seconds: int,
) -> None:
	baseline_dir = output_dir / "baselines"
	baseline_dir.mkdir(parents=True, exist_ok=True)
	_generate_blocksworld_baseline(
		output_file=baseline_dir / "blocksworld-first20.json",
		eval_base=PROJECT_ROOT / "src/domains/blocksworld/problems",
		eval_count=20,
		fast_downward=fast_downward,
		planner_timeout_seconds=planner_timeout_seconds,
		work_dir=output_dir / "baseline-work/blocksworld-first20",
	)
	_generate_blocksworld_baseline(
		output_file=baseline_dir / "blocksworld-satisfiable-large.json",
		eval_base=PROJECT_ROOT / "src/domains/blocksworld/satisfiable-large",
		eval_count=10,
		fast_downward=fast_downward,
		planner_timeout_seconds=planner_timeout_seconds,
		work_dir=output_dir / "baseline-work/blocksworld-satisfiable-large",
	)
	_generate_blocksworld_baseline(
		output_file=baseline_dir / "blocksworld-satisfiable-mixed-large.json",
		eval_base=PROJECT_ROOT / "src/domains/blocksworld/satisfiable-mixed-large",
		eval_count=10,
		fast_downward=fast_downward,
		planner_timeout_seconds=planner_timeout_seconds,
		work_dir=output_dir / "baseline-work/blocksworld-satisfiable-mixed-large",
	)
	lab_problems = tuple(PROJECT_ROOT / path for path in LABWORKFLOW_STRESS_PROBLEMS)
	_write_json(
		baseline_dir / "labworkflow.json",
		[
			generate_classical_planner_baseline(
				domain_file=PROJECT_ROOT / "src/domains/labworkflow/domain.pddl",
				problem_files=lab_problems,
				planner_executable=fast_downward,
				timeout_seconds=planner_timeout_seconds,
				work_dir=output_dir / "baseline-work/labworkflow",
			),
		],
	)


def _generate_blocksworld_baseline(
	*,
	output_file: Path,
	eval_base: Path,
	eval_count: int,
	fast_downward: Path,
	planner_timeout_seconds: int,
	work_dir: Path,
) -> None:
	problem_files = tuple(sorted(eval_base.glob("p*.pddl")))[:eval_count]
	records = [
		generate_classical_planner_baseline(
			domain_file=PROJECT_ROOT / "src/domains/blocksworld/domain.pddl",
			problem_files=problem_files,
			planner_executable=fast_downward,
			timeout_seconds=planner_timeout_seconds,
			work_dir=work_dir,
		),
		generate_external_sketch_audit_baseline(
			domain_file=PROJECT_ROOT / "src/domains/blocksworld/domain.pddl",
			problem_count=len(problem_files),
			source_name="blocks_4_on_2",
			policy_file=PROJECT_ROOT / BLOCKS_POLICY,
			vocabulary_file=PROJECT_ROOT / BLOCKS_VOCAB,
		),
		generate_moose_status_baseline(
			label="blocksworld_moose_paper_params_probe",
			status_file=PROJECT_ROOT / MOOSE_BLOCKS_STATUS,
		),
	]
	_write_json(output_file, records)


def _write_backend_audit_logs(output_dir: Path) -> None:
	output_dir.mkdir(parents=True, exist_ok=True)
	for name, command in {
		"gp-backend-status.txt": (
			sys.executable,
			"scripts/gp_backend_audit.py",
			"status",
		),
		"learner-sketches-summary.txt": (
			sys.executable,
			"scripts/gp_backend_audit.py",
			"learner-sketches-summary",
			"--experiment",
			"all",
		),
	}.items():
		completed = subprocess.run(
			command,
			cwd=PROJECT_ROOT,
			check=False,
			capture_output=True,
			text=True,
		)
		(output_dir / name).write_text(
			completed.stdout + completed.stderr,
			encoding="utf-8",
		)


def _run_final_matrices(
	*,
	output_dir: Path,
	package: dict[str, Path],
) -> dict[str, dict[str, object]]:
	results: dict[str, dict[str, object]] = {}
	for name, config_file in package.items():
		config = json.loads(config_file.read_text(encoding="utf-8"))
		results[name] = run_experiment_matrix(
			config=config,
			config_base=PROJECT_ROOT,
			output_dir=output_dir / f"{name}-matrix",
			continue_on_error=True,
		)
	return results


def _write_final_comparison(
	*,
	output_dir: Path,
	matrix_results: dict[str, dict[str, object]],
) -> dict[str, object]:
	reports = []
	for summary in matrix_results.values():
		for row in tuple(summary.get("rows") or ()):
			report_file = row.get("report_file")
			if report_file:
				reports.append(json.loads(Path(str(report_file)).read_text(encoding="utf-8")))
	comparison = compare_domain_level_experiment_reports(reports)
	_write_json(output_dir / "comparison.json", comparison)
	macros = format_comparison_latex_macros(comparison)
	macro_file = FINAL_RESULT_MACROS
	macro_file.parent.mkdir(parents=True, exist_ok=True)
	macro_file.write_text(macros, encoding="utf-8")
	main_tex = FINAL_PAPER_MAIN.read_text(encoding="utf-8")
	FINAL_PAPER_MAIN.write_text(
		_replace_result_macro_block(main_tex, macros),
		encoding="utf-8",
	)
	return comparison


def _write_json(path: Path, data: object) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
	main()
