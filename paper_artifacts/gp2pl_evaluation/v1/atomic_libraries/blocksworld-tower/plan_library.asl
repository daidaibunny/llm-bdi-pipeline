/* Generated AgentSpeak(L) Plan Library */
/* Domain: blocksworld-tower */

+!clear(X) : clear(X) <-
	true.

+!handempty : handempty <-
	true.

+!holding(X) : holding(X) <-
	true.

+!on(X, Y) : on(X, Y) <-
	true.

+!ontable(X) : ontable(X) <-
	true.

+!clear(X) : obj_tp(X, block) & holding(X) <-
	put_down(X).

+!clear(X) : obj_tp(X, block) & handempty & on(Y, X) & obj_tp(Y, block) & X \== Y & clear(Y) <-
	unstack(Y, X).

+!clear(X) : obj_tp(X, block) & handempty & on(Y, X) & obj_tp(Y, block) & clear(Y) <-
	unstack(Y, X);
	put_down(Y).

+!handempty : holding(X) & obj_tp(X, block) <-
	put_down(X).

+!holding(X) : obj_tp(X, block) & clear(X) & ontable(X) & handempty <-
	pick_up(X).

+!holding(X) : obj_tp(X, block) & clear(X) & handempty & on(X, Y) & obj_tp(Y, block) <-
	unstack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & clear(Y) & holding(X) <-
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & clear(Y) & ontable(X) & handempty <-
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & clear(Y) & handempty & on(X, Z) & obj_tp(Z, block) & Y \== Z <-
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & clear(Y) & handempty & on(X, Z) & obj_tp(Z, block) <-
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & clear(Y) & ontable(X) & handempty <-
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & clear(Y) & ontable(X) & holding(Z) & obj_tp(Z, block) & X \== Z <-
	put_down(Z);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & clear(Y) & on(X, A) & obj_tp(A, block) & holding(Z) & obj_tp(Z, block) & X \== Z <-
	put_down(Z);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & holding(Y) & ontable(X) <-
	put_down(Y);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & holding(Y) & on(X, Z) & obj_tp(Z, block) <-
	put_down(Y);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & handempty & on(X, A) & obj_tp(A, block) & on(Z, X) & obj_tp(Z, block) & X \== Z & clear(Z) <-
	unstack(Z, X);
	put_down(Z);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & ontable(X) & handempty & on(Z, Y) & obj_tp(Z, block) & X \== Z & clear(Z) <-
	unstack(Z, Y);
	put_down(Z);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & ontable(X) & handempty & on(Z, X) & obj_tp(Z, block) & X \== Z & clear(Z) <-
	unstack(Z, X);
	put_down(Z);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(Y, X) & clear(Y) & handempty & on(X, Z) & obj_tp(Z, block) <-
	unstack(Y, X);
	put_down(Y);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & handempty & on(X, A) & obj_tp(A, block) & on(Z, Y) & obj_tp(Z, block) & X \== Z & clear(Z) <-
	unstack(Z, Y);
	put_down(Z);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(Y, X) & clear(Y) & ontable(X) & handempty <-
	unstack(Y, X);
	put_down(Y);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & holding(X) & on(Z, Y) & obj_tp(Z, block) & X \== Z & clear(Z) <-
	put_down(X);
	unstack(Z, Y);
	put_down(Z);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & ontable(X) & on(A, X) & obj_tp(A, block) & A \== X & clear(A) & holding(Z) & obj_tp(Z, block) & A \== Z & X \== Z <-
	put_down(Z);
	unstack(A, X);
	put_down(A);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & on(A, Y) & obj_tp(A, block) & A \== X & clear(A) & on(X, B) & obj_tp(B, block) & holding(Z) & obj_tp(Z, block) & A \== Z & X \== Z <-
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	unstack(X, B);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & holding(Y) & ontable(X) & on(Z, X) & obj_tp(Z, block) & X \== Z & Y \== Z & clear(Z) <-
	put_down(Y);
	unstack(Z, X);
	put_down(Z);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & ontable(X) & on(A, Y) & obj_tp(A, block) & A \== X & clear(A) & holding(Z) & obj_tp(Z, block) & A \== Z & X \== Z <-
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(Y, X) & clear(Y) & on(X, A) & obj_tp(A, block) & holding(Z) & obj_tp(Z, block) & X \== Z & Y \== Z <-
	put_down(Z);
	unstack(Y, X);
	put_down(Y);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & holding(Y) & on(X, A) & obj_tp(A, block) & on(Z, X) & obj_tp(Z, block) & X \== Z & Y \== Z & clear(Z) <-
	put_down(Y);
	unstack(Z, X);
	put_down(Z);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & on(A, X) & obj_tp(A, block) & A \== X & clear(A) & on(X, B) & obj_tp(B, block) & holding(Z) & obj_tp(Z, block) & A \== Z & X \== Z <-
	put_down(Z);
	unstack(A, X);
	put_down(A);
	unstack(X, B);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & holding(X) & on(A, Y) & obj_tp(A, block) & A \== X & clear(A) & clear(Z) & obj_tp(Z, block) & A \== Z & X \== Z <-
	stack(X, Z);
	unstack(A, Y);
	put_down(A);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & handempty & on(A, X) & obj_tp(A, block) & A \== X & clear(A) & on(Z, Y) & obj_tp(Z, block) & A \== Z & X \== Z & clear(Z) <-
	unstack(Z, Y);
	put_down(Z);
	unstack(A, X);
	put_down(A);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & handempty & on(X, Z) & obj_tp(Z, block) & X \== Z & on(Z, Y) <-
	unstack(X, Z);
	put_down(X);
	unstack(Z, Y);
	put_down(Z);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & ontable(X) & handempty & on(A, Y) & obj_tp(A, block) & A \== X & on(Z, A) & obj_tp(Z, block) & A \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & handempty & on(A, X) & obj_tp(A, block) & A \== X & on(X, B) & obj_tp(B, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, X);
	put_down(A);
	unstack(X, B);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & ontable(X) & handempty & on(Y, Z) & obj_tp(Z, block) & X \== Z & Y \== Z & on(Z, X) <-
	unstack(Y, Z);
	put_down(Y);
	unstack(Z, X);
	put_down(Z);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & ontable(X) & handempty & on(A, X) & obj_tp(A, block) & A \== X & on(Z, A) & obj_tp(Z, block) & A \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, X);
	put_down(A);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & handempty & on(A, Y) & obj_tp(A, block) & A \== X & clear(A) & on(Z, X) & obj_tp(Z, block) & A \== Z & X \== Z & clear(Z) <-
	unstack(Z, X);
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & handempty & on(X, Z) & obj_tp(Z, block) & X \== Z & on(Z, Y) & clear(A) & obj_tp(A, block) & A \== X & A \== Z <-
	unstack(X, Z);
	stack(X, A);
	unstack(Z, Y);
	put_down(Z);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & handempty & on(A, Y) & obj_tp(A, block) & A \== X & on(X, B) & obj_tp(B, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	unstack(X, B);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & handempty & on(X, A) & obj_tp(A, block) & on(Y, Z) & obj_tp(Z, block) & X \== Z & Y \== Z & on(Z, X) <-
	unstack(Y, Z);
	put_down(Y);
	unstack(Z, X);
	put_down(Z);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(Y, X) & handempty & on(X, A) & obj_tp(A, block) & on(Z, Y) & obj_tp(Z, block) & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, Y);
	put_down(Z);
	unstack(Y, X);
	put_down(Y);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(Y, X) & on(A, Y) & obj_tp(A, block) & A \== X & A \== Y & clear(A) & on(X, B) & obj_tp(B, block) & holding(Z) & obj_tp(Z, block) & A \== Z & X \== Z & Y \== Z <-
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	unstack(Y, X);
	put_down(Y);
	unstack(X, B);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & holding(Y) & on(A, X) & obj_tp(A, block) & A \== X & A \== Y & on(X, B) & obj_tp(B, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & X \== Z & Y \== Z & clear(Z) <-
	put_down(Y);
	unstack(Z, A);
	put_down(Z);
	unstack(A, X);
	put_down(A);
	unstack(X, B);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & on(A, Y) & obj_tp(A, block) & A \== X & on(X, A) & clear(B) & obj_tp(B, block) & A \== B & B \== X & holding(Z) & obj_tp(Z, block) & A \== Z & X \== Z <-
	put_down(Z);
	unstack(X, A);
	stack(X, B);
	unstack(A, Y);
	put_down(A);
	unstack(X, B);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & on(A, X) & obj_tp(A, block) & A \== X & A \== Y & on(Y, A) & on(X, B) & obj_tp(B, block) & holding(Z) & obj_tp(Z, block) & A \== Z & X \== Z & Y \== Z <-
	put_down(Z);
	unstack(Y, A);
	put_down(Y);
	unstack(A, X);
	put_down(A);
	unstack(X, B);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & holding(X) & on(B, Y) & obj_tp(B, block) & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== X & clear(A) & clear(Z) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z <-
	stack(X, Z);
	unstack(A, B);
	put_down(A);
	unstack(B, Y);
	put_down(B);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & ontable(X) & on(A, X) & obj_tp(A, block) & A \== X & A \== Y & on(Y, A) & holding(Z) & obj_tp(Z, block) & A \== Z & X \== Z & Y \== Z <-
	put_down(Z);
	unstack(Y, A);
	put_down(Y);
	unstack(A, X);
	put_down(A);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & ontable(X) & on(B, Y) & obj_tp(B, block) & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== X & clear(A) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, Y);
	put_down(B);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & on(A, Y) & obj_tp(A, block) & A \== X & clear(A) & on(B, X) & obj_tp(B, block) & A \== B & B \== X & clear(B) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z <-
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	unstack(B, X);
	put_down(B);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & on(B, Y) & obj_tp(B, block) & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== X & clear(A) & on(X, C) & obj_tp(C, block) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, Y);
	put_down(B);
	unstack(X, C);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & holding(Y) & ontable(X) & on(A, X) & obj_tp(A, block) & A \== X & A \== Y & on(Z, A) & obj_tp(Z, block) & A \== Z & X \== Z & Y \== Z & clear(Z) <-
	put_down(Y);
	unstack(Z, A);
	put_down(Z);
	unstack(A, X);
	put_down(A);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & ontable(X) & on(B, X) & obj_tp(B, block) & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== X & clear(A) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, X);
	put_down(B);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & on(B, X) & obj_tp(B, block) & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== X & clear(A) & on(X, C) & obj_tp(C, block) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, X);
	put_down(B);
	unstack(X, C);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & on(A, X) & obj_tp(A, block) & A \== X & clear(A) & on(B, Y) & obj_tp(B, block) & A \== B & B \== X & clear(B) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z <-
	put_down(Z);
	unstack(A, X);
	put_down(A);
	unstack(B, Y);
	put_down(B);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & handempty & on(A, X) & obj_tp(A, block) & A \== X & A \== Y & on(X, B) & obj_tp(B, block) & on(Y, Z) & obj_tp(Z, block) & A \== Z & X \== Z & Y \== Z & on(Z, A) <-
	unstack(Y, Z);
	put_down(Y);
	unstack(Z, A);
	put_down(Z);
	unstack(A, X);
	put_down(A);
	unstack(X, B);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & handempty & on(B, Y) & obj_tp(B, block) & B \== X & on(X, Z) & obj_tp(Z, block) & B \== Z & X \== Z & on(Z, B) & clear(A) & obj_tp(A, block) & A \== B & A \== X & A \== Z <-
	unstack(X, Z);
	stack(X, A);
	unstack(Z, B);
	put_down(Z);
	unstack(B, Y);
	put_down(B);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & ontable(X) & handempty & on(B, X) & obj_tp(B, block) & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== X & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, X);
	put_down(B);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & handempty & on(B, X) & obj_tp(B, block) & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== X & clear(A) & on(Z, Y) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z & clear(Z) <-
	unstack(Z, Y);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, X);
	put_down(B);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & handempty & on(B, X) & obj_tp(B, block) & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== X & on(X, C) & obj_tp(C, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, X);
	put_down(B);
	unstack(X, C);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & handempty & on(B, Y) & obj_tp(B, block) & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== X & clear(A) & on(Z, X) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z & clear(Z) <-
	unstack(Z, X);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, Y);
	put_down(B);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & handempty & on(A, X) & obj_tp(A, block) & A \== X & A \== Y & on(Y, A) & on(Z, Y) & obj_tp(Z, block) & A \== Z & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, Y);
	put_down(Z);
	unstack(Y, A);
	put_down(Y);
	unstack(A, X);
	put_down(A);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(A, X) & obj_tp(A, block) & A \== X & A \== Y & on(Y, A) & on(X, B) & obj_tp(B, block) & on(Z, Y) & obj_tp(Z, block) & A \== Z & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, Y);
	put_down(Z);
	unstack(Y, A);
	put_down(Y);
	unstack(A, X);
	put_down(A);
	unstack(X, B);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & ontable(X) & handempty & on(B, Y) & obj_tp(B, block) & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== X & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, Y);
	put_down(B);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & ontable(X) & handempty & on(A, X) & obj_tp(A, block) & A \== X & A \== Y & on(Y, Z) & obj_tp(Z, block) & A \== Z & X \== Z & Y \== Z & on(Z, A) <-
	unstack(Y, Z);
	put_down(Y);
	unstack(Z, A);
	put_down(Z);
	unstack(A, X);
	put_down(A);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & handempty & on(A, X) & obj_tp(A, block) & A \== X & on(B, Y) & obj_tp(B, block) & A \== B & B \== X & clear(B) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(B, Y);
	put_down(B);
	unstack(A, X);
	put_down(A);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & handempty & on(B, Y) & obj_tp(B, block) & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== X & on(X, C) & obj_tp(C, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, Y);
	put_down(B);
	unstack(X, C);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(A, Y) & obj_tp(A, block) & A \== X & on(X, A) & on(Z, X) & obj_tp(Z, block) & A \== Z & X \== Z & clear(Z) & clear(B) & obj_tp(B, block) & A \== B & B \== X <-
	unstack(Z, X);
	put_down(Z);
	unstack(X, A);
	stack(X, B);
	unstack(A, Y);
	put_down(A);
	unstack(X, B);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(Y, X) & handempty & on(A, Y) & obj_tp(A, block) & A \== X & A \== Y & on(X, B) & obj_tp(B, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	unstack(Y, X);
	put_down(Y);
	unstack(X, B);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & handempty & on(A, Y) & obj_tp(A, block) & A \== X & on(B, X) & obj_tp(B, block) & A \== B & B \== X & clear(B) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(B, X);
	put_down(B);
	unstack(A, Y);
	put_down(A);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(Y, X) & on(B, Y) & obj_tp(B, block) & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== X & A \== Y & clear(A) & on(X, C) & obj_tp(C, block) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z & Y \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, Y);
	put_down(B);
	unstack(Y, X);
	put_down(Y);
	unstack(X, C);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & on(A, Y) & obj_tp(A, block) & A \== X & clear(A) & on(C, X) & obj_tp(C, block) & A \== C & C \== X & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== X & clear(B) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z <-
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, X);
	put_down(C);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & on(A, X) & obj_tp(A, block) & A \== X & clear(A) & on(C, Y) & obj_tp(C, block) & A \== C & C \== X & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== X & clear(B) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z <-
	put_down(Z);
	unstack(A, X);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, Y);
	put_down(C);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & holding(X) & on(C, Y) & obj_tp(C, block) & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== X & clear(A) & clear(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z <-
	stack(X, Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, Y);
	put_down(C);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & on(B, X) & obj_tp(B, block) & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== X & clear(A) & on(C, Y) & obj_tp(C, block) & A \== C & B \== C & C \== X & clear(C) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(C, Y);
	put_down(C);
	unstack(B, X);
	put_down(B);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & holding(Y) & ontable(X) & on(B, X) & obj_tp(B, block) & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== X & A \== Y & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z & Y \== Z & clear(Z) <-
	put_down(Y);
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, X);
	put_down(B);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & on(C, X) & obj_tp(C, block) & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== X & clear(A) & on(X, D) & obj_tp(D, block) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, X);
	put_down(C);
	unstack(X, D);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(A, X) & obj_tp(A, block) & A \== X & clear(A) & on(B, Y) & obj_tp(B, block) & A \== B & B \== X & on(X, B) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z <-
	put_down(Z);
	unstack(A, X);
	put_down(A);
	unstack(X, B);
	stack(X, Z);
	unstack(B, Y);
	put_down(B);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & on(C, Y) & obj_tp(C, block) & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== X & clear(A) & on(X, D) & obj_tp(D, block) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, Y);
	put_down(C);
	unstack(X, D);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & holding(Y) & on(B, X) & obj_tp(B, block) & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== X & A \== Y & on(X, C) & obj_tp(C, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z & Y \== Z & clear(Z) <-
	put_down(Y);
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, X);
	put_down(B);
	unstack(X, C);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & ontable(X) & on(C, X) & obj_tp(C, block) & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== X & clear(A) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, X);
	put_down(C);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(A, Y) & obj_tp(A, block) & A \== X & A \== Y & clear(A) & on(B, X) & obj_tp(B, block) & A \== B & B \== X & B \== Y & on(Y, B) & on(X, C) & obj_tp(C, block) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z & Y \== Z <-
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	unstack(Y, B);
	put_down(Y);
	unstack(B, X);
	put_down(B);
	unstack(X, C);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & on(B, Y) & obj_tp(B, block) & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== X & on(X, A) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z <-
	put_down(Z);
	unstack(X, A);
	stack(X, Z);
	unstack(A, B);
	put_down(A);
	unstack(B, Y);
	put_down(B);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & ontable(X) & on(C, Y) & obj_tp(C, block) & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== X & clear(A) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, Y);
	put_down(C);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & on(B, X) & obj_tp(B, block) & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== X & A \== Y & on(Y, A) & on(X, C) & obj_tp(C, block) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z & Y \== Z <-
	put_down(Z);
	unstack(Y, A);
	put_down(Y);
	unstack(A, B);
	put_down(A);
	unstack(B, X);
	put_down(B);
	unstack(X, C);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & on(C, Y) & obj_tp(C, block) & C \== X & on(A, C) & obj_tp(A, block) & A \== C & A \== X & on(X, A) & clear(B) & obj_tp(B, block) & A \== B & B \== C & B \== X & holding(Z) & obj_tp(Z, block) & A \== Z & C \== Z & X \== Z <-
	put_down(Z);
	unstack(X, A);
	stack(X, B);
	unstack(A, C);
	put_down(A);
	unstack(C, Y);
	put_down(C);
	unstack(X, B);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & handempty & on(A, Y) & obj_tp(A, block) & A \== X & on(C, X) & obj_tp(C, block) & A \== C & C \== X & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== X & clear(B) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(B, C);
	put_down(B);
	unstack(A, Y);
	put_down(A);
	unstack(C, X);
	put_down(C);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(C, X) & obj_tp(C, block) & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== X & clear(A) & on(X, D) & obj_tp(D, block) & on(Z, Y) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z & clear(Z) <-
	unstack(Z, Y);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, X);
	put_down(C);
	unstack(X, D);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & ontable(X) & handempty & on(C, Y) & obj_tp(C, block) & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== X & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, Y);
	put_down(C);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & handempty & on(C, Y) & obj_tp(C, block) & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== X & clear(A) & on(Z, X) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z & clear(Z) <-
	unstack(Z, X);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, Y);
	put_down(C);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(A, X) & obj_tp(A, block) & A \== X & on(B, Y) & obj_tp(B, block) & A \== B & B \== X & on(X, B) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, X);
	put_down(A);
	unstack(X, B);
	stack(X, Z);
	unstack(B, Y);
	put_down(B);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & ontable(X) & handempty & on(B, X) & obj_tp(B, block) & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== X & A \== Y & on(Y, Z) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z & Y \== Z & on(Z, A) <-
	unstack(Y, Z);
	put_down(Y);
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, X);
	put_down(B);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(B, X) & obj_tp(B, block) & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== X & A \== Y & on(Y, A) & on(X, C) & obj_tp(C, block) & on(Z, Y) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, Y);
	put_down(Z);
	unstack(Y, A);
	put_down(Y);
	unstack(A, B);
	put_down(A);
	unstack(B, X);
	put_down(B);
	unstack(X, C);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(C, Y) & obj_tp(C, block) & C \== X & on(A, C) & obj_tp(A, block) & A \== C & A \== X & on(X, A) & on(Z, X) & obj_tp(Z, block) & A \== Z & C \== Z & X \== Z & clear(Z) & clear(B) & obj_tp(B, block) & A \== B & B \== C & B \== X <-
	unstack(Z, X);
	put_down(Z);
	unstack(X, A);
	stack(X, B);
	unstack(A, C);
	put_down(A);
	unstack(C, Y);
	put_down(C);
	unstack(X, B);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & ontable(X) & handempty & on(C, X) & obj_tp(C, block) & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== X & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, X);
	put_down(C);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(B, Y) & obj_tp(B, block) & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== X & on(X, A) & on(Z, X) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z & clear(Z) <-
	unstack(Z, X);
	put_down(Z);
	unstack(X, A);
	stack(X, Z);
	unstack(A, B);
	put_down(A);
	unstack(B, Y);
	put_down(B);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & handempty & on(B, X) & obj_tp(B, block) & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== X & A \== Y & on(X, C) & obj_tp(C, block) & on(Y, Z) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z & Y \== Z & on(Z, A) <-
	unstack(Y, Z);
	put_down(Y);
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, X);
	put_down(B);
	unstack(X, C);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(Y, X) & handempty & on(B, Y) & obj_tp(B, block) & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== X & A \== Y & on(X, C) & obj_tp(C, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, Y);
	put_down(B);
	unstack(Y, X);
	put_down(Y);
	unstack(X, C);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & handempty & on(A, Y) & obj_tp(A, block) & A \== X & on(C, X) & obj_tp(C, block) & A \== C & C \== X & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== X & clear(B) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, X);
	put_down(C);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & handempty & on(C, X) & obj_tp(C, block) & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== X & on(X, D) & obj_tp(D, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, X);
	put_down(C);
	unstack(X, D);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & handempty & on(C, Y) & obj_tp(C, block) & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== X & on(X, D) & obj_tp(D, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, Y);
	put_down(C);
	unstack(X, D);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & handempty & on(C, Y) & obj_tp(C, block) & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== X & on(X, Z) & obj_tp(Z, block) & B \== Z & C \== Z & X \== Z & on(Z, B) & clear(A) & obj_tp(A, block) & A \== B & A \== C & A \== X & A \== Z <-
	unstack(X, Z);
	stack(X, A);
	unstack(Z, B);
	put_down(Z);
	unstack(B, C);
	put_down(B);
	unstack(C, Y);
	put_down(C);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & handempty & on(A, X) & obj_tp(A, block) & A \== X & on(C, Y) & obj_tp(C, block) & A \== C & C \== X & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== X & clear(B) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, X);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, Y);
	put_down(C);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(A, Y) & obj_tp(A, block) & A \== X & A \== Y & on(B, X) & obj_tp(B, block) & A \== B & B \== X & B \== Y & on(Y, B) & on(X, C) & obj_tp(C, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	unstack(Y, B);
	put_down(Y);
	unstack(B, X);
	put_down(B);
	unstack(X, C);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(A, X) & obj_tp(A, block) & A \== X & clear(A) & on(D, Y) & obj_tp(D, block) & A \== D & D \== X & on(B, D) & obj_tp(B, block) & A \== B & B \== D & B \== X & on(X, B) & clear(C) & obj_tp(C, block) & B \== C & C \== D & C \== X & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & D \== Z & X \== Z <-
	put_down(Z);
	unstack(A, X);
	put_down(A);
	unstack(X, B);
	stack(X, C);
	unstack(B, D);
	put_down(B);
	unstack(D, Y);
	put_down(D);
	unstack(X, C);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & ontable(X) & on(D, X) & obj_tp(D, block) & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== X & clear(A) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, X);
	put_down(D);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & on(D, Y) & obj_tp(D, block) & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== X & clear(A) & on(X, V7) & obj_tp(V7, block) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, Y);
	put_down(D);
	unstack(X, V7);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(A, Y) & obj_tp(A, block) & A \== X & A \== Y & clear(A) & on(C, X) & obj_tp(C, block) & A \== C & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== X & B \== Y & on(Y, B) & on(X, D) & obj_tp(D, block) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z & Y \== Z <-
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	unstack(Y, B);
	put_down(Y);
	unstack(B, C);
	put_down(B);
	unstack(C, X);
	put_down(C);
	unstack(X, D);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(A, Y) & obj_tp(A, block) & A \== X & clear(A) & on(D, X) & obj_tp(D, block) & A \== D & D \== X & on(C, D) & obj_tp(C, block) & A \== C & C \== D & C \== X & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== D & B \== X & clear(B) & on(X, V7) & obj_tp(V7, block) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z <-
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, X);
	put_down(D);
	unstack(X, V7);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & on(D, X) & obj_tp(D, block) & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== X & clear(A) & on(X, V7) & obj_tp(V7, block) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, X);
	put_down(D);
	unstack(X, V7);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & ontable(X) & on(D, Y) & obj_tp(D, block) & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== X & clear(A) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, Y);
	put_down(D);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & on(D, Y) & obj_tp(D, block) & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== X & on(A, C) & obj_tp(A, block) & A \== C & A \== D & A \== X & on(X, A) & clear(B) & obj_tp(B, block) & A \== B & B \== C & B \== D & B \== X & holding(Z) & obj_tp(Z, block) & A \== Z & C \== Z & D \== Z & X \== Z <-
	put_down(Z);
	unstack(X, A);
	stack(X, B);
	unstack(A, C);
	put_down(A);
	unstack(C, D);
	put_down(C);
	unstack(D, Y);
	put_down(D);
	unstack(X, B);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(A, X) & obj_tp(A, block) & A \== X & clear(A) & on(C, Y) & obj_tp(C, block) & A \== C & C \== X & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== X & on(X, B) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z <-
	put_down(Z);
	unstack(A, X);
	put_down(A);
	unstack(X, B);
	stack(X, Z);
	unstack(B, C);
	put_down(B);
	unstack(C, Y);
	put_down(C);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(Y, X) & on(C, Y) & obj_tp(C, block) & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & B \== C & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== X & A \== Y & clear(A) & on(X, D) & obj_tp(D, block) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z & Y \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, Y);
	put_down(C);
	unstack(Y, X);
	put_down(Y);
	unstack(X, D);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(B, Y) & obj_tp(B, block) & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== X & A \== Y & clear(A) & on(C, X) & obj_tp(C, block) & A \== C & B \== C & C \== X & C \== Y & on(Y, C) & on(X, D) & obj_tp(D, block) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z & Y \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, Y);
	put_down(B);
	unstack(Y, C);
	put_down(Y);
	unstack(C, X);
	put_down(C);
	unstack(X, D);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & holding(X) & on(D, Y) & obj_tp(D, block) & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== X & clear(A) & clear(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z <-
	stack(X, Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, Y);
	put_down(D);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & ontable(X) & on(C, X) & obj_tp(C, block) & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & B \== C & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== X & A \== Y & on(Y, A) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z & Y \== Z <-
	put_down(Z);
	unstack(Y, A);
	put_down(Y);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, X);
	put_down(C);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & on(C, Y) & obj_tp(C, block) & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== X & on(X, A) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z <-
	put_down(Z);
	unstack(X, A);
	stack(X, Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, Y);
	put_down(C);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & holding(Y) & ontable(X) & on(C, X) & obj_tp(C, block) & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & B \== C & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== X & A \== Y & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z & Y \== Z & clear(Z) <-
	put_down(Y);
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, X);
	put_down(C);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & ontable(X) & handempty & on(C, X) & obj_tp(C, block) & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & B \== C & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== X & A \== Y & on(Y, Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z & Y \== Z & on(Z, A) <-
	unstack(Y, Z);
	put_down(Y);
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, X);
	put_down(C);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & handempty & on(D, Y) & obj_tp(D, block) & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== X & on(X, Z) & obj_tp(Z, block) & B \== Z & C \== Z & D \== Z & X \== Z & on(Z, B) & clear(A) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== X & A \== Z <-
	unstack(X, Z);
	stack(X, A);
	unstack(Z, B);
	put_down(Z);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, Y);
	put_down(D);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & handempty & on(D, Y) & obj_tp(D, block) & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== X & on(X, V7) & obj_tp(V7, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, Y);
	put_down(D);
	unstack(X, V7);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(A, Y) & obj_tp(A, block) & A \== X & on(D, X) & obj_tp(D, block) & A \== D & D \== X & on(C, D) & obj_tp(C, block) & A \== C & C \== D & C \== X & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== D & B \== X & clear(B) & on(X, V7) & obj_tp(V7, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, X);
	put_down(D);
	unstack(X, V7);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(A, Y) & obj_tp(A, block) & A \== X & A \== Y & on(C, X) & obj_tp(C, block) & A \== C & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== X & B \== Y & on(Y, B) & on(X, D) & obj_tp(D, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	unstack(Y, B);
	put_down(Y);
	unstack(B, C);
	put_down(B);
	unstack(C, X);
	put_down(C);
	unstack(X, D);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(A, X) & obj_tp(A, block) & A \== X & on(D, Y) & obj_tp(D, block) & A \== D & D \== X & on(B, D) & obj_tp(B, block) & A \== B & B \== D & B \== X & on(X, B) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & D \== Z & X \== Z & clear(Z) & clear(C) & obj_tp(C, block) & B \== C & C \== D & C \== X <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, X);
	put_down(A);
	unstack(X, B);
	stack(X, C);
	unstack(B, D);
	put_down(B);
	unstack(D, Y);
	put_down(D);
	unstack(X, C);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & handempty & on(D, X) & obj_tp(D, block) & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== X & clear(A) & on(Z, Y) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z & clear(Z) <-
	unstack(Z, Y);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, X);
	put_down(D);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & ontable(X) & handempty & on(D, X) & obj_tp(D, block) & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== X & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, X);
	put_down(D);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & handempty & on(C, X) & obj_tp(C, block) & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & B \== C & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== X & A \== Y & on(Y, A) & on(Z, Y) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, Y);
	put_down(Z);
	unstack(Y, A);
	put_down(Y);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, X);
	put_down(C);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(Y, X) & handempty & on(C, Y) & obj_tp(C, block) & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & B \== C & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== X & A \== Y & on(X, D) & obj_tp(D, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, Y);
	put_down(C);
	unstack(Y, X);
	put_down(Y);
	unstack(X, D);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(B, Y) & obj_tp(B, block) & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== X & A \== Y & on(C, X) & obj_tp(C, block) & A \== C & B \== C & C \== X & C \== Y & on(Y, C) & on(X, D) & obj_tp(D, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, Y);
	put_down(B);
	unstack(Y, C);
	put_down(Y);
	unstack(C, X);
	put_down(C);
	unstack(X, D);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & handempty & on(D, X) & obj_tp(D, block) & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== X & on(X, V7) & obj_tp(V7, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, X);
	put_down(D);
	unstack(X, V7);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(D, Y) & obj_tp(D, block) & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== X & on(A, C) & obj_tp(A, block) & A \== C & A \== D & A \== X & on(X, A) & on(Z, X) & obj_tp(Z, block) & A \== Z & C \== Z & D \== Z & X \== Z & clear(Z) & clear(B) & obj_tp(B, block) & A \== B & B \== C & B \== D & B \== X <-
	unstack(Z, X);
	put_down(Z);
	unstack(X, A);
	stack(X, B);
	unstack(A, C);
	put_down(A);
	unstack(C, D);
	put_down(C);
	unstack(D, Y);
	put_down(D);
	unstack(X, B);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(D, Y) & obj_tp(D, block) & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== X & clear(A) & on(X, V7) & obj_tp(V7, block) & on(Z, X) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z & clear(Z) <-
	unstack(Z, X);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, Y);
	put_down(D);
	unstack(X, V7);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & ontable(X) & handempty & on(D, Y) & obj_tp(D, block) & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== X & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, Y);
	put_down(D);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(C, Y) & obj_tp(C, block) & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== X & on(X, A) & on(Z, X) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z & clear(Z) <-
	unstack(Z, X);
	put_down(Z);
	unstack(X, A);
	stack(X, Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, Y);
	put_down(C);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(A, X) & obj_tp(A, block) & A \== X & on(C, Y) & obj_tp(C, block) & A \== C & C \== X & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== X & on(X, B) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, X);
	put_down(A);
	unstack(X, B);
	stack(X, Z);
	unstack(B, C);
	put_down(B);
	unstack(C, Y);
	put_down(C);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & ontable(X) & on(V7, X) & obj_tp(V7, block) & V7 \== X & on(D, V7) & obj_tp(D, block) & D \== V7 & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== V7 & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== V7 & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== V7 & A \== X & clear(A) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, X);
	put_down(V7);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & on(A, Y) & obj_tp(A, block) & A \== X & A \== Y & clear(A) & on(D, X) & obj_tp(D, block) & A \== D & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & A \== C & C \== D & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== D & B \== X & B \== Y & on(Y, B) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z & Y \== Z <-
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	unstack(Y, B);
	put_down(Y);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, X);
	put_down(D);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & holding(Y) & on(D, X) & obj_tp(D, block) & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & C \== D & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== X & A \== Y & on(X, V7) & obj_tp(V7, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z & Y \== Z & clear(Z) <-
	put_down(Y);
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, X);
	put_down(D);
	unstack(X, V7);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & ontable(X) & on(V7, Y) & obj_tp(V7, block) & V7 \== X & on(D, V7) & obj_tp(D, block) & D \== V7 & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== V7 & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== V7 & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== V7 & A \== X & clear(A) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, Y);
	put_down(V7);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(A, X) & obj_tp(A, block) & A \== X & clear(A) & on(D, Y) & obj_tp(D, block) & A \== D & D \== X & on(C, D) & obj_tp(C, block) & A \== C & C \== D & C \== X & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== D & B \== X & on(X, B) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z <-
	put_down(Z);
	unstack(A, X);
	put_down(A);
	unstack(X, B);
	stack(X, A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, Y);
	put_down(D);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & on(V7, X) & obj_tp(V7, block) & V7 \== X & on(D, V7) & obj_tp(D, block) & D \== V7 & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== V7 & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== V7 & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== V7 & A \== X & clear(A) & on(X, V8) & obj_tp(V8, block) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, X);
	put_down(V7);
	unstack(X, V8);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(B, X) & obj_tp(B, block) & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== X & clear(A) & on(D, Y) & obj_tp(D, block) & A \== D & B \== D & D \== X & on(C, D) & obj_tp(C, block) & A \== C & B \== C & C \== D & C \== X & on(X, C) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, X);
	put_down(B);
	unstack(X, C);
	stack(X, Z);
	unstack(C, D);
	put_down(C);
	unstack(D, Y);
	put_down(D);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & holding(Y) & ontable(X) & on(D, X) & obj_tp(D, block) & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & C \== D & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== X & A \== Y & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z & Y \== Z & clear(Z) <-
	put_down(Y);
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, X);
	put_down(D);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & holding(X) & on(V7, Y) & obj_tp(V7, block) & V7 \== X & on(D, V7) & obj_tp(D, block) & D \== V7 & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== V7 & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== V7 & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== V7 & A \== X & clear(A) & clear(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z <-
	stack(X, Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, Y);
	put_down(V7);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & on(D, Y) & obj_tp(D, block) & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== X & on(X, A) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z <-
	put_down(Z);
	unstack(X, A);
	stack(X, Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, Y);
	put_down(D);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(C, Y) & obj_tp(C, block) & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & B \== C & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== X & A \== Y & clear(A) & on(D, X) & obj_tp(D, block) & A \== D & B \== D & C \== D & D \== X & D \== Y & on(Y, D) & on(X, V7) & obj_tp(V7, block) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z & Y \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, Y);
	put_down(C);
	unstack(Y, D);
	put_down(Y);
	unstack(D, X);
	put_down(D);
	unstack(X, V7);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(A, X) & obj_tp(A, block) & A \== X & clear(A) & on(V7, Y) & obj_tp(V7, block) & A \== V7 & V7 \== X & on(D, V7) & obj_tp(D, block) & A \== D & D \== V7 & D \== X & on(B, D) & obj_tp(B, block) & A \== B & B \== D & B \== V7 & B \== X & on(X, B) & clear(C) & obj_tp(C, block) & B \== C & C \== D & C \== V7 & C \== X & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & D \== Z & V7 \== Z & X \== Z <-
	put_down(Z);
	unstack(A, X);
	put_down(A);
	unstack(X, B);
	stack(X, C);
	unstack(B, D);
	put_down(B);
	unstack(D, V7);
	put_down(D);
	unstack(V7, Y);
	put_down(V7);
	unstack(X, C);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & ontable(X) & on(D, X) & obj_tp(D, block) & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & C \== D & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== X & A \== Y & on(Y, A) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z & Y \== Z <-
	put_down(Z);
	unstack(Y, A);
	put_down(Y);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, X);
	put_down(D);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(A, X) & obj_tp(A, block) & A \== X & clear(A) & on(V7, Y) & obj_tp(V7, block) & A \== V7 & V7 \== X & on(D, V7) & obj_tp(D, block) & A \== D & D \== V7 & D \== X & on(C, D) & obj_tp(C, block) & A \== C & C \== D & C \== V7 & C \== X & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== D & B \== V7 & B \== X & clear(B) & on(X, V8) & obj_tp(V8, block) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z <-
	put_down(Z);
	unstack(A, X);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, Y);
	put_down(V7);
	unstack(X, V8);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(D, Y) & obj_tp(D, block) & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== X & on(X, A) & on(Z, X) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z & clear(Z) <-
	unstack(Z, X);
	put_down(Z);
	unstack(X, A);
	stack(X, Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, Y);
	put_down(D);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(A, X) & obj_tp(A, block) & A \== X & on(D, Y) & obj_tp(D, block) & A \== D & D \== X & on(C, D) & obj_tp(C, block) & A \== C & C \== D & C \== X & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== D & B \== X & on(X, B) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, X);
	put_down(A);
	unstack(X, B);
	stack(X, A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, Y);
	put_down(D);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & ontable(X) & handempty & on(V7, X) & obj_tp(V7, block) & V7 \== X & on(D, V7) & obj_tp(D, block) & D \== V7 & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== V7 & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== V7 & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== V7 & A \== X & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, X);
	put_down(V7);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(C, Y) & obj_tp(C, block) & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & B \== C & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== X & A \== Y & on(D, X) & obj_tp(D, block) & A \== D & B \== D & C \== D & D \== X & D \== Y & on(Y, D) & on(X, V7) & obj_tp(V7, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, Y);
	put_down(C);
	unstack(Y, D);
	put_down(Y);
	unstack(D, X);
	put_down(D);
	unstack(X, V7);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & handempty & on(V7, X) & obj_tp(V7, block) & V7 \== X & on(D, V7) & obj_tp(D, block) & D \== V7 & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== V7 & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== V7 & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== V7 & A \== X & on(X, V8) & obj_tp(V8, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, X);
	put_down(V7);
	unstack(X, V8);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & handempty & on(D, X) & obj_tp(D, block) & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & C \== D & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== X & A \== Y & on(X, V7) & obj_tp(V7, block) & on(Y, Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z & Y \== Z & on(Z, A) <-
	unstack(Y, Z);
	put_down(Y);
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, X);
	put_down(D);
	unstack(X, V7);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & handempty & on(A, Y) & obj_tp(A, block) & A \== X & A \== Y & on(D, X) & obj_tp(D, block) & A \== D & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & A \== C & C \== D & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== D & B \== X & B \== Y & on(Y, B) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	unstack(Y, B);
	put_down(Y);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, X);
	put_down(D);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(B, X) & obj_tp(B, block) & B \== X & clear(B) & on(V7, Y) & obj_tp(V7, block) & B \== V7 & V7 \== X & on(D, V7) & obj_tp(D, block) & B \== D & D \== V7 & D \== X & on(C, D) & obj_tp(C, block) & B \== C & C \== D & C \== V7 & C \== X & on(A, C) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== V7 & A \== X & on(X, V8) & obj_tp(V8, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(B, X);
	put_down(B);
	unstack(A, C);
	put_down(A);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, Y);
	put_down(V7);
	unstack(X, V8);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & ontable(X) & handempty & on(V7, Y) & obj_tp(V7, block) & V7 \== X & on(D, V7) & obj_tp(D, block) & D \== V7 & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== V7 & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== V7 & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== V7 & A \== X & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, Y);
	put_down(V7);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & handempty & on(V7, Y) & obj_tp(V7, block) & V7 \== X & on(D, V7) & obj_tp(D, block) & D \== V7 & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== V7 & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== V7 & B \== X & on(X, Z) & obj_tp(Z, block) & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z & on(Z, B) & clear(A) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== V7 & A \== X & A \== Z <-
	unstack(X, Z);
	stack(X, A);
	unstack(Z, B);
	put_down(Z);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, Y);
	put_down(V7);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(A, X) & obj_tp(A, block) & A \== X & on(V7, Y) & obj_tp(V7, block) & A \== V7 & V7 \== X & on(D, V7) & obj_tp(D, block) & A \== D & D \== V7 & D \== X & on(B, D) & obj_tp(B, block) & A \== B & B \== D & B \== V7 & B \== X & on(X, B) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & D \== Z & V7 \== Z & X \== Z & clear(Z) & clear(C) & obj_tp(C, block) & B \== C & C \== D & C \== V7 & C \== X <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, X);
	put_down(A);
	unstack(X, B);
	stack(X, C);
	unstack(B, D);
	put_down(B);
	unstack(D, V7);
	put_down(D);
	unstack(V7, Y);
	put_down(V7);
	unstack(X, C);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(B, X) & obj_tp(B, block) & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== X & on(D, Y) & obj_tp(D, block) & A \== D & B \== D & D \== X & on(C, D) & obj_tp(C, block) & A \== C & B \== C & C \== D & C \== X & on(X, C) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, X);
	put_down(B);
	unstack(X, C);
	stack(X, Z);
	unstack(C, D);
	put_down(C);
	unstack(D, Y);
	put_down(D);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & ontable(X) & handempty & on(D, X) & obj_tp(D, block) & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & C \== D & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== X & A \== Y & on(Y, Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z & Y \== Z & on(Z, A) <-
	unstack(Y, Z);
	put_down(Y);
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, X);
	put_down(D);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & handempty & on(D, X) & obj_tp(D, block) & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & C \== D & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== X & A \== Y & on(Y, A) & on(Z, Y) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, Y);
	put_down(Z);
	unstack(Y, A);
	put_down(Y);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, X);
	put_down(D);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & holding(Y) & ontable(X) & on(V7, X) & obj_tp(V7, block) & V7 \== X & V7 \== Y & on(D, V7) & obj_tp(D, block) & D \== V7 & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & C \== D & C \== V7 & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== V7 & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== V7 & A \== X & A \== Y & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z & Y \== Z & clear(Z) <-
	put_down(Y);
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, X);
	put_down(V7);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & on(A, Y) & obj_tp(A, block) & A \== X & A \== Y & clear(A) & on(V7, X) & obj_tp(V7, block) & A \== V7 & V7 \== X & V7 \== Y & on(D, V7) & obj_tp(D, block) & A \== D & D \== V7 & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & A \== C & C \== D & C \== V7 & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== D & B \== V7 & B \== X & B \== Y & on(Y, B) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z & Y \== Z <-
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	unstack(Y, B);
	put_down(Y);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, X);
	put_down(V7);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & ontable(X) & on(V7, X) & obj_tp(V7, block) & V7 \== X & V7 \== Y & on(D, V7) & obj_tp(D, block) & D \== V7 & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & C \== D & C \== V7 & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== V7 & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== V7 & A \== X & A \== Y & on(Y, A) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z & Y \== Z <-
	put_down(Z);
	unstack(Y, A);
	put_down(Y);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, X);
	put_down(V7);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & ontable(X) & on(V8, Y) & obj_tp(V8, block) & V8 \== X & on(V7, V8) & obj_tp(V7, block) & V7 \== V8 & V7 \== X & on(D, V7) & obj_tp(D, block) & D \== V7 & D \== V8 & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== V7 & C \== V8 & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== V7 & B \== V8 & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== V7 & A \== V8 & A \== X & clear(A) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & V8 \== Z & X \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, V8);
	put_down(V7);
	unstack(V8, Y);
	put_down(V8);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & holding(Y) & on(V7, X) & obj_tp(V7, block) & V7 \== X & V7 \== Y & on(D, V7) & obj_tp(D, block) & D \== V7 & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & C \== D & C \== V7 & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== V7 & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== V7 & A \== X & A \== Y & on(X, V8) & obj_tp(V8, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z & Y \== Z & clear(Z) <-
	put_down(Y);
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, X);
	put_down(V7);
	unstack(X, V8);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(C, X) & obj_tp(C, block) & C \== X & clear(C) & on(V8, Y) & obj_tp(V8, block) & C \== V8 & V8 \== X & on(V7, V8) & obj_tp(V7, block) & C \== V7 & V7 \== V8 & V7 \== X & on(D, V7) & obj_tp(D, block) & C \== D & D \== V7 & D \== V8 & D \== X & on(B, D) & obj_tp(B, block) & B \== C & B \== D & B \== V7 & B \== V8 & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== V7 & A \== V8 & A \== X & clear(A) & on(X, V9) & obj_tp(V9, block) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & V8 \== Z & X \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(C, X);
	put_down(C);
	unstack(B, D);
	put_down(B);
	unstack(D, V7);
	put_down(D);
	unstack(V7, V8);
	put_down(V7);
	unstack(V8, Y);
	put_down(V8);
	unstack(X, V9);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & on(B, Y) & obj_tp(B, block) & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== X & A \== Y & clear(A) & on(V7, X) & obj_tp(V7, block) & A \== V7 & B \== V7 & V7 \== X & V7 \== Y & on(D, V7) & obj_tp(D, block) & A \== D & B \== D & D \== V7 & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & A \== C & B \== C & C \== D & C \== V7 & C \== X & C \== Y & on(Y, C) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z & Y \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, Y);
	put_down(B);
	unstack(Y, C);
	put_down(Y);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, X);
	put_down(V7);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(A, X) & obj_tp(A, block) & A \== X & clear(A) & on(V7, Y) & obj_tp(V7, block) & A \== V7 & V7 \== X & on(D, V7) & obj_tp(D, block) & A \== D & D \== V7 & D \== X & on(C, D) & obj_tp(C, block) & A \== C & C \== D & C \== V7 & C \== X & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== D & B \== V7 & B \== X & on(X, B) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z <-
	put_down(Z);
	unstack(A, X);
	put_down(A);
	unstack(X, B);
	stack(X, A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, Y);
	put_down(V7);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & on(B, X) & obj_tp(B, block) & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== X & clear(A) & on(V7, Y) & obj_tp(V7, block) & A \== V7 & B \== V7 & V7 \== X & on(D, V7) & obj_tp(D, block) & A \== D & B \== D & D \== V7 & D \== X & on(C, D) & obj_tp(C, block) & A \== C & B \== C & C \== D & C \== V7 & C \== X & on(X, C) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, X);
	put_down(B);
	unstack(X, C);
	stack(X, B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, Y);
	put_down(V7);
	unstack(X, B);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & handempty & on(B, Y) & obj_tp(B, block) & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== X & A \== Y & on(V7, X) & obj_tp(V7, block) & A \== V7 & B \== V7 & V7 \== X & V7 \== Y & on(D, V7) & obj_tp(D, block) & A \== D & B \== D & D \== V7 & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & A \== C & B \== C & C \== D & C \== V7 & C \== X & C \== Y & on(Y, C) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, Y);
	put_down(B);
	unstack(Y, C);
	put_down(Y);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, X);
	put_down(V7);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & ontable(X) & handempty & on(V7, X) & obj_tp(V7, block) & V7 \== X & V7 \== Y & on(D, V7) & obj_tp(D, block) & D \== V7 & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & C \== D & C \== V7 & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== V7 & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== V7 & A \== X & A \== Y & on(Y, Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z & Y \== Z & on(Z, A) <-
	unstack(Y, Z);
	put_down(Y);
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, X);
	put_down(V7);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(A, X) & obj_tp(A, block) & A \== X & on(V7, Y) & obj_tp(V7, block) & A \== V7 & V7 \== X & on(D, V7) & obj_tp(D, block) & A \== D & D \== V7 & D \== X & on(C, D) & obj_tp(C, block) & A \== C & C \== D & C \== V7 & C \== X & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== D & B \== V7 & B \== X & on(X, B) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, X);
	put_down(A);
	unstack(X, B);
	stack(X, A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, Y);
	put_down(V7);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(C, X) & obj_tp(C, block) & C \== X & clear(C) & on(V8, Y) & obj_tp(V8, block) & C \== V8 & V8 \== X & on(V7, V8) & obj_tp(V7, block) & C \== V7 & V7 \== V8 & V7 \== X & on(D, V7) & obj_tp(D, block) & C \== D & D \== V7 & D \== V8 & D \== X & on(B, D) & obj_tp(B, block) & B \== C & B \== D & B \== V7 & B \== V8 & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== V7 & A \== V8 & A \== X & on(X, V9) & obj_tp(V9, block) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & V8 \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(C, X);
	put_down(C);
	unstack(B, D);
	put_down(B);
	unstack(D, V7);
	put_down(D);
	unstack(V7, V8);
	put_down(V7);
	unstack(V8, Y);
	put_down(V8);
	unstack(X, V9);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & handempty & on(A, Y) & obj_tp(A, block) & A \== X & A \== Y & on(V7, X) & obj_tp(V7, block) & A \== V7 & V7 \== X & V7 \== Y & on(D, V7) & obj_tp(D, block) & A \== D & D \== V7 & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & A \== C & C \== D & C \== V7 & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== D & B \== V7 & B \== X & B \== Y & on(Y, B) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	unstack(Y, B);
	put_down(Y);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, X);
	put_down(V7);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & ontable(X) & handempty & on(V8, Y) & obj_tp(V8, block) & V8 \== X & on(V7, V8) & obj_tp(V7, block) & V7 \== V8 & V7 \== X & on(D, V7) & obj_tp(D, block) & D \== V7 & D \== V8 & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== V7 & C \== V8 & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== V7 & B \== V8 & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== V7 & A \== V8 & A \== X & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & V8 \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, V8);
	put_down(V7);
	unstack(V8, Y);
	put_down(V8);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & handempty & on(B, X) & obj_tp(B, block) & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== X & on(V7, Y) & obj_tp(V7, block) & A \== V7 & B \== V7 & V7 \== X & on(D, V7) & obj_tp(D, block) & A \== D & B \== D & D \== V7 & D \== X & on(C, D) & obj_tp(C, block) & A \== C & B \== C & C \== D & C \== V7 & C \== X & on(X, C) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, X);
	put_down(B);
	unstack(X, C);
	stack(X, B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, Y);
	put_down(V7);
	unstack(X, B);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(Y) & handempty & on(V7, X) & obj_tp(V7, block) & V7 \== X & V7 \== Y & on(D, V7) & obj_tp(D, block) & D \== V7 & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & C \== D & C \== V7 & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== V7 & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== V7 & A \== X & A \== Y & on(X, V8) & obj_tp(V8, block) & on(Y, Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z & Y \== Z & on(Z, A) <-
	unstack(Y, Z);
	put_down(Y);
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, X);
	put_down(V7);
	unstack(X, V8);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & handempty & on(V7, X) & obj_tp(V7, block) & V7 \== X & V7 \== Y & on(D, V7) & obj_tp(D, block) & D \== V7 & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & C \== D & C \== V7 & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== V7 & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== V7 & A \== X & A \== Y & on(Y, A) & on(Z, Y) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, Y);
	put_down(Z);
	unstack(Y, A);
	put_down(Y);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, X);
	put_down(V7);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & ontable(X) & on(V9, Y) & obj_tp(V9, block) & V9 \== X & on(V8, V9) & obj_tp(V8, block) & V8 \== V9 & V8 \== X & on(V7, V8) & obj_tp(V7, block) & V7 \== V8 & V7 \== V9 & V7 \== X & on(D, V7) & obj_tp(D, block) & D \== V7 & D \== V8 & D \== V9 & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== V7 & C \== V8 & C \== V9 & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== V7 & B \== V8 & B \== V9 & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== V7 & A \== V8 & A \== V9 & A \== X & clear(A) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & V8 \== Z & V9 \== Z & X \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, V8);
	put_down(V7);
	unstack(V8, V9);
	put_down(V8);
	unstack(V9, Y);
	put_down(V9);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & on(A, Y) & obj_tp(A, block) & A \== X & A \== Y & clear(A) & on(V8, X) & obj_tp(V8, block) & A \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & obj_tp(V7, block) & A \== V7 & V7 \== V8 & V7 \== X & V7 \== Y & on(D, V7) & obj_tp(D, block) & A \== D & D \== V7 & D \== V8 & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & A \== C & C \== D & C \== V7 & C \== V8 & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== D & B \== V7 & B \== V8 & B \== X & B \== Y & on(Y, B) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & V8 \== Z & X \== Z & Y \== Z <-
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	unstack(Y, B);
	put_down(Y);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, V8);
	put_down(V7);
	unstack(V8, X);
	put_down(V8);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & on(B, Y) & obj_tp(B, block) & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== X & A \== Y & clear(A) & on(V8, X) & obj_tp(V8, block) & A \== V8 & B \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & obj_tp(V7, block) & A \== V7 & B \== V7 & V7 \== V8 & V7 \== X & V7 \== Y & on(D, V7) & obj_tp(D, block) & A \== D & B \== D & D \== V7 & D \== V8 & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & A \== C & B \== C & C \== D & C \== V7 & C \== V8 & C \== X & C \== Y & on(Y, C) & holding(Z) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & V8 \== Z & X \== Z & Y \== Z <-
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, Y);
	put_down(B);
	unstack(Y, C);
	put_down(Y);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, V8);
	put_down(V7);
	unstack(V8, X);
	put_down(V8);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & handempty & on(A, Y) & obj_tp(A, block) & A \== X & A \== Y & on(V8, X) & obj_tp(V8, block) & A \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & obj_tp(V7, block) & A \== V7 & V7 \== V8 & V7 \== X & V7 \== Y & on(D, V7) & obj_tp(D, block) & A \== D & D \== V7 & D \== V8 & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & A \== C & C \== D & C \== V7 & C \== V8 & C \== X & C \== Y & on(B, C) & obj_tp(B, block) & A \== B & B \== C & B \== D & B \== V7 & B \== V8 & B \== X & B \== Y & on(Y, B) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & V8 \== Z & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, Y);
	put_down(A);
	unstack(Y, B);
	put_down(Y);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, V8);
	put_down(V7);
	unstack(V8, X);
	put_down(V8);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & clear(X) & ontable(X) & handempty & on(V9, Y) & obj_tp(V9, block) & V9 \== X & on(V8, V9) & obj_tp(V8, block) & V8 \== V9 & V8 \== X & on(V7, V8) & obj_tp(V7, block) & V7 \== V8 & V7 \== V9 & V7 \== X & on(D, V7) & obj_tp(D, block) & D \== V7 & D \== V8 & D \== V9 & D \== X & on(C, D) & obj_tp(C, block) & C \== D & C \== V7 & C \== V8 & C \== V9 & C \== X & on(B, C) & obj_tp(B, block) & B \== C & B \== D & B \== V7 & B \== V8 & B \== V9 & B \== X & on(A, B) & obj_tp(A, block) & A \== B & A \== C & A \== D & A \== V7 & A \== V8 & A \== V9 & A \== X & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & V8 \== Z & V9 \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, C);
	put_down(B);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, V8);
	put_down(V7);
	unstack(V8, V9);
	put_down(V8);
	unstack(V9, Y);
	put_down(V9);
	pick_up(X);
	stack(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & X \== Y & ontable(X) & handempty & on(B, Y) & obj_tp(B, block) & B \== X & B \== Y & on(A, B) & obj_tp(A, block) & A \== B & A \== X & A \== Y & on(V8, X) & obj_tp(V8, block) & A \== V8 & B \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & obj_tp(V7, block) & A \== V7 & B \== V7 & V7 \== V8 & V7 \== X & V7 \== Y & on(D, V7) & obj_tp(D, block) & A \== D & B \== D & D \== V7 & D \== V8 & D \== X & D \== Y & on(C, D) & obj_tp(C, block) & A \== C & B \== C & C \== D & C \== V7 & C \== V8 & C \== X & C \== Y & on(Y, C) & on(Z, A) & obj_tp(Z, block) & A \== Z & B \== Z & C \== Z & D \== Z & V7 \== Z & V8 \== Z & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, A);
	put_down(Z);
	unstack(A, B);
	put_down(A);
	unstack(B, Y);
	put_down(B);
	unstack(Y, C);
	put_down(Y);
	unstack(C, D);
	put_down(C);
	unstack(D, V7);
	put_down(D);
	unstack(V7, V8);
	put_down(V7);
	unstack(V8, X);
	put_down(V8);
	pick_up(X);
	stack(X, Y).

