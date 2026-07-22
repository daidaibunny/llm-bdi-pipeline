#!/usr/bin/env python3
"""Materialize the locked overview and generate the verified method figure."""

from __future__ import annotations

import argparse
from datetime import datetime
from datetime import timezone
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.patches import FancyArrowPatch  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "latex_code/aamas_method_paper/figures"
FIGURE_ONE_WIDTH_INCHES = 3.25
FIGURE_ONE_HEIGHT_INCHES = 1.60
FIGURE_TWO_WIDTH_INCHES = 7.0
FIGURE_TWO_HEIGHT_INCHES = 3.45
FIGURE_FONT_FAMILY = "Helvetica"
FIGURE_CODE_FONT_FAMILY = "Courier New"
MINIMUM_TEXT_SIZE_POINTS = 9.0
FIGURE_COLOR_MODE = "colorblind_safe_cmyk"

DOMAIN_FILE = PROJECT_ROOT / "src/domains/blocksworld-on/domain.pddl"
EVIDENCE_FILE = (
	PROJECT_ROOT
	/ "artifacts/moose_asl_batches/pddl-five-seed-20260713-153900-seed0"
	/ "run_logs/blocksworld-on/blocksworld-on.model.readable"
)
LIBRARY_FILE = (
	PROJECT_ROOT
	/ "artifacts/moose_asl_batches/pddl-five-seed-20260713-153900-seed0"
	/ "domain_libraries/blocksworld-on/plan_library.asl"
)
LOCKED_FIGURE_ONE_PATH = DEFAULT_OUTPUT_DIR / "fig1_architecture.png"
LOCKED_FIGURE_ONE_SHA256 = (
	"3636e5e510f16576a48026e751ff89ccd0dcadb70ad9c6adf588bd386ec1cefe"
)
LOCKED_FIGURE_ONE_PIXEL_SIZE = (2558, 1257)
LOCKED_FIGURE_ONE_DPI = 330

COLORS = {
	"text": "#1A1A1A",
	"muted": "#666666",
	"panel": "#FFFFFF",
	"gray_fill": "#F2F2F2",
	"gray_edge": "#767676",
	"amber_fill": "#FFF1CC",
	"amber_edge": "#B26A00",
	"blue_fill": "#DDEBF7",
	"blue_edge": "#0072B2",
	"green_fill": "#DDF2E9",
	"green_edge": "#009E73",
	"purple_fill": "#EEE4F2",
	"purple_edge": "#9A5796",
}


def generate_method_figures(*, output_dir: str | Path) -> dict[str, Any]:
	"""Copy the locked overview and render the evidence-backed method figure."""

	output_path = Path(output_dir).expanduser().resolve()
	source_hashes = _verify_worked_example_sources()
	figure_one_bytes = _locked_figure_one_bytes()
	figure_two_bytes = _render_figure_two()
	output_path.mkdir(parents=True, exist_ok=True)
	figure_one_path = output_path / "fig1_architecture.png"
	figure_two_path = output_path / "fig2_policy_lifting.pdf"
	if figure_one_path != LOCKED_FIGURE_ONE_PATH.resolve():
		figure_one_path.write_bytes(figure_one_bytes)
	figure_two_path.write_bytes(figure_two_bytes)

	metadata = {
		"schema_version": 1,
		"artifact_kind": "gp2pl_aaai_method_figures",
		"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
		"color_mode": "locked_rgb_overview_and_generated_cmyk_method_figure",
		"font_family": FIGURE_FONT_FAMILY,
		"minimum_text_size_points": MINIMUM_TEXT_SIZE_POINTS,
		"figure_one": {
			"output_file": _portable_path(figure_one_path),
			"semantic_role": "problem_overview",
			"source_kind": "locked_final_artwork",
			"sha256": LOCKED_FIGURE_ONE_SHA256,
			"pixel_size": list(LOCKED_FIGURE_ONE_PIXEL_SIZE),
			"dpi": LOCKED_FIGURE_ONE_DPI,
			"color_mode": "srgb_with_alpha",
			"width_inches": FIGURE_ONE_WIDTH_INCHES,
			"height_inches": FIGURE_ONE_HEIGHT_INCHES,
			"labels": [
				"Domain",
				"Singleton-goal Evidence",
				"Maintained BDI Plan Library",
				"Bound temporal query",
			],
		},
		"figure_two": {
			"output_file": _portable_path(figure_two_path),
			"semantic_role": "worked_policy_lifting_example",
			"color_mode": FIGURE_COLOR_MODE,
			"width_inches": FIGURE_TWO_WIDTH_INCHES,
			"height_inches": FIGURE_TWO_HEIGHT_INCHES,
			"example_domain": "blocksworld-on",
			"source_sha256": source_hashes,
			"excerpt_is_complete_library": False,
		},
	}
	metadata_path = output_path / "method_figures.metadata.json"
	metadata_path.write_text(
		json.dumps(metadata, indent=2, sort_keys=True) + "\n",
		encoding="utf-8",
	)
	return metadata


