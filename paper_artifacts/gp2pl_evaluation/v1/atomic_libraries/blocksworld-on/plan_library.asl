/* Generated AgentSpeak(L) Plan Library */
/* Domain: blocksworld-on */

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

+!clear(X) : arm_empty & on(Y, X) & X \== Y & clear(Y) <-
	unstack(Y, X).

+!clear(X) : arm_empty & on(Y, X) & clear(Y) <-
	unstack(Y, X);
	putdown(Y).

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

+!on(X, Y) : X \== Y & clear(X) & clear(Y) & on_table(X) & arm_empty <-
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(X) & clear(Y) & arm_empty & on(X, Z) <-
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(X) & clear(Y) & on(X, A) & holding(Z) & X \== Z <-
	putdown(Z);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(X) & holding(Y) & on(X, Z) <-
	putdown(Y);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(X) & clear(Y) & on_table(X) & holding(Z) & X \== Z <-
	putdown(Z);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(X) & holding(Y) & on_table(X) <-
	putdown(Y);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(X) & on_table(X) & arm_empty & on(Z, Y) & X \== Z & clear(Z) <-
	unstack(Z, Y);
	putdown(Z);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(Y) & arm_empty & on(X, A) & on(Z, X) & X \== Z & clear(Z) <-
	unstack(Z, X);
	putdown(Z);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(X) & arm_empty & on(X, A) & on(Z, Y) & X \== Z & clear(Z) <-
	unstack(Z, Y);
	putdown(Z);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : X \== Y & on(Y, X) & clear(Y) & arm_empty & on(X, Z) <-
	unstack(Y, X);
	putdown(Y);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(Y) & on_table(X) & arm_empty & on(Z, X) & X \== Z & clear(Z) <-
	unstack(Z, X);
	putdown(Z);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & on(Y, X) & clear(Y) & on_table(X) & arm_empty <-
	unstack(Y, X);
	putdown(Y);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(Y) & on_table(X) & on(A, X) & A \== X & clear(A) & holding(Z) & A \== Z & X \== Z <-
	putdown(Z);
	unstack(A, X);
	putdown(A);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & holding(X) & on(Z, Y) & X \== Z & clear(Z) <-
	putdown(X);
	unstack(Z, Y);
	putdown(Z);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(X) & on(A, Y) & A \== X & clear(A) & on(X, B) & holding(Z) & A \== Z & X \== Z <-
	putdown(Z);
	unstack(A, Y);
	putdown(A);
	unstack(X, B);
	stack(X, Y).

+!on(X, Y) : X \== Y & holding(Y) & on_table(X) & on(Z, X) & X \== Z & Y \== Z & clear(Z) <-
	putdown(Y);
	unstack(Z, X);
	putdown(Z);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & holding(Y) & on(X, A) & on(Z, X) & X \== Z & Y \== Z & clear(Z) <-
	putdown(Y);
	unstack(Z, X);
	putdown(Z);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : X \== Y & on(Y, X) & clear(Y) & on(X, A) & holding(Z) & X \== Z & Y \== Z <-
	putdown(Z);
	unstack(Y, X);
	putdown(Y);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : X \== Y & holding(X) & on(A, Y) & A \== X & clear(A) & clear(Z) & A \== Z & X \== Z <-
	stack(X, Z);
	unstack(A, Y);
	putdown(A);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : X \== Y & on(Y, X) & clear(Y) & on_table(X) & holding(Z) & X \== Z & Y \== Z <-
	putdown(Z);
	unstack(Y, X);
	putdown(Y);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(X) & on_table(X) & on(A, Y) & A \== X & clear(A) & holding(Z) & A \== Z & X \== Z <-
	putdown(Z);
	unstack(A, Y);
	putdown(A);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & on_table(X) & arm_empty & on(A, X) & A \== X & clear(A) & on(Z, Y) & A \== Z & X \== Z & clear(Z) <-
	unstack(Z, Y);
	putdown(Z);
	unstack(A, X);
	putdown(A);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(X) & arm_empty & on(X, Z) & X \== Z & on(Z, Y) & clear(A) & A \== X & A \== Z <-
	unstack(X, Z);
	stack(X, A);
	unstack(Z, Y);
	putdown(Z);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(Y) & on_table(X) & arm_empty & on(A, X) & A \== X & on(Z, A) & A \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	putdown(Z);
	unstack(A, X);
	putdown(A);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & on(Y, X) & arm_empty & on(X, A) & on(Z, Y) & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, Y);
	putdown(Z);
	unstack(Y, X);
	putdown(Y);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(X) & arm_empty & on(X, Z) & X \== Z & on(Z, Y) <-
	unstack(X, Z);
	putdown(X);
	unstack(Z, Y);
	putdown(Z);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(X) & on_table(X) & arm_empty & on(A, Y) & A \== X & on(Z, A) & A \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	putdown(Z);
	unstack(A, Y);
	putdown(A);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(X) & arm_empty & on(A, Y) & A \== X & on(X, B) & on(Z, A) & A \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	putdown(Z);
	unstack(A, Y);
	putdown(A);
	unstack(X, B);
	stack(X, Y).

