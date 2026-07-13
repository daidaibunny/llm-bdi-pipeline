/* Generated AgentSpeak(L) Plan Library */
/* Domain: gripper */

+!at(X, Y) : at(X, Y) <-
	true.

+!at_robby(X) : at_robby(X) <-
	true.

+!carry(X, Y) : carry(X, Y) <-
	true.

+!free(X) : free(X) <-
	true.

+!at(X, Y) : at_robby(Y) & ball(X) & room(Y) & carry(X, Z) & gripper(Z) <-
	drop(X, Y, Z).

+!at(X, Y) : ball(X) & room(Y) & at(X, A) & A \== Y & at_robby(A) & room(A) & free(Z) & gripper(Z) <-
	pick(X, A, Z);
	move(A, Y);
	drop(X, Y, Z).

+!at(X, Y) : ball(X) & room(Y) & carry(X, B) & gripper(B) & at_robby(A) & A \== Y & room(A) & free(Z) & B \== Z & gripper(Z) <-
	drop(X, A, B);
	pick(X, A, Z);
	move(A, Y);
	drop(X, Y, Z).

+!at(X, Y) : ball(X) & room(Y) & at(X, A) & A \== Y & room(A) & at_robby(B) & A \== B & B \== Y & room(B) & free(Z) & gripper(Z) <-
	move(B, A);
	pick(X, A, Z);
	move(A, Y);
	drop(X, Y, Z).

+!at(X, Y) : ball(X) & room(Y) & carry(X, A) & gripper(A) & at_robby(Z) & Y \== Z & room(Z) <-
	move(Z, Y);
	drop(X, Y, A).

+!at(X, Y) : ball(X) & room(Y) & at(X, Z) & Y \== Z & at_robby(Z) & room(Z) & free(A) & gripper(A) <-
	pick(X, Z, A);
	move(Z, Y);
	drop(X, Y, A).

+!at(X, Y) : at_robby(Y) & ball(X) & room(Y) & at(X, Z) & Y \== Z & room(Z) & free(A) & gripper(A) <-
	move(Y, Z);
	pick(X, Z, A);
	move(Z, Y);
	drop(X, Y, A).

+!at_robby(X) : room(X) & at_robby(Y) & X \== Y & room(Y) <-
	move(Y, X).

+!carry(X, Y) : ball(X) & free(Y) & gripper(Y) & at(X, Z) & at_robby(Z) & room(Z) <-
	pick(X, Z, Y).

+!carry(X, Y) : ball(X) & free(Y) & gripper(Y) & carry(X, A) & A \== Y & gripper(A) & at_robby(Z) & room(Z) <-
	drop(X, Z, A);
	pick(X, Z, Y).

+!free(X) : gripper(X) & carry(Y, X) & ball(Y) & at_robby(Z) & room(Z) <-
	drop(Y, Z, X).

+!at(X, Y) : ball(X) & room(Y) & gripper(B) & not carry(X, B) <-
	!carry(X, B);
	!at(X, Y).

+!at(X, Y) : at_robby(Y) & ball(X) & room(Y) & gripper(Z) & not carry(X, Z) <-
	!carry(X, Z);
	!at(X, Y).

+!at(X, Y) : ball(X) & room(Y) & gripper(Z) & not free(Z) <-
	!free(Z);
	!at(X, Y).

+!at(X, Y) : ball(X) & room(Y) & at(X, A) & room(A) & not at_robby(A) <-
	!at_robby(A);
	!at(X, Y).

+!at(X, Y) : ball(X) & room(Y) & carry(X, B) & gripper(B) & room(A) & not at_robby(A) <-
	!at_robby(A);
	!at(X, Y).

+!at(X, Y) : ball(X) & room(Y) & room(B) & not at_robby(B) <-
	!at_robby(B);
	!at(X, Y).

+!at(X, Y) : not at_robby(Y) <-
	!at_robby(Y);
	!at(X, Y).

+!carry(X, Y) : ball(X) & free(Y) & gripper(Y) & room(Z) & not at_robby(Z) <-
	!at_robby(Z);
	!carry(X, Y).

+!carry(X, Y) : ball(X) & free(Y) & gripper(Y) & at_robby(Z) & room(Z) & not at(X, Z) <-
	!at(X, Z);
	!carry(X, Y).

+!carry(X, Y) : not free(Y) <-
	!free(Y);
	!carry(X, Y).

+!free(X) : gripper(X) & room(Z) & not at_robby(Z) <-
	!at_robby(Z);
	!free(X).
