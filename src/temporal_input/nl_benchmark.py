"""Build controlled natural-language temporal queries from short legal PDDL traces."""

from __future__ import annotations

import hashlib
import itertools
import json
import re
import time
from collections import Counter
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from pathlib import Path
from typing import Iterable
from typing import Mapping
from typing import Sequence
from typing import Callable

from utils.pddl_parser import PDDLAction
from utils.pddl_parser import PDDLDomain
from utils.pddl_parser import PDDLNumericCondition
from utils.pddl_parser import PDDLNumericEffect
from utils.pddl_parser import PDDLNumericExpression
from utils.pddl_parser import PDDLParser
from utils.pddl_parser import PDDLProblem


DEFAULT_DOMAINS = (
	"barman",
	"ferry",
	"gripper",
	"logistics",
	"miconic",
	"rovers",
	"satellite",
	"transport",
	"numeric-ferry",
	"numeric-miconic",
	"numeric-minecraft",
	"numeric-transport",
	"blocksworld-clear",
	"blocksworld-on",
	"blocksworld-tower",
	"depots",
)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
_VARIABLE_NAMES = tuple("XYZABCDEFGHIJKLMNOPQRSTUVW")


@dataclass(frozen=True)
class BuildConfig:
	"""Pre-registered bounds for deterministic legal-trace construction."""

	max_actions_per_state: int = 12
	max_candidates_per_problem: int = 1024
	max_join_bindings: int = 64
	max_trace_depth: int = 3
	expanded_max_actions_per_state: int = 32
	expanded_max_join_bindings: int = 2048


@dataclass(frozen=True, order=True)
class GroundAtom:
	"""One positive grounded propositional PDDL fact."""

	predicate: str
	arguments: tuple[str, ...] = ()

	def render(self) -> str:
		return self.predicate if not self.arguments else (
		f"{self.predicate}({', '.join(self.arguments)})"
		)


@dataclass(frozen=True, order=True)
class NumericKey:
	"""One grounded numeric PDDL function key."""

	function: str
	arguments: tuple[str, ...] = ()

	def render(self) -> str:
		return self.function if not self.arguments else (
		f"{self.function}({', '.join(self.arguments)})"
		)


@dataclass(frozen=True)
class LiteralPattern:
	"""One positive or negative lifted predicate literal in an action schema."""

	predicate: str
	arguments: tuple[str, ...]
	positive: bool = True


@dataclass(frozen=True)
class ActionSchema:
	"""PDDL action schema lowered to the benchmark construction fragment."""

	name: str
	parameters: tuple[str, ...]
	parameter_types: Mapping[str, str]
	preconditions: tuple[LiteralPattern, ...]
	effects: tuple[LiteralPattern, ...]
	numeric_preconditions: tuple[PDDLNumericCondition, ...]
	numeric_effects: tuple[PDDLNumericEffect, ...]


@dataclass(frozen=True)
class PDDLCatalog:
	"""Schema-only PDDL information used by the natural-language builder."""

	domain: PDDLDomain
	type_parents: Mapping[str, str]
	predicate_types: Mapping[str, tuple[str, ...]]
	function_types: Mapping[str, tuple[str, ...]]
	actions: tuple[ActionSchema, ...]


@dataclass(frozen=True)
class GroundState:
	"""One replay state with propositional and integer numeric fluents."""

	facts: frozenset[GroundAtom]
	numeric_values: tuple[tuple[NumericKey, int], ...]
	fact_index_items: tuple[tuple[str, tuple[GroundAtom, ...]], ...] = field(
		default=(),
		compare=False,
		hash=False,
		repr=False,
	)

	@property
	def numeric(self) -> dict[NumericKey, int]:
		return dict(self.numeric_values)

	@property
	def fact_index(self) -> dict[str, tuple[GroundAtom, ...]]:
		return dict(self.fact_index_items)

	def fingerprint(self) -> str:
		payload = {
			"facts": [atom.render() for atom in sorted(self.facts)],
			"numeric": [
				[key.render(), value]
				for key, value in sorted(self.numeric_values)
			],
		}
		return hashlib.sha256(
			json.dumps(payload, separators=(",", ":"), sort_keys=True).encode(),
		).hexdigest()


@dataclass(frozen=True)
class GroundAction:
	"""One fully bound action call known to be applicable in a state."""

	name: str
	arguments: tuple[str, ...]
	binding_items: tuple[tuple[str, str], ...]

	@property
	def binding(self) -> dict[str, str]:
		return dict(self.binding_items)

	def render(self) -> str:
		return f"({self.name}{' ' if self.arguments else ''}{' '.join(self.arguments)})"


@dataclass(frozen=True)
class TraceReplay:
	"""Certified PDDL replay of a concrete primitive-action sequence."""

	actions: tuple[GroundAction, ...]
	states: tuple[GroundState, ...]


@dataclass(frozen=True)
class VariableSpec:
	"""One typed lifted parameter exposed in a natural-language query."""

	name: str
	pddl_type: str


@dataclass(frozen=True)
class TemporalAtom:
	"""One lifted predicate or numeric equality used by the hidden oracle."""

	atom_id: str
	kind: str
	symbol: str
	arguments: tuple[str, ...]
	value: int | None = None

	def to_dict(self) -> dict[str, object]:
		payload: dict[str, object] = {
			"atom_id": self.atom_id,
			"kind": self.kind,
			"arguments": list(self.arguments),
		}
		payload["predicate" if self.kind == "predicate" else "function"] = self.symbol
		if self.value is not None:
			payload["value"] = self.value
		return payload


@dataclass(frozen=True)
class Candidate:
	"""One witness-certified lifted ordered query candidate."""

	profile: str
	actions: tuple[GroundAction, ...]
	witness_states: tuple[GroundState, ...]
	atoms: tuple[TemporalAtom, ...]
	variables: tuple[VariableSpec, ...]
	constraints: tuple[tuple[str, str], ...]
	assignment_items: tuple[tuple[str, str], ...]
	source_text: str
	gold_formula_ast: Mapping[str, object]
	semantic_signature: str
	selection_signature: str
	quality_score: tuple[int, ...]
	witness_valid: bool = True

	@property
	def assignment(self) -> dict[str, str]:
		return dict(self.assignment_items)

	@property
	def state_fingerprints(self) -> tuple[str, ...]:
		return tuple(state.fingerprint() for state in self.witness_states)


