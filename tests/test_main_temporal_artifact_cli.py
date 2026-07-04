from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_main_compiles_moose_atomic_library(tmp_path: Path) -> None:
	policy_file = tmp_path / "ferry-seed0.model.readable"
	library_root = tmp_path / "domain_libraries"
	policy_file.write_text(
		"""
		precedence : (1, 1, 0, 0)
		      vars : car0 location0
		    s_cond : (at-ferry location0) (on car0)
		    g_cond : (at car0 location0)
		   actions : (debark car0 location0)
		""",
		encoding="utf-8",
	)

	completed = subprocess.run(
		[
			sys.executable,
			str(PROJECT_ROOT / "src" / "main.py"),
			"compile-moose-atomic-library",
			"--policy-file",
			str(policy_file),
			"--domain-name",
			"ferry",
			"--library-root",
			str(library_root),
		],
		cwd=PROJECT_ROOT,
		check=True,
		capture_output=True,
		text=True,
	)
	result = json.loads(completed.stdout)
	asl = Path(result["artifact_paths"]["plan_library_asl"]).read_text(encoding="utf-8")
	metadata = json.loads(
		Path(result["artifact_paths"]["artifact_metadata"]).read_text(encoding="utf-8"),
	)

	assert result["success"] is True
	assert result["plan_count"] == 1
	assert Path(result["artifact_paths"]["plan_library_asl"]).parent == library_root / "ferry"
	assert metadata["canonical_domain_library"] is True
	assert "+!at(Car0, Location0)" in asl
	assert "achieve_" not in asl
	assert "transition_" not in asl
	assert "dfa_state" not in asl


def test_main_compiles_moose_seeded_minimal_module_library(tmp_path: Path) -> None:
	policy_file = tmp_path / "blocks-seed0.model.readable"
	library_root = tmp_path / "domain_libraries"
	policy_file.write_text(
		"""
		precedence : (1, 1, 0, 0)
		      vars : block0 block1
		    s_cond : (clear block0) (ontable block0) (handempty) (clear block1)
		    g_cond : (on block0 block1)
		   actions : (pick-up block0) (stack block0 block1)
		""",
		encoding="utf-8",
	)

	completed = subprocess.run(
		[
			sys.executable,
			str(PROJECT_ROOT / "src" / "main.py"),
			"compile-moose-atomic-library",
			"--policy-file",
			str(policy_file),
			"--domain-file",
			str(PROJECT_ROOT / "src" / "domains" / "blocks" / "domain.pddl"),
			"--domain-name",
			"blocks",
			"--post-moose-recursive",
			"--library-root",
			str(library_root),
		],
		cwd=PROJECT_ROOT,
		check=True,
		capture_output=True,
		text=True,
	)
	result = json.loads(completed.stdout)
	asl = Path(result["artifact_paths"]["plan_library_asl"]).read_text(encoding="utf-8")
	metadata = json.loads(
		Path(result["artifact_paths"]["artifact_metadata"]).read_text(encoding="utf-8"),
	)

	assert result["success"] is True
	assert result["plan_count"] >= 17
	assert Path(result["artifact_paths"]["plan_library_asl"]).parent == library_root / "blocks"
	assert metadata["artifact_kind"] == "moose_seeded_atomic_minimal_literal_module_library"
	assert metadata["canonical_domain_library"] is True
	assert metadata["minimal_modules"] is True
	assert metadata["post_moose_recursive"] is True
	assert metadata["moose_backend_path"] == "post_moose_recursive_module_synthesis"
	assert "+!on(X, Y) : not clear(X)" in asl
	assert "on(Y, X) & not clear(Y)" in asl
	assert "+!clear(X) : not handempty" in asl
	assert "+!holding(X) : holding(X)" in asl
	assert "type_" not in asl
	assert "block0" not in asl


