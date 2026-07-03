/* Generated AgentSpeak(L) Plan Library */
/* Domain: blocks */

teg_state(g_probe_p01_tower, state_1).
teg_state(g_probe_p02_tower, state_1).

/* plan=moose_blocks_probe_first4_rule_1 | source_instruction_ids=none */
+!on(Block0, Block1) : clear(Block1) & holding(Block0) <-
	stack(Block0, Block1).

/* plan=moose_blocks_probe_first4_rule_2 | source_instruction_ids=none */
+!on(Block0, Block1) : clear(Block0) & clear(Block1) & handempty & ontable(Block0) <-
	pick_up(Block0);
	stack(Block0, Block1).

/* plan=moose_blocks_probe_first4_rule_3 | source_instruction_ids=none */
+!on(Block0, Block2) : clear(Block0) & clear(Block2) & handempty & on(Block0, Block1) <-
	unstack(Block0, Block1);
	stack(Block0, Block2).

/* plan=moose_blocks_probe_first4_rule_4 | source_instruction_ids=none */
+!on(Block1, Block2) : clear(Block1) & clear(Block2) & holding(Block0) & ontable(Block1) <-
	put_down(Block0);
	pick_up(Block1);
	stack(Block1, Block2).

/* plan=moose_blocks_probe_first4_rule_5 | source_instruction_ids=none */
+!on(Block1, Block0) : clear(Block1) & holding(Block0) & ontable(Block1) <-
	put_down(Block0);
	pick_up(Block1);
	stack(Block1, Block0).

/* plan=moose_blocks_probe_first4_rule_6 | source_instruction_ids=none */
+!on(Block1, Block3) : clear(Block1) & clear(Block3) & holding(Block0) & on(Block1, Block2) <-
	put_down(Block0);
	unstack(Block1, Block2);
	stack(Block1, Block3).

/* plan=moose_blocks_probe_first4_rule_7 | source_instruction_ids=none */
+!on(Block1, Block0) : clear(Block1) & holding(Block0) & on(Block1, Block2) <-
	put_down(Block0);
	unstack(Block1, Block2);
	stack(Block1, Block0).

/* plan=moose_blocks_probe_first4_rule_8 | source_instruction_ids=none */
+!on(Block1, Block0) : clear(Block0) & handempty & on(Block0, Block1) & ontable(Block1) <-
	unstack(Block0, Block1);
	put_down(Block0);
	pick_up(Block1);
	stack(Block1, Block0).

/* plan=moose_blocks_probe_first4_rule_9 | source_instruction_ids=none */
+!on(Block1, Block0) : clear(Block0) & handempty & on(Block0, Block1) & on(Block1, Block2) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	stack(Block1, Block0).

/* plan=moose_blocks_probe_first4_rule_10 | source_instruction_ids=none */
+!on(Block2, Block1) : clear(Block0) & clear(Block2) & handempty & on(Block0, Block1) & on(Block2, Block3) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block2, Block3);
	stack(Block2, Block1).

/* plan=moose_blocks_probe_first4_rule_11 | source_instruction_ids=none */
+!on(Block2, Block1) : clear(Block0) & clear(Block2) & handempty & on(Block0, Block1) & ontable(Block2) <-
	unstack(Block0, Block1);
	put_down(Block0);
	pick_up(Block2);
	stack(Block2, Block1).

/* plan=moose_blocks_probe_first4_rule_12 | source_instruction_ids=none */
+!on(Block1, Block2) : clear(Block0) & clear(Block2) & handempty & on(Block0, Block1) & ontable(Block1) <-
	unstack(Block0, Block1);
	put_down(Block0);
	pick_up(Block1);
	stack(Block1, Block2).

/* plan=moose_blocks_probe_first4_rule_13 | source_instruction_ids=none */
+!on(Block1, Block3) : clear(Block0) & clear(Block3) & handempty & on(Block0, Block1) & on(Block1, Block2) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	stack(Block1, Block3).

/* plan=moose_blocks_probe_first4_rule_14 | source_instruction_ids=none */
+!on(Block2, Block1) : clear(Block1) & holding(Block0) & on(Block1, Block2) & ontable(Block2) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	pick_up(Block2);
	stack(Block2, Block1).

