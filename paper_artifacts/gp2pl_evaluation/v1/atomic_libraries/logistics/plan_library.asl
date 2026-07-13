/* Generated AgentSpeak(L) Plan Library */
/* Domain: logistics */

+!at(X, Y) : at(X, Y) <-
	true.

+!in(X, Y) : in(X, Y) <-
	true.

+!at(X, Y) : obj_tp(X, truck) & obj_tp(Y, location) & at(X, Z) & obj_tp(Z, location) & Y \== Z & in_city(Y, A) & obj_tp(A, city) & in_city(Z, A) <-
	drive_truck(X, Z, Y, A).

+!at(X, Y) : obj_tp(X, airplane) & obj_tp(Y, location) & has_airport(Y) & at(X, Z) & obj_tp(Z, location) & Y \== Z & has_airport(Z) <-
	fly_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(Z, Y) & obj_tp(Z, airplane) & in(X, Z) <-
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(Z, Y) & obj_tp(Z, truck) & in(X, Z) <-
	unload_truck(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & at(X, A) & obj_tp(A, location) & A \== Y & has_airport(A) & at(Z, A) & obj_tp(Z, airplane) <-
	load_airplane(X, Z, A);
	fly_airplane(Z, A, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, A) & obj_tp(A, location) & A \== Y & at(Z, A) & obj_tp(Z, truck) & in_city(A, B) & obj_tp(B, city) & in_city(Y, B) <-
	load_truck(X, Z, A);
	drive_truck(Z, A, Y, B);
	unload_truck(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, A) & obj_tp(A, location) & A \== Y & in_city(A, B) & obj_tp(B, city) & in_city(Y, B) & in_city(A, D) & obj_tp(D, city) & in_city(C, D) & obj_tp(C, location) & A \== C & C \== Y & at(Z, C) & obj_tp(Z, truck) <-
	drive_truck(Z, C, A, D);
	load_truck(X, Z, A);
	drive_truck(Z, A, Y, B);
	unload_truck(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & at(X, A) & obj_tp(A, location) & A \== Y & has_airport(A) & has_airport(B) & obj_tp(B, location) & A \== B & B \== Y & at(Z, B) & obj_tp(Z, airplane) <-
	fly_airplane(Z, B, A);
	load_airplane(X, Z, A);
	fly_airplane(Z, A, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & in(X, B) & obj_tp(B, airplane) & at(B, A) & obj_tp(A, location) & A \== Y & has_airport(A) & at(Z, A) & obj_tp(Z, airplane) & B \== Z <-
	unload_airplane(X, B, A);
	load_airplane(X, Z, A);
	fly_airplane(Z, A, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & in(X, C) & obj_tp(C, airplane) & at(C, A) & obj_tp(A, location) & A \== Y & at(Z, A) & obj_tp(Z, truck) & in_city(A, B) & obj_tp(B, city) & in_city(Y, B) <-
	unload_airplane(X, C, A);
	load_truck(X, Z, A);
	drive_truck(Z, A, Y, B);
	unload_truck(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & in(X, B) & obj_tp(B, truck) & at(B, A) & obj_tp(A, location) & A \== Y & has_airport(A) & at(Z, A) & obj_tp(Z, airplane) <-
	unload_truck(X, B, A);
	load_airplane(X, Z, A);
	fly_airplane(Z, A, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & in(X, C) & obj_tp(C, truck) & at(C, A) & obj_tp(A, location) & A \== Y & at(Z, A) & obj_tp(Z, truck) & C \== Z & in_city(A, B) & obj_tp(B, city) & in_city(Y, B) <-
	unload_truck(X, C, A);
	load_truck(X, Z, A);
	drive_truck(Z, A, Y, B);
	unload_truck(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & in(X, B) & obj_tp(B, truck) & at(B, A) & obj_tp(A, location) & A \== Y & in_city(A, Z) & obj_tp(Z, city) & in_city(Y, Z) <-
	drive_truck(B, A, Y, Z);
	unload_truck(X, B, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & in(X, Z) & obj_tp(Z, airplane) & at(Z, A) & obj_tp(A, location) & A \== Y & has_airport(A) <-
	fly_airplane(Z, A, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, A) & obj_tp(A, location) & A \== Y & at(B, A) & obj_tp(B, truck) & B \== X & in_city(A, Z) & obj_tp(Z, city) & in_city(Y, Z) <-
	load_truck(X, B, A);
	drive_truck(B, A, Y, Z);
	unload_truck(X, B, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & at(X, A) & obj_tp(A, location) & A \== Y & has_airport(A) & at(Z, A) & obj_tp(Z, airplane) & X \== Z <-
	load_airplane(X, Z, A);
	fly_airplane(Z, A, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(B, Y) & obj_tp(B, truck) & B \== X & at(X, A) & obj_tp(A, location) & A \== Y & in_city(A, Z) & obj_tp(Z, city) & in_city(Y, Z) <-
	drive_truck(B, Y, A, Z);
	load_truck(X, B, A);
	drive_truck(B, A, Y, Z);
	unload_truck(X, B, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & in(X, B) & obj_tp(B, truck) & at(B, A) & obj_tp(A, location) & A \== Y & has_airport(A) & at(Z, A) & obj_tp(Z, airplane) & B \== Z & X \== Z <-
	unload_truck(X, B, A);
	load_airplane(X, Z, A);
	fly_airplane(Z, A, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & at(X, A) & obj_tp(A, location) & A \== Y & has_airport(A) & at(Z, Y) & obj_tp(Z, airplane) & X \== Z <-
	fly_airplane(Z, Y, A);
	load_airplane(X, Z, A);
	fly_airplane(Z, A, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & at(X, B) & obj_tp(B, location) & B \== Y & has_airport(B) & has_airport(A) & obj_tp(A, location) & A \== B & A \== Y & at(Z, A) & obj_tp(Z, airplane) & X \== Z <-
	fly_airplane(Z, A, B);
	load_airplane(X, Z, B);
	fly_airplane(Z, B, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & in(X, Z) & obj_tp(Z, airplane) & at(Z, B) & obj_tp(B, location) & B \== Y & at(C, B) & obj_tp(C, truck) & C \== X & C \== Z & in_city(B, A) & obj_tp(A, city) & in_city(Y, A) <-
	unload_airplane(X, Z, B);
	load_truck(X, C, B);
	drive_truck(C, B, Y, A);
	unload_truck(X, C, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, B) & obj_tp(B, location) & B \== Y & in_city(B, Z) & obj_tp(Z, city) & in_city(Y, Z) & in_city(A, Z) & obj_tp(A, location) & A \== B & A \== Y & at(C, A) & obj_tp(C, truck) & C \== X <-
	drive_truck(C, A, B, Z);
	load_truck(X, C, B);
	drive_truck(C, B, Y, Z);
	unload_truck(X, C, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & in(X, D) & obj_tp(D, truck) & D \== X & at(D, B) & obj_tp(B, location) & in_city(B, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & B \== C & C \== Y & has_airport(C) & at(Z, C) & obj_tp(Z, airplane) & D \== Z & X \== Z <-
	drive_truck(D, B, C, A);
	unload_truck(X, D, C);
	load_airplane(X, Z, C);
	fly_airplane(Z, C, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & at(Z, Y) & obj_tp(Z, airplane) & X \== Z & in(X, B) & obj_tp(B, truck) & B \== Z & at(B, A) & obj_tp(A, location) & A \== Y & has_airport(A) <-
	unload_truck(X, B, A);
	fly_airplane(Z, Y, A);
	load_airplane(X, Z, A);
	fly_airplane(Z, A, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & in(X, C) & obj_tp(C, truck) & at(C, A) & obj_tp(A, location) & A \== Y & has_airport(A) & has_airport(B) & obj_tp(B, location) & A \== B & B \== Y & at(Z, B) & obj_tp(Z, airplane) & C \== Z & X \== Z <-
	unload_truck(X, C, A);
	fly_airplane(Z, B, A);
	load_airplane(X, Z, A);
	fly_airplane(Z, A, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & in(X, Z) & obj_tp(Z, airplane) & X \== Z & at(Z, B) & obj_tp(B, location) & has_airport(B) & in_city(Y, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & B \== C & C \== Y & has_airport(C) & at(D, C) & obj_tp(D, truck) & D \== X & D \== Z <-
	fly_airplane(Z, B, C);
	unload_airplane(X, Z, C);
	load_truck(X, D, C);
	drive_truck(D, C, Y, A);
	unload_truck(X, D, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(C, Y) & obj_tp(C, truck) & C \== X & in(X, Z) & obj_tp(Z, airplane) & C \== Z & at(Z, B) & obj_tp(B, location) & B \== Y & in_city(B, A) & obj_tp(A, city) & in_city(Y, A) <-
	unload_airplane(X, Z, B);
	drive_truck(C, Y, B, A);
	load_truck(X, C, B);
	drive_truck(C, B, Y, A);
	unload_truck(X, C, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & at(Z, Y) & obj_tp(Z, airplane) & X \== Z & in(X, D) & obj_tp(D, truck) & D \== X & D \== Z & at(D, B) & obj_tp(B, location) & in_city(B, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & B \== C & C \== Y & has_airport(C) <-
	drive_truck(D, B, C, A);
	unload_truck(X, D, C);
	fly_airplane(Z, Y, C);
	load_airplane(X, Z, C);
	fly_airplane(Z, C, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & in(X, V7) & obj_tp(V7, truck) & V7 \== X & at(V7, B) & obj_tp(B, location) & in_city(B, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & B \== C & C \== Y & has_airport(C) & has_airport(D) & obj_tp(D, location) & C \== D & D \== Y & at(Z, D) & obj_tp(Z, airplane) & V7 \== Z & X \== Z <-
	drive_truck(V7, B, C, A);
	unload_truck(X, V7, C);
	fly_airplane(Z, D, C);
	load_airplane(X, Z, C);
	fly_airplane(Z, C, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(D, Y) & obj_tp(D, truck) & D \== X & in(X, Z) & obj_tp(Z, airplane) & D \== Z & X \== Z & at(Z, B) & obj_tp(B, location) & has_airport(B) & in_city(Y, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & B \== C & C \== Y & has_airport(C) <-
	fly_airplane(Z, B, C);
	unload_airplane(X, Z, C);
	drive_truck(D, Y, C, A);
	load_truck(X, D, C);
	drive_truck(D, C, Y, A);
	unload_truck(X, D, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & at(X, B) & obj_tp(B, location) & at(D, B) & obj_tp(D, truck) & D \== X & in_city(B, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & B \== C & C \== Y & has_airport(C) & at(Z, C) & obj_tp(Z, airplane) & D \== Z & X \== Z <-
	load_truck(X, D, B);
	drive_truck(D, B, C, A);
	unload_truck(X, D, C);
	load_airplane(X, Z, C);
	fly_airplane(Z, C, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, B) & obj_tp(B, location) & has_airport(B) & at(Z, B) & obj_tp(Z, airplane) & X \== Z & in_city(Y, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & B \== C & C \== Y & has_airport(C) & at(D, C) & obj_tp(D, truck) & D \== X & D \== Z <-
	load_airplane(X, Z, B);
	fly_airplane(Z, B, C);
	unload_airplane(X, Z, C);
	load_truck(X, D, C);
	drive_truck(D, C, Y, A);
	unload_truck(X, D, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & at(X, B) & obj_tp(B, location) & at(V7, B) & obj_tp(V7, truck) & V7 \== X & in_city(B, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & B \== C & C \== Y & has_airport(C) & has_airport(D) & obj_tp(D, location) & C \== D & D \== Y & at(Z, D) & obj_tp(Z, airplane) & V7 \== Z & X \== Z <-
	load_truck(X, V7, B);
	drive_truck(V7, B, C, A);
	unload_truck(X, V7, C);
	fly_airplane(Z, D, C);
	load_airplane(X, Z, C);
	fly_airplane(Z, C, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(D, Y) & obj_tp(D, truck) & D \== X & at(X, B) & obj_tp(B, location) & has_airport(B) & at(Z, B) & obj_tp(Z, airplane) & D \== Z & X \== Z & in_city(Y, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & B \== C & C \== Y & has_airport(C) <-
	load_airplane(X, Z, B);
	fly_airplane(Z, B, C);
	unload_airplane(X, Z, C);
	drive_truck(D, Y, C, A);
	load_truck(X, D, C);
	drive_truck(D, C, Y, A);
	unload_truck(X, D, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & in(X, D) & obj_tp(D, truck) & at(D, B) & obj_tp(B, location) & has_airport(B) & at(Z, B) & obj_tp(Z, airplane) & D \== Z & X \== Z & in_city(Y, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & B \== C & C \== Y & has_airport(C) & at(V7, C) & obj_tp(V7, truck) & D \== V7 & V7 \== X & V7 \== Z <-
	unload_truck(X, D, B);
	load_airplane(X, Z, B);
	fly_airplane(Z, B, C);
	unload_airplane(X, Z, C);
	load_truck(X, V7, C);
	drive_truck(V7, C, Y, A);
	unload_truck(X, V7, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & at(X, B) & obj_tp(B, location) & at(D, B) & obj_tp(D, truck) & D \== X & at(Z, Y) & obj_tp(Z, airplane) & D \== Z & X \== Z & in_city(B, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & B \== C & C \== Y & has_airport(C) <-
	load_truck(X, D, B);
	drive_truck(D, B, C, A);
	unload_truck(X, D, C);
	fly_airplane(Z, Y, C);
	load_airplane(X, Z, C);
	fly_airplane(Z, C, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, D) & obj_tp(D, location) & has_airport(D) & at(Z, D) & obj_tp(Z, airplane) & X \== Z & in_city(Y, A) & obj_tp(A, city) & in_city(B, A) & obj_tp(B, location) & B \== Y & at(V7, B) & obj_tp(V7, truck) & V7 \== X & V7 \== Z & in_city(C, A) & obj_tp(C, location) & B \== C & C \== D & C \== Y & has_airport(C) <-
	drive_truck(V7, B, C, A);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, C);
	unload_airplane(X, Z, C);
	load_truck(X, V7, C);
	drive_truck(V7, C, Y, A);
	unload_truck(X, V7, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & at(X, C) & obj_tp(C, location) & in_city(C, A) & obj_tp(A, city) & in_city(B, A) & obj_tp(B, location) & B \== C & B \== Y & has_airport(B) & at(D, B) & obj_tp(D, truck) & D \== X & at(Z, B) & obj_tp(Z, airplane) & D \== Z & X \== Z <-
	drive_truck(D, B, C, A);
	load_truck(X, D, C);
	drive_truck(D, C, B, A);
	unload_truck(X, D, B);
	load_airplane(X, Z, B);
	fly_airplane(Z, B, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, C) & obj_tp(C, location) & has_airport(C) & in_city(Y, A) & obj_tp(A, city) & in_city(B, A) & obj_tp(B, location) & B \== C & B \== Y & has_airport(B) & at(D, B) & obj_tp(D, truck) & D \== X & at(Z, B) & obj_tp(Z, airplane) & D \== Z & X \== Z <-
	fly_airplane(Z, B, C);
	load_airplane(X, Z, C);
	fly_airplane(Z, C, B);
	unload_airplane(X, Z, B);
	load_truck(X, D, B);
	drive_truck(D, B, Y, A);
	unload_truck(X, D, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, C) & obj_tp(C, location) & has_airport(C) & in_city(Y, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & C \== D & D \== Y & has_airport(D) & at(V7, D) & obj_tp(V7, truck) & V7 \== X & has_airport(B) & obj_tp(B, location) & B \== C & B \== D & at(Z, B) & obj_tp(Z, airplane) & V7 \== Z & X \== Z <-
	fly_airplane(Z, B, C);
	load_airplane(X, Z, C);
	fly_airplane(Z, C, D);
	unload_airplane(X, Z, D);
	load_truck(X, V7, D);
	drive_truck(V7, D, Y, A);
	unload_truck(X, V7, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & at(X, C) & obj_tp(C, location) & in_city(C, A) & obj_tp(A, city) & in_city(B, A) & obj_tp(B, location) & B \== C & at(V7, B) & obj_tp(V7, truck) & V7 \== X & in_city(D, A) & obj_tp(D, location) & B \== D & C \== D & D \== Y & has_airport(D) & at(Z, D) & obj_tp(Z, airplane) & V7 \== Z & X \== Z <-
	drive_truck(V7, B, C, A);
	load_truck(X, V7, C);
	drive_truck(V7, C, D, A);
	unload_truck(X, V7, D);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & in(X, D) & obj_tp(D, truck) & at(D, B) & obj_tp(B, location) & has_airport(B) & in_city(Y, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & B \== C & C \== Y & has_airport(C) & at(V7, C) & obj_tp(V7, truck) & D \== V7 & V7 \== X & at(Z, C) & obj_tp(Z, airplane) & D \== Z & V7 \== Z & X \== Z <-
	unload_truck(X, D, B);
	fly_airplane(Z, C, B);
	load_airplane(X, Z, B);
	fly_airplane(Z, B, C);
	unload_airplane(X, Z, C);
	load_truck(X, V7, C);
	drive_truck(V7, C, Y, A);
	unload_truck(X, V7, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & in(X, V7) & obj_tp(V7, truck) & at(V7, B) & obj_tp(B, location) & has_airport(B) & at(Z, B) & obj_tp(Z, airplane) & V7 \== Z & X \== Z & in_city(Y, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== Y & at(V8, C) & obj_tp(V8, truck) & V7 \== V8 & V8 \== X & V8 \== Z & in_city(D, A) & obj_tp(D, location) & B \== D & C \== D & D \== Y & has_airport(D) <-
	unload_truck(X, V7, B);
	drive_truck(V8, C, D, A);
	load_airplane(X, Z, B);
	fly_airplane(Z, B, D);
	unload_airplane(X, Z, D);
	load_truck(X, V8, D);
	drive_truck(V8, D, Y, A);
	unload_truck(X, V8, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & in(X, V7) & obj_tp(V7, truck) & at(V7, B) & obj_tp(B, location) & has_airport(B) & in_city(Y, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & B \== D & D \== Y & has_airport(D) & at(V8, D) & obj_tp(V8, truck) & V7 \== V8 & V8 \== X & has_airport(C) & obj_tp(C, location) & B \== C & C \== D & at(Z, C) & obj_tp(Z, airplane) & V7 \== Z & V8 \== Z & X \== Z <-
	unload_truck(X, V7, B);
	fly_airplane(Z, C, B);
	load_airplane(X, Z, B);
	fly_airplane(Z, B, D);
	unload_airplane(X, Z, D);
	load_truck(X, V8, D);
	drive_truck(V8, D, Y, A);
	unload_truck(X, V8, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & in(X, V8) & obj_tp(V8, truck) & V8 \== X & at(V8, C) & obj_tp(C, location) & in_city(C, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & C \== D & has_airport(D) & at(Z, D) & obj_tp(Z, airplane) & V8 \== Z & X \== Z & in_city(Y, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & D \== V7 & V7 \== Y & has_airport(V7) & at(V9, V7) & obj_tp(V9, truck) & V8 \== V9 & V9 \== X & V9 \== Z <-
	drive_truck(V8, C, D, A);
	unload_truck(X, V8, D);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, V7);
	unload_airplane(X, Z, V7);
	load_truck(X, V9, V7);
	drive_truck(V9, V7, Y, B);
	unload_truck(X, V9, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & at(X, D) & obj_tp(D, location) & in_city(D, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== D & C \== Y & has_airport(C) & at(V7, C) & obj_tp(V7, truck) & V7 \== X & has_airport(B) & obj_tp(B, location) & B \== C & B \== Y & at(Z, B) & obj_tp(Z, airplane) & V7 \== Z & X \== Z <-
	fly_airplane(Z, B, C);
	drive_truck(V7, C, D, A);
	load_truck(X, V7, D);
	drive_truck(V7, D, C, A);
	unload_truck(X, V7, C);
	load_airplane(X, Z, C);
	fly_airplane(Z, C, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(V7, Y) & obj_tp(V7, truck) & V7 \== X & at(X, C) & obj_tp(C, location) & has_airport(C) & in_city(Y, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & C \== D & D \== Y & has_airport(D) & has_airport(B) & obj_tp(B, location) & B \== C & B \== D & at(Z, B) & obj_tp(Z, airplane) & V7 \== Z & X \== Z <-
	fly_airplane(Z, B, C);
	load_airplane(X, Z, C);
	fly_airplane(Z, C, D);
	unload_airplane(X, Z, D);
	drive_truck(V7, Y, D, A);
	load_truck(X, V7, D);
	drive_truck(V7, D, Y, A);
	unload_truck(X, V7, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & at(X, C) & obj_tp(C, location) & in_city(C, A) & obj_tp(A, city) & in_city(B, A) & obj_tp(B, location) & B \== C & B \== Y & has_airport(B) & at(V7, B) & obj_tp(V7, truck) & V7 \== X & has_airport(D) & obj_tp(D, location) & B \== D & D \== Y & at(Z, D) & obj_tp(Z, airplane) & V7 \== Z & X \== Z <-
	drive_truck(V7, B, C, A);
	load_truck(X, V7, C);
	drive_truck(V7, C, B, A);
	unload_truck(X, V7, B);
	fly_airplane(Z, D, B);
	load_airplane(X, Z, B);
	fly_airplane(Z, B, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & at(X, C) & obj_tp(C, location) & in_city(C, A) & obj_tp(A, city) & in_city(B, A) & obj_tp(B, location) & B \== C & at(V8, B) & obj_tp(V8, truck) & V8 \== X & in_city(D, A) & obj_tp(D, location) & B \== D & C \== D & D \== Y & has_airport(D) & has_airport(V7) & obj_tp(V7, location) & D \== V7 & V7 \== Y & at(Z, V7) & obj_tp(Z, airplane) & V8 \== Z & X \== Z <-
	drive_truck(V8, B, C, A);
	load_truck(X, V8, C);
	drive_truck(V8, C, D, A);
	unload_truck(X, V8, D);
	fly_airplane(Z, V7, D);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & at(X, C) & obj_tp(C, location) & at(Z, Y) & obj_tp(Z, airplane) & X \== Z & in_city(C, A) & obj_tp(A, city) & in_city(B, A) & obj_tp(B, location) & B \== C & at(V7, B) & obj_tp(V7, truck) & V7 \== X & V7 \== Z & in_city(D, A) & obj_tp(D, location) & B \== D & C \== D & D \== Y & has_airport(D) <-
	drive_truck(V7, B, C, A);
	load_truck(X, V7, C);
	drive_truck(V7, C, D, A);
	unload_truck(X, V7, D);
	fly_airplane(Z, Y, D);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(V7, Y) & obj_tp(V7, truck) & V7 \== X & in(X, D) & obj_tp(D, truck) & D \== V7 & at(D, B) & obj_tp(B, location) & has_airport(B) & at(Z, B) & obj_tp(Z, airplane) & D \== Z & V7 \== Z & X \== Z & in_city(Y, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & B \== C & C \== Y & has_airport(C) <-
	unload_truck(X, D, B);
	load_airplane(X, Z, B);
	fly_airplane(Z, B, C);
	unload_airplane(X, Z, C);
	drive_truck(V7, Y, C, A);
	load_truck(X, V7, C);
	drive_truck(V7, C, Y, A);
	unload_truck(X, V7, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & in(X, V8) & obj_tp(V8, truck) & at(V8, D) & obj_tp(D, location) & has_airport(D) & at(Z, D) & obj_tp(Z, airplane) & V8 \== Z & X \== Z & in_city(Y, A) & obj_tp(A, city) & in_city(B, A) & obj_tp(B, location) & B \== Y & at(V7, B) & obj_tp(V7, truck) & V7 \== V8 & V7 \== X & V7 \== Z & in_city(C, A) & obj_tp(C, location) & B \== C & C \== D & C \== Y & has_airport(C) <-
	drive_truck(V7, B, C, A);
	unload_truck(X, V8, D);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, C);
	unload_airplane(X, Z, C);
	load_truck(X, V7, C);
	drive_truck(V7, C, Y, A);
	unload_truck(X, V7, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, V7) & obj_tp(V7, location) & has_airport(V7) & in_city(Y, A) & obj_tp(A, city) & in_city(B, A) & obj_tp(B, location) & B \== Y & at(V8, B) & obj_tp(V8, truck) & V8 \== X & in_city(C, A) & obj_tp(C, location) & B \== C & C \== V7 & C \== Y & has_airport(C) & has_airport(D) & obj_tp(D, location) & C \== D & D \== V7 & at(Z, D) & obj_tp(Z, airplane) & V8 \== Z & X \== Z <-
	drive_truck(V8, B, C, A);
	fly_airplane(Z, D, V7);
	load_airplane(X, Z, V7);
	fly_airplane(Z, V7, C);
	unload_airplane(X, Z, C);
	load_truck(X, V8, C);
	drive_truck(V8, C, Y, A);
	unload_truck(X, V8, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, D) & obj_tp(D, location) & has_airport(D) & in_city(Y, A) & obj_tp(A, city) & in_city(B, A) & obj_tp(B, location) & B \== Y & at(V7, B) & obj_tp(V7, truck) & V7 \== X & in_city(C, A) & obj_tp(C, location) & B \== C & C \== D & C \== Y & has_airport(C) & at(Z, C) & obj_tp(Z, airplane) & V7 \== Z & X \== Z <-
	drive_truck(V7, B, C, A);
	fly_airplane(Z, C, D);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, C);
	unload_airplane(X, Z, C);
	load_truck(X, V7, C);
	drive_truck(V7, C, Y, A);
	unload_truck(X, V7, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & at(X, C) & obj_tp(C, location) & at(Z, Y) & obj_tp(Z, airplane) & X \== Z & in_city(C, A) & obj_tp(A, city) & in_city(B, A) & obj_tp(B, location) & B \== C & B \== Y & has_airport(B) & at(D, B) & obj_tp(D, truck) & D \== X & D \== Z <-
	drive_truck(D, B, C, A);
	load_truck(X, D, C);
	drive_truck(D, C, B, A);
	unload_truck(X, D, B);
	fly_airplane(Z, Y, B);
	load_airplane(X, Z, B);
	fly_airplane(Z, B, Y);
	unload_airplane(X, Z, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(D, Y) & obj_tp(D, truck) & D \== X & at(X, C) & obj_tp(C, location) & has_airport(C) & in_city(Y, A) & obj_tp(A, city) & in_city(B, A) & obj_tp(B, location) & B \== C & B \== Y & has_airport(B) & at(Z, B) & obj_tp(Z, airplane) & D \== Z & X \== Z <-
	fly_airplane(Z, B, C);
	load_airplane(X, Z, C);
	fly_airplane(Z, C, B);
	unload_airplane(X, Z, B);
	drive_truck(D, Y, B, A);
	load_truck(X, D, B);
	drive_truck(D, B, Y, A);
	unload_truck(X, D, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & in(X, V8) & obj_tp(V8, truck) & V8 \== X & at(V8, C) & obj_tp(C, location) & in_city(C, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & C \== D & has_airport(D) & in_city(Y, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & D \== V7 & V7 \== Y & has_airport(V7) & at(V9, V7) & obj_tp(V9, truck) & V8 \== V9 & V9 \== X & at(Z, V7) & obj_tp(Z, airplane) & V8 \== Z & V9 \== Z & X \== Z <-
	drive_truck(V8, C, D, A);
	unload_truck(X, V8, D);
	fly_airplane(Z, V7, D);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, V7);
	unload_airplane(X, Z, V7);
	load_truck(X, V9, V7);
	drive_truck(V9, V7, Y, B);
	unload_truck(X, V9, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & in(X, V9) & obj_tp(V9, truck) & V9 \== X & at(V9, C) & obj_tp(C, location) & in_city(C, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & C \== D & has_airport(D) & at(Z, D) & obj_tp(Z, airplane) & V9 \== Z & X \== Z & in_city(Y, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & V7 \== Y & at(V10, V7) & obj_tp(V10, truck) & V10 \== V9 & V10 \== X & V10 \== Z & in_city(V8, B) & obj_tp(V8, location) & D \== V8 & V7 \== V8 & V8 \== Y & has_airport(V8) <-
	drive_truck(V9, C, D, A);
	drive_truck(V10, V7, V8, B);
	unload_truck(X, V9, D);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, V8);
	unload_airplane(X, Z, V8);
	load_truck(X, V10, V8);
	drive_truck(V10, V8, Y, B);
	unload_truck(X, V10, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(V8, Y) & obj_tp(V8, truck) & V8 \== X & in(X, V7) & obj_tp(V7, truck) & V7 \== V8 & at(V7, B) & obj_tp(B, location) & has_airport(B) & in_city(Y, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & B \== D & D \== Y & has_airport(D) & has_airport(C) & obj_tp(C, location) & B \== C & C \== D & at(Z, C) & obj_tp(Z, airplane) & V7 \== Z & V8 \== Z & X \== Z <-
	unload_truck(X, V7, B);
	fly_airplane(Z, C, B);
	load_airplane(X, Z, B);
	fly_airplane(Z, B, D);
	unload_airplane(X, Z, D);
	drive_truck(V8, Y, D, A);
	load_truck(X, V8, D);
	drive_truck(V8, D, Y, A);
	unload_truck(X, V8, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & in(X, V9) & obj_tp(V9, truck) & V9 \== X & at(V9, C) & obj_tp(C, location) & in_city(C, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & C \== D & has_airport(D) & in_city(Y, B) & obj_tp(B, city) & in_city(V8, B) & obj_tp(V8, location) & D \== V8 & V8 \== Y & has_airport(V8) & at(V10, V8) & obj_tp(V10, truck) & V10 \== V9 & V10 \== X & has_airport(V7) & obj_tp(V7, location) & D \== V7 & V7 \== V8 & at(Z, V7) & obj_tp(Z, airplane) & V10 \== Z & V9 \== Z & X \== Z <-
	drive_truck(V9, C, D, A);
	unload_truck(X, V9, D);
	fly_airplane(Z, V7, D);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, V8);
	unload_airplane(X, Z, V8);
	load_truck(X, V10, V8);
	drive_truck(V10, V8, Y, B);
	unload_truck(X, V10, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(V7, Y) & obj_tp(V7, truck) & V7 \== X & in(X, D) & obj_tp(D, truck) & D \== V7 & at(D, B) & obj_tp(B, location) & has_airport(B) & in_city(Y, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & B \== C & C \== Y & has_airport(C) & at(Z, C) & obj_tp(Z, airplane) & D \== Z & V7 \== Z & X \== Z <-
	unload_truck(X, D, B);
	fly_airplane(Z, C, B);
	load_airplane(X, Z, B);
	fly_airplane(Z, B, C);
	unload_airplane(X, Z, C);
	drive_truck(V7, Y, C, A);
	load_truck(X, V7, C);
	drive_truck(V7, C, Y, A);
	unload_truck(X, V7, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & in(X, V9) & obj_tp(V9, truck) & V9 \== X & at(V9, C) & obj_tp(C, location) & in_city(C, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & C \== D & has_airport(D) & at(Z, D) & obj_tp(Z, airplane) & V9 \== Z & X \== Z & in_city(Y, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & V7 \== Y & at(V10, V7) & obj_tp(V10, truck) & V10 \== V9 & V10 \== X & V10 \== Z & in_city(V8, B) & obj_tp(V8, location) & D \== V8 & V7 \== V8 & V8 \== Y & has_airport(V8) <-
	drive_truck(V9, C, D, A);
	unload_truck(X, V9, D);
	drive_truck(V10, V7, V8, B);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, V8);
	unload_airplane(X, Z, V8);
	load_truck(X, V10, V8);
	drive_truck(V10, V8, Y, B);
	unload_truck(X, V10, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(V9, Y) & obj_tp(V9, truck) & V9 \== X & in(X, V8) & obj_tp(V8, truck) & V8 \== V9 & V8 \== X & at(V8, C) & obj_tp(C, location) & in_city(C, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & C \== D & has_airport(D) & at(Z, D) & obj_tp(Z, airplane) & V8 \== Z & V9 \== Z & X \== Z & in_city(Y, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & D \== V7 & V7 \== Y & has_airport(V7) <-
	drive_truck(V8, C, D, A);
	unload_truck(X, V8, D);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, V7);
	unload_airplane(X, Z, V7);
	drive_truck(V9, Y, V7, B);
	load_truck(X, V9, V7);
	drive_truck(V9, V7, Y, B);
	unload_truck(X, V9, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, C) & obj_tp(C, location) & at(V8, C) & obj_tp(V8, truck) & V8 \== X & in_city(C, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & C \== D & has_airport(D) & at(Z, D) & obj_tp(Z, airplane) & V8 \== Z & X \== Z & in_city(Y, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & C \== V7 & D \== V7 & V7 \== Y & has_airport(V7) & at(V9, V7) & obj_tp(V9, truck) & V8 \== V9 & V9 \== X & V9 \== Z <-
	load_truck(X, V8, C);
	drive_truck(V8, C, D, A);
	unload_truck(X, V8, D);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, V7);
	unload_airplane(X, Z, V7);
	load_truck(X, V9, V7);
	drive_truck(V9, V7, Y, B);
	unload_truck(X, V9, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(V9, Y) & obj_tp(V9, truck) & V9 \== X & in(X, V8) & obj_tp(V8, truck) & V8 \== V9 & V8 \== X & at(V8, C) & obj_tp(C, location) & in_city(C, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & C \== D & has_airport(D) & in_city(Y, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & D \== V7 & V7 \== Y & has_airport(V7) & at(Z, V7) & obj_tp(Z, airplane) & V8 \== Z & V9 \== Z & X \== Z <-
	drive_truck(V8, C, D, A);
	unload_truck(X, V8, D);
	fly_airplane(Z, V7, D);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, V7);
	unload_airplane(X, Z, V7);
	drive_truck(V9, Y, V7, B);
	load_truck(X, V9, V7);
	drive_truck(V9, V7, Y, B);
	unload_truck(X, V9, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(V9, Y) & obj_tp(V9, truck) & V9 \== X & at(X, C) & obj_tp(C, location) & at(V8, C) & obj_tp(V8, truck) & V8 \== V9 & V8 \== X & in_city(C, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & C \== D & has_airport(D) & at(Z, D) & obj_tp(Z, airplane) & V8 \== Z & V9 \== Z & X \== Z & in_city(Y, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & C \== V7 & D \== V7 & V7 \== Y & has_airport(V7) <-
	load_truck(X, V8, C);
	drive_truck(V8, C, D, A);
	unload_truck(X, V8, D);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, V7);
	unload_airplane(X, Z, V7);
	drive_truck(V9, Y, V7, B);
	load_truck(X, V9, V7);
	drive_truck(V9, V7, Y, B);
	unload_truck(X, V9, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, C) & obj_tp(C, location) & at(V9, C) & obj_tp(V9, truck) & V9 \== X & in_city(C, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & C \== D & has_airport(D) & at(Z, D) & obj_tp(Z, airplane) & V9 \== Z & X \== Z & in_city(Y, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & V7 \== Y & at(V10, V7) & obj_tp(V10, truck) & V10 \== V9 & V10 \== X & V10 \== Z & in_city(V8, B) & obj_tp(V8, location) & C \== V8 & D \== V8 & V7 \== V8 & V8 \== Y & has_airport(V8) <-
	load_truck(X, V9, C);
	drive_truck(V9, C, D, A);
	unload_truck(X, V9, D);
	drive_truck(V10, V7, V8, B);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, V8);
	unload_airplane(X, Z, V8);
	load_truck(X, V10, V8);
	drive_truck(V10, V8, Y, B);
	unload_truck(X, V10, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, D) & obj_tp(D, location) & in_city(D, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== D & at(V9, C) & obj_tp(V9, truck) & V9 \== X & in_city(V7, A) & obj_tp(V7, location) & C \== V7 & D \== V7 & has_airport(V7) & at(Z, V7) & obj_tp(Z, airplane) & V9 \== Z & X \== Z & in_city(Y, B) & obj_tp(B, city) & in_city(V8, B) & obj_tp(V8, location) & D \== V8 & V7 \== V8 & V8 \== Y & has_airport(V8) & at(V10, V8) & obj_tp(V10, truck) & V10 \== V9 & V10 \== X & V10 \== Z <-
	drive_truck(V9, C, D, A);
	load_truck(X, V9, D);
	drive_truck(V9, D, V7, A);
	unload_truck(X, V9, V7);
	load_airplane(X, Z, V7);
	fly_airplane(Z, V7, V8);
	unload_airplane(X, Z, V8);
	load_truck(X, V10, V8);
	drive_truck(V10, V8, Y, B);
	unload_truck(X, V10, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, D) & obj_tp(D, location) & in_city(D, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== D & has_airport(C) & at(V8, C) & obj_tp(V8, truck) & V8 \== X & at(Z, C) & obj_tp(Z, airplane) & V8 \== Z & X \== Z & in_city(Y, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & C \== V7 & D \== V7 & V7 \== Y & has_airport(V7) & at(V9, V7) & obj_tp(V9, truck) & V8 \== V9 & V9 \== X & V9 \== Z <-
	drive_truck(V8, C, D, A);
	load_truck(X, V8, D);
	drive_truck(V8, D, C, A);
	unload_truck(X, V8, C);
	load_airplane(X, Z, C);
	fly_airplane(Z, C, V7);
	unload_airplane(X, Z, V7);
	load_truck(X, V9, V7);
	drive_truck(V9, V7, Y, B);
	unload_truck(X, V9, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, C) & obj_tp(C, location) & at(V8, C) & obj_tp(V8, truck) & V8 \== X & in_city(C, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & C \== D & has_airport(D) & in_city(Y, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & C \== V7 & D \== V7 & V7 \== Y & has_airport(V7) & at(V9, V7) & obj_tp(V9, truck) & V8 \== V9 & V9 \== X & at(Z, V7) & obj_tp(Z, airplane) & V8 \== Z & V9 \== Z & X \== Z <-
	load_truck(X, V8, C);
	drive_truck(V8, C, D, A);
	unload_truck(X, V8, D);
	fly_airplane(Z, V7, D);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, V7);
	unload_airplane(X, Z, V7);
	load_truck(X, V9, V7);
	drive_truck(V9, V7, Y, B);
	unload_truck(X, V9, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, C) & obj_tp(C, location) & at(V9, C) & obj_tp(V9, truck) & V9 \== X & in_city(C, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & C \== D & has_airport(D) & at(Z, D) & obj_tp(Z, airplane) & V9 \== Z & X \== Z & in_city(Y, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & V7 \== Y & at(V10, V7) & obj_tp(V10, truck) & V10 \== V9 & V10 \== X & V10 \== Z & in_city(V8, B) & obj_tp(V8, location) & C \== V8 & D \== V8 & V7 \== V8 & V8 \== Y & has_airport(V8) <-
	load_truck(X, V9, C);
	drive_truck(V9, C, D, A);
	drive_truck(V10, V7, V8, B);
	unload_truck(X, V9, D);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, V8);
	unload_airplane(X, Z, V8);
	load_truck(X, V10, V8);
	drive_truck(V10, V8, Y, B);
	unload_truck(X, V10, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(V10, Y) & obj_tp(V10, truck) & V10 \== X & in(X, V9) & obj_tp(V9, truck) & V10 \== V9 & V9 \== X & at(V9, C) & obj_tp(C, location) & in_city(C, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & C \== D & has_airport(D) & in_city(Y, B) & obj_tp(B, city) & in_city(V8, B) & obj_tp(V8, location) & D \== V8 & V8 \== Y & has_airport(V8) & has_airport(V7) & obj_tp(V7, location) & D \== V7 & V7 \== V8 & at(Z, V7) & obj_tp(Z, airplane) & V10 \== Z & V9 \== Z & X \== Z <-
	drive_truck(V9, C, D, A);
	unload_truck(X, V9, D);
	fly_airplane(Z, V7, D);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, V8);
	unload_airplane(X, Z, V8);
	drive_truck(V10, Y, V8, B);
	load_truck(X, V10, V8);
	drive_truck(V10, V8, Y, B);
	unload_truck(X, V10, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, C) & obj_tp(C, location) & at(V9, C) & obj_tp(V9, truck) & V9 \== X & in_city(C, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & C \== D & has_airport(D) & in_city(Y, B) & obj_tp(B, city) & in_city(V8, B) & obj_tp(V8, location) & C \== V8 & D \== V8 & V8 \== Y & has_airport(V8) & at(V10, V8) & obj_tp(V10, truck) & V10 \== V9 & V10 \== X & has_airport(V7) & obj_tp(V7, location) & D \== V7 & V7 \== V8 & at(Z, V7) & obj_tp(Z, airplane) & V10 \== Z & V9 \== Z & X \== Z <-
	load_truck(X, V9, C);
	drive_truck(V9, C, D, A);
	unload_truck(X, V9, D);
	fly_airplane(Z, V7, D);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, V8);
	unload_airplane(X, Z, V8);
	load_truck(X, V10, V8);
	drive_truck(V10, V8, Y, B);
	unload_truck(X, V10, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, V7) & obj_tp(V7, location) & at(V10, V7) & obj_tp(V10, truck) & V10 \== X & in_city(V7, B) & obj_tp(B, city) & in_city(V8, B) & obj_tp(V8, location) & V7 \== V8 & has_airport(V8) & at(Z, V8) & obj_tp(Z, airplane) & V10 \== Z & X \== Z & in_city(Y, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== Y & at(V9, C) & obj_tp(V9, truck) & V10 \== V9 & V9 \== X & V9 \== Z & in_city(D, A) & obj_tp(D, location) & C \== D & D \== V7 & D \== V8 & D \== Y & has_airport(D) <-
	drive_truck(V9, C, D, A);
	load_truck(X, V10, V7);
	drive_truck(V10, V7, V8, B);
	unload_truck(X, V10, V8);
	load_airplane(X, Z, V8);
	fly_airplane(Z, V8, D);
	unload_airplane(X, Z, D);
	load_truck(X, V9, D);
	drive_truck(V9, D, Y, A);
	unload_truck(X, V9, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, V8) & obj_tp(V8, location) & in_city(V8, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & V7 \== V8 & has_airport(V7) & at(V10, V7) & obj_tp(V10, truck) & V10 \== X & at(Z, V7) & obj_tp(Z, airplane) & V10 \== Z & X \== Z & in_city(Y, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== Y & at(V9, C) & obj_tp(V9, truck) & V10 \== V9 & V9 \== X & V9 \== Z & in_city(D, A) & obj_tp(D, location) & C \== D & D \== V7 & D \== V8 & D \== Y & has_airport(D) <-
	drive_truck(V9, C, D, A);
	drive_truck(V10, V7, V8, B);
	load_truck(X, V10, V8);
	drive_truck(V10, V8, V7, B);
	unload_truck(X, V10, V7);
	load_airplane(X, Z, V7);
	fly_airplane(Z, V7, D);
	unload_airplane(X, Z, D);
	load_truck(X, V9, D);
	drive_truck(V9, D, Y, A);
	unload_truck(X, V9, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, D) & obj_tp(D, location) & in_city(D, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== D & at(V10, C) & obj_tp(V10, truck) & V10 \== X & in_city(V7, A) & obj_tp(V7, location) & C \== V7 & D \== V7 & has_airport(V7) & in_city(Y, B) & obj_tp(B, city) & in_city(V9, B) & obj_tp(V9, location) & D \== V9 & V7 \== V9 & V9 \== Y & has_airport(V9) & at(V11, V9) & obj_tp(V11, truck) & V10 \== V11 & V11 \== X & has_airport(V8) & obj_tp(V8, location) & V7 \== V8 & V8 \== V9 & at(Z, V8) & obj_tp(Z, airplane) & V10 \== Z & V11 \== Z & X \== Z <-
	drive_truck(V10, C, D, A);
	load_truck(X, V10, D);
	drive_truck(V10, D, V7, A);
	unload_truck(X, V10, V7);
	fly_airplane(Z, V8, V7);
	load_airplane(X, Z, V7);
	fly_airplane(Z, V7, V9);
	unload_airplane(X, Z, V9);
	load_truck(X, V11, V9);
	drive_truck(V11, V9, Y, B);
	unload_truck(X, V11, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, D) & obj_tp(D, location) & in_city(D, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== D & has_airport(C) & at(V8, C) & obj_tp(V8, truck) & V8 \== X & in_city(Y, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & C \== V7 & D \== V7 & V7 \== Y & has_airport(V7) & at(V9, V7) & obj_tp(V9, truck) & V8 \== V9 & V9 \== X & at(Z, V7) & obj_tp(Z, airplane) & V8 \== Z & V9 \== Z & X \== Z <-
	drive_truck(V8, C, D, A);
	load_truck(X, V8, D);
	drive_truck(V8, D, C, A);
	unload_truck(X, V8, C);
	fly_airplane(Z, V7, C);
	load_airplane(X, Z, C);
	fly_airplane(Z, C, V7);
	unload_airplane(X, Z, V7);
	load_truck(X, V9, V7);
	drive_truck(V9, V7, Y, B);
	unload_truck(X, V9, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, V7) & obj_tp(V7, location) & at(V11, V7) & obj_tp(V11, truck) & V11 \== X & in_city(V7, B) & obj_tp(B, city) & in_city(V8, B) & obj_tp(V8, location) & V7 \== V8 & has_airport(V8) & in_city(Y, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== Y & at(V10, C) & obj_tp(V10, truck) & V10 \== V11 & V10 \== X & in_city(D, A) & obj_tp(D, location) & C \== D & D \== V7 & D \== V8 & D \== Y & has_airport(D) & has_airport(V9) & obj_tp(V9, location) & D \== V9 & V8 \== V9 & at(Z, V9) & obj_tp(Z, airplane) & V10 \== Z & V11 \== Z & X \== Z <-
	drive_truck(V10, C, D, A);
	load_truck(X, V11, V7);
	drive_truck(V11, V7, V8, B);
	unload_truck(X, V11, V8);
	fly_airplane(Z, V9, V8);
	load_airplane(X, Z, V8);
	fly_airplane(Z, V8, D);
	unload_airplane(X, Z, D);
	load_truck(X, V10, D);
	drive_truck(V10, D, Y, A);
	unload_truck(X, V10, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, D) & obj_tp(D, location) & in_city(D, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== D & has_airport(C) & at(V9, C) & obj_tp(V9, truck) & V9 \== X & in_city(Y, B) & obj_tp(B, city) & in_city(V8, B) & obj_tp(V8, location) & C \== V8 & D \== V8 & V8 \== Y & has_airport(V8) & at(V10, V8) & obj_tp(V10, truck) & V10 \== V9 & V10 \== X & has_airport(V7) & obj_tp(V7, location) & C \== V7 & V7 \== V8 & at(Z, V7) & obj_tp(Z, airplane) & V10 \== Z & V9 \== Z & X \== Z <-
	drive_truck(V9, C, D, A);
	load_truck(X, V9, D);
	drive_truck(V9, D, C, A);
	unload_truck(X, V9, C);
	fly_airplane(Z, V7, C);
	load_airplane(X, Z, C);
	fly_airplane(Z, C, V8);
	unload_airplane(X, Z, V8);
	load_truck(X, V10, V8);
	drive_truck(V10, V8, Y, B);
	unload_truck(X, V10, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(V9, Y) & obj_tp(V9, truck) & V9 \== X & at(X, C) & obj_tp(C, location) & at(V8, C) & obj_tp(V8, truck) & V8 \== V9 & V8 \== X & in_city(C, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & C \== D & has_airport(D) & in_city(Y, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & C \== V7 & D \== V7 & V7 \== Y & has_airport(V7) & at(Z, V7) & obj_tp(Z, airplane) & V8 \== Z & V9 \== Z & X \== Z <-
	load_truck(X, V8, C);
	drive_truck(V8, C, D, A);
	unload_truck(X, V8, D);
	fly_airplane(Z, V7, D);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, V7);
	unload_airplane(X, Z, V7);
	drive_truck(V9, Y, V7, B);
	load_truck(X, V9, V7);
	drive_truck(V9, V7, Y, B);
	unload_truck(X, V9, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, V7) & obj_tp(V7, location) & in_city(V7, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & D \== V7 & has_airport(D) & at(V9, D) & obj_tp(V9, truck) & V9 \== X & in_city(Y, B) & obj_tp(B, city) & in_city(V8, B) & obj_tp(V8, location) & D \== V8 & V7 \== V8 & V8 \== Y & has_airport(V8) & at(V10, V8) & obj_tp(V10, truck) & V10 \== V9 & V10 \== X & has_airport(C) & obj_tp(C, location) & C \== D & C \== V8 & at(Z, C) & obj_tp(Z, airplane) & V10 \== Z & V9 \== Z & X \== Z <-
	fly_airplane(Z, C, D);
	drive_truck(V9, D, V7, A);
	load_truck(X, V9, V7);
	drive_truck(V9, V7, D, A);
	unload_truck(X, V9, D);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, V8);
	unload_airplane(X, Z, V8);
	load_truck(X, V10, V8);
	drive_truck(V10, V8, Y, B);
	unload_truck(X, V10, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, V7) & obj_tp(V7, location) & at(V10, V7) & obj_tp(V10, truck) & V10 \== X & in_city(V7, B) & obj_tp(B, city) & in_city(V8, B) & obj_tp(V8, location) & V7 \== V8 & has_airport(V8) & in_city(Y, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== Y & at(V9, C) & obj_tp(V9, truck) & V10 \== V9 & V9 \== X & in_city(D, A) & obj_tp(D, location) & C \== D & D \== V7 & D \== V8 & D \== Y & has_airport(D) & at(Z, D) & obj_tp(Z, airplane) & V10 \== Z & V9 \== Z & X \== Z <-
	drive_truck(V9, C, D, A);
	load_truck(X, V10, V7);
	drive_truck(V10, V7, V8, B);
	unload_truck(X, V10, V8);
	fly_airplane(Z, D, V8);
	load_airplane(X, Z, V8);
	fly_airplane(Z, V8, D);
	unload_airplane(X, Z, D);
	load_truck(X, V9, D);
	drive_truck(V9, D, Y, A);
	unload_truck(X, V9, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(V9, Y) & obj_tp(V9, truck) & V9 \== X & at(X, D) & obj_tp(D, location) & in_city(D, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== D & has_airport(C) & at(V8, C) & obj_tp(V8, truck) & V8 \== V9 & V8 \== X & at(Z, C) & obj_tp(Z, airplane) & V8 \== Z & V9 \== Z & X \== Z & in_city(Y, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & C \== V7 & D \== V7 & V7 \== Y & has_airport(V7) <-
	drive_truck(V8, C, D, A);
	load_truck(X, V8, D);
	drive_truck(V8, D, C, A);
	unload_truck(X, V8, C);
	load_airplane(X, Z, C);
	fly_airplane(Z, C, V7);
	unload_airplane(X, Z, V7);
	drive_truck(V9, Y, V7, B);
	load_truck(X, V9, V7);
	drive_truck(V9, V7, Y, B);
	unload_truck(X, V9, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(V10, Y) & obj_tp(V10, truck) & V10 \== X & at(X, D) & obj_tp(D, location) & in_city(D, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== D & at(V9, C) & obj_tp(V9, truck) & V10 \== V9 & V9 \== X & in_city(V7, A) & obj_tp(V7, location) & C \== V7 & D \== V7 & has_airport(V7) & at(Z, V7) & obj_tp(Z, airplane) & V10 \== Z & V9 \== Z & X \== Z & in_city(Y, B) & obj_tp(B, city) & in_city(V8, B) & obj_tp(V8, location) & D \== V8 & V7 \== V8 & V8 \== Y & has_airport(V8) <-
	drive_truck(V9, C, D, A);
	load_truck(X, V9, D);
	drive_truck(V9, D, V7, A);
	unload_truck(X, V9, V7);
	load_airplane(X, Z, V7);
	fly_airplane(Z, V7, V8);
	unload_airplane(X, Z, V8);
	drive_truck(V10, Y, V8, B);
	load_truck(X, V10, V8);
	drive_truck(V10, V8, Y, B);
	unload_truck(X, V10, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, D) & obj_tp(D, location) & in_city(D, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== D & at(V10, C) & obj_tp(V10, truck) & V10 \== X & in_city(V7, A) & obj_tp(V7, location) & C \== V7 & D \== V7 & has_airport(V7) & at(Z, V7) & obj_tp(Z, airplane) & V10 \== Z & X \== Z & in_city(Y, B) & obj_tp(B, city) & in_city(V8, B) & obj_tp(V8, location) & V8 \== Y & at(V11, V8) & obj_tp(V11, truck) & V10 \== V11 & V11 \== X & V11 \== Z & in_city(V9, B) & obj_tp(V9, location) & D \== V9 & V7 \== V9 & V8 \== V9 & V9 \== Y & has_airport(V9) <-
	drive_truck(V10, C, D, A);
	load_truck(X, V10, D);
	drive_truck(V10, D, V7, A);
	drive_truck(V11, V8, V9, B);
	unload_truck(X, V10, V7);
	load_airplane(X, Z, V7);
	fly_airplane(Z, V7, V9);
	unload_airplane(X, Z, V9);
	load_truck(X, V11, V9);
	drive_truck(V11, V9, Y, B);
	unload_truck(X, V11, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(V10, Y) & obj_tp(V10, truck) & V10 \== X & at(X, C) & obj_tp(C, location) & at(V9, C) & obj_tp(V9, truck) & V10 \== V9 & V9 \== X & in_city(C, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & C \== D & has_airport(D) & in_city(Y, B) & obj_tp(B, city) & in_city(V8, B) & obj_tp(V8, location) & C \== V8 & D \== V8 & V8 \== Y & has_airport(V8) & has_airport(V7) & obj_tp(V7, location) & D \== V7 & V7 \== V8 & at(Z, V7) & obj_tp(Z, airplane) & V10 \== Z & V9 \== Z & X \== Z <-
	load_truck(X, V9, C);
	drive_truck(V9, C, D, A);
	unload_truck(X, V9, D);
	fly_airplane(Z, V7, D);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, V8);
	unload_airplane(X, Z, V8);
	drive_truck(V10, Y, V8, B);
	load_truck(X, V10, V8);
	drive_truck(V10, V8, Y, B);
	unload_truck(X, V10, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, V8) & obj_tp(V8, location) & in_city(V8, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & V7 \== V8 & at(V11, V7) & obj_tp(V11, truck) & V11 \== X & in_city(V9, B) & obj_tp(V9, location) & V7 \== V9 & V8 \== V9 & has_airport(V9) & at(Z, V9) & obj_tp(Z, airplane) & V11 \== Z & X \== Z & in_city(Y, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== Y & at(V10, C) & obj_tp(V10, truck) & V10 \== V11 & V10 \== X & V10 \== Z & in_city(D, A) & obj_tp(D, location) & C \== D & D \== V8 & D \== V9 & D \== Y & has_airport(D) <-
	drive_truck(V10, C, D, A);
	drive_truck(V11, V7, V8, B);
	load_truck(X, V11, V8);
	drive_truck(V11, V8, V9, B);
	unload_truck(X, V11, V9);
	load_airplane(X, Z, V9);
	fly_airplane(Z, V9, D);
	unload_airplane(X, Z, D);
	load_truck(X, V10, D);
	drive_truck(V10, D, Y, A);
	unload_truck(X, V10, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, D) & obj_tp(D, location) & in_city(D, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== D & at(V9, C) & obj_tp(V9, truck) & V9 \== X & in_city(V7, A) & obj_tp(V7, location) & C \== V7 & D \== V7 & has_airport(V7) & in_city(Y, B) & obj_tp(B, city) & in_city(V8, B) & obj_tp(V8, location) & D \== V8 & V7 \== V8 & V8 \== Y & has_airport(V8) & at(V10, V8) & obj_tp(V10, truck) & V10 \== V9 & V10 \== X & at(Z, V8) & obj_tp(Z, airplane) & V10 \== Z & V9 \== Z & X \== Z <-
	drive_truck(V9, C, D, A);
	load_truck(X, V9, D);
	drive_truck(V9, D, V7, A);
	unload_truck(X, V9, V7);
	fly_airplane(Z, V8, V7);
	load_airplane(X, Z, V7);
	fly_airplane(Z, V7, V8);
	unload_airplane(X, Z, V8);
	load_truck(X, V10, V8);
	drive_truck(V10, V8, Y, B);
	unload_truck(X, V10, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, D) & obj_tp(D, location) & in_city(D, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== D & at(V10, C) & obj_tp(V10, truck) & V10 \== X & in_city(V7, A) & obj_tp(V7, location) & C \== V7 & D \== V7 & has_airport(V7) & at(Z, V7) & obj_tp(Z, airplane) & V10 \== Z & X \== Z & in_city(Y, B) & obj_tp(B, city) & in_city(V8, B) & obj_tp(V8, location) & V8 \== Y & at(V11, V8) & obj_tp(V11, truck) & V10 \== V11 & V11 \== X & V11 \== Z & in_city(V9, B) & obj_tp(V9, location) & D \== V9 & V7 \== V9 & V8 \== V9 & V9 \== Y & has_airport(V9) <-
	drive_truck(V10, C, D, A);
	load_truck(X, V10, D);
	drive_truck(V10, D, V7, A);
	unload_truck(X, V10, V7);
	drive_truck(V11, V8, V9, B);
	load_airplane(X, Z, V7);
	fly_airplane(Z, V7, V9);
	unload_airplane(X, Z, V9);
	load_truck(X, V11, V9);
	drive_truck(V11, V9, Y, B);
	unload_truck(X, V11, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, V8) & obj_tp(V8, location) & in_city(V8, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & V7 \== V8 & at(V11, V7) & obj_tp(V11, truck) & V11 \== X & in_city(V9, B) & obj_tp(V9, location) & V7 \== V9 & V8 \== V9 & has_airport(V9) & in_city(Y, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== Y & at(V10, C) & obj_tp(V10, truck) & V10 \== V11 & V10 \== X & in_city(D, A) & obj_tp(D, location) & C \== D & D \== V8 & D \== V9 & D \== Y & has_airport(D) & at(Z, D) & obj_tp(Z, airplane) & V10 \== Z & V11 \== Z & X \== Z <-
	drive_truck(V10, C, D, A);
	drive_truck(V11, V7, V8, B);
	load_truck(X, V11, V8);
	drive_truck(V11, V8, V9, B);
	unload_truck(X, V11, V9);
	fly_airplane(Z, D, V9);
	load_airplane(X, Z, V9);
	fly_airplane(Z, V9, D);
	unload_airplane(X, Z, D);
	load_truck(X, V10, D);
	drive_truck(V10, D, Y, A);
	unload_truck(X, V10, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(V10, Y) & obj_tp(V10, truck) & V10 \== X & at(X, V7) & obj_tp(V7, location) & in_city(V7, A) & obj_tp(A, city) & in_city(D, A) & obj_tp(D, location) & D \== V7 & has_airport(D) & at(V9, D) & obj_tp(V9, truck) & V10 \== V9 & V9 \== X & in_city(Y, B) & obj_tp(B, city) & in_city(V8, B) & obj_tp(V8, location) & D \== V8 & V7 \== V8 & V8 \== Y & has_airport(V8) & has_airport(C) & obj_tp(C, location) & C \== D & C \== V8 & at(Z, C) & obj_tp(Z, airplane) & V10 \== Z & V9 \== Z & X \== Z <-
	fly_airplane(Z, C, D);
	drive_truck(V9, D, V7, A);
	load_truck(X, V9, V7);
	drive_truck(V9, V7, D, A);
	unload_truck(X, V9, D);
	load_airplane(X, Z, D);
	fly_airplane(Z, D, V8);
	unload_airplane(X, Z, V8);
	drive_truck(V10, Y, V8, B);
	load_truck(X, V10, V8);
	drive_truck(V10, V8, Y, B);
	unload_truck(X, V10, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, V8) & obj_tp(V8, location) & in_city(V8, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & V7 \== V8 & has_airport(V7) & at(V10, V7) & obj_tp(V10, truck) & V10 \== X & in_city(Y, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== Y & at(V9, C) & obj_tp(V9, truck) & V10 \== V9 & V9 \== X & in_city(D, A) & obj_tp(D, location) & C \== D & D \== V7 & D \== V8 & D \== Y & has_airport(D) & at(Z, D) & obj_tp(Z, airplane) & V10 \== Z & V9 \== Z & X \== Z <-
	drive_truck(V9, C, D, A);
	drive_truck(V10, V7, V8, B);
	load_truck(X, V10, V8);
	drive_truck(V10, V8, V7, B);
	unload_truck(X, V10, V7);
	fly_airplane(Z, D, V7);
	load_airplane(X, Z, V7);
	fly_airplane(Z, V7, D);
	unload_airplane(X, Z, D);
	load_truck(X, V9, D);
	drive_truck(V9, D, Y, A);
	unload_truck(X, V9, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(V9, Y) & obj_tp(V9, truck) & V9 \== X & at(X, D) & obj_tp(D, location) & in_city(D, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== D & has_airport(C) & at(V8, C) & obj_tp(V8, truck) & V8 \== V9 & V8 \== X & in_city(Y, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & C \== V7 & D \== V7 & V7 \== Y & has_airport(V7) & at(Z, V7) & obj_tp(Z, airplane) & V8 \== Z & V9 \== Z & X \== Z <-
	drive_truck(V8, C, D, A);
	load_truck(X, V8, D);
	drive_truck(V8, D, C, A);
	unload_truck(X, V8, C);
	fly_airplane(Z, V7, C);
	load_airplane(X, Z, C);
	fly_airplane(Z, C, V7);
	unload_airplane(X, Z, V7);
	drive_truck(V9, Y, V7, B);
	load_truck(X, V9, V7);
	drive_truck(V9, V7, Y, B);
	unload_truck(X, V9, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, V8) & obj_tp(V8, location) & in_city(V8, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & V7 \== V8 & has_airport(V7) & at(V11, V7) & obj_tp(V11, truck) & V11 \== X & in_city(Y, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== Y & at(V10, C) & obj_tp(V10, truck) & V10 \== V11 & V10 \== X & in_city(D, A) & obj_tp(D, location) & C \== D & D \== V7 & D \== V8 & D \== Y & has_airport(D) & has_airport(V9) & obj_tp(V9, location) & D \== V9 & V7 \== V9 & at(Z, V9) & obj_tp(Z, airplane) & V10 \== Z & V11 \== Z & X \== Z <-
	drive_truck(V10, C, D, A);
	drive_truck(V11, V7, V8, B);
	load_truck(X, V11, V8);
	drive_truck(V11, V8, V7, B);
	unload_truck(X, V11, V7);
	fly_airplane(Z, V9, V7);
	load_airplane(X, Z, V7);
	fly_airplane(Z, V7, D);
	unload_airplane(X, Z, D);
	load_truck(X, V10, D);
	drive_truck(V10, D, Y, A);
	unload_truck(X, V10, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, V9) & obj_tp(V9, location) & in_city(V9, B) & obj_tp(B, city) & in_city(V8, B) & obj_tp(V8, location) & V8 \== V9 & has_airport(V8) & at(V11, V8) & obj_tp(V11, truck) & V11 \== X & in_city(Y, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== Y & at(V10, C) & obj_tp(V10, truck) & V10 \== V11 & V10 \== X & in_city(D, A) & obj_tp(D, location) & C \== D & D \== V8 & D \== V9 & D \== Y & has_airport(D) & has_airport(V7) & obj_tp(V7, location) & D \== V7 & V7 \== V8 & at(Z, V7) & obj_tp(Z, airplane) & V10 \== Z & V11 \== Z & X \== Z <-
	drive_truck(V10, C, D, A);
	fly_airplane(Z, V7, V8);
	drive_truck(V11, V8, V9, B);
	load_truck(X, V11, V9);
	drive_truck(V11, V9, V8, B);
	unload_truck(X, V11, V8);
	load_airplane(X, Z, V8);
	fly_airplane(Z, V8, D);
	unload_airplane(X, Z, D);
	load_truck(X, V10, D);
	drive_truck(V10, D, Y, A);
	unload_truck(X, V10, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(V10, Y) & obj_tp(V10, truck) & V10 \== X & at(X, D) & obj_tp(D, location) & in_city(D, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== D & has_airport(C) & at(V9, C) & obj_tp(V9, truck) & V10 \== V9 & V9 \== X & in_city(Y, B) & obj_tp(B, city) & in_city(V8, B) & obj_tp(V8, location) & C \== V8 & D \== V8 & V8 \== Y & has_airport(V8) & has_airport(V7) & obj_tp(V7, location) & C \== V7 & V7 \== V8 & at(Z, V7) & obj_tp(Z, airplane) & V10 \== Z & V9 \== Z & X \== Z <-
	drive_truck(V9, C, D, A);
	load_truck(X, V9, D);
	drive_truck(V9, D, C, A);
	unload_truck(X, V9, C);
	fly_airplane(Z, V7, C);
	load_airplane(X, Z, C);
	fly_airplane(Z, C, V8);
	unload_airplane(X, Z, V8);
	drive_truck(V10, Y, V8, B);
	load_truck(X, V10, V8);
	drive_truck(V10, V8, Y, B);
	unload_truck(X, V10, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(X, V8) & obj_tp(V8, location) & in_city(V8, B) & obj_tp(B, city) & in_city(V7, B) & obj_tp(V7, location) & V7 \== V8 & at(V12, V7) & obj_tp(V12, truck) & V12 \== X & in_city(V9, B) & obj_tp(V9, location) & V7 \== V9 & V8 \== V9 & has_airport(V9) & in_city(Y, A) & obj_tp(A, city) & in_city(C, A) & obj_tp(C, location) & C \== Y & at(V11, C) & obj_tp(V11, truck) & V11 \== V12 & V11 \== X & in_city(D, A) & obj_tp(D, location) & C \== D & D \== V8 & D \== V9 & D \== Y & has_airport(D) & has_airport(V10) & obj_tp(V10, location) & D \== V10 & V10 \== V9 & at(Z, V10) & obj_tp(Z, airplane) & V11 \== Z & V12 \== Z & X \== Z <-
	drive_truck(V11, C, D, A);
	drive_truck(V12, V7, V8, B);
	load_truck(X, V12, V8);
	drive_truck(V12, V8, V9, B);
	unload_truck(X, V12, V9);
	fly_airplane(Z, V10, V9);
	load_airplane(X, Z, V9);
	fly_airplane(Z, V9, D);
	unload_airplane(X, Z, D);
	load_truck(X, V11, D);
	drive_truck(V11, D, Y, A);
	unload_truck(X, V11, Y).

+!in(X, Y) : obj_tp(X, package) & obj_tp(Y, airplane) & at(X, Z) & obj_tp(Z, location) & at(Y, Z) <-
	load_airplane(X, Y, Z).

+!in(X, Y) : obj_tp(X, package) & obj_tp(Y, truck) & at(X, Z) & obj_tp(Z, location) & at(Y, Z) <-
	load_truck(X, Y, Z).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & has_airport(A) & obj_tp(A, location) & at(B, A) & obj_tp(B, truck) & not in(X, B) & at(Z, A) & obj_tp(Z, airplane) <-
	!in(X, B);
	!at(X, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & has_airport(Y) & has_airport(A) & obj_tp(A, location) & at(B, A) & obj_tp(B, airplane) & not in(X, B) & at(Z, A) & obj_tp(Z, airplane) <-
	!in(X, B);
	!at(X, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & in_city(Y, B) & obj_tp(B, city) & in_city(A, B) & obj_tp(A, location) & at(C, A) & obj_tp(C, truck) & not in(X, C) & at(Z, A) & obj_tp(Z, truck) <-
	!in(X, C);
	!at(X, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & in_city(Y, B) & obj_tp(B, city) & in_city(A, B) & obj_tp(A, location) & at(C, A) & obj_tp(C, airplane) & not in(X, C) & at(Z, A) & obj_tp(Z, truck) <-
	!in(X, C);
	!at(X, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(Z, Y) & obj_tp(Z, truck) & not in(X, Z) <-
	!in(X, Z);
	!at(X, Y).

+!at(X, Y) : obj_tp(X, package) & obj_tp(Y, location) & at(Z, Y) & obj_tp(Z, airplane) & not in(X, Z) <-
	!in(X, Z);
	!at(X, Y).

+!in(X, Y) : obj_tp(X, package) & obj_tp(Y, truck) & at(Y, Z) & obj_tp(Z, location) & not at(X, Z) <-
	!at(X, Z);
	!in(X, Y).

+!in(X, Y) : obj_tp(X, package) & obj_tp(Y, airplane) & at(Y, Z) & obj_tp(Z, location) & not at(X, Z) <-
	!at(X, Z);
	!in(X, Y).

+!in(X, Y) : obj_tp(X, package) & obj_tp(Y, truck) & at(X, Z) & obj_tp(Z, location) & not at(Y, Z) <-
	!at(Y, Z);
	!in(X, Y).

+!in(X, Y) : obj_tp(X, package) & obj_tp(Y, airplane) & at(X, Z) & obj_tp(Z, location) & not at(Y, Z) <-
	!at(Y, Z);
	!in(X, Y).