@dataclass(frozen=True)
class ManifestRow:
	"""One public or private construction outcome for a test problem."""

	sample_id: str
	domain: str
	problem_file: str
	catalog_file: str
	status: str
	profile: str | None
	construction_tier: str | None
	source_text: str | None
	declared_parameters: tuple[VariableSpec, ...]
	constraints: tuple[tuple[str, str], ...]
	semantic_signature: str | None
	gold_atoms: tuple[TemporalAtom, ...] = ()
	gold_formula_ast: Mapping[str, object] | None = None
	assignment: Mapping[str, str] | None = None
	witness_actions: tuple[str, ...] = ()
	state_fingerprints: tuple[str, ...] = ()
	failure_reason: str | None = None

	def to_public_dict(self) -> dict[str, object]:
		return {
			"sample_id": self.sample_id,
			"domain": self.domain,
			"problem_file": self.problem_file,
			"catalog_file": self.catalog_file,
			"status": self.status,
			"profile": self.profile,
			"construction_tier": self.construction_tier,
			"parameter_semantics": "externally_bound",
			"source_text": self.source_text,
			"declared_parameters": [asdict(item) for item in self.declared_parameters],
			"constraints": [
				{"operator": "not_equal", "left": left, "right": right}
				for left, right in self.constraints
			],
			"semantic_signature": self.semantic_signature,
			"failure_reason": self.failure_reason,
		}

	def to_audit_dict(self) -> dict[str, object]:
		payload = self.to_public_dict()
		payload.update(
			{
				"gold_atoms": [atom.to_dict() for atom in self.gold_atoms],
				"gold_formula_ast": self.gold_formula_ast,
				"assignment": dict(self.assignment or {}),
				"witness_actions": list(self.witness_actions),
				"state_fingerprints": list(self.state_fingerprints),
			},
		)
		return payload


@dataclass(frozen=True)
class DomainNLManifest:
	"""Public natural-language rows and separate hidden construction audit rows."""

	domain: str
	public_rows: tuple[ManifestRow, ...]
	audit_rows: tuple[ManifestRow, ...]
	catalog: Mapping[str, object]


@dataclass(frozen=True)
class _GroundEvent:
	kind: str
	symbol: str
	arguments: tuple[str, ...]
	value: int | None
	negated: bool = False

	def objects(self) -> frozenset[str]:
		return frozenset(self.arguments)


def replay_ground_action_trace(
	*,
	domain_file: str | Path,
	problem_file: str | Path,
	action_lines: Sequence[str],
) -> TraceReplay:
	"""Replay one concrete trace and fail at the first inapplicable PDDL action."""

	catalog = _build_catalog(Path(domain_file))
	problem = PDDLParser.parse_problem(problem_file)
	if problem.domain_name not in {catalog.domain.name, "unknown_domain"}:
		raise ValueError(
			f"Problem domain {problem.domain_name!r} does not match {catalog.domain.name!r}.",
		)
	object_types = _all_object_types(catalog.domain, problem)
	schema_by_name = {schema.name: schema for schema in catalog.actions}
	state = _initial_state(problem)
	states = [state]
	actions: list[GroundAction] = []
	for step_index, line in enumerate(action_lines, start=1):
		name, arguments = _parse_ground_action_line(line)
		schema = schema_by_name.get(name)
		if schema is None:
			raise ValueError(f"Trace step {step_index} uses unknown action {name!r}.")
		if len(arguments) != len(schema.parameters):
			raise ValueError(
				f"Trace step {step_index} action {name!r} expects "
				f"{len(schema.parameters)} arguments; received {len(arguments)}.",
			)
		binding = dict(zip(schema.parameters, arguments))
		unknown_objects = [argument for argument in arguments if argument not in object_types]
		if unknown_objects:
			raise ValueError(
				f"Trace step {step_index} references unknown objects {unknown_objects}.",
			)
		if not _binding_types_valid(schema, binding, catalog, object_types):
			raise ValueError(f"Trace step {step_index} violates PDDL parameter types.")
		if not _binding_satisfies(schema, binding, state):
			raise ValueError(
				f"Trace step {step_index} action {name!r} has an unsatisfied precondition.",
			)
		action = GroundAction(
			name=name,
			arguments=arguments,
			binding_items=tuple(sorted(binding.items())),
		)
		state = _apply_action(catalog, state, action)
		actions.append(action)
		states.append(state)
	return TraceReplay(actions=tuple(actions), states=tuple(states))