/* plan=moose_blocks_probe_first4_rule_15 | source_instruction_ids=none */
+!on(Block2, Block4) : clear(Block1) & clear(Block4) & holding(Block0) & on(Block1, Block2) & on(Block2, Block3) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	stack(Block2, Block4).

/* plan=moose_blocks_probe_first4_rule_16 | source_instruction_ids=none */
+!on(Block2, Block3) : clear(Block1) & clear(Block3) & holding(Block0) & on(Block1, Block2) & ontable(Block2) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	pick_up(Block2);
	stack(Block2, Block3).

/* plan=moose_blocks_probe_first4_rule_17 | source_instruction_ids=none */
+!on(Block3, Block2) : clear(Block1) & clear(Block3) & holding(Block0) & on(Block1, Block2) & ontable(Block3) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	pick_up(Block3);
	stack(Block3, Block2).

/* plan=moose_blocks_probe_first4_rule_18 | source_instruction_ids=none */
+!on(Block0, Block3) : clear(Block1) & clear(Block2) & holding(Block0) & on(Block2, Block3) <-
	stack(Block0, Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block0, Block1);
	stack(Block0, Block3).

/* plan=moose_blocks_probe_first4_rule_19 | source_instruction_ids=none */
+!on(Block3, Block2) : clear(Block1) & clear(Block3) & holding(Block0) & on(Block1, Block2) & on(Block3, Block4) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block3, Block4);
	stack(Block3, Block2).

/* plan=moose_blocks_probe_first4_rule_20 | source_instruction_ids=none */
+!on(Block2, Block4) : clear(Block0) & clear(Block4) & handempty & on(Block0, Block1) & on(Block1, Block2) & on(Block2, Block3) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	stack(Block2, Block4).

/* plan=moose_blocks_probe_first4_rule_21 | source_instruction_ids=none */
+!on(Block2, Block3) : clear(Block0) & clear(Block3) & handempty & on(Block0, Block1) & on(Block1, Block2) & ontable(Block2) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	pick_up(Block2);
	stack(Block2, Block3).

/* plan=moose_blocks_probe_first4_rule_22 | source_instruction_ids=none */
+!on(Block3, Block2) : clear(Block0) & clear(Block3) & handempty & on(Block0, Block1) & on(Block1, Block2) & on(Block3, Block4) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block3, Block4);
	stack(Block3, Block2).

/* plan=moose_blocks_probe_first4_rule_23 | source_instruction_ids=none */
+!on(Block1, Block3) : clear(Block0) & clear(Block2) & handempty & on(Block0, Block1) & on(Block2, Block3) & ontable(Block1) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block2, Block3);
	put_down(Block2);
	pick_up(Block1);
	stack(Block1, Block3).

/* plan=moose_blocks_probe_first4_rule_24 | source_instruction_ids=none */
+!on(Block0, Block3) : clear(Block0) & clear(Block2) & handempty & on(Block0, Block1) & on(Block1, Block3) <-
	unstack(Block0, Block1);
	stack(Block0, Block2);
	unstack(Block1, Block3);
	put_down(Block1);
	unstack(Block0, Block2);
	stack(Block0, Block3).

/* plan=moose_blocks_probe_first4_rule_25 | source_instruction_ids=none */
+!on(Block2, Block1) : clear(Block0) & handempty & on(Block0, Block1) & on(Block1, Block2) & ontable(Block2) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	pick_up(Block2);
	stack(Block2, Block1).

/* plan=moose_blocks_probe_first4_rule_26 | source_instruction_ids=none */
+!on(Block3, Block2) : clear(Block0) & clear(Block3) & handempty & on(Block0, Block1) & on(Block1, Block2) & ontable(Block3) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	pick_up(Block3);
	stack(Block3, Block2).

/* plan=moose_blocks_probe_first4_rule_27 | source_instruction_ids=none */
+!on(Block4, Block3) : clear(Block1) & clear(Block4) & holding(Block0) & on(Block1, Block2) & on(Block2, Block3) & on(Block4, Block5) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block4, Block5);
	stack(Block4, Block3).

