"""
Adapters for external generalized-planning learner backends.

These adapters keep paper code outside the main source tree while giving the
pipeline reproducible commands and parseable sketch outputs.
"""

from __future__ import annotations

import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence


DEFAULT_BACKEND_ROOT = Path(__file__).resolve().parents[2] / ".external" / "gp-backends"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_EXTERNAL_ROOT = PROJECT_ROOT / ".external"
DEFAULT_MAX_RSS_GB = 16.0
DEFAULT_POLL_SECONDS = 5.0

MOOSE_BACKEND = {
	"name": "moose",
	"url": "https://github.com/DillonZChen/moose.git",
	"commit": "ce1e99bc12e9c839c5e8e870aac878fd5d31cf9e",
	"path": PROJECT_EXTERNAL_ROOT / "moose",
}

PINNED_BACKENDS = (
	{
		"name": "learner-sketches",
		"url": "https://github.com/bonetblai/learner-sketches.git",
		"commit": "7a7ea6a6356035afa16ed958b53d8edc86994e0a",
	},
	{
		"name": "h-policy-learner",
		"url": "https://github.com/drexlerd/h-policy-learner.git",
		"commit": "03e345537208ab804c1f4958bf183b65d4863a62",
	},
	{
		"name": "d2l",
		"url": "https://github.com/rleap-project/d2l.git",
		"commit": "0620e169c894d79b3c84f435dba1462996f7c270",
	},
	{
		"name": "learner-policies-from-examples",
		"url": "https://github.com/bonetblai/learner-policies-from-examples.git",
		"commit": "9991926f7655c4b6c8dc2f0404123639e42056f2",
	},
	{
		"name": "pg3",
		"url": "https://github.com/ryangpeixu/pg3.git",
		"commit": "61496456c89ebccc66ba83679ba0e363232f6ac0",
	},
	{
		"name": "mimir-rgnn",
		"url": "https://github.com/simon-stahlberg/mimir-rgnn.git",
		"commit": "ea3089713c18ab1d7faf1a7f5ecddb4f5acdcbab",
	},
	{
		"name": "best-first-generalized-planning",
		"url": "https://github.com/rleap-project/best-first-generalized-planning.git",
		"commit": "7641bc46670c180f70cb3aca035a0459fc117554",
	},
	{
		"name": "bfgp-pp",
		"url": "https://github.com/jsego/bfgp-pp.git",
		"commit": "e913a3455030fac623c38df016fb3ce36999440c",
	},
	{
		"name": "pgp-landmarks",
		"url": "https://github.com/aig-upf/pgp-landmarks.git",
		"commit": "33e45fb647d1fde5a0e6c33a0935bf4cca2bc5ed",
	},
	{
		"name": "sltp",
		"url": "https://github.com/aig-upf/sltp.git",
		"commit": "f66d82cb684f02ff72600f07b4f3423716bc671f",
	},
	{
		"name": "up-bfgp",
		"url": "https://github.com/aiplan4eu/up-bfgp.git",
		"commit": "704fffb5da8d62fdcaca34606dca30497b5ef63f",
	},
	{
		"name": "llm-genplan",
		"url": "https://github.com/tomsilver/llm-genplan.git",
		"commit": "a2b8baa7153d5a8f2df51fbc72c51def80ddc169",
	},
	{
		"name": "state-centric-gen-planning",
		"url": "https://github.com/ai4society/state-centric-gen-planning.git",
		"commit": "03a61f587ea5a2745192225a1d0be19ca045a774",
	},
	{
		"name": "ipc-learning-huzar",
		"url": "https://github.com/ipc2023-learning/repo01.git",
		"commit": "29c09b57364721a8444fa9fabd22ecd0f3eae1ff",
	},
	{
		"name": "ipc-learning-pgp-baseline",
		"url": "https://github.com/ipc2023-learning/baseline02.git",
		"commit": "95a2d734f06ca58b6edfc6fad756519c67311445",
	},
)

AUDIT_ONLY_CONSUMPTION_ROLE = {
	"drives_atomic_templates": False,
	"drives_temporal_wrapper": False,
	"consumed_by_atomic_library": False,
	"consumption_mode": "audit_or_baseline_only",
	"blocking_gap": "no_verified_lifted_policy_program_adapter",
}

ATOMIC_COMPILER_PENDING_CONSUMPTION_ROLE = {
	"drives_atomic_templates": False,
	"drives_temporal_wrapper": False,
	"consumed_by_atomic_library": False,
	"consumption_mode": "candidate_policy_artifact_pending_atomic_asl_compiler",
	"blocking_gap": "no_verified_atomic_literal_asl_compiler_for_this_backend",
}

CAPABILITY_EXACT_REPRODUCTION_READY = "confirmed_exact_reproduction_ready"
CAPABILITY_PAPER_SOURCE_COMPLETE = "confirmed_paper_source_complete"
CAPABILITY_SOURCE_COMPLETE_NEEDS_ENVIRONMENT = (
	"confirmed_source_complete_needs_paper_environment"
)
CAPABILITY_LIBRARY_OR_INTERFACE_ONLY = "confirmed_library_or_interface_only"
CAPABILITY_COMPETITION_ARTIFACT_ONLY = "confirmed_competition_artifact_only"

