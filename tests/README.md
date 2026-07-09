# Tests

The active test suite covers:

- PDDL parsing
- lifted LTLf JSON schema validation
- LTLf-to-DFA conversion
- singleton-literal DFA validation
- Evidence Module compilation, including the MOOSE readable-policy adapter
- temporal goal append wrappers
- external generalized-planning backend audit helpers

Run the focused suite with:

```bash
uv run pytest \
  tests/utils/test_pddl_parser.py \
  tests/utils/test_symbol_normalizer.py \
  tests/utils/test_config.py \
  tests/evaluation/temporal_compilation/test_ltlf_to_dfa.py \
  tests/domain_level_planning/test_lifted_ltlf_goal_schema.py \
  tests/domain_level_planning/test_temporal_goal_appender.py \
  tests/domain_level_planning/test_evidence_module.py
```