/* plan=moose_blocks_probe_first4_rule_28 | source_instruction_ids=none */
+!on(Block3, Block4) : clear(Block1) & clear(Block4) & holding(Block0) & on(Block1, Block2) & on(Block2, Block3) & ontable(Block3) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	pick_up(Block3);
	stack(Block3, Block4).

/* plan=moose_blocks_probe_first4_rule_29 | source_instruction_ids=none */
+!on(Block3, Block2) : clear(Block1) & holding(Block0) & on(Block1, Block2) & on(Block2, Block3) & ontable(Block3) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	pick_up(Block3);
	stack(Block3, Block2).

/* plan=moose_blocks_probe_first4_rule_30 | source_instruction_ids=none */
+!on(Block3, Block0) : clear(Block1) & holding(Block0) & on(Block1, Block2) & on(Block2, Block3) & on(Block3, Block4) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	stack(Block3, Block0).

/* plan=moose_blocks_probe_first4_rule_31 | source_instruction_ids=none */
+!on(Block0, Block4) : clear(Block1) & clear(Block2) & holding(Block0) & on(Block2, Block3) & on(Block3, Block4) <-
	stack(Block0, Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block0, Block1);
	stack(Block0, Block4).

/* plan=moose_blocks_probe_first4_rule_32 | source_instruction_ids=none */
+!on(Block3, Block2) : clear(Block0) & handempty & on(Block0, Block1) & on(Block1, Block2) & on(Block2, Block3) & ontable(Block3) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	pick_up(Block3);
	stack(Block3, Block2).

/* plan=moose_blocks_probe_first4_rule_33 | source_instruction_ids=none */
+!on(Block4, Block3) : clear(Block0) & clear(Block4) & handempty & on(Block0, Block1) & on(Block1, Block2) & on(Block2, Block3) & on(Block4, Block5) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block4, Block5);
	stack(Block4, Block3).

/* plan=moose_blocks_probe_first4_rule_34 | source_instruction_ids=none */
+!on(Block3, Block4) : clear(Block0) & clear(Block4) & handempty & on(Block0, Block1) & on(Block1, Block2) & on(Block2, Block3) & ontable(Block3) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	pick_up(Block3);
	stack(Block3, Block4).

/* plan=moose_blocks_probe_first4_rule_35 | source_instruction_ids=none */
+!on(Block3, Block0) : clear(Block0) & handempty & on(Block0, Block1) & on(Block1, Block2) & on(Block2, Block3) & on(Block3, Block4) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	stack(Block3, Block0).

/* plan=moose_blocks_probe_first4_rule_36 | source_instruction_ids=none */
+!on(Block0, Block4) : clear(Block0) & clear(Block2) & handempty & on(Block0, Block1) & on(Block1, Block3) & on(Block3, Block4) <-
	unstack(Block0, Block1);
	stack(Block0, Block2);
	unstack(Block1, Block3);
	put_down(Block1);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block0, Block2);
	stack(Block0, Block4).

/* plan=moose_blocks_probe_first4_rule_37 | source_instruction_ids=none */
+!on(Block4, Block1) : clear(Block0) & clear(Block2) & handempty & on(Block0, Block1) & on(Block2, Block3) & on(Block3, Block4) & ontable(Block4) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	put_down(Block3);
	pick_up(Block4);
	stack(Block4, Block1).

/* plan=moose_blocks_probe_first4_rule_38 | source_instruction_ids=none */
+!on(Block1, Block4) : clear(Block1) & holding(Block0) & on(Block1, Block2) & on(Block2, Block3) & on(Block3, Block4) <-
	put_down(Block0);
	unstack(Block1, Block2);
	stack(Block1, Block0);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block1, Block0);
	stack(Block1, Block4).

/* plan=moose_blocks_probe_first4_rule_39 | source_instruction_ids=none */
+!on(Block4, Block3) : clear(Block1) & holding(Block0) & on(Block1, Block2) & on(Block2, Block3) & on(Block3, Block4) & ontable(Block4) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	put_down(Block3);
	pick_up(Block4);
	stack(Block4, Block3).

/* plan=moose_blocks_probe_first4_rule_40 | source_instruction_ids=none */
+!on(Block5, Block2) : clear(Block1) & clear(Block3) & holding(Block0) & on(Block1, Block2) & on(Block3, Block4) & on(Block4, Block5) & ontable(Block5) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block4, Block5);
	put_down(Block4);
	pick_up(Block5);
	stack(Block5, Block2).

