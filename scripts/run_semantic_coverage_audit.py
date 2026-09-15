"""Freeze an outcome-independent audit scope, then analyze unchanged libraries."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
from time import monotonic

from evaluation.coverage_audit import metric_bounds, problem_targets
from evaluation.coverage_model import PDDLExecutionModel
from evaluation.execution_coverage import (
	Call, Proof, UnsupportedModel, analyze_library, validate_proof,
)
from plan_library.models import PlanLibrary
from utils.pddl_parser import PDDLParser


ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
	return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: object) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def freeze(args: argparse.Namespace) -> None:
	output = args.output.resolve()
	if (output / "protocol.json").exists():
		raise ValueError("A frozen protocol already exists; use a new output directory")
	reference = json.loads(args.reference_summary.read_text())
	domains = sorted(row["domain"] for row in reference["domains"])
	seeds = reference["protocol"]["seeds"]
	cases, libraries = [], []
	population = None
	for seed in seeds:
		run = args.source_root / f"{args.source_root.parent.name}-seed{seed}-full"
		records = [json.loads(line) for line in
			(run / "validation_results.jsonl").read_text().splitlines() if line.strip()]
		this_population = []
		for domain in domains:
			rows = sorted((r for r in records if r["domain"] == domain),
				key=lambda r: r["test_index"])[:args.instances_per_domain]
			if len(rows) != args.instances_per_domain:
				raise ValueError(f"Incomplete registered population: {seed}/{domain}")
			library_file = run / "domain_libraries" / domain / "plan_library.json"
			original = json.loads(library_file.read_text())
			if original.get("initial_beliefs"):
				raise UnsupportedModel("Audit requires world beliefs from the PDDL instance")
			projection = {"domain_name": original["domain_name"], "initial_beliefs": [],
				"plans": [{key: plan[key] for key in ("plan_name", "trigger", "context", "body")}
					for plan in original["plans"]]}
			snapshot = output / "libraries" / f"seed{seed}" / f"{domain}.json"
			write_json(snapshot, projection)
			libraries.append({"seed": seed, "domain": domain,
				"file": str(snapshot.relative_to(output)), "sha256": digest(snapshot),
				"original_json_sha256": digest(library_file),
				"template_count": len(projection["plans"])})
			domain_file = ROOT / "src" / "domains" / domain / "domain.pddl"
			frozen_domain = run / "input_snapshot" / domain / "domain.pddl"
			if digest(domain_file) != digest(frozen_domain):
				raise ValueError(f"Domain changed since full evaluation: {domain}")
			for record in rows:
				problem_file = ROOT / "src" / "domains" / domain / "test" / (
					Path(record["problem_file"]).name)
				frozen_problem = run / "input_snapshot" / domain / "test" / problem_file.name
				if digest(problem_file) != digest(frozen_problem):
					raise ValueError(f"Problem changed since full evaluation: {problem_file}")
				problem = PDDLParser.parse_problem(problem_file)
				for target in problem_targets(problem):
					case = {"domain": domain, "problem": str(problem_file.relative_to(ROOT)),
						"problem_sha256": digest(problem_file),
						"domain_file": str(domain_file.relative_to(ROOT)),
						"domain_sha256": digest(domain_file), "goal": asdict(target)}
					this_population.append(case)
					if population is None:
						cases.append(case)
		if population is not None and this_population != population:
			raise ValueError("Different input populations across seeds")
		population = this_population
	protocol = {"schema_version": 1, "scope": "held_out_initial_state_atomic_goal_audit",
		"selection": "first instances by frozen full-run test_index, all distinct atomic goals",
		"instances_per_domain": args.instances_per_domain, "seeds": seeds,
		"source_run": args.source_root.parent.name, "reference_sha256": digest(args.reference_summary),
		"reference_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
			text=True).strip(), "max_seconds_per_goal": args.max_seconds,
		"max_configurations_per_goal": args.max_configurations,
		"max_binding_join_attempts_per_goal": args.max_join_attempts,
		"branch_correctness": "existential complete execution per applicable full binding",
		"unknown_policy": "unresolved obligations remain unknown; incomplete binding counts are N/A",
		"state_scope": "initial world state of each selected held-out instance",
		"libraries": libraries, "cases": cases}
	write_json(output / "protocol.json", protocol)
	print(f"[freeze] {len(cases)} goal-state pairs x {len(seeds)} seeds; {output}", flush=True)


def proof_graph(proofs: tuple[Proof | None, ...]) -> dict[str, object]:
	indices: dict[int, int] = {}
	nodes = []
	pending = [proof for proof in proofs if proof is not None]
	while pending:
		proof = pending.pop()
		if id(proof) in indices:
			continue
		indices[id(proof)] = len(nodes)
		nodes.append(proof)
		pending.extend(child for child in proof.children if isinstance(child, Proof))
	return {"roots": [indices[id(proof)] if proof is not None else None for proof in proofs],
		"nodes": [{"branch": asdict(proof.branch),
			"start_state_sha256": proof.start.fingerprint(),
			"end_state_sha256": proof.end.fingerprint(),
			"children": [{"proof": indices[id(child)]} if isinstance(child, Proof)
				else {"action": asdict(child)} for child in proof.children]} for proof in nodes]}


def audit_case(model: PDDLExecutionModel, goal: Call, protocol: dict) -> dict:
	start = monotonic()
	model.reset_budget(protocol["max_seconds_per_goal"],
		protocol["max_binding_join_attempts_per_goal"])
	result = analyze_library(model, ((goal, model.initial),),
		max_seconds=protocol["max_seconds_per_goal"],
		max_configurations=protocol["max_configurations_per_goal"])
	elapsed = monotonic() - start
	proofs = result.root_proofs + result.obligation_proofs
	seen = set()
	for proof in proofs:
		if proof is not None and id(proof) not in seen:
			validate_proof(model, proof, materialize_trace=False)
			seen.add(id(proof))
	return {"coverage": result.coverage, "coverage_bounds": metric_bounds(result.coverage),
		"correctness": result.correctness,
		"correctness_bounds": metric_bounds(result.correctness)
			if result.root_enumeration_complete else None,
		"root_enumeration_complete": result.root_enumeration_complete,
		"all_obligations_resolved": result.complete, "saturated": result.saturated,
		"reason": result.reason, "analysis_seconds": elapsed,
		"verification_seconds": monotonic() - start - elapsed,
		"request_count": result.request_count, "return_count": result.return_count,
		"configuration_count": result.configuration_count,
		"obligations": [{"plan": branch.name, "binding": dict(branch.binding), "status": status}
			for branch, _, status in result.obligations],
		"witnesses": proof_graph(proofs), "witnesses_replayed": True}


def totals(rows: list[dict], metric: str) -> dict[str, int]:
	return {key: sum(row[metric][key] for row in rows)
		for key in ("pass", "fail", "unknown", "total")}


def aggregate(rows: list[dict], seeds: list[int], domains: list[str]) -> dict:
	groups = []
	for domain in [*domains, "ALL"]:
		selected = [row for row in rows if domain == "ALL" or row["domain"] == domain]
		seed_rows = []
		for seed in seeds:
			subset = [row for row in selected if row["seed"] == seed]
			enumeration_complete = all(row["root_enumeration_complete"] for row in subset)
			seed_rows.append({"seed": seed, "coverage": totals(subset, "coverage"),
				"correctness": totals(subset, "correctness"),
				"coverage_bounds": metric_bounds(totals(subset, "coverage")),
				"correctness_bounds": metric_bounds(totals(subset, "correctness"))
					if enumeration_complete else None})
		group = {"domain": domain, "seed_results": seed_rows,
			"coverage": totals(selected, "coverage"), "correctness": totals(selected, "correctness"),
			"incomplete_binding_enumeration_cases": sum(not row["root_enumeration_complete"]
				for row in selected),
			"tested_template_seed_pairs": len({(row["seed"], row["domain"], obligation["plan"])
				for row in selected for obligation in row["obligations"]})}
		for metric in ("coverage", "correctness"):
			bounds = [row[f"{metric}_bounds"] for row in seed_rows]
			group[f"{metric}_five_seed"] = None if any(b is None for b in bounds) else {
				bound: {"mean": statistics.mean(b[bound] for b in bounds),
					"sample_sd": statistics.stdev(b[bound] for b in bounds)}
				for bound in ("lower", "upper")}
		groups.append(group)
	return {"domains": groups}


def run(args: argparse.Namespace) -> None:
	output = args.protocol.resolve().parent
	protocol = json.loads(args.protocol.read_text())
	rows = []
	for library_record in protocol["libraries"]:
		seed, domain = library_record["seed"], library_record["domain"]
		library_path = output / library_record["file"]
		if digest(library_path) != library_record["sha256"]:
			raise ValueError(f"Frozen library changed: {library_path}")
		library = PlanLibrary.from_dict(json.loads(library_path.read_text()))
		for index, case in enumerate(protocol["cases"]):
			if case["domain"] != domain:
				continue
			for key in ("domain_file", "problem"):
				sha_key = "domain_sha256" if key == "domain_file" else "problem_sha256"
				if digest(ROOT / case[key]) != case[sha_key]:
					raise ValueError(f"Frozen input changed: {case[key]}")
			goal = Call(case["goal"]["symbol"], tuple(case["goal"]["arguments"]))
			model = PDDLExecutionModel(ROOT / case["domain_file"], ROOT / case["problem"], library)
			result = audit_case(model, goal, protocol)
			result.update({"seed": seed, "domain": domain, "case_index": index,
				"problem": case["problem"], "goal": case["goal"]})
			write_json(output / "cases" / f"seed{seed}" / f"case-{index:04d}.json", result)
			rows.append({key: value for key, value in result.items() if key != "witnesses"})
			print(f"[audit] seed={seed} {domain} {Path(case['problem']).stem} "
				f"goal={goal.symbol}{goal.arguments} coverage={result['coverage']} "
				f"correctness={result['correctness']} {result['analysis_seconds']:.2f}s", flush=True)
	summary = aggregate(rows, protocol["seeds"], sorted({r["domain"] for r in rows}))
	summary.update({"protocol_sha256": digest(args.protocol), "records": rows,
		"evaluator_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
			text=True).strip(), "evaluator_files_sha256": {str(p.relative_to(ROOT)): digest(p)
			for p in (Path(__file__), ROOT / "src/evaluation/execution_coverage.py",
				ROOT / "src/evaluation/coverage_model.py", ROOT / "src/evaluation/coverage_audit.py")}})
	write_json(output / "summary.json", summary)
	print(f"[complete] {output / 'summary.json'}", flush=True)


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	subparsers = parser.add_subparsers(dest="command", required=True)
	freeze_parser = subparsers.add_parser("freeze")
	freeze_parser.add_argument("--source-root", type=Path, required=True)
	freeze_parser.add_argument("--reference-summary", type=Path,
		default=ROOT / "paper_artifacts/gp2pl_evaluation/v1/five_seed_full_compiler_summary.json")
	freeze_parser.add_argument("--output", type=Path, required=True)
	freeze_parser.add_argument("--instances-per-domain", type=int, default=3)
	freeze_parser.add_argument("--max-seconds", type=float, default=5.0)
	freeze_parser.add_argument("--max-configurations", type=int, default=10_000)
	freeze_parser.add_argument("--max-join-attempts", type=int, default=1_000_000)
	run_parser = subparsers.add_parser("run")
	run_parser.add_argument("--protocol", type=Path, required=True)
	args = parser.parse_args()
	if args.command == "freeze":
		if min(args.instances_per_domain, args.max_seconds,
				args.max_configurations, args.max_join_attempts) <= 0:
			parser.error("All analysis budgets and population sizes must be positive")
		freeze(args)
	else:
		run(args)


if __name__ == "__main__":
	main()
