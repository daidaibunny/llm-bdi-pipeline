# Tests

The active test suite covers:

- PDDL parsing
- stored LTLf event extraction and PDDL fluent mapping
- DFA-driven high-level AgentSpeak(L) plan generation
- Fast Downward low-level planning adapter
- plan-library artifact persistence
- structural validation of context-driven `!g` plans

Run the focused suite with:

```bash
uv run pytest \
  tests/utils/test_pddl_parser.py \
  tests/utils/test_symbol_normalizer.py \
  tests/utils/test_negation_mode_resolver.py \
  tests/utils/test_config.py \
  tests/temporal_specification \
  tests/low_level_planning \
  tests/plan_library
```