/* plan=moose_blocks_probe_first4_rule_41 | source_instruction_ids=none */
+!on(Block4, Block5) : clear(Block1) & clear(Block5) & holding(Block0) & on(Block1, Block2) & on(Block2, Block3) & on(Block3, Block4) & ontable(Block4) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	put_down(Block3);
	pick_up(Block4);
	stack(Block4, Block5).

/* plan=moose_blocks_probe_first4_rule_42 | source_instruction_ids=none */
+!on(Block0, Block5) : clear(Block1) & clear(Block2) & holding(Block0) & on(Block2, Block3) & on(Block3, Block4) & on(Block4, Block5) <-
	stack(Block0, Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block4, Block5);
	put_down(Block4);
	unstack(Block0, Block1);
	stack(Block0, Block5).

/* plan=moose_blocks_probe_first4_rule_43 | source_instruction_ids=none */
+!on(Block4, Block5) : clear(Block0) & clear(Block5) & handempty & on(Block0, Block1) & on(Block1, Block2) & on(Block2, Block3) & on(Block3, Block4) & ontable(Block4) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	put_down(Block3);
	pick_up(Block4);
	stack(Block4, Block5).

/* plan=moose_blocks_probe_first4_rule_44 | source_instruction_ids=none */
+!on(Block0, Block5) : clear(Block0) & clear(Block2) & handempty & on(Block0, Block1) & on(Block1, Block3) & on(Block3, Block4) & on(Block4, Block5) <-
	unstack(Block0, Block1);
	stack(Block0, Block2);
	unstack(Block1, Block3);
	put_down(Block1);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block4, Block5);
	put_down(Block4);
	unstack(Block0, Block2);
	stack(Block0, Block5).

/* plan=moose_blocks_probe_first4_rule_45 | source_instruction_ids=none */
+!on(Block5, Block2) : clear(Block0) & clear(Block3) & handempty & on(Block0, Block1) & on(Block1, Block2) & on(Block3, Block4) & on(Block4, Block5) & ontable(Block5) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block4, Block5);
	put_down(Block4);
	pick_up(Block5);
	stack(Block5, Block2).

/* plan=moose_blocks_probe_first4_rule_46 | source_instruction_ids=none */
+!on(Block5, Block1) : clear(Block0) & clear(Block2) & handempty & on(Block0, Block1) & on(Block2, Block3) & on(Block3, Block4) & on(Block4, Block5) & ontable(Block5) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block4, Block5);
	put_down(Block4);
	pick_up(Block5);
	stack(Block5, Block1).

/* plan=moose_blocks_probe_first4_rule_47 | source_instruction_ids=none */
+!on(Block1, Block4) : clear(Block0) & handempty & on(Block0, Block1) & on(Block1, Block2) & on(Block2, Block3) & on(Block3, Block4) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	stack(Block1, Block0);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block1, Block0);
	stack(Block1, Block4).

/* plan=moose_blocks_probe_first4_rule_48 | source_instruction_ids=none */
+!on(Block4, Block3) : clear(Block0) & handempty & on(Block0, Block1) & on(Block1, Block2) & on(Block2, Block3) & on(Block3, Block4) & ontable(Block4) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	put_down(Block3);
	pick_up(Block4);
	stack(Block4, Block3).

/* plan=moose_blocks_probe_first4_rule_49 | source_instruction_ids=none */
+!on(Block5, Block6) : clear(Block1) & clear(Block6) & holding(Block0) & on(Block1, Block2) & on(Block2, Block3) & on(Block3, Block4) & on(Block4, Block5) & ontable(Block5) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block4, Block5);
	put_down(Block4);
	pick_up(Block5);
	stack(Block5, Block6).

/* plan=moose_blocks_probe_first4_rule_50 | source_instruction_ids=none */
+!on(Block6, Block2) : clear(Block1) & clear(Block3) & holding(Block0) & on(Block1, Block2) & on(Block3, Block4) & on(Block4, Block5) & on(Block5, Block6) & ontable(Block6) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block4, Block5);
	put_down(Block4);
	unstack(Block5, Block6);
	put_down(Block5);
	pick_up(Block6);
	stack(Block6, Block2).