def _locked_figure_one_bytes() -> bytes:
	"""Return the approved Figure 1 artwork only when its identity is unchanged."""

	if not LOCKED_FIGURE_ONE_PATH.is_file():
		raise FileNotFoundError(
			f"Locked Figure 1 artwork is missing: {LOCKED_FIGURE_ONE_PATH}",
		)
	payload = LOCKED_FIGURE_ONE_PATH.read_bytes()
	if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
		raise ValueError("Locked Figure 1 artwork is not a PNG file")
	digest = hashlib.sha256(payload).hexdigest()
	if digest != LOCKED_FIGURE_ONE_SHA256:
		raise ValueError(
			"Locked Figure 1 artwork hash changed: "
			f"expected {LOCKED_FIGURE_ONE_SHA256}, received {digest}",
		)
	return payload


def convert_pdf_bytes_to_cmyk(pdf_bytes: bytes) -> bytes:
	"""Convert a vector PDF to print-oriented CMYK while preserving its fonts."""

	ghostscript = shutil.which("gs")
	if ghostscript is None:
		raise RuntimeError("Ghostscript is required for CMYK figure generation")
	with tempfile.TemporaryDirectory(prefix="gp2pl-figure-") as temporary_dir:
		temporary_root = Path(temporary_dir)
		input_path = temporary_root / "input.pdf"
		output_path = temporary_root / "output.pdf"
		input_path.write_bytes(pdf_bytes)
		completed = subprocess.run(
			(
				ghostscript,
				"-q",
				"-dNOPAUSE",
				"-dBATCH",
				"-sDEVICE=pdfwrite",
				"-dPDFSETTINGS=/prepress",
				"-dEmbedAllFonts=true",
				"-dSubsetFonts=true",
				"-dAutoRotatePages=/None",
				"-sProcessColorModel=DeviceCMYK",
				"-sColorConversionStrategy=CMYK",
				"-sColorConversionStrategyForImages=CMYK",
				f"-sOutputFile={output_path}",
				str(input_path),
			),
			check=False,
			capture_output=True,
			text=True,
		)
		if completed.returncode != 0 or not output_path.is_file():
			detail = completed.stderr.strip() or completed.stdout.strip()
			raise RuntimeError(f"Ghostscript CMYK conversion failed: {detail}")
		converted = output_path.read_bytes()
	if not converted.startswith(b"%PDF"):
		raise RuntimeError("Ghostscript did not produce a PDF")
	return converted


def _verify_worked_example_sources() -> dict[str, str]:
	domain_text = DOMAIN_FILE.read_text(encoding="utf-8")
	evidence_text = EVIDENCE_FILE.read_text(encoding="utf-8")
	library_text = LIBRARY_FILE.read_text(encoding="utf-8")
	required_domain_fragments = (
		"(:action stack",
		":precondition (and (clear ?underob) (holding ?ob))",
		"(on ?ob ?underob)",
	)
	required_evidence_fragments = (
		"s_cond : (clear any_obj1) (holding any_obj0)",
		"g_cond : (on any_obj0 any_obj1)",
		"actions : (stack any_obj0 any_obj1)",
	)
	required_library_fragments = (
		"+!on(X, Y) : on(X, Y) <-",
		"+!on(X, Y) : clear(Y) & holding(X) <-\n\tstack(X, Y).",
		"+!on(X, Y) : not clear(Y) <-\n\t!clear(Y);\n\t!on(X, Y).",
		"+!clear(X) : on(Y, X) & not clear(Y) <-",
	)
	for fragment in required_domain_fragments:
		if fragment not in domain_text:
			raise ValueError(f"worked-example domain no longer contains {fragment!r}")
	for fragment in required_evidence_fragments:
		if fragment not in evidence_text:
			raise ValueError(f"worked-example evidence no longer contains {fragment!r}")
	for fragment in required_library_fragments:
		if fragment not in library_text:
			raise ValueError(f"worked-example library no longer contains {fragment!r}")
	return {
		"domain_pddl": _sha256(DOMAIN_FILE),
		"evidence_policy": _sha256(EVIDENCE_FILE),
		"agentspeak_library": _sha256(LIBRARY_FILE),
	}


