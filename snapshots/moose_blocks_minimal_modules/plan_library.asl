/* Generated AgentSpeak(L) Plan Library */
/* Domain: blocks */

/* plan=on_already_true | source_instruction_ids=none */
+!on(X, Y) : on(X, Y) <-
	true.

/* plan=on_via_pick-up_then_stack | source_instruction_ids=none */
+!on(X, Y) : clear(X) & ontable(X) & handempty & clear(Y) <-
	pick_up(X);
	stack(X, Y).

/* plan=on_prepare_clear_X | source_instruction_ids=none */
+!on(X, Y) : not clear(X) <-
	!clear(X);
	!on(X, Y).

/* plan=on_prepare_clear_Y | source_instruction_ids=none */
+!on(X, Y) : not clear(Y) <-
	!clear(Y);
	!on(X, Y).

/* plan=on_via_unstack_then_stack | source_instruction_ids=none */
+!on(X, Y) : on(X, Z) & clear(X) & handempty & clear(Y) <-
	unstack(X, Z);
	stack(X, Y).

/* plan=clear_already_true | source_instruction_ids=none */
+!clear(X) : clear(X) <-
	true.

/* plan=clear_via_unstack_then_put-down | source_instruction_ids=none */
+!clear(X) : on(Y, X) & clear(Y) & handempty <-
	unstack(Y, X);
	put_down(Y).

/* plan=clear_prepare_clear_Y | source_instruction_ids=none */
+!clear(X) : on(Y, X) & not clear(Y) <-
	!clear(Y);
	!clear(X).