BACKEND_RESEARCH_PROFILES = {
	"moose": {
		"paper_role": "AAAI 2026 goal-regression generalized planner",
		"preferred_use": (
			"primary backend candidate for positive singleton atomic predicate "
			"template generation"
		),
		"input_artifacts": (
			"PDDL domain",
			"training PDDL problems from the benchmark directory",
			"optional planner/search configuration",
		),
		"output_artifacts": (
			"first_order_decision_list_model",
			"readable_decision_list_policy",
			"policy_execution_plans",
			"optional_search_pruned_plans",
		),
		"reusable_evidence": (
			"atomic singleton-goal regression policy",
			"readable MOOSE policy adapter to LiftedPolicyProgram",
			"goal independence diagnostics",
			"validated policy-execution coverage",
		),
		"known_failure_modes": (
			"missing_backend",
			"missing_apptainer_image",
			"goal_dependency_not_goal_regression_friendly",
		),
		"resource_profile": {
			"execution_environment": (
				"Docker linux/amd64 wrapper plus Apptainer image; use VAL for "
				"policy-execution plan validation"
			),
			"default_max_rss_gb": DEFAULT_MAX_RSS_GB,
			"guard_required": True,
		},
		"usage_entrypoints": (
			"./moose.sif train benchmarks/<domain>/domain.pddl",
			"./moose.sif plan <domain>.model benchmarks/<domain>/domain.pddl benchmarks/<domain>/testing/<problem>.pddl",
			"./moose.sif plan <domain>.model benchmarks/<domain>/domain.pddl benchmarks/<domain>/testing/<problem>.pddl --search symk",
			"use the Docker/Apptainer pattern in AGENTS.md for local reproducibility",
		),
		"paper_code_capability": {
			"status": CAPABILITY_EXACT_REPRODUCTION_READY,
			"basis": (
				"official repository is pinned",
				"local Apptainer image, dataset, and VAL integration are present",
				"Ferry paper reproduction has already been VAL-validated locally",
			),
			"reproduction_gap": (
				"full-paper synthesis under the original 32GB and 12h budget is "
				"not re-run by the lightweight audit command",
			),
		},
		"current_consumption_role": {
			"drives_atomic_templates": True,
			"drives_temporal_wrapper": False,
			"consumed_by_atomic_library": True,
			"consumption_mode": "moose_readable_policy_atomic_templates",
			"blocking_gap": None,
		},
	},
	"learner-sketches": {
		"paper_role": "serialized-width sketch learner for qualitative DLPlan policies",
		"preferred_use": (
			"candidate external sketch backend; current repository parses and "
			"summarizes policies but does not compile them into atomic ASL"
		),
		"input_artifacts": (
			"PDDL domain",
			"training PDDL problems",
			"width bound",
		),
		"output_artifacts": (
			"feature_rule_policy",
			"raw_policy",
			"minimized_policy",
		),
		"reusable_evidence": (
			"qualitative sketch-policy representation",
			"DLPlan feature vocabulary",
			"qualitative feature conditions and effects",
		),
		"known_failure_modes": (
			"no_verified_atomic_literal_asl_compiler",
			"vocabulary_mismatch",
			"missing_policy_artifact",
		),
		"resource_profile": {
			"execution_environment": "local Python with resource_guard.py",
			"default_max_rss_gb": DEFAULT_MAX_RSS_GB,
			"guard_required": True,
		},
		"usage_entrypoints": (
			"uv run python scripts/gp_backend_audit.py install-deps",
			"uv run python scripts/gp_backend_audit.py learner-sketches-command --experiment <experiment> --timeout-seconds 1800",
			"uv run python scripts/gp_backend_audit.py learner-sketches-summary --experiment <experiment>",
		),
		"paper_code_capability": {
			"status": CAPABILITY_PAPER_SOURCE_COMPLETE,
			"basis": (
				"official repository is pinned",
				"learning entrypoint and benchmark folders are present",
				"README provides learning and testing experiment scripts",
			),
			"reproduction_gap": (
				"full ICAPS learning and testing tables have not been re-run in "
				"this lightweight audit",
			),
		},
		"current_consumption_role": ATOMIC_COMPILER_PENDING_CONSUMPTION_ROLE,
	},
	"h-policy-learner": {
		"paper_role": "hierarchical policy learner for reusable generalized policies",
		"preferred_use": (
			"candidate hierarchical-policy backend; current repository audits "
			"paper code but has no verified atomic ASL compiler"
		),
		"input_artifacts": (
			"PDDL-like benchmark tasks",
			"paper experiment scripts",
		),
		"output_artifacts": (
			"hierarchical policy",
			"experiment logs",
		),
		"reusable_evidence": (
			"policy-reuse representation baseline",
			"hierarchical policy language comparison",
			"hierarchical atomic-template candidates after a future compiler adapter",
		),
		"known_failure_modes": (
			"missing_backend",
			"unmapped_policy_language",
			"environment_reproduction_gap",
		),
		"resource_profile": {
			"execution_environment": "paper scripts; guarded before long runs",
			"default_max_rss_gb": DEFAULT_MAX_RSS_GB,
			"guard_required": True,
		},
		"usage_entrypoints": (
			"cd .external/gp-backends/h-policy-learner/learning/experiments/scripts",
			"bash <experiment>.sh",
			"bash <second-experiment>.sh",
			"parse generated sketch_str.txt only through the verified DLPlan policy adapter",
		),
		"paper_code_capability": {
			"status": CAPABILITY_PAPER_SOURCE_COMPLETE,
			"basis": (
				"official repository is pinned",
				"learning and testing experiment scripts are present",
				"benchmark folders for the reported hierarchical-policy suite are present",
			),
			"reproduction_gap": (
				"exact cluster-scale hierarchical-policy experiments are not re-run "
				"by the audit command",
				"policy-to-ASL parser validation remains a project-side adapter task",
			),
		},
		"current_consumption_role": ATOMIC_COMPILER_PENDING_CONSUMPTION_ROLE,
	},
	"d2l": {
		"paper_role": "description-logic policy learner baseline",
		"preferred_use": (
			"candidate description-logic policy backend; current repository parses "
			"safe text-policy subsets but has no verified atomic ASL compiler"
		),
		"input_artifacts": (
			"paper benchmark selector",
			"Docker/apptainer-compatible environment",
		),
		"output_artifacts": (
			"description_logic_policy",
			"experiment logs",
		),
		"reusable_evidence": (
			"description-logic feature templates",
			"generalized-policy baseline behavior",
			"atomic transition-policy candidates after a future compiler adapter",
		),
		"known_failure_modes": (
			"pin_mismatch",
			"docker_image_missing",
			"unmapped_policy_language",
		),
		"resource_profile": {
			"execution_environment": "Docker linux/amd64 paper environment",
			"default_max_rss_gb": DEFAULT_MAX_RSS_GB,
			"guard_required": True,
		},
		"usage_entrypoints": (
			"uv run python scripts/gp_backend_audit.py d2l-docker-commands",
			"docker build --platform linux/amd64 -t d2l-official-env:local -f .external/gp-backends/d2l/containers/Dockerfile .external/gp-backends/d2l",
			"docker run --rm --platform linux/amd64 -v .external/gp-backends/d2l:/workspace/d2l d2l-official-env:local blocks:clear",
		),
		"paper_code_capability": {
			"status": CAPABILITY_SOURCE_COMPLETE_NEEDS_ENVIRONMENT,
			"basis": (
				"official repository is pinned",
				"Dockerfile and experiment runner are present",
				"README lists the concrete paper experiments and Docker invocation",
			),
			"reproduction_gap": (
				"AAAI table reproduction depends on the original planner and MaxSAT "
				"toolchain inside the paper environment",
				"full table has not been re-run by this lightweight audit",
			),
		},
		"current_consumption_role": ATOMIC_COMPILER_PENDING_CONSUMPTION_ROLE,
	},
	"learner-policies-from-examples": {
		"paper_role": (
			"KR 2025 generalized-policy learner from examples with feature-pool "
			"generation and structural termination checks"
		),
		"preferred_use": (
			"candidate policy-first backend for learned LiftedPolicyProgram "
			"representations; ASL compilation remains a verified-adapter gap"
		),
		"input_artifacts": (
			"PDDL domain",
			"training PDDL problems",
			"planner traces from preprocessing",
			"feature-complexity limits",
		),
		"output_artifacts": (
			"dlplan_policy",
			"minimized_policy",
			"feature_pool",
			"verification_log",
		),
		"reusable_evidence": (
			"domain-independent feature generation",
			"hitting-set-style policy selection",
			"structural termination evidence",
			"policy-first representation before atomic ASL compilation",
		),
		"known_failure_modes": (
			"no_verified_atomic_literal_asl_compiler",
			"missing_policy_artifact",
			"no_policy_learned",
			"resource_limit_exceeded",
		),
		"resource_profile": {
			"execution_environment": (
				"Docker linux/amd64 with resource_guard.py; native macOS is "
				"unsupported because bundled planner libraries are Linux ELF"
			),
			"default_max_rss_gb": DEFAULT_MAX_RSS_GB,
			"guard_required": True,
		},
		"usage_entrypoints": (
			"uv run python scripts/gp_backend_audit.py learning-general-policies-docker-build-command",
			"uv run python scripts/gp_backend_audit.py learning-general-policies-docker-command --experiment <experiment> --timeout-seconds 1800 --max-num-instances 1",
			"uv run python scripts/gp_backend_audit.py learning-general-policies-summary --experiment <experiment>",
		),
		"paper_code_capability": {
			"status": CAPABILITY_SOURCE_COMPLETE_NEEDS_ENVIRONMENT,
			"basis": (
				"official repository is pinned",
				"README identifies the final-paper commit and implemented algorithm",
				"learning entrypoint and paper benchmark folders are present",
			),
			"reproduction_gap": (
				"native macOS cannot run the bundled Linux planner libraries",
				"full KR experiment matrix must use the project Docker wrapper and "
				"is not part of the lightweight audit",
			),
		},
		"current_consumption_role": ATOMIC_COMPILER_PENDING_CONSUMPTION_ROLE,
	},
	"pg3": {
		"paper_role": "IJCAI 2022 policy-guided generalized policy generation",
		"preferred_use": "candidate lifted decision-list policy backend after parser support",
		"input_artifacts": (
			"configured PDDL learning environment",
			"training and testing tasks",
		),
		"output_artifacts": (
			"lifted decision-list policy",
			"training and evaluation logs",
		),
		"reusable_evidence": (
			"direct lifted action-selection policy baseline",
			"planner-guided policy search behavior",
		),
		"known_failure_modes": (
			"no_lifted_policy_program_adapter",
			"environment_specific_experiment_config",
		),
		"resource_profile": {
			"execution_environment": "Python 3.6+ via requirements.txt and run.sh",
			"default_max_rss_gb": DEFAULT_MAX_RSS_GB,
			"guard_required": True,
		},
		"usage_entrypoints": (
			"pip install -r requirements.txt",
			"./run.sh",
			"edit ENV in run.sh to switch domains",
		),
		"paper_code_capability": {
			"status": CAPABILITY_PAPER_SOURCE_COMPLETE,
			"basis": (
				"official repository is pinned",
				"README states that it implements the main IJCAI approach",
				"run script and Python entrypoint are present",
			),
			"reproduction_gap": (
				"policy training to the reported iteration budget is not re-run by "
				"this lightweight audit",
				"lifted decision-list to ASL adapter is not implemented yet",
			),
		},
		"current_consumption_role": AUDIT_ONLY_CONSUMPTION_ROLE,
	},
	"mimir-rgnn": {
		"paper_role": "KR 2022 relational graph-neural generalized policy library",
		"preferred_use": "neural policy baseline or feature-discovery reference",
		"input_artifacts": (
			"PDDL domain and problems through Mimir",
			"state/action/goal encoders",
			"training data for neural policy or value learning",
		),
		"output_artifacts": (
			"PyTorch R-GNN model",
			"action or object readouts",
		),
		"reusable_evidence": (
			"relational neural baseline",
			"PDDL-to-graph encoding strategy",
		),
		"known_failure_modes": (
			"neural_policy_not_symbolic_asl",
			"no_distillation_or_certification_adapter",
		),
		"resource_profile": {
			"execution_environment": "Python 3.11+; pip install pymimir-rgnn",
			"default_max_rss_gb": DEFAULT_MAX_RSS_GB,
			"guard_required": True,
		},
		"usage_entrypoints": (
			"pip install pymimir-rgnn",
			"import pymimir_rgnn and build RelationalGraphNeuralNetwork",
		),
		"paper_code_capability": {
			"status": CAPABILITY_LIBRARY_OR_INTERFACE_ONLY,
			"basis": (
				"official repository is pinned",
				"README documents the R-GNN planning library and PDDL integration",
				"library API implements the neural representation used by the paper line",
			),
			"reproduction_gap": (
				"repository is a reusable library rather than a full paper "
				"experiment release with all training scripts and checkpoints",
				"neural policy distillation to symbolic ASL is not available",
			),
		},
		"current_consumption_role": AUDIT_ONLY_CONSUMPTION_ROLE,
	},
	"best-first-generalized-planning": {
		"paper_role": "ICAPS 2021 best-first search over planning programs",
		"preferred_use": "planning-program baseline for loop/pointer domains",
		"input_artifacts": (
			"generated synthesis instances",
			"generated validation instances",
			"program line bound",
		),
		"output_artifacts": (
			"assembly-like planning program",
			"validator report",
		),
		"reusable_evidence": (
			"generalized program synthesis baseline",
			"loop and pointer strategy examples",
		),
		"known_failure_modes": (
			"planning_program_not_asl_module",
			"requires_program_to_asl_adapter",
		),
		"resource_profile": {
			"execution_environment": "C++ binaries built by scripts/compile_all.sh",
			"default_max_rss_gb": DEFAULT_MAX_RSS_GB,
			"guard_required": True,
		},
		"usage_entrypoints": (
			"./scripts/compile_all.sh",
			"./main.bin 8 domain/heuristics/fibo/",
			"./validator.bin programs/fibo.prog domain/validation/fibo/",
		),
		"paper_code_capability": {
			"status": CAPABILITY_PAPER_SOURCE_COMPLETE,
			"basis": (
				"official repository is pinned",
				"README includes generator, synthesis, validation, and paper "
				"experiment scripts",
				"program examples and validator entrypoints are present",
			),
			"reproduction_gap": (
				"C++ binaries and full ICAPS experiment scripts are not built or "
				"run by the lightweight audit",
				"planning-program to ASL adapter is not implemented yet",
			),
		},
		"current_consumption_role": AUDIT_ONLY_CONSUMPTION_ROLE,
	},
	"bfgp-pp": {
		"paper_role": "BFGP++ structured generalized planning program synthesis",
		"preferred_use": "planning-program baseline and possible future ASL program adapter",
		"input_artifacts": (
			"PDDL preprocessing environment",
			"synthesis instance folder",
			"program language and line bound",
		),
		"output_artifacts": (
			"structured planning program",
			"validation logs",
		),
		"reusable_evidence": (
			"loop-structured generalized programs",
			"repair-mode program synthesis",
		),
		"known_failure_modes": (
			"planning_program_not_symbolic_predicate_modules",
			"requires_program_to_asl_adapter",
		),
		"resource_profile": {
			"execution_environment": "Python venv plus C++ build via scripts/compile.sh",
			"default_max_rss_gb": DEFAULT_MAX_RSS_GB,
			"guard_required": True,
		},
		"usage_entrypoints": (
			"pip install -r requirements.txt && pip install -e .",
			"./scripts/compile.sh",
			"./main.bin -m synthesis -l 8 -f domains/gripper/synthesis/ -o gripper -pgp True",
		),
		"paper_code_capability": {
			"status": CAPABILITY_PAPER_SOURCE_COMPLETE,
			"basis": (
				"official repository is pinned",
				"README documents synthesis, validation, and repair modes",
				"structured program source, domains, and compile scripts are present",
			),
			"reproduction_gap": (
				"full structured-program experiment suite is not re-run by this audit",
				"structured program to ASL adapter is not implemented yet",
			),
		},
		"current_consumption_role": AUDIT_ONLY_CONSUMPTION_ROLE,
	},
	"pgp-landmarks": {
		"paper_role": "SoCS 2022 progressive generalized planning with landmarks",
		"preferred_use": "landmark-guided planning-program baseline",
		"input_artifacts": (
			"generated synthesis instances",
			"generated validation instances",
			"program line bound",
		),
		"output_artifacts": (
			"planning program",
			"landmark graph files",
			"validation report",
		),
		"reusable_evidence": (
			"landmark-guided generalized planning baseline",
			"progressive planning program output",
		),
		"known_failure_modes": (
			"planning_program_not_asl_module",
			"requires_program_to_asl_adapter",
		),
		"resource_profile": {
			"execution_environment": "C++ binaries built by scripts/compile_all.sh",
			"default_max_rss_gb": DEFAULT_MAX_RSS_GB,
			"guard_required": True,
		},
		"usage_entrypoints": (
			"./scripts/compile_all.sh",
			"./main.bin PGP 7 domain/synthesis/visitall/",
			"./validator.bin experiments/synthesis/visitall_PGP_7_landmarks.prog domain/validation/visitall/",
		),
		"paper_code_capability": {
			"status": CAPABILITY_PAPER_SOURCE_COMPLETE,
			"basis": (
				"official repository is pinned",
				"README identifies Progressive Generalized Planning with landmarks",
				"paper reproduction scripts, generators, and validators are present",
			),
			"reproduction_gap": (
				"SoCS experiment script is not run by the lightweight audit",
				"planning-program to ASL adapter is not implemented yet",
			),
		},
		"current_consumption_role": AUDIT_ONLY_CONSUMPTION_ROLE,
	},
	"sltp": {
		"paper_role": "Sample, Learn, Transform and Plan generalized planning framework",
		"preferred_use": "feature-policy predecessor and theory/reference backend",
		"input_artifacts": (
			"experiment configuration",
			"sampled transition systems",
			"feature generator and MaxSAT solver",
		),
		"output_artifacts": (
			"sample files",
			"feature matrices",
			"learned feature policy files",
		),
		"reusable_evidence": (
			"description-logic feature generation",
			"transition-sample learning pipeline",
		),
		"known_failure_modes": (
			"requires_FS_private_or_Docker",
			"legacy_environment",
		),
		"resource_profile": {
			"execution_environment": "Python 3, FS planner, OpenWBO, or Docker image",
			"default_max_rss_gb": DEFAULT_MAX_RSS_GB,
			"guard_required": True,
		},
		"usage_entrypoints": (
			"pip install -e .",
			"./run.py blocks:aaai_clear_x_simple_hybrid",
			"docker run ... gfrancesm/sltp sltp gripper:aaai_prob01",
		),
		"paper_code_capability": {
			"status": CAPABILITY_SOURCE_COMPLETE_NEEDS_ENVIRONMENT,
			"basis": (
				"official repository is pinned",
				"README documents the sample-learn-transform-plan pipeline",
				"feature generation, sampling, and Docker usage are documented",
			),
			"reproduction_gap": (
				"legacy external planner and MaxSAT dependencies are required",
				"full pipeline and paper results are not re-run by this audit",
			),
		},
		"current_consumption_role": AUDIT_ONLY_CONSUMPTION_ROLE,
	},
	"up-bfgp": {
		"paper_role": "Unified Planning interface for BFGP++",
		"preferred_use": "future interface route for BFGP++ if program-to-ASL adapter exists",
		"input_artifacts": (
			"Unified Planning problem",
			"BFGP++ installation",
		),
		"output_artifacts": (
			"Unified Planning engine result",
			"BFGP++ planning programs",
		),
		"reusable_evidence": (
			"Unified Planning integration pattern",
			"BFGP++ API wrapper",
		),
		"known_failure_modes": (
			"depends_on_custom_unified_planning_checkout",
			"no_program_to_asl_adapter",
		),
		"resource_profile": {
			"execution_environment": "Ubuntu 22.04 Python package plus BFGP++ build",
			"default_max_rss_gb": DEFAULT_MAX_RSS_GB,
			"guard_required": True,
		},
		"usage_entrypoints": (
			"pip install unified-planning/",
			"pip install -r requirements.txt && pip install -e .",
		),
		"paper_code_capability": {
			"status": CAPABILITY_LIBRARY_OR_INTERFACE_ONLY,
			"basis": (
				"official repository is pinned",
				"README states that this is a Unified Planning interface for BFGP++",
				"installation path for the interface is documented",
			),
			"reproduction_gap": (
				"it is an integration interface, not a standalone experiment release",
				"depends on a custom Unified Planning checkout and BFGP++ installation",
			),
		},
		"current_consumption_role": AUDIT_ONLY_CONSUMPTION_ROLE,
	},
	"llm-genplan": {
		"paper_role": "AAAI 2024 LLM-generated generalized planning programs",
		"preferred_use": "LLM baseline or related-work comparator, not deterministic route",
		"input_artifacts": (
			"PDDL domains and example tasks",
			"cached or live LLM interactions",
		),
		"output_artifacts": (
			"Python generalized planning programs",
			"cached chat logs",
			"coverage results",
		),
		"reusable_evidence": (
			"LLM generalized-program baseline",
			"PG3 comparison domains",
		),
		"known_failure_modes": (
			"nondeterministic_or_cache_dependent",
			"python_program_not_asl_policy",
		),
		"resource_profile": {
			"execution_environment": "Python 3.11+ package; cached reproduction scripts",
			"default_max_rss_gb": DEFAULT_MAX_RSS_GB,
			"guard_required": True,
		},
		"usage_entrypoints": (
			"pip install -e '.[develop]'",
			"./run_ci_checks.sh",
			"./scripts/run_all.sh",
		),
		"paper_code_capability": {
			"status": CAPABILITY_PAPER_SOURCE_COMPLETE,
			"basis": (
				"official repository is pinned",
				"README identifies the AAAI paper and cached-log reproduction path",
				"CI, run-all script, and cached chat-log directory are present",
			),
			"reproduction_gap": (
				"full cached reproduction is long-running and not part of the "
				"lightweight audit",
				"output is Python program code, not directly a symbolic ASL policy",
			),
		},
		"current_consumption_role": AUDIT_ONLY_CONSUMPTION_ROLE,
	},
	"state-centric-gen-planning": {
		"paper_role": "ICAPS 2026 learned transition-model generalized planning",
		"preferred_use": "neural transition-model baseline and future route candidate",
		"input_artifacts": (
			"PDDL domains and generated plans",
			"state trajectories",
			"WL graph or factored encodings",
		),
		"output_artifacts": (
			"LSTM or XGBoost transition model",
			"inference logs",
			"coverage tables",
		),
		"reusable_evidence": (
			"state-centric OOD generalized planning baseline",
			"symbolically valid successor decoding",
		),
		"known_failure_modes": (
			"neural_transition_model_not_symbolic_asl",
			"requires_checkpoint_or_training_pipeline",
		),
		"resource_profile": {
			"execution_environment": "uv or pip with Fast Downward, VAL, Pyperplan, WLPlan",
			"default_max_rss_gb": DEFAULT_MAX_RSS_GB,
			"guard_required": True,
		},
		"usage_entrypoints": (
			"uv sync",
			"python -m code.data-processing.generate_plans --workers 8",
			"python -m code.modeling.train_lstm --domain blocks --delta",
			"python -m code.modeling.inference_lstm --domain blocks --delta",
		),
		"paper_code_capability": {
			"status": CAPABILITY_SOURCE_COMPLETE_NEEDS_ENVIRONMENT,
			"basis": (
				"official repository is pinned",
				"README states that it is the official implementation",
				"data generation, training, inference, and aggregation entrypoints "
				"are documented",
			),
			"reproduction_gap": (
				"pretrained checkpoints are external release files",
				"neural transition model is not a direct lifted ASL plan library",
			),
		},
		"current_consumption_role": AUDIT_ONLY_CONSUMPTION_ROLE,
	},
	"ipc-learning-huzar": {
		"paper_role": "IPC 2023 learning-track HUZAR domain-knowledge system",
		"preferred_use": "learning-track comparator for planner domain knowledge",
		"input_artifacts": (
			"IPC training tasks",
			"relaxed plans and simple landmarks from Scorpion/Fast Downward",
		),
		"output_artifacts": (
			"GNN preprocessor model",
			"planner-domain knowledge files",
		),
		"reusable_evidence": (
			"IPC learning-track comparison",
			"learned planner preprocessor route",
		),
		"known_failure_modes": (
			"domain_knowledge_not_generalized_policy",
			"no_asl_compiler_adapter",
		),
		"resource_profile": {
			"execution_environment": "Python plus Scorpion/Fast Downward toolchain",
			"default_max_rss_gb": DEFAULT_MAX_RSS_GB,
			"guard_required": True,
		},
		"usage_entrypoints": (
			"./scorpion/fast-downward.py --alias lama-first --find-simple-landmarks --find-relaxed-plan ...",
			"python src/graph_data_generation.py <data> <output> --relaxed-plan --simple-landmarks",
		),
		"paper_code_capability": {
			"status": CAPABILITY_COMPETITION_ARTIFACT_ONLY,
			"basis": (
				"competition repository is pinned",
				"learning and planning Apptainer recipes are present",
				"Scorpion, symbolic planner, and graph-neural learning components "
				"are present",
			),
			"reproduction_gap": (
				"competition release emits planner domain knowledge rather than a standalone "
				"generalized policy",
				"not a direct route to ASL without a separate domain-knowledge adapter",
			),
		},
		"current_consumption_role": AUDIT_ONLY_CONSUMPTION_ROLE,
	},
	"ipc-learning-pgp-baseline": {
		"paper_role": "IPC 2023 PGP learning-track baseline",
		"preferred_use": "competition-compatible Progressive Generalized Planner baseline",
		"input_artifacts": (
			"PDDL domain",
			"training problems for learning image",
			"testing problem for planning image",
		),
		"output_artifacts": (
			"planning program",
			"competition plan output",
		),
		"reusable_evidence": (
			"IPC learning-track PGP baseline",
			"Apptainer packaging pattern",
		),
		"known_failure_modes": (
			"planning_program_not_asl_module",
			"requires_apptainer",
		),
		"resource_profile": {
			"execution_environment": "Apptainer learn and plan images",
			"default_max_rss_gb": DEFAULT_MAX_RSS_GB,
			"guard_required": True,
		},
		"usage_entrypoints": (
			"apptainer build learn.img Apptainer.pgp.learn",
			"./learn.img dck.prog domains/gripper/domain.pddl domains/gripper/p-2-0.pddl ...",
			"apptainer build plan.img Apptainer.pgp.plan",
			"./plan.img dck.prog domains/gripper/domain.pddl domains/gripper/p-10-0.pddl plan.10",
		),
		"paper_code_capability": {
			"status": CAPABILITY_COMPETITION_ARTIFACT_ONLY,
			"basis": (
				"competition repository is pinned",
				"README states that it is a refactored Progressive Generalized "
				"Planner baseline",
				"learning and planning Apptainer recipes are present",
			),
			"reproduction_gap": (
				"competition image flow is not run by the lightweight audit",
				"planning-program to ASL adapter is not implemented yet",
			),
		},
		"current_consumption_role": AUDIT_ONLY_CONSUMPTION_ROLE,
	},
}