+!on(X, Y) : X \== Y & on_table(X) & arm_empty & on(A, Y) & A \== X & clear(A) & on(Z, X) & A \== Z & X \== Z & clear(Z) <-
	unstack(Z, X);
	putdown(Z);
	unstack(A, Y);
	putdown(A);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(Y) & on_table(X) & arm_empty & on(Y, Z) & X \== Z & Y \== Z & on(Z, X) <-
	unstack(Y, Z);
	putdown(Y);
	unstack(Z, X);
	putdown(Z);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & on(Y, X) & on_table(X) & arm_empty & on(Z, Y) & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, Y);
	putdown(Z);
	unstack(Y, X);
	putdown(Y);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(Y) & arm_empty & on(X, A) & on(Y, Z) & X \== Z & Y \== Z & on(Z, X) <-
	unstack(Y, Z);
	putdown(Y);
	unstack(Z, X);
	putdown(Z);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(X) & on(A, Y) & A \== X & on(X, A) & holding(Z) & A \== Z & X \== Z <-
	putdown(Z);
	unstack(X, A);
	stack(X, Z);
	unstack(A, Y);
	putdown(A);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : X \== Y & holding(X) & on(A, Y) & A \== X & on(Z, A) & A \== Z & X \== Z & clear(Z) <-
	putdown(X);
	unstack(Z, A);
	putdown(Z);
	unstack(A, Y);
	putdown(A);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(Y) & on_table(X) & on(B, X) & B \== X & on(A, B) & A \== B & A \== X & clear(A) & holding(Z) & A \== Z & B \== Z & X \== Z <-
	putdown(Z);
	unstack(A, B);
	putdown(A);
	unstack(B, X);
	putdown(B);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & on_table(X) & on(A, Y) & A \== X & clear(A) & on(B, X) & A \== B & B \== X & clear(B) & holding(Z) & A \== Z & B \== Z & X \== Z <-
	putdown(Z);
	unstack(A, Y);
	putdown(A);
	unstack(B, X);
	putdown(B);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & holding(Y) & on_table(X) & on(A, X) & A \== X & A \== Y & on(Z, A) & A \== Z & X \== Z & Y \== Z & clear(Z) <-
	putdown(Y);
	unstack(Z, A);
	putdown(Z);
	unstack(A, X);
	putdown(A);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(Y) & on_table(X) & on(A, X) & A \== X & A \== Y & on(Y, A) & holding(Z) & A \== Z & X \== Z & Y \== Z <-
	putdown(Z);
	unstack(Y, A);
	putdown(Y);
	unstack(A, X);
	putdown(A);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & holding(X) & on(B, Y) & B \== X & on(A, B) & A \== B & A \== X & clear(A) & clear(Z) & A \== Z & B \== Z & X \== Z <-
	stack(X, Z);
	unstack(A, B);
	putdown(A);
	unstack(B, Y);
	putdown(B);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(X) & on_table(X) & on(B, Y) & B \== X & on(A, B) & A \== B & A \== X & clear(A) & holding(Z) & A \== Z & B \== Z & X \== Z <-
	putdown(Z);
	unstack(A, B);
	putdown(A);
	unstack(B, Y);
	putdown(B);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & on_table(X) & arm_empty & on(B, X) & B \== X & on(A, B) & A \== B & A \== X & clear(A) & on(Z, Y) & A \== Z & B \== Z & X \== Z & clear(Z) <-
	unstack(Z, Y);
	putdown(Z);
	unstack(A, B);
	putdown(A);
	unstack(B, X);
	putdown(B);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(X) & arm_empty & on(A, Y) & A \== X & on(X, Z) & A \== Z & X \== Z & on(Z, A) <-
	unstack(X, Z);
	putdown(X);
	unstack(Z, A);
	putdown(Z);
	unstack(A, Y);
	putdown(A);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(Y) & on_table(X) & arm_empty & on(A, X) & A \== X & A \== Y & on(Y, Z) & A \== Z & X \== Z & Y \== Z & on(Z, A) <-
	unstack(Y, Z);
	putdown(Y);
	unstack(Z, A);
	putdown(Z);
	unstack(A, X);
	putdown(A);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & on_table(X) & arm_empty & on(A, X) & A \== X & A \== Y & on(Y, A) & on(Z, Y) & A \== Z & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, Y);
	putdown(Z);
	unstack(Y, A);
	putdown(Y);
	unstack(A, X);
	putdown(A);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(X) & arm_empty & on(B, Y) & B \== X & on(X, Z) & B \== Z & X \== Z & on(Z, B) & clear(A) & A \== B & A \== X & A \== Z <-
	unstack(X, Z);
	stack(X, A);
	unstack(Z, B);
	putdown(Z);
	unstack(B, Y);
	putdown(B);
	unstack(X, A);
	stack(X, Y).

