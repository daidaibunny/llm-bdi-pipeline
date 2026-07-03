"""
Adapter for MOOSE readable policy artifacts.

MOOSE stores trained policies as Python pickle files, but its official
interface exposes a stable text form via `policy <model> --dump-policy`. This
module consumes that readable decision-list form instead of importing MOOSE
runtime classes into the main package.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.models import PlanLibrary

from .policy_program import LearnedPolicyRule
from .policy_program import LiftedPolicyProgram
from .policy_program import PolicyModule


@dataclass(frozen=True)
class MooseAtom:
	"""One lifted atom or action call in a MOOSE readable policy rule."""

	predicate: str
	arguments: tuple[str, ...]

	def to_call(self, variable_map: dict[str, str]) -> str:
		return _call(self.predicate, tuple(variable_map.get(arg, arg) for arg in self.arguments))


@dataclass(frozen=True)
class MooseReadableRule:
	"""One MOOSE first-order decision-list rule parsed from readable text."""

	precedence: str
	variables: tuple[str, ...]
	state_conditions: tuple[MooseAtom, ...]
	goal_conditions: tuple[MooseAtom, ...]
	actions: tuple[MooseAtom, ...]
	source_rule: str

	@property
	def is_singleton_goal_rule(self) -> bool:
		return len(self.goal_conditions) == 1

	def variable_map(self) -> dict[str, str]:
		return {variable: _agentspeak_variable(variable) for variable in self.variables}


@dataclass(frozen=True)
class MooseAtomicLibraryQualityReport:
	"""Structural quality report for direct MOOSE-to-ASL atomic libraries."""

	plan_count: int
	goal_symbol_count: int
	goal_symbols: tuple[str, ...]
	max_plans_per_goal_symbol: int
	max_body_step_count: int
	primitive_action_step_count: int
	subgoal_step_count: int
	singleton_macro_library_ready: bool
	compact_recursive_module_ready: bool
	artifact_classification: str
	warnings: tuple[str, ...] = ()

	def to_dict(self) -> dict[str, object]:
		return {
			"plan_count": self.plan_count,
			"goal_symbol_count": self.goal_symbol_count,
			"goal_symbols": list(self.goal_symbols),
			"max_plans_per_goal_symbol": self.max_plans_per_goal_symbol,
			"max_body_step_count": self.max_body_step_count,
			"primitive_action_step_count": self.primitive_action_step_count,
			"subgoal_step_count": self.subgoal_step_count,
			"singleton_macro_library_ready": self.singleton_macro_library_ready,
			"compact_recursive_module_ready": self.compact_recursive_module_ready,
			"artifact_classification": self.artifact_classification,
			"warnings": list(self.warnings),
		}


def parse_moose_readable_policy(text: str) -> tuple[MooseReadableRule, ...]:
	"""Parse MOOSE `--dump-policy` output into structured lifted rules."""

	blocks = tuple(
		block.strip()
		for block in re.split(r"\n\s*\n", str(text or "").strip())
		if block.strip()
	)
	rules: list[MooseReadableRule] = []
	for index, block in enumerate(blocks, start=1):
		rule = _parse_optional_rule_block(block, index=index)
		if rule is not None:
			rules.append(rule)
	return tuple(rules)


def load_moose_readable_policy(path: str | Path) -> tuple[MooseReadableRule, ...]:
	"""Load a MOOSE readable policy file from disk."""

	return parse_moose_readable_policy(Path(path).read_text(encoding="utf-8"))


def policy_program_from_moose_readable_policy(
	text: str,
	*,
	domain_name: str,
	source_name: str,
	policy_file: str | Path | None = None,
) -> LiftedPolicyProgram:
	"""Convert MOOSE readable policy text into the policy-first IR."""

	rules = parse_moose_readable_policy(text)
	learned_rules: list[LearnedPolicyRule] = []
	modules: list[PolicyModule] = []
	for index, rule in enumerate(rules, start=1):
		if not rule.is_singleton_goal_rule:
			continue
		variable_map = rule.variable_map()
		goal = rule.goal_conditions[0]
		name = f"moose_{_safe_name(source_name)}_rule_{index}"
		learned_rules.append(
			LearnedPolicyRule(
				name=name,
				conditions=tuple(
					(condition.to_call(variable_map), "holds")
					for condition in rule.state_conditions
				)
				+ ((goal.to_call(variable_map), "goal"),),
				effects=tuple(
					(f"primitive_action:{action.to_call(variable_map)}", "call")
					for action in rule.actions
				),
				source_rule=rule.source_rule,
			),
		)
		modules.append(
			PolicyModule(
				name=f"module_{_safe_name(goal.predicate)}",
				parameters=tuple(variable_map.get(arg, arg) for arg in goal.arguments),
				rule_names=(name,),
				goal_symbol=goal.predicate,
			),
		)
	return LiftedPolicyProgram(
		domain_name=domain_name,
		backend_name="moose",
		source_name=source_name,
		representation="moose_first_order_decision_list",
		features=(),
		rules=tuple(learned_rules),
		modules=tuple(modules),
		progress_certificate={
			"termination_basis": "moose_learned_precedence_order",
			"raw_rule_count": len(rules),
			"singleton_goal_rule_count": len(learned_rules),
		},
		provenance={
			"paper_basis": "MOOSE goal-regression generalized planner",
			"policy_file": str(policy_file) if policy_file is not None else None,
			"source_backend": "moose",
			"artifact_format": "policy --dump-policy readable text",
		},
		is_learned_policy=True,
	)


def compile_moose_readable_policy_to_asl_library(
	text: str,
	*,
	domain_name: str,
	source_name: str,
	policy_file: str | Path | None = None,
) -> PlanLibrary:
	"""Compile singleton-goal MOOSE readable policy rules into ASL plans."""

	rules = parse_moose_readable_policy(text)
	plans: list[AgentSpeakPlan] = []
	for index, rule in enumerate(rules, start=1):
		if not rule.is_singleton_goal_rule:
			continue
		variable_map = rule.variable_map()
		goal = rule.goal_conditions[0]
		plans.append(
			AgentSpeakPlan(
				plan_name=f"moose_{_safe_name(source_name)}_rule_{index}",
				trigger=AgentSpeakTrigger(
					event_type="achievement_goal",
					symbol=goal.predicate,
					arguments=tuple(variable_map.get(arg, arg) for arg in goal.arguments),
				),
				context=tuple(
					condition.to_call(variable_map)
					for condition in rule.state_conditions
				),
				body=tuple(
					AgentSpeakBodyStep(
						"action",
						action.predicate,
						tuple(variable_map.get(arg, arg) for arg in action.arguments),
					)
					for action in rule.actions
				),
				binding_certificate=(
					{
						"artifact_family": "moose_goal_regression_policy",
						"source_backend": "moose",
						"source_name": source_name,
						"policy_file": str(policy_file) if policy_file is not None else None,
						"precedence": rule.precedence,
					},
				),
			),
		)
	quality_report = audit_moose_atomic_library_quality(
		plans=tuple(plans),
	)
	return PlanLibrary(
		domain_name=domain_name,
		plans=tuple(plans),
		metadata={
			"atomic_template_backend": "moose",
			"source_name": source_name,
			"policy_file": str(policy_file) if policy_file is not None else None,
			"raw_rule_count": len(rules),
			"compiled_singleton_rule_count": len(plans),
			"library_quality": quality_report.to_dict(),
		},
	)


def audit_moose_atomic_library_quality(
	*,
	plans: Sequence[AgentSpeakPlan],
	max_compact_plan_count: int = 10,
	max_macro_body_steps: int = 8,
) -> MooseAtomicLibraryQualityReport:
	"""Classify direct MOOSE output without treating raw macros as modules."""

	plan_tuple = tuple(plans or ())
	plans_by_goal: dict[str, int] = {}
	primitive_action_step_count = 0
	subgoal_step_count = 0
	max_body_step_count = 0
	for plan in plan_tuple:
		plans_by_goal[plan.trigger.symbol] = plans_by_goal.get(plan.trigger.symbol, 0) + 1
		body = tuple(plan.body or ())
		max_body_step_count = max(max_body_step_count, len(body))
		primitive_action_step_count += sum(1 for step in body if step.kind == "action")
		subgoal_step_count += sum(1 for step in body if step.kind == "subgoal")
	goal_symbols = tuple(sorted(plans_by_goal))
	max_plans_per_goal_symbol = max(plans_by_goal.values(), default=0)
	singleton_macro_library_ready = (
		len(plan_tuple) <= max_compact_plan_count
		and max_body_step_count <= max_macro_body_steps
	)
	compact_recursive_module_ready = (
		singleton_macro_library_ready
		and subgoal_step_count > 0
	)
	if compact_recursive_module_ready:
		artifact_classification = "compact_recursive_atomic_module_library"
	elif singleton_macro_library_ready:
		artifact_classification = "compact_lifted_singleton_macro_library"
	else:
		artifact_classification = "raw_lifted_singleton_macro_policy_not_compact"
	warnings: list[str] = []
	if subgoal_step_count == 0 and plan_tuple:
		warnings.append(
			"Direct MOOSE output contains primitive macro actions but no recursive "
			"atomic subgoal calls; do not claim compact module-level quality when "
			"the domain requires recursive decomposition."
		)
	if len(plan_tuple) > max_compact_plan_count:
		warnings.append(
			"Plan count exceeds the compact-library threshold; this artifact is "
			"backend evidence or a smoke output, not the final compact library."
		)
	if max_body_step_count > max_macro_body_steps:
		warnings.append(
			"At least one plan body exceeds the compact macro threshold; inspect "
			"whether raw trace replay leaked into the library."
		)
	return MooseAtomicLibraryQualityReport(
		plan_count=len(plan_tuple),
		goal_symbol_count=len(goal_symbols),
		goal_symbols=goal_symbols,
		max_plans_per_goal_symbol=max_plans_per_goal_symbol,
		max_body_step_count=max_body_step_count,
		primitive_action_step_count=primitive_action_step_count,
		subgoal_step_count=subgoal_step_count,
		singleton_macro_library_ready=singleton_macro_library_ready,
		compact_recursive_module_ready=compact_recursive_module_ready,
		artifact_classification=artifact_classification,
		warnings=tuple(warnings),
	)


def _parse_optional_rule_block(block: str, *, index: int) -> MooseReadableRule | None:
	lines = tuple(line.rstrip() for line in block.splitlines() if line.strip())
	fields: dict[str, str] = {}
	for line in lines:
		if ":" not in line:
			continue
		key, value = line.split(":", 1)
		fields[key.strip()] = value.strip()
	required = ("precedence", "vars", "s_cond", "g_cond", "actions")
	missing = tuple(key for key in required if key not in fields)
	if len(missing) == len(required):
		return None
	if missing:
		raise ValueError(
			f"MOOSE readable policy rule {index} is missing fields: {', '.join(missing)}",
		)
	return MooseReadableRule(
		precedence=fields["precedence"],
		variables=tuple(item for item in fields["vars"].split() if item),
		state_conditions=_parse_atoms(fields["s_cond"]),
		goal_conditions=_parse_atoms(fields["g_cond"]),
		actions=_parse_atoms(fields["actions"]),
		source_rule="\n".join(lines),
	)


def _parse_atoms(text: str) -> tuple[MooseAtom, ...]:
	atoms: list[MooseAtom] = []
	for raw_atom in re.findall(r"\(([^()]*)\)", str(text or "")):
		parts = tuple(part for part in raw_atom.split() if part)
		if not parts:
			continue
		atoms.append(MooseAtom(predicate=parts[0], arguments=parts[1:]))
	return tuple(atoms)


def _agentspeak_variable(variable: str) -> str:
	text = str(variable or "").strip()
	if not text:
		return "V"
	return text[:1].upper() + text[1:]


def _call(predicate: str, arguments: Sequence[str]) -> str:
	args = tuple(arguments or ())
	return str(predicate) if not args else f"{predicate}({', '.join(args)})"


def _safe_name(value: str) -> str:
	text = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "").strip()).strip("_")
	if not text:
		return "policy"
	if text[0].isdigit():
		return f"p_{text}"
	return text
