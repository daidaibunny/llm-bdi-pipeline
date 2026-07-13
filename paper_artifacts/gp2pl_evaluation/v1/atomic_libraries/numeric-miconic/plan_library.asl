/* Generated AgentSpeak(L) Plan Library */
/* Domain: numeric-miconic */

+!boarded(X) : boarded(X) <-
	true.

+!lift_at(X) : lift_at(X) <-
	true.

+!move_slow_half : move_slow_half <-
	true.

+!served(X) : served(X) <-
	true.

+!boarded(X) : obj_tp(X, passenger) & origin(X, Y) & obj_tp(Y, floor) & lift_at(Y) & lift_capacity(N) & N >= 1 <-
	board(Y, X).

+!lift_at(X) : obj_tp(X, floor) & above(X, Y) & obj_tp(Y, floor) & X \== Y & lift_at(Y) & lift_capacity(N) & N >= 1 <-
	down_fast(Y, X).

+!lift_at(X) : obj_tp(X, floor) & move_slow_half & above(X, Y) & obj_tp(Y, floor) & X \== Y & lift_at(Y) <-
	down_slow_part_2(Y, X).

+!lift_at(X) : obj_tp(X, floor) & above(Y, X) & obj_tp(Y, floor) & X \== Y & lift_at(Y) & lift_capacity(N) & N >= 1 <-
	up_fast(Y, X).

+!lift_at(X) : obj_tp(X, floor) & move_slow_half & above(Y, X) & obj_tp(Y, floor) & X \== Y & lift_at(Y) <-
	up_slow_part_2(Y, X).

+!move_slow_half : lift_at(X) & obj_tp(X, floor) & above(Y, X) & obj_tp(Y, floor) <-
	down_slow_part_1(X, Y).

+!move_slow_half : lift_at(X) & obj_tp(X, floor) & above(X, Y) & obj_tp(Y, floor) <-
	up_slow_part_1(X, Y).

+!served(X) : obj_tp(X, passenger) & boarded(X) & destin(X, Y) & obj_tp(Y, floor) & lift_at(Y) <-
	depart(Y, X).

+!served(X) : obj_tp(X, passenger) & boarded(X) & destin(X, Z) & obj_tp(Z, floor) & above(Z, Y) & obj_tp(Y, floor) & Y \== Z & lift_at(Y) & lift_capacity(N) & N >= 1 <-
	down_fast(Y, Z);
	depart(Z, X).

+!served(X) : obj_tp(X, passenger) & boarded(X) & destin(X, Z) & obj_tp(Z, floor) & above(Y, Z) & obj_tp(Y, floor) & Y \== Z & lift_at(Y) & lift_capacity(N) & N >= 1 <-
	up_fast(Y, Z);
	depart(Z, X).

+!served(X) : obj_tp(X, passenger) & destin(X, Z) & obj_tp(Z, floor) & above(Y, Z) & obj_tp(Y, floor) & Y \== Z & origin(X, Y) & lift_at(Y) & lift_capacity(N) & N >= 1 <-
	board(Y, X);
	up_fast(Y, Z);
	depart(Z, X).

+!served(X) : obj_tp(X, passenger) & destin(X, Z) & obj_tp(Z, floor) & above(Z, Y) & obj_tp(Y, floor) & Y \== Z & origin(X, Y) & lift_at(Y) & lift_capacity(N) & N >= 1 <-
	board(Y, X);
	down_fast(Y, Z);
	depart(Z, X).

+!served(X) : obj_tp(X, passenger) & destin(X, Y) & obj_tp(Y, floor) & lift_at(Y) & above(Y, Z) & obj_tp(Z, floor) & Y \== Z & origin(X, Z) & lift_capacity(N) & N >= 1 <-
	up_fast(Y, Z);
	board(Z, X);
	down_fast(Z, Y);
	depart(Y, X).

+!served(X) : obj_tp(X, passenger) & destin(X, A) & obj_tp(A, floor) & above(A, Z) & obj_tp(Z, floor) & A \== Z & origin(X, Z) & above(Y, Z) & obj_tp(Y, floor) & A \== Y & Y \== Z & lift_at(Y) & lift_capacity(N) & N >= 1 <-
	up_fast(Y, Z);
	board(Z, X);
	down_fast(Z, A);
	depart(A, X).

+!served(X) : obj_tp(X, passenger) & destin(X, Y) & obj_tp(Y, floor) & lift_at(Y) & above(Z, Y) & obj_tp(Z, floor) & Y \== Z & origin(X, Z) & lift_capacity(N) & N >= 1 <-
	down_fast(Y, Z);
	board(Z, X);
	up_fast(Z, Y);
	depart(Y, X).

+!served(X) : obj_tp(X, passenger) & destin(X, A) & obj_tp(A, floor) & above(Z, A) & obj_tp(Z, floor) & A \== Z & origin(X, Z) & above(Y, Z) & obj_tp(Y, floor) & A \== Y & Y \== Z & lift_at(Y) & lift_capacity(N) & N >= 1 <-
	up_fast(Y, Z);
	board(Z, X);
	up_fast(Z, A);
	depart(A, X).

+!served(X) : obj_tp(X, passenger) & destin(X, A) & obj_tp(A, floor) & above(Z, A) & obj_tp(Z, floor) & A \== Z & origin(X, Z) & above(Z, Y) & obj_tp(Y, floor) & A \== Y & Y \== Z & lift_at(Y) & lift_capacity(N) & N >= 1 <-
	down_fast(Y, Z);
	board(Z, X);
	up_fast(Z, A);
	depart(A, X).

+!served(X) : obj_tp(X, passenger) & destin(X, A) & obj_tp(A, floor) & above(A, Z) & obj_tp(Z, floor) & A \== Z & origin(X, Z) & above(Z, Y) & obj_tp(Y, floor) & A \== Y & Y \== Z & lift_at(Y) & lift_capacity(N) & N >= 1 <-
	down_fast(Y, Z);
	board(Z, X);
	down_fast(Z, A);
	depart(A, X).

+!boarded(X) : obj_tp(X, passenger) & origin(X, Y) & obj_tp(Y, floor) & not lift_at(Y) <-
	!lift_at(Y);
	!boarded(X).

+!lift_at(X) : obj_tp(X, floor) & not move_slow_half <-
	!move_slow_half;
	!lift_at(X).

+!served(X) : obj_tp(X, passenger) & not boarded(X) <-
	!boarded(X);
	!served(X).

+!served(X) : obj_tp(X, passenger) & boarded(X) & destin(X, Y) & obj_tp(Y, floor) & not lift_at(Y) <-
	!lift_at(Y);
	!served(X).