/* plan=moose_blocks_probe_first4_rule_51 | source_instruction_ids=none */
+!on(Block2, Block5) : clear(Block1) & holding(Block0) & on(Block1, Block2) & on(Block2, Block3) & on(Block3, Block4) & on(Block4, Block5) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	stack(Block2, Block1);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block4, Block5);
	put_down(Block4);
	unstack(Block2, Block1);
	stack(Block2, Block5).

/* plan=moose_blocks_probe_first4_rule_52 | source_instruction_ids=none */
+!on(Block6, Block3) : clear(Block1) & clear(Block4) & holding(Block0) & on(Block1, Block2) & on(Block2, Block3) & on(Block4, Block5) & on(Block5, Block6) & ontable(Block6) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block4, Block5);
	put_down(Block4);
	unstack(Block5, Block6);
	put_down(Block5);
	pick_up(Block6);
	stack(Block6, Block3).

/* plan=moose_blocks_probe_first4_rule_53 | source_instruction_ids=none */
+!on(Block1, Block6) : clear(Block1) & clear(Block3) & holding(Block0) & on(Block1, Block2) & on(Block2, Block4) & on(Block4, Block5) & on(Block5, Block6) <-
	put_down(Block0);
	unstack(Block1, Block2);
	stack(Block1, Block3);
	unstack(Block2, Block4);
	put_down(Block2);
	unstack(Block4, Block5);
	put_down(Block4);
	unstack(Block5, Block6);
	put_down(Block5);
	unstack(Block1, Block3);
	stack(Block1, Block6).

/* plan=moose_blocks_probe_first4_rule_54 | source_instruction_ids=none */
+!on(Block1, Block6) : clear(Block0) & clear(Block3) & handempty & on(Block0, Block1) & on(Block1, Block2) & on(Block2, Block4) & on(Block4, Block5) & on(Block5, Block6) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	stack(Block1, Block3);
	unstack(Block2, Block4);
	put_down(Block2);
	unstack(Block4, Block5);
	put_down(Block4);
	unstack(Block5, Block6);
	put_down(Block5);
	unstack(Block1, Block3);
	stack(Block1, Block6).

/* plan=moose_blocks_probe_first4_rule_55 | source_instruction_ids=none */
+!on(Block5, Block6) : clear(Block0) & clear(Block6) & handempty & on(Block0, Block1) & on(Block1, Block2) & on(Block2, Block3) & on(Block3, Block4) & on(Block4, Block5) & ontable(Block5) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block4, Block5);
	put_down(Block4);
	pick_up(Block5);
	stack(Block5, Block6).

/* plan=moose_blocks_probe_first4_rule_56 | source_instruction_ids=none */
+!on(Block6, Block3) : clear(Block0) & clear(Block2) & handempty & on(Block0, Block1) & on(Block1, Block4) & on(Block2, Block3) & on(Block4, Block5) & on(Block5, Block6) & ontable(Block6) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block1, Block4);
	put_down(Block1);
	unstack(Block4, Block5);
	put_down(Block4);
	unstack(Block5, Block6);
	put_down(Block5);
	pick_up(Block6);
	stack(Block6, Block3).

/* plan=moose_blocks_probe_first4_rule_57 | source_instruction_ids=none */
+!on(Block2, Block5) : clear(Block0) & handempty & on(Block0, Block1) & on(Block1, Block2) & on(Block2, Block3) & on(Block3, Block4) & on(Block4, Block5) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	stack(Block2, Block1);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block4, Block5);
	put_down(Block4);
	unstack(Block2, Block1);
	stack(Block2, Block5).

/* plan=moose_blocks_probe_first4_rule_58 | source_instruction_ids=none */
+!on(Block6, Block3) : clear(Block0) & clear(Block4) & handempty & on(Block0, Block1) & on(Block1, Block2) & on(Block2, Block3) & on(Block4, Block5) & on(Block5, Block6) & ontable(Block6) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block4, Block5);
	put_down(Block4);
	unstack(Block5, Block6);
	put_down(Block5);
	pick_up(Block6);
	stack(Block6, Block3).