def _render_figure_two() -> bytes:
	with plt.rc_context(_matplotlib_style()):
		figure, axis = plt.subplots(
			figsize=(FIGURE_TWO_WIDTH_INCHES, FIGURE_TWO_HEIGHT_INCHES),
		)
		figure.subplots_adjust(left=0.008, right=0.992, bottom=0.015, top=0.985)
		_prepare_axis(axis)
		for x, width in ((0.7, 31.5), (33.0, 32.5), (66.3, 33.0)):
			_draw_box(
				axis,
				x,
				2.0,
				width,
				95.5,
				"",
				fill=COLORS["panel"],
				edge="#B8B8B8",
				linewidth=0.8,
			)

		_draw_panel_a(axis)
		_draw_panel_b(axis)
		_draw_panel_c(axis)
		return _figure_to_cmyk_pdf(figure)


def _draw_panel_a(axis: Axes) -> None:
	axis.text(
		2.0,
		94.0,
		"(a) Evidence and producible targets",
		ha="left",
		va="top",
		fontsize=MINIMUM_TEXT_SIZE_POINTS,
		color=COLORS["text"],
	)
	_draw_box(
		axis,
		2.2,
		65.0,
		28.5,
		22.0,
		"",
		fill=COLORS["amber_fill"],
		edge=COLORS["amber_edge"],
	)
	axis.text(
		3.2,
		84.2,
		"Normalized evidence  $e\\in E$",
		ha="left",
		va="top",
		fontsize=MINIMUM_TEXT_SIZE_POINTS,
		color=COLORS["text"],
	)
	axis.text(
		3.2,
		79.5,
		"goal:    on(X,Y)\ncontext: holding(X),\n         clear(Y)\nbody:    stack(X,Y)",
		ha="left",
		va="top",
		fontsize=MINIMUM_TEXT_SIZE_POINTS,
		fontfamily=FIGURE_CODE_FONT_FAMILY,
		linespacing=1.15,
		color=COLORS["text"],
	)
	_draw_arrow(axis, (16.4, 65.0), (16.4, 60.0), color=COLORS["amber_edge"])
	axis.text(
		16.4,
		62.3,
		"schema-validated",
		ha="center",
		va="center",
		fontsize=MINIMUM_TEXT_SIZE_POINTS,
		color=COLORS["muted"],
	)
	_draw_box(
		axis,
		2.2,
		37.0,
		28.5,
		21.0,
		"",
		fill=COLORS["blue_fill"],
		edge=COLORS["blue_edge"],
	)
	axis.text(
		3.2,
		57.0,
		"Producer schema (excerpt)",
		ha="left",
		va="top",
		fontsize=MINIMUM_TEXT_SIZE_POINTS,
		color=COLORS["text"],
	)
	axis.text(
		3.2,
		52.5,
		"stack(X,Y)\npre: holding(X),\n     clear(Y)\nadd: on(X,Y)",
		ha="left",
		va="top",
		fontsize=MINIMUM_TEXT_SIZE_POINTS,
		fontfamily=FIGURE_CODE_FONT_FAMILY,
		linespacing=1.12,
		color=COLORS["text"],
	)
	_draw_arrow(axis, (16.4, 37.0), (16.4, 32.0), color=COLORS["blue_edge"])
	axis.text(
		16.4,
		34.4,
		"producible-target\nexpansion",
		ha="center",
		va="center",
		fontsize=MINIMUM_TEXT_SIZE_POINTS,
		color=COLORS["blue_edge"],
	)
	_draw_box(
		axis,
		2.2,
		10.0,
		28.5,
		20.0,
		"",
		fill=COLORS["green_fill"],
		edge=COLORS["green_edge"],
	)
	axis.text(
		16.4,
		27.8,
		"$T_D(E)$",
		ha="center",
		va="top",
		fontsize=MINIMUM_TEXT_SIZE_POINTS,
		color=COLORS["text"],
	)
	axis.text(
		16.4,
		22.5,
		"on/2, clear/1, holding/1,\narm_empty/0, on_table/1",
		ha="center",
		va="top",
		fontsize=MINIMUM_TEXT_SIZE_POINTS,
		fontfamily=FIGURE_CODE_FONT_FAMILY,
		linespacing=1.2,
		color=COLORS["text"],
	)
	axis.text(
		16.4,
		5.5,
		"Static predicates: context only.",
		ha="center",
		va="center",
		fontsize=MINIMUM_TEXT_SIZE_POINTS,
		color=COLORS["muted"],
	)