@dataclass(frozen=True)
class BackendManifest:
	"""Pinned metadata for one external generalized-planning backend."""

	name: str
	path: Path
	url: str
	expected_commit: str
	present: bool
	observed_commit: str | None = None


@dataclass(frozen=True)
class SketchFeature:
	"""One boolean or numerical feature from an external sketch learner."""

	identifier: str
	kind: str
	expression: str


@dataclass(frozen=True)
class SketchCondition:
	"""One qualitative feature condition in a sketch rule."""

	operator: str
	feature_id: str


@dataclass(frozen=True)
class SketchEffect:
	"""One qualitative feature effect in a sketch rule."""

	operator: str
	feature_id: str


@dataclass(frozen=True)
class SketchRule:
	"""Parsed view of a learner-sketches rule."""

	conditions: tuple[SketchCondition, ...]
	effects: tuple[SketchEffect, ...]
	raw: str


@dataclass(frozen=True)
class SketchPolicy:
	"""Small parsed view of a DLPlan policy sketch file."""

	features: Mapping[str, str]
	rules: tuple[str, ...]
	boolean_features: Mapping[str, str] = field(default_factory=dict)
	numerical_features: Mapping[str, str] = field(default_factory=dict)
	parsed_rules: tuple[SketchRule, ...] = ()


