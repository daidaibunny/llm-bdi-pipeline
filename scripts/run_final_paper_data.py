#!/usr/bin/env python3
"""
Build the final paper data package for the domain-level ASL method.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
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
BLOCKS_VOCAB = "tmp/blocksworld-first20-experiment/learner-sketches-blocksworld-vocab.json"
MOOSE_BLOCKS_STATUS = ".external/moose/exact-runs/blocksworld-paper-params-probe/train-status.csv"


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
		"--config-only",
		action="store_true",
		help="Write final configs only; do not generate baselines or run matrices.",
	)
	args = parser.parse_args()

	output_dir = args.output_dir.expanduser().resolve()
	package = write_final_paper_configs(output_dir)
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
	print(
		"wrote final paper data package "
		f"{output_dir} reports={comparison['report_count']} "
		f"baselines={comparison['baseline_count']}",
	)


def write_final_paper_configs(output_dir: Path) -> dict[str, Path]:
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
				"name": "labworkflow-counterexample-refinement-final",
				"domain_file": "src/domains/labworkflow/domain.pddl",
				"train_problems": ["src/domains/labworkflow/problems/p01.pddl"],
				"eval_problems": [
					"src/domains/labworkflow/problems/p01.pddl",
					"src/domains/labworkflow/problems/p02.pddl",
				],
				"use_counterexample_refinement": True,
				"max_refinement_rounds": 1,
				"max_steps": 100,
				"max_depth": 50,
				"synthesis_profile": "bootstrap",
				"baseline_json": [
					str(output_dir / "baselines" / "labworkflow.json"),
				],
				"ablation_label": "labworkflow_counterexample_refinement",
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
				"name": "labworkflow-no-layer-c-no-refinement",
				"domain_file": "src/domains/labworkflow/domain.pddl",
				"train_problems": ["src/domains/labworkflow/problems/p01.pddl"],
				"eval_problems": [
					"src/domains/labworkflow/problems/p01.pddl",
					"src/domains/labworkflow/problems/p02.pddl",
				],
				"disabled_synthesis_mechanisms": ["layer_c_ordering"],
				"max_steps": 100,
				"max_depth": 50,
				"synthesis_profile": "bootstrap",
				"ablation_label": "no_layer_c_no_refinement_labworkflow",
			},
			{
				"name": "labworkflow-no-counterexample-refinement",
				"domain_file": "src/domains/labworkflow/domain.pddl",
				"train_problems": ["src/domains/labworkflow/problems/p01.pddl"],
				"eval_problems": [
					"src/domains/labworkflow/problems/p01.pddl",
					"src/domains/labworkflow/problems/p02.pddl",
				],
				"max_steps": 100,
				"max_depth": 50,
				"synthesis_profile": "bootstrap",
				"ablation_label": "no_counterexample_refinement_labworkflow",
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
				"name": "marsrover-bootstrap-train3-first10-scalability",
				"domain_file": "src/domains/marsrover/domain.pddl",
				"train_base": "src/domains/marsrover/problems",
				"train_glob": "pfile*.pddl",
				"train_count": 3,
				"eval_base": "src/domains/marsrover/problems",
				"eval_glob": "pfile*.pddl",
				"eval_count": 10,
				"max_steps": 20000,
				"max_depth": 2000,
				"timeout_seconds": 180,
				"evaluation_timeout_seconds": 5,
				"synthesis_profile": "bootstrap",
				"ablation_label": "marsrover_state_space_scalability_limit",
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
	lab_problems = (
		PROJECT_ROOT / "src/domains/labworkflow/problems/p01.pddl",
		PROJECT_ROOT / "src/domains/labworkflow/problems/p02.pddl",
	)
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
	macro_file = PROJECT_ROOT / "latex_code/aamas_method_paper/generated/results.tex"
	macro_file.parent.mkdir(parents=True, exist_ok=True)
	macro_file.write_text(macros, encoding="utf-8")
	return comparison


def _write_json(path: Path, data: object) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
	main()
