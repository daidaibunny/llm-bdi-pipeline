"""Certificate-producing validation for predicted temporally extended goals."""

from __future__ import annotations

import itertools
import json
import re
from collections import Counter
from collections import deque
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from evaluation.temporal_compilation.ltlf_to_dfa import LTLfToDFA
from evaluation.external_plan_verifier import run_external_plan_verifier
from temporal_input.nl_benchmark import GroundAtom
from temporal_input.nl_benchmark import GroundState
from temporal_input.nl_benchmark import NumericKey
from temporal_input.nl_benchmark import replay_ground_action_trace
from temporal_specification.prediction_validation import ValidatedLTLfPrediction


SemanticAtomKey = tuple[str, str, tuple[str, ...], int | None]


class TemporalGoalValidationError(ValueError):
	"""Fail-closed temporal validation error unrelated to model retry advice."""


@dataclass(frozen=True)
class DFAEquivalenceResult:
	"""Exact finite-trace language-equivalence result and optional counterexample."""

	equivalent: bool
	gold_formula: str
	prediction_formula: str
	gold_state_count: int
	prediction_state_count: int
	explored_product_state_count: int
	counterexample_trace: tuple[Mapping[str, bool], ...] = ()
	gold_accepts_counterexample: bool | None = None
	prediction_accepts_counterexample: bool | None = None

	def to_dict(self) -> dict[str, object]:
		return {
			"equivalent": self.equivalent,
			"gold_formula": self.gold_formula,
			"prediction_formula": self.prediction_formula,
			"gold_state_count": self.gold_state_count,
			"prediction_state_count": self.prediction_state_count,
			"explored_product_state_count": self.explored_product_state_count,
			"counterexample_trace": [dict(item) for item in self.counterexample_trace],
			"gold_accepts_counterexample": self.gold_accepts_counterexample,
			"prediction_accepts_counterexample": self.prediction_accepts_counterexample,
		}


@dataclass(frozen=True)
class WitnessValidationResult:
	"""Post-prediction validation on one hidden PDDL witness trace."""

	replay_valid: bool
	state_fingerprints_match: bool
	gold_accepted: bool
	prediction_accepted: bool
	action_count: int
	state_count: int

	def to_dict(self) -> dict[str, object]:
		return {
			"replay_valid": self.replay_valid,
			"state_fingerprints_match": self.state_fingerprints_match,
			"gold_accepted": self.gold_accepted,
			"prediction_accepted": self.prediction_accepted,
			"action_count": self.action_count,
			"state_count": self.state_count,
		}


@dataclass(frozen=True)
class ExecutionTraceValidationResult:
	"""Independent action-legality and temporal-acceptance result for one trace."""

	replay_valid: bool
	val_attempted: bool
	val_success: bool | None
	gold_accepted: bool
	prediction_accepted: bool
	action_count: int
	state_count: int
	neutral_problem_file: str
	plan_verifier_error: str | None = None

	@property
	def success(self) -> bool:
		return (
			self.replay_valid
			and self.val_success is True
			and self.gold_accepted
			and self.prediction_accepted
		)

	def to_dict(self) -> dict[str, object]:
		return {
			"success": self.success,
			"replay_valid": self.replay_valid,
			"val_attempted": self.val_attempted,
			"val_success": self.val_success,
			"gold_accepted": self.gold_accepted,
			"prediction_accepted": self.prediction_accepted,
			"action_count": self.action_count,
			"state_count": self.state_count,
			"neutral_problem_file": self.neutral_problem_file,
			"plan_verifier_error": self.plan_verifier_error,
		}


@dataclass(frozen=True)
class _GuardTransition:
	source_state: str
	target_state: str
	cube: str