@dataclass(frozen=True)
class D2LPolicyParseDiagnostic:
	"""One non-fatal D2L policy conversion diagnostic."""

	line: str
	reason: str

	def to_dict(self) -> dict[str, str]:
		return {
			"line": self.line,
			"reason": self.reason,
		}


@dataclass(frozen=True)
class LearnerSketchesRunConfig:
	"""Configuration for one guarded learner-sketches training run."""

	domain_file: str | Path
	problems_directory: str | Path
	workspace: str | Path
	width: int = 1
	python_executable: str | Path | None = None
	max_states_per_instance: int = 10000
	max_time_per_instance: int = 10000
	max_rss_gb: float = DEFAULT_MAX_RSS_GB
	poll_seconds: float = DEFAULT_POLL_SECONDS
	timeout_seconds: int | None = None
	additional_booleans: tuple[str, ...] = ()
	additional_numericals: tuple[str, ...] = ()
	use_resource_guard: bool = True


@dataclass(frozen=True)
class LearnerSketchesRunResult:
	"""Result of one learner-sketches training run and discovered policies."""

	command: tuple[str, ...]
	workspace: Path
	returncode: int
	policy_file: Path | None
	raw_policy_file: Path | None
	stdout: str
	stderr: str

	@property
	def succeeded(self) -> bool:
		return self.returncode == 0 and self.policy_file is not None

	def to_dict(self) -> dict[str, object]:
		return {
			"command": list(self.command),
			"workspace": str(self.workspace),
			"returncode": self.returncode,
			"policy_file": str(self.policy_file) if self.policy_file is not None else None,
			"raw_policy_file": (
				str(self.raw_policy_file)
				if self.raw_policy_file is not None
				else None
			),
			"stdout": self.stdout,
			"stderr": self.stderr,
			"succeeded": self.succeeded,
			}