/* plan=moose_blocks_probe_first4_rule_59 | source_instruction_ids=none */
+!on(Block7, Block4) : clear(Block1) & clear(Block5) & holding(Block0) & on(Block1, Block2) & on(Block2, Block3) & on(Block3, Block4) & on(Block5, Block6) & on(Block6, Block7) & ontable(Block7) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block5, Block6);
	put_down(Block5);
	unstack(Block6, Block7);
	put_down(Block6);
	pick_up(Block7);
	stack(Block7, Block4).

/* plan=moose_blocks_probe_first4_rule_60 | source_instruction_ids=none */
+!on(Block6, Block7) : clear(Block1) & clear(Block7) & holding(Block0) & on(Block1, Block2) & on(Block2, Block3) & on(Block3, Block4) & on(Block4, Block5) & on(Block5, Block6) & ontable(Block6) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block4, Block5);
	put_down(Block4);
	unstack(Block5, Block6);
	put_down(Block5);
	pick_up(Block6);
	stack(Block6, Block7).

/* plan=moose_blocks_probe_first4_rule_61 | source_instruction_ids=none */
+!on(Block2, Block7) : clear(Block1) & clear(Block4) & holding(Block0) & on(Block1, Block2) & on(Block2, Block3) & on(Block3, Block5) & on(Block5, Block6) & on(Block6, Block7) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	stack(Block2, Block4);
	unstack(Block3, Block5);
	put_down(Block3);
	unstack(Block5, Block6);
	put_down(Block5);
	unstack(Block6, Block7);
	put_down(Block6);
	unstack(Block2, Block4);
	stack(Block2, Block7).

/* plan=moose_blocks_probe_first4_rule_62 | source_instruction_ids=none */
+!on(Block7, Block4) : clear(Block1) & clear(Block3) & holding(Block0) & on(Block1, Block2) & on(Block2, Block5) & on(Block3, Block4) & on(Block5, Block6) & on(Block6, Block7) & ontable(Block7) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block2, Block5);
	put_down(Block2);
	unstack(Block5, Block6);
	put_down(Block5);
	unstack(Block6, Block7);
	put_down(Block6);
	pick_up(Block7);
	stack(Block7, Block4).

/* plan=moose_blocks_probe_first4_rule_63 | source_instruction_ids=none */
+!on(Block7, Block4) : clear(Block0) & clear(Block2) & handempty & on(Block0, Block1) & on(Block1, Block4) & on(Block2, Block3) & on(Block3, Block5) & on(Block5, Block6) & on(Block6, Block7) & ontable(Block7) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block1, Block4);
	put_down(Block1);
	unstack(Block3, Block5);
	put_down(Block3);
	unstack(Block5, Block6);
	put_down(Block5);
	unstack(Block6, Block7);
	put_down(Block6);
	pick_up(Block7);
	stack(Block7, Block4).

/* plan=moose_blocks_probe_first4_rule_64 | source_instruction_ids=none */
+!on(Block2, Block7) : clear(Block0) & clear(Block4) & handempty & on(Block0, Block1) & on(Block1, Block2) & on(Block2, Block3) & on(Block3, Block5) & on(Block5, Block6) & on(Block6, Block7) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	stack(Block2, Block4);
	unstack(Block3, Block5);
	put_down(Block3);
	unstack(Block5, Block6);
	put_down(Block5);
	unstack(Block6, Block7);
	put_down(Block6);
	unstack(Block2, Block4);
	stack(Block2, Block7).

/* plan=moose_blocks_probe_first4_rule_65 | source_instruction_ids=none */
+!on(Block6, Block7) : clear(Block0) & clear(Block7) & handempty & on(Block0, Block1) & on(Block1, Block2) & on(Block2, Block3) & on(Block3, Block4) & on(Block4, Block5) & on(Block5, Block6) & ontable(Block6) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block4, Block5);
	put_down(Block4);
	unstack(Block5, Block6);
	put_down(Block5);
	pick_up(Block6);
	stack(Block6, Block7).

/* plan=moose_blocks_probe_first4_rule_66 | source_instruction_ids=none */
+!on(Block7, Block4) : clear(Block0) & clear(Block5) & handempty & on(Block0, Block1) & on(Block1, Block2) & on(Block2, Block3) & on(Block3, Block4) & on(Block5, Block6) & on(Block6, Block7) & ontable(Block7) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block5, Block6);
	put_down(Block5);
	unstack(Block6, Block7);
	put_down(Block6);
	pick_up(Block7);
	stack(Block7, Block4).