@dataclass(frozen=True)
class _CompiledDFA:
	initial_state: str
	accepting_states: frozenset[str]
	free_variables: tuple[str, ...]
	transitions: tuple[_GuardTransition, ...]
	state_count: int

	def step(self, state: str, valuation: Mapping[str, bool]) -> str:
		matches = {
			transition.target_state
			for transition in self.transitions
			if transition.source_state == state
			and _cube_matches(
				transition.cube,
				free_variables=self.free_variables,
				valuation=valuation,
			)
		}
		if len(matches) != 1:
			raise TemporalGoalValidationError(
				"DFA transition relation must be total and deterministic; "
				f"state={state!r}, matching_targets={sorted(matches)}.",
			)
		return next(iter(matches))

	def accepts(self, trace: Sequence[Mapping[str, bool]]) -> bool:
		if not trace:
			raise TemporalGoalValidationError("LTLf validation requires a non-empty trace.")
		state = self.initial_state
		for valuation in trace:
			state = self.step(state, valuation)
		return state in self.accepting_states


def expand_translation_predictions(
	*,
	worklist_rows: Sequence[Mapping[str, Any]],
	prediction_rows: Sequence[Mapping[str, Any]],
	expected_sample_ids: set[str],
) -> dict[str, Mapping[str, Any]]:
	"""Expand one prediction per unique input to each covered problem exactly once."""

	predictions_by_id: dict[str, Mapping[str, Any]] = {}
	for index, row in enumerate(prediction_rows, start=1):
		translation_id = _required_text(row, "translation_id", label=f"prediction row {index}")
		if translation_id in predictions_by_id:
			raise ValueError(f"Duplicate prediction translation_id {translation_id!r}.")
		predictions_by_id[translation_id] = row

	membership: list[str] = []
	expanded: dict[str, Mapping[str, Any]] = {}
	seen_translation_ids: set[str] = set()
	for index, row in enumerate(worklist_rows, start=1):
		translation_id = _required_text(row, "translation_id", label=f"worklist row {index}")
		if translation_id in seen_translation_ids:
			raise ValueError(f"Duplicate worklist translation_id {translation_id!r}.")
		seen_translation_ids.add(translation_id)
		prediction = predictions_by_id.get(translation_id)
		if prediction is None:
			raise ValueError(f"Missing prediction for translation_id {translation_id!r}.")
		raw_members = row.get("member_sample_ids")
		if not isinstance(raw_members, Sequence) or isinstance(raw_members, (str, bytes)):
			raise ValueError(f"Worklist row {translation_id!r} has no member_sample_ids array.")
		for raw_sample_id in raw_members:
			sample_id = str(raw_sample_id or "").strip()
			membership.append(sample_id)
			if sample_id in expanded:
				raise ValueError(f"Every sample_id must occur exactly once; duplicate={sample_id!r}.")
			expanded[sample_id] = prediction
	if Counter(membership) != Counter(expected_sample_ids):
		missing = sorted(expected_sample_ids - set(membership))
		extra = sorted(set(membership) - expected_sample_ids)
		raise ValueError(
			"Worklist membership must cover every expected sample_id exactly once; "
			f"missing={missing}, extra={extra}.",
		)
	if set(predictions_by_id) != seen_translation_ids:
		raise ValueError(
			"Predictions contain translation_id values absent from the worklist: "
			f"{sorted(set(predictions_by_id) - seen_translation_ids)}.",
		)
	return expanded