def _draw_panel_b(axis: Axes) -> None:
	axis.text(
		34.0,
		94.0,
		"(b) Feasible-core optimization",
		ha="left",
		va="top",
		fontsize=MINIMUM_TEXT_SIZE_POINTS,
		color=COLORS["text"],
	)
	axis.text(
		34.2,
		87.5,
		"Certified candidates  $\\mathcal{C}^{\\checkmark}_{D,E}$",
		ha="left",
		va="top",
		fontsize=MINIMUM_TEXT_SIZE_POINTS,
		color=COLORS["blue_edge"],
	)
	candidates = (
		(74.0, "E", "validated evidence macro", "amber_fill", "amber_edge", "-"),
		(62.0, "D1", "direct stack producer", "blue_fill", "blue_edge", "-"),
		(50.0, "R1", "!clear(Y); !on(X,Y)", "blue_fill", "blue_edge", "-"),
		(38.0, "M1", "longer feasible macro", "gray_fill", "gray_edge", "--"),
	)
	for y, identifier, label, fill_key, edge_key, line_style in candidates:
		_draw_box(
			axis,
			34.2,
			y,
			30.2,
			9.0,
			"",
			fill=COLORS[fill_key],
			edge=COLORS[edge_key],
			linestyle=line_style,
		)
		axis.text(
			35.4,
			y + 4.5,
			f"{identifier}: {label}",
			ha="left",
			va="center",
			fontsize=MINIMUM_TEXT_SIZE_POINTS,
			fontfamily=(
				FIGURE_CODE_FONT_FAMILY if identifier == "R1" else FIGURE_FONT_FAMILY
			),
			color=COLORS["text"],
		)
	_draw_box(
		axis,
		34.2,
		19.0,
		30.2,
		18.0,
		"",
		fill="#F8FBFE",
		edge=COLORS["blue_edge"],
		linestyle="--",
	)
	axis.text(
		49.3,
		33.5,
		"Candidate soundness certificate",
		ha="center",
		va="top",
		fontsize=MINIMUM_TEXT_SIZE_POINTS,
		color=COLORS["blue_edge"],
	)
	axis.text(
		49.3,
		28.5,
		"binding | execution | achievement\ninternal-call | progress\nresource discharge",
		ha="center",
		va="top",
		fontsize=MINIMUM_TEXT_SIZE_POINTS,
		linespacing=1.05,
		color=COLORS["text"],
	)
	selection = Polygon(
		((39.0, 13.5), (42.0, 17.5), (59.6, 17.5), (62.6, 13.5),
		 (59.6, 9.5), (42.0, 9.5)),
		closed=True,
		facecolor=COLORS["blue_edge"],
		edgecolor=COLORS["blue_edge"],
		linewidth=0.9,
	)
	axis.add_patch(selection)
	axis.text(
		50.8,
		13.5,
		"lexicographic\nselection",
		ha="center",
		va="center",
		fontsize=MINIMUM_TEXT_SIZE_POINTS,
		color="white",
	)
	_draw_arrow(axis, (49.3, 19.0), (50.8, 17.5), color=COLORS["blue_edge"])
	axis.text(
		49.3,
		5.3,
		"Optimum is relative to $\\mathcal{C}^{\\checkmark}_{D,E}$.",
		ha="center",
		va="center",
		fontsize=MINIMUM_TEXT_SIZE_POINTS,
		color=COLORS["muted"],
	)
	_draw_arrow(axis, (62.6, 13.5), (67.5, 13.5), color=COLORS["green_edge"])