+!on(X, Y) : X \== Y & arm_empty & on(A, Y) & A \== X & on(X, A) & on(Z, X) & A \== Z & X \== Z & clear(Z) <-
	unstack(Z, X);
	putdown(Z);
	unstack(X, A);
	stack(X, Z);
	unstack(A, Y);
	putdown(A);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : X \== Y & on_table(X) & arm_empty & on(B, Y) & B \== X & on(A, B) & A \== B & A \== X & clear(A) & on(Z, X) & A \== Z & B \== Z & X \== Z & clear(Z) <-
	unstack(Z, X);
	putdown(Z);
	unstack(A, B);
	putdown(A);
	unstack(B, Y);
	putdown(B);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & on_table(X) & arm_empty & on(A, Y) & A \== X & on(B, X) & A \== B & B \== X & clear(B) & on(Z, A) & A \== Z & B \== Z & X \== Z & clear(Z) <-
	unstack(Z, A);
	putdown(Z);
	unstack(A, Y);
	putdown(A);
	unstack(B, X);
	putdown(B);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & clear(X) & on(B, Y) & B \== X & on(A, B) & A \== B & A \== X & on(X, A) & holding(Z) & A \== Z & B \== Z & X \== Z <-
	putdown(Z);
	unstack(X, A);
	stack(X, Z);
	unstack(A, B);
	putdown(A);
	unstack(B, Y);
	putdown(B);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : X \== Y & on_table(X) & on(A, Y) & A \== X & A \== Y & clear(A) & on(B, X) & A \== B & B \== X & B \== Y & on(Y, B) & holding(Z) & A \== Z & B \== Z & X \== Z & Y \== Z <-
	putdown(Z);
	unstack(A, Y);
	putdown(A);
	unstack(Y, B);
	putdown(Y);
	unstack(B, X);
	putdown(B);
	pickup(X);
	stack(X, Y).

+!on(X, Y) : X \== Y & arm_empty & on(B, Y) & B \== X & on(A, B) & A \== B & A \== X & on(X, A) & on(Z, X) & A \== Z & B \== Z & X \== Z & clear(Z) <-
	unstack(Z, X);
	putdown(Z);
	unstack(X, A);
	stack(X, Z);
	unstack(A, B);
	putdown(A);
	unstack(B, Y);
	putdown(B);
	unstack(X, Z);
	stack(X, Y).

+!on(X, Y) : X \== Y & on_table(X) & arm_empty & on(A, Y) & A \== X & A \== Y & on(B, X) & A \== B & B \== X & B \== Y & on(Y, B) & on(Z, A) & A \== Z & B \== Z & X \== Z & Y \== Z & clear(Z) <-
	unstack(Z, A);
	putdown(Z);
	unstack(A, Y);
	putdown(A);
	unstack(Y, B);
	putdown(Y);
	unstack(B, X);
	putdown(B);
	pickup(X);
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
