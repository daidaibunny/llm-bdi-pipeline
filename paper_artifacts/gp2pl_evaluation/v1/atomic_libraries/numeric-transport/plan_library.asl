/* Generated AgentSpeak(L) Plan Library */
/* Domain: numeric-transport */

+!at(X, Y) : at(X, Y) <-
	true.

+!in(X, Y) : in(X, Y) <-
	true.

+!at(X, Y) : obj_tp(X, vehicle) & obj_tp(Y, location) & at(X, Z) & obj_tp(Z, location) & Y \== Z <-
	drive(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(Z, Y) & obj_tp(Z, vehicle) & in(X, Z) <-
	drop(Z, Y, X).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, A) & obj_tp(A, location) & A \== Y & at(Z, A) & obj_tp(Z, vehicle) & capacity(Z, N) & N >= 1 <-
	pick_up(Z, A, X);
	drive(Z, A, Y);
	drop(Z, Y, X).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, A) & obj_tp(A, location) & A \== Y & at(Z, B) & obj_tp(B, location) & obj_tp(Z, vehicle) & A \== B & B \== Y & capacity(Z, N) & N >= 1 <-
	drive(Z, B, A);
	pick_up(Z, A, X);
	drive(Z, A, Y);
	drop(Z, Y, X).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & in(X, B) & obj_tp(B, vehicle) & at(B, A) & obj_tp(A, location) & A \== Y & at(Z, A) & obj_tp(Z, vehicle) & B \== Z & capacity(Z, N) & N >= 1 <-
	drop(B, A, X);
	pick_up(Z, A, X);
	drive(Z, A, Y);
	drop(Z, Y, X).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & in(X, A) & obj_tp(A, vehicle) & at(A, Z) & obj_tp(Z, location) & Y \== Z & capacity(A, N) & N >= 0 <-
	drive(A, Z, Y);
	drop(A, Y, X).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, Z) & obj_tp(Z, location) & Y \== Z & at(A, Z) & obj_tp(A, vehicle) & A \== X & capacity(A, N) & N >= 1 <-
	pick_up(A, Z, X);
	drive(A, Z, Y);
	drop(A, Y, X).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, A) & obj_tp(A, location) & A \== Y & at(B, Z) & obj_tp(B, vehicle) & obj_tp(Z, location) & A \== Z & B \== X & Y \== Z & capacity(B, N) & N >= 1 <-
	drive(B, Z, A);
	pick_up(B, A, X);
	drive(B, A, Y);
	drop(B, Y, X).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(A, Y) & obj_tp(A, vehicle) & A \== X & at(X, Z) & obj_tp(Z, location) & Y \== Z & capacity(A, N) & N >= 1 <-
	drive(A, Y, Z);
	pick_up(A, Z, X);
	drive(A, Z, Y);
	drop(A, Y, X).

+!in(X, Y) : obj_tp(X, package) & obj_tp(Y, vehicle) & at(X, Z) & obj_tp(Z, location) & at(Y, Z) & capacity(Y, N) & N >= 1 <-
	pick_up(Y, Z, X).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(B, A) & obj_tp(A, location) & obj_tp(B, vehicle) & not in(X, B) & at(Z, A) & obj_tp(Z, vehicle) <-
	!in(X, B);
	!at(X, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(Z, Y) & obj_tp(Z, vehicle) & not in(X, Z) <-
	!in(X, Z);
	!at(X, Y).

+!in(X, Y) : obj_tp(X, package) & obj_tp(Y, vehicle) & at(Y, Z) & obj_tp(Z, location) & not at(X, Z) <-
	!at(X, Z);
	!in(X, Y).

+!in(X, Y) : obj_tp(X, package) & obj_tp(Y, vehicle) & at(X, Z) & obj_tp(Z, location) & not at(Y, Z) <-
	!at(Y, Z);
	!in(X, Y).