def _draw_panel_c(axis: Axes) -> None:
	axis.text(
		67.5,
		94.0,
		"(c) Certified atomic module core",
		ha="left",
		va="top",
		fontsize=MINIMUM_TEXT_SIZE_POINTS,
		color=COLORS["text"],
	)
	_draw_box(
		axis,
		67.5,
		9.0,
		30.5,
		78.0,
		"",
		fill="#F7FBF5",
		edge=COLORS["green_edge"],
		linewidth=1.1,
	)
	axis.text(
		82.75,
		83.5,
		"Selected excerpt from $\\mathcal{M}_D=S^\\star$",
		ha="center",
		va="top",
		fontsize=MINIMUM_TEXT_SIZE_POINTS,
		color=COLORS["text"],
	)
	_draw_box(
		axis,
		69.0,
		36.0,
		27.5,
		41.5,
		"",
		fill="white",
		edge=COLORS["gray_edge"],
	)
	code = (
		"+!on(X,Y) : on(X,Y)\n"
		"  <- true.\n\n"
		"+!on(X,Y) :\n"
		"  clear(Y) & holding(X)\n"
		"  <- stack(X,Y).\n\n"
		"+!on(X,Y) : not clear(Y)\n"
		"  <- !clear(Y);\n"
		"     !on(X,Y).\n"
		"..."
	)
	axis.text(
		70.0,
		75.0,
		code,
		ha="left",
		va="top",
		fontsize=MINIMUM_TEXT_SIZE_POINTS,
		fontfamily=FIGURE_CODE_FONT_FAMILY,
		linespacing=1.08,
		color=COLORS["text"],
	)
	_draw_arrow(axis, (82.75, 36.0), (82.75, 30.8), color=COLORS["green_edge"])
	axis.text(
		87.0,
		33.3,
		"internal-call closure",
		ha="center",
		va="center",
		fontsize=MINIMUM_TEXT_SIZE_POINTS,
		color=COLORS["green_edge"],
	)
	_draw_box(
		axis,
		71.5,
		18.0,
		22.5,
		11.5,
		"+!clear(...) module",
		fill=COLORS["green_fill"],
		edge=COLORS["green_edge"],
		fontfamily=FIGURE_CODE_FONT_FAMILY,
	)
	axis.text(
		82.75,
		12.7,
		"No training objects;\nno synthetic goals.",
		ha="center",
		va="center",
		fontsize=MINIMUM_TEXT_SIZE_POINTS,
		color=COLORS["muted"],
	)


def _draw_box(
	axis: Axes,
	x: float,
	y: float,
	width: float,
	height: float,
	label: str,
	*,
	fill: str,
	edge: str,
	linestyle: str = "-",
	linewidth: float = 0.9,
	fontfamily: str = FIGURE_FONT_FAMILY,
) -> None:
	patch = FancyBboxPatch(
		(x, y),
		width,
		height,
		boxstyle="round,pad=0.25,rounding_size=1.5",
		facecolor=fill,
		edgecolor=edge,
		linestyle=linestyle,
		linewidth=linewidth,
	)
	axis.add_patch(patch)
	if label:
		axis.text(
			x + width / 2,
			y + height / 2,
			label,
			ha="center",
			va="center",
			fontsize=MINIMUM_TEXT_SIZE_POINTS,
			fontfamily=fontfamily,
			color=COLORS["text"],
		)


def _draw_arrow(
	axis: Axes,
	start: tuple[float, float],
	end: tuple[float, float],
	*,
	color: str,
	linestyle: str = "-",
	connectionstyle: str = "arc3",
) -> None:
	axis.add_patch(
		FancyArrowPatch(
			start,
			end,
			arrowstyle="-|>",
			mutation_scale=8.0,
			linewidth=0.9,
			linestyle=linestyle,
			color=color,
			connectionstyle=connectionstyle,
			shrinkA=0.0,
			shrinkB=0.0,
		),
	)


def _prepare_axis(axis: Axes) -> None:
	axis.set_xlim(0, 100)
	axis.set_ylim(0, 100)
	axis.axis("off")


def _figure_to_cmyk_pdf(figure: Figure) -> bytes:
	buffer = io.BytesIO()
	figure.savefig(
		buffer,
		format="pdf",
		bbox_inches=None,
		pad_inches=0,
		facecolor="white",
		metadata={
			"Title": "GP2PL method figure",
			"Creator": "scripts/generate_aaai_method_figures.py",
		},
	)
	plt.close(figure)
	return convert_pdf_bytes_to_cmyk(buffer.getvalue())


def _matplotlib_style() -> dict[str, Any]:
	return {
		"font.family": "sans-serif",
		"font.sans-serif": [FIGURE_FONT_FAMILY],
		"font.size": MINIMUM_TEXT_SIZE_POINTS,
		"font.weight": "normal",
		"axes.titleweight": "normal",
		"pdf.fonttype": 42,
		"ps.fonttype": 42,
		"savefig.transparent": False,
	}


def _portable_path(path: Path) -> str:
	try:
		return path.resolve().relative_to(PROJECT_ROOT).as_posix()
	except ValueError:
		return path.resolve().as_posix()


def _sha256(path: Path) -> str:
	digest = hashlib.sha256()
	with path.open("rb") as handle:
		for chunk in iter(lambda: handle.read(1024 * 1024), b""):
			digest.update(chunk)
	return digest.hexdigest()


def _parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
	return parser.parse_args()


def main() -> int:
	args = _parse_args()
	metadata = generate_method_figures(output_dir=args.output_dir)
	print(
		"[ok] method_figures "
		f"figure1={metadata['figure_one']['output_file']} "
		f"figure2={metadata['figure_two']['output_file']}",
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
