/* Generated AgentSpeak(L) Plan Library */
/* Domain: blocksworld-clear */

+!arm_empty : arm_empty <-
	true.

+!clear(X) : clear(X) <-
	true.

+!holding(X) : holding(X) <-
	true.

+!on(X, Y) : on(X, Y) <-
	true.

+!on_table(X) : on_table(X) <-
	true.

+!arm_empty : holding(X) <-
	putdown(X).

+!clear(X) : holding(X) <-
	putdown(X).

+!clear(X) : arm_empty & on(Y, X) & clear(Y) <-
	unstack(Y, X);
	putdown(Y).

+!clear(X) : arm_empty & on(Y, X) & clear(Y) <-
	unstack(Y, X).

+!clear(X) : on(Z, X) & clear(Z) & holding(Y) <-
	putdown(Y);
	unstack(Z, X).

+!clear(X) : arm_empty & on(Z, X) & on(Y, Z) & Y \== Z & clear(Y) <-
	unstack(Y, Z);
	putdown(Y);
	unstack(Z, X).

+!clear(X) : on(A, X) & on(Z, A) & A \== Z & clear(Z) & holding(Y) & Y \== Z <-
	putdown(Y);
	unstack(Z, A);
	putdown(Z);
	unstack(A, X).

+!clear(X) : arm_empty & on(A, X) & on(Z, A) & A \== Z & on(Y, Z) & A \== Y & Y \== Z & clear(Y) <-
	unstack(Y, Z);
	putdown(Y);
	unstack(Z, A);
	putdown(Z);
	unstack(A, X).

+!clear(X) : on(B, X) & on(A, B) & A \== B & on(Z, A) & A \== Z & B \== Z & clear(Z) & holding(Y) & A \== Y & Y \== Z <-
	putdown(Y);
	unstack(Z, A);
	putdown(Z);
	unstack(A, B);
	putdown(A);
	unstack(B, X).

+!clear(X) : arm_empty & on(B, X) & on(A, B) & A \== B & on(Z, A) & A \== Z & B \== Z & on(Y, Z) & A \== Y & B \== Y & Y \== Z & clear(Y) <-
	unstack(Y, Z);
	putdown(Y);
	unstack(Z, A);
	putdown(Z);
	unstack(A, B);
	putdown(A);
	unstack(B, X).

+!holding(X) : clear(X) & on_table(X) & arm_empty <-
	pickup(X).

+!holding(X) : clear(X) & arm_empty & on(X, Y) <-
	unstack(X, Y).

+!on(X, Y) : clear(Y) & holding(X) <-
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(X) & clear(Y) & on_table(X) & arm_empty <-
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(X) & clear(Y) & arm_empty & on(X, Z) & Y \== Z <-
	unstack(X, Z);
	stack(X, Y).

+!on_table(X) : holding(X) <-
	putdown(X).

+!on_table(X) : clear(X) & arm_empty & on(X, Y) <-
	unstack(X, Y);
	putdown(X).

+!clear(X) : not arm_empty <-
	!arm_empty;
	!clear(X).

+!clear(X) : on(Y, X) & not clear(Y) <-
	!clear(Y);
	!clear(X).

+!holding(X) : not arm_empty <-
	!arm_empty;
	!holding(X).

+!holding(X) : not clear(X) <-
	!clear(X);
	!holding(X).

+!on(X, Y) : not arm_empty <-
	!arm_empty;
	!on(X, Y).

+!on(X, Y) : not clear(X) <-
	!clear(X);
	!on(X, Y).

+!on(X, Y) : not clear(Y) <-
	!clear(Y);
	!on(X, Y).

+!on(X, Y) : not holding(X) <-
	!holding(X);
	!on(X, Y).

+!on(X, Y) : not on_table(X) <-
	!on_table(X);
	!on(X, Y).

+!on_table(X) : not arm_empty <-
	!arm_empty;
	!on_table(X).

+!on_table(X) : not clear(X) <-
	!clear(X);
	!on_table(X).

+!on_table(X) : not holding(X) <-
	!holding(X);
	!on_table(X).