@dataclass(frozen=True)
class LearningGeneralPoliciesRunConfig:
	"""Configuration for the KR 2025 learner-policies-from-examples backend."""

	domain_file: str | Path
	problems_directory: str | Path
	workspace: str | Path
	width: int = 0
	python_executable: str | Path | None = None
	planner: str = "bfws"
	max_num_instances: int | None = None
	max_states_per_instance: int = 10000
	max_time_per_instance: int = 10000
	complexity_limit: int | None = None
	feature_limit: int = 1000000
	max_features: int = 15
	cost_bound: int = 100
	max_rss_gb: float = DEFAULT_MAX_RSS_GB
	poll_seconds: float = DEFAULT_POLL_SECONDS
	timeout_seconds: int | None = None
	use_resource_guard: bool = True


@dataclass(frozen=True)
class LearningGeneralPoliciesRunResult:
	"""Result of one policy-first generalized-policy learner run."""

	command: tuple[str, ...]
	workspace: Path
	returncode: int
	policy_file: Path | None
	raw_policy_file: Path | None
	stdout: str
	stderr: str

	@property
	def succeeded(self) -> bool:
		return self.returncode == 0 and self.policy_file is not None

	def to_dict(self) -> dict[str, object]:
		return {
			"command": list(self.command),
			"workspace": str(self.workspace),
			"returncode": self.returncode,
			"policy_file": str(self.policy_file) if self.policy_file is not None else None,
			"raw_policy_file": (
				str(self.raw_policy_file)
				if self.raw_policy_file is not None
				else None
			),
			"stdout": self.stdout,
			"stderr": self.stderr,
			"succeeded": self.succeeded,
		}


def discover_backend_manifest(
	*,
	root: str | Path = DEFAULT_BACKEND_ROOT,
	name: str,
	url: str,
	commit: str,
) -> BackendManifest:
	"""Return local status for a pinned external backend."""

	root_path = Path(root)
	backend_path = root_path / name
	observed_commit = _observed_git_commit(backend_path)
	return BackendManifest(
		name=name,
		path=backend_path,
		url=url,
		expected_commit=commit,
		present=backend_path.exists(),
		observed_commit=observed_commit,
	)


def backend_audit_matrix(
	*,
	root: str | Path = DEFAULT_BACKEND_ROOT,
) -> tuple[dict[str, object], ...]:
	"""Return paper-backend audit evidence without running external learners."""

	entries: list[dict[str, object]] = []
	entries.append(_backend_matrix_entry(_discover_moose_manifest(root)))
	for backend in PINNED_BACKENDS:
		manifest = discover_backend_manifest(
			root=root,
			name=backend["name"],
			url=backend["url"],
			commit=backend["commit"],
		)
		entries.append(_backend_matrix_entry(manifest))
	return tuple(entries)


def _discover_moose_manifest(root: str | Path = DEFAULT_BACKEND_ROOT) -> BackendManifest:
	root_path = Path(root)
	candidates: tuple[Path, ...] = (
		root_path / "moose",
		root_path.parent / "moose",
	)
	if root_path.expanduser().resolve() == DEFAULT_BACKEND_ROOT.expanduser().resolve():
		candidates = (*candidates, Path(MOOSE_BACKEND["path"]))
	backend_path = next((path for path in candidates if path.exists()), candidates[0])
	observed_commit = _observed_git_commit(backend_path)
	return BackendManifest(
		name=str(MOOSE_BACKEND["name"]),
		path=backend_path,
		url=str(MOOSE_BACKEND["url"]),
		expected_commit=str(MOOSE_BACKEND["commit"]),
		present=backend_path.exists(),
		observed_commit=observed_commit,
	)


def _backend_matrix_entry(manifest: BackendManifest) -> dict[str, object]:
	profile = BACKEND_RESEARCH_PROFILES[manifest.name]
	pin_status = _pin_status(manifest)
	failures = _backend_failure_modes(manifest=manifest, pin_status=pin_status)
	return {
		"name": manifest.name,
		"url": manifest.url,
		"path": str(manifest.path),
		"expected_commit": manifest.expected_commit,
		"observed_commit": manifest.observed_commit,
		"present": manifest.present,
		"pin_status": pin_status,
		"paper_role": profile["paper_role"],
		"preferred_use": profile["preferred_use"],
		"input_artifacts": list(profile["input_artifacts"]),
		"output_artifacts": list(profile["output_artifacts"]),
		"reusable_evidence": list(profile["reusable_evidence"]),
		"usage_entrypoints": list(profile.get("usage_entrypoints") or ()),
		"paper_code_capability": dict(profile["paper_code_capability"]),
		"failure_modes": failures,
		"known_failure_modes": list(profile["known_failure_modes"]),
		"resource_profile": dict(profile["resource_profile"]),
		"current_consumption_role": dict(profile["current_consumption_role"]),
	}


def backend_consumption_role(name: str) -> dict[str, object]:
	"""Return whether a backend may currently drive atomic ASL library generation."""

	profile = BACKEND_RESEARCH_PROFILES.get(str(name or "").strip())
	if profile is None:
		return {
			"drives_atomic_templates": False,
			"drives_temporal_wrapper": False,
			"consumed_by_atomic_library": False,
			"consumption_mode": "unknown_backend_audit_only",
			"blocking_gap": "no_pinned_backend_profile_or_verified_adapter",
		}
	return dict(profile["current_consumption_role"])


