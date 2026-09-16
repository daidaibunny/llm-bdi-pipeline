"""Check metric eligibility against an uploaded definition, without editing it."""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from time import monotonic
from zipfile import ZipFile

from evaluation.coverage_model import PDDLExecutionModel
from evaluation.structural_coverage import count_contexts, ground_boolean_context
from plan_library.models import PlanLibrary


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
	return hashlib.sha256(path.read_bytes()).hexdigest()


def exact(value: Fraction) -> dict[str, int]:
	return {"numerator": value.numerator, "denominator": value.denominator}


def audit(source_zip: Path, audit_dir: Path) -> dict:
	"""Return exact scoped counts and explicit reasons a final metric is unavailable."""
	with ZipFile(source_zip) as archive:
		members = [name for name in archive.namelist()
			if name.endswith("/outline/sections/preliminaries.tex")]
		if len(members) != 1:
			raise ValueError("Expected exactly one supervisor preliminaries source")
		definition = archive.read(members[0])
	labels = ("def:correctness-plan-instance", "def:correctness-plan-template",
		"eq:basic-coverage-plan", "eq:extended-coverage-plan", "eq:extended-coverage-goal")
	lines = definition.decode().splitlines()
	locations = {label: next(index + 1 for index, line in enumerate(lines)
		if f"\\label{{{label}}}" in line) for label in labels}
	protocol = json.loads((audit_dir / "protocol.json").read_text())
	summary = json.loads((audit_dir / "summary.json").read_text())
	if sha256(audit_dir / "protocol.json") != summary["protocol_sha256"]:
		raise ValueError("Protocol hash mismatch")
	for filename, expected in summary["evaluator_files_sha256"].items():
		if sha256(ROOT / filename) != expected:
			raise ValueError(f"Evaluator changed: {filename}")
	rows = defaultdict(list)
	for row in summary["records"]:
		rows[row["seed"], row["domain"]].append(row)
	results, bindings = [], []
	for record in protocol["libraries"]:
		start = monotonic()
		seed, domain = record["seed"], record["domain"]
		filename = audit_dir / record["file"]
		if sha256(filename) != record["sha256"]:
			raise ValueError("Frozen library hash mismatch")
		library = PlanLibrary.from_dict(json.loads(filename.read_text()))
		plans = {plan.plan_name: plan for plan in library.plans}
		if len(plans) != len(library.plans):
			raise ValueError("Ambiguous plan names")
		refuted = {}
		models = {}
		by_template = defaultdict(list)
		for row in rows[seed, domain]:
			if row["problem"] not in models:
				case = protocol["cases"][row["case_index"]]
				if case["problem"] != row["problem"]:
					raise ValueError("Problem identity mismatch")
				if sha256(ROOT / case["problem"]) != case["problem_sha256"]:
					raise ValueError("Problem changed since frozen audit")
				if sha256(ROOT / case["domain_file"]) != case["domain_sha256"]:
					raise ValueError("Domain changed since frozen audit")
				models[row["problem"]] = PDDLExecutionModel(
					ROOT / case["domain_file"],
					ROOT / row["problem"], library)
			model = models[row["problem"]]
			for obligation in row["obligations"]:
				plan = plans[obligation["plan"]]
				if obligation["status"] == "fail":
					if not row["saturated"]:
						raise ValueError("A negative lacks exhaustive saturation")
					refuted.setdefault(plan.plan_name, {"case_index": row["case_index"],
						"problem": row["problem"], "binding": obligation["binding"]})
				if model.catalog.function_types:
					continue
				context = ground_boolean_context(plan.context, obligation["binding"], model)
				value = count_contexts((context,)).basic[0]
				item = {"seed": seed, "domain": domain, "problem": row["problem"],
					"plan": plan.plan_name, "binding": obligation["binding"],
					"basic_coverage": exact(value)}
				bindings.append(item)
				by_template[row["problem"], plan.plan_name].append((value, item))
		varying = []
		for (problem, plan), instances in by_template.items():
			low = min(instances, key=lambda pair: pair[0])
			high = max(instances, key=lambda pair: pair[0])
			if low[0] != high[0]:
				varying.append({"problem": problem, "plan": plan,
					"lower": low[1], "upper": high[1]})
		numeric = bool(next(iter(models.values())).catalog.function_types)
		recursive = [plan.plan_name for plan in library.plans if any(
			step.kind == "subgoal" and step.symbol == plan.trigger.symbol
			and step.arguments == plan.trigger.arguments for step in plan.body)]
		results.append({"domain": domain, "seed": seed, "templates": len(plans),
			"numeric_scope_undefined": numeric, "direct_recursive_templates": recursive,
			"universal_correctness": ("outside_boolean_definition" if numeric else
				"refuted" if refuted else "not_established"),
			"completion_counterexamples": refuted,
			"binding_invariance_counterexamples": varying,
			"extended_coverage": None,
			"extended_coverage_status": "requires_measure_binding_and_recursion_contract",
			"global_coverage_optimality": "not_established"})
		print(f"[definition audit] seed={seed} {domain} templates={len(plans)} "
			f"counterexamples={len(refuted)} {monotonic()-start:.2f}s", flush=True)
	return {"schema_version": 1, "final_paper_metrics_complete": False,
		"definition_evaluator_sha256": {str(path.relative_to(ROOT)): sha256(path)
			for path in (Path(__file__), ROOT / "src/evaluation/structural_coverage.py")},
		"source_zip_sha256": sha256(source_zip), "source_member": members[0],
		"source_tex_sha256": hashlib.sha256(definition).hexdigest(),
		"definition_lines": locations, "diagnostic_summary_sha256": sha256(audit_dir / "summary.json"),
		"scope": "exact Boolean counts for observed ground bindings; universal refutations only",
		"basic_coverage_state_measure": "uniform over all Boolean worlds, with object types fixed",
		"not_claimed": ["all bindings tested", "all states execution-checked",
			"semantic execution coverage equals structural extended coverage",
			"sample success proves universal correctness", "coverage maximization"],
		"open_definition_requirements": [
			"Ground-binding aggregation: the same template need not have equal context coverage for all substitutions.",
			"Overlap convention: a raw sum can exceed one; the supplied coverage paper explicitly requires overlap adjustment.",
			"Recursive equations: no fixed-point selection or existence/uniqueness condition is specified.",
			"Numeric worlds: integer-valued functions need a declared state space and measure.",
		], "libraries": results, "exact_ground_context_counts": bindings}


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--source-zip", type=Path, required=True)
	parser.add_argument("--audit-dir", type=Path,
		default=ROOT / "paper_artifacts/semantic_coverage/v1")
	parser.add_argument("--output", type=Path, required=True)
	args = parser.parse_args()
	if args.output.exists():
		parser.error("Refusing to overwrite an existing definition audit")
	result = audit(args.source_zip, args.audit_dir)
	args.output.parent.mkdir(parents=True, exist_ok=True)
	args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
	print(f"[complete] {args.output}; final-paper metrics are not yet established", flush=True)


if __name__ == "__main__":
	main()
