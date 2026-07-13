/* Generated AgentSpeak(L) Plan Library */
/* Domain: transport */

+!at(X, Y) : at(X, Y) <-
	true.

+!capacity(X, Y) : capacity(X, Y) <-
	true.

+!in(X, Y) : in(X, Y) <-
	true.

+!at(X, Y) : obj_tp(X, vehicle) & obj_tp(Y, location) & at(X, Z) & obj_tp(Z, location) & Y \== Z <-
	drive(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(B, Y) & obj_tp(B, vehicle) & in(X, B) & capacity(B, Z) & obj_tp(Z, size) & capacity_predecessor(Z, A) & obj_tp(A, size) <-
	drop(B, Y, X, Z, A).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & in(X, C) & obj_tp(C, vehicle) & at(C, Z) & obj_tp(Z, location) & Y \== Z & capacity(C, A) & obj_tp(A, size) & capacity_predecessor(A, B) & obj_tp(B, size) <-
	drive(C, Z, Y);
	drop(C, Y, X, A, B).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, Z) & obj_tp(Z, location) & Y \== Z & at(C, Z) & obj_tp(C, vehicle) & C \== X & capacity(C, B) & obj_tp(B, size) & capacity_predecessor(A, B) & obj_tp(A, size) & A \== B <-
	pick_up(C, Z, X, A, B);
	drive(C, Z, Y);
	drop(C, Y, X, A, B).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, A) & obj_tp(A, location) & A \== Y & at(D, Z) & obj_tp(D, vehicle) & obj_tp(Z, location) & A \== Z & D \== X & Y \== Z & capacity(D, C) & obj_tp(C, size) & capacity_predecessor(B, C) & obj_tp(B, size) & B \== C <-
	drive(D, Z, A);
	pick_up(D, A, X, B, C);
	drive(D, A, Y);
	drop(D, Y, X, B, C).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(C, Y) & obj_tp(C, vehicle) & C \== X & at(X, Z) & obj_tp(Z, location) & Y \== Z & capacity(C, B) & obj_tp(B, size) & capacity_predecessor(A, B) & obj_tp(A, size) & A \== B <-
	drive(C, Y, Z);
	pick_up(C, Z, X, A, B);
	drive(C, Z, Y);
	drop(C, Y, X, A, B).

+!capacity(X, Y) : obj_tp(X, vehicle) & obj_tp(Y, size) & at(X, Z) & obj_tp(Z, location) & capacity(X, B) & obj_tp(B, size) & B \== Y & capacity_predecessor(B, Y) & in(A, X) & obj_tp(A, package) <-
	drop(X, Z, A, B, Y).

+!capacity(X, Y) : obj_tp(X, vehicle) & obj_tp(Y, size) & at(X, Z) & obj_tp(Z, location) & at(A, Z) & obj_tp(A, package) & capacity(X, B) & obj_tp(B, size) & B \== Y & capacity_predecessor(Y, B) <-
	pick_up(X, Z, A, Y, B).

+!in(X, Y) : obj_tp(X, package) & obj_tp(Y, vehicle) & at(X, Z) & obj_tp(Z, location) & at(Y, Z) & capacity(Y, B) & obj_tp(B, size) & capacity_predecessor(A, B) & obj_tp(A, size) <-
	pick_up(Y, Z, X, A, B).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(Z, Y) & obj_tp(Z, vehicle) & in(X, Z) & capacity_predecessor(A, B) & obj_tp(A, size) & obj_tp(B, size) & not capacity(Z, A) <-
	!capacity(Z, A);
	!at(X, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(Z, Y) & obj_tp(Z, vehicle) & not in(X, Z) & capacity(Z, A) & obj_tp(A, size) & capacity_predecessor(A, B) & obj_tp(B, size) <-
	!in(X, Z);
	!at(X, Y).

+!capacity(X, Y) : obj_tp(X, vehicle) & obj_tp(Y, size) & capacity(X, B) & obj_tp(B, size) & capacity_predecessor(Y, B) & at(A, Z) & obj_tp(A, package) & obj_tp(Z, location) & not at(X, Z) <-
	!at(X, Z);
	!capacity(X, Y).

+!in(X, Y) : obj_tp(X, package) & obj_tp(Y, vehicle) & at(Y, Z) & obj_tp(Z, location) & not at(X, Z) & capacity(Y, B) & obj_tp(B, size) & capacity_predecessor(A, B) & obj_tp(A, size) <-
	!at(X, Z);
	!in(X, Y).

+!in(X, Y) : obj_tp(X, package) & obj_tp(Y, vehicle) & at(X, Z) & obj_tp(Z, location) & not at(Y, Z) & capacity(Y, B) & obj_tp(B, size) & capacity_predecessor(A, B) & obj_tp(A, size) <-
	!at(Y, Z);
	!in(X, Y).

+!in(X, Y) : obj_tp(X, package) & obj_tp(Y, vehicle) & at(X, Z) & obj_tp(Z, location) & at(Y, Z) & capacity_predecessor(A, B) & obj_tp(A, size) & obj_tp(B, size) & not capacity(Y, B) <-
	!capacity(Y, B);
	!in(X, Y).