def test_main_records_nonofficial_source_metadata_for_native_moose_compile(
	tmp_path: Path,
) -> None:
	domain_dir = tmp_path / "sample-domain"
	domain_dir.mkdir()
	domain_file = domain_dir / "domain.pddl"
	domain_file.write_text(
		"""
		(define (domain sample)
		 (:requirements :strips :typing)
		 (:types thing place)
		 (:predicates (at ?x - thing ?y - place))
		 (:action move
		  :parameters (?x - thing ?from ?to - place)
		  :precondition (at ?x ?from)
		  :effect (and (not (at ?x ?from)) (at ?x ?to)))
		)
		""",
		encoding="utf-8",
	)
	(domain_dir / "source.json").write_text(
		json.dumps({"source_id": "external_case_study", "train_count": 2}) + "\n",
		encoding="utf-8",
	)
	policy_file = tmp_path / "sample.model.readable"
	policy_file.write_text(
		"""
		precedence : (1, 1, 0, 0)
		      vars : thing0 place0 place1
		    s_cond : (at thing0 place0)
		    g_cond : (at thing0 place1)
		   actions : (move thing0 place0 place1)
		""",
		encoding="utf-8",
	)
	library_root = tmp_path / "domain_libraries"

	completed = subprocess.run(
		[
			sys.executable,
			str(PROJECT_ROOT / "src" / "main.py"),
			"compile-moose-atomic-library",
			"--policy-file",
			str(policy_file),
			"--domain-file",
			str(domain_file),
			"--domain-name",
			"sample",
			"--library-root",
			str(library_root),
		],
		cwd=PROJECT_ROOT,
		check=True,
		capture_output=True,
		text=True,
	)
	result = json.loads(completed.stdout)
	metadata = json.loads(
		Path(result["artifact_paths"]["artifact_metadata"]).read_text(encoding="utf-8"),
	)

	assert result["success"] is True
	assert metadata["minimal_modules"] is False
	assert metadata["post_moose_recursive"] is False
	assert metadata["moose_backend_path"] == "native_train_dump_policy"
	assert metadata["moose_official_benchmark"] is False
	assert metadata["source_metadata"]["source_id"] == "external_case_study"


def test_main_appends_lifted_temporal_goal_to_existing_library(
	tmp_path: Path,
) -> None:
	domain_file, _ = _write_tiny_domain_and_problem(tmp_path)
	library_root = tmp_path / "domain_libraries"
	_write_atomic_library_json(library_root, domain_name="tiny")
	(library_root / "tiny" / "artifact_metadata.json").write_text(
		json.dumps(
			{
				"artifact_kind": "moose_atomic_library",
				"moose_backend_path": "native_train_dump_policy",
				"moose_official_benchmark": False,
				"source_metadata": {"source_id": "external_case_study"},
			},
		)
		+ "\n",
		encoding="utf-8",
	)
	goal_json = _write_lifted_ltlf_goal_json(tmp_path)

	completed = subprocess.run(
		[
			sys.executable,
			str(PROJECT_ROOT / "src" / "main.py"),
			"append-lifted-temporal-goal",
			"--domain-file",
			str(domain_file),
			"--ltlf-goal-json",
			str(goal_json),
			"--query-id",
			"query_1",
			"--library-root",
			str(library_root),
		],
		cwd=PROJECT_ROOT,
		check=True,
		capture_output=True,
		text=True,
	)
	result = json.loads(completed.stdout)
	asl = Path(result["artifact_paths"]["plan_library_asl"]).read_text(encoding="utf-8")
	metadata = json.loads(
		Path(result["artifact_paths"]["artifact_metadata"]).read_text(encoding="utf-8"),
	)

	assert result["success"] is True
	assert result["appended_query_count"] == 1
	assert Path(result["artifact_paths"]["plan_library_asl"]).parent == library_root / "tiny"
	assert metadata["canonical_domain_library"] is True
	assert metadata["base_artifact_kind"] == "moose_atomic_library"
	assert metadata["moose_backend_path"] == "native_train_dump_policy"
	assert metadata["moose_official_benchmark"] is False
	assert metadata["source_metadata"]["source_id"] == "external_case_study"
	assert metadata["query_ids"] == ["query_1"]
	assert "teg_state" not in asl
	assert "+!g_query_1 : not done <-" in asl
	assert "\t!done;" in asl
	assert "\t!g_query_1." in asl
	assert "achieve_" not in asl
	assert "transition_" not in asl
	assert "dfa_state" not in asl