class GPBackendRunner:
	"""Build reproducible invocations for external generalized-planning code."""

	def __init__(self, manifest: BackendManifest) -> None:
		self.manifest = manifest

	def learner_sketches_command(
		self,
		*,
		domain_file: str | Path,
		problems_directory: str | Path,
		workspace: str | Path,
		python_executable: str | Path = "python3",
		width: int = 1,
		max_states_per_instance: int = 10000,
		max_time_per_instance: int = 10000,
		additional_booleans: Sequence[str] = (),
		additional_numericals: Sequence[str] = (),
	) -> tuple[str, ...]:
		"""Command for the ICAPS sketch learner backend."""

		self._require_backend()
		command: list[str] = [
			str(python_executable),
			str(self.manifest.path / "learning" / "main.py"),
			"--domain_filepath",
			str(Path(domain_file)),
			"--problems_directory",
			str(Path(problems_directory)),
			"--workspace",
			str(Path(workspace)),
			"--width",
			str(width),
			"--max_num_states_per_instance",
			str(max_states_per_instance),
			"--max_time_per_instance",
			str(max_time_per_instance),
		]
		if additional_booleans:
			command.append("--additional_booleans")
			command.extend(additional_booleans)
		if additional_numericals:
			command.append("--additional_numericals")
			command.extend(additional_numericals)
		return tuple(command)

	def guarded_command(
		self,
		command: Sequence[str | Path],
		*,
		label: str,
		max_rss_gb: float = DEFAULT_MAX_RSS_GB,
		poll_seconds: float = DEFAULT_POLL_SECONDS,
		timeout_seconds: int | None = None,
	) -> tuple[str, ...]:
		"""Wrap an external learner invocation in the local resource guard."""

		self._require_backend()
		guard: list[str] = [
			"uv",
			"run",
			"python",
			str(PROJECT_ROOT / "scripts" / "resource_guard.py"),
			"--max-rss-gb",
			str(max_rss_gb),
			"--poll-seconds",
			str(poll_seconds),
			"--label",
			label,
		]
		if timeout_seconds is not None:
			guard.extend(("--timeout-seconds", str(timeout_seconds)))
		guard.append("--")
		guard.extend(str(item) for item in command)
		return tuple(guard)

	def h_policy_learner_command(
		self,
		*,
		experiment_script: str,
	) -> tuple[str, ...]:
		"""Command for a pinned hierarchical-policy learner experiment script."""

		self._require_backend()
		script_path = self.manifest.path / "learning" / "experiments" / "scripts" / experiment_script
		return ("bash", str(script_path))

	def d2l_command(
		self,
		*,
		experiment: str,
		python_executable: str | Path = "python3",
		steps: Sequence[int] = (),
	) -> tuple[str, ...]:
		"""Command for a D2L experiment such as blocks:clear."""

		self._require_backend()
		command: list[str] = [
			str(python_executable),
			str(self.manifest.path / "experiments" / "run.py"),
			experiment,
		]
		command.extend(str(step) for step in steps)
		return tuple(command)

	def learning_general_policies_command(
		self,
		*,
		domain_file: str | Path,
		problems_directory: str | Path,
		workspace: str | Path,
		python_executable: str | Path = "python3",
		width: int = 0,
		planner: str = "bfws",
		max_num_instances: int | None = None,
		max_states_per_instance: int = 10000,
		max_time_per_instance: int = 10000,
		complexity_limit: int | None = None,
		feature_limit: int = 1000000,
		max_features: int = 15,
		cost_bound: int = 100,
	) -> tuple[str, ...]:
		"""Command for the KR 2025 learner-policies-from-examples backend."""

		self._require_backend()
		command: list[str] = [
			str(python_executable),
			str(self.manifest.path / "learning" / "main.py"),
			"--domain_filepath",
			str(Path(domain_file)),
			"--problems_directory",
			str(Path(problems_directory)),
			"--workspace",
			str(Path(workspace)),
			"--width",
			str(width),
			"--planner",
			planner,
			"--max_num_states_per_instance",
			str(max_states_per_instance),
			"--max_time_per_instance",
			str(max_time_per_instance),
			"--feature_limit",
			str(feature_limit),
			"--max_features",
			str(max_features),
			"--cost_bound",
			str(cost_bound),
		]
		if max_num_instances is not None:
			command.extend(("--max_num_instances", str(max_num_instances)))
		if complexity_limit is not None:
			command.extend(("--complexity_limit", str(complexity_limit)))
		return tuple(command)

	def learning_general_policies_docker_build_command(
		self,
		*,
		image: str = "learner-policies-from-examples-env:local",
		platform: str = "linux/amd64",
		build_args: Mapping[str, str] | None = None,
	) -> tuple[str, ...]:
		"""Docker build command for the KR 2025 Linux planner environment."""

		self._require_backend()
		command: list[str] = [
			"docker",
			"build",
			"--platform",
			platform,
		]
		for name, value in sorted((build_args or {}).items()):
			if value:
				command.extend(("--build-arg", f"{name}={value}"))
		command.extend(
			(
				"-t",
				image,
				"-f",
				str(PROJECT_ROOT / "docker" / "learning-general-policies" / "Dockerfile"),
				str(PROJECT_ROOT),
			),
		)
		return (
			*command,
		)

	def learning_general_policies_docker_run_command(
		self,
		*,
		domain_file: str | Path,
		problems_directory: str | Path,
		workspace: str | Path,
		image: str = "learner-policies-from-examples-env:local",
		platform: str = "linux/amd64",
		width: int = 0,
		planner: str = "bfws",
		max_num_instances: int | None = None,
		max_states_per_instance: int = 10000,
		max_time_per_instance: int = 10000,
		complexity_limit: int | None = None,
		feature_limit: int = 1000000,
		max_features: int = 15,
		cost_bound: int = 100,
		max_rss_gb: float = DEFAULT_MAX_RSS_GB,
		poll_seconds: float = DEFAULT_POLL_SECONDS,
		timeout_seconds: int | None = None,
	) -> tuple[str, ...]:
		"""Docker invocation for KR 2025 code with Linux-only planner libraries."""

		self._require_backend()
		inner_command = [
			"python",
			str(PROJECT_ROOT / "scripts" / "resource_guard.py"),
			"--max-rss-gb",
			str(max_rss_gb),
			"--poll-seconds",
			str(poll_seconds),
			"--label",
			f"learner-policies-from-examples:{Path(workspace).name}",
		]
		if timeout_seconds is not None:
			inner_command.extend(("--timeout-seconds", str(timeout_seconds)))
		inner_command.append("--")
		inner_command.extend(
			self.learning_general_policies_command(
				domain_file=domain_file,
				problems_directory=problems_directory,
				workspace=workspace,
				python_executable="python",
				width=width,
				planner=planner,
				max_num_instances=max_num_instances,
				max_states_per_instance=max_states_per_instance,
				max_time_per_instance=max_time_per_instance,
				complexity_limit=complexity_limit,
				feature_limit=feature_limit,
				max_features=max_features,
				cost_bound=cost_bound,
			),
		)
		inner = (
			f"export PYTHONPATH={shlex.quote(str(self.manifest.path / 'learning'))}; "
			+ " ".join(shlex.quote(item) for item in inner_command)
		)
		return (
			"docker",
			"run",
			"--rm",
			"--platform",
			platform,
			"--memory",
			f"{max_rss_gb:g}g",
			"-v",
			f"{PROJECT_ROOT}:{PROJECT_ROOT}",
			"-w",
			str(PROJECT_ROOT),
			image,
			"bash",
			"-lc",
			inner,
		)

	def d2l_docker_run_command(
		self,
		*,
		experiment: str,
		image: str = "d2l-official-env:local",
		workspace: str | Path,
		platform: str = "linux/amd64",
	) -> tuple[str, ...]:
		"""Docker invocation for the D2L paper environment."""

		self._require_backend()
		return (
			"docker",
			"run",
			"--rm",
			"--platform",
			platform,
			"-v",
			f"{self.manifest.path}:/workspace/d2l",
			"-v",
			f"{Path(workspace)}:/workspace/d2l/workspace",
			image,
			experiment,
		)

	def _require_backend(self) -> None:
		if not self.manifest.present:
			raise FileNotFoundError(
				f"External GP backend '{self.manifest.name}' is not installed at "
				f"{self.manifest.path}. Expected {self.manifest.url} at "
				f"{self.manifest.expected_commit}.",
			)


def run_learner_sketches(
	*,
	manifest: BackendManifest,
	config: LearnerSketchesRunConfig,
	env: Mapping[str, str] | None = None,
) -> LearnerSketchesRunResult:
	"""Run learner-sketches with guards and return the minimized policy file."""

	runner = GPBackendRunner(manifest)
	workspace = Path(config.workspace)
	workspace.mkdir(parents=True, exist_ok=True)
	python_executable = (
		config.python_executable
		if config.python_executable is not None
		else _default_backend_python(manifest)
	)
	command = runner.learner_sketches_command(
		domain_file=config.domain_file,
		problems_directory=config.problems_directory,
		workspace=workspace,
		python_executable=python_executable,
		width=config.width,
		max_states_per_instance=config.max_states_per_instance,
		max_time_per_instance=config.max_time_per_instance,
		additional_booleans=config.additional_booleans,
		additional_numericals=config.additional_numericals,
	)
	if config.use_resource_guard:
		command = runner.guarded_command(
			command,
			label=f"learner-sketches:{workspace.name}",
			max_rss_gb=config.max_rss_gb,
			poll_seconds=config.poll_seconds,
			timeout_seconds=config.timeout_seconds,
		)
	process = subprocess.run(
		command,
		check=False,
		capture_output=True,
		text=True,
		env=dict(env) if env is not None else None,
	)
	policy_file = discover_learner_sketches_policy_file(workspace, width=config.width)
	raw_policy_file = discover_learner_sketches_policy_file(
		workspace,
		width=config.width,
		minimized=False,
	)
	return LearnerSketchesRunResult(
		command=command,
		workspace=workspace,
		returncode=process.returncode,
		policy_file=policy_file,
		raw_policy_file=raw_policy_file,
		stdout=process.stdout,
		stderr=process.stderr,
	)


def run_learning_general_policies(
	*,
	manifest: BackendManifest,
	config: LearningGeneralPoliciesRunConfig,
	env: Mapping[str, str] | None = None,
) -> LearningGeneralPoliciesRunResult:
	"""Run the KR 2025 generalized-policy learner and discover policy files."""

	runner = GPBackendRunner(manifest)
	workspace = Path(config.workspace)
	workspace.mkdir(parents=True, exist_ok=True)
	python_executable = (
		config.python_executable
		if config.python_executable is not None
		else _default_backend_python(manifest)
	)
	command = runner.learning_general_policies_command(
		domain_file=config.domain_file,
		problems_directory=config.problems_directory,
		workspace=workspace,
		python_executable=python_executable,
		width=config.width,
		planner=config.planner,
		max_num_instances=config.max_num_instances,
		max_states_per_instance=config.max_states_per_instance,
		max_time_per_instance=config.max_time_per_instance,
		complexity_limit=config.complexity_limit,
		feature_limit=config.feature_limit,
		max_features=config.max_features,
		cost_bound=config.cost_bound,
	)
	if config.use_resource_guard:
		command = runner.guarded_command(
			command,
			label=f"learner-policies-from-examples:{workspace.name}",
			max_rss_gb=config.max_rss_gb,
			poll_seconds=config.poll_seconds,
			timeout_seconds=config.timeout_seconds,
		)
	process = subprocess.run(
		command,
		check=False,
		capture_output=True,
		text=True,
		env=dict(env) if env is not None else None,
	)
	policy_file = discover_learning_general_policies_policy_file(
		workspace,
		width=config.width,
	)
	raw_policy_file = discover_learning_general_policies_policy_file(
		workspace,
		width=config.width,
		minimized=False,
	)
	return LearningGeneralPoliciesRunResult(
		command=command,
		workspace=workspace,
		returncode=process.returncode,
		policy_file=policy_file,
		raw_policy_file=raw_policy_file,
		stdout=process.stdout,
		stderr=process.stderr,
	)


def discover_learner_sketches_policy_file(
	workspace: str | Path,
	*,
	width: int,
	minimized: bool = True,
) -> Path | None:
	"""Return learner-sketches policy file path when the expected file exists."""

	output_dir = Path(workspace) / "output"
	name = f"sketch_minimized_{width}.txt" if minimized else f"sketch_{width}.txt"
	path = output_dir / name
	return path if path.exists() else None