+!ontable(X) : obj_tp(X, block) & holding(X) <-
	put_down(X).

+!ontable(X) : obj_tp(X, block) & clear(X) & handempty & on(X, Y) & obj_tp(Y, block) <-
	unstack(X, Y);
	put_down(X).

+!clear(X) : obj_tp(X, block) & on(Y, X) & obj_tp(Y, block) & not clear(Y) <-
	!clear(Y);
	!clear(X).

+!clear(X) : obj_tp(X, block) & not handempty <-
	!handempty;
	!clear(X).

+!holding(X) : obj_tp(X, block) & not clear(X) <-
	!clear(X);
	!holding(X).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & not clear(X) <-
	!clear(X);
	!on(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & not clear(Y) <-
	!clear(Y);
	!on(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & not handempty <-
	!handempty;
	!on(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & not holding(X) <-
	!holding(X);
	!on(X, Y).

+!on(X, Y) : obj_tp(X, block) & obj_tp(Y, block) & not ontable(X) <-
	!ontable(X);
	!on(X, Y).

+!ontable(X) : obj_tp(X, block) & not clear(X) <-
	!clear(X);
	!ontable(X).

+!ontable(X) : obj_tp(X, block) & not handempty <-
	!handempty;
	!ontable(X).

+!ontable(X) : obj_tp(X, block) & not holding(X) <-
	!holding(X);
	!ontable(X).