def test_main_can_append_multiple_queries_to_same_domain_library(
	tmp_path: Path,
) -> None:
	domain_file, _ = _write_tiny_domain_and_problem(tmp_path)
	library_root = tmp_path / "domain_libraries"
	_write_atomic_library_json(library_root, domain_name="tiny")
	goal_json = tmp_path / "lifted_ltlf_goals.json"
	goal_json.write_text(
		json.dumps(
			{
				"schema_version": 1,
				"goal_specification_kind": "temporal_extended_goal",
				"temporal_logic": "LTLf",
				"domain": "tiny",
				"cases": {
					"query_1": {
						"goal_name": "g_query_1",
						"problem_file": "problem.pddl",
						"source_text": "Eventually finish.",
						"ltlf_formula": "F(done)",
						"atoms": ["done"],
						"bindings": {},
						"atom_vocabulary": "pddl_fluents",
						"status": "supported",
					},
					"query_2": {
						"goal_name": "g_query_2",
						"problem_file": "problem.pddl",
						"source_text": "Eventually be ready.",
						"ltlf_formula": "F(ready)",
						"atoms": ["ready"],
						"bindings": {},
						"atom_vocabulary": "pddl_fluents",
						"status": "supported",
					},
				},
			},
		),
		encoding="utf-8",
	)

	first = subprocess.run(
		[
			sys.executable,
			str(PROJECT_ROOT / "src" / "main.py"),
			"append-lifted-temporal-goal",
			"--domain-file",
			str(domain_file),
			"--ltlf-goal-json",
			str(goal_json),
			"--query-id",
			"query_1",
			"--library-root",
			str(library_root),
		],
		cwd=PROJECT_ROOT,
		check=True,
		capture_output=True,
		text=True,
	)
	first_result = json.loads(first.stdout)
	assert Path(first_result["artifact_paths"]["plan_library"]).parent == library_root / "tiny"
	second = subprocess.run(
		[
			sys.executable,
			str(PROJECT_ROOT / "src" / "main.py"),
			"append-lifted-temporal-goal",
			"--domain-file",
			str(domain_file),
			"--plan-library-file",
			first_result["artifact_paths"]["plan_library"],
			"--ltlf-goal-json",
			str(goal_json),
			"--query-id",
			"query_2",
			"--library-root",
			str(library_root),
		],
		cwd=PROJECT_ROOT,
		check=True,
		capture_output=True,
		text=True,
	)
	second_result = json.loads(second.stdout)
	library_json = json.loads(
		Path(second_result["artifact_paths"]["plan_library"]).read_text(encoding="utf-8"),
	)
	asl = Path(second_result["artifact_paths"]["plan_library_asl"]).read_text(encoding="utf-8")

	assert "teg_state" not in asl
	assert "+!g_query_1 : not done <-" in asl
	assert "+!g_query_2 : not ready <-" in asl
	assert [
		record["goal_name"]
		for record in library_json["metadata"]["temporal_goal_append_history"]
	] == ["g_query_1", "g_query_2"]
	assert second_result["plan_count"] == 5


def test_main_rejects_noncanonical_output_root(tmp_path: Path) -> None:
	policy_file = tmp_path / "ferry-seed0.model.readable"
	policy_file.write_text(
		"""
		precedence : (1, 1, 0, 0)
		      vars : car0 location0
		    s_cond : (at-ferry location0) (on car0)
		    g_cond : (at car0 location0)
		   actions : (debark car0 location0)
		""",
		encoding="utf-8",
	)

	completed = subprocess.run(
		[
			sys.executable,
			str(PROJECT_ROOT / "src" / "main.py"),
			"compile-moose-atomic-library",
			"--policy-file",
			str(policy_file),
			"--domain-name",
			"ferry",
			"--library-root",
			str(tmp_path / "domain_libraries"),
			"--output-root",
			str(tmp_path / "somewhere_else"),
		],
		cwd=PROJECT_ROOT,
		capture_output=True,
		text=True,
	)

	assert completed.returncode != 0
	assert "noncanonical_domain_library" in completed.stderr