/* plan=moose_blocks_probe_first4_rule_67 | source_instruction_ids=none */
+!on(Block7, Block8) : clear(Block1) & clear(Block8) & holding(Block0) & on(Block1, Block2) & on(Block2, Block3) & on(Block3, Block4) & on(Block4, Block5) & on(Block5, Block6) & on(Block6, Block7) & ontable(Block7) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block4, Block5);
	put_down(Block4);
	unstack(Block5, Block6);
	put_down(Block5);
	unstack(Block6, Block7);
	put_down(Block6);
	pick_up(Block7);
	stack(Block7, Block8).

/* plan=moose_blocks_probe_first4_rule_68 | source_instruction_ids=none */
+!on(Block8, Block5) : clear(Block1) & clear(Block6) & holding(Block0) & on(Block1, Block2) & on(Block2, Block3) & on(Block3, Block4) & on(Block4, Block5) & on(Block6, Block7) & on(Block7, Block8) & ontable(Block8) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block4, Block5);
	put_down(Block4);
	unstack(Block6, Block7);
	put_down(Block6);
	unstack(Block7, Block8);
	put_down(Block7);
	pick_up(Block8);
	stack(Block8, Block5).

/* plan=moose_blocks_probe_first4_rule_69 | source_instruction_ids=none */
+!on(Block8, Block6) : clear(Block0) & clear(Block2) & handempty & on(Block0, Block1) & on(Block1, Block7) & on(Block2, Block3) & on(Block3, Block4) & on(Block4, Block5) & on(Block5, Block6) & on(Block7, Block8) & ontable(Block8) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block4, Block5);
	put_down(Block4);
	unstack(Block5, Block6);
	put_down(Block5);
	unstack(Block1, Block7);
	put_down(Block1);
	unstack(Block7, Block8);
	put_down(Block7);
	pick_up(Block8);
	stack(Block8, Block6).

/* plan=moose_blocks_probe_first4_rule_70 | source_instruction_ids=none */
+!on(Block8, Block1) : clear(Block0) & clear(Block2) & handempty & on(Block0, Block1) & on(Block2, Block3) & on(Block3, Block4) & on(Block4, Block5) & on(Block5, Block6) & on(Block6, Block7) & on(Block7, Block8) & ontable(Block8) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block4, Block5);
	put_down(Block4);
	unstack(Block5, Block6);
	put_down(Block5);
	unstack(Block6, Block7);
	put_down(Block6);
	unstack(Block7, Block8);
	put_down(Block7);
	pick_up(Block8);
	stack(Block8, Block1).

/* plan=moose_blocks_probe_first4_rule_71 | source_instruction_ids=none */
+!on(Block9, Block7) : clear(Block1) & clear(Block3) & holding(Block0) & on(Block1, Block2) & on(Block2, Block8) & on(Block3, Block4) & on(Block4, Block5) & on(Block5, Block6) & on(Block6, Block7) & on(Block8, Block9) & ontable(Block9) <-
	put_down(Block0);
	unstack(Block1, Block2);
	put_down(Block1);
	unstack(Block3, Block4);
	put_down(Block3);
	unstack(Block4, Block5);
	put_down(Block4);
	unstack(Block5, Block6);
	put_down(Block5);
	unstack(Block6, Block7);
	put_down(Block6);
	unstack(Block2, Block8);
	put_down(Block2);
	unstack(Block8, Block9);
	put_down(Block8);
	pick_up(Block9);
	stack(Block9, Block7).

/* plan=moose_blocks_probe_first4_rule_72 | source_instruction_ids=none */
+!on(Block9, Block7) : clear(Block0) & clear(Block2) & handempty & on(Block0, Block1) & on(Block1, Block4) & on(Block2, Block3) & on(Block3, Block8) & on(Block4, Block5) & on(Block5, Block6) & on(Block6, Block7) & on(Block8, Block9) & ontable(Block9) <-
	unstack(Block0, Block1);
	put_down(Block0);
	unstack(Block2, Block3);
	put_down(Block2);
	unstack(Block1, Block4);
	put_down(Block1);
	unstack(Block4, Block5);
	put_down(Block4);
	unstack(Block5, Block6);
	put_down(Block5);
	unstack(Block6, Block7);
	put_down(Block6);
	unstack(Block3, Block8);
	put_down(Block3);
	unstack(Block8, Block9);
	put_down(Block8);
	pick_up(Block9);
	stack(Block9, Block7).

