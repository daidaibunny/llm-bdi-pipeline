/* Generated AgentSpeak(L) Plan Library */
/* Domain: ferry */

+!at(X, Y) : at(X, Y) <-
	true.

+!at_ferry(X) : at_ferry(X) <-
	true.

+!empty_ferry : empty_ferry <-
	true.

+!on(X) : on(X) <-
	true.

+!at(X, Y) : obj_tp(X, car) & obj_tp(Y, location) & at_ferry(Y) & on(X) <-
	debark(X, Y).

+!at(X, Y) : obj_tp(X, car) & obj_tp(Y, location) & empty_ferry & not at_ferry(Y) & at(X, Z) & obj_tp(Z, location) & Y \== Z & at_ferry(Z) <-
	board(X, Z);
	sail(Z, Y);
	debark(X, Y).

+!at(X, Y) : obj_tp(X, car) & obj_tp(Y, location) & on(X) & not at_ferry(Y) & at_ferry(Z) & obj_tp(Z, location) & Y \== Z <-
	debark(X, Z);
	board(X, Z);
	sail(Z, Y);
	debark(X, Y).

+!at(X, Y) : obj_tp(X, car) & obj_tp(Y, location) & empty_ferry & not at_ferry(Y) & at(X, Z) & obj_tp(Z, location) & Y \== Z & not at_ferry(Z) & at_ferry(A) & obj_tp(A, location) & A \== Y & A \== Z <-
	sail(A, Z);
	board(X, Z);
	sail(Z, Y);
	debark(X, Y).

+!at(X, Y) : obj_tp(X, car) & obj_tp(Y, location) & on(X) & at_ferry(Z) & obj_tp(Z, location) & Y \== Z <-
	sail(Z, Y);
	debark(X, Y).

+!at(X, Y) : obj_tp(X, car) & obj_tp(Y, location) & empty_ferry & at(X, Z) & obj_tp(Z, location) & Y \== Z & at_ferry(Z) <-
	board(X, Z);
	sail(Z, Y);
	debark(X, Y).

+!at(X, Y) : obj_tp(X, car) & obj_tp(Y, location) & empty_ferry & at(X, A) & obj_tp(A, location) & A \== Y & at_ferry(Z) & obj_tp(Z, location) & A \== Z & Y \== Z <-
	sail(Z, A);
	board(X, A);
	sail(A, Y);
	debark(X, Y).

+!at(X, Y) : obj_tp(X, car) & obj_tp(Y, location) & at_ferry(Y) & empty_ferry & at(X, Z) & obj_tp(Z, location) & Y \== Z <-
	sail(Y, Z);
	board(X, Z);
	sail(Z, Y);
	debark(X, Y).

+!at_ferry(X) : obj_tp(X, location) & not at_ferry(X) & at_ferry(Y) & obj_tp(Y, location) & X \== Y <-
	sail(Y, X).

+!empty_ferry : at_ferry(Y) & obj_tp(Y, location) & on(X) & obj_tp(X, car) <-
	debark(X, Y).

+!on(X) : obj_tp(X, car) & empty_ferry & at(X, Y) & obj_tp(Y, location) & at_ferry(Y) <-
	board(X, Y).

+!at(X, Y) : obj_tp(X, car) & obj_tp(Y, location) & not on(X) <-
	!on(X);
	!at(X, Y).

+!at(X, Y) : obj_tp(X, car) & obj_tp(Y, location) & not at_ferry(Y) <-
	!at_ferry(Y);
	!at(X, Y).

+!at(X, Y) : obj_tp(X, car) & obj_tp(Y, location) & at(X, Z) & obj_tp(Z, location) & not at_ferry(Z) <-
	!at_ferry(Z);
	!at(X, Y).

+!at(X, Y) : obj_tp(X, car) & obj_tp(Y, location) & not empty_ferry <-
	!empty_ferry;
	!at(X, Y).

+!on(X) : obj_tp(X, car) & at(X, Y) & obj_tp(Y, location) & not at_ferry(Y) <-
	!at_ferry(Y);
	!on(X).

+!on(X) : obj_tp(X, car) & not empty_ferry <-
	!empty_ferry;
	!on(X).