def compare_gold_and_prediction(
	*,
	audit_row: Mapping[str, Any],
	prediction: ValidatedLTLfPrediction,
	max_alphabet_size: int = 12,
) -> DFAEquivalenceResult:
	"""Check exact LTLf language equivalence using a reachable DFA product."""

	gold_formula, prediction_formula, alphabet = _canonical_formula_pair(
		audit_row=audit_row,
		prediction=prediction,
	)
	if len(alphabet) > max_alphabet_size:
		raise TemporalGoalValidationError(
			f"DFA equivalence alphabet has {len(alphabet)} atoms; "
			f"configured exact bound is {max_alphabet_size}.",
		)
	gold_dfa = _compile_dfa(gold_formula)
	prediction_dfa = _compile_dfa(prediction_formula)
	valuations = tuple(_all_valuations(alphabet))
	queue: deque[tuple[str, str, tuple[Mapping[str, bool], ...]]] = deque()
	visited: set[tuple[str, str]] = set()
	for valuation in valuations:
		gold_state = gold_dfa.step(gold_dfa.initial_state, valuation)
		prediction_state = prediction_dfa.step(prediction_dfa.initial_state, valuation)
		trace = (valuation,)
		if (gold_state in gold_dfa.accepting_states) != (
			prediction_state in prediction_dfa.accepting_states
		):
			return _inequivalent_result(
				gold_formula,
				prediction_formula,
				gold_dfa,
				prediction_dfa,
				trace,
				explored_count=1,
			)
		pair = (gold_state, prediction_state)
		if pair not in visited:
			visited.add(pair)
			queue.append((gold_state, prediction_state, trace))
	while queue:
		gold_state, prediction_state, trace = queue.popleft()
		for valuation in valuations:
			next_gold = gold_dfa.step(gold_state, valuation)
			next_prediction = prediction_dfa.step(prediction_state, valuation)
			next_trace = (*trace, valuation)
			if (next_gold in gold_dfa.accepting_states) != (
				next_prediction in prediction_dfa.accepting_states
			):
				return _inequivalent_result(
					gold_formula,
					prediction_formula,
					gold_dfa,
					prediction_dfa,
					next_trace,
					explored_count=len(visited) + 1,
				)
			pair = (next_gold, next_prediction)
			if pair not in visited:
				visited.add(pair)
				queue.append((next_gold, next_prediction, next_trace))
	return DFAEquivalenceResult(
		equivalent=True,
		gold_formula=gold_formula,
		prediction_formula=prediction_formula,
		gold_state_count=gold_dfa.state_count,
		prediction_state_count=prediction_dfa.state_count,
		explored_product_state_count=len(visited),
	)


def validate_prediction_on_witness(
	*,
	audit_row: Mapping[str, Any],
	prediction: ValidatedLTLfPrediction,
	domain_file: str | Path,
	problem_file: str | Path,
) -> WitnessValidationResult:
	"""Replay the hidden witness and evaluate both formulae on its PDDL states."""

	raw_actions = audit_row.get("witness_actions")
	if not isinstance(raw_actions, Sequence) or isinstance(raw_actions, (str, bytes)):
		raise TemporalGoalValidationError("construction audit has no witness_actions array.")
	replay = replay_ground_action_trace(
		domain_file=domain_file,
		problem_file=problem_file,
		action_lines=tuple(str(item) for item in raw_actions),
	)
	expected_fingerprints = tuple(str(item) for item in audit_row.get("state_fingerprints") or ())
	actual_fingerprints = tuple(state.fingerprint() for state in replay.states)
	fingerprints_match = actual_fingerprints == expected_fingerprints
	if not fingerprints_match:
		raise TemporalGoalValidationError(
			"Replayed witness state fingerprints differ from the sealed construction audit.",
		)
	gold_formula, prediction_formula, alphabet = _canonical_formula_pair(
		audit_row=audit_row,
		prediction=prediction,
	)
	assignment_raw = audit_row.get("assignment")
	if not isinstance(assignment_raw, Mapping):
		raise TemporalGoalValidationError("construction audit has no assignment object.")
	assignment = {str(key): str(value) for key, value in assignment_raw.items()}
	semantic_keys = _semantic_keys_by_canonical_symbol(
		audit_row=audit_row,
		prediction=prediction,
	)
	valuations = tuple(
		_state_valuation(
			state,
			alphabet=alphabet,
			semantic_keys=semantic_keys,
			assignment=assignment,
		)
		for state in replay.states
	)
	gold_accepted = _compile_dfa(gold_formula).accepts(valuations)
	prediction_accepted = _compile_dfa(prediction_formula).accepts(valuations)
	return WitnessValidationResult(
		replay_valid=True,
		state_fingerprints_match=True,
		gold_accepted=gold_accepted,
		prediction_accepted=prediction_accepted,
		action_count=len(replay.actions),
		state_count=len(replay.states),
	)


def rewrite_problem_with_neutral_goal(
	problem_file: str | Path,
	output_file: str | Path,
) -> Path:
	"""Copy a PDDL problem while replacing only its original goal with true."""

	source = Path(problem_file)
	text = source.read_text(encoding="utf-8")
	matches = list(re.finditer(r"\(\s*:goal\b", text, flags=re.IGNORECASE))
	if len(matches) != 1:
		raise TemporalGoalValidationError(
			f"Expected exactly one :goal block in {source}; found {len(matches)}.",
		)
	start = matches[0].start()
	end = _matching_parenthesis(text, start)
	rewritten = text[:start] + "(:goal (and))" + text[end + 1 :]
	output = Path(output_file)
	output.parent.mkdir(parents=True, exist_ok=True)
	output.write_text(rewritten, encoding="utf-8")
	return output