def discover_learning_general_policies_policy_file(
	workspace: str | Path,
	*,
	width: int,
	minimized: bool = True,
) -> Path | None:
	"""Return the KR 2025 learner policy file from `output.<uuid>` folders."""

	workspace_path = Path(workspace)
	name = f"sketch_minimized_{width}.txt" if minimized else f"sketch_{width}.txt"
	candidates = tuple(
		sorted(
			(
				workspace_path / "output" / name,
				*workspace_path.glob(f"output.*/{name}"),
			),
			key=lambda path: str(path),
		),
	)
	for path in candidates:
		if path.exists():
			return path
	return None


def parse_dlplan_policy(policy_text: str) -> SketchPolicy:
	"""Parse the feature table and rule forms from a DLPlan policy string."""

	boolean_features = _extract_features(policy_text, "booleans")
	numerical_features = _extract_features(policy_text, "numericals")
	features = {
		**boolean_features,
		**numerical_features,
	}
	rules = tuple(_extract_top_level_rules(policy_text))
	return SketchPolicy(
		features=features,
		rules=rules,
		boolean_features=boolean_features,
		numerical_features=numerical_features,
		parsed_rules=tuple(_parse_rule(rule) for rule in rules),
	)


def parse_d2l_policy(
	policy_text: str,
	*,
	predicate_arities: Mapping[str, int],
) -> tuple[SketchPolicy, tuple[D2LPolicyParseDiagnostic, ...]]:
	"""Parse the D2L text policy dialect into the internal sketch dialect.

	D2L prints transition-classification policies as a feature list followed by
	rules of the form ``state conditions -> {qualitative feature changes}``.
	This adapter converts only the lifted feature subset whose PDDL meaning is
	recoverable. Unsupported features remain in the policy with an unbindable
	expression so the normal feature-binding audit can reject them precisely.
	"""

	if "(:policy" in policy_text:
		return parse_dlplan_policy(policy_text), ()
	feature_ids: dict[str, str] = {}
	feature_expressions: dict[str, str] = {}
	diagnostics: list[D2LPolicyParseDiagnostic] = []
	for feature in _extract_d2l_header_features(policy_text):
		_ensure_d2l_feature(
			feature,
			feature_ids=feature_ids,
			feature_expressions=feature_expressions,
			predicate_arities=predicate_arities,
			diagnostics=diagnostics,
		)
	rules: list[str] = []
	for line in _extract_d2l_policy_lines(policy_text):
		parsed_rules = _parse_d2l_policy_line(
			line,
			feature_ids=feature_ids,
			feature_expressions=feature_expressions,
			predicate_arities=predicate_arities,
			diagnostics=diagnostics,
		)
		rules.extend(parsed_rules)
	numerical_features = {
		feature_id: expression
		for feature, feature_id in feature_ids.items()
		if not feature_expressions[feature_id].startswith("b_nullary(")
		for expression in (feature_expressions[feature_id],)
	}
	boolean_features = {
		feature_id: expression
		for feature, feature_id in feature_ids.items()
		if feature_expressions[feature_id].startswith("b_nullary(")
		for expression in (feature_expressions[feature_id],)
	}
	features = {
		**boolean_features,
		**numerical_features,
	}
	return (
		SketchPolicy(
			features=features,
			rules=tuple(rules),
			boolean_features=boolean_features,
			numerical_features=numerical_features,
			parsed_rules=tuple(_parse_rule(rule) for rule in rules),
		),
		tuple(diagnostics),
	)


def _extract_d2l_header_features(policy_text: str) -> tuple[str, ...]:
	features: list[str] = []
	for raw_line in policy_text.splitlines():
		line = raw_line.strip()
		if not line or line.startswith("Features") or line.startswith("Invariants"):
			continue
		if line.startswith("Policy:"):
			break
		match = re.fullmatch(r"(.+?)\s+\[k=\d+\]", line)
		if match:
			features.append(match.group(1).strip())
	return tuple(dict.fromkeys(features))


def _extract_d2l_policy_lines(policy_text: str) -> tuple[str, ...]:
	lines: list[str] = []
	in_policy = False
	for raw_line in policy_text.splitlines():
		line = raw_line.strip()
		if line == "Policy:":
			in_policy = True
			continue
		if not in_policy or not line:
			continue
		match = re.fullmatch(r"\d+\.\s*(.+)", line)
		if match:
			lines.append(match.group(1).strip())
	return tuple(lines)


def _parse_d2l_policy_line(
	line: str,
	*,
	feature_ids: dict[str, str],
	feature_expressions: dict[str, str],
	predicate_arities: Mapping[str, int],
	diagnostics: list[D2LPolicyParseDiagnostic],
) -> tuple[str, ...]:
	if "->" not in line:
		diagnostics.append(
			D2LPolicyParseDiagnostic(line=line, reason="missing_transition_arrow"),
		)
		return ()
	raw_conditions, raw_effects = line.split("->", 1)
	conditions = []
	for atom in _split_d2l_conditions(raw_conditions):
		parsed = _parse_d2l_feature_atom(
			atom,
			feature_ids=feature_ids,
			feature_expressions=feature_expressions,
			predicate_arities=predicate_arities,
			diagnostics=diagnostics,
			role="condition",
		)
		if parsed is not None:
			conditions.append(parsed)
	effect_sets = _extract_d2l_effect_sets(raw_effects)
	if not effect_sets:
		diagnostics.append(
			D2LPolicyParseDiagnostic(line=line, reason="missing_effect_set"),
		)
		return ()
	rules: list[str] = []
	for effect_set in effect_sets:
		effects = []
		for atom in _split_d2l_effect_atoms(effect_set):
			parsed = _parse_d2l_feature_atom(
				atom,
				feature_ids=feature_ids,
				feature_expressions=feature_expressions,
				predicate_arities=predicate_arities,
				diagnostics=diagnostics,
				role="effect",
			)
			if parsed is not None:
				effects.append(parsed)
		rules.append(_dlplan_rule_text(conditions=tuple(conditions), effects=tuple(effects)))
	return tuple(rules)


def _split_d2l_conditions(raw_conditions: str) -> tuple[str, ...]:
	text = raw_conditions.strip()
	if not text:
		return ()
	return tuple(
		part.strip()
		for part in re.split(r"\s+AND\s+", text)
		if part.strip()
	)


def _extract_d2l_effect_sets(raw_effects: str) -> tuple[str, ...]:
	effect_sets: list[str] = []
	depth = 0
	start: int | None = None
	for index, character in enumerate(raw_effects):
		if character == "{":
			if depth == 0:
				start = index + 1
			depth += 1
		elif character == "}":
			depth -= 1
			if depth == 0 and start is not None:
				effect_sets.append(raw_effects[start:index].strip())
				start = None
	return tuple(effect_sets)


def _split_d2l_effect_atoms(effect_set: str) -> tuple[str, ...]:
	return tuple(
		part.strip()
		for part in _split_top_level(effect_set, ",")
		if part.strip()
	)


def _split_top_level(text: str, separator: str) -> tuple[str, ...]:
	parts: list[str] = []
	depth = 0
	start = 0
	for index, character in enumerate(text):
		if character in "([{":
			depth += 1
		elif character in ")]}":
			depth -= 1
		elif character == separator and depth == 0:
			parts.append(text[start:index])
			start = index + 1
	parts.append(text[start:])
	return tuple(parts)


def _parse_d2l_feature_atom(
	atom: str,
	*,
	feature_ids: dict[str, str],
	feature_expressions: dict[str, str],
	predicate_arities: Mapping[str, int],
	diagnostics: list[D2LPolicyParseDiagnostic],
	role: str,
) -> tuple[str, str] | None:
	text = atom.strip()
	if not text:
		return None
	state_match = re.fullmatch(r"(.+?)(>0|=0)", text)
	change_match = re.fullmatch(r"(.+?)\s+(INC|DEC|ADD|DEL|NIL)s?", text)
	if state_match:
		feature = state_match.group(1).strip()
		value = state_match.group(2)
		feature_id = _ensure_d2l_feature(
			feature,
			feature_ids=feature_ids,
			feature_expressions=feature_expressions,
			predicate_arities=predicate_arities,
			diagnostics=diagnostics,
		)
		boolean_feature = feature_expressions[feature_id].startswith("b_nullary(")
		if role == "effect":
			diagnostics.append(
				D2LPolicyParseDiagnostic(
					line=atom,
					reason="state_value_atom_inside_effect_set_is_not_executable",
				),
			)
			return None
		operator = (
			"c_b_pos"
			if boolean_feature and value == ">0"
			else "c_b_neg"
			if boolean_feature
			else "c_n_gt"
			if value == ">0"
			else "c_n_eq"
		)
		return operator, feature_id
	if change_match:
		feature = change_match.group(1).strip()
		change = change_match.group(2)
		feature_id = _ensure_d2l_feature(
			feature,
			feature_ids=feature_ids,
			feature_expressions=feature_expressions,
			predicate_arities=predicate_arities,
			diagnostics=diagnostics,
		)
		boolean_feature = feature_expressions[feature_id].startswith("b_nullary(")
		if role == "condition":
			diagnostics.append(
				D2LPolicyParseDiagnostic(
					line=atom,
					reason="transition_change_atom_inside_condition_is_not_a_state_guard",
				),
			)
			return None
		if change == "NIL":
			diagnostics.append(
				D2LPolicyParseDiagnostic(
					line=atom,
					reason="nil_feature_change_has_no_executable_asl_body",
				),
			)
			return None
		operator = (
			"e_b_pos"
			if boolean_feature and change in {"INC", "ADD"}
			else "e_b_neg"
			if boolean_feature
			else "e_n_inc"
			if change in {"INC", "ADD"}
			else "e_n_dec"
		)
		return operator, feature_id
	diagnostics.append(
		D2LPolicyParseDiagnostic(line=atom, reason="unrecognized_d2l_policy_atom"),
	)
	return None


