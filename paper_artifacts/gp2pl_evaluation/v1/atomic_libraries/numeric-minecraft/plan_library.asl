/* Generated AgentSpeak(L) Plan Library */
/* Domain: numeric-minecraft */

+!air_cell(X) : air_cell(X) <-
	true.

+!pogo_sticks_to_make(0) : pogo_sticks_to_make(N) & N == 0 <-
	true.

+!position(X) : position(X) <-
	true.

+!air_cell(X) : obj_tp(X, cell) & position(X) & tree_cell(X) <-
	break(X).

+!pogo_sticks_to_make(0) : position(crafting_table) & count_planks_in_inventory(M) & M >= 2 & count_sack_polyisoprene_pellets_in_inventory(Q) & Q >= 1 & count_stick_in_inventory(K) & K >= 4 & pogo_sticks_to_make(N) & N > 0 <-
	craft_wooden_pogo.

+!pogo_sticks_to_make(0) : position(crafting_table) & count_planks_in_inventory(M) & M >= 4 & count_sack_polyisoprene_pellets_in_inventory(Q) & Q >= 1 & count_stick_in_inventory(K) & K >= 0 & pogo_sticks_to_make(N) & N > 0 <-
	craft_stick;
	craft_wooden_pogo.

+!pogo_sticks_to_make(0) : position(crafting_table) & count_log_in_inventory(M) & M >= 1 & count_planks_in_inventory(K) & K >= 0 & count_sack_polyisoprene_pellets_in_inventory(R) & R >= 1 & count_stick_in_inventory(Q) & Q >= 0 & pogo_sticks_to_make(N) & N > 0 <-
	craft_plank;
	craft_stick;
	craft_wooden_pogo.

+!pogo_sticks_to_make(0) : count_log_in_inventory(M) & M >= 1 & count_planks_in_inventory(K) & K >= 0 & count_sack_polyisoprene_pellets_in_inventory(R) & R >= 1 & count_stick_in_inventory(Q) & Q >= 0 & pogo_sticks_to_make(N) & N > 0 & position(X) & obj_tp(X, cell) & X \== crafting_table <-
	tp_to(X, crafting_table);
	craft_plank;
	craft_stick;
	craft_wooden_pogo.

+!pogo_sticks_to_make(0) : count_log_in_inventory(M) & M >= 0 & count_planks_in_inventory(K) & K >= 0 & count_sack_polyisoprene_pellets_in_inventory(R) & R >= 1 & count_stick_in_inventory(Q) & Q >= 0 & pogo_sticks_to_make(N) & N > 0 & position(X) & obj_tp(X, cell) & X \== crafting_table & tree_cell(X) <-
	break(X);
	tp_to(X, crafting_table);
	craft_plank;
	craft_stick;
	craft_wooden_pogo.

+!pogo_sticks_to_make(0) : count_log_in_inventory(K) & K >= 0 & count_planks_in_inventory(Q) & Q >= 0 & count_sack_polyisoprene_pellets_in_inventory(N0) & N0 >= 0 & count_stick_in_inventory(R) & R >= 0 & count_tree_tap_in_inventory(M) & M >= 1 & pogo_sticks_to_make(N) & N > 0 & position(X) & obj_tp(X, cell) & X \== crafting_table & tree_cell(X) <-
	place_tree_tap(X);
	break(X);
	tp_to(X, crafting_table);
	craft_plank;
	craft_stick;
	craft_wooden_pogo.

+!pogo_sticks_to_make(0) : position(crafting_table) & count_log_in_inventory(K) & K >= 0 & count_planks_in_inventory(Q) & Q >= 0 & count_sack_polyisoprene_pellets_in_inventory(N0) & N0 >= 0 & count_stick_in_inventory(R) & R >= 0 & count_tree_tap_in_inventory(M) & M >= 1 & pogo_sticks_to_make(N) & N > 0 & tree_cell(X) & obj_tp(X, cell) & X \== crafting_table <-
	tp_to(crafting_table, X);
	place_tree_tap(X);
	break(X);
	tp_to(X, crafting_table);
	craft_plank;
	craft_stick;
	craft_wooden_pogo.