def build_problem_candidates(
	*,
	domain_file: str | Path,
	problem_file: str | Path,
	config: BuildConfig | None = None,
) -> tuple[Candidate, ...]:
	"""Return bounded, deterministic ordered-query candidates for one problem."""
	settings = config or BuildConfig()
	if settings.max_trace_depth != 3:
		raise ValueError("The current profile set requires max_trace_depth=3.")
	catalog = _build_catalog(Path(domain_file))
	problem = PDDLParser.parse_problem(problem_file)
	object_types = _all_object_types(catalog.domain, problem)
	initial = _initial_state(problem)
	first_actions = _applicable_actions(
		catalog,
		problem,
		initial,
		object_types,
		settings,
	)
	candidates: list[Candidate] = []
	seen: set[tuple[str, tuple[str, ...]]] = set()
	profile_counts: Counter[str] = Counter()
	profile_limit = max(4, min(16, settings.max_candidates_per_problem // 5))

	def add_candidate(candidate: Candidate) -> None:
		key = (
			candidate.semantic_signature,
			tuple(action.render() for action in candidate.actions),
		)
		if key in seen or profile_counts[candidate.profile] >= profile_limit:
			return
		seen.add(key)
		profile_counts[candidate.profile] += 1
		candidates.append(candidate)

	first_paths: list[
		tuple[GroundAction, GroundState, tuple[_GroundEvent, ...], tuple[_GroundEvent, ...]]
	] = []
	first_limit = min(len(first_actions), 4)
	for first_action in first_actions[:first_limit]:
		state_one = _apply_action(catalog, initial, first_action)
		if state_one == initial:
			continue
		first_events = _positive_events(initial, state_one, catalog, object_types)
		if not first_events:
			continue
		_validate_witness(
			catalog=catalog,
			initial_state=initial,
			object_types=object_types,
			states=(initial, state_one),
			actions=(first_action,),
		)
		deleted_events = _deleted_events(initial, state_one, catalog, object_types)
		first_paths.append((first_action, state_one, first_events, deleted_events))
		for left, right in itertools.combinations(first_events, 2):
			if profile_counts["same_state_conjunction"] >= profile_limit:
				break
			add_candidate(
				_lift_candidate(
					catalog=catalog,
					problem=problem,
					object_types=object_types,
					states=(initial, state_one),
					actions=(first_action,),
					events=(left, right),
					profile="same_state_conjunction",
				),
			)
		for positive_event, deleted_event in itertools.product(first_events, deleted_events):
			if profile_counts["same_state_with_negation"] >= profile_limit:
				break
			add_candidate(
				_lift_candidate(
					catalog=catalog,
					problem=problem,
					object_types=object_types,
					states=(initial, state_one),
					actions=(first_action,),
					events=(positive_event, deleted_event),
					profile="same_state_with_negation",
				),
			)

	second_paths: list[
		tuple[
			GroundAction,
			GroundState,
			tuple[_GroundEvent, ...],
			GroundAction,
			GroundState,
			tuple[_GroundEvent, ...],
		]
	] = []
	dynamic_predicates = {
		effect.predicate for schema in catalog.actions for effect in schema.effects
	}
	for first_action, state_one, first_events, _ in first_paths:
		if (
			profile_counts["ordered_two_milestone"] >= profile_limit
			and profile_counts["persistence_until"] >= profile_limit
			and second_paths
		):
			break
		second_actions = _applicable_actions(
			catalog,
			problem,
			state_one,
			object_types,
			settings,
		)
		for second_action in second_actions[:4]:
			state_two = _apply_action(catalog, state_one, second_action)
			if state_two in {initial, state_one}:
				continue
			second_events = _positive_events(state_one, state_two, catalog, object_types)
			if not second_events:
				continue
			_validate_witness(
				catalog=catalog,
				initial_state=initial,
				object_types=object_types,
				states=(initial, state_one, state_two),
				actions=(first_action, second_action),
			)
			second_paths.append(
				(
					first_action,
					state_one,
					first_events,
					second_action,
					state_two,
					second_events,
				),
			)
			for first_event, second_event in itertools.product(first_events, second_events):
				if profile_counts["ordered_two_milestone"] >= profile_limit:
					break
				add_candidate(
					_lift_candidate(
						catalog=catalog,
						problem=problem,
						object_types=object_types,
						states=(initial, state_one, state_two),
						actions=(first_action, second_action),
						events=(first_event, second_event),
						profile="ordered_two_milestone",
					),
				)
			persisting: list[_GroundEvent] = []
			initial_index = initial.fact_index
			for predicate in (
				item.name
				for item in catalog.domain.predicates
				if item.name in dynamic_predicates
			):
				for atom in initial_index.get(predicate, ()):
					if atom in state_one.facts:
						persisting.append(
							_GroundEvent("predicate", atom.predicate, atom.arguments, None),
						)
						if len(persisting) >= 8:
							break
				if len(persisting) >= 8:
					break
			for persistent_event, second_event in itertools.product(
				persisting[:8], second_events,
			):
				if profile_counts["persistence_until"] >= profile_limit:
					break
				if _event_holds(second_event, initial):
					continue
				add_candidate(
					_lift_candidate(
						catalog=catalog,
						problem=problem,
						object_types=object_types,
						states=(initial, state_one, state_two),
						actions=(first_action, second_action),
						events=(persistent_event, second_event),
						profile="persistence_until",
					),
				)

	for (
		first_action,
		state_one,
		first_events,
		second_action,
		state_two,
		second_events,
	) in second_paths[:1]:
		if profile_counts["ordered_three_milestone"] >= min(8, profile_limit):
			break
		third_actions = _applicable_actions(
			catalog,
			problem,
			state_two,
			object_types,
			settings,
		)
		for third_action in third_actions[:4]:
			if profile_counts["ordered_three_milestone"] >= min(8, profile_limit):
				break
			state_three = _apply_action(catalog, state_two, third_action)
			if state_three in {initial, state_one, state_two}:
				continue
			third_events = _positive_events(state_two, state_three, catalog, object_types)
			if not third_events:
				continue
			_validate_witness(
				catalog=catalog,
				initial_state=initial,
				object_types=object_types,
				states=(initial, state_one, state_two, state_three),
				actions=(first_action, second_action, third_action),
			)
			for event_tuple in itertools.product(first_events, second_events, third_events):
				if profile_counts["ordered_three_milestone"] >= min(8, profile_limit):
					break
				add_candidate(
					_lift_candidate(
						catalog=catalog,
						problem=problem,
						object_types=object_types,
						states=(initial, state_one, state_two, state_three),
						actions=(first_action, second_action, third_action),
						events=event_tuple,
						profile="ordered_three_milestone",
					),
				)
	return tuple(sorted(candidates, key=_candidate_sort_key))


def build_domain_nl_manifest(
	*,
	domain_dir: str | Path,
	config: BuildConfig | None = None,
	progress: Callable[[ManifestRow, float], None] | None = None,
) -> DomainNLManifest:
	"""Construct one public natural-language row for every test problem."""
	directory = Path(domain_dir)
	domain_file = directory / "domain.pddl"
	catalog = _build_catalog(domain_file)
	usage: Counter[str] = Counter()
	profile_usage: Counter[str] = Counter()
	public_rows: list[ManifestRow] = []
	audit_rows: list[ManifestRow] = []
	for problem_file in sorted((directory / "test").glob("*.pddl")):
		started = time.perf_counter()
		sample_id = _sample_id(directory.name, problem_file.stem)
		candidates = build_problem_candidates(
			domain_file=domain_file,
			problem_file=problem_file,
			config=config,
		)
		construction_tier = "primary"
		if not candidates:
			primary = config or BuildConfig()
			candidates = build_problem_candidates(
				domain_file=domain_file,
				problem_file=problem_file,
				config=replace(
					primary,
					max_actions_per_state=primary.expanded_max_actions_per_state,
					max_join_bindings=primary.expanded_max_join_bindings,
				),
			)
			construction_tier = "expanded"
		if not candidates:
			row = _failure_row(
				sample_id=sample_id,
				domain=directory.name,
				problem_file=problem_file,
				reason="No non-repeating two-action trace produced an ordered event pair.",
			)
			public_rows.append(row)
			audit_rows.append(row)
			if progress is not None:
				progress(row, time.perf_counter() - started)
			continue
		selected = min(
			candidates,
			key=lambda candidate: (
				profile_usage[candidate.profile],
				usage[candidate.semantic_signature],
				candidate.quality_score,
				candidate.selection_signature,
			),
		)
		usage[selected.semantic_signature] += 1
		profile_usage[selected.profile] += 1
		common = {
			"sample_id": sample_id,
			"domain": directory.name,
			"problem_file": _relative_path(problem_file),
			"catalog_file": f"domains/{directory.name}/catalog.json",
			"status": "constructed_temporal_query",
			"profile": selected.profile,
			"construction_tier": construction_tier,
			"source_text": selected.source_text,
			"declared_parameters": selected.variables,
			"constraints": selected.constraints,
			"semantic_signature": selected.semantic_signature,
		}
		public_rows.append(ManifestRow(**common))
		audit_rows.append(
			ManifestRow(
				**common,
				gold_atoms=selected.atoms,
				gold_formula_ast=selected.gold_formula_ast,
				assignment=selected.assignment,
				witness_actions=tuple(action.render() for action in selected.actions),
				state_fingerprints=selected.state_fingerprints,
			),
		)
		if progress is not None:
			progress(public_rows[-1], time.perf_counter() - started)
	public_catalog = dict(_public_catalog(catalog))
	public_catalog["benchmark_domain"] = directory.name
	public_catalog["pddl_domain"] = catalog.domain.name
	return DomainNLManifest(
		domain=directory.name,
		public_rows=tuple(public_rows),
		audit_rows=tuple(audit_rows),
		catalog=public_catalog,
	)


def write_natural_language_benchmark(
	*,
	domains_root: str | Path,
	output_root: str | Path,
	domain_names: Sequence[str] = DEFAULT_DOMAINS,
	config: BuildConfig | None = None,
	progress: Callable[[ManifestRow, float], None] | None = None,
) -> dict[str, object]:
	"""Write public NL manifests plus private witness and oracle audit records."""
	root = Path(output_root)
	root.mkdir(parents=True, exist_ok=True)
	settings = config or BuildConfig()
	all_public: list[dict[str, object]] = []
	domain_summaries: list[dict[str, object]] = []
	for domain_name in domain_names:
		manifest = build_domain_nl_manifest(
			domain_dir=Path(domains_root) / domain_name,
			config=settings,
			progress=progress,
		)
		domain_root = root / "domains" / domain_name
		domain_root.mkdir(parents=True, exist_ok=True)
		public = [row.to_public_dict() for row in manifest.public_rows]
		audit = [row.to_audit_dict() for row in manifest.audit_rows]
		_write_json(domain_root / "catalog.json", manifest.catalog)
		_write_json(domain_root / "natural_language_manifest.json", public)
		_write_jsonl(domain_root / "construction_audit.jsonl", audit)
		all_public.extend(public)
		constructed = sum(row["status"] == "constructed_temporal_query" for row in public)
		expanded = sum(row["construction_tier"] == "expanded" for row in public)
		domain_summaries.append(
			{
				"domain": domain_name,
				"problem_count": len(public),
				"constructed_count": constructed,
				"expanded_count": expanded,
				"construction_rate": constructed / len(public) if public else 0.0,
				"unique_semantic_signature_count": len(
					{row["semantic_signature"] for row in public if row["semantic_signature"]}
				),
			},
		)
	_write_jsonl(root / "natural_language_manifest.jsonl", all_public)
	summary = {
		"schema_version": 1,
		"artifact_kind": "lifted_temporal_natural_language_benchmark",
		"handoff_boundary": "natural_language_manifest",
		"model_generated_ltlf_included": False,
		"settings": asdict(settings),
		"domains": domain_summaries,
		"problem_count": len(all_public),
		"constructed_count": sum(
			row["status"] == "constructed_temporal_query" for row in all_public
		),
		"public_manifest": "natural_language_manifest.jsonl",
		"private_audit_pattern": "domains/<domain>/construction_audit.jsonl",
	}
	_write_json(root / "manifest.json", summary)
	return summary


def _build_catalog(domain_file: Path) -> PDDLCatalog:
	domain = PDDLParser.parse_domain(domain_file)
	return PDDLCatalog(
		domain=domain,
		type_parents=_type_parent_map(domain.types),
		predicate_types={
			predicate.name: tuple(_parameter_type(item) for item in predicate.parameters)
			for predicate in domain.predicates
		},
		function_types={
			function.name: tuple(_parameter_type(item) for item in function.parameters)
			for function in domain.functions
		},
		actions=tuple(_lower_action(action) for action in domain.actions),
	)


def _lower_action(action: PDDLAction) -> ActionSchema:
	parameters = tuple(_parameter_name(item) for item in action.parameters)
	return ActionSchema(
		name=action.name,
		parameters=parameters,
		parameter_types={
			_parameter_name(item): _parameter_type(item) for item in action.parameters
		},
		preconditions=_parse_literals(action.preconditions),
		effects=_parse_literals(action.effects),
		numeric_preconditions=tuple(action.numeric_preconditions),
		numeric_effects=tuple(action.numeric_effects),
	)


def _initial_state(problem: PDDLProblem) -> GroundState:
	ordered_facts = tuple(
		GroundAtom(fact.predicate, tuple(fact.args))
		for fact in problem.init_facts
		if fact.is_positive
	)
	facts = frozenset(ordered_facts)
	fact_index: dict[str, list[GroundAtom]] = {}
	for atom in ordered_facts:
		fact_index.setdefault(atom.predicate, []).append(atom)
	numeric = tuple(
		sorted(
			(
				NumericKey(assignment.fluent.function, tuple(assignment.fluent.args)),
				assignment.value,
			)
			for assignment in problem.numeric_init
		),
	)
	return GroundState(
		facts=facts,
		numeric_values=numeric,
		fact_index_items=tuple(
			(predicate, tuple(atoms)) for predicate, atoms in fact_index.items()
		),
	)


def _applicable_actions(
	catalog: PDDLCatalog,
	problem: PDDLProblem,
	state: GroundState,
	object_types: Mapping[str, str],
	config: BuildConfig,
) -> tuple[GroundAction, ...]:
	facts_by_predicate = state.fact_index
	object_order = {name: index for index, name in enumerate(object_types)}
	per_schema_limit = max(
		8,
		(config.max_actions_per_state + max(1, len(catalog.actions)) - 1)
		// max(1, len(catalog.actions)),
	)
	by_schema: list[list[GroundAction]] = []
	for schema in catalog.actions:
		bindings: list[dict[str, str]] = [{}]
		positive = [literal for literal in schema.preconditions if literal.positive]
		positive.sort(key=lambda item: len(facts_by_predicate.get(item.predicate, ())))
		for literal in positive:
			next_bindings: list[dict[str, str]] = []
			for binding in bindings:
				for atom in facts_by_predicate.get(literal.predicate, ()):
					unified = _unify_literal(literal, atom, binding)
					if unified is not None:
						next_bindings.append(unified)
						if len(next_bindings) >= config.max_join_bindings:
							break
				if len(next_bindings) >= config.max_join_bindings:
					break
			bindings = _deduplicate_bindings(next_bindings)
			if not bindings:
				break
		grounded: list[GroundAction] = []
		for binding in bindings:
			for completed in _complete_binding(
				schema,
				binding,
				catalog,
				object_types,
			):
				if not _binding_types_valid(
					schema,
					completed,
					catalog,
					object_types,
				):
					continue
				if not _binding_satisfies(schema, completed, state):
					continue
				grounded.append(
					GroundAction(
						name=schema.name,
						arguments=tuple(completed[name] for name in schema.parameters),
						binding_items=tuple(sorted(completed.items())),
					),
				)
				if len(grounded) >= per_schema_limit:
					break
			if len(grounded) >= per_schema_limit:
				break
		by_schema.append(
			sorted(
				set(grounded),
				key=lambda action: tuple(object_order[item] for item in action.arguments),
			),
		)
	actions: list[GroundAction] = []
	for offset in range(max((len(items) for items in by_schema), default=0)):
		for items in by_schema:
			if offset < len(items):
				actions.append(items[offset])
				if len(actions) >= config.max_actions_per_state:
					return tuple(actions)
	return tuple(actions)


def _unify_literal(
	literal: LiteralPattern,
	atom: GroundAtom,
	binding: Mapping[str, str],
) -> dict[str, str] | None:
	if len(literal.arguments) != len(atom.arguments):
		return None
	result = dict(binding)
	for term, value in zip(literal.arguments, atom.arguments):
		if term.startswith("?"):
			known = result.get(term)
			if known is not None and known != value:
				return None
			result[term] = value
		elif term != value:
			return None
	return result


def _complete_binding(
	schema: ActionSchema,
	binding: Mapping[str, str],
	catalog: PDDLCatalog,
	object_types: Mapping[str, str],
) -> Iterable[dict[str, str]]:
	unbound = [name for name in schema.parameters if name not in binding]
	if not unbound:
		yield dict(binding)
		return
	object_universe = tuple(object_types)
	choices = [
		[
			object_name
			for object_name in object_universe
			if _object_has_type(
				object_types[object_name],
				schema.parameter_types.get(name, "object"),
				catalog.type_parents,
			)
		]
		for name in unbound
	]
	for values in itertools.product(*choices):
		completed = dict(binding)
		completed.update(zip(unbound, values))
		yield completed


def _binding_satisfies(
	schema: ActionSchema,
	binding: Mapping[str, str],
	state: GroundState,
) -> bool:
	for literal in schema.preconditions:
		atom = _ground_literal(literal, binding)
		if literal.positive != (atom in state.facts):
			return False
	return all(
		_evaluate_numeric_condition(condition, binding, state.numeric)
		for condition in schema.numeric_preconditions
	)


def _apply_action(
	catalog: PDDLCatalog,
	state: GroundState,
	action: GroundAction,
) -> GroundState:
	schema = next(item for item in catalog.actions if item.name == action.name)
	binding = action.binding
	facts = set(state.facts)
	ordered_add_effects: list[GroundAtom] = []
	ordered_delete_effects: list[GroundAtom] = []
	add_effects: set[GroundAtom] = set()
	delete_effects: set[GroundAtom] = set()
	for effect in schema.effects:
		atom = _ground_literal(effect, binding)
		if effect.positive:
			add_effects.add(atom)
			ordered_add_effects.append(atom)
		else:
			delete_effects.add(atom)
			ordered_delete_effects.append(atom)
	facts.difference_update(delete_effects)
	facts.update(add_effects)
	fact_index = state.fact_index
	for predicate in dict.fromkeys(
		atom.predicate for atom in (*ordered_delete_effects, *ordered_add_effects)
	):
		bucket = [
			atom
			for atom in fact_index.get(predicate, ())
			if atom not in delete_effects
		]
		for atom in ordered_add_effects:
			if atom.predicate == predicate and atom not in bucket:
				bucket.append(atom)
		fact_index[predicate] = tuple(bucket)
	numeric = state.numeric
	updates: dict[NumericKey, int] = {}
	for effect in schema.numeric_effects:
		key = NumericKey(
			effect.fluent.function,
			tuple(_ground_term(item, binding) for item in effect.fluent.args),
		)
		amount = _evaluate_numeric_expression(effect.amount, binding, state.numeric)
		delta = amount if effect.operator == "increase" else -amount
		updates[key] = updates.get(key, 0) + delta
	for key, delta in updates.items():
		numeric[key] = numeric.get(key, 0) + delta
	return GroundState(
		facts=frozenset(facts),
		numeric_values=tuple(sorted(numeric.items())),
		fact_index_items=tuple(fact_index.items()),
	)


def _positive_events(
	before: GroundState,
	after: GroundState,
	catalog: PDDLCatalog,
	object_types: Mapping[str, str],
) -> tuple[_GroundEvent, ...]:
	predicate_order, object_order = _structural_orders(catalog, object_types)
	events = [
		_GroundEvent("predicate", atom.predicate, atom.arguments, None)
		for atom in sorted(
			after.facts - before.facts,
			key=lambda item: _atom_structural_key(item, predicate_order, object_order),
		)
	]
	before_numeric = before.numeric
	for key, value in sorted(
		after.numeric.items(),
		key=lambda item: _numeric_structural_key(
			item[0],
			{function.name: index for index, function in enumerate(catalog.domain.functions)},
			object_order,
		),
	):
		if before_numeric.get(key) != value:
			events.append(_GroundEvent("numeric_equality", key.function, key.arguments, value))
	return tuple(events)


def _deleted_events(
	before: GroundState,
	after: GroundState,
	catalog: PDDLCatalog,
	object_types: Mapping[str, str],
) -> tuple[_GroundEvent, ...]:
	predicate_order, object_order = _structural_orders(catalog, object_types)
	return tuple(
		_GroundEvent("predicate", atom.predicate, atom.arguments, None, negated=True)
		for atom in sorted(
			before.facts - after.facts,
			key=lambda item: _atom_structural_key(item, predicate_order, object_order),
		)
	)


def _lift_candidate(
	*,
	catalog: PDDLCatalog,
	problem: PDDLProblem,
	object_types: Mapping[str, str],
	states: tuple[GroundState, ...],
	actions: tuple[GroundAction, ...],
	events: tuple[_GroundEvent, ...],
	profile: str,
) -> Candidate:
	constant_names = frozenset(catalog.domain.constants)
	object_to_variable: dict[str, str] = {}
	variables: list[VariableSpec] = []
	assignment: list[tuple[str, str]] = []

	def lift_argument(argument: str) -> str:
		if argument in constant_names:
			return argument
		if argument not in object_to_variable:
			index = len(object_to_variable)
			name = _VARIABLE_NAMES[index] if index < len(_VARIABLE_NAMES) else f"V{index + 1}"
			object_to_variable[argument] = name
			variables.append(VariableSpec(name=name, pddl_type=object_types.get(argument, "object")))
			assignment.append((name, argument))
		return object_to_variable[argument]

	atoms = tuple(
		TemporalAtom(
			atom_id=f"a{index}",
			kind=event.kind,
			symbol=event.symbol,
			arguments=tuple(lift_argument(item) for item in event.arguments),
			value=event.value,
		)
		for index, event in enumerate(events)
	)
	constraints = tuple(
		(left.name, right.name)
		for index, left in enumerate(variables)
		for right in variables[index + 1 :]
		if _types_may_alias(left.pddl_type, right.pddl_type, catalog.type_parents)
	)
	formula_ast = _formula_ast(profile, events)
	if not _formula_holds_on_trace(formula_ast, events, states):
		raise ValueError(
			f"Constructed profile {profile!r} is false on its source witness.",
		)
	signature_payload = {
		"profile": profile,
		"variables": [asdict(item) for item in variables],
		"constraints": constraints,
		"atoms": [item.to_dict() for item in atoms],
		"formula_ast": formula_ast,
	}
	semantic_signature = hashlib.sha256(
		json.dumps(signature_payload, sort_keys=True, separators=(",", ":")).encode(),
	).hexdigest()
	selection_signature = _selection_signature(
		catalog=catalog,
		problem=problem,
		variables=tuple(variables),
		constraints=constraints,
		atoms=atoms,
		formula_ast=formula_ast,
		actions=actions,
	)
	first_survives = _event_holds(events[0], states[-1])
	shared_count = sum(
		len(left.objects() & right.objects())
		for left, right in itertools.pairwise(events)
	)
	numeric_count = sum(event.kind == "numeric_equality" for event in events)
	quality_score = (
		1 if first_survives else 0,
		0 if variables else 1,
		-shared_count,
		-numeric_count,
		sum(len(event.arguments) for event in events),
	)
	return Candidate(
		profile=profile,
		actions=actions,
		witness_states=states,
		atoms=atoms,
		variables=tuple(variables),
		constraints=constraints,
		assignment_items=tuple(assignment),
		source_text=_render_controlled_english(
			tuple(variables), constraints, atoms, profile,
		),
		gold_formula_ast=formula_ast,
		semantic_signature=semantic_signature,
		selection_signature=selection_signature,
		quality_score=quality_score,
	)


def _validate_witness(
	*,
	catalog: PDDLCatalog,
	initial_state: GroundState,
	object_types: Mapping[str, str],
	states: tuple[GroundState, ...],
	actions: tuple[GroundAction, ...],
) -> None:
	if len(states) != len(actions) + 1 or states[0] != initial_state:
		raise ValueError("Witness states do not match the problem initial state and action count.")
	if len(set(states)) != len(states):
		raise ValueError("Witness contains a repeated complete state.")
	current = states[0]
	for index, action in enumerate(actions):
		schema = next(item for item in catalog.actions if item.name == action.name)
		binding = action.binding
		if not _binding_types_valid(schema, binding, catalog, object_types):
			raise ValueError(f"Witness action {action.render()} violates its parameter types.")
		if not _binding_satisfies(schema, binding, current):
			raise ValueError(
				f"Witness action {action.render()} is inapplicable at step {index}.",
			)
		current = _apply_action(catalog, current, action)
		if current != states[index + 1]:
			raise ValueError(
				f"Witness replay diverges after action {action.render()} at step {index}.",
			)


def _binding_types_valid(
	schema: ActionSchema,
	binding: Mapping[str, str],
	catalog: PDDLCatalog,
	object_types: Mapping[str, str],
) -> bool:
	return all(
		object_name in object_types
		and _object_has_type(
			object_types[object_name],
			schema.parameter_types.get(parameter, "object"),
			catalog.type_parents,
		)
		for parameter, object_name in (
			(parameter, binding[parameter]) for parameter in schema.parameters
		)
	)


def _render_controlled_english(
	variables: tuple[VariableSpec, ...],
	constraints: tuple[tuple[str, str], ...],
	atoms: tuple[TemporalAtom, ...],
	profile: str,
) -> str:
	if variables:
		declarations = _join_english(
			[
				f"parameter {item.name} of PDDL type {item.pddl_type}"
				for item in variables
			],
		)
		prefix = f"Given {declarations}"
	else:
		prefix = "For the declared PDDL domain"
	if constraints:
		differences = _join_english(
			[f"{left} differs from {right}" for left, right in constraints],
		)
		prefix += f", where {differences}"
	if profile == "same_state_conjunction":
		return (
			f"{prefix}, ensure that at some state, both {_render_atom(atoms[0])} "
			f"and {_render_atom(atoms[1])}."
		)
	if profile == "same_state_with_negation":
		return (
			f"{prefix}, ensure that at some state, {_render_atom(atoms[0])}, "
			f"while {_render_atom(atoms[1], negated=True)}."
		)
	if profile == "persistence_until":
		return (
			f"{prefix}, ensure that {_render_atom(atoms[0])} at every state before "
			f"the first state where {_render_atom(atoms[1])}."
		)
	if profile == "ordered_three_milestone":
		return (
			f"{prefix}, ensure that at some state, {_render_atom(atoms[0])}; "
			f"at a strictly later state, {_render_atom(atoms[1])}; and at a "
			f"strictly later state after that, {_render_atom(atoms[2])}."
		)
	return (
		f"{prefix}, ensure that at some state, {_render_atom(atoms[0])}, "
		f"and at a strictly later state, {_render_atom(atoms[1])}."
	)


def _formula_ast(
	profile: str,
	events: tuple[_GroundEvent, ...],
) -> Mapping[str, object]:
	if not events:
		raise ValueError("A temporal formula requires at least one event.")

	def atom(index: int) -> dict[str, str]:
		return {"operator": "atom", "atom_id": f"a{index}"}
	if profile == "same_state_conjunction":
		return {
			"operator": "eventually",
			"operand": {"operator": "and", "operands": [atom(0), atom(1)]},
		}
	if profile == "same_state_with_negation":
		return {
			"operator": "eventually",
			"operand": {
				"operator": "and",
				"operands": [
					atom(0),
					{"operator": "not", "operand": atom(1)},
				],
			},
		}
	if profile == "persistence_until":
		return {"operator": "until", "left": atom(0), "right": atom(1)}
	if profile == "ordered_three_milestone":
		return {
			"operator": "eventually",
			"operand": {
				"operator": "and",
				"operands": [
					atom(0),
					{
						"operator": "next",
						"operand": {
							"operator": "eventually",
							"operand": {
								"operator": "and",
								"operands": [
									atom(1),
									{
										"operator": "next",
										"operand": {
											"operator": "eventually",
											"operand": atom(2),
										},
									},
								],
							},
						},
					},
				],
			},
		}
	return {
		"operator": "eventually",
		"operand": {
			"operator": "and",
			"operands": [
				atom(0),
				{
					"operator": "next",
					"operand": {
						"operator": "eventually",
						"operand": atom(1),
					},
				},
			],
		},
	}


def _render_atom(atom: TemporalAtom, *, negated: bool = False) -> str:
	if atom.kind == "predicate":
		verb = "does not hold" if negated else "holds"
		if atom.arguments:
			argument_label = "argument" if len(atom.arguments) == 1 else "arguments"
			return (
				f"predicate {atom.symbol} {verb} for {argument_label} "
				f"{_join_english(list(atom.arguments))}"
			)
		return f"zero-arity predicate {atom.symbol} {verb}"
	arguments = (
		f" for {'argument' if len(atom.arguments) == 1 else 'arguments'} "
		f"{_join_english(list(atom.arguments))}"
		if atom.arguments
		else ""
	)
	comparison = "does not equal" if negated else "equals"
	return f"numeric function {atom.symbol}{arguments} {comparison} {atom.value}"


def _event_holds(event: _GroundEvent, state: GroundState) -> bool:
	if event.kind == "predicate":
		holds = GroundAtom(event.symbol, event.arguments) in state.facts
		return not holds if event.negated else holds
	return state.numeric.get(NumericKey(event.symbol, event.arguments)) == event.value


def _formula_holds_on_trace(
	formula: Mapping[str, object],
	events: tuple[_GroundEvent, ...],
	states: tuple[GroundState, ...],
) -> bool:
	"""Evaluate the hidden formula independently under finite-trace semantics."""
	event_by_id = {f"a{index}": event for index, event in enumerate(events)}

	def evaluate(node: Mapping[str, object], position: int) -> bool:
		operator = str(node.get("operator", ""))
		if operator == "atom":
			event = event_by_id[str(node["atom_id"])]
			if event.kind == "predicate":
				return GroundAtom(event.symbol, event.arguments) in states[position].facts
			return (
				states[position].numeric.get(NumericKey(event.symbol, event.arguments))
				== event.value
			)
		if operator == "not":
			return not evaluate(_as_formula_node(node["operand"]), position)
		if operator == "and":
			return all(
				evaluate(_as_formula_node(operand), position)
				for operand in _as_formula_nodes(node["operands"])
			)
		if operator == "next":
			return position + 1 < len(states) and evaluate(
				_as_formula_node(node["operand"]),
				position + 1,
			)
		if operator == "eventually":
			return any(
				evaluate(_as_formula_node(node["operand"]), future)
				for future in range(position, len(states))
			)
		if operator == "until":
			left = _as_formula_node(node["left"])
			right = _as_formula_node(node["right"])
			return any(
				evaluate(right, future)
				and all(evaluate(left, prior) for prior in range(position, future))
				for future in range(position, len(states))
			)
		raise ValueError(f"Unsupported hidden temporal operator: {operator!r}")

	return bool(states) and evaluate(formula, 0)


def _as_formula_node(value: object) -> Mapping[str, object]:
	if not isinstance(value, Mapping):
		raise ValueError(f"Expected formula node, received {value!r}.")
	return value


def _as_formula_nodes(value: object) -> tuple[Mapping[str, object], ...]:
	if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
		raise ValueError(f"Expected formula node sequence, received {value!r}.")
	return tuple(_as_formula_node(item) for item in value)


def _ground_literal(
	literal: LiteralPattern,
	binding: Mapping[str, str],
) -> GroundAtom:
	return GroundAtom(
		literal.predicate,
		tuple(_ground_term(argument, binding) for argument in literal.arguments),
	)


def _ground_term(term: str, binding: Mapping[str, str]) -> str:
	return binding[term] if term.startswith("?") else term


def _parse_ground_action_line(line: str) -> tuple[str, tuple[str, ...]]:
	text = str(line or "").strip()
	match = re.search(r"\(([^()]*)\)", text)
	if match is None:
		raise ValueError(f"Invalid PDDL plan action line: {line!r}.")
	tokens = tuple(token.lower() for token in match.group(1).split() if token.strip())
	if not tokens:
		raise ValueError(f"Empty PDDL plan action line: {line!r}.")
	return tokens[0], tokens[1:]


def _evaluate_numeric_condition(
	condition: PDDLNumericCondition,
	binding: Mapping[str, str],
	numeric: Mapping[NumericKey, int],
) -> bool:
	left = _evaluate_numeric_expression(condition.left, binding, numeric)
	right = _evaluate_numeric_expression(condition.right, binding, numeric)
	return {
		">": left > right,
		">=": left >= right,
		"<": left < right,
		"<=": left <= right,
		"=": left == right,
	}[condition.comparator]


def _evaluate_numeric_expression(
	expression: PDDLNumericExpression,
	binding: Mapping[str, str],
	numeric: Mapping[NumericKey, int],
) -> int:
	if expression.kind == "constant":
		return int(expression.value)
	key = NumericKey(
		expression.value,
		tuple(_ground_term(item, binding) for item in expression.args),
	)
	return int(numeric.get(key, 0))


def _parse_literals(expression: str) -> tuple[LiteralPattern, ...]:
	node = _parse_s_expression(expression)
	return tuple(_flatten_literals(node))


def _flatten_literals(node: object, *, positive: bool = True) -> Iterable[LiteralPattern]:
	if not isinstance(node, list) or not node:
		return ()
	head = str(node[0]).lower()
	if head == "and":
		return tuple(
			literal
			for child in node[1:]
			for literal in _flatten_literals(child, positive=positive)
		)
	if head == "not" and len(node) == 2:
		return tuple(_flatten_literals(node[1], positive=not positive))
	if head in {">", ">=", "<", "<=", "=", "increase", "decrease"}:
		return ()
	if any(isinstance(item, list) for item in node[1:]):
		raise ValueError(f"Unsupported nested PDDL literal: {node!r}")
	return (
		LiteralPattern(
			predicate=head,
			arguments=tuple(str(item).lower() for item in node[1:]),
			positive=positive,
		),
	)


def _parse_s_expression(expression: str) -> object:
	tokens = re.findall(r"\(|\)|[^\s()]+", str(expression or "").strip())
	position = 0

	def parse_one() -> object:
		nonlocal position
		if position >= len(tokens):
			return []
		token = tokens[position]
		position += 1
		if token != "(":
			return token.lower()
		items: list[object] = []
		while position < len(tokens) and tokens[position] != ")":
			items.append(parse_one())
		if position >= len(tokens):
			raise ValueError(f"Unmatched PDDL expression: {expression}")
		position += 1
		return items

	return parse_one()


def _all_object_types(domain: PDDLDomain, problem: PDDLProblem) -> dict[str, str]:
	result = dict(problem.object_types)
	result.update(domain.constant_types)
	return result


def _parameter_name(parameter: str) -> str:
	return parameter.split(" - ", 1)[0].strip().lower()


def _parameter_type(parameter: str) -> str:
	return (
		parameter.split(" - ", 1)[1].strip().lower()
		if " - " in parameter
		else "object"
	)


def _type_parent_map(tokens: Sequence[str]) -> dict[str, str]:
	parents: dict[str, str] = {}
	pending: list[str] = []
	index = 0
	while index < len(tokens):
		token = str(tokens[index]).lower()
		if token == "-" and index + 1 < len(tokens):
			parent = str(tokens[index + 1]).lower()
			for child in pending:
				parents[child] = parent
			pending = []
			index += 2
			continue
		pending.append(token)
		index += 1
	for child in pending:
		parents.setdefault(child, "object")
	return parents


def _object_has_type(
	actual: str,
	required: str,
	parents: Mapping[str, str],
) -> bool:
	if required == "object":
		return True
	current = actual
	seen: set[str] = set()
	while current not in seen:
		if current == required:
			return True
		seen.add(current)
		if current == "object":
			return False
		current = parents.get(current, "object")
	return False


def _types_may_alias(left: str, right: str, parents: Mapping[str, str]) -> bool:
	return _object_has_type(left, right, parents) or _object_has_type(right, left, parents)


def _deduplicate_bindings(bindings: Iterable[Mapping[str, str]]) -> list[dict[str, str]]:
	seen: set[tuple[tuple[str, str], ...]] = set()
	result: list[dict[str, str]] = []
	for binding in bindings:
		key = tuple(sorted(binding.items()))
		if key not in seen:
			seen.add(key)
			result.append(dict(binding))
	return result


def _candidate_sort_key(candidate: Candidate) -> tuple[object, ...]:
	return (
		candidate.quality_score,
		candidate.selection_signature,
	)


def _selection_signature(
	*,
	catalog: PDDLCatalog,
	problem: PDDLProblem,
	variables: tuple[VariableSpec, ...],
	constraints: tuple[tuple[str, str], ...],
	atoms: tuple[TemporalAtom, ...],
	formula_ast: Mapping[str, object],
	actions: tuple[GroundAction, ...],
) -> str:
	object_order = {
		name: index
		for index, name in enumerate((*problem.objects, *catalog.domain.constants))
	}
	type_ids: dict[str, int] = {}
	symbol_ids: dict[tuple[str, str], int] = {}
	action_ids: dict[str, int] = {}

	def type_id(type_name: str) -> int:
		return type_ids.setdefault(type_name, len(type_ids))

	def symbol_id(kind: str, symbol: str) -> int:
		key = (kind, symbol)
		return symbol_ids.setdefault(key, len(symbol_ids))

	def action_id(action_name: str) -> int:
		return action_ids.setdefault(action_name, len(action_ids))

	payload = {
		"variables": [type_id(item.pddl_type) for item in variables],
		"constraints": constraints,
		"atoms": [
			{
				"kind": item.kind,
				"symbol_index": symbol_id(item.kind, item.symbol),
				"arguments": item.arguments,
				"value": item.value,
			}
			for item in atoms
		],
		"formula_ast": formula_ast,
		"actions": [
			[
				action_id(action.name),
				*[object_order[argument] for argument in action.arguments],
			]
			for action in actions
		],
	}
	return _stable_hash(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _atom_structural_key(
	atom: GroundAtom,
	predicate_order: Mapping[str, int],
	object_order: Mapping[str, int],
) -> tuple[int, ...]:
	return (
		predicate_order[atom.predicate],
		*(object_order[item] for item in atom.arguments),
	)


def _numeric_structural_key(
	key: NumericKey,
	function_order: Mapping[str, int],
	object_order: Mapping[str, int],
) -> tuple[int, ...]:
	return (
		function_order[key.function],
		*(object_order[item] for item in key.arguments),
	)


def _structural_orders(
	catalog: PDDLCatalog,
	object_types: Mapping[str, str],
) -> tuple[dict[str, int], dict[str, int]]:
	return (
		{
			item.name: index
			for index, item in enumerate(catalog.domain.predicates)
		},
		{name: index for index, name in enumerate(object_types)},
	)


def _public_catalog(catalog: PDDLCatalog) -> dict[str, object]:
	return {
		"schema_version": 1,
		"domain": catalog.domain.name,
		"type_parents": dict(sorted(catalog.type_parents.items())),
		"constants": [
			{
				"name": name,
				"pddl_type": catalog.domain.constant_types.get(name, "object"),
			}
			for name in catalog.domain.constants
		],
		"predicates": [
			{"name": name, "argument_types": list(types)}
			for name, types in sorted(catalog.predicate_types.items())
		],
		"numeric_functions": [
			{"name": name, "argument_types": list(types)}
			for name, types in sorted(catalog.function_types.items())
		],
	}


def _failure_row(
	*, sample_id: str, domain: str, problem_file: Path, reason: str,
) -> ManifestRow:
	return ManifestRow(
		sample_id=sample_id,
		domain=domain,
		problem_file=_relative_path(problem_file),
		catalog_file=f"domains/{domain}/catalog.json",
		status="source_witness_not_found",
		profile=None,
		construction_tier=None,
		source_text=None,
		declared_parameters=(),
		constraints=(),
		semantic_signature=None,
		failure_reason=reason,
	)


def _sample_id(domain: str, problem: str) -> str:
	return re.sub(r"[^a-z0-9_]+", "_", f"{domain}_{problem}".lower()).strip("_")


def _relative_path(path: Path) -> str:
	try:
		return str(path.resolve().relative_to(PROJECT_ROOT))
	except ValueError:
		return str(path)


def _stable_hash(text: str) -> str:
	return hashlib.sha256(text.encode()).hexdigest()


def _join_english(items: Sequence[str]) -> str:
	if not items:
		return ""
	if len(items) == 1:
		return items[0]
	if len(items) == 2:
		return f"{items[0]} and {items[1]}"
	return f"{', '.join(items[:-1])}, and {items[-1]}"


def _write_json(path: Path, payload: object) -> None:
	path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
	path.write_text(
		"".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
		encoding="utf-8",
	)