def validate_execution_trace(
	*,
	audit_row: Mapping[str, Any],
	prediction: ValidatedLTLfPrediction,
	domain_file: str | Path,
	problem_file: str | Path,
	plan_file: str | Path,
	output_dir: str | Path,
	plan_verifier_command: Sequence[str] | str | None = None,
	plan_verifier_timeout_seconds: int = 1800,
) -> ExecutionTraceValidationResult:
	"""Validate one generated trace with PDDL replay, VAL, and both temporal DFAs."""

	plan_path = Path(plan_file)
	action_lines = tuple(
		line.strip()
		for line in plan_path.read_text(encoding="utf-8").splitlines()
		if line.strip() and not line.lstrip().startswith(";")
	)
	if not action_lines:
		raise TemporalGoalValidationError(f"Execution trace is empty: {plan_path}.")
	replay = replay_ground_action_trace(
		domain_file=domain_file,
		problem_file=problem_file,
		action_lines=action_lines,
	)
	output = Path(output_dir)
	neutral_problem = rewrite_problem_with_neutral_goal(
		problem_file,
		output / "neutral_goal_problem.pddl",
	)
	verifier = run_external_plan_verifier(
		domain_file=domain_file,
		problem_file=neutral_problem,
		plan_file=plan_path,
		output_dir=output,
		command=plan_verifier_command,
		timeout_seconds=plan_verifier_timeout_seconds,
	)
	gold_formula, prediction_formula, alphabet = _canonical_formula_pair(
		audit_row=audit_row,
		prediction=prediction,
	)
	assignment_raw = audit_row.get("assignment")
	if not isinstance(assignment_raw, Mapping):
		raise TemporalGoalValidationError("construction audit has no assignment object.")
	assignment = {str(key): str(value) for key, value in assignment_raw.items()}
	semantic_keys = _semantic_keys_by_canonical_symbol(
		audit_row=audit_row,
		prediction=prediction,
	)
	valuations = tuple(
		_state_valuation(
			state,
			alphabet=alphabet,
			semantic_keys=semantic_keys,
			assignment=assignment,
		)
		for state in replay.states
	)
	return ExecutionTraceValidationResult(
		replay_valid=True,
		val_attempted=verifier.attempted,
		val_success=verifier.success,
		gold_accepted=_compile_dfa(gold_formula).accepts(valuations),
		prediction_accepted=_compile_dfa(prediction_formula).accepts(valuations),
		action_count=len(replay.actions),
		state_count=len(replay.states),
		neutral_problem_file=str(neutral_problem),
		plan_verifier_error=verifier.error,
	)


def _canonical_formula_pair(
	*,
	audit_row: Mapping[str, Any],
	prediction: ValidatedLTLfPrediction,
) -> tuple[str, str, tuple[str, ...]]:
	gold_by_id = _gold_atoms_by_id(audit_row)
	prediction_by_id = {
		atom.symbol: atom.semantic_key for atom in prediction.atoms
	}
	all_keys = sorted(
		set(gold_by_id.values()) | set(prediction_by_id.values()),
		key=_semantic_key_sort_key,
	)
	canonical_by_key = {key: f"v{index}" for index, key in enumerate(all_keys)}
	gold_symbols = {symbol: canonical_by_key[key] for symbol, key in gold_by_id.items()}
	prediction_symbols = {
		symbol: canonical_by_key[key] for symbol, key in prediction_by_id.items()
	}
	formula_ast = audit_row.get("gold_formula_ast")
	if not isinstance(formula_ast, Mapping):
		raise TemporalGoalValidationError("construction audit has no gold_formula_ast object.")
	gold_formula = _render_formula_ast(formula_ast, gold_symbols)
	prediction_formula = _rewrite_formula_symbols(
		prediction.ltlf_formula,
		prediction_symbols,
	)
	return gold_formula, prediction_formula, tuple(canonical_by_key[key] for key in all_keys)