+!pogo_sticks_to_make(0) : position(crafting_table) & count_log_in_inventory(R) & R >= 0 & count_planks_in_inventory(M) & M >= 5 & count_sack_polyisoprene_pellets_in_inventory(N0) & N0 >= 0 & count_stick_in_inventory(K) & K >= 1 & count_tree_tap_in_inventory(Q) & Q >= 0 & pogo_sticks_to_make(N) & N > 0 & tree_cell(X) & obj_tp(X, cell) & X \== crafting_table <-
	craft_tree_tap;
	tp_to(crafting_table, X);
	place_tree_tap(X);
	break(X);
	tp_to(X, crafting_table);
	craft_plank;
	craft_stick;
	craft_wooden_pogo.

+!pogo_sticks_to_make(0) : position(crafting_table) & count_log_in_inventory(M) & M >= 1 & count_planks_in_inventory(K) & K >= 1 & count_sack_polyisoprene_pellets_in_inventory(N0) & N0 >= 0 & count_stick_in_inventory(Q) & Q >= 1 & count_tree_tap_in_inventory(R) & R >= 0 & pogo_sticks_to_make(N) & N > 0 & tree_cell(X) & obj_tp(X, cell) & X \== crafting_table <-
	craft_plank;
	craft_tree_tap;
	tp_to(crafting_table, X);
	place_tree_tap(X);
	break(X);
	tp_to(X, crafting_table);
	craft_plank;
	craft_stick;
	craft_wooden_pogo.

+!pogo_sticks_to_make(0) : count_log_in_inventory(M) & M >= 1 & count_planks_in_inventory(K) & K >= 1 & count_sack_polyisoprene_pellets_in_inventory(N0) & N0 >= 0 & count_stick_in_inventory(Q) & Q >= 1 & count_tree_tap_in_inventory(R) & R >= 0 & pogo_sticks_to_make(N) & N > 0 & position(X) & obj_tp(X, cell) & X \== crafting_table & tree_cell(Y) & obj_tp(Y, cell) & X \== Y & Y \== crafting_table <-
	tp_to(X, crafting_table);
	craft_plank;
	craft_tree_tap;
	tp_to(crafting_table, Y);
	place_tree_tap(Y);
	break(Y);
	tp_to(Y, crafting_table);
	craft_plank;
	craft_stick;
	craft_wooden_pogo.

+!pogo_sticks_to_make(0) : count_log_in_inventory(M) & M >= 0 & count_planks_in_inventory(K) & K >= 1 & count_sack_polyisoprene_pellets_in_inventory(N0) & N0 >= 0 & count_stick_in_inventory(Q) & Q >= 1 & count_tree_tap_in_inventory(R) & R >= 0 & pogo_sticks_to_make(N) & N > 0 & position(X) & obj_tp(X, cell) & X \== crafting_table & tree_cell(X) & tree_cell(Y) & obj_tp(Y, cell) & X \== Y & Y \== crafting_table <-
	break(X);
	tp_to(X, crafting_table);
	craft_plank;
	craft_tree_tap;
	tp_to(crafting_table, Y);
	place_tree_tap(Y);
	break(Y);
	tp_to(Y, crafting_table);
	craft_plank;
	craft_stick;
	craft_wooden_pogo.

+!pogo_sticks_to_make(0) : count_log_in_inventory(K) & K >= 0 & count_planks_in_inventory(M) & M >= 3 & count_sack_polyisoprene_pellets_in_inventory(N0) & N0 >= 0 & count_stick_in_inventory(Q) & Q >= -3 & count_tree_tap_in_inventory(R) & R >= 0 & pogo_sticks_to_make(N) & N > 0 & position(X) & obj_tp(X, cell) & X \== crafting_table & tree_cell(X) & tree_cell(Y) & obj_tp(Y, cell) & X \== Y & Y \== crafting_table <-
	craft_stick;
	break(X);
	tp_to(X, crafting_table);
	craft_plank;
	craft_tree_tap;
	tp_to(crafting_table, Y);
	place_tree_tap(Y);
	break(Y);
	tp_to(Y, crafting_table);
	craft_plank;
	craft_stick;
	craft_wooden_pogo.

