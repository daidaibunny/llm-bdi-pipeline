"""Evidence-module interfaces and backend adapters.

The evidence module is the boundary between external generalized-planning
backends and the validated policy-lifting compiler. Backend-specific adapters
parse native artifacts, such as a MOOSE ``policy --dump-policy`` readable
decision list, into a backend-agnostic policy evidence program. The compiler
then consumes that evidence program plus the PDDL domain schema; it does not
need to know which backend produced the evidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Mapping, Sequence

from plan_library.models import AgentSpeakBodyStep
from plan_library.models import AgentSpeakPlan
from plan_library.models import AgentSpeakTrigger
from plan_library.models import PlanLibrary
from utils.pddl_parser import PDDLDomain
from utils.pddl_parser import PDDLFunction
from utils.pddl_parser import PDDLNumericCondition
from utils.pddl_parser import PDDLNumericExpression
from utils.pddl_parser import PDDLParser

from .atomic_module_synthesis import synthesize_atomic_minimal_literal_module_library
from .atomic_module_synthesis import PDDLLiteralSchema
from .atomic_module_synthesis import _ParsedAction
from .atomic_module_synthesis import _numeric_condition_contexts
from .atomic_module_synthesis import _order_contexts_for_matching
from .atomic_module_synthesis import _parameter_type
from .pddl_types import OBJ_TP_PREDICATE
from .pddl_types import type_closure
from .policy_program import LearnedPolicyRule
from .policy_program import LiftedPolicyProgram
from .policy_program import PolicyModule


@dataclass(frozen=True)
class PolicyEvidenceAtom:
	"""One atom or primitive action call supplied by an evidence backend.

	Example: in a singleton-goal policy rule, ``at(package0, location1)`` is a
	goal atom and ``load-truck(package0, truck0, location0)`` is a primitive
	action atom.
	"""

	predicate: str
	arguments: tuple[str, ...]

	def to_call(self, variable_map: dict[str, str]) -> str:
		return _call(self.predicate, tuple(variable_map.get(arg, arg) for arg in self.arguments))


@dataclass(frozen=True)
class PolicyEvidenceRule:
	"""One backend-agnostic singleton-goal evidence rule.

	A rule states that, under ``state_conditions``, a backend observed or learned
	that the ``actions`` sequence can make the ``goal_conditions`` true. For
	example, a MOOSE rule for Logistics may say that a package at airport A can
	reach location L through ``load-airplane; fly-airplane; unload-airplane``.
	"""

	precedence: str
	variables: tuple[str, ...]
	state_conditions: tuple[PolicyEvidenceAtom, ...]
	goal_conditions: tuple[PolicyEvidenceAtom, ...]
	state_numeric_conditions: tuple[PDDLNumericCondition, ...]
	goal_numeric_conditions: tuple[PDDLNumericCondition, ...]
	actions: tuple[PolicyEvidenceAtom, ...]
	source_rule: str

	@property
	def is_singleton_goal_rule(self) -> bool:
		return self.has_singleton_predicate_goal

	@property
	def has_singleton_predicate_goal(self) -> bool:
		return len(self.goal_conditions) == 1 and not self.goal_numeric_conditions

	@property
	def has_singleton_numeric_goal(self) -> bool:
		return len(self.goal_numeric_conditions) == 1 and not self.goal_conditions

	def variable_map(self) -> dict[str, str]:
		return {variable: _agentspeak_variable(variable) for variable in self.variables}


@dataclass(frozen=True)
class PolicyEvidenceProgram:
	"""Backend-agnostic evidence program consumed by the compiler.

	``source_provider`` records provenance, for example ``"moose"``. ``rules``
	are the normalized singleton-goal policy rules. A future D2L or sketch
	adapter should emit this same shape rather than making the compiler parse its
	native artifact directly.
	"""

	source_provider: str
	source_name: str
	representation: str
	rules: tuple[PolicyEvidenceRule, ...]
	policy_file: str | Path | None = None
	provenance: Mapping[str, object] = field(default_factory=dict)


class MooseAtom(PolicyEvidenceAtom):
	"""MOOSE-specific alias for one readable-policy atom."""


class MooseReadableRule(PolicyEvidenceRule):
	"""MOOSE-specific alias for one readable decision-list rule."""


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
	faithful_decision_list_ready: bool
	artifact_classification: str
	library_profile: str
	plan_template_kind_counts: Mapping[str, int]
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
			"faithful_decision_list_ready": self.faithful_decision_list_ready,
			"artifact_classification": self.artifact_classification,
			"library_profile": self.library_profile,
			"plan_template_kind_counts": dict(self.plan_template_kind_counts),
			"warnings": list(self.warnings),
		}


@dataclass(frozen=True)
class PolicyEvidenceReducerReport:
	"""Audit record for validated macro evidence preserved in ASL."""

	raw_singleton_macro_count: int
	raw_numeric_goal_macro_count: int
	validated_macro_count: int
	validated_numeric_macro_count: int
	invalid_macro_count: int
	deduplicated_macro_count: int
	merged_plan_count: int
	validation_basis: tuple[str, ...]

	def to_dict(self) -> dict[str, object]:
		return {
			"raw_singleton_macro_count": self.raw_singleton_macro_count,
			"raw_numeric_goal_macro_count": self.raw_numeric_goal_macro_count,
			"validated_macro_count": self.validated_macro_count,
			"validated_numeric_macro_count": self.validated_numeric_macro_count,
			"invalid_macro_count": self.invalid_macro_count,
			"deduplicated_macro_count": self.deduplicated_macro_count,
			"merged_plan_count": self.merged_plan_count,
			"validation_basis": list(self.validation_basis),
		}


@dataclass(frozen=True)
class _PolicyEvidencePlans:
	plans: tuple[AgentSpeakPlan, ...]
	report: PolicyEvidenceReducerReport


MooseMacroEvidenceReducerReport = PolicyEvidenceReducerReport


@dataclass(frozen=True)
class _NumericGoalSpec:
	function: str
	arguments: tuple[str, ...]
	target: str


@dataclass(frozen=True)
class _NumericProgressSpec:
	guard_operator: str
	net_delta: int


@dataclass(frozen=True)
class _NumericFluentRef:
	function: str
	arguments: tuple[str, ...]


@dataclass(frozen=True)
class _NumericInitialGuard:
	ref: _NumericFluentRef
	comparator: str
	threshold: int


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


def evidence_program_from_moose_readable_policy(
	text: str,
	*,
	source_name: str,
	policy_file: str | Path | None = None,
) -> PolicyEvidenceProgram:
	"""Convert MOOSE readable policy text into backend-agnostic evidence IR."""

	rules = parse_moose_readable_policy(text)
	return PolicyEvidenceProgram(
		source_provider="moose",
		source_name=source_name,
		representation="moose_readable_first_order_decision_list",
		rules=tuple(rules),
		policy_file=policy_file,
		provenance={
			"paper_basis": "MOOSE goal-regression generalized planner",
			"artifact_format": "policy --dump-policy readable text",
			"policy_file": str(policy_file) if policy_file is not None else None,
		},
	)


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
			"source_provider": "moose",
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
		state_contexts = _rule_state_contexts(
			rule=rule,
			variable_map=variable_map,
		)
		plans.append(
			AgentSpeakPlan(
				plan_name=f"moose_{_safe_name(source_name)}_rule_{index}",
				trigger=AgentSpeakTrigger(
					event_type="achievement_goal",
					symbol=goal.predicate,
					arguments=tuple(variable_map.get(arg, arg) for arg in goal.arguments),
				),
				context=state_contexts,
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
						"source_provider": "moose",
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
			"generation_mode": "faithful_moose_decision_list_asl_library",
			"atomic_template_provider": "moose",
			"atomic_template_backend": "moose",
			"source_name": source_name,
			"policy_file": str(policy_file) if policy_file is not None else None,
			"raw_rule_count": len(rules),
			"compiled_singleton_rule_count": len(plans),
			"library_quality": quality_report.to_dict(),
			"artifact_contract": (
				"faithful ASL rendering of MOOSE first-order decision-list "
				"singleton-goal rules; rule order, state context, goal trigger, "
				"and macro action sequence are preserved"
			),
		},
	)


def compile_moose_readable_policy_to_minimal_module_asl_library(
	text: str,
	*,
	domain_file: str | Path,
	domain_name: str,
	source_name: str,
	policy_file: str | Path | None = None,
) -> PlanLibrary:
	"""Lift validated MOOSE adapter evidence into an executable ASL library."""

	evidence_program = evidence_program_from_moose_readable_policy(
		text,
		source_name=source_name,
		policy_file=policy_file,
	)
	return compile_policy_evidence_program_to_minimal_module_asl_library(
		evidence_program,
		domain_file=domain_file,
		domain_name=domain_name,
	)


def compile_policy_evidence_program_to_minimal_module_asl_library(
	evidence_program: PolicyEvidenceProgram,
	*,
	domain_file: str | Path,
	domain_name: str,
) -> PlanLibrary:
	"""Compile backend-agnostic singleton evidence into an atomic ASL library.

		The evidence program is the decoupling point: MOOSE, D2L, or future sketch
		providers should normalize their native artifacts into this IR before the
		validated policy-lifting compiler sees them.
	"""

	rules = tuple(evidence_program.rules or ())
	seed_predicates = tuple(
		dict.fromkeys(
			rule.goal_conditions[0].predicate
			for rule in rules
			if rule.has_singleton_predicate_goal
		),
	)
	domain = PDDLParser.parse_domain(domain_file)
	numeric_goal_functions = _numeric_goal_functions_from_rules(
		rules=rules,
		declared_functions=domain.functions,
	)
	if seed_predicates:
		library = synthesize_atomic_minimal_literal_module_library(
			domain_file=domain_file,
			seed_predicates=seed_predicates,
			source_backend=f"{evidence_program.source_provider}_validated_policy_lifting",
			source_name=evidence_program.source_name,
			policy_file=evidence_program.policy_file,
		)
	else:
		library = PlanLibrary(
			domain_name=domain.name,
			plans=(),
			initial_beliefs=(),
			metadata={
				"generation_mode": "atomic_minimal_literal_module_library",
				"atomic_template_provider": (
					f"{evidence_program.source_provider}_validated_policy_lifting"
				),
				"atomic_template_backend": (
					f"{evidence_program.source_provider}_validated_policy_lifting"
				),
				"source_name": evidence_program.source_name,
				"policy_file": (
					str(evidence_program.policy_file)
					if evidence_program.policy_file is not None
					else None
				),
				"library_quality": {
					"artifact_classification": "empty_or_unbound_atomic_template_library",
					"artifact_classification_basis": (
						"no predicate singleton seeds were present; numeric resource "
						"modules may still be emitted from validated evidence-module numeric "
						"goal evidence"
					),
					"library_profile": "empty_atomic_template_library",
					"plan_template_kind_counts": {},
					"compact_recursive_module_ready": False,
					"plan_count": 0,
					"primitive_action_step_count": 0,
					"subgoal_step_count": 0,
				},
				"atomic_module_synthesis": {
					"seed_predicates": [],
					"module_predicates": [],
					"plan_count": 0,
					"raw_candidate_count": 0,
					"selector_backend": "not_invoked_no_predicate_seed",
				},
				},
			)
	macro_evidence = _compile_validated_policy_evidence_macro_plans(
		rules=rules,
		domain_file=domain_file,
		source_provider=evidence_program.source_provider,
		source_name=evidence_program.source_name,
		policy_file=evidence_program.policy_file,
	)
	merged_plans = _ensure_unique_plan_names(
		_deduplicate_agent_plans((*library.plans, *macro_evidence.plans)),
	)
	macro_quality_report = audit_moose_atomic_library_quality(plans=macro_evidence.plans)
	library_quality = _evidence_compiler_library_quality(
		plans=merged_plans,
		macro_evidence_plan_count=len(macro_evidence.plans),
	)
	return PlanLibrary(
		domain_name=domain_name or library.domain_name,
		plans=merged_plans,
		initial_beliefs=library.initial_beliefs,
		metadata={
			**dict(library.metadata),
			"evidence_module": {
				"source_provider": evidence_program.source_provider,
				"source_name": evidence_program.source_name,
				"representation": evidence_program.representation,
				"policy_file": (
					str(evidence_program.policy_file)
					if evidence_program.policy_file is not None
					else None
				),
				"rule_count": len(rules),
			},
			"source_raw_rule_count": len(rules),
			"source_seed_predicates": list(seed_predicates),
			"source_numeric_goal_functions": list(numeric_goal_functions),
			"validated_policy_lifting": {
				**macro_evidence.report.to_dict(),
				"merged_plan_count": len(merged_plans),
			},
			"library_quality": library_quality,
			"moose_macro_library_quality": macro_quality_report.to_dict(),
		},
	)


def _compile_validated_policy_evidence_macro_plans(
	*,
	rules: Sequence[PolicyEvidenceRule],
	domain_file: str | Path,
	source_provider: str,
	source_name: str,
	policy_file: str | Path | None,
) -> _PolicyEvidencePlans:
	domain = PDDLParser.parse_domain(domain_file)
	actions_by_name = {
		action.name: action
		for action in (_ParsedAction.from_pddl(action) for action in domain.actions)
	}
	predicate_types = _predicate_parameter_types(domain)
	declared_constants = tuple(str(constant).strip().lower() for constant in domain.constants)
	raw_singleton_rules = tuple(rule for rule in rules if rule.has_singleton_predicate_goal)
	raw_numeric_goal_rules = tuple(rule for rule in rules if rule.has_singleton_numeric_goal)
	plans: list[AgentSpeakPlan] = []
	invalid_count = 0
	for index, rule in enumerate(raw_singleton_rules, start=1):
		plan = _validated_policy_evidence_macro_rule_plan(
			rule=rule,
			rule_index=index,
			actions_by_name=actions_by_name,
				predicate_types=predicate_types,
				type_tokens=domain.types,
				declared_constants=declared_constants,
				source_provider=source_provider,
				source_name=source_name,
				policy_file=policy_file,
			)
		if plan is None:
			invalid_count += 1
			continue
		plans.append(plan)
	numeric_plans = _numeric_goal_already_true_plans(
		rules=raw_numeric_goal_rules,
		declared_functions=domain.functions,
		declared_constants=declared_constants,
		source_provider=source_provider,
		source_name=source_name,
		policy_file=policy_file,
	)
	validated_numeric_count = 0
	for index, rule in enumerate(raw_numeric_goal_rules, start=1):
		plan = _validated_policy_evidence_numeric_macro_rule_plan(
			rule=rule,
			rule_index=index,
			actions_by_name=actions_by_name,
			predicate_types=predicate_types,
			type_tokens=domain.types,
				declared_functions=domain.functions,
				declared_constants=declared_constants,
				source_provider=source_provider,
				source_name=source_name,
				policy_file=policy_file,
			)
		if plan is None:
			invalid_count += 1
			continue
		validated_numeric_count += 1
		plans.append(plan)
	plans.extend(numeric_plans)
	deduplicated = _deduplicate_agent_plans(tuple(plans))
	return _PolicyEvidencePlans(
		plans=_ensure_unique_plan_names(deduplicated),
		report=PolicyEvidenceReducerReport(
			raw_singleton_macro_count=len(raw_singleton_rules),
			raw_numeric_goal_macro_count=len(raw_numeric_goal_rules),
			validated_macro_count=len(plans),
			validated_numeric_macro_count=validated_numeric_count,
			invalid_macro_count=invalid_count,
			deduplicated_macro_count=len(deduplicated),
			merged_plan_count=len(deduplicated),
				validation_basis=(
					"MOOSE readable singleton goal rule supplies state context, goal, and macro action sequence",
					"PDDL action schemas validate every primitive action arity and symbolic precondition/effect transition",
					"MOOSE numeric equality goal evidence may compile to bounded integer resource modules when the macro has a unit monotone numeric effect toward the target value",
					"PDDL predicate and action parameter types compile to reserved obj_tp/2 context guards",
					"Goal variables are alpha-normalized to X,Y,... and non-goal witnesses to fresh lifted variables",
					"PDDL constants are preserved as constants; negative precondition conflicts and positive preconditions that may alias prior deletes compile to explicit inequality guards when representable in the supported ASL subset",
				),
			),
		)


def _evidence_compiler_library_quality(
	*,
	plans: Sequence[AgentSpeakPlan],
	macro_evidence_plan_count: int,
) -> dict[str, object]:
	plan_tuple = tuple(plans or ())
	subgoal_step_count = sum(
		1
		for plan in plan_tuple
		for step in tuple(plan.body or ())
		if step.kind == "subgoal"
	)
	primitive_action_step_count = sum(
		1
		for plan in plan_tuple
		for step in tuple(plan.body or ())
		if step.kind == "action"
	)
	plan_template_kind_counts = _plan_template_kind_counts(plan_tuple)
	return {
		"artifact_classification": (
			"atomic_template_library"
			if plan_tuple
			else "empty_or_unbound_atomic_template_library"
		),
		"artifact_classification_basis": (
			"generic artifact label; structural categories are plan-template-level, "
			"not domain-level"
		),
		"library_profile": _library_template_profile(plan_template_kind_counts),
		"plan_template_kind_counts": plan_template_kind_counts,
		"plan_template_classification_basis": (
			"per plan template: numeric resource goal modules are classified "
			"by their numeric certificate, empty non-numeric bodies are "
			"already-true, bodies with only primitive actions are action-only, "
			"and bodies containing achievement subgoals are subgoal-decomposed"
		),
		"plan_count": len(plan_tuple),
		"primitive_action_step_count": primitive_action_step_count,
		"subgoal_step_count": subgoal_step_count,
		"macro_evidence_plan_count": macro_evidence_plan_count,
		"moose_macro_evidence_plan_count": macro_evidence_plan_count,
		"validated_policy_rule_plan_count": macro_evidence_plan_count,
		"compact_recursive_module_ready": subgoal_step_count > 0,
		"schema_augmented_recursive_modules_ready": subgoal_step_count > 0,
		"validated_macro_evidence_ready": macro_evidence_plan_count > 0,
		"validated_policy_lifting_ready": macro_evidence_plan_count > 0,
	}


def _plan_template_kind_counts(plans: Sequence[AgentSpeakPlan]) -> dict[str, int]:
	counts: dict[str, int] = {}
	for plan in tuple(plans or ()):
		kind = _plan_template_kind(plan)
		counts[kind] = counts.get(kind, 0) + 1
	return dict(sorted(counts.items()))


def _plan_template_kind(plan: AgentSpeakPlan) -> str:
	numeric_kind = _numeric_plan_template_kind(plan)
	if numeric_kind is not None:
		return numeric_kind
	body = tuple(plan.body or ())
	if not body:
		return "already_true_plan_template"
	if any(step.kind == "subgoal" for step in body):
		return "subgoal_decomposed_plan_template"
	if all(step.kind == "action" for step in body):
		return "action_only_plan_template"
	return "mixed_body_plan_template"


_NUMERIC_PLAN_TEMPLATE_KINDS = frozenset(
	{
		"numeric_already_true_plan_template",
		"numeric_resource_progress_plan_template",
		"numeric_resource_plan_template",
	},
)


def _numeric_plan_template_kind(plan: AgentSpeakPlan) -> str | None:
	for certificate in tuple(plan.binding_certificate or ()):
		if not isinstance(certificate, Mapping):
			continue
		if certificate.get("artifact_family") != "numeric_resource_goal_module":
			continue
		rule_kind = str(certificate.get("rule_kind") or "").strip()
		if rule_kind == "already_true":
			return "numeric_already_true_plan_template"
		if rule_kind == "monotone_resource_macro":
			return "numeric_resource_progress_plan_template"
		return "numeric_resource_plan_template"
	return None


def _library_template_profile(kind_counts: Mapping[str, int]) -> str:
	kinds = {kind for kind, count in dict(kind_counts).items() if count > 0}
	if not kinds:
		return "empty_atomic_template_library"
	if kinds <= _NUMERIC_PLAN_TEMPLATE_KINDS:
		return "numeric_resource_atomic_template_library"
	if len(kinds) > 1:
		return "mixed_atomic_template_library"
	kind = next(iter(kinds))
	if kind == "already_true_plan_template":
		return "already_true_only_atomic_template_library"
	if kind == "action_only_plan_template":
		return "action_only_atomic_template_library"
	if kind == "subgoal_decomposed_plan_template":
		return "subgoal_decomposed_atomic_template_library"
	return "mixed_body_atomic_template_library"


def _validated_policy_evidence_macro_rule_plan(
	*,
	rule: PolicyEvidenceRule,
	rule_index: int,
	actions_by_name: Mapping[str, _ParsedAction],
	predicate_types: Mapping[str, tuple[str, ...]],
	type_tokens: Sequence[str],
	declared_constants: Sequence[str],
	source_provider: str,
	source_name: str,
	policy_file: str | Path | None,
) -> AgentSpeakPlan | None:
	if not rule.is_singleton_goal_rule or not rule.actions:
		return None
	goal = rule.goal_conditions[0]
	variable_map = _canonical_rule_variable_map(
		rule,
		declared_constants=declared_constants,
	)
	type_contexts = _obj_tp_contexts_for_rule(
		rule=rule,
		actions_by_name=actions_by_name,
		predicate_types=predicate_types,
		type_tokens=type_tokens,
		variable_map=variable_map,
	)
	if type_contexts is None:
		return None
	symbolic_guards = _policy_evidence_rule_symbolic_execution_guards(
		rule=rule,
		actions_by_name=actions_by_name,
		variable_map=variable_map,
		declared_constants=declared_constants,
	)
	if symbolic_guards is None:
		return None
	evidence_distinctness_guards = _evidence_distinctness_guards(
		rule=rule,
		variable_map=variable_map,
		declared_constants=declared_constants,
	)
	binding_guards = _deduplicate_strings(
		(*symbolic_guards, *evidence_distinctness_guards),
	)
	state_contexts = _rule_state_contexts(
		rule=rule,
		variable_map=variable_map,
	)
	return AgentSpeakPlan(
		plan_name=f"{_safe_name(source_provider)}_reduced_{_safe_name(source_name)}_rule_{rule_index}",
		trigger=AgentSpeakTrigger(
			event_type="achievement_goal",
			symbol=goal.predicate,
			arguments=tuple(variable_map.get(argument, argument) for argument in goal.arguments),
		),
		context=_order_contexts_for_matching(
			(*state_contexts, *binding_guards),
			type_contexts,
			initial_bound_variables=tuple(
				variable_map.get(argument, argument) for argument in goal.arguments
			),
		),
		body=tuple(
			AgentSpeakBodyStep(
				"action",
				action.predicate,
				tuple(variable_map.get(argument, argument) for argument in action.arguments),
			)
			for action in rule.actions
			),
			binding_certificate=(
				{
					"artifact_family": "validated_policy_lifting_macro_rule",
					"source_provider": source_provider,
					"source_name": source_name,
					"policy_file": str(policy_file) if policy_file is not None else None,
					"precedence": rule.precedence,
					"validation": "pddl_schema_symbolic_execution",
					"schema_binding_guards": list(symbolic_guards),
					"evidence_distinctness_guards": list(evidence_distinctness_guards),
				},
			),
		)


def _rule_state_contexts(
	*,
	rule: PolicyEvidenceRule,
	variable_map: Mapping[str, str],
	skip_numeric_functions: Sequence[str] = (),
	reserved_numeric_variables: Sequence[str] = (),
) -> tuple[str, ...]:
	contexts: list[str] = [
		condition.to_call(dict(variable_map))
		for condition in rule.state_conditions
	]
	used_variables = set(
		variable
		for variable in tuple(reserved_numeric_variables or ())
		if _is_agentspeak_variable_name(variable)
	)
	used_variables.update(_used_agentspeak_variables_from_contexts(contexts))
	used_variables.update(
		value
		for value in variable_map.values()
		if _is_agentspeak_variable_name(value)
	)
	skip_functions = {str(function).strip().lower() for function in skip_numeric_functions}
	for condition in rule.state_numeric_conditions:
		if _numeric_condition_mentions_any_function(condition, skip_functions):
			continue
		contexts.extend(
			_numeric_condition_contexts(
				condition=condition,
				variable_map=variable_map,
				used_variables=used_variables,
			),
		)
	return _deduplicate_strings(tuple(contexts))


def _numeric_goal_functions_from_rules(
	*,
	rules: Sequence[PolicyEvidenceRule],
	declared_functions: Sequence[PDDLFunction],
) -> tuple[str, ...]:
	functions: list[str] = []
	for rule in tuple(rules or ()):
		spec = _numeric_goal_spec_from_rule(
			rule=rule,
			declared_functions=declared_functions,
		)
		if spec is None:
			continue
		functions.append(spec.function)
	return tuple(dict.fromkeys(functions))


def _numeric_goal_already_true_plans(
	*,
	rules: Sequence[PolicyEvidenceRule],
	declared_functions: Sequence[PDDLFunction],
	declared_constants: Sequence[str],
	source_provider: str,
	source_name: str,
	policy_file: str | Path | None,
) -> tuple[AgentSpeakPlan, ...]:
	plans: list[AgentSpeakPlan] = []
	seen: set[tuple[str, tuple[str, ...], str]] = set()
	for rule in tuple(rules or ()):
		spec = _numeric_goal_spec_from_rule(
			rule=rule,
			declared_functions=declared_functions,
		)
		if spec is None:
			continue
		variable_map = _canonical_rule_variable_map(
			rule,
			declared_constants=declared_constants,
		)
		trigger_arguments = tuple(variable_map.get(argument, argument) for argument in spec.arguments)
		key = (spec.function, trigger_arguments, spec.target)
		if key in seen:
			continue
		seen.add(key)
		value_variable = _first_available_numeric_variable(set(trigger_arguments))
		plans.append(
			AgentSpeakPlan(
				plan_name=(
					f"{_safe_name(spec.function)}_already_target_"
					f"{_safe_name(spec.target)}"
				),
				trigger=AgentSpeakTrigger(
					"achievement_goal",
					spec.function,
					(*trigger_arguments, spec.target),
				),
				context=(
					_numeric_fluent_context(
						function=spec.function,
						arguments=trigger_arguments,
						value_variable=value_variable,
					),
					f"{value_variable} == {spec.target}",
				),
				body=(),
				binding_certificate=(
						{
							"artifact_family": "numeric_resource_goal_module",
							"rule_kind": "already_true",
							"source_provider": source_provider,
							"source_name": source_name,
							"policy_file": str(policy_file) if policy_file is not None else None,
						"numeric_function": spec.function,
						"target_value": spec.target,
					},
				),
			),
		)
	return tuple(plans)


def _validated_policy_evidence_numeric_macro_rule_plan(
	*,
	rule: PolicyEvidenceRule,
	rule_index: int,
	actions_by_name: Mapping[str, _ParsedAction],
	predicate_types: Mapping[str, tuple[str, ...]],
	type_tokens: Sequence[str],
	declared_functions: Sequence[PDDLFunction],
	declared_constants: Sequence[str],
	source_provider: str,
	source_name: str,
	policy_file: str | Path | None,
) -> AgentSpeakPlan | None:
	if not rule.has_singleton_numeric_goal or not rule.actions:
		return None
	spec = _numeric_goal_spec_from_rule(
		rule=rule,
		declared_functions=declared_functions,
	)
	if spec is None:
		return None
	variable_map = _canonical_rule_variable_map(
		rule,
		declared_constants=declared_constants,
	)
	type_contexts = _obj_tp_contexts_for_rule(
		rule=rule,
		actions_by_name=actions_by_name,
		predicate_types=predicate_types,
		type_tokens=type_tokens,
		variable_map=variable_map,
	)
	if type_contexts is None:
		return None
	symbolic_guards = _policy_evidence_rule_symbolic_execution_guards(
		rule=rule,
		actions_by_name=actions_by_name,
		variable_map=variable_map,
		declared_constants=declared_constants,
	)
	if symbolic_guards is None:
		return None
	evidence_distinctness_guards = _evidence_distinctness_guards(
		rule=rule,
		variable_map=variable_map,
		declared_constants=declared_constants,
	)
	binding_guards = _deduplicate_strings(
		(*symbolic_guards, *evidence_distinctness_guards),
	)
	progress = _numeric_macro_progress_spec(
		rule=rule,
		spec=spec,
		actions_by_name=actions_by_name,
	)
	if progress is None:
		return None
	trigger_arguments = tuple(variable_map.get(argument, argument) for argument in spec.arguments)
	value_variable = _first_available_numeric_variable(set(trigger_arguments))
	progress_contexts = (
		_numeric_fluent_context(
			function=spec.function,
			arguments=trigger_arguments,
			value_variable=value_variable,
		),
		f"{value_variable} {progress.guard_operator} {spec.target}",
	)
	state_contexts = _rule_state_contexts(
		rule=rule,
		variable_map=variable_map,
		skip_numeric_functions=(
			*tuple(_numeric_macro_guard_functions(rule=rule, actions_by_name=actions_by_name)),
			spec.function,
		),
		reserved_numeric_variables=(*trigger_arguments, value_variable),
	)
	numeric_execution_contexts = _numeric_macro_execution_contexts(
		rule=rule,
		actions_by_name=actions_by_name,
		variable_map=variable_map,
		reserved_numeric_variables=(*trigger_arguments, value_variable),
		skip_numeric_functions=(spec.function,),
	)
	if numeric_execution_contexts is None:
		return None
	contexts = _order_contexts_for_matching(
		(*progress_contexts, *state_contexts, *numeric_execution_contexts, *binding_guards),
		type_contexts,
		initial_bound_variables=trigger_arguments,
	)
	return AgentSpeakPlan(
		plan_name=f"{_safe_name(source_provider)}_numeric_{_safe_name(source_name)}_rule_{rule_index}",
		trigger=AgentSpeakTrigger(
			"achievement_goal",
			spec.function,
			(*trigger_arguments, spec.target),
		),
		context=contexts,
		body=tuple(
			AgentSpeakBodyStep(
				"action",
				action.predicate,
				tuple(variable_map.get(argument, argument) for argument in action.arguments),
			)
			for action in rule.actions
			),
			binding_certificate=(
				{
					"artifact_family": "numeric_resource_goal_module",
					"rule_kind": "monotone_resource_macro",
					"source_provider": source_provider,
					"source_name": source_name,
					"policy_file": str(policy_file) if policy_file is not None else None,
					"precedence": rule.precedence,
					"numeric_function": spec.function,
				"target_value": spec.target,
				"net_delta": progress.net_delta,
				"validation": "pddl_schema_symbolic_execution_and_unit_numeric_progress",
				"schema_binding_guards": list(symbolic_guards),
				"evidence_distinctness_guards": list(evidence_distinctness_guards),
			},
		),
	)


def _numeric_goal_spec_from_rule(
	*,
	rule: PolicyEvidenceRule,
	declared_functions: Sequence[PDDLFunction],
) -> _NumericGoalSpec | None:
	if len(rule.goal_numeric_conditions) != 1 or rule.goal_conditions:
		return None
	return _numeric_goal_spec_from_condition(
		rule.goal_numeric_conditions[0],
		declared_functions=declared_functions,
	)


def _numeric_goal_spec_from_condition(
	condition: PDDLNumericCondition,
	*,
	declared_functions: Sequence[PDDLFunction],
) -> _NumericGoalSpec | None:
	if condition.comparator != "=":
		return None
	left_fluent, right_constant = _fluent_and_integer_constant(
		condition.left,
		condition.right,
	)
	if left_fluent is None or right_constant is None:
		left_fluent, right_constant = _fluent_and_integer_constant(
			condition.right,
			condition.left,
		)
	if left_fluent is None or right_constant is None:
		return None
	function = _declared_numeric_function_name(
		str(left_fluent.value),
		declared_functions=declared_functions,
	)
	if function is None:
		return None
	return _NumericGoalSpec(
		function=function,
		arguments=tuple(str(argument) for argument in left_fluent.args),
		target=str(right_constant),
	)


def _fluent_and_integer_constant(
	left: PDDLNumericExpression,
	right: PDDLNumericExpression,
) -> tuple[PDDLNumericExpression | None, int | None]:
	if left.kind != "fluent" or right.kind != "constant":
		return None, None
	if not re.fullmatch(r"[+-]?\d+", str(right.value)):
		return None, None
	return left, int(str(right.value))


def _declared_numeric_function_name(
	name: str,
	*,
	declared_functions: Sequence[PDDLFunction],
) -> str | None:
	declared = {function.name for function in tuple(declared_functions or ())}
	candidates = [str(name or "").strip().lower()]
	for suffix in ("__ug", "_ug"):
		if candidates[0].endswith(suffix):
			candidates.append(candidates[0][: -len(suffix)])
	for candidate in candidates:
		if candidate in declared:
			return candidate
	return None


def _numeric_macro_progress_spec(
	*,
	rule: PolicyEvidenceRule,
	spec: _NumericGoalSpec,
	actions_by_name: Mapping[str, _ParsedAction],
) -> _NumericProgressSpec | None:
	net_delta = 0
	for action_call in rule.actions:
		action = actions_by_name.get(action_call.predicate)
		if action is None or len(action.parameters) != len(action_call.arguments):
			return None
		binding = {
			parameter: argument
			for parameter, argument in zip(action.parameters, action_call.arguments)
		}
		for effect in action.numeric_effects:
			mapped_function = str(effect.fluent.function).strip().lower()
			if mapped_function != spec.function:
				continue
			mapped_arguments = tuple(
				binding.get(argument, argument)
				for argument in tuple(effect.fluent.args or ())
			)
			if mapped_arguments != spec.arguments:
				continue
			if effect.amount.kind != "constant" or not re.fullmatch(
				r"[+-]?\d+",
				str(effect.amount.value),
			):
				return None
			amount = int(str(effect.amount.value))
			if effect.operator == "increase":
				net_delta += amount
			elif effect.operator == "decrease":
				net_delta -= amount
			else:
				return None
	if net_delta == -1:
		return _NumericProgressSpec(guard_operator=">", net_delta=net_delta)
	if net_delta == 1:
		return _NumericProgressSpec(guard_operator="<", net_delta=net_delta)
	return None


def _numeric_macro_guard_functions(
	*,
	rule: PolicyEvidenceRule,
	actions_by_name: Mapping[str, _ParsedAction],
) -> tuple[str, ...]:
	functions: list[str] = []
	for action_call in tuple(rule.actions or ()):
		action = actions_by_name.get(action_call.predicate)
		if action is None:
			continue
		for condition in action.numeric_preconditions:
			for expression in (condition.left, condition.right):
				if expression.kind == "fluent":
					functions.append(str(expression.value).strip().lower())
		for effect in action.numeric_effects:
			functions.append(str(effect.fluent.function).strip().lower())
	return tuple(dict.fromkeys(functions))


def _numeric_macro_execution_contexts(
	*,
	rule: PolicyEvidenceRule,
	actions_by_name: Mapping[str, _ParsedAction],
	variable_map: Mapping[str, str],
	reserved_numeric_variables: Sequence[str],
	skip_numeric_functions: Sequence[str] = (),
) -> tuple[str, ...] | None:
	guards = _numeric_macro_initial_guards(
		rule=rule,
		actions_by_name=actions_by_name,
	)
	if guards is None:
		return None
	skip_functions = {
		str(function).strip().lower()
		for function in tuple(skip_numeric_functions or ())
	}
	value_variables: dict[_NumericFluentRef, str] = {}
	used_variables = {
		variable
		for variable in tuple(reserved_numeric_variables or ())
		if _is_agentspeak_variable_name(variable)
	}
	used_variables.update(
		value
		for value in variable_map.values()
		if _is_agentspeak_variable_name(value)
	)
	contexts: list[str] = []
	for guard in guards:
		if guard.ref.function in skip_functions:
			continue
		mapped_ref = _map_numeric_ref(guard.ref, variable_map=variable_map)
		value_variable = value_variables.get(mapped_ref)
		if value_variable is None:
			value_variable = _first_available_numeric_variable(used_variables)
			used_variables.add(value_variable)
			value_variables[mapped_ref] = value_variable
			contexts.append(
				_numeric_fluent_context(
					function=mapped_ref.function,
					arguments=mapped_ref.arguments,
					value_variable=value_variable,
				),
			)
		contexts.append(f"{value_variable} {guard.comparator} {guard.threshold}")
	return _deduplicate_strings(tuple(contexts))


def _numeric_macro_initial_guards(
	*,
	rule: PolicyEvidenceRule,
	actions_by_name: Mapping[str, _ParsedAction],
) -> tuple[_NumericInitialGuard, ...] | None:
	offsets: dict[_NumericFluentRef, int] = {}
	strongest_lower_bounds: dict[_NumericFluentRef, int] = {}
	weakest_upper_bounds: dict[_NumericFluentRef, int] = {}
	for action_call in tuple(rule.actions or ()):
		action = actions_by_name.get(action_call.predicate)
		if action is None or len(action.parameters) != len(action_call.arguments):
			return None
		binding = {
			parameter: argument
			for parameter, argument in zip(action.parameters, action_call.arguments)
		}
		for condition in action.numeric_preconditions:
			guards = _numeric_condition_initial_guards(
				condition=condition,
				binding=binding,
				offsets=offsets,
			)
			if guards is None:
				return None
			for guard in guards:
				_add_numeric_guard_bound(
					guard=guard,
					strongest_lower_bounds=strongest_lower_bounds,
					weakest_upper_bounds=weakest_upper_bounds,
				)
		for effect in action.numeric_effects:
			mapped_effect = _mapped_numeric_effect_delta(effect, binding=binding)
			if mapped_effect is None:
				return None
			ref, delta = mapped_effect
			offsets[ref] = offsets.get(ref, 0) + delta
	guards = [
		_NumericInitialGuard(ref=ref, comparator=">=", threshold=threshold)
		for ref, threshold in strongest_lower_bounds.items()
	]
	guards.extend(
		_NumericInitialGuard(ref=ref, comparator="<=", threshold=threshold)
		for ref, threshold in weakest_upper_bounds.items()
	)
	return tuple(guards)


def _numeric_condition_initial_guards(
	*,
	condition: PDDLNumericCondition,
	binding: Mapping[str, str],
	offsets: Mapping[_NumericFluentRef, int],
) -> tuple[_NumericInitialGuard, ...] | None:
	left_ref, left_constant = _numeric_expression_ref_or_constant(condition.left, binding)
	right_ref, right_constant = _numeric_expression_ref_or_constant(condition.right, binding)
	if left_ref is not None and right_constant is not None:
		return _initial_guards_for_fluent_constant_comparison(
			ref=left_ref,
			comparator=condition.comparator,
			constant=right_constant,
			offset=offsets.get(left_ref, 0),
		)
	if right_ref is not None and left_constant is not None:
		return _initial_guards_for_fluent_constant_comparison(
			ref=right_ref,
			comparator=_reverse_numeric_comparator(condition.comparator),
			constant=left_constant,
			offset=offsets.get(right_ref, 0),
		)
	return None


def _initial_guards_for_fluent_constant_comparison(
	*,
	ref: _NumericFluentRef,
	comparator: str,
	constant: int,
	offset: int,
) -> tuple[_NumericInitialGuard, ...] | None:
	threshold = constant - offset
	if comparator == ">":
		return (
			_NumericInitialGuard(
				ref=ref,
				comparator=">=",
				threshold=threshold + 1,
			)
		,)
	if comparator == ">=":
		return (
			_NumericInitialGuard(ref=ref, comparator=">=", threshold=threshold),
		)
	if comparator == "<":
		return (
			_NumericInitialGuard(
				ref=ref,
				comparator="<=",
				threshold=threshold - 1,
			)
		,)
	if comparator == "<=":
		return (
			_NumericInitialGuard(ref=ref, comparator="<=", threshold=threshold),
		)
	if comparator == "=":
		return (
			_NumericInitialGuard(ref=ref, comparator=">=", threshold=threshold),
			_NumericInitialGuard(ref=ref, comparator="<=", threshold=threshold),
		)
	return None


def _reverse_numeric_comparator(comparator: str) -> str:
	return {
		">": "<",
		">=": "<=",
		"<": ">",
		"<=": ">=",
		"=": "=",
	}.get(comparator, comparator)


def _numeric_expression_ref_or_constant(
	expression: PDDLNumericExpression,
	binding: Mapping[str, str],
) -> tuple[_NumericFluentRef | None, int | None]:
	if expression.kind == "constant":
		if not re.fullmatch(r"[+-]?\d+", str(expression.value)):
			return None, None
		return None, int(str(expression.value))
	if expression.kind != "fluent":
		return None, None
	return _NumericFluentRef(
		function=str(expression.value).strip().lower(),
		arguments=tuple(
			binding.get(argument, argument)
			for argument in tuple(expression.args or ())
		),
	), None


def _add_numeric_guard_bound(
	*,
	guard: _NumericInitialGuard,
	strongest_lower_bounds: dict[_NumericFluentRef, int],
	weakest_upper_bounds: dict[_NumericFluentRef, int],
) -> None:
	if guard.comparator == ">=":
		current = strongest_lower_bounds.get(guard.ref)
		if current is None or guard.threshold > current:
			strongest_lower_bounds[guard.ref] = guard.threshold
		return
	if guard.comparator == "<=":
		current = weakest_upper_bounds.get(guard.ref)
		if current is None or guard.threshold < current:
			weakest_upper_bounds[guard.ref] = guard.threshold


def _mapped_numeric_effect_delta(
	effect: object,
	*,
	binding: Mapping[str, str],
) -> tuple[_NumericFluentRef, int] | None:
	fluent = getattr(effect, "fluent", None)
	amount = getattr(effect, "amount", None)
	operator = str(getattr(effect, "operator", "") or "").strip().lower()
	if fluent is None or amount is None:
		return None
	if getattr(amount, "kind", None) != "constant" or not re.fullmatch(
		r"[+-]?\d+",
		str(getattr(amount, "value", "")),
	):
		return None
	delta = int(str(amount.value))
	if operator == "decrease":
		delta = -delta
	elif operator != "increase":
		return None
	ref = _NumericFluentRef(
		function=str(fluent.function).strip().lower(),
		arguments=tuple(
			binding.get(argument, argument)
			for argument in tuple(fluent.args or ())
		),
	)
	return ref, delta


def _map_numeric_ref(
	ref: _NumericFluentRef,
	*,
	variable_map: Mapping[str, str],
) -> _NumericFluentRef:
	return _NumericFluentRef(
		function=ref.function,
		arguments=tuple(variable_map.get(argument, argument) for argument in ref.arguments),
	)


def _numeric_condition_mentions_any_function(
	condition: PDDLNumericCondition,
	functions: set[str],
) -> bool:
	if not functions:
		return False
	return any(
		expression.kind == "fluent" and str(expression.value).strip().lower() in functions
		for expression in (condition.left, condition.right)
	)


def _numeric_fluent_context(
	*,
	function: str,
	arguments: Sequence[str],
	value_variable: str,
) -> str:
	return _call(str(function), (*tuple(arguments or ()), value_variable))


def _first_available_numeric_variable(used_variables: set[str]) -> str:
	for candidate in ("N", "M", "K", "Q", "R"):
		if candidate not in used_variables:
			return candidate
	index = 0
	while f"N{index}" in used_variables:
		index += 1
	return f"N{index}"


def _used_agentspeak_variables_from_contexts(contexts: Sequence[str]) -> set[str]:
	return {
		match.group(0)
		for context in tuple(contexts or ())
		for match in re.finditer(r"\b[A-Z][A-Za-z0-9_]*\b", str(context))
	}


def _is_agentspeak_variable_name(value: str) -> bool:
	return re.fullmatch(r"[A-Z][A-Za-z0-9_]*", str(value or "").strip()) is not None


def _canonical_rule_variable_map(
	rule: PolicyEvidenceRule,
	*,
	declared_constants: Sequence[str] = (),
) -> dict[str, str]:
	names = ("X", "Y", "Z", "A", "B", "C", "D")
	constants = {str(constant).strip().lower() for constant in tuple(declared_constants or ())}
	mapping: dict[str, str] = {}
	next_index = 0
	for argument in rule.goal_conditions[0].arguments if rule.goal_conditions else ():
		if argument in constants:
			continue
		if argument in mapping:
			continue
		mapping[argument] = names[next_index] if next_index < len(names) else f"V{next_index}"
		next_index += 1
	for condition in rule.goal_numeric_conditions:
		for expression in (condition.left, condition.right):
			if expression.kind != "fluent":
				continue
			for argument in tuple(expression.args or ()):
				if argument in constants:
					continue
				if argument in mapping:
					continue
				mapping[argument] = names[next_index] if next_index < len(names) else f"V{next_index}"
				next_index += 1
	for variable in rule.variables:
		if variable in constants:
			continue
		if variable in mapping:
			continue
		mapping[variable] = names[next_index] if next_index < len(names) else f"V{next_index}"
		next_index += 1
	return mapping


def _evidence_rule_is_symbolically_executable(
	*,
	rule: PolicyEvidenceRule,
	actions_by_name: Mapping[str, _ParsedAction],
) -> bool:
	return _policy_evidence_rule_symbolic_execution_guards(
		rule=rule,
		actions_by_name=actions_by_name,
		variable_map=_canonical_rule_variable_map(rule),
		declared_constants=(),
	) is not None


def _policy_evidence_rule_symbolic_execution_guards(
	*,
	rule: PolicyEvidenceRule,
	actions_by_name: Mapping[str, _ParsedAction],
	variable_map: Mapping[str, str],
	declared_constants: Sequence[str],
) -> tuple[str, ...] | None:
	state = {_atom_key(condition): True for condition in rule.state_conditions}
	guards: list[str] = []
	for action_call in rule.actions:
		action = actions_by_name.get(action_call.predicate)
		if action is None or len(action.parameters) != len(action_call.arguments):
			return None
		binding = {
			parameter: argument
			for parameter, argument in zip(action.parameters, action_call.arguments)
		}
		for precondition in action.preconditions:
			mapped = _map_schema_literal(precondition, binding)
			current = state.get(_atom_key(mapped))
			if precondition.is_positive:
				if current is not True:
					return None
				for deleted_atom in _state_atoms_that_can_conflict(
					state=state,
					atom=mapped,
					expected_value=False,
				):
					guard = _non_unification_guard(
						positive_atom=mapped,
						negative_atom=deleted_atom,
						variable_map=variable_map,
						declared_constants=declared_constants,
					)
					if guard is None:
						return None
					if guard:
						guards.append(guard)
				continue
			if current is True:
				return None
			for positive_atom in _state_atoms_that_can_conflict(
				state=state,
				atom=mapped,
				expected_value=True,
			):
				guard = _non_unification_guard(
					positive_atom=positive_atom,
					negative_atom=mapped,
					variable_map=variable_map,
					declared_constants=declared_constants,
				)
				if guard is None:
					return None
				if guard:
					guards.append(guard)
		for delete_effect in action.delete_effects:
			state[_atom_key(_map_schema_literal(delete_effect, binding))] = False
		for add_effect in action.add_effects:
			state[_atom_key(_map_schema_literal(add_effect, binding))] = True
	if not all(state.get(_atom_key(goal)) is True for goal in rule.goal_conditions):
		return None
	return _deduplicate_strings(tuple(guards))


def _evidence_distinctness_guards(
	*,
	rule: PolicyEvidenceRule,
	variable_map: Mapping[str, str],
	declared_constants: Sequence[str],
) -> tuple[str, ...]:
	"""Preserve distinct PDDL objects that were merged away by variable lifting."""

	constants = {str(constant).strip().lower() for constant in tuple(declared_constants or ())}
	source_terms = _evidence_rule_object_terms(rule)
	lifted_terms = tuple(
		term
		for term in source_terms
		if term in variable_map and _is_agentspeak_variable_name(variable_map[term])
	)
	constant_terms = tuple(term for term in source_terms if term in constants)
	guards: list[str] = []
	for left_index, left in enumerate(lifted_terms):
		for right in lifted_terms[left_index + 1 :]:
			if left == right:
				continue
			guards.append(
				_inequality_guard_text(variable_map[left], variable_map[right]),
			)
		for constant in constant_terms:
			if left == constant:
				continue
			guards.append(
				_inequality_guard_text(variable_map[left], constant),
			)
	return _deduplicate_strings(tuple(guards))


def _evidence_rule_object_terms(rule: PolicyEvidenceRule) -> tuple[str, ...]:
	terms: list[str] = []
	terms.extend(rule.variables)
	for atom in (*rule.state_conditions, *rule.goal_conditions):
		terms.extend(atom.arguments)
	for condition in (*rule.state_numeric_conditions, *rule.goal_numeric_conditions):
		for expression in (condition.left, condition.right):
			if expression.kind == "fluent":
				terms.extend(str(argument) for argument in tuple(expression.args or ()))
	for action in rule.actions:
		terms.extend(action.arguments)
	return tuple(dict.fromkeys(str(term).strip() for term in terms if str(term).strip()))


def _state_atoms_that_can_conflict(
	*,
	state: Mapping[tuple[str, tuple[str, ...]], bool],
	atom: PolicyEvidenceAtom,
	expected_value: bool,
) -> tuple[PolicyEvidenceAtom, ...]:
	candidates: list[PolicyEvidenceAtom] = []
	for (predicate, arguments), value in state.items():
		if value is not expected_value:
			continue
		if predicate != atom.predicate:
			continue
		if len(arguments) != len(atom.arguments):
			continue
		candidates.append(PolicyEvidenceAtom(predicate=predicate, arguments=arguments))
	return tuple(candidates)


def _non_unification_guard(
	*,
	positive_atom: PolicyEvidenceAtom,
	negative_atom: PolicyEvidenceAtom,
	variable_map: Mapping[str, str],
	declared_constants: Sequence[str],
) -> str | None:
	constants = {str(constant).strip().lower() for constant in tuple(declared_constants or ())}
	differences: list[tuple[str, str]] = []
	for positive_argument, negative_argument in zip(
		positive_atom.arguments,
		negative_atom.arguments,
	):
		if positive_argument == negative_argument:
			continue
		if positive_argument in constants and negative_argument in constants:
			return ""
		left = _guard_term(positive_argument, variable_map=variable_map)
		right = _guard_term(negative_argument, variable_map=variable_map)
		if left == right:
			return None
		differences.append((left, right))
	if not differences:
		return None
	left, right = differences[0]
	return _inequality_guard_text(left, right)


def _inequality_guard_text(left: str, right: str) -> str:
	left_is_variable = _is_agentspeak_variable_name(left)
	right_is_variable = _is_agentspeak_variable_name(right)
	if right_is_variable and not left_is_variable:
		left, right = right, left
	elif left_is_variable == right_is_variable and right < left:
		left, right = right, left
	return f"{left} != {right}"


def _guard_term(
	argument: str,
	*,
	variable_map: Mapping[str, str],
) -> str:
	return variable_map.get(argument, argument)


def _map_schema_literal(
	literal: PDDLLiteralSchema,
	binding: Mapping[str, str],
) -> PolicyEvidenceAtom:
	return PolicyEvidenceAtom(
		predicate=literal.predicate,
		arguments=tuple(binding.get(argument, argument) for argument in literal.arguments),
	)


def _obj_tp_contexts_for_rule(
	*,
	rule: PolicyEvidenceRule,
	actions_by_name: Mapping[str, _ParsedAction],
	predicate_types: Mapping[str, tuple[str, ...]],
	type_tokens: Sequence[str],
	variable_map: Mapping[str, str],
) -> tuple[str, ...] | None:
	types_by_argument: dict[str, set[str]] = {}
	for atom in (*rule.state_conditions, *rule.goal_conditions):
		for argument, type_name in zip(atom.arguments, predicate_types.get(atom.predicate, ())):
			_add_required_type(types_by_argument, argument, type_name)
	for action_call in rule.actions:
		action = actions_by_name.get(action_call.predicate)
		if action is None or len(action.parameters) != len(action_call.arguments):
			return None
		for parameter, argument in zip(action.parameters, action_call.arguments):
			_add_required_type(
				types_by_argument,
				argument,
				action.parameter_types.get(parameter, "object"),
			)
	contexts: list[str] = []
	for argument, required_types in sorted(types_by_argument.items()):
		most_specific = _most_specific_compatible_types(required_types, type_tokens)
		if most_specific is None:
			return None
		mapped_argument = variable_map.get(argument, argument)
		if not _is_agentspeak_variable_name(mapped_argument):
			continue
		for type_name in most_specific:
			if type_name == "object":
				continue
			contexts.append(
				f"{OBJ_TP_PREDICATE}({mapped_argument}, {type_name})",
			)
	return _deduplicate_strings(tuple(contexts))


def _add_required_type(
	types_by_argument: dict[str, set[str]],
	argument: str,
	type_name: str,
) -> None:
	canonical = _canonical_type_name(type_name)
	if canonical == "object":
		return
	types_by_argument.setdefault(argument, set()).add(canonical)


def _predicate_parameter_types(domain: PDDLDomain) -> dict[str, tuple[str, ...]]:
	return {
		predicate.name: tuple(_parameter_type(parameter) for parameter in predicate.parameters)
		for predicate in domain.predicates
	}


def _most_specific_compatible_types(
	type_names: set[str],
	type_tokens: Sequence[str],
) -> tuple[str, ...] | None:
	normalized = tuple(dict.fromkeys(_canonical_type_name(item) for item in type_names))
	non_object = tuple(type_name for type_name in normalized if type_name != "object")
	if not non_object:
		return ()
	for left in non_object:
		for right in non_object:
			if left == right:
				continue
			if not _types_are_compatible(left, right, type_tokens):
				return None
	return tuple(
		dict.fromkeys(
			type_name
			for type_name in non_object
			if not any(
				type_name != other
				and _is_subtype(other, type_name, type_tokens)
				for other in non_object
			)
		),
	)


def _types_are_compatible(left: str, right: str, type_tokens: Sequence[str]) -> bool:
	if left == "object" or right == "object":
		return True
	return _is_subtype(left, right, type_tokens) or _is_subtype(right, left, type_tokens)


def _is_subtype(child: str, parent: str, type_tokens: Sequence[str]) -> bool:
	return _canonical_type_name(parent) in type_closure(_canonical_type_name(child), type_tokens)


def _canonical_type_name(type_name: str) -> str:
	return str(type_name or "").strip().lower() or "object"


def _atom_key(atom: PolicyEvidenceAtom) -> tuple[str, tuple[str, ...]]:
	return (atom.predicate, atom.arguments)


def _deduplicate_agent_plans(plans: Sequence[AgentSpeakPlan]) -> tuple[AgentSpeakPlan, ...]:
	seen: set[tuple[object, ...]] = set()
	unique: list[AgentSpeakPlan] = []
	for plan in plans:
		key = (
			plan.trigger.symbol,
			plan.trigger.arguments,
			plan.context,
			tuple((step.kind, step.symbol, step.arguments) for step in plan.body),
		)
		if key in seen:
			continue
		seen.add(key)
		unique.append(plan)
	return tuple(unique)


def _ensure_unique_plan_names(plans: Sequence[AgentSpeakPlan]) -> tuple[AgentSpeakPlan, ...]:
	name_counts: dict[str, int] = {}
	unique: list[AgentSpeakPlan] = []
	for plan in plans:
		seen_count = name_counts.get(plan.plan_name, 0)
		name_counts[plan.plan_name] = seen_count + 1
		if seen_count == 0:
			unique.append(plan)
			continue
		unique.append(
			AgentSpeakPlan(
				plan_name=f"{plan.plan_name}_{seen_count + 1}",
				trigger=plan.trigger,
				context=plan.context,
				body=plan.body,
				source_instruction_ids=plan.source_instruction_ids,
				binding_certificate=plan.binding_certificate,
			),
		)
	return tuple(unique)


def _deduplicate_strings(items: Sequence[str]) -> tuple[str, ...]:
	return tuple(dict.fromkeys(item for item in items if item))


def audit_moose_atomic_library_quality(
	*,
	plans: Sequence[AgentSpeakPlan],
	max_compact_plan_count: int = 10,
	max_macro_body_steps: int = 8,
) -> MooseAtomicLibraryQualityReport:
	"""Classify MOOSE output without mistaking decision-list macros for recursion."""

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
	faithful_decision_list_ready = bool(plan_tuple) and primitive_action_step_count > 0
	artifact_classification = (
		"atomic_template_library"
		if plan_tuple
		else "empty_or_unbound_moose_atomic_library"
	)
	plan_template_kind_counts = _plan_template_kind_counts(plan_tuple)
	warnings: list[str] = []
	if subgoal_step_count == 0 and plan_tuple:
		warnings.append(
			"Direct MOOSE output contains primitive macro actions but no recursive "
			"atomic subgoal calls; claim faithful decision-list compilation rather "
			"than compact recursive module synthesis."
		)
	if len(plan_tuple) > max_compact_plan_count:
		warnings.append(
			"Plan count exceeds the compact-library threshold; this is acceptable "
			"for faithful MOOSE decision-list compilation, but it is not a compact "
			"recursive module artifact."
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
		faithful_decision_list_ready=faithful_decision_list_ready,
		artifact_classification=artifact_classification,
		library_profile=_library_template_profile(plan_template_kind_counts),
		plan_template_kind_counts=plan_template_kind_counts,
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
	state_conditions, state_numeric_conditions = _parse_conditions(fields["s_cond"])
	goal_conditions, goal_numeric_conditions = _parse_conditions(fields["g_cond"])
	return MooseReadableRule(
		precedence=fields["precedence"],
		variables=tuple(item for item in fields["vars"].split() if item),
		state_conditions=state_conditions,
		goal_conditions=goal_conditions,
		state_numeric_conditions=state_numeric_conditions,
		goal_numeric_conditions=goal_numeric_conditions,
		actions=_parse_atoms(fields["actions"]),
		source_rule="\n".join(lines),
	)


def _parse_conditions(
	text: str,
) -> tuple[tuple[MooseAtom, ...], tuple[PDDLNumericCondition, ...]]:
	atoms: list[MooseAtom] = []
	numeric_conditions: list[PDDLNumericCondition] = []
	for expression in _top_level_s_expressions(text):
		parsed = _parse_s_expression(expression)
		if not isinstance(parsed, list) or not parsed:
			continue
		condition = _numeric_condition_from_node(parsed)
		if condition is not None:
			numeric_conditions.append(condition)
			continue
		atom = _atom_from_node(parsed)
		if atom is not None:
			atoms.append(atom)
	return tuple(atoms), tuple(numeric_conditions)


def _parse_atoms(text: str) -> tuple[MooseAtom, ...]:
	atoms: list[MooseAtom] = []
	for expression in _top_level_s_expressions(text):
		parsed = _parse_s_expression(expression)
		atom = _atom_from_node(parsed)
		if atom is None:
			continue
		atoms.append(atom)
	return tuple(atoms)


def _atom_from_node(node: object) -> MooseAtom | None:
	if not isinstance(node, list) or not node:
		return None
	if any(isinstance(argument, list) for argument in node[1:]):
		return None
	predicate = str(node[0]).strip().lower()
	if not predicate or predicate in {">", ">=", "<", "<=", "="}:
		return None
	return MooseAtom(
		predicate=predicate,
		arguments=tuple(str(argument).strip().lower() for argument in node[1:]),
	)


def _numeric_condition_from_node(node: object) -> PDDLNumericCondition | None:
	if not isinstance(node, list) or len(node) != 3:
		return None
	comparator = str(node[0]).strip().lower()
	if comparator not in {">", ">=", "<", "<=", "="}:
		return None
	left = _numeric_expression_from_node(node[1])
	right = _numeric_expression_from_node(node[2])
	if left is None or right is None:
		return None
	return PDDLNumericCondition(comparator=comparator, left=left, right=right)


def _numeric_expression_from_node(node: object) -> PDDLNumericExpression | None:
	if not isinstance(node, list):
		text = str(node).strip().lower()
		if re.fullmatch(r"[+-]?\d+", text):
			return PDDLNumericExpression(kind="constant", value=str(int(text)))
		return None
	if not node:
		return None
	if any(isinstance(argument, list) for argument in node[1:]):
		return None
	return PDDLNumericExpression(
		kind="fluent",
		value=str(node[0]).strip().lower(),
		args=[str(argument).strip().lower() for argument in node[1:]],
	)


def _top_level_s_expressions(text: str) -> tuple[str, ...]:
	expressions: list[str] = []
	start: int | None = None
	depth = 0
	for index, character in enumerate(str(text or "")):
		if character == "(":
			if depth == 0:
				start = index
			depth += 1
		elif character == ")":
			depth -= 1
			if depth < 0:
				raise ValueError(f"Invalid MOOSE readable expression: {text!r}")
			if depth == 0 and start is not None:
				expressions.append(str(text)[start:index + 1])
				start = None
	if depth != 0:
		raise ValueError(f"Invalid MOOSE readable expression: {text!r}")
	return tuple(expressions)


def _parse_s_expression(text: str) -> object:
	tokens = tuple(
		token
		for token in (
			str(text or "")
			.replace("(", " ( ")
			.replace(")", " ) ")
			.split()
		)
		if token
	)
	if not tokens:
		return []
	parsed, index = _parse_s_expression_tokens(tokens, 0)
	if index != len(tokens):
		raise ValueError(f"Invalid MOOSE readable expression with trailing tokens: {text!r}")
	return parsed


def _parse_s_expression_tokens(
	tokens: Sequence[str],
	index: int,
) -> tuple[object, int]:
	if index >= len(tokens):
		raise ValueError("Unexpected end of MOOSE readable expression.")
	token = tokens[index]
	if token != "(":
		return token.lower(), index + 1
	items: list[object] = []
	index += 1
	while index < len(tokens) and tokens[index] != ")":
		item, index = _parse_s_expression_tokens(tokens, index)
		items.append(item)
	if index >= len(tokens):
		raise ValueError("Unmatched parenthesis in MOOSE readable expression.")
	return items, index + 1


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
