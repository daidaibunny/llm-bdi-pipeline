/* Generated AgentSpeak(L) Plan Library */
/* Domain: miconic */

+!boarded(X) : boarded(X) <-
	true.

+!lift_at(X) : lift_at(X) <-
	true.

+!served(X) : served(X) <-
	true.

+!boarded(X) : obj_tp(X, passenger) & origin(X, Y) & obj_tp(Y, floor) & lift_at(Y) <-
	board(Y, X).

+!lift_at(X) : obj_tp(X, floor) & above(X, Y) & obj_tp(Y, floor) & X \== Y & lift_at(Y) <-
	down(Y, X).

+!lift_at(X) : obj_tp(X, floor) & above(Y, X) & obj_tp(Y, floor) & X \== Y & lift_at(Y) <-
	up(Y, X).

+!served(X) : obj_tp(X, passenger) & boarded(X) & destin(X, Y) & obj_tp(Y, floor) & lift_at(Y) <-
	depart(Y, X).

+!served(X) : obj_tp(X, passenger) & boarded(X) & destin(X, Z) & obj_tp(Z, floor) & above(Z, Y) & obj_tp(Y, floor) & Y \== Z & lift_at(Y) <-
	down(Y, Z);
	depart(Z, X).

+!served(X) : obj_tp(X, passenger) & boarded(X) & destin(X, Z) & obj_tp(Z, floor) & above(Y, Z) & obj_tp(Y, floor) & Y \== Z & lift_at(Y) <-
	up(Y, Z);
	depart(Z, X).

+!served(X) : obj_tp(X, passenger) & destin(X, Z) & obj_tp(Z, floor) & above(Y, Z) & obj_tp(Y, floor) & Y \== Z & origin(X, Y) & lift_at(Y) <-
	board(Y, X);
	up(Y, Z);
	depart(Z, X).

+!served(X) : obj_tp(X, passenger) & destin(X, Z) & obj_tp(Z, floor) & above(Z, Y) & obj_tp(Y, floor) & Y \== Z & origin(X, Y) & lift_at(Y) <-
	board(Y, X);
	down(Y, Z);
	depart(Z, X).

+!served(X) : obj_tp(X, passenger) & destin(X, A) & obj_tp(A, floor) & above(A, Z) & obj_tp(Z, floor) & A \== Z & origin(X, Z) & above(Y, Z) & obj_tp(Y, floor) & A \== Y & Y \== Z & lift_at(Y) <-
	up(Y, Z);
	board(Z, X);
	down(Z, A);
	depart(A, X).

+!served(X) : obj_tp(X, passenger) & destin(X, Y) & obj_tp(Y, floor) & lift_at(Y) & above(Z, Y) & obj_tp(Z, floor) & Y \== Z & origin(X, Z) <-
	down(Y, Z);
	board(Z, X);
	up(Z, Y);
	depart(Y, X).

+!served(X) : obj_tp(X, passenger) & destin(X, A) & obj_tp(A, floor) & above(Z, A) & obj_tp(Z, floor) & A \== Z & origin(X, Z) & above(Z, Y) & obj_tp(Y, floor) & A \== Y & Y \== Z & lift_at(Y) <-
	down(Y, Z);
	board(Z, X);
	up(Z, A);
	depart(A, X).

+!served(X) : obj_tp(X, passenger) & destin(X, A) & obj_tp(A, floor) & above(A, Z) & obj_tp(Z, floor) & A \== Z & origin(X, Z) & above(Z, Y) & obj_tp(Y, floor) & A \== Y & Y \== Z & lift_at(Y) <-
	down(Y, Z);
	board(Z, X);
	down(Z, A);
	depart(A, X).

+!served(X) : obj_tp(X, passenger) & destin(X, A) & obj_tp(A, floor) & above(Z, A) & obj_tp(Z, floor) & A \== Z & origin(X, Z) & above(Y, Z) & obj_tp(Y, floor) & A \== Y & Y \== Z & lift_at(Y) <-
	up(Y, Z);
	board(Z, X);
	up(Z, A);
	depart(A, X).

+!served(X) : obj_tp(X, passenger) & destin(X, Y) & obj_tp(Y, floor) & lift_at(Y) & above(Y, Z) & obj_tp(Z, floor) & Y \== Z & origin(X, Z) <-
	up(Y, Z);
	board(Z, X);
	down(Z, Y);
	depart(Y, X).

+!boarded(X) : obj_tp(X, passenger) & origin(X, Y) & obj_tp(Y, floor) & not lift_at(Y) <-
	!lift_at(Y);
	!boarded(X).

+!served(X) : obj_tp(X, passenger) & not boarded(X) <-
	!boarded(X);
	!served(X).

+!served(X) : obj_tp(X, passenger) & boarded(X) & destin(X, Y) & obj_tp(Y, floor) & not lift_at(Y) <-
	!lift_at(Y);
	!served(X).
