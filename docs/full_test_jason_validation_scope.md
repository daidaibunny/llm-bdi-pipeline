# Full-Test Jason Validation Scope

`scripts/run_full_test_jason_validation.py` is a diagnostic runner, not the full
natural-language/LTLf/LTLf2DFA pipeline.

Current behavior:

1. Read each test `problem.pddl`.
2. Extract positive facts from the PDDL `:goal`.
3. Preserve the parser/file order of those facts.
4. Emit a query-local `tg_state(...)` ASL wrapper with one progress step per
   goal fact.
5. Run Jason against the generated atomic ASL library plus that wrapper.

This means the runner validates:

```text
PDDL test goal facts -> ordered singleton progress wrapper -> Jason execution
```

It does not validate:

```text
natural language -> lifted LTLf JSON -> LTLf2DFA -> validated DFA -> ASL append
```

The goal order is not learned and is not derived by LTLf2DFA. It is currently
the PDDL parser order. For domains with interacting goal literals, especially
Blocks-style construction goals, this can be the wrong temporal order. Treat
failures as useful diagnostics of atomic library behavior and ordering
limitations, not as final evidence about the real temporal input pipeline.
