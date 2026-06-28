#!/usr/bin/env python3
"""End-to-end NL-to-LTLf goal evaluation over a train/test instance split.

Pipeline (per supported domain):

1. Synthesize the domain-level AgentSpeak(L) plan library from the TRAINING
   instances (the first ~2/3 of the split).
2. For each HELD-OUT instance, take the LTLf goal generated from natural language
   (stored in ``queries_LTLf.json`` by ``generate_ltlf_dataset.py``) and test whether
   the training-built library satisfies that goal:
   - Achievement goal (pure conjunction, no temporal operators): run the library
     from the held-out initial state against the conjunction's fluent atoms.
   - Temporal extended goal (TEG): the ordered eventualities are executed as a
     sequence of achievement sub-goals threaded through the same library, mirroring
     the DFA-controller-over-achievement-library design in BDI.md.

The LTLf formulas are consumed, not regenerated here, so this step needs no live
language-model access (only the offline synthesis/execution stack).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from domain_level_planning.library_executor import (  # noqa: E402
	execute_library_from_state,
)
from domain_level_planning.library_synthesis import (  # noqa: E402
	synthesize_domain_level_asl_library,
)
from domain_level_planning.pddl_types import object_type_atoms  # noqa: E402
from low_level_planning.strips_state import (  # noqa: E402
	STRIPSStateSimulator,
	fact_to_signature,
)
from temporal_specification import extract_formula_atoms_in_order  # noqa: E402
from utils.pddl_parser import PDDLParser  # noqa: E402
from utils.symbol_normalizer import SymbolNormalizer  # noqa: E402

DEFAULT_LTLF_DATASET = PROJECT_ROOT / "src" / "benchmark_data" / "queries_LTLf.json"
_TEMPORAL_OPERATOR_PATTERN = re.compile(r"(?<![A-Za-z0-9_])(?:WX|[FGXUR])(?![A-Za-z0-9_])")


def is_temporal_goal(ltlf_formula: str) -> bool:
	"""True when the formula uses any temporal operator (otherwise pure achievement)."""

	return bool(_TEMPORAL_OPERATOR_PATTERN.search(str(ltlf_formula or "")))


def _goal_fact(atom: str) -> str:
	name, arguments = SymbolNormalizer().parse_predicate_string(atom)
	return f"goal_{name}" if not arguments else f"goal_{name}({', '.join(arguments)})"


def _goal_atom(atom: str) -> str:
	name, arguments = SymbolNormalizer().parse_predicate_string(atom)
	return name if not arguments else f"{name}({', '.join(arguments)})"


def _initial_state(*, problem_file: Path, simulator: STRIPSStateSimulator) -> frozenset[str]:
	problem = PDDLParser.parse_problem(problem_file)
	return frozenset(
		(
			*(fact_to_signature(fact) for fact in problem.init_facts if fact.is_positive),
			*object_type_atoms(problem, simulator.domain.types),
		),
	)


def evaluate_goal(
	*,
	plan_library,
	domain_file: Path,
	problem_file: Path,
	ltlf_formula: str,
	max_steps: int,
	max_depth: int,
) -> dict[str, object]:
	"""Evaluate one generated LTLf goal against the library on one held-out instance."""

	simulator = STRIPSStateSimulator(str(domain_file))
	atoms = list(extract_formula_atoms_in_order(ltlf_formula))
	problem_name = PDDLParser.parse_problem(problem_file).name
	temporal = is_temporal_goal(ltlf_formula)
	state = _initial_state(problem_file=problem_file, simulator=simulator)

	if not temporal:
		# Achievement goal: satisfy the whole conjunction at once.
		result = execute_library_from_state(
			plan_library=plan_library,
			domain_file=domain_file,
			problem_name=problem_name,
			initial_state=state,
			goal_facts=tuple(_goal_fact(atom) for atom in atoms),
			goal_atoms=tuple(_goal_atom(atom) for atom in atoms),
			max_steps=max_steps,
			max_depth=max_depth,
		)
		return {
			"kind": "achievement",
			"solved": bool(result.solved),
			"failure_reason": result.failure_reason,
			"steps": list(result.steps),
		}

	# TEG: execute ordered eventualities as sequential achievement sub-goals.
	completed_steps: list[str] = []
	for index, atom in enumerate(atoms):
		result = execute_library_from_state(
			plan_library=plan_library,
			domain_file=domain_file,
			problem_name=f"{problem_name}#teg{index + 1}",
			initial_state=state,
			goal_facts=(_goal_fact(atom),),
			goal_atoms=(_goal_atom(atom),),
			max_steps=max_steps,
			max_depth=max_depth,
		)
		completed_steps.extend(result.steps)
		if not result.solved:
			return {
				"kind": "temporal_extended_goal",
				"solved": False,
				"failure_reason": f"sub-goal {index + 1} ({atom}) failed: {result.failure_reason}",
				"completed_subgoals": index,
				"subgoal_count": len(atoms),
				"steps": completed_steps,
			}
		state = result.final_state
	return {
		"kind": "temporal_extended_goal",
		"solved": True,
		"failure_reason": None,
		"completed_subgoals": len(atoms),
		"subgoal_count": len(atoms),
		"steps": completed_steps,
	}


def _load_split_domain(split_file: Path, domain: str) -> dict[str, object]:
	manifest = json.loads(split_file.read_text(encoding="utf-8"))
	entry = (manifest.get("domains") or {}).get(domain)
	if not entry:
		raise ValueError(f"Split manifest {split_file} has no entry for domain {domain!r}.")
	return entry


def run_domain_eval(
	*,
	domain: str,
	domain_file: Path,
	train_problems: Sequence[Path],
	test_problems: Sequence[Path],
	ltlf_dataset: Path,
	max_steps: int,
	max_depth: int,
) -> dict[str, object]:
	"""Synthesize from train problems and evaluate generated goals on test problems."""

	if not train_problems:
		raise ValueError("At least one training problem is required.")
	synthesis = synthesize_domain_level_asl_library(
		domain_file=domain_file,
		training_problem_files=tuple(str(path) for path in train_problems),
	)
	plan_library = synthesis.plan_library

	dataset = json.loads(ltlf_dataset.read_text(encoding="utf-8"))
	cases = ((dataset.get("domains") or {}).get(domain) or {}).get("cases") or {}
	test_basenames = {Path(path).name for path in test_problems}
	problem_dir = domain_file.parent / "problems"

	results = []
	for query_id, case in cases.items():
		problem_basename = str(case.get("problem_file") or "").strip()
		if problem_basename not in test_basenames:
			continue
		ltlf_formula = str(case.get("ltlf_formula") or "").strip()
		if not ltlf_formula:
			continue
		problem_file = problem_dir / problem_basename
		outcome = evaluate_goal(
			plan_library=plan_library,
			domain_file=domain_file,
			problem_file=problem_file,
			ltlf_formula=ltlf_formula,
			max_steps=max_steps,
			max_depth=max_depth,
		)
		results.append(
			{
				"query_id": query_id,
				"problem_file": problem_basename,
				"ltlf_formula": ltlf_formula,
				**outcome,
			},
		)

	solved = sum(1 for item in results if item["solved"])
	return {
		"domain": domain,
		"library_plan_count": len(plan_library.plans),
		"train_problem_count": len(train_problems),
		"evaluated_goal_count": len(results),
		"coverage": {
			"solved_count": solved,
			"total": len(results),
			"ratio": (solved / len(results)) if results else 0.0,
		},
		"results": results,
	}


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--query-domain", required=True, help="Domain key to evaluate.")
	parser.add_argument("--split-file", type=Path, help="Split manifest from generate_domain_instance_split.py.")
	parser.add_argument("--domain-file", type=Path, help="Override PDDL domain file.")
	parser.add_argument("--train-problem", action="append", default=[], help="Training PDDL problem (repeatable).")
	parser.add_argument("--test-problem", action="append", default=[], help="Held-out PDDL problem (repeatable).")
	parser.add_argument("--query-dataset", type=Path, default=DEFAULT_LTLF_DATASET, help="Stored LTLf dataset.")
	parser.add_argument("--output", type=Path, help="Optional report output JSON path.")
	parser.add_argument("--max-steps", type=int, default=2000)
	parser.add_argument("--max-depth", type=int, default=200)
	args = parser.parse_args()

	if args.split_file:
		entry = _load_split_domain(args.split_file.resolve(), args.query_domain)
		domain_file = Path(args.domain_file or (PROJECT_ROOT / str(entry["domain_file"]))).resolve()
		train_problems = [(PROJECT_ROOT / str(path)).resolve() for path in entry["train"]]
		test_problems = [(PROJECT_ROOT / str(path)).resolve() for path in entry["test"]]
	else:
		if not args.domain_file:
			parser.error("--domain-file is required when --split-file is not provided.")
		domain_file = args.domain_file.resolve()
		train_problems = [Path(path).resolve() for path in args.train_problem]
		test_problems = [Path(path).resolve() for path in args.test_problem]

	report = run_domain_eval(
		domain=args.query_domain,
		domain_file=domain_file,
		train_problems=train_problems,
		test_problems=test_problems,
		ltlf_dataset=args.query_dataset.resolve(),
		max_steps=args.max_steps,
		max_depth=args.max_depth,
	)
	if args.output:
		args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
		args.output.resolve().write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
	print(
		f"{report['domain']}: solved "
		f"{report['coverage']['solved_count']}/{report['coverage']['total']} "
		f"(library plans={report['library_plan_count']})",
	)
	print(json.dumps(report, indent=2))


if __name__ == "__main__":
	main()
