from __future__ import annotations

import json
from pathlib import Path

from scripts.build_reproducibility_release import build_reproducibility_release


def test_release_copies_atomic_libraries_and_removes_local_absolute_paths(
	tmp_path: Path,
) -> None:
	project_root = tmp_path / "project"
	atomic_root = project_root / "artifacts" / "batch" / "domain_libraries"
	domain_root = atomic_root / "demo"
	domain_root.mkdir(parents=True)
	_asl_file = _write_text(domain_root / "plan_library.asl", "+!done : true <- true.\n")
	_json_file = _write_json(domain_root / "plan_library.json", {"plans": []})
	_write_json(domain_root / "atomic_library_metadata.json", {"domain": "demo"})
	benchmark_file = project_root / "paper_artifacts" / "benchmark.json"
	release_benchmark = {
		"benchmark_id": "demo-benchmark",
	}
	_write_json(benchmark_file, release_benchmark)
	execution_file = project_root / "artifacts" / "execution" / "summary.json"
	_write_json(
		execution_file,
		{
			"benchmark_id": "demo-benchmark",
			"atomic_batch_root": str(atomic_root.parent),
			"atomic_library_inputs": {
				"demo": {
					"plan_library_asl": str(_asl_file),
					"plan_library_json": str(_json_file),
				},
			},
			"parameters": {
				"plan_verifier_command": (
					f"bash {project_root / 'scripts/validate_with_docker_val.sh'}"
				),
			},
			"results": [
				{
					"domain": "demo",
					"sample_id": "demo_1",
					"problem_file": str(project_root / "src/domains/demo/test/p01.pddl"),
					"output_dir": str(project_root / "artifacts/execution/cases/demo_1"),
					"duration_seconds": 2.5,
					"action_count": 3,
				},
			],
		},
	)
	challenge_file = project_root / "artifacts" / "challenges" / "summary.json"
	_write_json(
		challenge_file,
		{
			"success": True,
			"records": [
				{
					"name": "binding",
					"success": True,
					"stdout": str(project_root / "artifacts/challenges/stdout.log"),
				},
			],
		},
	)
	output_dir = project_root / "paper_artifacts" / "gp2pl_evaluation" / "v1"

	report = build_reproducibility_release(
		project_root=project_root,
		execution_summary_file=execution_file,
		atomic_library_root=atomic_root,
		challenge_summary_file=challenge_file,
		benchmark_file=benchmark_file,
		output_dir=output_dir,
	)

	assert report["domain_count"] == 1
	assert report["result_count"] == 1
	assert (output_dir / "atomic_libraries/demo/plan_library.asl").is_file()
	portable_execution = json.loads(
		(output_dir / "temporal_execution_summary.json").read_text(encoding="utf-8"),
	)
	assert "atomic_batch_root" not in portable_execution
	assert portable_execution["atomic_library_inputs"]["demo"] == {
		"plan_library_asl": "atomic_libraries/demo/plan_library.asl",
		"plan_library_json": "atomic_libraries/demo/plan_library.json",
	}
	assert portable_execution["results"][0]["sample_id"] == "demo_1"
	assert "problem_file" not in portable_execution["results"][0]
	assert "output_dir" not in portable_execution["results"][0]
	assert "plan_verifier_command" not in portable_execution["parameters"]
	assert str(project_root) not in json.dumps(portable_execution)
	manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
	assert "atomic_libraries/demo/plan_library.asl" in manifest["files"]
	assert "benchmark_compatibility.json" not in manifest["files"]


def _write_text(path: Path, content: str) -> Path:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(content, encoding="utf-8")
	return path


def _write_json(path: Path, payload: object) -> Path:
	return _write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
