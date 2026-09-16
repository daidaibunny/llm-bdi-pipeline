import importlib.util
import json
from pathlib import Path
from zipfile import ZipFile

import pytest


def test_definition_audit_rejects_changed_problem_inputs(tmp_path, monkeypatch):
	path = Path(__file__).resolve().parents[2] / "scripts/audit_uploaded_metric_definitions.py"
	spec = importlib.util.spec_from_file_location("definition_audit", path)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	monkeypatch.setattr(module, "ROOT", tmp_path)
	domain = tmp_path / "src/domains/test/domain.pddl"
	domain.parent.mkdir(parents=True)
	domain.write_text("(define (domain test) (:predicates (p)))")
	problem = domain.parent / "problem.pddl"
	problem.write_text("(define (problem p) (:domain test) (:init (p)) (:goal (p)))")
	folder = tmp_path / "audit"
	folder.mkdir()
	library = folder / "library.json"
	library.write_text(json.dumps({"plans": []}))
	protocol = {"libraries": [{"seed": 0, "domain": "test", "file": "library.json",
		"sha256": module.sha256(library)}], "cases": [{
		"domain_file": str(domain.relative_to(tmp_path)), "domain_sha256": module.sha256(domain),
		"problem": str(problem.relative_to(tmp_path)), "problem_sha256": module.sha256(problem)}]}
	(folder / "protocol.json").write_text(json.dumps(protocol))
	summary = {"protocol_sha256": module.sha256(folder / "protocol.json"),
		"evaluator_files_sha256": {}, "records": [{"seed": 0, "domain": "test",
		"problem": str(problem.relative_to(tmp_path)), "case_index": 0, "obligations": []}]}
	(folder / "summary.json").write_text(json.dumps(summary))
	labels = ("def:correctness-plan-instance", "def:correctness-plan-template",
		"eq:basic-coverage-plan", "eq:extended-coverage-plan", "eq:extended-coverage-goal")
	archive = tmp_path / "source.zip"
	with ZipFile(archive, "w") as output:
		output.writestr("paper/outline/sections/preliminaries.tex",
			"\n".join(f"\\label{{{label}}}" for label in labels))
	problem.write_text(problem.read_text() + "\n; changed\n")
	with pytest.raises(ValueError, match="Problem changed"):
		module.audit(archive, folder)
