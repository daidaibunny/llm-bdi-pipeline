"""
Command-line entry point for DFA-driven BDI plan-library generation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_src_dir = str(Path(__file__).parent)
if _src_dir not in sys.path:
	sys.path.insert(0, _src_dir)

from plan_library import PlanLibraryGenerationPipeline


def _absolute_path(path_text: str | None) -> str | None:
	if not path_text:
		return None
	return str(Path(path_text).expanduser().resolve())


def _require_existing_path(path_text: str | None, *, label: str) -> str:
	resolved_path = _absolute_path(path_text)
	if not resolved_path or not Path(resolved_path).exists():
		print("=" * 80)
		print(f"ERROR: {label} Not Found")
		print("=" * 80)
		print(f"\nProvided path does not exist:\n{resolved_path}")
		sys.exit(1)
	return resolved_path


def build_argument_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		description=(
			"Generate DFA-driven high-level AgentSpeak(L) plan libraries from PDDL "
			"domains and stored LTLf task specifications."
		),
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog="""
Examples:
  python src/main.py generate-library --domain-file ./src/domains/blocksworld/domain.pddl --query-id query_1
  python src/main.py generate-library --domain-file ./src/domains/transport/domain.pddl --query-domain transport --output-root ./artifacts/plan_library/transport/query_1
		""",
	)
	subparsers = parser.add_subparsers(dest="command")

	generate_parser = subparsers.add_parser(
		"generate-library",
		help="Generate a DFA-driven high-level AgentSpeak(L) plan library.",
	)
	generate_parser.add_argument("--domain-file", required=True, help="Path to the PDDL domain file.")
	generate_parser.add_argument(
		"--query-dataset",
		help="Optional path to a stored temporal-specification dataset. Defaults to queries_LTLf.json.",
	)
	generate_parser.add_argument(
		"--query-domain",
		help="Optional explicit dataset domain key. Otherwise inferred from the domain file.",
	)
	generate_parser.add_argument(
		"--query-id",
		action="append",
		help=(
			"Stored benchmark query identifier to include in generation. "
			"Repeat to generate from multiple selected queries. Defaults to all domain queries."
		),
	)
	generate_parser.add_argument(
		"--output-root",
		help="Optional explicit output root for the persisted plan-library artifact bundle.",
	)
	generate_parser.add_argument(
		"--fast-downward",
		help=(
			"Optional path to the Fast Downward driver. If omitted, FAST_DOWNWARD "
			"or PATH is used."
		),
	)
	generate_parser.add_argument(
		"--disable-low-level-planning",
		action="store_true",
		help=(
			"Disable Fast Downward for diagnostics. Context-driven generation requires "
			"primitive low-level actions for progress plans."
		),
	)
	generate_parser.add_argument(
		"--render-primitive-actions",
		action="store_true",
		default=True,
		help="Deprecated compatibility flag; primitive ASL actions are rendered by default.",
	)
	return parser


def main() -> None:
	parser = build_argument_parser()
	args = parser.parse_args()
	if not args.command:
		parser.print_help()
		sys.exit(2)

	if args.command == "generate-library":
		domain_file = _require_existing_path(args.domain_file, label="Domain File")
		pipeline = PlanLibraryGenerationPipeline(
			domain_file=domain_file,
			query_dataset=_absolute_path(args.query_dataset),
			query_domain=args.query_domain,
			query_ids=tuple(args.query_id or ()),
			fast_downward_executable=args.fast_downward,
			enable_low_level_planning=not args.disable_low_level_planning,
			render_primitive_actions=True,
		)
		results = pipeline.build_library_bundle(output_root=_absolute_path(args.output_root))
	else:
		parser.error(f"Unsupported command {args.command!r}")
		return

	print(json.dumps(results, indent=2, default=str))
	sys.exit(0 if results.get("success", False) else 1)


if __name__ == "__main__":
	main()