def test_main_uses_benchmark_folder_key_when_pddl_domain_name_differs(
	tmp_path: Path,
) -> None:
	domain_dir = tmp_path / "src" / "domains" / "folder-key"
	domain_dir.mkdir(parents=True)
	domain_file = domain_dir / "domain.pddl"
	domain_file.write_text(
		"""
		(define (domain internal-name)
		 (:requirements :strips)
		 (:predicates (ready) (done))
		 (:action finish
		  :parameters ()
		  :precondition (ready)
		  :effect (and (not (ready)) (done))
		 )
		)
		""",
		encoding="utf-8",
	)
	library_root = tmp_path / "domain_libraries"
	_write_atomic_library_json(library_root, domain_name="folder-key")
	goal_json = _write_lifted_ltlf_goal_json(tmp_path)

	completed = subprocess.run(
		[
			sys.executable,
			str(PROJECT_ROOT / "src" / "main.py"),
			"append-lifted-temporal-goal",
			"--domain-file",
			str(domain_file),
			"--ltlf-goal-json",
			str(goal_json),
			"--query-id",
			"query_1",
			"--library-root",
			str(library_root),
		],
		cwd=PROJECT_ROOT,
		check=True,
		capture_output=True,
		text=True,
	)
	result = json.loads(completed.stdout)

	assert Path(result["artifact_paths"]["plan_library_asl"]).parent == (
		library_root / "folder-key"
	)
	assert not (library_root / "internal-name" / "plan_library.asl").exists()


def test_main_rejects_noncanonical_append_library_file(tmp_path: Path) -> None:
	domain_file, _ = _write_tiny_domain_and_problem(tmp_path)
	noncanonical_library = tmp_path / "plan_library.json"
	_write_atomic_library_json(tmp_path, domain_name="tiny", library_file=noncanonical_library)
	goal_json = _write_lifted_ltlf_goal_json(tmp_path)

	completed = subprocess.run(
		[
			sys.executable,
			str(PROJECT_ROOT / "src" / "main.py"),
			"append-lifted-temporal-goal",
			"--domain-file",
			str(domain_file),
			"--plan-library-file",
			str(noncanonical_library),
			"--ltlf-goal-json",
			str(goal_json),
			"--query-id",
			"query_1",
			"--library-root",
			str(tmp_path / "domain_libraries"),
		],
		cwd=PROJECT_ROOT,
		capture_output=True,
		text=True,
	)

	assert completed.returncode != 0
	assert "noncanonical_domain_library" in completed.stderr


def _write_tiny_domain_and_problem(tmp_path: Path) -> tuple[Path, Path]:
	domain_file = tmp_path / "domain.pddl"
	problem_file = tmp_path / "problem.pddl"
	domain_file.write_text(
		"""
		(define (domain tiny)
		 (:requirements :strips)
		 (:predicates (ready) (done))
		 (:action finish
		  :parameters ()
		  :precondition (ready)
		  :effect (and (not (ready)) (done))
		 )
		)
		""",
		encoding="utf-8",
	)
	problem_file.write_text(
		"""
		(define (problem tiny-p1)
		 (:domain tiny)
		 (:objects)
		 (:init (ready))
		 (:goal (and (done)))
		)
		""",
		encoding="utf-8",
	)
	return domain_file, problem_file


def _write_atomic_library_json(
	root: Path,
	*,
	domain_name: str,
	library_file: Path | None = None,
) -> Path:
	library_file = library_file or root / domain_name / "plan_library.json"
	library_file.parent.mkdir(parents=True, exist_ok=True)
	library_file.write_text(
		json.dumps(
			{
				"domain_name": domain_name,
				"initial_beliefs": [],
				"metadata": {"atomic_template_backend": "test"},
				"plans": [
					{
						"plan_name": "done_via_finish",
						"trigger": {
							"event_type": "achievement_goal",
							"symbol": "done",
							"arguments": [],
						},
						"context": ["ready"],
						"body": [
							{"kind": "action", "symbol": "finish", "arguments": []},
						],
						"source_instruction_ids": [],
						"binding_certificate": [],
					},
				],
			},
		),
		encoding="utf-8",
	)
	return library_file


def _write_lifted_ltlf_goal_json(tmp_path: Path) -> Path:
	goal_json = tmp_path / "lifted_ltlf_goals.json"
	goal_json.write_text(
		json.dumps(
			{
				"schema_version": 1,
				"goal_specification_kind": "temporal_extended_goal",
				"temporal_logic": "LTLf",
				"domain": "tiny",
				"cases": {
					"query_1": {
						"goal_name": "g_query_1",
						"problem_file": "problem.pddl",
						"source_text": "Eventually finish.",
						"ltlf_formula": "F(done)",
						"atoms": ["done"],
						"bindings": {},
						"atom_vocabulary": "pddl_fluents",
						"status": "supported",
					},
				},
			},
		),
		encoding="utf-8",
	)
	return goal_json
