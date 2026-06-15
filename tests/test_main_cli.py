from __future__ import annotations

from main import build_argument_parser


def test_synthesize_domain_library_cli_parses_learner_sketches_options() -> None:
	parser = build_argument_parser()

	args = parser.parse_args(
		(
			"synthesize-domain-library",
			"--domain-file",
			"domain.pddl",
			"--training-problem",
			"p01.pddl",
			"--run-learner-sketches",
			"--learner-sketches-workspace",
			"tmp/learner",
			"--learner-sketches-width",
			"2",
			"--learner-sketches-max-rss-gb",
			"8",
			"--learner-sketches-timeout-seconds",
			"60",
			"--synthesis-profile",
			"paper",
		),
	)

	assert args.command == "synthesize-domain-library"
	assert args.run_learner_sketches is True
	assert args.learner_sketches_workspace == "tmp/learner"
	assert args.learner_sketches_width == 2
	assert args.learner_sketches_max_rss_gb == 8
	assert args.learner_sketches_timeout_seconds == 60
	assert args.synthesis_profile == "paper"