def _semantic_keys_by_canonical_symbol(
	*,
	audit_row: Mapping[str, Any],
	prediction: ValidatedLTLfPrediction,
) -> dict[str, SemanticAtomKey]:
	gold_keys = set(_gold_atoms_by_id(audit_row).values())
	prediction_keys = {atom.semantic_key for atom in prediction.atoms}
	all_keys = sorted(gold_keys | prediction_keys, key=_semantic_key_sort_key)
	return {f"v{index}": key for index, key in enumerate(all_keys)}


def _gold_atoms_by_id(audit_row: Mapping[str, Any]) -> dict[str, SemanticAtomKey]:
	raw_atoms = audit_row.get("gold_atoms")
	if not isinstance(raw_atoms, Sequence) or isinstance(raw_atoms, (str, bytes)):
		raise TemporalGoalValidationError("construction audit has no gold_atoms array.")
	result: dict[str, SemanticAtomKey] = {}
	for index, raw_atom in enumerate(raw_atoms):
		if not isinstance(raw_atom, Mapping):
			raise TemporalGoalValidationError(f"gold_atoms[{index}] is not an object.")
		atom_id = str(raw_atom.get("atom_id") or "").strip()
		kind = str(raw_atom.get("kind") or "").strip()
		name_field = "predicate" if kind == "predicate" else "function"
		name = str(raw_atom.get(name_field) or "").strip()
		arguments = tuple(str(item) for item in raw_atom.get("arguments") or ())
		value_raw = raw_atom.get("value")
		value = int(value_raw) if kind == "numeric_equality" else None
		if not atom_id or kind not in {"predicate", "numeric_equality"} or not name:
			raise TemporalGoalValidationError(f"gold_atoms[{index}] is malformed.")
		result[atom_id] = (kind, name, arguments, value)
	return result


def _render_formula_ast(node: Mapping[str, Any], symbols: Mapping[str, str]) -> str:
	operator = str(node.get("operator") or "")
	if operator == "atom":
		atom_id = str(node.get("atom_id") or "")
		if atom_id not in symbols:
			raise TemporalGoalValidationError(f"Gold formula references unknown atom {atom_id!r}.")
		return symbols[atom_id]
	if operator == "not":
		return f"!({_render_formula_ast(_formula_node(node.get('operand')), symbols)})"
	if operator == "and":
		operands = node.get("operands")
		if not isinstance(operands, Sequence) or isinstance(operands, (str, bytes)):
			raise TemporalGoalValidationError("Gold and node requires operands.")
		return "(" + " & ".join(
			_render_formula_ast(_formula_node(item), symbols) for item in operands
		) + ")"
	if operator == "next":
		return f"X({_render_formula_ast(_formula_node(node.get('operand')), symbols)})"
	if operator == "eventually":
		return f"F({_render_formula_ast(_formula_node(node.get('operand')), symbols)})"
	if operator == "until":
		left = _render_formula_ast(_formula_node(node.get("left")), symbols)
		right = _render_formula_ast(_formula_node(node.get("right")), symbols)
		return f"({left}) U ({right})"
	raise TemporalGoalValidationError(f"Unsupported gold formula operator {operator!r}.")


def _rewrite_formula_symbols(formula: str, symbols: Mapping[str, str]) -> str:
	def replace(match: re.Match[str]) -> str:
		symbol = match.group(0)
		if symbol not in symbols:
			raise TemporalGoalValidationError(
				f"Prediction formula references atom absent from its atom table: {symbol}.",
			)
		return symbols[symbol]

	return re.sub(r"\ba\d+\b", replace, formula)


