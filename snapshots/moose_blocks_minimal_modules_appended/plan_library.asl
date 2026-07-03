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

/* plan=g_probe_p01_tower_progress_1 | source_instruction_ids=none */
+!g_probe_p01_tower : not on(b4, b2) <-
	!on(b4, b2);
	!g_probe_p01_tower.

/* plan=g_probe_p01_tower_progress_2 | source_instruction_ids=none */
+!g_probe_p01_tower : on(b4, b2) & not on(b1, b4) <-
	!on(b1, b4);
	!g_probe_p01_tower.

/* plan=g_probe_p01_tower_progress_3 | source_instruction_ids=none */
+!g_probe_p01_tower : on(b4, b2) & on(b1, b4) & not on(b3, b1) <-
	!on(b3, b1);
	!g_probe_p01_tower.

/* plan=g_probe_p01_tower_accepting_1 | source_instruction_ids=none */
+!g_probe_p01_tower : on(b4, b2) & on(b1, b4) & on(b3, b1) <-
	true.

/* plan=g_probe_p02_tower_progress_1 | source_instruction_ids=none */
+!g_probe_p02_tower : not on(b3, b5) <-
	!on(b3, b5);
	!g_probe_p02_tower.

/* plan=g_probe_p02_tower_progress_2 | source_instruction_ids=none */
+!g_probe_p02_tower : on(b3, b5) & not on(b6, b3) <-
	!on(b6, b3);
	!g_probe_p02_tower.

/* plan=g_probe_p02_tower_progress_3 | source_instruction_ids=none */
+!g_probe_p02_tower : on(b3, b5) & on(b6, b3) & not on(b1, b6) <-
	!on(b1, b6);
	!g_probe_p02_tower.

/* plan=g_probe_p02_tower_progress_4 | source_instruction_ids=none */
+!g_probe_p02_tower : on(b3, b5) & on(b6, b3) & on(b1, b6) & not on(b2, b1) <-
	!on(b2, b1);
	!g_probe_p02_tower.

/* plan=g_probe_p02_tower_progress_5 | source_instruction_ids=none */
+!g_probe_p02_tower : on(b3, b5) & on(b6, b3) & on(b1, b6) & on(b2, b1) & not on(b4, b2) <-
	!on(b4, b2);
	!g_probe_p02_tower.

/* plan=g_probe_p02_tower_progress_6 | source_instruction_ids=none */
+!g_probe_p02_tower : on(b3, b5) & on(b6, b3) & on(b1, b6) & on(b2, b1) & on(b4, b2) & not on(b7, b4) <-
	!on(b7, b4);
	!g_probe_p02_tower.

/* plan=g_probe_p02_tower_accepting_1 | source_instruction_ids=none */
+!g_probe_p02_tower : on(b3, b5) & on(b6, b3) & on(b1, b6) & on(b2, b1) & on(b4, b2) & on(b7, b4) <-
	true.