+!pogo_sticks_to_make(0) : count_log_in_inventory(M) & M >= 1 & count_planks_in_inventory(K) & K >= -1 & count_sack_polyisoprene_pellets_in_inventory(N0) & N0 >= 0 & count_stick_in_inventory(Q) & Q >= -3 & count_tree_tap_in_inventory(R) & R >= 0 & pogo_sticks_to_make(N) & N > 0 & position(X) & obj_tp(X, cell) & X \== crafting_table & tree_cell(X) & tree_cell(Y) & obj_tp(Y, cell) & X \== Y & Y \== crafting_table <-
	craft_plank;
	craft_stick;
	break(X);
	tp_to(X, crafting_table);
	craft_plank;
	craft_tree_tap;
	tp_to(crafting_table, Y);
	place_tree_tap(Y);
	break(Y);
	tp_to(Y, crafting_table);
	craft_plank;
	craft_stick;
	craft_wooden_pogo.

+!pogo_sticks_to_make(0) : count_log_in_inventory(M) & M >= 1 & count_planks_in_inventory(K) & K >= -1 & count_sack_polyisoprene_pellets_in_inventory(N0) & N0 >= 0 & count_stick_in_inventory(Q) & Q >= -3 & count_tree_tap_in_inventory(R) & R >= 0 & pogo_sticks_to_make(N) & N > 0 & position(X) & obj_tp(X, cell) & X \== crafting_table & tree_cell(Y) & obj_tp(Y, cell) & X \== Y & Y \== crafting_table & tree_cell(Z) & obj_tp(Z, cell) & X \== Z & Y \== Z & Z \== crafting_table <-
	tp_to(X, Y);
	craft_plank;
	craft_stick;
	break(Y);
	tp_to(Y, crafting_table);
	craft_plank;
	craft_tree_tap;
	tp_to(crafting_table, Z);
	place_tree_tap(Z);
	break(Z);
	tp_to(Z, crafting_table);
	craft_plank;
	craft_stick;
	craft_wooden_pogo.

+!pogo_sticks_to_make(0) : count_log_in_inventory(M) & M >= 0 & count_planks_in_inventory(K) & K >= -1 & count_sack_polyisoprene_pellets_in_inventory(N0) & N0 >= 0 & count_stick_in_inventory(Q) & Q >= -3 & count_tree_tap_in_inventory(R) & R >= 0 & pogo_sticks_to_make(N) & N > 0 & position(X) & obj_tp(X, cell) & X \== crafting_table & tree_cell(X) & tree_cell(Y) & obj_tp(Y, cell) & X \== Y & Y \== crafting_table & tree_cell(Z) & obj_tp(Z, cell) & X \== Z & Y \== Z & Z \== crafting_table <-
	break(X);
	tp_to(X, Y);
	craft_plank;
	craft_stick;
	break(Y);
	tp_to(Y, crafting_table);
	craft_plank;
	craft_tree_tap;
	tp_to(crafting_table, Z);
	place_tree_tap(Z);
	break(Z);
	tp_to(Z, crafting_table);
	craft_plank;
	craft_stick;
	craft_wooden_pogo.

+!pogo_sticks_to_make(0) : count_log_in_inventory(M) & M >= 0 & count_planks_in_inventory(K) & K >= -1 & count_sack_polyisoprene_pellets_in_inventory(N0) & N0 >= 0 & count_stick_in_inventory(Q) & Q >= -3 & count_tree_tap_in_inventory(R) & R >= 0 & pogo_sticks_to_make(N) & N > 0 & position(X) & obj_tp(X, cell) & X \== crafting_table & tree_cell(A) & obj_tp(A, cell) & A \== X & A \== crafting_table & tree_cell(Y) & obj_tp(Y, cell) & A \== Y & X \== Y & Y \== crafting_table & tree_cell(Z) & obj_tp(Z, cell) & A \== Z & X \== Z & Y \== Z & Z \== crafting_table <-
	tp_to(X, Y);
	break(Y);
	tp_to(Y, Z);
	craft_plank;
	craft_stick;
	break(Z);
	tp_to(Z, crafting_table);
	craft_plank;
	craft_tree_tap;
	tp_to(crafting_table, A);
	place_tree_tap(A);
	break(A);
	tp_to(A, crafting_table);
	craft_plank;
	craft_stick;
	craft_wooden_pogo.

+!position(X) : obj_tp(X, cell) & not position(X) & position(Y) & obj_tp(Y, cell) & X \== Y <-
	tp_to(Y, X).

+!air_cell(X) : obj_tp(X, cell) & not position(X) <-
	!position(X);
	!air_cell(X).