@lru_cache(maxsize=4096)
def _compile_dfa(formula: str) -> _CompiledDFA:
	_, metadata = LTLfToDFA().convert(formula)
	initial_state = str(metadata.get("initial_state") or "").strip()
	accepting_states = frozenset(str(item) for item in metadata.get("accepting_states") or ())
	free_variables = tuple(str(item) for item in metadata.get("free_variables") or ())
	transitions: list[_GuardTransition] = []
	for record in metadata.get("guarded_transitions") or ():
		if not isinstance(record, Mapping):
			raise TemporalGoalValidationError("DFA transition record is not an object.")
		for raw_cube in record.get("guards") or ():
			cube = str(raw_cube).strip()
			if not re.fullmatch(r"[01X]+", cube) or len(cube) != len(free_variables):
				raise TemporalGoalValidationError(f"Unsupported DFA guard cube {cube!r}.")
			transitions.append(
				_GuardTransition(
					source_state=str(record.get("source_state") or ""),
					target_state=str(record.get("target_state") or ""),
					cube=cube,
				),
			)
	if not transitions and not accepting_states:
		free_variables = tuple(dict.fromkeys(re.findall(r"\bv\d+\b", formula)))
		return _CompiledDFA(
			initial_state="__reject__",
			accepting_states=frozenset(),
			free_variables=free_variables,
			transitions=(
				_GuardTransition(
					source_state="__reject__",
					target_state="__reject__",
					cube="X" * len(free_variables),
				),
			),
			state_count=1,
		)
	if not initial_state or not transitions:
		raise TemporalGoalValidationError("DFA conversion returned no executable transition relation.")
	return _CompiledDFA(
		initial_state=initial_state,
		accepting_states=accepting_states,
		free_variables=free_variables,
		transitions=tuple(transitions),
		state_count=int(metadata.get("num_states") or 0),
	)


def _cube_matches(
	cube: str,
	*,
	free_variables: Sequence[str],
	valuation: Mapping[str, bool],
) -> bool:
	return all(
		value == "X" or (value == "1") == bool(valuation.get(symbol, False))
		for symbol, value in zip(free_variables, cube)
	)


def _all_valuations(alphabet: Sequence[str]):
	for values in itertools.product((False, True), repeat=len(alphabet)):
		yield dict(zip(alphabet, values))


def _inequivalent_result(
	gold_formula: str,
	prediction_formula: str,
	gold_dfa: _CompiledDFA,
	prediction_dfa: _CompiledDFA,
	trace: tuple[Mapping[str, bool], ...],
	*,
	explored_count: int,
) -> DFAEquivalenceResult:
	return DFAEquivalenceResult(
		equivalent=False,
		gold_formula=gold_formula,
		prediction_formula=prediction_formula,
		gold_state_count=gold_dfa.state_count,
		prediction_state_count=prediction_dfa.state_count,
		explored_product_state_count=explored_count,
		counterexample_trace=trace,
		gold_accepts_counterexample=gold_dfa.accepts(trace),
		prediction_accepts_counterexample=prediction_dfa.accepts(trace),
	)


def _state_valuation(
	state: GroundState,
	*,
	alphabet: Sequence[str],
	semantic_keys: Mapping[str, SemanticAtomKey],
	assignment: Mapping[str, str],
) -> dict[str, bool]:
	valuation: dict[str, bool] = {}
	for symbol in alphabet:
		kind, name, arguments, value = semantic_keys[symbol]
		ground_arguments = tuple(assignment.get(argument, argument).lower() for argument in arguments)
		if kind == "predicate":
			valuation[symbol] = GroundAtom(name, ground_arguments) in state.facts
		else:
			valuation[symbol] = state.numeric.get(NumericKey(name, ground_arguments)) == value
	return valuation


def _semantic_key_sort_key(key: SemanticAtomKey) -> str:
	return json.dumps(key, ensure_ascii=False, separators=(",", ":"))


def _formula_node(value: object) -> Mapping[str, Any]:
	if not isinstance(value, Mapping):
		raise TemporalGoalValidationError(f"Expected formula node, received {value!r}.")
	return value


def _matching_parenthesis(text: str, start: int) -> int:
	depth = 0
	for index in range(start, len(text)):
		if text[index] == "(":
			depth += 1
		elif text[index] == ")":
			depth -= 1
			if depth == 0:
				return index
	raise TemporalGoalValidationError("Unbalanced PDDL problem while replacing :goal.")


def _required_text(payload: Mapping[str, Any], field: str, *, label: str) -> str:
	value = str(payload.get(field) or "").strip()
	if not value:
		raise ValueError(f"{label} has empty {field}.")
	return value