/* plan=g_probe_p01_tower_progress_1 | source_instruction_ids=none */
+!g_probe_p01_tower : teg_state(g_probe_p01_tower, state_1) & not on(b4, b2) <-
	!on(b4, b2);
	-teg_state(g_probe_p01_tower, state_1);
	+teg_state(g_probe_p01_tower, state_2);
	!g_probe_p01_tower.

/* plan=g_probe_p01_tower_progress_2 | source_instruction_ids=none */
+!g_probe_p01_tower : teg_state(g_probe_p01_tower, state_2) & not on(b1, b4) <-
	!on(b1, b4);
	-teg_state(g_probe_p01_tower, state_2);
	+teg_state(g_probe_p01_tower, state_3);
	!g_probe_p01_tower.

/* plan=g_probe_p01_tower_progress_3 | source_instruction_ids=none */
+!g_probe_p01_tower : teg_state(g_probe_p01_tower, state_3) & not on(b3, b1) <-
	!on(b3, b1);
	-teg_state(g_probe_p01_tower, state_3);
	+teg_state(g_probe_p01_tower, state_4);
	!g_probe_p01_tower.

/* plan=g_probe_p01_tower_accepting_1 | source_instruction_ids=none */
+!g_probe_p01_tower : teg_state(g_probe_p01_tower, state_4) <-
	true.

/* plan=g_probe_p02_tower_progress_1 | source_instruction_ids=none */
+!g_probe_p02_tower : teg_state(g_probe_p02_tower, state_1) & not on(b3, b5) <-
	!on(b3, b5);
	-teg_state(g_probe_p02_tower, state_1);
	+teg_state(g_probe_p02_tower, state_2);
	!g_probe_p02_tower.

/* plan=g_probe_p02_tower_progress_2 | source_instruction_ids=none */
+!g_probe_p02_tower : teg_state(g_probe_p02_tower, state_2) & not on(b6, b3) <-
	!on(b6, b3);
	-teg_state(g_probe_p02_tower, state_2);
	+teg_state(g_probe_p02_tower, state_3);
	!g_probe_p02_tower.

/* plan=g_probe_p02_tower_progress_3 | source_instruction_ids=none */
+!g_probe_p02_tower : teg_state(g_probe_p02_tower, state_3) & not on(b1, b6) <-
	!on(b1, b6);
	-teg_state(g_probe_p02_tower, state_3);
	+teg_state(g_probe_p02_tower, state_4);
	!g_probe_p02_tower.

/* plan=g_probe_p02_tower_progress_4 | source_instruction_ids=none */
+!g_probe_p02_tower : teg_state(g_probe_p02_tower, state_4) & not on(b2, b1) <-
	!on(b2, b1);
	-teg_state(g_probe_p02_tower, state_4);
	+teg_state(g_probe_p02_tower, state_5);
	!g_probe_p02_tower.

/* plan=g_probe_p02_tower_progress_5 | source_instruction_ids=none */
+!g_probe_p02_tower : teg_state(g_probe_p02_tower, state_5) & not on(b4, b2) <-
	!on(b4, b2);
	-teg_state(g_probe_p02_tower, state_5);
	+teg_state(g_probe_p02_tower, state_6);
	!g_probe_p02_tower.

/* plan=g_probe_p02_tower_progress_6 | source_instruction_ids=none */
+!g_probe_p02_tower : teg_state(g_probe_p02_tower, state_6) & not on(b7, b4) <-
	!on(b7, b4);
	-teg_state(g_probe_p02_tower, state_6);
	+teg_state(g_probe_p02_tower, state_7);
	!g_probe_p02_tower.

/* plan=g_probe_p02_tower_accepting_1 | source_instruction_ids=none */
+!g_probe_p02_tower : teg_state(g_probe_p02_tower, state_7) <-
	true.
