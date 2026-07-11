"""Fail-closed validation for model-generated lifted LTLf payloads."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from typing import Mapping
from typing import Sequence

from ltlf2dfa.parser.ltlf import LTLfParser

from .errors import TranslationErrorCode


_REQUIRED_TOP_LEVEL_KEYS = frozenset(
	{
		"schema_version",
		"sample_id",
		"temporal_logic",
		"ltlf_formula",
		"atoms",
		"declared_parameters",
		"constraints",
		"status",
	},
)
_ATOM_SYMBOL_RE = re.compile(r"a\d+")
_FORMULA_TOKEN_RE = re.compile(r"a\d+|F|X|U|&|!|\(|\)")


class PredictionValidationError(ValueError):
	"""One stable, model-facing validation failure."""

	def __init__(self, code: TranslationErrorCode, message: str) -> None:
		super().__init__(message)
		self.code = TranslationErrorCode(code)


@dataclass(frozen=True)
class ValidatedTemporalAtom:
	"""One catalogue-checked lifted predicate or numeric equality."""

	symbol: str
	kind: str
	name: str
	args: tuple[str, ...]
	value: int | None = None

	@property
	def semantic_key(self) -> tuple[str, str, tuple[str, ...], int | None]:
		return (self.kind, self.name, self.args, self.value)

	def to_dict(self) -> dict[str, object]:
		payload: dict[str, object] = {
			"symbol": self.symbol,
			"kind": self.kind,
			"args": list(self.args),
		}
		payload["predicate" if self.kind == "predicate" else "function"] = self.name
		if self.kind == "numeric_equality":
			payload["value"] = self.value
		return payload


@dataclass(frozen=True)
class ValidatedLTLfPrediction:
	"""Normalized prediction that passed the public Input contract."""

	sample_id: str
	ltlf_formula: str
	atoms: tuple[ValidatedTemporalAtom, ...]
	declared_parameters: tuple[tuple[str, str], ...]
	constraints: tuple[str, ...]

	@property
	def atom_by_symbol(self) -> dict[str, ValidatedTemporalAtom]:
		return {atom.symbol: atom for atom in self.atoms}

	def to_payload(self) -> dict[str, object]:
		return {
			"schema_version": 1,
			"sample_id": self.sample_id,
			"temporal_logic": "LTLf",
			"ltlf_formula": self.ltlf_formula,
			"atoms": [atom.to_dict() for atom in self.atoms],
			"declared_parameters": [
				{"name": name, "pddl_type": pddl_type}
				for name, pddl_type in self.declared_parameters
			],
			"constraints": [json.loads(item) for item in self.constraints],
			"status": "supported",
		}


def validate_prediction_payload(
	payload: Mapping[str, Any],
	*,
	expected_sample: Mapping[str, Any],
	catalog: Mapping[str, Any],
) -> ValidatedLTLfPrediction:
	"""Validate one model response without repairing or inferring missing data."""

	if not isinstance(payload, Mapping):
		_fail(TranslationErrorCode.E_JSON_FORMAT, "Prediction must be a JSON object.")
	actual_keys = frozenset(str(key) for key in payload)
	if actual_keys != _REQUIRED_TOP_LEVEL_KEYS:
		_fail(
			TranslationErrorCode.E_JSON_FORMAT,
			"Prediction must contain exactly the eight required top-level keys; "
			f"missing={sorted(_REQUIRED_TOP_LEVEL_KEYS - actual_keys)}, "
			f"extra={sorted(actual_keys - _REQUIRED_TOP_LEVEL_KEYS)}.",
		)
	if payload.get("schema_version") != 1:
		_fail(TranslationErrorCode.E_JSON_FORMAT, "schema_version must be integer 1.")
	if payload.get("temporal_logic") != "LTLf":
		_fail(TranslationErrorCode.E_JSON_FORMAT, "temporal_logic must be LTLf.")
	if payload.get("status") != "supported":
		_fail(TranslationErrorCode.E_JSON_FORMAT, "status must be supported.")

	expected_sample_id = _required_text(expected_sample, "sample_id")
	sample_id = _required_text(payload, "sample_id")
	if sample_id != expected_sample_id:
		_fail(
			TranslationErrorCode.E_JSON_FORMAT,
			f"sample_id must remain {expected_sample_id!r}; received {sample_id!r}.",
		)

	expected_parameters = _json_array(expected_sample, "declared_parameters")
	declared_parameters = _json_array(payload, "declared_parameters")
	if declared_parameters != expected_parameters:
		_fail(
			TranslationErrorCode.E_DECLARED_PARAMETER_MISMATCH,
			"declared_parameters must be copied exactly from the input row.",
		)
	expected_constraints = _json_array(expected_sample, "constraints")
	constraints = _json_array(payload, "constraints")
	if constraints != expected_constraints:
		_fail(
			TranslationErrorCode.E_CONSTRAINT_MISMATCH,
			"constraints must be copied exactly from the input row.",
		)
	parameter_types = _parameter_types(declared_parameters)

	formula = _required_text(payload, "ltlf_formula")
	_validate_formula_syntax(formula)
	raw_atoms = _json_array(payload, "atoms")
	used_symbols = _first_use_atom_symbols(formula)
	expected_symbols = tuple(f"a{index}" for index in range(len(raw_atoms)))
	declared_symbols = tuple(
		str(atom.get("symbol") or "").strip()
		if isinstance(atom, Mapping)
		else ""
		for atom in raw_atoms
	)
	if declared_symbols != expected_symbols or used_symbols != declared_symbols:
		_fail(
			TranslationErrorCode.E_FORMULA_ATOM_MISMATCH,
			"Atom entries must be a0, a1, ... in first-formula-occurrence order, "
			"with no missing or unused entries.",
		)

	predicates = _catalog_signatures(catalog, "predicates")
	functions = _catalog_signatures(catalog, "numeric_functions")
	constants = _catalog_constants(catalog)
	type_parents = _type_parents(catalog)
	atoms = tuple(
		_validate_atom(
			raw_atom,
			index=index,
			parameter_types=parameter_types,
			constants=constants,
			predicates=predicates,
			functions=functions,
			type_parents=type_parents,
		)
		for index, raw_atom in enumerate(raw_atoms)
	)
	if len({atom.semantic_key for atom in atoms}) != len(atoms):
		_fail(
			TranslationErrorCode.E_FORMULA_ATOM_MISMATCH,
			"The atom table must not define the same lifted semantic atom twice.",
		)
	used_parameters = {argument for atom in atoms for argument in atom.args if argument in parameter_types}
	if used_parameters != set(parameter_types):
		_fail(
			TranslationErrorCode.E_DECLARED_PARAMETER_MISMATCH,
			"Every declared parameter must occur in at least one atom and no parameter may be invented.",
		)

	return ValidatedLTLfPrediction(
		sample_id=sample_id,
		ltlf_formula=formula,
		atoms=atoms,
		declared_parameters=tuple(parameter_types.items()),
		constraints=tuple(_canonical_json(item) for item in constraints),
	)


def _validate_formula_syntax(formula: str) -> None:
	residual = _FORMULA_TOKEN_RE.sub("", formula)
	if residual.strip():
		_fail(
			TranslationErrorCode.E_UNSUPPORTED_OPERATOR,
			"Formula contains a symbol or operator outside a<number>, F, X, U, &, and !.",
		)
	try:
		LTLfParser()(formula)
	except Exception as error:  # noqa: BLE001 - normalized into a stable model error.
		_fail(TranslationErrorCode.E_LTLF_SYNTAX, f"Invalid LTLf syntax: {error}")


def _validate_atom(
	raw_atom: object,
	*,
	index: int,
	parameter_types: Mapping[str, str],
	constants: Mapping[str, str],
	predicates: Mapping[str, tuple[str, ...]],
	functions: Mapping[str, tuple[str, ...]],
	type_parents: Mapping[str, str],
) -> ValidatedTemporalAtom:
	if not isinstance(raw_atom, Mapping):
		_fail(TranslationErrorCode.E_ATOM_KIND, f"atoms[{index}] must be a JSON object.")
	kind = str(raw_atom.get("kind") or "").strip()
	symbol = str(raw_atom.get("symbol") or "").strip()
	if kind == "predicate":
		required_keys = {"symbol", "kind", "predicate", "args"}
		name_field = "predicate"
		signatures = predicates
		value = None
	elif kind == "numeric_equality":
		required_keys = {"symbol", "kind", "function", "args", "value"}
		name_field = "function"
		signatures = functions
		raw_value = raw_atom.get("value")
		if isinstance(raw_value, bool) or not isinstance(raw_value, int):
			_fail(
				TranslationErrorCode.E_ATOM_KIND,
				f"atoms[{index}].value must be an integer.",
			)
		value = int(raw_value)
	else:
		_fail(
			TranslationErrorCode.E_ATOM_KIND,
			f"atoms[{index}].kind must be predicate or numeric_equality.",
		)
	actual_keys = {str(key) for key in raw_atom}
	if actual_keys != required_keys:
		_fail(
			TranslationErrorCode.E_ATOM_KIND,
			f"atoms[{index}] has wrong fields for kind {kind!r}.",
		)
	name = str(raw_atom.get(name_field) or "").strip()
	if name not in signatures:
		_fail(
			TranslationErrorCode.E_UNKNOWN_SYMBOL,
			f"atoms[{index}] references undeclared {name_field} {name!r}.",
		)
	args = _json_array(raw_atom, "args")
	if not all(isinstance(argument, str) and argument.strip() for argument in args):
		_fail(TranslationErrorCode.E_UNKNOWN_SYMBOL, f"atoms[{index}].args must contain strings.")
	arguments = tuple(str(argument).strip() for argument in args)
	expected_types = signatures[name]
	if len(arguments) != len(expected_types):
		_fail(
			TranslationErrorCode.E_ARITY_MISMATCH,
			f"{name} expects {len(expected_types)} arguments; received {len(arguments)}.",
		)
	for position, (argument, expected_type) in enumerate(zip(arguments, expected_types)):
		actual_type = parameter_types.get(argument) or constants.get(argument)
		if actual_type is None:
			_fail(
				TranslationErrorCode.E_UNKNOWN_SYMBOL,
				f"Argument {argument!r} is neither a declared parameter nor a domain constant.",
			)
		if not _is_subtype(actual_type, expected_type, type_parents):
			_fail(
				TranslationErrorCode.E_TYPE_MISMATCH,
				f"Argument {position} of {name} requires {expected_type}; {argument} has {actual_type}.",
			)
	return ValidatedTemporalAtom(symbol=symbol, kind=kind, name=name, args=arguments, value=value)


def _parameter_types(raw_parameters: Sequence[object]) -> dict[str, str]:
	result: dict[str, str] = {}
	for index, item in enumerate(raw_parameters):
		if not isinstance(item, Mapping) or set(item) != {"name", "pddl_type"}:
			_fail(
				TranslationErrorCode.E_DECLARED_PARAMETER_MISMATCH,
				f"declared_parameters[{index}] must contain exactly name and pddl_type.",
			)
		name = str(item.get("name") or "").strip()
		pddl_type = str(item.get("pddl_type") or "").strip()
		if not name or not pddl_type or name in result:
			_fail(
				TranslationErrorCode.E_DECLARED_PARAMETER_MISMATCH,
				"Declared parameter names and types must be non-empty and unique.",
			)
		result[name] = pddl_type
	return result


def _catalog_signatures(catalog: Mapping[str, Any], field: str) -> dict[str, tuple[str, ...]]:
	result: dict[str, tuple[str, ...]] = {}
	for item in _json_array(catalog, field):
		if not isinstance(item, Mapping):
			continue
		name = str(item.get("name") or "").strip()
		argument_types = item.get("argument_types")
		if name and isinstance(argument_types, Sequence) and not isinstance(argument_types, (str, bytes)):
			result[name] = tuple(str(value).strip() for value in argument_types)
	return result


def _catalog_constants(catalog: Mapping[str, Any]) -> dict[str, str]:
	result: dict[str, str] = {}
	for item in _json_array(catalog, "constants"):
		if isinstance(item, Mapping):
			name = str(item.get("name") or "").strip()
			pddl_type = str(item.get("pddl_type") or "object").strip()
			if name:
				result[name] = pddl_type
	return result


def _type_parents(catalog: Mapping[str, Any]) -> dict[str, str]:
	raw = catalog.get("type_parents")
	if not isinstance(raw, Mapping):
		return {}
	return {str(child): str(parent) for child, parent in raw.items()}


def _is_subtype(actual: str, expected: str, type_parents: Mapping[str, str]) -> bool:
	current = actual
	seen: set[str] = set()
	while current not in seen:
		if current == expected or expected == "object":
			return True
		seen.add(current)
		current = str(type_parents.get(current) or "")
		if not current:
			break
	return False


def _first_use_atom_symbols(formula: str) -> tuple[str, ...]:
	return tuple(dict.fromkeys(_ATOM_SYMBOL_RE.findall(formula)))


def _json_array(payload: Mapping[str, Any], field: str) -> list[Any]:
	value = payload.get(field)
	if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
		_fail(TranslationErrorCode.E_JSON_FORMAT, f"{field} must be a JSON array.")
	return list(value)


def _required_text(payload: Mapping[str, Any], field: str) -> str:
	value = str(payload.get(field) or "").strip()
	if not value:
		_fail(TranslationErrorCode.E_JSON_FORMAT, f"{field} must be a non-empty string.")
	return value


def _canonical_json(value: object) -> str:
	return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _fail(code: TranslationErrorCode, message: str) -> None:
	raise PredictionValidationError(code, message)