def _ensure_d2l_feature(
	feature: str,
	*,
	feature_ids: dict[str, str],
	feature_expressions: dict[str, str],
	predicate_arities: Mapping[str, int],
	diagnostics: list[D2LPolicyParseDiagnostic],
) -> str:
	if feature in feature_ids:
		return feature_ids[feature]
	feature_id = f"d2l_f{len(feature_ids) + 1}"
	feature_ids[feature] = feature_id
	expression, reason = _d2l_feature_to_dlplan_expression(
		feature,
		predicate_arities=predicate_arities,
	)
	feature_expressions[feature_id] = expression
	if reason is not None:
		diagnostics.append(D2LPolicyParseDiagnostic(line=feature, reason=reason))
	return feature_id


def _d2l_feature_to_dlplan_expression(
	feature: str,
	*,
	predicate_arities: Mapping[str, int],
) -> tuple[str, str | None]:
	text = feature.strip()
	match = re.fullmatch(r"(Atom|Bool|Num)\[(.+)\]", text)
	if not match:
		return (
			f"d2l_unsupported({text})",
			"unsupported_d2l_feature_wrapper",
		)
	kind = match.group(1)
	concept = match.group(2).strip()
	if kind == "Atom":
		if predicate_arities.get(concept) == 0:
			return f"b_nullary({concept})", None
		return (
			f"d2l_unsupported({text})",
			"atom_feature_requires_declared_nullary_predicate",
		)
	converted = _d2l_concept_to_dlplan(concept, predicate_arities=predicate_arities)
	if converted is None:
		return (
			f"d2l_unsupported({text})",
			"unsupported_d2l_description_logic_feature",
		)
	return f"n_count({converted})", None


def _d2l_concept_to_dlplan(
	concept: str,
	*,
	predicate_arities: Mapping[str, int],
) -> str | None:
	text = concept.strip()
	if predicate_arities.get(text) == 1:
		return f"c_primitive({text},0)"
	equal = re.fullmatch(r"Equal\(([^(),]+)_g,([^(),]+)\)", text)
	if equal and equal.group(1) == equal.group(2):
		predicate = equal.group(1)
		arity = predicate_arities.get(predicate)
		if arity == 1:
			return (
				f"c_equal(c_primitive({predicate},0),"
				f"c_primitive({predicate}_g,0))"
			)
		if arity == 2:
			return (
				f"c_equal(r_primitive({predicate},0,1),"
				f"r_primitive({predicate}_g,0,1))"
			)
	and_parts = _d2l_binary_concept_args(text, "And")
	if and_parts is not None:
		left = _d2l_concept_to_dlplan(
			and_parts[0],
			predicate_arities=predicate_arities,
		)
		right = _d2l_concept_to_dlplan(
			and_parts[1],
			predicate_arities=predicate_arities,
		)
		if left is not None and right is not None:
			return f"c_and({left},{right})"
	not_part = _d2l_unary_concept_arg(text, "Not")
	if not_part is not None:
		converted = _d2l_concept_to_dlplan(
			not_part,
			predicate_arities=predicate_arities,
		)
		if converted is not None:
			return f"c_not({converted})"
	return None


def _d2l_unary_concept_arg(text: str, operator: str) -> str | None:
	prefix = f"{operator}("
	if not text.startswith(prefix) or not text.endswith(")"):
		return None
	return text[len(prefix) : -1]


def _d2l_binary_concept_args(text: str, operator: str) -> tuple[str, str] | None:
	prefix = f"{operator}("
	if not text.startswith(prefix) or not text.endswith(")"):
		return None
	inner = text[len(prefix) : -1]
	depth = 0
	for index, character in enumerate(inner):
		if character == "(":
			depth += 1
		elif character == ")":
			depth -= 1
		elif character == "," and depth == 0:
			return inner[:index].strip(), inner[index + 1 :].strip()
	return None


def _dlplan_rule_text(
	*,
	conditions: tuple[tuple[str, str], ...],
	effects: tuple[tuple[str, str], ...],
) -> str:
	condition_text = " ".join(
		f"(:{operator} {feature_id})"
		for operator, feature_id in conditions
	)
	effect_text = " ".join(
		f"(:{operator} {feature_id})"
		for operator, feature_id in effects
	)
	return f"(:rule (:conditions {condition_text}) (:effects {effect_text}))"


def _extract_features(policy_text: str, section_name: str) -> dict[str, str]:
	section = _extract_form(policy_text, f"(:{section_name}")
	if not section:
		return {}
	return {
		feature_id: feature_repr
		for feature_id, feature_repr in re.findall(
			r'\(([A-Za-z_][A-Za-z0-9_]*|\d+)\s+"([^"]+)"\)',
			section,
		)
	}


def _parse_rule(rule_text: str) -> SketchRule:
	return SketchRule(
		conditions=tuple(
			SketchCondition(operator=operator, feature_id=feature_id)
			for operator, feature_id in _extract_feature_atoms(rule_text, "conditions")
		),
		effects=tuple(
			SketchEffect(operator=operator, feature_id=feature_id)
			for operator, feature_id in _extract_feature_atoms(rule_text, "effects")
		),
		raw=" ".join(rule_text.split()),
	)


def _extract_feature_atoms(rule_text: str, section_name: str) -> tuple[tuple[str, str], ...]:
	section = _extract_form(rule_text, f"(:{section_name}")
	if not section:
		return ()
	return tuple(
		(operator, feature_id)
		for operator, feature_id in re.findall(
			r'\(:([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*|\d+)\)',
			section,
		)
	)


def _extract_form(text: str, marker: str) -> str:
	start = text.find(marker)
	if start == -1:
		return ""
	depth = 0
	in_string = False
	escaped = False
	for index in range(start, len(text)):
		character = text[index]
		if escaped:
			escaped = False
			continue
		if character == "\\" and in_string:
			escaped = True
			continue
		if character == '"':
			in_string = not in_string
			continue
		if in_string:
			continue
		if character == "(":
			depth += 1
		elif character == ")":
			depth -= 1
			if depth == 0:
				return text[start : index + 1]
	return ""


def _extract_top_level_rules(policy_text: str) -> tuple[str, ...]:
	rules: list[str] = []
	index = 0
	while True:
		start = policy_text.find("(:rule", index)
		if start == -1:
			break
		depth = 0
		end = start
		for end in range(start, len(policy_text)):
			char = policy_text[end]
			if char == "(":
				depth += 1
			elif char == ")":
				depth -= 1
				if depth == 0:
					rules.append(" ".join(policy_text[start : end + 1].split()))
					break
		index = end + 1
	return tuple(rules)


def _observed_git_commit(path: Path) -> str | None:
	head_file = path / ".git" / "HEAD"
	if not head_file.exists():
		return None
	head = head_file.read_text(encoding="utf-8").strip()
	if head.startswith("ref:"):
		ref = head.removeprefix("ref:").strip()
		ref_file = path / ".git" / ref
		if ref_file.exists():
			return ref_file.read_text(encoding="utf-8").strip()
	return head or None


def _pin_status(manifest: BackendManifest) -> str:
	if not manifest.present:
		return "missing"
	if manifest.observed_commit is None:
		return "unknown"
	if manifest.observed_commit.startswith(manifest.expected_commit[:12]):
		return "ok"
	return "mismatch"


def _backend_failure_modes(
	*,
	manifest: BackendManifest,
	pin_status: str,
) -> list[str]:
	failures: list[str] = []
	if not manifest.present:
		failures.append("missing_backend")
	elif pin_status == "mismatch":
		failures.append("pin_mismatch")
	elif pin_status == "unknown":
		failures.append("unknown_git_commit")
	return failures


def _default_backend_python(manifest: BackendManifest) -> str:
	candidates = (
		manifest.path.parent / ".venv" / "bin" / "python",
		manifest.path / ".venv" / "bin" / "python",
	)
	for candidate in candidates:
		if candidate.exists():
			return str(candidate)
	return shutil.which("python3") or "python3"
