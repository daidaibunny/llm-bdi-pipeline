#!/usr/bin/env python3
"""Generate the stored LTLf goal-specification dataset from NL benchmark queries.

PDDL-based replacement for the removed HDDL dataset generator. For each selected
domain and query, the natural-language instruction in ``benchmark_queries.json`` is
converted to one predicate-grounded LTLf formula by the NL-to-LTLf generator, and
the result is written to ``queries_LTLf.json`` using the existing dataset schema.

The generator is injectable (``generator_factory``) so tests can run fully offline
with a fake language-model client.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from temporal_specification import NLToLTLfGenerator  # noqa: E402
from utils.pddl_parser import PDDLParser  # noqa: E402

DEFAULT_SOURCE = PROJECT_ROOT / "src" / "benchmark_data" / "benchmark_queries.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "src" / "benchmark_data" / "queries_LTLf.json"
DEFAULT_DOMAINS_ROOT = PROJECT_ROOT / "src" / "domains"

GeneratorFactory = Callable[..., Any]


def _resolve_domain_file(domain_key: str, *, domains_root: Path) -> Path:
	domain_file = domains_root / domain_key / "domain.pddl"
	if not domain_file.exists():
		raise FileNotFoundError(
			f"Missing PDDL domain for {domain_key!r}: {domain_file}",
		)
	return domain_file


def generate_ltlf_dataset(
	*,
	source: str | Path | None = None,
	output: str | Path | None = None,
	domains_root: str | Path | None = None,
	query_domains: Sequence[str] | None = None,
	query_ids: Sequence[str] | None = None,
	regenerate_existing: bool = False,
	generator_factory: GeneratorFactory = NLToLTLfGenerator,
	generator_kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
	"""Build a stored LTLf dataset from natural-language benchmark queries."""

	source_path = Path(source or DEFAULT_SOURCE).expanduser().resolve()
	output_path = Path(output or DEFAULT_OUTPUT).expanduser().resolve()
	root = Path(domains_root or DEFAULT_DOMAINS_ROOT).expanduser().resolve()
	source_payload = json.loads(source_path.read_text(encoding="utf-8"))

	existing_payload: Dict[str, Any] = {}
	if output_path.exists():
		existing_payload = json.loads(output_path.read_text(encoding="utf-8"))
	existing_domains = (existing_payload.get("domains") or {}) if not regenerate_existing else {}

	selected_domains = tuple(query_domains or ()) or tuple((source_payload.get("domains") or {}).keys())
	selected_ids = {str(value).strip() for value in (query_ids or ()) if str(value).strip()}

	output_domains: Dict[str, Any] = {}
	report: Dict[str, Any] = {"generated": 0, "reused": 0, "domains": {}}
	for domain_key in selected_domains:
		domain_cases = ((source_payload.get("domains") or {}).get(domain_key) or {}).get("cases") or {}
		if not domain_cases:
			raise ValueError(f"No source query cases for domain {domain_key!r} in {source_path}")
		domain_file = _resolve_domain_file(domain_key, domains_root=root)
		domain = PDDLParser.parse_domain(domain_file)
		generator = generator_factory(**(generator_kwargs or {}))
		existing_cases = ((existing_domains.get(domain_key) or {}).get("cases") or {})

		generated_cases: Dict[str, Any] = {}
		domain_generated = 0
		domain_reused = 0
		for query_id, case in domain_cases.items():
			if selected_ids and query_id not in selected_ids:
				continue
			instruction = str(case.get("instruction") or case.get("source_text") or "").strip()
			problem_file = case.get("problem_file")
			prior = existing_cases.get(query_id)
			if not regenerate_existing and prior and str(prior.get("ltlf_formula") or "").strip():
				generated_cases[query_id] = dict(prior)
				domain_reused += 1
				continue
			record = generator.generate(
				domain=domain,
				instruction=instruction,
				instruction_id=query_id,
				problem_file=problem_file,
			)
			generated_cases[query_id] = {
				"instruction": instruction,
				"problem_file": problem_file,
				"ltlf_formula": record.ltlf_formula,
				"atoms": [
					_event_atom_text(event)
					for event in record.referenced_events
				],
				"atom_vocabulary": "pddl_fluents",
			}
			domain_generated += 1
		output_domains[domain_key] = {"cases": generated_cases}
		report["domains"][domain_key] = {
			"generated": domain_generated,
			"reused": domain_reused,
			"case_count": len(generated_cases),
		}
		report["generated"] += domain_generated
		report["reused"] += domain_reused

	output_payload = {
		"version": 1,
		"dataset_kind": "stored_benchmark_ltlf_queries",
		"query_protocol_document": "docs/query_protocol.md",
		"atom_vocabulary": "pddl_fluents",
		"domains": output_domains,
	}
	output_path.parent.mkdir(parents=True, exist_ok=True)
	output_path.write_text(json.dumps(output_payload, indent=2) + "\n", encoding="utf-8")
	report["output"] = str(output_path)
	return report


def _event_atom_text(event: Any) -> str:
	name = str(getattr(event, "event", "") or "").strip()
	arguments = tuple(getattr(event, "arguments", ()) or ())
	if not arguments:
		return name
	return f"{name}({', '.join(str(arg) for arg in arguments)})"


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="NL benchmark query dataset.")
	parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output LTLf dataset path.")
	parser.add_argument("--domains-root", type=Path, default=DEFAULT_DOMAINS_ROOT)
	parser.add_argument(
		"--query-domain",
		action="append",
		default=[],
		help="Domain key to generate. Repeat for multiple; defaults to all source domains.",
	)
	parser.add_argument(
		"--query-id",
		action="append",
		default=[],
		help="Restrict generation to specific query ids.",
	)
	parser.add_argument(
		"--regenerate-existing",
		action="store_true",
		help="Regenerate formulas even when an existing LTLf value is present.",
	)
	args = parser.parse_args()

	report = generate_ltlf_dataset(
		source=args.source,
		output=args.output,
		domains_root=args.domains_root,
		query_domains=args.query_domain or None,
		query_ids=args.query_id or None,
		regenerate_existing=args.regenerate_existing,
	)
	print(json.dumps(report, indent=2))


if __name__ == "__main__":
	main()
