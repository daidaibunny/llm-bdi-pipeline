/* Generated AgentSpeak(L) Plan Library */
/* Domain: depots */

+!at(X, Y) : at(X, Y) <-
	true.

+!available(X) : available(X) <-
	true.

+!clear(X) : clear(X) <-
	true.

+!in(X, Y) : in(X, Y) <-
	true.

+!lifting(X, Y) : lifting(X, Y) <-
	true.

+!on(X, Y) : on(X, Y) <-
	true.

+!at(X, Y) : place(Y) & truck(X) & at(X, Z) & Y \== Z & place(Z) <-
	drive(X, Z, Y).

+!at(X, Y) : crate(X) & place(Y) & at(A, Y) & clear(A) & surface(A) & at(Z, Y) & lifting(Z, X) & hoist(Z) <-
	drop(Z, X, A, Y).

+!at(X, Y) : crate(X) & place(Y) & at(A, Y) & clear(A) & surface(A) & at(Z, Y) & available(Z) & hoist(Z) & at(Z, C) & place(C) & at(B, C) & in(X, B) & truck(B) <-
	unload(Z, X, B, C);
	drop(Z, X, A, Y).

+!available(X) : hoist(X) & at(X, A) & place(A) & at(Z, A) & clear(Z) & surface(Z) & lifting(X, Y) & crate(Y) <-
	drop(X, Y, Z, A).

+!available(X) : hoist(X) & at(X, A) & place(A) & at(Z, A) & truck(Z) & lifting(X, Y) & crate(Y) <-
	load(X, Y, Z, A).

+!available(X) : hoist(X) & at(X, A) & A \== X & available(A) & hoist(A) & place(A) & at(A, B) & place(B) & at(Y, B) & lifting(X, Y) & crate(Y) & at(Z, A) & Y \== Z & clear(Z) & surface(Z) <-
	drop(X, Y, Z, A);
	lift(A, Y, Z, B).

+!clear(X) : crate(X) & lifting(Y, X) & hoist(Y) & at(Y, A) & place(A) & at(Z, A) & X \== Z & clear(Z) & surface(Z) <-
	drop(Y, X, Z, A).

+!clear(X) : surface(X) & on(Z, X) & X \== Z & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(Y, A) & available(Y) & hoist(Y) <-
	lift(Y, Z, X, A).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & B \== X & B \== Z & clear(B) & surface(B) & at(Y, A) & Y \== Z & available(Y) & hoist(Y) <-
	lift(Y, Z, X, A);
	drop(Y, Z, B, A).

+!clear(X) : surface(X) & on(Z, X) & X \== Z & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & B \== Z & truck(B) & at(Y, A) & Y \== Z & available(Y) & hoist(Y) <-
	lift(Y, Z, X, A);
	load(Y, Z, B, A).

+!clear(X) : surface(X) & on(Z, X) & X \== Z & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(Y, A) & Y \== Z & available(Y) & hoist(Y) & truck(Y) <-
	lift(Y, Z, X, A);
	load(Y, Z, Y, A).

+!clear(X) : surface(X) & on(Z, X) & X \== Z & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(Y, A) & hoist(Y) & at(Y, D) & place(D) & at(C, D) & truck(C) & lifting(Y, B) & crate(B) <-
	load(Y, B, C, D);
	lift(Y, Z, X, A).

+!clear(X) : crate(X) & in(X, B) & truck(B) & at(B, C) & place(C) & at(Y, C) & available(Y) & hoist(Y) & at(Y, A) & place(A) & at(Z, A) & X \== Z & clear(Z) & surface(Z) <-
	unload(Y, X, B, C);
	drop(Y, X, Z, A).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & B \== X & B \== Z & crate(B) & surface(B) & at(Y, A) & Y \== Z & lifting(Y, B) & hoist(Y) & at(Y, D) & place(D) & at(C, D) & B \== C & C \== X & C \== Z & clear(C) & surface(C) <-
	drop(Y, B, C, D);
	lift(Y, Z, X, A);
	drop(Y, Z, B, A).

+!clear(X) : surface(X) & on(Z, X) & X \== Z & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & B \== Z & crate(B) & truck(B) & at(Y, A) & Y \== Z & lifting(Y, B) & hoist(Y) & at(Y, D) & place(D) & at(C, D) & C \== X & C \== Z & clear(C) & surface(C) <-
	drop(Y, B, C, D);
	lift(Y, Z, X, A);
	load(Y, Z, B, A).

+!clear(X) : surface(X) & on(Z, X) & X \== Z & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(Y, A) & Y \== Z & hoist(Y) & truck(Y) & at(Y, D) & place(D) & at(C, D) & C \== X & C \== Z & clear(C) & surface(C) & lifting(Y, B) & B \== Z & crate(B) <-
	drop(Y, B, C, D);
	lift(Y, Z, X, A);
	load(Y, Z, Y, A).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & B \== X & B \== Z & clear(B) & crate(B) & surface(B) & at(Y, A) & Y \== Z & lifting(Y, B) & hoist(Y) & at(Y, D) & place(D) & at(C, D) & truck(C) <-
	load(Y, B, C, D);
	lift(Y, Z, X, A);
	drop(Y, Z, B, A).

+!clear(X) : surface(X) & on(Z, X) & X \== Z & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(C, A) & C \== Z & truck(C) & at(C, D) & place(D) & at(Y, A) & Y \== Z & at(Y, D) & hoist(Y) & lifting(Y, B) & B \== Z & crate(B) <-
	load(Y, B, C, D);
	lift(Y, Z, X, A);
	load(Y, Z, C, A).

+!clear(X) : surface(X) & on(Z, X) & X \== Z & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & B \== Z & crate(B) & truck(B) & at(Y, A) & Y \== Z & lifting(Y, B) & hoist(Y) & at(Y, D) & place(D) & at(C, D) & truck(C) <-
	load(Y, B, C, D);
	lift(Y, Z, X, A);
	load(Y, Z, B, A).

+!clear(X) : surface(X) & on(Z, X) & X \== Z & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(Y, A) & Y \== Z & hoist(Y) & truck(Y) & at(Y, D) & place(D) & at(C, D) & truck(C) & lifting(Y, B) & B \== Z & crate(B) <-
	load(Y, B, C, D);
	lift(Y, Z, X, A);
	load(Y, Z, Y, A).

+!in(X, Y) : crate(X) & truck(Y) & at(Y, A) & place(A) & at(Z, A) & lifting(Z, X) & hoist(Z) <-
	load(Z, X, Y, A).

+!in(X, Y) : crate(X) & truck(Y) & at(Y, A) & place(A) & at(Z, A) & available(Z) & hoist(Z) & at(Z, C) & place(C) & at(B, C) & B \== Y & in(X, B) & truck(B) <-
	unload(Z, X, B, C);
	load(Z, X, Y, A).

+!lifting(X, Y) : available(X) & clear(Y) & crate(Y) & hoist(X) & at(X, A) & at(Y, A) & place(A) & on(Y, Z) & surface(Z) <-
	lift(X, Y, Z, A).

+!lifting(X, Y) : available(X) & crate(Y) & hoist(X) & at(X, A) & place(A) & at(Z, A) & in(Y, Z) & truck(Z) <-
	unload(X, Y, Z, A).

+!lifting(X, Y) : crate(Y) & hoist(X) & at(X, A) & place(A) & at(X, D) & place(D) & at(C, D) & clear(C) & surface(C) & at(Z, A) & in(Y, Z) & truck(Z) & lifting(X, B) & B \== Y & crate(B) <-
	drop(X, B, C, D);
	unload(X, Y, Z, A).

+!lifting(X, Y) : clear(Y) & crate(Y) & hoist(X) & at(X, A) & at(Y, A) & place(A) & at(X, D) & place(D) & at(C, D) & truck(C) & lifting(X, B) & B \== Y & crate(B) & on(Y, Z) & surface(Z) <-
	load(X, B, C, D);
	lift(X, Y, Z, A).

+!lifting(X, Y) : crate(Y) & hoist(X) & at(X, A) & place(A) & at(X, D) & place(D) & at(C, D) & truck(C) & at(Z, A) & in(Y, Z) & truck(Z) & lifting(X, B) & B \== Y & crate(B) <-
	load(X, B, C, D);
	unload(X, Y, Z, A).

+!lifting(X, Y) : available(X) & crate(Y) & hoist(X) & at(X, A) & place(A) & at(Z, A) & truck(Z) & at(Z, C) & place(C) & at(B, C) & B \== X & lifting(B, Y) & hoist(B) <-
	load(B, Y, Z, C);
	unload(X, Y, Z, A).

+!on(X, Y) : clear(Y) & crate(X) & surface(Y) & at(Y, A) & place(A) & at(Z, A) & lifting(Z, X) & hoist(Z) <-
	drop(Z, X, Y, A).

+!on(X, Y) : clear(Y) & crate(X) & surface(Y) & at(Y, A) & place(A) & at(Z, A) & available(Z) & hoist(Z) & at(Z, C) & place(C) & at(B, C) & in(X, B) & truck(B) <-
	unload(Z, X, B, C);
	drop(Z, X, Y, A).

+!on(X, Y) : clear(Y) & crate(X) & surface(Y) & at(Y, B) & place(B) & at(A, B) & in(X, A) & truck(A) & at(Z, B) & available(Z) & hoist(Z) <-
	unload(Z, X, A, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & clear(X) & clear(Y) & crate(X) & surface(Y) & at(X, B) & at(Y, B) & place(B) & at(Z, B) & X \== Z & available(Z) & hoist(Z) & on(X, A) & surface(A) <-
	lift(Z, X, A, B);
	drop(Z, X, Y, B).

+!on(X, Y) : clear(Y) & crate(X) & surface(Y) & at(Y, C) & place(C) & at(B, C) & in(X, B) & truck(B) & at(Z, C) & hoist(Z) & lifting(Z, A) & A \== X & crate(A) <-
	load(Z, A, B, C);
	unload(Z, X, B, C);
	drop(Z, X, Y, C).

+!on(X, Y) : clear(Y) & crate(X) & surface(Y) & at(Y, B) & place(B) & at(C, B) & available(C) & hoist(C) & in(X, Z) & C \== Z & Y \== Z & truck(Z) & at(Z, A) & A \== B & place(A) <-
	drive(Z, A, B);
	unload(C, X, Z, B);
	drop(C, X, Y, B).

+!on(X, Y) : clear(Y) & crate(X) & surface(Y) & at(Y, C) & place(C) & at(B, C) & truck(B) & at(D, C) & in(X, D) & truck(D) & at(Z, C) & hoist(Z) & lifting(Z, A) & A \== X & crate(A) <-
	load(Z, A, B, C);
	unload(Z, X, D, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & clear(X) & clear(Y) & crate(X) & surface(Y) & at(X, C) & at(Y, C) & place(C) & at(B, C) & B \== X & B \== Y & clear(B) & surface(B) & at(Z, C) & X \== Z & hoist(Z) & lifting(Z, A) & A \== X & crate(A) & on(X, D) & surface(D) <-
	drop(Z, A, B, C);
	lift(Z, X, D, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & clear(X) & clear(Y) & crate(X) & surface(Y) & at(X, C) & at(Y, C) & place(C) & at(B, C) & truck(B) & at(Z, C) & X \== Z & hoist(Z) & lifting(Z, A) & A \== X & crate(A) & on(X, D) & surface(D) <-
	load(Z, A, B, C);
	lift(Z, X, D, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & crate(X) & crate(Y) & surface(Y) & in(X, C) & truck(C) & at(C, B) & place(B) & at(A, B) & A \== Y & clear(A) & surface(A) & at(Z, B) & lifting(Z, Y) & hoist(Z) <-
	drop(Z, Y, A, B);
	unload(Z, X, C, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & crate(Y) & surface(Y) & at(X, B) & place(B) & at(A, B) & A \== X & A \== Y & clear(A) & surface(A) & at(Z, B) & X \== Z & lifting(Z, Y) & hoist(Z) & on(X, C) & surface(C) <-
	drop(Z, Y, A, B);
	lift(Z, X, C, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, B) & at(Y, B) & place(B) & at(A, B) & A \== X & A \== Y & on(A, Y) & clear(A) & crate(A) & at(C, B) & A \== C & truck(C) & at(Z, B) & A \== Z & X \== Z & available(Z) & hoist(Z) & on(X, D) & surface(D) <-
	lift(Z, A, Y, B);
	load(Z, A, C, B);
	lift(Z, X, D, B);
	drop(Z, X, Y, B).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, B) & place(B) & at(A, B) & A \== X & A \== Y & on(A, Y) & clear(A) & crate(A) & at(C, B) & A \== C & in(X, C) & truck(C) & at(Z, B) & A \== Z & available(Z) & hoist(Z) <-
	lift(Z, A, Y, B);
	load(Z, A, C, B);
	unload(Z, X, C, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & crate(X) & crate(Y) & surface(Y) & in(X, D) & truck(D) & at(D, B) & place(B) & at(A, B) & in(Y, A) & truck(A) & at(C, B) & C \== Y & clear(C) & surface(C) & at(Z, B) & available(Z) & hoist(Z) <-
	unload(Z, Y, A, B);
	drop(Z, Y, C, B);
	unload(Z, X, D, B);
	drop(Z, X, Y, B).

+!on(X, Y) : clear(Y) & crate(X) & surface(Y) & at(Y, C) & place(C) & at(D, C) & available(D) & hoist(D) & lifting(Z, X) & D \== Z & hoist(Z) & at(Z, B) & B \== C & place(B) & at(A, B) & A \== D & A \== Y & truck(A) <-
	load(Z, X, A, B);
	drive(A, B, C);
	unload(D, X, A, C);
	drop(D, X, Y, C).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, B) & place(B) & at(A, B) & A \== X & A \== Y & on(A, Y) & clear(A) & crate(A) & at(C, B) & A \== C & truck(C) & at(D, B) & A \== D & in(X, D) & truck(D) & at(Z, B) & A \== Z & available(Z) & hoist(Z) <-
	lift(Z, A, Y, B);
	load(Z, A, C, B);
	unload(Z, X, D, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & crate(Y) & surface(Y) & at(X, B) & place(B) & at(A, B) & in(Y, A) & truck(A) & at(C, B) & C \== X & C \== Y & clear(C) & surface(C) & at(Z, B) & X \== Z & available(Z) & hoist(Z) & on(X, D) & surface(D) <-
	unload(Z, Y, A, B);
	drop(Z, Y, C, B);
	lift(Z, X, D, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & crate(X) & crate(Y) & surface(Y) & in(X, A) & in(Y, A) & truck(A) & at(A, B) & place(B) & at(C, B) & C \== Y & clear(C) & surface(C) & at(Z, B) & available(Z) & hoist(Z) <-
	unload(Z, Y, A, B);
	drop(Z, Y, C, B);
	unload(Z, X, A, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & clear(Y) & crate(X) & surface(X) & surface(Y) & at(X, B) & at(Y, B) & place(B) & at(A, B) & A \== X & A \== Y & on(A, X) & clear(A) & crate(A) & at(C, B) & A \== C & truck(C) & at(Z, B) & A \== Z & X \== Z & available(Z) & hoist(Z) & on(X, D) & surface(D) <-
	lift(Z, A, X, B);
	load(Z, A, C, B);
	lift(Z, X, D, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & clear(Y) & crate(X) & surface(X) & surface(Y) & at(X, B) & at(Y, B) & place(B) & at(A, B) & A \== X & on(A, X) & clear(A) & crate(A) & at(C, B) & A \== C & C \== X & C \== Y & clear(C) & surface(C) & at(Z, B) & A \== Z & X \== Z & available(Z) & hoist(Z) & on(X, D) & surface(D) <-
	lift(Z, A, X, B);
	drop(Z, A, C, B);
	lift(Z, X, D, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & on(Y, X) & clear(Y) & crate(X) & crate(Y) & surface(X) & surface(Y) & at(X, A) & at(Y, A) & place(A) & at(B, A) & B \== X & B \== Y & clear(B) & surface(B) & at(Z, A) & X \== Z & Y \== Z & available(Z) & hoist(Z) & on(X, C) & surface(C) <-
	lift(Z, Y, X, A);
	drop(Z, Y, B, A);
	lift(Z, X, C, A);
	drop(Z, X, Y, A).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, B) & place(B) & at(A, B) & truck(A) & at(C, B) & A \== C & C \== X & C \== Y & on(C, Y) & clear(C) & crate(C) & at(Z, B) & C \== Z & lifting(Z, X) & hoist(Z) <-
	load(Z, X, A, B);
	lift(Z, C, Y, B);
	load(Z, C, A, B);
	unload(Z, X, A, B);
	drop(Z, X, Y, B).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, B) & place(B) & at(C, B) & available(C) & hoist(C) & at(D, B) & C \== D & D \== X & D \== Y & on(D, Y) & clear(D) & crate(D) & in(X, Z) & C \== Z & D \== Z & Y \== Z & truck(Z) & at(Z, A) & A \== B & place(A) <-
	drive(Z, A, B);
	lift(C, D, Y, B);
	load(C, D, Z, B);
	unload(C, X, Z, B);
	drop(C, X, Y, B).

+!on(X, Y) : X \== Y & crate(X) & crate(Y) & surface(Y) & in(X, V7) & truck(V7) & at(V7, B) & place(B) & at(C, B) & available(C) & hoist(C) & at(D, B) & D \== Y & clear(D) & surface(D) & in(Y, Z) & C \== Z & D \== Z & V7 \== Z & Y \== Z & truck(Z) & at(Z, A) & A \== B & place(A) <-
	drive(Z, A, B);
	unload(C, Y, Z, B);
	drop(C, Y, D, B);
	unload(C, X, V7, B);
	drop(C, X, Y, B).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, C) & at(Y, C) & place(C) & at(B, C) & truck(B) & at(D, C) & B \== D & D \== X & D \== Y & on(D, Y) & clear(D) & crate(D) & at(Z, C) & D \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== D & A \== X & crate(A) & on(X, V7) & surface(V7) <-
	load(Z, A, B, C);
	lift(Z, D, Y, C);
	load(Z, D, B, C);
	lift(Z, X, V7, C);
	drop(Z, X, Y, C).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, B) & place(B) & at(C, B) & available(C) & hoist(C) & at(D, B) & C \== D & D \== X & D \== Y & on(D, Y) & clear(D) & crate(D) & at(V7, B) & D \== V7 & truck(V7) & in(X, Z) & C \== Z & D \== Z & V7 \== Z & Y \== Z & truck(Z) & at(Z, A) & A \== B & place(A) <-
	drive(Z, A, B);
	lift(C, D, Y, B);
	load(C, D, V7, B);
	unload(C, X, Z, B);
	drop(C, X, Y, B).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & crate(Y) & surface(Y) & at(X, B) & place(B) & at(C, B) & C \== X & available(C) & hoist(C) & at(D, B) & D \== X & D \== Y & clear(D) & surface(D) & in(Y, Z) & C \== Z & D \== Z & X \== Z & Y \== Z & truck(Z) & at(Z, A) & A \== B & place(A) & on(X, V7) & surface(V7) <-
	drive(Z, A, B);
	unload(C, Y, Z, B);
	drop(C, Y, D, B);
	lift(C, X, V7, B);
	drop(C, X, Y, B).

+!on(X, Y) : X \== Y & crate(X) & crate(Y) & surface(Y) & in(Y, A) & truck(A) & at(A, B) & place(B) & at(C, B) & C \== Y & clear(C) & surface(C) & at(Z, B) & lifting(Z, X) & hoist(Z) <-
	load(Z, X, A, B);
	unload(Z, Y, A, B);
	drop(Z, Y, C, B);
	unload(Z, X, A, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & clear(X) & clear(Y) & crate(X) & surface(Y) & at(X, B) & place(B) & at(C, B) & C \== X & C \== Y & truck(C) & at(Y, D) & B \== D & place(D) & at(V7, D) & C \== V7 & V7 \== X & available(V7) & hoist(V7) & at(Z, B) & V7 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, A) & surface(A) <-
	lift(Z, X, A, B);
	load(Z, X, C, B);
	drive(C, B, D);
	unload(V7, X, C, D);
	drop(V7, X, Y, D).

+!on(X, Y) : X \== Y & crate(X) & crate(Y) & surface(Y) & in(Y, C) & truck(C) & at(C, B) & place(B) & at(A, B) & truck(A) & at(D, B) & D \== Y & clear(D) & surface(D) & at(Z, B) & lifting(Z, X) & hoist(Z) <-
	load(Z, X, A, B);
	unload(Z, Y, C, B);
	drop(Z, Y, D, B);
	unload(Z, X, A, B);
	drop(Z, X, Y, B).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, C) & place(C) & at(B, C) & truck(B) & at(D, C) & B \== D & D \== X & D \== Y & on(D, Y) & clear(D) & crate(D) & at(V7, C) & D \== V7 & in(X, V7) & truck(V7) & at(Z, C) & D \== Z & hoist(Z) & lifting(Z, A) & A \== D & A \== X & crate(A) <-
	load(Z, A, B, C);
	lift(Z, D, Y, C);
	load(Z, D, B, C);
	unload(Z, X, V7, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & crate(X) & crate(Y) & surface(Y) & in(X, Z) & Y \== Z & truck(Z) & at(Z, A) & place(A) & in(Y, D) & D \== Z & truck(D) & at(D, B) & A \== B & place(B) & at(C, B) & C \== Z & available(C) & hoist(C) & at(V7, B) & V7 \== Y & V7 \== Z & clear(V7) & surface(V7) <-
	drive(Z, A, B);
	unload(C, Y, D, B);
	drop(C, Y, V7, B);
	unload(C, X, Z, B);
	drop(C, X, Y, B).

+!on(X, Y) : clear(Y) & crate(X) & surface(Y) & at(Y, A) & place(A) & at(D, A) & available(D) & hoist(D) & at(Z, A) & D \== Z & Y \== Z & truck(Z) & lifting(C, X) & C \== D & C \== Z & hoist(C) & at(C, B) & A \== B & place(B) <-
	drive(Z, A, B);
	load(C, X, Z, B);
	drive(Z, B, A);
	unload(D, X, Z, A);
	drop(D, X, Y, A).

+!on(X, Y) : X \== Y & clear(Y) & crate(X) & surface(X) & surface(Y) & at(X, C) & at(Y, C) & place(C) & at(B, C) & truck(B) & at(D, C) & B \== D & D \== X & D \== Y & on(D, X) & clear(D) & crate(D) & at(Z, C) & D \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== D & A \== X & crate(A) & on(X, V7) & surface(V7) <-
	load(Z, A, B, C);
	lift(Z, D, X, C);
	load(Z, D, B, C);
	lift(Z, X, V7, C);
	drop(Z, X, Y, C).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, C) & place(C) & at(B, C) & in(X, B) & truck(B) & at(D, C) & B \== D & D \== X & D \== Y & on(D, Y) & clear(D) & crate(D) & at(Z, C) & D \== Z & hoist(Z) & lifting(Z, A) & A \== D & A \== X & crate(A) <-
	load(Z, A, B, C);
	lift(Z, D, Y, C);
	load(Z, D, B, C);
	unload(Z, X, B, C);
	drop(Z, X, Y, C).

+!on(X, Y) : clear(Y) & crate(X) & surface(Y) & at(Y, D) & place(D) & at(V7, D) & available(V7) & hoist(V7) & lifting(C, X) & C \== V7 & hoist(C) & at(C, B) & B \== D & place(B) & place(A) & A \== B & A \== D & at(Z, A) & C \== Z & V7 \== Z & Y \== Z & truck(Z) <-
	drive(Z, A, B);
	load(C, X, Z, B);
	drive(Z, B, D);
	unload(V7, X, Z, D);
	drop(V7, X, Y, D).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, C) & place(C) & at(A, C) & A \== X & A \== Y & clear(A) & crate(A) & at(B, C) & A \== B & B \== X & B \== Y & on(A, B) & on(B, Y) & crate(B) & surface(B) & at(D, C) & A \== D & B \== D & truck(D) & at(V7, C) & A \== V7 & B \== V7 & in(X, V7) & truck(V7) & at(Z, C) & A \== Z & B \== Z & available(Z) & hoist(Z) <-
	lift(Z, A, B, C);
	load(Z, A, D, C);
	lift(Z, B, Y, C);
	load(Z, B, D, C);
	unload(Z, X, V7, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & clear(X) & clear(Y) & crate(X) & surface(Y) & at(X, B) & place(B) & at(C, B) & C \== X & available(C) & hoist(C) & at(Y, V7) & B \== V7 & place(V7) & at(V8, V7) & C \== V8 & V8 \== X & available(V8) & hoist(V8) & on(X, D) & surface(D) & place(A) & A \== B & A \== V7 & at(Z, A) & C \== Z & V8 \== Z & X \== Z & Y \== Z & truck(Z) <-
	drive(Z, A, B);
	lift(C, X, D, B);
	load(C, X, Z, B);
	drive(Z, B, V7);
	unload(V8, X, Z, V7);
	drop(V8, X, Y, V7).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, C) & at(Y, C) & place(C) & at(A, C) & A \== X & A \== Y & clear(A) & crate(A) & at(B, C) & A \== B & B \== X & B \== Y & on(A, B) & on(B, Y) & crate(B) & surface(B) & at(D, C) & A \== D & B \== D & truck(D) & at(Z, C) & A \== Z & B \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V7) & surface(V7) <-
	lift(Z, A, B, C);
	load(Z, A, D, C);
	lift(Z, B, Y, C);
	load(Z, B, D, C);
	lift(Z, X, V7, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & crate(Y) & surface(Y) & at(X, B) & place(B) & at(A, B) & A \== X & A \== Y & on(X, A) & surface(A) & at(C, B) & C \== X & in(Y, C) & truck(C) & at(Z, B) & X \== Z & available(Z) & hoist(Z) <-
	lift(Z, X, A, B);
	load(Z, X, C, B);
	unload(Z, Y, C, B);
	drop(Z, Y, A, B);
	unload(Z, X, C, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & clear(Y) & crate(X) & surface(X) & surface(Y) & at(X, C) & at(Y, C) & place(C) & at(A, C) & A \== X & A \== Y & clear(A) & crate(A) & at(B, C) & A \== B & B \== X & B \== Y & on(A, B) & on(B, X) & crate(B) & surface(B) & at(D, C) & A \== D & B \== D & truck(D) & at(Z, C) & A \== Z & B \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V7) & surface(V7) <-
	lift(Z, A, B, C);
	load(Z, A, D, C);
	lift(Z, B, X, C);
	load(Z, B, D, C);
	lift(Z, X, V7, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, B) & at(Y, B) & place(B) & at(A, B) & A \== X & A \== Y & on(A, Y) & on(X, A) & crate(A) & surface(A) & at(C, B) & A \== C & C \== X & truck(C) & at(Z, B) & A \== Z & X \== Z & available(Z) & hoist(Z) <-
	lift(Z, X, A, B);
	load(Z, X, C, B);
	lift(Z, A, Y, B);
	load(Z, A, C, B);
	unload(Z, X, C, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & clear(X) & clear(Y) & crate(X) & surface(Y) & at(X, C) & place(C) & at(B, C) & B \== X & B \== Y & truck(B) & at(Y, V7) & C \== V7 & place(V7) & at(V8, V7) & B \== V8 & V8 \== X & available(V8) & hoist(V8) & at(Z, C) & V8 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== X & crate(A) & on(X, D) & surface(D) <-
	load(Z, A, B, C);
	lift(Z, X, D, C);
	load(Z, X, B, C);
	drive(B, C, V7);
	unload(V8, X, B, V7);
	drop(V8, X, Y, V7).

+!on(X, Y) : X \== Y & clear(X) & clear(Y) & crate(X) & surface(Y) & at(X, B) & place(B) & at(Y, D) & B \== D & place(D) & at(C, D) & C \== X & C \== Y & truck(C) & at(V7, D) & C \== V7 & V7 \== X & available(V7) & hoist(V7) & at(Z, B) & C \== Z & V7 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, A) & surface(A) <-
	lift(Z, X, A, B);
	drive(C, D, B);
	load(Z, X, C, B);
	drive(C, B, D);
	unload(V7, X, C, D);
	drop(V7, X, Y, D).

+!on(X, Y) : X \== Y & clear(X) & clear(Y) & crate(X) & surface(Y) & at(X, B) & place(B) & at(Y, V7) & B \== V7 & place(V7) & at(V8, V7) & V8 \== X & available(V8) & hoist(V8) & at(Z, B) & V8 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, A) & surface(A) & place(D) & B \== D & D \== V7 & at(C, D) & C \== V8 & C \== X & C \== Y & C \== Z & truck(C) <-
	lift(Z, X, A, B);
	drive(C, D, B);
	load(Z, X, C, B);
	drive(C, B, V7);
	unload(V8, X, C, V7);
	drop(V8, X, Y, V7).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, B) & at(Y, B) & place(B) & at(A, B) & A \== X & A \== Y & on(A, Y) & clear(A) & crate(A) & at(C, B) & A \== C & truck(C) & at(D, B) & A \== D & C \== D & D \== X & D \== Y & on(D, X) & clear(D) & crate(D) & at(Z, B) & A \== Z & D \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V7) & surface(V7) <-
	lift(Z, A, Y, B);
	load(Z, A, C, B);
	lift(Z, D, X, B);
	load(Z, D, C, B);
	lift(Z, X, V7, B);
	drop(Z, X, Y, B).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, C) & place(C) & at(A, C) & A \== X & A \== Y & clear(A) & crate(A) & at(B, C) & A \== B & B \== X & B \== Y & on(A, B) & on(B, Y) & crate(B) & surface(B) & at(D, C) & A \== D & B \== D & in(X, D) & truck(D) & at(Z, C) & A \== Z & B \== Z & available(Z) & hoist(Z) <-
	lift(Z, A, B, C);
	load(Z, A, D, C);
	lift(Z, B, Y, C);
	load(Z, B, D, C);
	unload(Z, X, D, C);
	drop(Z, X, Y, C).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, C) & place(C) & at(D, C) & available(D) & hoist(D) & at(V7, C) & D \== V7 & V7 \== X & V7 \== Y & on(V7, Y) & clear(V7) & crate(V7) & lifting(Z, X) & D \== Z & hoist(Z) & at(Z, B) & B \== C & place(B) & at(A, B) & A \== D & A \== V7 & A \== Y & truck(A) <-
	load(Z, X, A, B);
	drive(A, B, C);
	lift(D, V7, Y, C);
	load(D, V7, A, C);
	unload(D, X, A, C);
	drop(D, X, Y, C).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & crate(Y) & surface(Y) & at(X, B) & place(B) & at(A, B) & A \== X & A \== Y & on(X, A) & surface(A) & at(C, B) & C \== X & truck(C) & at(D, B) & D \== X & in(Y, D) & truck(D) & at(Z, B) & X \== Z & available(Z) & hoist(Z) <-
	lift(Z, X, A, B);
	load(Z, X, C, B);
	unload(Z, Y, D, B);
	drop(Z, Y, A, B);
	unload(Z, X, C, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & crate(Y) & surface(Y) & at(X, C) & place(C) & at(B, C) & B \== X & truck(B) & at(D, C) & D \== X & D \== Y & on(X, D) & surface(D) & at(V7, C) & V7 \== X & in(Y, V7) & truck(V7) & at(Z, C) & X \== Z & hoist(Z) & lifting(Z, A) & A \== X & A \== Y & crate(A) <-
	load(Z, A, B, C);
	lift(Z, X, D, C);
	load(Z, X, B, C);
	unload(Z, Y, V7, C);
	drop(Z, Y, D, C);
	unload(Z, X, B, C);
	drop(Z, X, Y, C).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, B) & place(B) & at(C, B) & available(C) & hoist(C) & at(D, B) & C \== D & D \== X & D \== Y & clear(D) & crate(D) & at(V7, B) & C \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & on(V7, Y) & crate(V7) & surface(V7) & in(X, Z) & C \== Z & D \== Z & V7 \== Z & Y \== Z & truck(Z) & at(Z, A) & A \== B & place(A) <-
	drive(Z, A, B);
	lift(C, D, V7, B);
	load(C, D, Z, B);
	lift(C, V7, Y, B);
	load(C, V7, Z, B);
	unload(C, X, Z, B);
	drop(C, X, Y, B).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, C) & place(C) & at(B, C) & in(X, B) & truck(B) & at(D, C) & B \== D & D \== X & D \== Y & clear(D) & crate(D) & at(V7, C) & B \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & on(V7, Y) & crate(V7) & surface(V7) & at(Z, C) & D \== Z & V7 \== Z & hoist(Z) & lifting(Z, A) & A \== D & A \== V7 & A \== X & crate(A) <-
	load(Z, A, B, C);
	lift(Z, D, V7, C);
	load(Z, D, B, C);
	lift(Z, V7, Y, C);
	load(Z, V7, B, C);
	unload(Z, X, B, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, B) & place(B) & at(C, B) & C \== X & C \== Y & truck(C) & at(Y, D) & B \== D & place(D) & at(V7, D) & C \== V7 & V7 \== X & available(V7) & hoist(V7) & at(V8, D) & C \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V8, Y) & clear(V8) & crate(V8) & at(Z, B) & V7 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, A) & surface(A) <-
	lift(Z, X, A, B);
	load(Z, X, C, B);
	drive(C, B, D);
	lift(V7, V8, Y, D);
	load(V7, V8, C, D);
	unload(V7, X, C, D);
	drop(V7, X, Y, D).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, A) & place(A) & at(D, A) & available(D) & hoist(D) & at(V7, A) & D \== V7 & V7 \== X & V7 \== Y & on(V7, Y) & clear(V7) & crate(V7) & at(Z, A) & D \== Z & V7 \== Z & Y \== Z & truck(Z) & lifting(C, X) & C \== D & C \== Z & hoist(C) & at(C, B) & A \== B & place(B) <-
	drive(Z, A, B);
	load(C, X, Z, B);
	drive(Z, B, A);
	lift(D, V7, Y, A);
	load(D, V7, Z, A);
	unload(D, X, Z, A);
	drop(D, X, Y, A).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, C) & at(Y, C) & place(C) & at(B, C) & B \== X & truck(B) & at(D, C) & B \== D & D \== X & D \== Y & on(D, Y) & on(X, D) & crate(D) & surface(D) & at(Z, C) & D \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== D & A \== X & crate(A) <-
	load(Z, A, B, C);
	lift(Z, X, D, C);
	load(Z, X, B, C);
	lift(Z, D, Y, C);
	load(Z, D, B, C);
	unload(Z, X, B, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, B) & at(Y, B) & place(B) & at(C, B) & C \== X & available(C) & hoist(C) & at(D, B) & C \== D & D \== X & D \== Y & on(D, Y) & clear(D) & crate(D) & at(V7, B) & C \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(V7, X) & clear(V7) & crate(V7) & on(X, V8) & surface(V8) & place(A) & A \== B & at(Z, A) & C \== Z & D \== Z & V7 \== Z & X \== Z & Y \== Z & truck(Z) <-
	drive(Z, A, B);
	lift(C, D, Y, B);
	load(C, D, Z, B);
	lift(C, V7, X, B);
	load(C, V7, Z, B);
	lift(C, X, V8, B);
	drop(C, X, Y, B).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, B) & at(Y, B) & place(B) & at(C, B) & C \== X & available(C) & hoist(C) & at(D, B) & C \== D & D \== X & D \== Y & on(D, Y) & on(X, D) & crate(D) & surface(D) & place(A) & A \== B & at(Z, A) & C \== Z & D \== Z & X \== Z & Y \== Z & truck(Z) <-
	drive(Z, A, B);
	lift(C, X, D, B);
	load(C, X, Z, B);
	lift(C, D, Y, B);
	load(C, D, Z, B);
	unload(C, X, Z, B);
	drop(C, X, Y, B).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, B) & place(B) & at(A, B) & truck(A) & at(C, B) & A \== C & C \== X & C \== Y & clear(C) & crate(C) & at(D, B) & A \== D & C \== D & D \== X & D \== Y & on(C, D) & on(D, Y) & crate(D) & surface(D) & at(Z, B) & C \== Z & D \== Z & lifting(Z, X) & hoist(Z) <-
	load(Z, X, A, B);
	lift(Z, C, D, B);
	load(Z, C, A, B);
	lift(Z, D, Y, B);
	load(Z, D, A, B);
	unload(Z, X, A, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & crate(Y) & surface(Y) & at(X, B) & place(B) & at(C, B) & C \== X & available(C) & hoist(C) & at(D, B) & D \== X & D \== Y & on(X, D) & surface(D) & in(Y, Z) & C \== Z & D \== Z & X \== Z & Y \== Z & truck(Z) & at(Z, A) & A \== B & place(A) <-
	drive(Z, A, B);
	lift(C, X, D, B);
	load(C, X, Z, B);
	unload(C, Y, Z, B);
	drop(C, Y, D, B);
	unload(C, X, Z, B);
	drop(C, X, Y, B).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, C) & at(Y, C) & place(C) & at(B, C) & truck(B) & at(D, C) & B \== D & D \== X & D \== Y & clear(D) & crate(D) & at(V7, C) & B \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & on(V7, Y) & crate(V7) & surface(V7) & at(Z, C) & D \== Z & V7 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== D & A \== V7 & A \== X & crate(A) & on(X, V8) & surface(V8) <-
	load(Z, A, B, C);
	lift(Z, D, V7, C);
	load(Z, D, B, C);
	lift(Z, V7, Y, C);
	load(Z, V7, B, C);
	lift(Z, X, V8, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & crate(Y) & surface(Y) & at(X, C) & place(C) & at(B, C) & B \== X & in(Y, B) & truck(B) & at(D, C) & D \== X & D \== Y & on(X, D) & surface(D) & at(Z, C) & X \== Z & hoist(Z) & lifting(Z, A) & A \== X & A \== Y & crate(A) <-
	load(Z, A, B, C);
	lift(Z, X, D, C);
	load(Z, X, B, C);
	unload(Z, Y, B, C);
	drop(Z, Y, D, C);
	unload(Z, X, B, C);
	drop(Z, X, Y, C).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, B) & place(B) & at(C, B) & available(C) & hoist(C) & at(D, B) & C \== D & D \== X & D \== Y & clear(D) & crate(D) & at(V7, B) & C \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & on(V7, Y) & crate(V7) & surface(V7) & at(V8, B) & D \== V8 & V7 \== V8 & truck(V8) & in(X, Z) & C \== Z & D \== Z & V7 \== Z & V8 \== Z & Y \== Z & truck(Z) & at(Z, A) & A \== B & place(A) <-
	drive(Z, A, B);
	lift(C, D, V7, B);
	load(C, D, V8, B);
	lift(C, V7, Y, B);
	load(C, V7, V8, B);
	unload(C, X, Z, B);
	drop(C, X, Y, B).

+!on(X, Y) : X \== Y & clear(Y) & crate(X) & surface(X) & surface(Y) & at(X, C) & at(Y, C) & place(C) & at(B, C) & truck(B) & at(D, C) & B \== D & D \== X & D \== Y & clear(D) & crate(D) & at(V7, C) & B \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & on(V7, X) & crate(V7) & surface(V7) & at(Z, C) & D \== Z & V7 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== D & A \== V7 & A \== X & crate(A) & on(X, V8) & surface(V8) <-
	load(Z, A, B, C);
	lift(Z, D, V7, C);
	load(Z, D, B, C);
	lift(Z, V7, X, C);
	load(Z, V7, B, C);
	lift(Z, X, V8, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & clear(Y) & crate(X) & surface(X) & surface(Y) & at(X, B) & place(B) & at(A, B) & A \== X & A \== Y & on(A, X) & clear(A) & crate(A) & at(C, B) & A \== C & C \== X & C \== Y & truck(C) & at(Y, V7) & B \== V7 & place(V7) & at(V8, V7) & A \== V8 & C \== V8 & V8 \== X & available(V8) & hoist(V8) & at(Z, B) & A \== Z & V8 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, D) & surface(D) <-
	lift(Z, A, X, B);
	load(Z, A, C, B);
	lift(Z, X, D, B);
	load(Z, X, C, B);
	drive(C, B, V7);
	unload(V8, X, C, V7);
	drop(V8, X, Y, V7).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & crate(Y) & surface(Y) & at(X, B) & place(B) & at(C, B) & C \== X & available(C) & hoist(C) & at(D, B) & D \== X & D \== Y & on(X, D) & surface(D) & at(V7, B) & V7 \== X & truck(V7) & in(Y, Z) & C \== Z & D \== Z & V7 \== Z & X \== Z & Y \== Z & truck(Z) & at(Z, A) & A \== B & place(A) <-
	drive(Z, A, B);
	lift(C, X, D, B);
	load(C, X, V7, B);
	unload(C, Y, Z, B);
	drop(C, Y, D, B);
	unload(C, X, V7, B);
	drop(C, X, Y, B).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & crate(Y) & surface(Y) & at(X, B) & place(B) & at(A, B) & A \== X & truck(A) & at(C, B) & C \== X & C \== Y & on(X, C) & surface(C) & at(Z, B) & X \== Z & lifting(Z, Y) & hoist(Z) <-
	load(Z, Y, A, B);
	lift(Z, X, C, B);
	load(Z, X, A, B);
	unload(Z, Y, A, B);
	drop(Z, Y, C, B);
	unload(Z, X, A, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & clear(Y) & crate(X) & surface(X) & surface(Y) & at(X, C) & place(C) & at(B, C) & B \== X & B \== Y & truck(B) & at(D, C) & B \== D & D \== X & D \== Y & on(D, X) & clear(D) & crate(D) & at(Y, V8) & C \== V8 & place(V8) & at(V9, V8) & B \== V9 & D \== V9 & V9 \== X & available(V9) & hoist(V9) & at(Z, C) & D \== Z & V9 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== D & A \== X & crate(A) & on(X, V7) & surface(V7) <-
	load(Z, A, B, C);
	lift(Z, D, X, C);
	load(Z, D, B, C);
	lift(Z, X, V7, C);
	load(Z, X, B, C);
	drive(B, C, V8);
	unload(V9, X, B, V8);
	drop(V9, X, Y, V8).

+!on(X, Y) : X \== Y & clear(Y) & crate(X) & surface(X) & surface(Y) & at(X, B) & place(B) & at(C, B) & C \== X & available(C) & hoist(C) & at(D, B) & C \== D & D \== X & D \== Y & on(D, X) & clear(D) & crate(D) & at(Y, V8) & B \== V8 & place(V8) & at(V9, V8) & C \== V9 & D \== V9 & V9 \== X & available(V9) & hoist(V9) & on(X, V7) & surface(V7) & place(A) & A \== B & A \== V8 & at(Z, A) & C \== Z & D \== Z & V9 \== Z & X \== Z & Y \== Z & truck(Z) <-
	drive(Z, A, B);
	lift(C, D, X, B);
	load(C, D, Z, B);
	lift(C, X, V7, B);
	load(C, X, Z, B);
	drive(Z, B, V8);
	unload(V9, X, Z, V8);
	drop(V9, X, Y, V8).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, C) & place(C) & at(D, C) & available(D) & hoist(D) & at(V7, C) & D \== V7 & V7 \== X & V7 \== Y & clear(V7) & crate(V7) & at(V8, C) & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & on(V8, Y) & crate(V8) & surface(V8) & at(V9, C) & V7 \== V9 & V8 \== V9 & truck(V9) & lifting(Z, X) & D \== Z & hoist(Z) & at(Z, B) & B \== C & place(B) & at(A, B) & A \== D & A \== V7 & A \== V8 & A \== V9 & A \== Y & truck(A) <-
	load(Z, X, A, B);
	drive(A, B, C);
	lift(D, V7, V8, C);
	load(D, V7, V9, C);
	lift(D, V8, Y, C);
	load(D, V8, V9, C);
	unload(D, X, A, C);
	drop(D, X, Y, C).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, B) & at(Y, B) & place(B) & at(A, B) & A \== X & A \== Y & on(A, X) & clear(A) & crate(A) & at(C, B) & A \== C & C \== X & truck(C) & at(D, B) & A \== D & C \== D & D \== X & D \== Y & on(D, Y) & on(X, D) & crate(D) & surface(D) & at(Z, B) & A \== Z & D \== Z & X \== Z & available(Z) & hoist(Z) <-
	lift(Z, A, X, B);
	load(Z, A, C, B);
	lift(Z, X, D, B);
	load(Z, X, C, B);
	lift(Z, D, Y, B);
	load(Z, D, C, B);
	unload(Z, X, C, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, C) & place(C) & at(B, C) & B \== X & B \== Y & truck(B) & at(Y, V7) & C \== V7 & place(V7) & at(V8, V7) & B \== V8 & V8 \== X & available(V8) & hoist(V8) & at(V9, V7) & B \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V9, Y) & clear(V9) & crate(V9) & at(Z, C) & V8 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== X & crate(A) & on(X, D) & surface(D) <-
	load(Z, A, B, C);
	lift(Z, X, D, C);
	load(Z, X, B, C);
	drive(B, C, V7);
	lift(V8, V9, Y, V7);
	load(V8, V9, B, V7);
	unload(V8, X, B, V7);
	drop(V8, X, Y, V7).

+!on(X, Y) : X \== Y & on(Y, X) & clear(Y) & crate(X) & crate(Y) & surface(X) & surface(Y) & at(X, A) & at(Y, A) & place(A) & at(B, A) & B \== X & B \== Y & truck(B) & at(C, A) & C \== X & C \== Y & on(X, C) & surface(C) & at(Z, A) & X \== Z & Y \== Z & available(Z) & hoist(Z) <-
	lift(Z, Y, X, A);
	load(Z, Y, B, A);
	lift(Z, X, C, A);
	load(Z, X, B, A);
	unload(Z, Y, B, A);
	drop(Z, Y, C, A);
	unload(Z, X, B, A);
	drop(Z, X, Y, A).

+!on(X, Y) : X \== Y & clear(Y) & crate(X) & surface(X) & surface(Y) & at(X, C) & at(Y, C) & place(C) & at(A, C) & A \== X & A \== Y & clear(A) & crate(A) & at(B, C) & A \== B & B \== X & B \== Y & on(A, B) & crate(B) & surface(B) & at(D, C) & A \== D & B \== D & truck(D) & at(V7, C) & A \== V7 & B \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(B, V7) & on(V7, X) & crate(V7) & surface(V7) & at(Z, C) & A \== Z & B \== Z & V7 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V8) & surface(V8) <-
	lift(Z, A, B, C);
	load(Z, A, D, C);
	lift(Z, B, V7, C);
	load(Z, B, D, C);
	lift(Z, V7, X, C);
	load(Z, V7, D, C);
	lift(Z, X, V8, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, B) & place(B) & at(C, B) & C \== X & available(C) & hoist(C) & at(Y, V7) & B \== V7 & place(V7) & at(V8, V7) & C \== V8 & V8 \== X & available(V8) & hoist(V8) & at(V9, V7) & V8 \== V9 & V9 \== X & V9 \== Y & on(V9, Y) & clear(V9) & crate(V9) & on(X, D) & surface(D) & place(A) & A \== B & A \== V7 & at(Z, A) & C \== Z & V8 \== Z & V9 \== Z & X \== Z & Y \== Z & truck(Z) <-
	drive(Z, A, B);
	lift(C, X, D, B);
	load(C, X, Z, B);
	drive(Z, B, V7);
	lift(V8, V9, Y, V7);
	load(V8, V9, Z, V7);
	unload(V8, X, Z, V7);
	drop(V8, X, Y, V7).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, B) & at(Y, B) & place(B) & at(A, B) & A \== X & A \== Y & on(A, Y) & clear(A) & crate(A) & at(C, B) & A \== C & truck(C) & at(D, B) & A \== D & C \== D & D \== X & D \== Y & clear(D) & crate(D) & at(V7, B) & A \== V7 & C \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & on(V7, X) & crate(V7) & surface(V7) & at(Z, B) & A \== Z & D \== Z & V7 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V8) & surface(V8) <-
	lift(Z, A, Y, B);
	load(Z, A, C, B);
	lift(Z, D, V7, B);
	load(Z, D, C, B);
	lift(Z, V7, X, B);
	load(Z, V7, C, B);
	lift(Z, X, V8, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, B) & at(Y, B) & place(B) & at(A, B) & A \== X & A \== Y & on(X, A) & crate(A) & surface(A) & at(C, B) & A \== C & C \== X & truck(C) & at(D, B) & A \== D & C \== D & D \== X & D \== Y & on(A, D) & on(D, Y) & crate(D) & surface(D) & at(Z, B) & A \== Z & D \== Z & X \== Z & available(Z) & hoist(Z) <-
	lift(Z, X, A, B);
	load(Z, X, C, B);
	lift(Z, A, D, B);
	load(Z, A, C, B);
	lift(Z, D, Y, B);
	load(Z, D, C, B);
	unload(Z, X, C, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, C) & at(Y, C) & place(C) & at(A, C) & A \== X & A \== Y & clear(A) & crate(A) & at(B, C) & A \== B & B \== X & B \== Y & on(A, B) & crate(B) & surface(B) & at(D, C) & A \== D & B \== D & truck(D) & at(V7, C) & A \== V7 & B \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(B, V7) & on(V7, Y) & crate(V7) & surface(V7) & at(Z, C) & A \== Z & B \== Z & V7 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V8) & surface(V8) <-
	lift(Z, A, B, C);
	load(Z, A, D, C);
	lift(Z, B, V7, C);
	load(Z, B, D, C);
	lift(Z, V7, Y, C);
	load(Z, V7, D, C);
	lift(Z, X, V8, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & crate(X) & crate(Y) & surface(X) & surface(Y) & at(X, B) & place(B) & at(A, B) & A \== X & A \== Y & on(A, X) & clear(A) & crate(A) & at(C, B) & A \== C & C \== X & in(Y, C) & truck(C) & at(D, B) & A \== D & D \== X & D \== Y & on(X, D) & surface(D) & at(Z, B) & A \== Z & X \== Z & available(Z) & hoist(Z) <-
	lift(Z, A, X, B);
	load(Z, A, C, B);
	lift(Z, X, D, B);
	load(Z, X, C, B);
	unload(Z, Y, C, B);
	drop(Z, Y, D, B);
	unload(Z, X, C, B);
	drop(Z, X, Y, B).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, C) & place(C) & at(A, C) & A \== X & A \== Y & clear(A) & crate(A) & at(B, C) & A \== B & B \== X & B \== Y & on(A, B) & crate(B) & surface(B) & at(D, C) & A \== D & B \== D & in(X, D) & truck(D) & at(V7, C) & A \== V7 & B \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(B, V7) & on(V7, Y) & crate(V7) & surface(V7) & at(Z, C) & A \== Z & B \== Z & V7 \== Z & available(Z) & hoist(Z) <-
	lift(Z, A, B, C);
	load(Z, A, D, C);
	lift(Z, B, V7, C);
	load(Z, B, D, C);
	lift(Z, V7, Y, C);
	load(Z, V7, D, C);
	unload(Z, X, D, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & crate(X) & crate(Y) & surface(X) & surface(Y) & at(X, B) & place(B) & at(A, B) & A \== X & A \== Y & on(A, X) & clear(A) & crate(A) & at(C, B) & A \== C & C \== X & truck(C) & at(D, B) & A \== D & D \== X & D \== Y & on(X, D) & surface(D) & at(V7, B) & A \== V7 & V7 \== X & in(Y, V7) & truck(V7) & at(Z, B) & A \== Z & X \== Z & available(Z) & hoist(Z) <-
	lift(Z, A, X, B);
	load(Z, A, C, B);
	lift(Z, X, D, B);
	load(Z, X, C, B);
	unload(Z, Y, V7, B);
	drop(Z, Y, D, B);
	unload(Z, X, C, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, B) & place(B) & at(Y, D) & B \== D & place(D) & at(C, D) & C \== X & C \== Y & truck(C) & at(V7, D) & C \== V7 & V7 \== X & available(V7) & hoist(V7) & at(V8, D) & C \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V8, Y) & clear(V8) & crate(V8) & at(Z, B) & C \== Z & V7 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, A) & surface(A) <-
	lift(Z, X, A, B);
	drive(C, D, B);
	load(Z, X, C, B);
	drive(C, B, D);
	lift(V7, V8, Y, D);
	load(V7, V8, C, D);
	unload(V7, X, C, D);
	drop(V7, X, Y, D).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, C) & place(C) & at(D, C) & available(D) & hoist(D) & at(V7, C) & D \== V7 & V7 \== X & V7 \== Y & clear(V7) & crate(V7) & at(V8, C) & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & on(V8, Y) & crate(V8) & surface(V8) & lifting(Z, X) & D \== Z & hoist(Z) & at(Z, B) & B \== C & place(B) & at(A, B) & A \== D & A \== V7 & A \== V8 & A \== Y & truck(A) <-
	load(Z, X, A, B);
	drive(A, B, C);
	lift(D, V7, V8, C);
	load(D, V7, A, C);
	lift(D, V8, Y, C);
	load(D, V8, A, C);
	unload(D, X, A, C);
	drop(D, X, Y, C).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, D) & place(D) & at(V7, D) & available(V7) & hoist(V7) & at(V8, D) & V7 \== V8 & V8 \== X & V8 \== Y & clear(V8) & crate(V8) & at(V9, D) & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, Y) & crate(V9) & surface(V9) & lifting(C, X) & C \== V7 & hoist(C) & at(C, B) & B \== D & place(B) & place(A) & A \== B & A \== D & at(Z, A) & C \== Z & V7 \== Z & V8 \== Z & V9 \== Z & Y \== Z & truck(Z) <-
	drive(Z, A, B);
	load(C, X, Z, B);
	drive(Z, B, D);
	lift(V7, V8, V9, D);
	load(V7, V8, Z, D);
	lift(V7, V9, Y, D);
	load(V7, V9, Z, D);
	unload(V7, X, Z, D);
	drop(V7, X, Y, D).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, B) & place(B) & at(A, B) & truck(A) & at(C, B) & A \== C & C \== X & C \== Y & clear(C) & crate(C) & at(D, B) & A \== D & C \== D & D \== X & D \== Y & on(C, D) & crate(D) & surface(D) & at(V7, B) & A \== V7 & C \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & on(V7, Y) & crate(V7) & surface(V7) & at(Z, B) & C \== Z & D \== Z & V7 \== Z & lifting(Z, X) & hoist(Z) <-
	load(Z, X, A, B);
	lift(Z, C, D, B);
	load(Z, C, A, B);
	lift(Z, D, V7, B);
	load(Z, D, A, B);
	lift(Z, V7, Y, B);
	load(Z, V7, A, B);
	unload(Z, X, A, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, B) & at(Y, B) & place(B) & at(C, B) & C \== X & available(C) & hoist(C) & at(D, B) & C \== D & D \== X & D \== Y & on(D, Y) & clear(D) & crate(D) & at(V7, B) & C \== V7 & D \== V7 & V7 \== X & V7 \== Y & clear(V7) & crate(V7) & at(V8, B) & C \== V8 & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & on(V8, X) & crate(V8) & surface(V8) & on(X, V9) & surface(V9) & place(A) & A \== B & at(Z, A) & C \== Z & D \== Z & V7 \== Z & V8 \== Z & X \== Z & Y \== Z & truck(Z) <-
	drive(Z, A, B);
	lift(C, D, Y, B);
	load(C, D, Z, B);
	lift(C, V7, V8, B);
	load(C, V7, Z, B);
	lift(C, V8, X, B);
	load(C, V8, Z, B);
	lift(C, X, V9, B);
	drop(C, X, Y, B).

+!on(X, Y) : X \== Y & on(Y, X) & clear(Y) & crate(X) & crate(Y) & surface(X) & surface(Y) & at(X, B) & at(Y, B) & place(B) & at(C, B) & C \== X & C \== Y & available(C) & hoist(C) & at(D, B) & D \== X & D \== Y & on(X, D) & surface(D) & place(A) & A \== B & at(Z, A) & C \== Z & D \== Z & X \== Z & Y \== Z & truck(Z) <-
	drive(Z, A, B);
	lift(C, Y, X, B);
	load(C, Y, Z, B);
	lift(C, X, D, B);
	load(C, X, Z, B);
	unload(C, Y, Z, B);
	drop(C, Y, D, B);
	unload(C, X, Z, B);
	drop(C, X, Y, B).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, C) & place(C) & at(B, C) & in(X, B) & truck(B) & at(D, C) & B \== D & D \== X & D \== Y & clear(D) & crate(D) & at(V7, C) & B \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & crate(V7) & surface(V7) & at(V8, C) & B \== V8 & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & on(V8, Y) & crate(V8) & surface(V8) & at(Z, C) & D \== Z & V7 \== Z & V8 \== Z & hoist(Z) & lifting(Z, A) & A \== D & A \== V7 & A \== V8 & A \== X & crate(A) <-
	load(Z, A, B, C);
	lift(Z, D, V7, C);
	load(Z, D, B, C);
	lift(Z, V7, V8, C);
	load(Z, V7, B, C);
	lift(Z, V8, Y, C);
	load(Z, V8, B, C);
	unload(Z, X, B, C);
	drop(Z, X, Y, C).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, B) & place(B) & at(C, B) & available(C) & hoist(C) & at(D, B) & C \== D & D \== X & D \== Y & clear(D) & crate(D) & at(V7, B) & C \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & crate(V7) & surface(V7) & at(V8, B) & C \== V8 & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & on(V8, Y) & crate(V8) & surface(V8) & in(X, Z) & C \== Z & D \== Z & V7 \== Z & V8 \== Z & Y \== Z & truck(Z) & at(Z, A) & A \== B & place(A) <-
	drive(Z, A, B);
	lift(C, D, V7, B);
	load(C, D, Z, B);
	lift(C, V7, V8, B);
	load(C, V7, Z, B);
	lift(C, V8, Y, B);
	load(C, V8, Z, B);
	unload(C, X, Z, B);
	drop(C, X, Y, B).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, B) & place(B) & at(A, B) & A \== X & A \== Y & on(A, X) & clear(A) & crate(A) & at(C, B) & A \== C & C \== X & C \== Y & truck(C) & at(Y, V7) & B \== V7 & place(V7) & at(V8, V7) & A \== V8 & C \== V8 & V8 \== X & available(V8) & hoist(V8) & at(V9, V7) & A \== V9 & C \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V9, Y) & clear(V9) & crate(V9) & at(Z, B) & A \== Z & V8 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, D) & surface(D) <-
	lift(Z, A, X, B);
	load(Z, A, C, B);
	lift(Z, X, D, B);
	load(Z, X, C, B);
	drive(C, B, V7);
	lift(V8, V9, Y, V7);
	load(V8, V9, C, V7);
	unload(V8, X, C, V7);
	drop(V8, X, Y, V7).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, B) & at(Y, B) & place(B) & at(C, B) & C \== X & available(C) & hoist(C) & at(D, B) & C \== D & D \== X & D \== Y & on(X, D) & crate(D) & surface(D) & at(V7, B) & C \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & on(V7, Y) & crate(V7) & surface(V7) & place(A) & A \== B & at(Z, A) & C \== Z & D \== Z & V7 \== Z & X \== Z & Y \== Z & truck(Z) <-
	drive(Z, A, B);
	lift(C, X, D, B);
	load(C, X, Z, B);
	lift(C, D, V7, B);
	load(C, D, Z, B);
	lift(C, V7, Y, B);
	load(C, V7, Z, B);
	unload(C, X, Z, B);
	drop(C, X, Y, B).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, B) & place(B) & at(C, B) & C \== X & C \== Y & truck(C) & at(Y, D) & B \== D & place(D) & at(V7, D) & C \== V7 & V7 \== X & available(V7) & hoist(V7) & at(V8, D) & C \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & clear(V8) & crate(V8) & at(V9, D) & C \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, Y) & crate(V9) & surface(V9) & at(Z, B) & V7 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, A) & surface(A) <-
	lift(Z, X, A, B);
	load(Z, X, C, B);
	drive(C, B, D);
	lift(V7, V8, V9, D);
	load(V7, V8, C, D);
	lift(V7, V9, Y, D);
	load(V7, V9, C, D);
	unload(V7, X, C, D);
	drop(V7, X, Y, D).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, A) & place(A) & at(D, A) & available(D) & hoist(D) & at(V7, A) & D \== V7 & V7 \== X & V7 \== Y & clear(V7) & crate(V7) & at(V8, A) & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & on(V8, Y) & crate(V8) & surface(V8) & at(Z, A) & D \== Z & V7 \== Z & V8 \== Z & Y \== Z & truck(Z) & lifting(C, X) & C \== D & C \== Z & hoist(C) & at(C, B) & A \== B & place(B) <-
	drive(Z, A, B);
	load(C, X, Z, B);
	drive(Z, B, A);
	lift(D, V7, V8, A);
	load(D, V7, Z, A);
	lift(D, V8, Y, A);
	load(D, V8, Z, A);
	unload(D, X, Z, A);
	drop(D, X, Y, A).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, C) & at(Y, C) & place(C) & at(B, C) & B \== X & truck(B) & at(D, C) & B \== D & D \== X & D \== Y & on(D, X) & clear(D) & crate(D) & at(V7, C) & B \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(V7, Y) & on(X, V7) & crate(V7) & surface(V7) & at(Z, C) & D \== Z & V7 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== D & A \== V7 & A \== X & crate(A) <-
	load(Z, A, B, C);
	lift(Z, D, X, C);
	load(Z, D, B, C);
	lift(Z, X, V7, C);
	load(Z, X, B, C);
	lift(Z, V7, Y, C);
	load(Z, V7, B, C);
	unload(Z, X, B, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, C) & at(Y, C) & place(C) & at(B, C) & B \== X & truck(B) & at(D, C) & B \== D & D \== X & D \== Y & on(X, D) & crate(D) & surface(D) & at(V7, C) & B \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & on(V7, Y) & crate(V7) & surface(V7) & at(Z, C) & D \== Z & V7 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== D & A \== V7 & A \== X & crate(A) <-
	load(Z, A, B, C);
	lift(Z, X, D, C);
	load(Z, X, B, C);
	lift(Z, D, V7, C);
	load(Z, D, B, C);
	lift(Z, V7, Y, C);
	load(Z, V7, B, C);
	unload(Z, X, B, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & crate(X) & crate(Y) & surface(X) & surface(Y) & at(X, B) & place(B) & at(C, B) & C \== X & available(C) & hoist(C) & at(D, B) & C \== D & D \== X & D \== Y & on(D, X) & clear(D) & crate(D) & at(V7, B) & D \== V7 & V7 \== X & V7 \== Y & on(X, V7) & surface(V7) & in(Y, Z) & C \== Z & D \== Z & V7 \== Z & X \== Z & Y \== Z & truck(Z) & at(Z, A) & A \== B & place(A) <-
	drive(Z, A, B);
	lift(C, D, X, B);
	load(C, D, Z, B);
	lift(C, X, V7, B);
	load(C, X, Z, B);
	unload(C, Y, Z, B);
	drop(C, Y, V7, B);
	unload(C, X, Z, B);
	drop(C, X, Y, B).

+!on(X, Y) : X \== Y & clear(Y) & crate(X) & surface(X) & surface(Y) & at(X, C) & at(Y, C) & place(C) & at(B, C) & truck(B) & at(D, C) & B \== D & D \== X & D \== Y & clear(D) & crate(D) & at(V7, C) & B \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & crate(V7) & surface(V7) & at(V8, C) & B \== V8 & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & on(V8, X) & crate(V8) & surface(V8) & at(Z, C) & D \== Z & V7 \== Z & V8 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== D & A \== V7 & A \== V8 & A \== X & crate(A) & on(X, V9) & surface(V9) <-
	load(Z, A, B, C);
	lift(Z, D, V7, C);
	load(Z, D, B, C);
	lift(Z, V7, V8, C);
	load(Z, V7, B, C);
	lift(Z, V8, X, C);
	load(Z, V8, B, C);
	lift(Z, X, V9, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, C) & at(Y, C) & place(C) & at(B, C) & truck(B) & at(D, C) & B \== D & D \== X & D \== Y & clear(D) & crate(D) & at(V7, C) & B \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & crate(V7) & surface(V7) & at(V8, C) & B \== V8 & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & on(V8, Y) & crate(V8) & surface(V8) & at(Z, C) & D \== Z & V7 \== Z & V8 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== D & A \== V7 & A \== V8 & A \== X & crate(A) & on(X, V9) & surface(V9) <-
	load(Z, A, B, C);
	lift(Z, D, V7, C);
	load(Z, D, B, C);
	lift(Z, V7, V8, C);
	load(Z, V7, B, C);
	lift(Z, V8, Y, C);
	load(Z, V8, B, C);
	lift(Z, X, V9, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, B) & place(B) & at(C, B) & C \== X & C \== Y & truck(C) & at(Y, D) & B \== D & place(D) & at(V10, D) & C \== V10 & V10 \== X & truck(V10) & at(V7, D) & C \== V7 & V7 \== X & available(V7) & hoist(V7) & at(V8, D) & C \== V8 & V10 \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & clear(V8) & crate(V8) & at(V9, D) & C \== V9 & V10 \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, Y) & crate(V9) & surface(V9) & at(Z, B) & V7 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, A) & surface(A) <-
	lift(Z, X, A, B);
	load(Z, X, C, B);
	drive(C, B, D);
	lift(V7, V8, V9, D);
	load(V7, V8, V10, D);
	lift(V7, V9, Y, D);
	load(V7, V9, V10, D);
	unload(V7, X, C, D);
	drop(V7, X, Y, D).

+!on(X, Y) : X \== Y & clear(Y) & crate(X) & surface(X) & surface(Y) & at(X, C) & place(C) & at(A, C) & A \== X & A \== Y & clear(A) & crate(A) & at(B, C) & A \== B & B \== X & B \== Y & on(A, B) & on(B, X) & crate(B) & surface(B) & at(D, C) & A \== D & B \== D & D \== X & D \== Y & truck(D) & at(Y, V8) & C \== V8 & place(V8) & at(V9, V8) & A \== V9 & B \== V9 & D \== V9 & V9 \== X & available(V9) & hoist(V9) & at(Z, C) & A \== Z & B \== Z & V9 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V7) & surface(V7) <-
	lift(Z, A, B, C);
	load(Z, A, D, C);
	lift(Z, B, X, C);
	load(Z, B, D, C);
	lift(Z, X, V7, C);
	load(Z, X, D, C);
	drive(D, C, V8);
	unload(V9, X, D, V8);
	drop(V9, X, Y, V8).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, C) & at(Y, C) & place(C) & at(A, C) & A \== X & A \== Y & clear(A) & crate(A) & at(B, C) & A \== B & B \== X & B \== Y & on(A, B) & on(B, X) & crate(B) & surface(B) & at(D, C) & A \== D & B \== D & D \== X & truck(D) & at(V7, C) & A \== V7 & B \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(V7, Y) & on(X, V7) & crate(V7) & surface(V7) & at(Z, C) & A \== Z & B \== Z & V7 \== Z & X \== Z & available(Z) & hoist(Z) <-
	lift(Z, A, B, C);
	load(Z, A, D, C);
	lift(Z, B, X, C);
	load(Z, B, D, C);
	lift(Z, X, V7, C);
	load(Z, X, D, C);
	lift(Z, V7, Y, C);
	load(Z, V7, D, C);
	unload(Z, X, D, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, B) & at(Y, B) & place(B) & at(A, B) & A \== X & A \== Y & on(A, X) & clear(A) & crate(A) & at(C, B) & A \== C & C \== X & truck(C) & at(D, B) & A \== D & C \== D & D \== X & D \== Y & on(X, D) & crate(D) & surface(D) & at(V7, B) & A \== V7 & C \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & on(V7, Y) & crate(V7) & surface(V7) & at(Z, B) & A \== Z & D \== Z & V7 \== Z & X \== Z & available(Z) & hoist(Z) <-
	lift(Z, A, X, B);
	load(Z, A, C, B);
	lift(Z, X, D, B);
	load(Z, X, C, B);
	lift(Z, D, V7, B);
	load(Z, D, C, B);
	lift(Z, V7, Y, B);
	load(Z, V7, C, B);
	unload(Z, X, C, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, B) & place(B) & at(Y, V7) & B \== V7 & place(V7) & at(V10, V7) & V10 \== X & V10 \== Y & on(V10, Y) & crate(V10) & surface(V10) & at(V8, V7) & V10 \== V8 & V8 \== X & available(V8) & hoist(V8) & at(V9, V7) & V10 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V9, V10) & clear(V9) & crate(V9) & at(Z, B) & V8 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, A) & surface(A) & place(D) & B \== D & D \== V7 & at(C, D) & C \== V10 & C \== V8 & C \== V9 & C \== X & C \== Y & C \== Z & truck(C) <-
	lift(Z, X, A, B);
	drive(C, D, B);
	load(Z, X, C, B);
	drive(C, B, V7);
	lift(V8, V9, V10, V7);
	load(V8, V9, C, V7);
	lift(V8, V10, Y, V7);
	load(V8, V10, C, V7);
	unload(V8, X, C, V7);
	drop(V8, X, Y, V7).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, C) & place(C) & at(A, C) & A \== X & A \== Y & clear(A) & crate(A) & at(B, C) & A \== B & B \== X & B \== Y & on(A, B) & crate(B) & surface(B) & at(D, C) & A \== D & B \== D & in(X, D) & truck(D) & at(V7, C) & A \== V7 & B \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(B, V7) & crate(V7) & surface(V7) & at(V8, C) & A \== V8 & B \== V8 & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & on(V8, Y) & crate(V8) & surface(V8) & at(Z, C) & A \== Z & B \== Z & V7 \== Z & V8 \== Z & available(Z) & hoist(Z) <-
	lift(Z, A, B, C);
	load(Z, A, D, C);
	lift(Z, B, V7, C);
	load(Z, B, D, C);
	lift(Z, V7, V8, C);
	load(Z, V7, D, C);
	lift(Z, V8, Y, C);
	load(Z, V8, D, C);
	unload(Z, X, D, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, C) & place(C) & at(B, C) & B \== X & B \== Y & truck(B) & at(Y, V7) & C \== V7 & place(V7) & at(V10, V7) & B \== V10 & V10 \== X & V10 \== Y & on(V10, Y) & crate(V10) & surface(V10) & at(V8, V7) & B \== V8 & V10 \== V8 & V8 \== X & available(V8) & hoist(V8) & at(V9, V7) & B \== V9 & V10 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V9, V10) & clear(V9) & crate(V9) & at(Z, C) & V8 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== X & crate(A) & on(X, D) & surface(D) <-
	load(Z, A, B, C);
	lift(Z, X, D, C);
	load(Z, X, B, C);
	drive(B, C, V7);
	lift(V8, V9, V10, V7);
	load(V8, V9, B, V7);
	lift(V8, V10, Y, V7);
	load(V8, V10, B, V7);
	unload(V8, X, B, V7);
	drop(V8, X, Y, V7).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, C) & at(Y, C) & place(C) & at(A, C) & A \== X & A \== Y & clear(A) & crate(A) & at(B, C) & A \== B & B \== X & B \== Y & on(A, B) & crate(B) & surface(B) & at(D, C) & A \== D & B \== D & truck(D) & at(V7, C) & A \== V7 & B \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(B, V7) & crate(V7) & surface(V7) & at(V8, C) & A \== V8 & B \== V8 & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & on(V8, Y) & crate(V8) & surface(V8) & at(Z, C) & A \== Z & B \== Z & V7 \== Z & V8 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V9) & surface(V9) <-
	lift(Z, A, B, C);
	load(Z, A, D, C);
	lift(Z, B, V7, C);
	load(Z, B, D, C);
	lift(Z, V7, V8, C);
	load(Z, V7, D, C);
	lift(Z, V8, Y, C);
	load(Z, V8, D, C);
	lift(Z, X, V9, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, B) & place(B) & at(Y, D) & B \== D & place(D) & at(C, D) & C \== X & C \== Y & truck(C) & at(V7, D) & C \== V7 & V7 \== X & available(V7) & hoist(V7) & at(V8, D) & C \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & clear(V8) & crate(V8) & at(V9, D) & C \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, Y) & crate(V9) & surface(V9) & at(Z, B) & C \== Z & V7 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, A) & surface(A) <-
	lift(Z, X, A, B);
	drive(C, D, B);
	load(Z, X, C, B);
	drive(C, B, D);
	lift(V7, V8, V9, D);
	load(V7, V8, C, D);
	lift(V7, V9, Y, D);
	load(V7, V9, C, D);
	unload(V7, X, C, D);
	drop(V7, X, Y, D).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, V9) & place(V9) & at(V10, V9) & V10 \== X & V10 \== Y & truck(V10) & at(V7, V9) & V7 \== X & available(V7) & hoist(V7) & at(Y, D) & D \== V9 & place(D) & at(B, D) & B \== V10 & B \== X & B \== Y & on(B, Y) & crate(B) & surface(B) & at(C, D) & truck(C) & at(V11, D) & B \== V11 & V10 \== V11 & V11 \== X & V11 \== Y & on(V11, B) & clear(V11) & crate(V11) & at(Z, D) & B \== Z & V10 \== Z & V11 \== Z & V7 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== B & A \== V11 & A \== X & crate(A) & on(X, V8) & surface(V8) <-
	load(Z, A, C, D);
	lift(V7, X, V8, V9);
	load(V7, X, V10, V9);
	drive(V10, V9, D);
	lift(Z, V11, B, D);
	load(Z, V11, V10, D);
	lift(Z, B, Y, D);
	load(Z, B, V10, D);
	unload(Z, X, V10, D);
	drop(Z, X, Y, D).

+!on(X, Y) : X \== Y & clear(Y) & crate(X) & surface(X) & surface(Y) & at(X, C) & place(C) & at(B, C) & B \== X & B \== Y & truck(B) & at(D, C) & B \== D & D \== X & D \== Y & clear(D) & crate(D) & at(V7, C) & B \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & on(V7, X) & crate(V7) & surface(V7) & at(Y, V9) & C \== V9 & place(V9) & at(V10, V9) & B \== V10 & D \== V10 & V10 \== V7 & V10 \== X & available(V10) & hoist(V10) & at(Z, C) & D \== Z & V10 \== Z & V7 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== D & A \== V7 & A \== X & crate(A) & on(X, V8) & surface(V8) <-
	load(Z, A, B, C);
	lift(Z, D, V7, C);
	load(Z, D, B, C);
	lift(Z, V7, X, C);
	load(Z, V7, B, C);
	lift(Z, X, V8, C);
	load(Z, X, B, C);
	drive(B, C, V9);
	unload(V10, X, B, V9);
	drop(V10, X, Y, V9).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, C) & place(C) & at(D, C) & available(D) & hoist(D) & at(V7, C) & D \== V7 & V7 \== X & V7 \== Y & clear(V7) & crate(V7) & at(V8, C) & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & crate(V8) & surface(V8) & at(V9, C) & D \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, Y) & crate(V9) & surface(V9) & lifting(Z, X) & D \== Z & hoist(Z) & at(Z, B) & B \== C & place(B) & at(A, B) & A \== D & A \== V7 & A \== V8 & A \== V9 & A \== Y & truck(A) <-
	load(Z, X, A, B);
	drive(A, B, C);
	lift(D, V7, V8, C);
	load(D, V7, A, C);
	lift(D, V8, V9, C);
	load(D, V8, A, C);
	lift(D, V9, Y, C);
	load(D, V9, A, C);
	unload(D, X, A, C);
	drop(D, X, Y, C).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, B) & at(Y, B) & place(B) & at(A, B) & A \== X & A \== Y & on(X, A) & crate(A) & surface(A) & at(C, B) & A \== C & C \== X & truck(C) & at(D, B) & A \== D & C \== D & D \== X & D \== Y & on(A, D) & crate(D) & surface(D) & at(V7, B) & A \== V7 & C \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & on(V7, Y) & crate(V7) & surface(V7) & at(Z, B) & A \== Z & D \== Z & V7 \== Z & X \== Z & available(Z) & hoist(Z) <-
	lift(Z, X, A, B);
	load(Z, X, C, B);
	lift(Z, A, D, B);
	load(Z, A, C, B);
	lift(Z, D, V7, B);
	load(Z, D, C, B);
	lift(Z, V7, Y, B);
	load(Z, V7, C, B);
	unload(Z, X, C, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, B) & place(B) & at(C, B) & C \== X & available(C) & hoist(C) & at(D, B) & C \== D & D \== X & D \== Y & on(D, X) & clear(D) & crate(D) & at(Y, V8) & B \== V8 & place(V8) & at(V10, V8) & D \== V10 & V10 \== X & V10 \== Y & on(V10, Y) & clear(V10) & crate(V10) & at(V9, V8) & C \== V9 & D \== V9 & V10 \== V9 & V9 \== X & available(V9) & hoist(V9) & on(X, V7) & surface(V7) & place(A) & A \== B & A \== V8 & at(Z, A) & C \== Z & D \== Z & V10 \== Z & V9 \== Z & X \== Z & Y \== Z & truck(Z) <-
	drive(Z, A, B);
	lift(C, D, X, B);
	load(C, D, Z, B);
	lift(C, X, V7, B);
	load(C, X, Z, B);
	drive(Z, B, V8);
	lift(V9, V10, Y, V8);
	load(V9, V10, Z, V8);
	unload(V9, X, Z, V8);
	drop(V9, X, Y, V8).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, B) & at(Y, B) & place(B) & at(A, B) & A \== X & A \== Y & on(A, Y) & clear(A) & crate(A) & at(C, B) & A \== C & truck(C) & at(D, B) & A \== D & C \== D & D \== X & D \== Y & clear(D) & crate(D) & at(V7, B) & A \== V7 & C \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & crate(V7) & surface(V7) & at(V8, B) & A \== V8 & C \== V8 & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & on(V8, X) & crate(V8) & surface(V8) & at(Z, B) & A \== Z & D \== Z & V7 \== Z & V8 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V9) & surface(V9) <-
	lift(Z, A, Y, B);
	load(Z, A, C, B);
	lift(Z, D, V7, B);
	load(Z, D, C, B);
	lift(Z, V7, V8, B);
	load(Z, V7, C, B);
	lift(Z, V8, X, B);
	load(Z, V8, C, B);
	lift(Z, X, V9, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, C) & place(C) & at(B, C) & B \== X & B \== Y & truck(B) & at(D, C) & B \== D & D \== X & D \== Y & on(D, X) & clear(D) & crate(D) & at(Y, V8) & C \== V8 & place(V8) & at(V10, V8) & B \== V10 & D \== V10 & V10 \== X & V10 \== Y & on(V10, Y) & clear(V10) & crate(V10) & at(V9, V8) & B \== V9 & D \== V9 & V10 \== V9 & V9 \== X & available(V9) & hoist(V9) & at(Z, C) & D \== Z & V9 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== D & A \== X & crate(A) & on(X, V7) & surface(V7) <-
	load(Z, A, B, C);
	lift(Z, D, X, C);
	load(Z, D, B, C);
	lift(Z, X, V7, C);
	load(Z, X, B, C);
	drive(B, C, V8);
	lift(V9, V10, Y, V8);
	load(V9, V10, B, V8);
	unload(V9, X, B, V8);
	drop(V9, X, Y, V8).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, V10) & place(V10) & at(V8, V10) & V8 \== X & available(V8) & hoist(V8) & at(Y, V7) & V10 \== V7 & place(V7) & at(B, V7) & B \== X & B \== Y & clear(B) & crate(B) & at(C, V7) & B \== C & C \== X & C \== Y & on(B, C) & on(C, Y) & crate(C) & surface(C) & at(D, V7) & truck(D) & at(Z, V7) & B \== Z & C \== Z & V8 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== B & A \== C & A \== X & crate(A) & on(X, V9) & surface(V9) & place(V12) & V10 \== V12 & V12 \== V7 & at(V11, V12) & B \== V11 & C \== V11 & V11 \== V8 & V11 \== X & V11 \== Y & V11 \== Z & truck(V11) <-
	load(Z, A, D, V7);
	lift(V8, X, V9, V10);
	drive(V11, V12, V10);
	load(V8, X, V11, V10);
	drive(V11, V10, V7);
	lift(Z, B, C, V7);
	load(Z, B, V11, V7);
	lift(Z, C, Y, V7);
	load(Z, C, V11, V7);
	unload(Z, X, V11, V7);
	drop(Z, X, Y, V7).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, B) & place(B) & at(C, B) & available(C) & hoist(C) & at(D, B) & C \== D & D \== X & D \== Y & clear(D) & crate(D) & at(V7, B) & C \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & crate(V7) & surface(V7) & at(V8, B) & C \== V8 & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & crate(V8) & surface(V8) & at(V9, B) & C \== V9 & D \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, Y) & crate(V9) & surface(V9) & in(X, Z) & C \== Z & D \== Z & V7 \== Z & V8 \== Z & V9 \== Z & Y \== Z & truck(Z) & at(Z, A) & A \== B & place(A) <-
	drive(Z, A, B);
	lift(C, D, V7, B);
	load(C, D, Z, B);
	lift(C, V7, V8, B);
	load(C, V7, Z, B);
	lift(C, V8, V9, B);
	load(C, V8, Z, B);
	lift(C, V9, Y, B);
	load(C, V9, Z, B);
	unload(C, X, Z, B);
	drop(C, X, Y, B).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, B) & place(B) & at(A, B) & A \== X & A \== Y & on(A, X) & clear(A) & crate(A) & at(C, B) & A \== C & C \== X & C \== Y & truck(C) & at(Y, V7) & B \== V7 & place(V7) & at(V10, V7) & A \== V10 & C \== V10 & V10 \== X & V10 \== Y & on(V10, Y) & crate(V10) & surface(V10) & at(V8, V7) & A \== V8 & C \== V8 & V10 \== V8 & V8 \== X & available(V8) & hoist(V8) & at(V9, V7) & A \== V9 & C \== V9 & V10 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V9, V10) & clear(V9) & crate(V9) & at(Z, B) & A \== Z & V8 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, D) & surface(D) <-
	lift(Z, A, X, B);
	load(Z, A, C, B);
	lift(Z, X, D, B);
	load(Z, X, C, B);
	drive(C, B, V7);
	lift(V8, V9, V10, V7);
	load(V8, V9, C, V7);
	lift(V8, V10, Y, V7);
	load(V8, V10, C, V7);
	unload(V8, X, C, V7);
	drop(V8, X, Y, V7).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, V8) & place(V8) & at(D, V8) & D \== X & available(D) & hoist(D) & at(Y, C) & C \== V8 & place(C) & at(B, C) & B \== D & B \== X & B \== Y & truck(B) & at(V10, C) & B \== V10 & V10 \== X & V10 \== Y & on(V10, Y) & crate(V10) & surface(V10) & at(V9, C) & B \== V9 & V10 \== V9 & V9 \== X & V9 \== Y & on(V9, V10) & clear(V9) & crate(V9) & at(Z, C) & B \== Z & D \== Z & V10 \== Z & V9 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== V10 & A \== V9 & A \== X & crate(A) & on(X, V7) & surface(V7) <-
	load(Z, A, B, C);
	lift(D, X, V7, V8);
	drive(B, C, V8);
	load(D, X, B, V8);
	drive(B, V8, C);
	lift(Z, V9, V10, C);
	load(Z, V9, B, C);
	lift(Z, V10, Y, C);
	load(Z, V10, B, C);
	unload(Z, X, B, C);
	drop(Z, X, Y, C).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, C) & place(C) & at(B, C) & in(X, B) & truck(B) & at(D, C) & B \== D & D \== X & D \== Y & clear(D) & crate(D) & at(V7, C) & B \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & crate(V7) & surface(V7) & at(V8, C) & B \== V8 & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & crate(V8) & surface(V8) & at(V9, C) & B \== V9 & D \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, Y) & crate(V9) & surface(V9) & at(Z, C) & D \== Z & V7 \== Z & V8 \== Z & V9 \== Z & hoist(Z) & lifting(Z, A) & A \== D & A \== V7 & A \== V8 & A \== V9 & A \== X & crate(A) <-
	load(Z, A, B, C);
	lift(Z, D, V7, C);
	load(Z, D, B, C);
	lift(Z, V7, V8, C);
	load(Z, V7, B, C);
	lift(Z, V8, V9, C);
	load(Z, V8, B, C);
	lift(Z, V9, Y, C);
	load(Z, V9, B, C);
	unload(Z, X, B, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & clear(Y) & crate(X) & surface(X) & surface(Y) & at(X, C) & place(C) & at(A, C) & A \== X & A \== Y & clear(A) & crate(A) & at(B, C) & A \== B & B \== X & B \== Y & on(A, B) & crate(B) & surface(B) & at(D, C) & A \== D & B \== D & D \== X & D \== Y & truck(D) & at(V7, C) & A \== V7 & B \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(B, V7) & on(V7, X) & crate(V7) & surface(V7) & at(Y, V9) & C \== V9 & place(V9) & at(V10, V9) & A \== V10 & B \== V10 & D \== V10 & V10 \== V7 & V10 \== X & available(V10) & hoist(V10) & at(Z, C) & A \== Z & B \== Z & V10 \== Z & V7 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V8) & surface(V8) <-
	lift(Z, A, B, C);
	load(Z, A, D, C);
	lift(Z, B, V7, C);
	load(Z, B, D, C);
	lift(Z, V7, X, C);
	load(Z, V7, D, C);
	lift(Z, X, V8, C);
	load(Z, X, D, C);
	drive(D, C, V9);
	unload(V10, X, D, V9);
	drop(V10, X, Y, V9).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, D) & at(Y, D) & place(D) & at(C, D) & truck(C) & at(V10, D) & C \== V10 & V10 \== X & V10 \== Y & on(V10, X) & crate(V10) & surface(V10) & at(V7, D) & C \== V7 & V10 \== V7 & V7 \== X & V7 \== Y & on(V7, Y) & clear(V7) & crate(V7) & at(V8, D) & C \== V8 & V10 \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & clear(V8) & crate(V8) & at(V9, D) & C \== V9 & V10 \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, V10) & crate(V9) & surface(V9) & at(Z, D) & V10 \== Z & V7 \== Z & V8 \== Z & V9 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== V10 & A \== V7 & A \== V8 & A \== V9 & A \== X & crate(A) & on(X, B) & surface(B) <-
	load(Z, A, C, D);
	lift(Z, V7, Y, D);
	load(Z, V7, C, D);
	lift(Z, V8, V9, D);
	load(Z, V8, C, D);
	lift(Z, V9, V10, D);
	load(Z, V9, C, D);
	lift(Z, V10, X, D);
	load(Z, V10, C, D);
	lift(Z, X, B, D);
	drop(Z, X, Y, D).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, B) & at(Y, B) & place(B) & at(C, B) & C \== X & available(C) & hoist(C) & at(D, B) & C \== D & D \== X & D \== Y & on(X, D) & crate(D) & surface(D) & at(V7, B) & C \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & crate(V7) & surface(V7) & at(V8, B) & C \== V8 & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & on(V8, Y) & crate(V8) & surface(V8) & place(A) & A \== B & at(Z, A) & C \== Z & D \== Z & V7 \== Z & V8 \== Z & X \== Z & Y \== Z & truck(Z) <-
	drive(Z, A, B);
	lift(C, X, D, B);
	load(C, X, Z, B);
	lift(C, D, V7, B);
	load(C, D, Z, B);
	lift(C, V7, V8, B);
	load(C, V7, Z, B);
	lift(C, V8, Y, B);
	load(C, V8, Z, B);
	unload(C, X, Z, B);
	drop(C, X, Y, B).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, D) & at(Y, D) & place(D) & at(C, D) & truck(C) & at(V10, D) & C \== V10 & V10 \== X & V10 \== Y & on(V10, Y) & crate(V10) & surface(V10) & at(V7, D) & C \== V7 & V10 \== V7 & V7 \== X & V7 \== Y & clear(V7) & crate(V7) & at(V8, D) & C \== V8 & V10 \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & crate(V8) & surface(V8) & at(V9, D) & C \== V9 & V10 \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, V10) & crate(V9) & surface(V9) & at(Z, D) & V10 \== Z & V7 \== Z & V8 \== Z & V9 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== V10 & A \== V7 & A \== V8 & A \== V9 & A \== X & crate(A) & on(X, B) & surface(B) <-
	load(Z, A, C, D);
	lift(Z, V7, V8, D);
	load(Z, V7, C, D);
	lift(Z, V8, V9, D);
	load(Z, V8, C, D);
	lift(Z, V9, V10, D);
	load(Z, V9, C, D);
	lift(Z, V10, Y, D);
	load(Z, V10, C, D);
	lift(Z, X, B, D);
	drop(Z, X, Y, D).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, B) & place(B) & at(C, B) & C \== X & C \== Y & truck(C) & at(Y, D) & B \== D & place(D) & at(V10, D) & C \== V10 & V10 \== X & V10 \== Y & on(V10, Y) & crate(V10) & surface(V10) & at(V7, D) & C \== V7 & V10 \== V7 & V7 \== X & available(V7) & hoist(V7) & at(V8, D) & C \== V8 & V10 \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & clear(V8) & crate(V8) & at(V9, D) & C \== V9 & V10 \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, V10) & crate(V9) & surface(V9) & at(Z, B) & V7 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, A) & surface(A) <-
	lift(Z, X, A, B);
	load(Z, X, C, B);
	drive(C, B, D);
	lift(V7, V8, V9, D);
	load(V7, V8, C, D);
	lift(V7, V9, V10, D);
	load(V7, V9, C, D);
	lift(V7, V10, Y, D);
	load(V7, V10, C, D);
	unload(V7, X, C, D);
	drop(V7, X, Y, D).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, B) & place(B) & at(A, B) & truck(A) & at(C, B) & A \== C & C \== X & C \== Y & clear(C) & crate(C) & at(D, B) & A \== D & C \== D & D \== X & D \== Y & on(C, D) & crate(D) & surface(D) & at(V7, B) & A \== V7 & C \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & crate(V7) & surface(V7) & at(V8, B) & A \== V8 & C \== V8 & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & on(V8, Y) & crate(V8) & surface(V8) & at(Z, B) & C \== Z & D \== Z & V7 \== Z & V8 \== Z & lifting(Z, X) & hoist(Z) <-
	load(Z, X, A, B);
	lift(Z, C, D, B);
	load(Z, C, A, B);
	lift(Z, D, V7, B);
	load(Z, D, A, B);
	lift(Z, V7, V8, B);
	load(Z, V7, A, B);
	lift(Z, V8, Y, B);
	load(Z, V8, A, B);
	unload(Z, X, A, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, V10) & place(V10) & at(V11, V10) & V11 \== X & V11 \== Y & truck(V11) & at(V8, V10) & V8 \== X & available(V8) & hoist(V8) & at(Y, D) & D \== V10 & place(D) & at(A, D) & A \== V11 & A \== V8 & A \== X & A \== Y & clear(A) & crate(A) & at(B, D) & A \== B & B \== V11 & B \== X & B \== Y & on(B, Y) & crate(B) & surface(B) & at(C, D) & A \== C & B \== C & C \== V11 & C \== X & C \== Y & on(A, C) & on(C, B) & crate(C) & surface(C) & at(V7, D) & A \== V7 & truck(V7) & at(Z, D) & A \== Z & B \== Z & C \== Z & V11 \== Z & V8 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V9) & surface(V9) <-
	lift(Z, A, C, D);
	load(Z, A, V7, D);
	lift(V8, X, V9, V10);
	load(V8, X, V11, V10);
	drive(V11, V10, D);
	lift(Z, C, B, D);
	load(Z, C, V11, D);
	lift(Z, B, Y, D);
	load(Z, B, V11, D);
	unload(Z, X, V11, D);
	drop(Z, X, Y, D).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, C) & place(C) & at(A, C) & A \== X & A \== Y & clear(A) & crate(A) & at(B, C) & A \== B & B \== X & B \== Y & on(A, B) & on(B, X) & crate(B) & surface(B) & at(D, C) & A \== D & B \== D & D \== X & D \== Y & truck(D) & at(Y, V8) & C \== V8 & place(V8) & at(V10, V8) & A \== V10 & B \== V10 & D \== V10 & V10 \== X & V10 \== Y & on(V10, Y) & clear(V10) & crate(V10) & at(V9, V8) & A \== V9 & B \== V9 & D \== V9 & V10 \== V9 & V9 \== X & available(V9) & hoist(V9) & at(Z, C) & A \== Z & B \== Z & V9 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V7) & surface(V7) <-
	lift(Z, A, B, C);
	load(Z, A, D, C);
	lift(Z, B, X, C);
	load(Z, B, D, C);
	lift(Z, X, V7, C);
	load(Z, X, D, C);
	drive(D, C, V8);
	lift(V9, V10, Y, V8);
	load(V9, V10, D, V8);
	unload(V9, X, D, V8);
	drop(V9, X, Y, V8).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, C) & place(C) & at(D, C) & D \== X & available(D) & hoist(D) & at(V7, C) & D \== V7 & V7 \== X & V7 \== Y & clear(V7) & crate(V7) & at(V8, C) & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & on(V8, X) & crate(V8) & surface(V8) & at(Y, V10) & C \== V10 & place(V10) & at(B, V10) & B \== V7 & B \== V8 & B \== X & B \== Y & on(B, Y) & clear(B) & crate(B) & at(V11, V10) & B \== V11 & D \== V11 & V11 \== V7 & V11 \== V8 & V11 \== X & available(V11) & hoist(V11) & on(X, V9) & surface(V9) & place(A) & A \== C & A \== V10 & at(Z, A) & B \== Z & D \== Z & V11 \== Z & V7 \== Z & V8 \== Z & X \== Z & Y \== Z & truck(Z) <-
	drive(Z, A, C);
	lift(D, V7, V8, C);
	load(D, V7, Z, C);
	lift(D, V8, X, C);
	load(D, V8, Z, C);
	lift(D, X, V9, C);
	load(D, X, Z, C);
	drive(Z, C, V10);
	lift(V11, B, Y, V10);
	load(V11, B, Z, V10);
	unload(V11, X, Z, V10);
	drop(V11, X, Y, V10).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, D) & place(D) & at(C, D) & C \== X & C \== Y & truck(C) & at(V7, D) & C \== V7 & V7 \== X & V7 \== Y & on(V7, X) & clear(V7) & crate(V7) & at(Y, V9) & D \== V9 & place(V9) & at(B, V9) & B \== C & B \== V7 & B \== X & B \== Y & on(B, Y) & crate(B) & surface(B) & at(V10, V9) & B \== V10 & C \== V10 & V10 \== V7 & V10 \== X & available(V10) & hoist(V10) & at(V11, V9) & B \== V11 & C \== V11 & V10 \== V11 & V11 \== V7 & V11 \== X & V11 \== Y & on(V11, B) & clear(V11) & crate(V11) & at(Z, D) & V10 \== Z & V7 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== V7 & A \== X & crate(A) & on(X, V8) & surface(V8) <-
	load(Z, A, C, D);
	lift(Z, V7, X, D);
	load(Z, V7, C, D);
	lift(Z, X, V8, D);
	load(Z, X, C, D);
	drive(C, D, V9);
	lift(V10, V11, B, V9);
	load(V10, V11, C, V9);
	lift(V10, B, Y, V9);
	load(V10, B, C, V9);
	unload(V10, X, C, V9);
	drop(V10, X, Y, V9).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, D) & at(Y, D) & place(D) & at(A, D) & A \== X & A \== Y & clear(A) & crate(A) & at(C, D) & A \== C & C \== X & C \== Y & on(A, C) & crate(C) & surface(C) & at(V10, D) & A \== V10 & C \== V10 & V10 \== X & V10 \== Y & on(V10, Y) & crate(V10) & surface(V10) & at(V7, D) & A \== V7 & C \== V7 & V10 \== V7 & truck(V7) & at(V8, D) & A \== V8 & C \== V8 & V10 \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(C, V8) & crate(V8) & surface(V8) & at(V9, D) & A \== V9 & C \== V9 & V10 \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, V10) & crate(V9) & surface(V9) & at(Z, D) & A \== Z & C \== Z & V10 \== Z & V8 \== Z & V9 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, B) & surface(B) <-
	lift(Z, A, C, D);
	load(Z, A, V7, D);
	lift(Z, C, V8, D);
	load(Z, C, V7, D);
	lift(Z, V8, V9, D);
	load(Z, V8, V7, D);
	lift(Z, V9, V10, D);
	load(Z, V9, V7, D);
	lift(Z, V10, Y, D);
	load(Z, V10, V7, D);
	lift(Z, X, B, D);
	drop(Z, X, Y, D).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, V11) & place(V11) & at(V9, V11) & V9 \== X & available(V9) & hoist(V9) & at(Y, V7) & V11 \== V7 & place(V7) & at(A, V7) & A \== V9 & A \== X & A \== Y & clear(A) & crate(A) & at(C, V7) & A \== C & C \== X & C \== Y & on(C, Y) & crate(C) & surface(C) & at(D, V7) & A \== D & C \== D & D \== X & D \== Y & on(A, D) & on(D, C) & crate(D) & surface(D) & at(V8, V7) & A \== V8 & truck(V8) & at(Z, V7) & A \== Z & C \== Z & D \== Z & V9 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V10) & surface(V10) & place(B) & B \== V11 & B \== V7 & at(V12, B) & A \== V12 & C \== V12 & D \== V12 & V12 \== V9 & V12 \== X & V12 \== Y & V12 \== Z & truck(V12) <-
	lift(Z, A, D, V7);
	load(Z, A, V8, V7);
	lift(V9, X, V10, V11);
	drive(V12, B, V11);
	load(V9, X, V12, V11);
	drive(V12, V11, V7);
	lift(Z, D, C, V7);
	load(Z, D, V12, V7);
	lift(Z, C, Y, V7);
	load(Z, C, V12, V7);
	unload(Z, X, V12, V7);
	drop(Z, X, Y, V7).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, B) & at(Y, B) & place(B) & at(A, B) & A \== X & A \== Y & on(X, A) & crate(A) & surface(A) & at(C, B) & A \== C & C \== X & truck(C) & at(D, B) & A \== D & C \== D & D \== X & D \== Y & on(A, D) & crate(D) & surface(D) & at(V7, B) & A \== V7 & C \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & crate(V7) & surface(V7) & at(V8, B) & A \== V8 & C \== V8 & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & on(V8, Y) & crate(V8) & surface(V8) & at(Z, B) & A \== Z & D \== Z & V7 \== Z & V8 \== Z & X \== Z & available(Z) & hoist(Z) <-
	lift(Z, X, A, B);
	load(Z, X, C, B);
	lift(Z, A, D, B);
	load(Z, A, C, B);
	lift(Z, D, V7, B);
	load(Z, D, C, B);
	lift(Z, V7, V8, B);
	load(Z, V7, C, B);
	lift(Z, V8, Y, B);
	load(Z, V8, C, B);
	unload(Z, X, C, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & clear(Y) & crate(X) & surface(X) & surface(Y) & at(X, B) & place(B) & at(C, B) & C \== X & available(C) & hoist(C) & at(D, B) & C \== D & D \== X & D \== Y & clear(D) & crate(D) & at(V7, B) & C \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & crate(V7) & surface(V7) & at(V8, B) & C \== V8 & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & on(V8, X) & crate(V8) & surface(V8) & at(Y, A) & A \== B & place(A) & at(V10, A) & C \== V10 & D \== V10 & V10 \== V7 & V10 \== V8 & V10 \== X & available(V10) & hoist(V10) & at(Z, A) & C \== Z & D \== Z & V10 \== Z & V7 \== Z & V8 \== Z & X \== Z & Y \== Z & truck(Z) & on(X, V9) & surface(V9) <-
	drive(Z, A, B);
	lift(C, D, V7, B);
	load(C, D, Z, B);
	lift(C, V7, V8, B);
	load(C, V7, Z, B);
	lift(C, V8, X, B);
	load(C, V8, Z, B);
	lift(C, X, V9, B);
	load(C, X, Z, B);
	drive(Z, B, A);
	unload(V10, X, Z, A);
	drop(V10, X, Y, A).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, V12) & place(V12) & at(B, V12) & B \== X & B \== Y & truck(B) & at(V10, V12) & V10 \== X & available(V10) & hoist(V10) & at(Y, V7) & V12 \== V7 & place(V7) & at(C, V7) & B \== C & C \== X & C \== Y & on(C, Y) & crate(C) & surface(C) & at(D, V7) & truck(D) & at(V8, V7) & B \== V8 & C \== V8 & D \== V8 & V10 \== V8 & V8 \== X & V8 \== Y & clear(V8) & crate(V8) & at(V9, V7) & B \== V9 & C \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, C) & crate(V9) & surface(V9) & at(Z, V7) & B \== Z & C \== Z & V10 \== Z & V8 \== Z & V9 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== C & A \== V8 & A \== V9 & A \== X & crate(A) & on(X, V11) & surface(V11) <-
	load(Z, A, D, V7);
	lift(Z, V8, V9, V7);
	load(Z, V8, D, V7);
	lift(V10, X, V11, V12);
	load(V10, X, B, V12);
	drive(B, V12, V7);
	lift(Z, V9, C, V7);
	load(Z, V9, B, V7);
	lift(Z, C, Y, V7);
	load(Z, C, B, V7);
	unload(Z, X, B, V7);
	drop(Z, X, Y, V7).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, D) & at(Y, D) & place(D) & at(A, D) & A \== X & A \== Y & clear(A) & crate(A) & at(C, D) & A \== C & C \== X & C \== Y & on(A, C) & on(C, Y) & crate(C) & surface(C) & at(V10, D) & A \== V10 & C \== V10 & V10 \== X & V10 \== Y & on(V10, X) & crate(V10) & surface(V10) & at(V7, D) & A \== V7 & C \== V7 & V10 \== V7 & truck(V7) & at(V8, D) & A \== V8 & C \== V8 & V10 \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & clear(V8) & crate(V8) & at(V9, D) & A \== V9 & C \== V9 & V10 \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, V10) & crate(V9) & surface(V9) & at(Z, D) & A \== Z & C \== Z & V10 \== Z & V8 \== Z & V9 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, B) & surface(B) <-
	lift(Z, A, C, D);
	load(Z, A, V7, D);
	lift(Z, C, Y, D);
	load(Z, C, V7, D);
	lift(Z, V8, V9, D);
	load(Z, V8, V7, D);
	lift(Z, V9, V10, D);
	load(Z, V9, V7, D);
	lift(Z, V10, X, D);
	load(Z, V10, V7, D);
	lift(Z, X, B, D);
	drop(Z, X, Y, D).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, V7) & place(V7) & at(D, V7) & D \== X & D \== Y & truck(D) & at(Y, V11) & V11 \== V7 & place(V11) & at(C, V11) & C \== D & C \== X & C \== Y & on(C, Y) & crate(C) & surface(C) & at(V10, V11) & C \== V10 & D \== V10 & V10 \== X & V10 \== Y & on(V10, C) & crate(V10) & surface(V10) & at(V12, V11) & truck(V12) & at(V8, V11) & C \== V8 & D \== V8 & V10 \== V8 & V8 \== X & available(V8) & hoist(V8) & at(V9, V11) & C \== V9 & D \== V9 & V10 \== V9 & V12 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V9, V10) & clear(V9) & crate(V9) & at(Z, V7) & V8 \== Z & V9 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== X & crate(A) & on(X, B) & surface(B) <-
	load(Z, A, D, V7);
	lift(V8, V9, V10, V11);
	load(V8, V9, V12, V11);
	lift(Z, X, B, V7);
	load(Z, X, D, V7);
	drive(D, V7, V11);
	lift(V8, V10, C, V11);
	load(V8, V10, D, V11);
	lift(V8, C, Y, V11);
	load(V8, C, D, V11);
	unload(V8, X, D, V11);
	drop(V8, X, Y, V11).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, C) & place(C) & at(D, C) & available(D) & hoist(D) & at(V10, C) & D \== V10 & V10 \== X & V10 \== Y & on(V10, Y) & crate(V10) & surface(V10) & at(V7, C) & D \== V7 & V10 \== V7 & V7 \== X & V7 \== Y & clear(V7) & crate(V7) & at(V8, C) & D \== V8 & V10 \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & crate(V8) & surface(V8) & at(V9, C) & D \== V9 & V10 \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, V10) & crate(V9) & surface(V9) & lifting(Z, X) & D \== Z & hoist(Z) & at(Z, B) & B \== C & place(B) & at(A, B) & A \== D & A \== V10 & A \== V7 & A \== V8 & A \== V9 & A \== Y & truck(A) <-
	load(Z, X, A, B);
	drive(A, B, C);
	lift(D, V7, V8, C);
	load(D, V7, A, C);
	lift(D, V8, V9, C);
	load(D, V8, A, C);
	lift(D, V9, V10, C);
	load(D, V9, A, C);
	lift(D, V10, Y, C);
	load(D, V10, A, C);
	unload(D, X, A, C);
	drop(D, X, Y, C).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, D) & place(D) & at(C, D) & C \== X & C \== Y & truck(C) & at(Y, V8) & D \== V8 & place(V8) & at(B, V8) & B \== C & B \== X & B \== Y & on(B, Y) & crate(B) & surface(B) & at(V10, V8) & B \== V10 & C \== V10 & V10 \== X & V10 \== Y & clear(V10) & crate(V10) & at(V11, V8) & B \== V11 & C \== V11 & V10 \== V11 & V11 \== X & V11 \== Y & on(V10, V11) & on(V11, B) & crate(V11) & surface(V11) & at(V9, V8) & B \== V9 & C \== V9 & V10 \== V9 & V11 \== V9 & V9 \== X & available(V9) & hoist(V9) & at(Z, D) & V9 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== X & crate(A) & on(X, V7) & surface(V7) <-
	load(Z, A, C, D);
	lift(Z, X, V7, D);
	load(Z, X, C, D);
	drive(C, D, V8);
	lift(V9, V10, V11, V8);
	load(V9, V10, C, V8);
	lift(V9, V11, B, V8);
	load(V9, V11, C, V8);
	lift(V9, B, Y, V8);
	load(V9, B, C, V8);
	unload(V9, X, C, V8);
	drop(V9, X, Y, V8).

+!on(X, Y) : X \== Y & clear(Y) & crate(X) & surface(X) & surface(Y) & at(X, C) & place(C) & at(D, C) & D \== X & available(D) & hoist(D) & at(V7, C) & D \== V7 & V7 \== X & V7 \== Y & clear(V7) & crate(V7) & at(V8, C) & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & crate(V8) & surface(V8) & at(V9, C) & D \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, X) & crate(V9) & surface(V9) & at(Y, V11) & C \== V11 & place(V11) & at(B, V11) & B \== D & B \== V7 & B \== V8 & B \== V9 & B \== X & available(B) & hoist(B) & on(X, V10) & surface(V10) & place(A) & A \== C & A \== V11 & at(Z, A) & B \== Z & D \== Z & V7 \== Z & V8 \== Z & V9 \== Z & X \== Z & Y \== Z & truck(Z) <-
	drive(Z, A, C);
	lift(D, V7, V8, C);
	load(D, V7, Z, C);
	lift(D, V8, V9, C);
	load(D, V8, Z, C);
	lift(D, V9, X, C);
	load(D, V9, Z, C);
	lift(D, X, V10, C);
	load(D, X, Z, C);
	drive(Z, C, V11);
	unload(B, X, Z, V11);
	drop(B, X, Y, V11).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, C) & place(C) & at(A, C) & A \== X & A \== Y & clear(A) & crate(A) & at(B, C) & A \== B & B \== X & B \== Y & on(A, B) & crate(B) & surface(B) & at(D, C) & A \== D & B \== D & in(X, D) & truck(D) & at(V7, C) & A \== V7 & B \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(B, V7) & crate(V7) & surface(V7) & at(V8, C) & A \== V8 & B \== V8 & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & crate(V8) & surface(V8) & at(V9, C) & A \== V9 & B \== V9 & D \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, Y) & crate(V9) & surface(V9) & at(Z, C) & A \== Z & B \== Z & V7 \== Z & V8 \== Z & V9 \== Z & available(Z) & hoist(Z) <-
	lift(Z, A, B, C);
	load(Z, A, D, C);
	lift(Z, B, V7, C);
	load(Z, B, D, C);
	lift(Z, V7, V8, C);
	load(Z, V7, D, C);
	lift(Z, V8, V9, C);
	load(Z, V8, D, C);
	lift(Z, V9, Y, C);
	load(Z, V9, D, C);
	unload(Z, X, D, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, V9) & place(V9) & at(V7, V9) & V7 \== X & available(V7) & hoist(V7) & at(Y, C) & C \== V9 & place(C) & at(A, C) & A \== V7 & A \== X & A \== Y & clear(A) & crate(A) & at(B, C) & A \== B & B \== X & B \== Y & on(A, B) & crate(B) & surface(B) & at(D, C) & A \== D & B \== D & D \== V7 & D \== X & D \== Y & truck(D) & at(V10, C) & A \== V10 & B \== V10 & D \== V10 & V10 \== X & V10 \== Y & on(B, V10) & on(V10, Y) & crate(V10) & surface(V10) & at(Z, C) & A \== Z & B \== Z & D \== Z & V10 \== Z & V7 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V8) & surface(V8) <-
	lift(Z, A, B, C);
	load(Z, A, D, C);
	lift(V7, X, V8, V9);
	drive(D, C, V9);
	load(V7, X, D, V9);
	drive(D, V9, C);
	lift(Z, B, V10, C);
	load(Z, B, D, C);
	lift(Z, V10, Y, C);
	load(Z, V10, D, C);
	unload(Z, X, D, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, D) & place(D) & at(C, D) & C \== X & C \== Y & truck(C) & at(V7, D) & C \== V7 & V7 \== X & V7 \== Y & clear(V7) & crate(V7) & at(V8, D) & C \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & on(V8, X) & crate(V8) & surface(V8) & at(Y, V10) & D \== V10 & place(V10) & at(B, V10) & B \== C & B \== V7 & B \== V8 & B \== X & B \== Y & on(B, Y) & clear(B) & crate(B) & at(V11, V10) & B \== V11 & C \== V11 & V11 \== V7 & V11 \== V8 & V11 \== X & available(V11) & hoist(V11) & at(Z, D) & V11 \== Z & V7 \== Z & V8 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== V7 & A \== V8 & A \== X & crate(A) & on(X, V9) & surface(V9) <-
	load(Z, A, C, D);
	lift(Z, V7, V8, D);
	load(Z, V7, C, D);
	lift(Z, V8, X, D);
	load(Z, V8, C, D);
	lift(Z, X, V9, D);
	load(Z, X, C, D);
	drive(C, D, V10);
	lift(V11, B, Y, V10);
	load(V11, B, C, V10);
	unload(V11, X, C, V10);
	drop(V11, X, Y, V10).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, V7) & place(V7) & at(D, V7) & D \== X & D \== Y & clear(D) & surface(D) & at(Y, V11) & V11 \== V7 & place(V11) & at(C, V11) & C \== D & C \== X & C \== Y & on(C, Y) & crate(C) & surface(C) & at(V10, V11) & C \== V10 & D \== V10 & V10 \== X & V10 \== Y & on(V10, C) & crate(V10) & surface(V10) & at(V12, V11) & C \== V12 & V10 \== V12 & V12 \== X & V12 \== Y & truck(V12) & at(V8, V11) & C \== V8 & V10 \== V8 & V12 \== V8 & V8 \== X & available(V8) & hoist(V8) & at(V9, V11) & C \== V9 & D \== V9 & V10 \== V9 & V12 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V9, V10) & clear(V9) & crate(V9) & at(Z, V7) & V12 \== Z & V8 \== Z & V9 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== X & crate(A) & on(X, B) & surface(B) <-
	drop(Z, A, D, V7);
	lift(V8, V9, V10, V11);
	load(V8, V9, V12, V11);
	lift(Z, X, B, V7);
	drive(V12, V11, V7);
	load(Z, X, V12, V7);
	drive(V12, V7, V11);
	lift(V8, V10, C, V11);
	load(V8, V10, V12, V11);
	lift(V8, C, Y, V11);
	load(V8, C, V12, V11);
	unload(V8, X, V12, V11);
	drop(V8, X, Y, V11).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, C) & place(C) & at(A, C) & A \== X & A \== Y & on(A, X) & clear(A) & crate(A) & at(D, C) & A \== D & D \== X & D \== Y & truck(D) & at(Y, V8) & C \== V8 & place(V8) & at(B, V8) & A \== B & B \== D & B \== X & B \== Y & on(B, Y) & crate(B) & surface(B) & at(V10, V8) & A \== V10 & B \== V10 & D \== V10 & V10 \== X & V10 \== Y & clear(V10) & crate(V10) & at(V11, V8) & A \== V11 & B \== V11 & D \== V11 & V10 \== V11 & V11 \== X & V11 \== Y & on(V10, V11) & on(V11, B) & crate(V11) & surface(V11) & at(V9, V8) & A \== V9 & B \== V9 & D \== V9 & V10 \== V9 & V11 \== V9 & V9 \== X & available(V9) & hoist(V9) & at(Z, C) & A \== Z & V9 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V7) & surface(V7) <-
	lift(Z, A, X, C);
	load(Z, A, D, C);
	lift(Z, X, V7, C);
	load(Z, X, D, C);
	drive(D, C, V8);
	lift(V9, V10, V11, V8);
	load(V9, V10, D, V8);
	lift(V9, V11, B, V8);
	load(V9, V11, D, V8);
	lift(V9, B, Y, V8);
	load(V9, B, D, V8);
	unload(V9, X, D, V8);
	drop(V9, X, Y, V8).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, V12) & place(V12) & at(B, V12) & B \== X & B \== Y & truck(B) & at(V10, V12) & V10 \== X & available(V10) & hoist(V10) & at(Y, V7) & V12 \== V7 & place(V7) & at(A, V7) & A \== B & A \== V10 & A \== X & A \== Y & clear(A) & crate(A) & at(C, V7) & A \== C & B \== C & C \== X & C \== Y & on(C, Y) & crate(C) & surface(C) & at(D, V7) & A \== D & B \== D & C \== D & D \== V10 & D \== X & D \== Y & on(A, D) & crate(D) & surface(D) & at(V8, V7) & A \== V8 & D \== V8 & truck(V8) & at(V9, V7) & A \== V9 & B \== V9 & C \== V9 & D \== V9 & V9 \== X & V9 \== Y & on(D, V9) & on(V9, C) & crate(V9) & surface(V9) & at(Z, V7) & A \== Z & B \== Z & C \== Z & D \== Z & V10 \== Z & V9 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V11) & surface(V11) <-
	lift(Z, A, D, V7);
	load(Z, A, V8, V7);
	lift(Z, D, V9, V7);
	load(Z, D, V8, V7);
	lift(V10, X, V11, V12);
	load(V10, X, B, V12);
	drive(B, V12, V7);
	lift(Z, V9, C, V7);
	load(Z, V9, B, V7);
	lift(Z, C, Y, V7);
	load(Z, C, B, V7);
	unload(Z, X, B, V7);
	drop(Z, X, Y, V7).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, D) & place(D) & at(A, D) & A \== X & A \== Y & clear(A) & crate(A) & at(C, D) & A \== C & C \== X & C \== Y & on(A, C) & on(C, X) & crate(C) & surface(C) & at(V7, D) & A \== V7 & C \== V7 & V7 \== X & V7 \== Y & truck(V7) & at(Y, V9) & D \== V9 & place(V9) & at(B, V9) & A \== B & B \== C & B \== V7 & B \== X & B \== Y & on(B, Y) & crate(B) & surface(B) & at(V10, V9) & A \== V10 & B \== V10 & C \== V10 & V10 \== V7 & V10 \== X & available(V10) & hoist(V10) & at(V11, V9) & A \== V11 & B \== V11 & C \== V11 & V10 \== V11 & V11 \== V7 & V11 \== X & V11 \== Y & on(V11, B) & clear(V11) & crate(V11) & at(Z, D) & A \== Z & C \== Z & V10 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V8) & surface(V8) <-
	lift(Z, A, C, D);
	load(Z, A, V7, D);
	lift(Z, C, X, D);
	load(Z, C, V7, D);
	lift(Z, X, V8, D);
	load(Z, X, V7, D);
	drive(V7, D, V9);
	lift(V10, V11, B, V9);
	load(V10, V11, V7, V9);
	lift(V10, B, Y, V9);
	load(V10, B, V7, V9);
	unload(V10, X, V7, V9);
	drop(V10, X, Y, V9).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, C) & at(Y, C) & place(C) & at(B, C) & B \== X & truck(B) & at(D, C) & B \== D & D \== X & D \== Y & on(X, D) & crate(D) & surface(D) & at(V7, C) & B \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & crate(V7) & surface(V7) & at(V8, C) & B \== V8 & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & crate(V8) & surface(V8) & at(V9, C) & B \== V9 & D \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, Y) & crate(V9) & surface(V9) & at(Z, C) & D \== Z & V7 \== Z & V8 \== Z & V9 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== D & A \== V7 & A \== V8 & A \== V9 & A \== X & crate(A) <-
	load(Z, A, B, C);
	lift(Z, X, D, C);
	load(Z, X, B, C);
	lift(Z, D, V7, C);
	load(Z, D, B, C);
	lift(Z, V7, V8, C);
	load(Z, V7, B, C);
	lift(Z, V8, V9, C);
	load(Z, V8, B, C);
	lift(Z, V9, Y, C);
	load(Z, V9, B, C);
	unload(Z, X, B, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, D) & place(D) & at(A, D) & A \== X & A \== Y & on(A, X) & clear(A) & crate(A) & at(V7, D) & A \== V7 & V7 \== X & V7 \== Y & truck(V7) & at(Y, V11) & D \== V11 & place(V11) & at(C, V11) & A \== C & C \== V7 & C \== X & C \== Y & on(C, Y) & crate(C) & surface(C) & at(V10, V11) & A \== V10 & C \== V10 & V10 \== V7 & V10 \== X & V10 \== Y & on(V10, C) & crate(V10) & surface(V10) & at(V12, V11) & A \== V12 & truck(V12) & at(V8, V11) & A \== V8 & C \== V8 & V10 \== V8 & V7 \== V8 & V8 \== X & available(V8) & hoist(V8) & at(V9, V11) & A \== V9 & C \== V9 & V10 \== V9 & V12 \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V9, V10) & clear(V9) & crate(V9) & at(Z, D) & A \== Z & V8 \== Z & V9 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, B) & surface(B) <-
	lift(Z, A, X, D);
	load(Z, A, V7, D);
	lift(V8, V9, V10, V11);
	load(V8, V9, V12, V11);
	lift(Z, X, B, D);
	load(Z, X, V7, D);
	drive(V7, D, V11);
	lift(V8, V10, C, V11);
	load(V8, V10, V7, V11);
	lift(V8, C, Y, V11);
	load(V8, C, V7, V11);
	unload(V8, X, V7, V11);
	drop(V8, X, Y, V11).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, D) & at(Y, D) & place(D) & at(C, D) & truck(C) & at(V10, D) & C \== V10 & V10 \== X & V10 \== Y & crate(V10) & surface(V10) & at(V11, D) & C \== V11 & V10 \== V11 & V11 \== X & V11 \== Y & on(V10, V11) & on(V11, Y) & crate(V11) & surface(V11) & at(V7, D) & C \== V7 & V10 \== V7 & V11 \== V7 & V7 \== X & V7 \== Y & clear(V7) & crate(V7) & at(V8, D) & C \== V8 & V10 \== V8 & V11 \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & crate(V8) & surface(V8) & at(V9, D) & C \== V9 & V10 \== V9 & V11 \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, V10) & crate(V9) & surface(V9) & at(Z, D) & V10 \== Z & V11 \== Z & V7 \== Z & V8 \== Z & V9 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== V10 & A \== V11 & A \== V7 & A \== V8 & A \== V9 & A \== X & crate(A) & on(X, B) & surface(B) <-
	load(Z, A, C, D);
	lift(Z, V7, V8, D);
	load(Z, V7, C, D);
	lift(Z, V8, V9, D);
	load(Z, V8, C, D);
	lift(Z, V9, V10, D);
	load(Z, V9, C, D);
	lift(Z, V10, V11, D);
	load(Z, V10, C, D);
	lift(Z, V11, Y, D);
	load(Z, V11, C, D);
	lift(Z, X, B, D);
	drop(Z, X, Y, D).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, C) & place(C) & at(D, C) & D \== X & D \== Y & truck(D) & at(Y, V7) & C \== V7 & place(V7) & at(A, V7) & A \== D & A \== X & A \== Y & on(A, Y) & crate(A) & surface(A) & at(V10, V7) & A \== V10 & D \== V10 & V10 \== X & V10 \== Y & crate(V10) & surface(V10) & at(V11, V7) & A \== V11 & D \== V11 & V10 \== V11 & V11 \== X & V11 \== Y & on(V10, V11) & on(V11, A) & crate(V11) & surface(V11) & at(V8, V7) & A \== V8 & D \== V8 & V10 \== V8 & V11 \== V8 & V8 \== X & available(V8) & hoist(V8) & at(V9, V7) & A \== V9 & D \== V9 & V10 \== V9 & V11 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V9, V10) & clear(V9) & crate(V9) & at(Z, C) & V8 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, B) & surface(B) <-
	lift(Z, X, B, C);
	load(Z, X, D, C);
	drive(D, C, V7);
	lift(V8, V9, V10, V7);
	load(V8, V9, D, V7);
	lift(V8, V10, V11, V7);
	load(V8, V10, D, V7);
	lift(V8, V11, A, V7);
	load(V8, V11, D, V7);
	lift(V8, A, Y, V7);
	load(V8, A, D, V7);
	unload(V8, X, D, V7);
	drop(V8, X, Y, V7).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, D) & place(D) & at(A, D) & A \== X & A \== Y & clear(A) & crate(A) & at(C, D) & A \== C & C \== X & C \== Y & on(A, C) & crate(C) & surface(C) & at(V7, D) & A \== V7 & C \== V7 & V7 \== X & V7 \== Y & truck(V7) & at(V8, D) & A \== V8 & C \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(C, V8) & on(V8, X) & crate(V8) & surface(V8) & at(Y, V10) & D \== V10 & place(V10) & at(B, V10) & A \== B & B \== C & B \== V7 & B \== V8 & B \== X & B \== Y & on(B, Y) & clear(B) & crate(B) & at(V11, V10) & A \== V11 & B \== V11 & C \== V11 & V11 \== V7 & V11 \== V8 & V11 \== X & available(V11) & hoist(V11) & at(Z, D) & A \== Z & C \== Z & V11 \== Z & V8 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V9) & surface(V9) <-
	lift(Z, A, C, D);
	load(Z, A, V7, D);
	lift(Z, C, V8, D);
	load(Z, C, V7, D);
	lift(Z, V8, X, D);
	load(Z, V8, V7, D);
	lift(Z, X, V9, D);
	load(Z, X, V7, D);
	drive(V7, D, V10);
	lift(V11, B, Y, V10);
	load(V11, B, V7, V10);
	unload(V11, X, V7, V10);
	drop(V11, X, Y, V10).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, C) & place(C) & at(B, C) & in(X, B) & truck(B) & at(D, C) & B \== D & D \== X & D \== Y & clear(D) & crate(D) & at(V10, C) & B \== V10 & D \== V10 & V10 \== X & V10 \== Y & on(V10, Y) & crate(V10) & surface(V10) & at(V7, C) & B \== V7 & D \== V7 & V10 \== V7 & V7 \== X & V7 \== Y & on(D, V7) & crate(V7) & surface(V7) & at(V8, C) & B \== V8 & D \== V8 & V10 \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & crate(V8) & surface(V8) & at(V9, C) & B \== V9 & D \== V9 & V10 \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, V10) & crate(V9) & surface(V9) & at(Z, C) & D \== Z & V10 \== Z & V7 \== Z & V8 \== Z & V9 \== Z & hoist(Z) & lifting(Z, A) & A \== D & A \== V10 & A \== V7 & A \== V8 & A \== V9 & A \== X & crate(A) <-
	load(Z, A, B, C);
	lift(Z, D, V7, C);
	load(Z, D, B, C);
	lift(Z, V7, V8, C);
	load(Z, V7, B, C);
	lift(Z, V8, V9, C);
	load(Z, V8, B, C);
	lift(Z, V9, V10, C);
	load(Z, V9, B, C);
	lift(Z, V10, Y, C);
	load(Z, V10, B, C);
	unload(Z, X, B, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, B) & at(Y, B) & place(B) & at(A, B) & A \== X & A \== Y & on(A, X) & clear(A) & crate(A) & at(C, B) & A \== C & C \== X & truck(C) & at(D, B) & A \== D & C \== D & D \== X & D \== Y & on(X, D) & crate(D) & surface(D) & at(V7, B) & A \== V7 & C \== V7 & D \== V7 & V7 \== X & V7 \== Y & on(D, V7) & crate(V7) & surface(V7) & at(V8, B) & A \== V8 & C \== V8 & D \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & crate(V8) & surface(V8) & at(V9, B) & A \== V9 & C \== V9 & D \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, Y) & crate(V9) & surface(V9) & at(Z, B) & A \== Z & D \== Z & V7 \== Z & V8 \== Z & V9 \== Z & X \== Z & available(Z) & hoist(Z) <-
	lift(Z, A, X, B);
	load(Z, A, C, B);
	lift(Z, X, D, B);
	load(Z, X, C, B);
	lift(Z, D, V7, B);
	load(Z, D, C, B);
	lift(Z, V7, V8, B);
	load(Z, V7, C, B);
	lift(Z, V8, V9, B);
	load(Z, V8, C, B);
	lift(Z, V9, Y, B);
	load(Z, V9, C, B);
	unload(Z, X, C, B);
	drop(Z, X, Y, B).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, V7) & place(V7) & at(D, V7) & D \== X & D \== Y & truck(D) & at(V8, V7) & D \== V8 & V8 \== X & V8 \== Y & on(V8, X) & clear(V8) & crate(V8) & at(Y, V10) & V10 \== V7 & place(V10) & at(B, V10) & B \== D & B \== V8 & B \== X & B \== Y & crate(B) & surface(B) & at(C, V10) & B \== C & C \== D & C \== V8 & C \== X & C \== Y & on(B, C) & on(C, Y) & crate(C) & surface(C) & at(V11, V10) & B \== V11 & C \== V11 & D \== V11 & V11 \== V8 & V11 \== X & available(V11) & hoist(V11) & at(V12, V10) & B \== V12 & C \== V12 & D \== V12 & V11 \== V12 & V12 \== V8 & V12 \== X & V12 \== Y & on(V12, B) & clear(V12) & crate(V12) & at(Z, V7) & V11 \== Z & V8 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== V8 & A \== X & crate(A) & on(X, V9) & surface(V9) <-
	load(Z, A, D, V7);
	lift(Z, V8, X, V7);
	load(Z, V8, D, V7);
	lift(Z, X, V9, V7);
	load(Z, X, D, V7);
	drive(D, V7, V10);
	lift(V11, V12, B, V10);
	load(V11, V12, D, V10);
	lift(V11, B, C, V10);
	load(V11, B, D, V10);
	lift(V11, C, Y, V10);
	load(V11, C, D, V10);
	unload(V11, X, D, V10);
	drop(V11, X, Y, V10).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, C) & at(Y, C) & place(C) & at(A, C) & A \== X & A \== Y & on(A, X) & clear(A) & crate(A) & at(D, C) & A \== D & truck(D) & at(V10, C) & A \== V10 & D \== V10 & V10 \== X & V10 \== Y & crate(V10) & surface(V10) & at(V11, C) & A \== V11 & D \== V11 & V10 \== V11 & V11 \== X & V11 \== Y & on(V10, V11) & on(V11, Y) & crate(V11) & surface(V11) & at(V7, C) & A \== V7 & D \== V7 & V10 \== V7 & V11 \== V7 & V7 \== X & V7 \== Y & clear(V7) & crate(V7) & at(V8, C) & A \== V8 & D \== V8 & V10 \== V8 & V11 \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & crate(V8) & surface(V8) & at(V9, C) & A \== V9 & D \== V9 & V10 \== V9 & V11 \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, V10) & crate(V9) & surface(V9) & at(Z, C) & A \== Z & V10 \== Z & V11 \== Z & V7 \== Z & V8 \== Z & V9 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, B) & surface(B) <-
	lift(Z, A, X, C);
	load(Z, A, D, C);
	lift(Z, V7, V8, C);
	load(Z, V7, D, C);
	lift(Z, V8, V9, C);
	load(Z, V8, D, C);
	lift(Z, V9, V10, C);
	load(Z, V9, D, C);
	lift(Z, V10, V11, C);
	load(Z, V10, D, C);
	lift(Z, V11, Y, C);
	load(Z, V11, D, C);
	lift(Z, X, B, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, V7) & place(V7) & at(D, V7) & D \== X & D \== Y & truck(D) & at(V10, V7) & D \== V10 & V10 \== X & V10 \== Y & on(V10, X) & crate(V10) & surface(V10) & at(V8, V7) & D \== V8 & V10 \== V8 & V8 \== X & V8 \== Y & clear(V8) & crate(V8) & at(V9, V7) & D \== V9 & V10 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, V10) & crate(V9) & surface(V9) & at(Y, V12) & V12 \== V7 & place(V12) & at(B, V12) & B \== D & B \== V10 & B \== V8 & B \== V9 & B \== X & available(B) & hoist(B) & at(C, V12) & B \== C & C \== D & C \== V10 & C \== V8 & C \== V9 & C \== X & C \== Y & on(C, Y) & clear(C) & crate(C) & at(Z, V7) & B \== Z & V10 \== Z & V8 \== Z & V9 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== V10 & A \== V8 & A \== V9 & A \== X & crate(A) & on(X, V11) & surface(V11) <-
	load(Z, A, D, V7);
	lift(Z, V8, V9, V7);
	load(Z, V8, D, V7);
	lift(Z, V9, V10, V7);
	load(Z, V9, D, V7);
	lift(Z, V10, X, V7);
	load(Z, V10, D, V7);
	lift(Z, X, V11, V7);
	load(Z, X, D, V7);
	drive(D, V7, V12);
	lift(B, C, Y, V12);
	load(B, C, D, V12);
	unload(B, X, D, V12);
	drop(B, X, Y, V12).

+!on(X, Y) : X \== Y & clear(X) & crate(X) & surface(Y) & at(X, V7) & place(V7) & at(D, V7) & D \== X & D \== Y & truck(D) & at(Y, V9) & V7 \== V9 & place(V9) & at(B, V9) & B \== D & B \== X & B \== Y & crate(B) & surface(B) & at(C, V9) & B \== C & C \== D & C \== X & C \== Y & on(B, C) & on(C, Y) & crate(C) & surface(C) & at(V10, V9) & B \== V10 & C \== V10 & D \== V10 & V10 \== X & available(V10) & hoist(V10) & at(V11, V9) & B \== V11 & C \== V11 & D \== V11 & V10 \== V11 & V11 \== X & V11 \== Y & clear(V11) & crate(V11) & at(V12, V9) & B \== V12 & C \== V12 & D \== V12 & V10 \== V12 & V11 \== V12 & V12 \== X & V12 \== Y & on(V11, V12) & on(V12, B) & crate(V12) & surface(V12) & at(Z, V7) & V10 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== X & crate(A) & on(X, V8) & surface(V8) <-
	load(Z, A, D, V7);
	lift(Z, X, V8, V7);
	load(Z, X, D, V7);
	drive(D, V7, V9);
	lift(V10, V11, V12, V9);
	load(V10, V11, D, V9);
	lift(V10, V12, B, V9);
	load(V10, V12, D, V9);
	lift(V10, B, C, V9);
	load(V10, B, D, V9);
	lift(V10, C, Y, V9);
	load(V10, C, D, V9);
	unload(V10, X, D, V9);
	drop(V10, X, Y, V9).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, V8) & place(V8) & at(V7, V8) & V7 \== X & V7 \== Y & truck(V7) & at(V9, V8) & V7 \== V9 & V9 \== X & V9 \== Y & on(V9, X) & clear(V9) & crate(V9) & at(Y, V13) & V13 \== V8 & place(V13) & at(B, V13) & B \== V9 & truck(B) & at(D, V13) & D \== V7 & D \== V9 & D \== X & D \== Y & on(D, Y) & crate(D) & surface(D) & at(V10, V13) & D \== V10 & V10 \== V7 & V10 \== V9 & V10 \== X & available(V10) & hoist(V10) & at(V11, V13) & B \== V11 & D \== V11 & V10 \== V11 & V11 \== V7 & V11 \== V9 & V11 \== X & V11 \== Y & clear(V11) & crate(V11) & at(V12, V13) & D \== V12 & V10 \== V12 & V11 \== V12 & V12 \== V7 & V12 \== V9 & V12 \== X & V12 \== Y & on(V11, V12) & on(V12, D) & crate(V12) & surface(V12) & at(Z, V8) & V10 \== Z & V11 \== Z & V9 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== V9 & A \== X & crate(A) & on(X, C) & surface(C) <-
	load(Z, A, V7, V8);
	lift(Z, V9, X, V8);
	load(Z, V9, V7, V8);
	lift(V10, V11, V12, V13);
	load(V10, V11, B, V13);
	lift(Z, X, C, V8);
	load(Z, X, V7, V8);
	drive(V7, V8, V13);
	lift(V10, V12, D, V13);
	load(V10, V12, V7, V13);
	lift(V10, D, Y, V13);
	load(V10, D, V7, V13);
	unload(V10, X, V7, V13);
	drop(V10, X, Y, V13).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, D) & place(D) & at(A, D) & A \== X & on(A, X) & clear(A) & crate(A) & at(V7, D) & A \== V7 & V7 \== X & V7 \== Y & clear(V7) & surface(V7) & at(Y, V11) & D \== V11 & place(V11) & at(C, V11) & A \== C & C \== V7 & C \== X & C \== Y & on(C, Y) & crate(C) & surface(C) & at(V10, V11) & A \== V10 & C \== V10 & V10 \== V7 & V10 \== X & V10 \== Y & on(V10, C) & crate(V10) & surface(V10) & at(V12, V11) & C \== V12 & V10 \== V12 & V12 \== X & V12 \== Y & truck(V12) & at(V8, V11) & C \== V8 & V10 \== V8 & V12 \== V8 & V8 \== X & available(V8) & hoist(V8) & at(V9, V11) & A \== V9 & C \== V9 & V10 \== V9 & V12 \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V9, V10) & clear(V9) & crate(V9) & at(Z, D) & A \== Z & V12 \== Z & V8 \== Z & V9 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, B) & surface(B) <-
	lift(Z, A, X, D);
	drop(Z, A, V7, D);
	lift(V8, V9, V10, V11);
	load(V8, V9, V12, V11);
	lift(Z, X, B, D);
	drive(V12, V11, D);
	load(Z, X, V12, D);
	drive(V12, D, V11);
	lift(V8, V10, C, V11);
	load(V8, V10, V12, V11);
	lift(V8, C, Y, V11);
	load(V8, C, V12, V11);
	unload(V8, X, V12, V11);
	drop(V8, X, Y, V11).

+!on(X, Y) : crate(X) & surface(Y) & at(Y, C) & place(C) & at(A, C) & A \== X & A \== Y & clear(A) & crate(A) & at(B, C) & A \== B & B \== X & B \== Y & on(A, B) & crate(B) & surface(B) & at(D, C) & A \== D & B \== D & in(X, D) & truck(D) & at(V10, C) & A \== V10 & B \== V10 & D \== V10 & V10 \== X & V10 \== Y & on(V10, Y) & crate(V10) & surface(V10) & at(V7, C) & A \== V7 & B \== V7 & D \== V7 & V10 \== V7 & V7 \== X & V7 \== Y & on(B, V7) & crate(V7) & surface(V7) & at(V8, C) & A \== V8 & B \== V8 & D \== V8 & V10 \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & crate(V8) & surface(V8) & at(V9, C) & A \== V9 & B \== V9 & D \== V9 & V10 \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, V10) & crate(V9) & surface(V9) & at(Z, C) & A \== Z & B \== Z & V10 \== Z & V7 \== Z & V8 \== Z & V9 \== Z & available(Z) & hoist(Z) <-
	lift(Z, A, B, C);
	load(Z, A, D, C);
	lift(Z, B, V7, C);
	load(Z, B, D, C);
	lift(Z, V7, V8, C);
	load(Z, V7, D, C);
	lift(Z, V8, V9, C);
	load(Z, V8, D, C);
	lift(Z, V9, V10, C);
	load(Z, V9, D, C);
	lift(Z, V10, Y, C);
	load(Z, V10, D, C);
	unload(Z, X, D, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, D) & place(D) & at(A, D) & A \== X & A \== Y & on(A, X) & clear(A) & crate(A) & at(V7, D) & A \== V7 & V7 \== X & V7 \== Y & truck(V7) & at(Y, V9) & D \== V9 & place(V9) & at(B, V9) & A \== B & B \== V7 & B \== X & B \== Y & crate(B) & surface(B) & at(C, V9) & A \== C & B \== C & C \== V7 & C \== X & C \== Y & on(B, C) & on(C, Y) & crate(C) & surface(C) & at(V10, V9) & A \== V10 & B \== V10 & C \== V10 & V10 \== V7 & V10 \== X & available(V10) & hoist(V10) & at(V11, V9) & A \== V11 & B \== V11 & C \== V11 & V10 \== V11 & V11 \== V7 & V11 \== X & V11 \== Y & clear(V11) & crate(V11) & at(V12, V9) & A \== V12 & B \== V12 & C \== V12 & V10 \== V12 & V11 \== V12 & V12 \== V7 & V12 \== X & V12 \== Y & on(V11, V12) & on(V12, B) & crate(V12) & surface(V12) & at(Z, D) & A \== Z & V10 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V8) & surface(V8) <-
	lift(Z, A, X, D);
	load(Z, A, V7, D);
	lift(Z, X, V8, D);
	load(Z, X, V7, D);
	drive(V7, D, V9);
	lift(V10, V11, V12, V9);
	load(V10, V11, V7, V9);
	lift(V10, V12, B, V9);
	load(V10, V12, V7, V9);
	lift(V10, B, C, V9);
	load(V10, B, V7, V9);
	lift(V10, C, Y, V9);
	load(V10, C, V7, V9);
	unload(V10, X, V7, V9);
	drop(V10, X, Y, V9).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, C) & at(Y, C) & place(C) & at(B, C) & B \== X & truck(B) & at(D, C) & B \== D & D \== X & D \== Y & on(D, X) & clear(D) & crate(D) & at(V10, C) & B \== V10 & D \== V10 & V10 \== X & V10 \== Y & on(V10, Y) & crate(V10) & surface(V10) & at(V7, C) & B \== V7 & D \== V7 & V10 \== V7 & V7 \== X & V7 \== Y & on(X, V7) & crate(V7) & surface(V7) & at(V8, C) & B \== V8 & D \== V8 & V10 \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & crate(V8) & surface(V8) & at(V9, C) & B \== V9 & D \== V9 & V10 \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, V10) & crate(V9) & surface(V9) & at(Z, C) & D \== Z & V10 \== Z & V7 \== Z & V8 \== Z & V9 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== D & A \== V10 & A \== V7 & A \== V8 & A \== V9 & A \== X & crate(A) <-
	load(Z, A, B, C);
	lift(Z, D, X, C);
	load(Z, D, B, C);
	lift(Z, X, V7, C);
	load(Z, X, B, C);
	lift(Z, V7, V8, C);
	load(Z, V7, B, C);
	lift(Z, V8, V9, C);
	load(Z, V8, B, C);
	lift(Z, V9, V10, C);
	load(Z, V9, B, C);
	lift(Z, V10, Y, C);
	load(Z, V10, B, C);
	unload(Z, X, B, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, V8) & place(V8) & at(A, V8) & A \== X & A \== Y & clear(A) & crate(A) & at(V7, V8) & A \== V7 & V7 \== X & V7 \== Y & on(A, V7) & on(V7, X) & crate(V7) & surface(V7) & at(V9, V8) & A \== V9 & V7 \== V9 & V9 \== X & V9 \== Y & truck(V9) & at(Y, V13) & V13 \== V8 & place(V13) & at(B, V13) & A \== B & B \== V7 & truck(B) & at(D, V13) & A \== D & D \== V7 & D \== V9 & D \== X & D \== Y & on(D, Y) & crate(D) & surface(D) & at(V10, V13) & A \== V10 & D \== V10 & V10 \== V7 & V10 \== V9 & V10 \== X & available(V10) & hoist(V10) & at(V11, V13) & A \== V11 & B \== V11 & D \== V11 & V10 \== V11 & V11 \== V7 & V11 \== V9 & V11 \== X & V11 \== Y & clear(V11) & crate(V11) & at(V12, V13) & A \== V12 & D \== V12 & V10 \== V12 & V11 \== V12 & V12 \== V7 & V12 \== V9 & V12 \== X & V12 \== Y & on(V11, V12) & on(V12, D) & crate(V12) & surface(V12) & at(Z, V8) & A \== Z & V10 \== Z & V11 \== Z & V7 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, C) & surface(C) <-
	lift(Z, A, V7, V8);
	load(Z, A, V9, V8);
	lift(Z, V7, X, V8);
	load(Z, V7, V9, V8);
	lift(V10, V11, V12, V13);
	load(V10, V11, B, V13);
	lift(Z, X, C, V8);
	load(Z, X, V9, V8);
	drive(V9, V8, V13);
	lift(V10, V12, D, V13);
	load(V10, V12, V9, V13);
	lift(V10, D, Y, V13);
	load(V10, D, V9, V13);
	unload(V10, X, V9, V13);
	drop(V10, X, Y, V13).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, V7) & place(V7) & at(A, V7) & A \== X & A \== Y & clear(A) & crate(A) & at(D, V7) & A \== D & D \== X & D \== Y & on(A, D) & on(D, X) & crate(D) & surface(D) & at(V8, V7) & A \== V8 & D \== V8 & V8 \== X & V8 \== Y & truck(V8) & at(Y, V10) & V10 \== V7 & place(V10) & at(B, V10) & A \== B & B \== D & B \== V8 & B \== X & B \== Y & crate(B) & surface(B) & at(C, V10) & A \== C & B \== C & C \== D & C \== V8 & C \== X & C \== Y & on(B, C) & on(C, Y) & crate(C) & surface(C) & at(V11, V10) & A \== V11 & B \== V11 & C \== V11 & D \== V11 & V11 \== V8 & V11 \== X & available(V11) & hoist(V11) & at(V12, V10) & A \== V12 & B \== V12 & C \== V12 & D \== V12 & V11 \== V12 & V12 \== V8 & V12 \== X & V12 \== Y & on(V12, B) & clear(V12) & crate(V12) & at(Z, V7) & A \== Z & D \== Z & V11 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V9) & surface(V9) <-
	lift(Z, A, D, V7);
	load(Z, A, V8, V7);
	lift(Z, D, X, V7);
	load(Z, D, V8, V7);
	lift(Z, X, V9, V7);
	load(Z, X, V8, V7);
	drive(V8, V7, V10);
	lift(V11, V12, B, V10);
	load(V11, V12, V8, V10);
	lift(V11, B, C, V10);
	load(V11, B, V8, V10);
	lift(V11, C, Y, V10);
	load(V11, C, V8, V10);
	unload(V11, X, V8, V10);
	drop(V11, X, Y, V10).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, V7) & place(V7) & at(A, V7) & A \== X & A \== Y & clear(A) & crate(A) & at(D, V7) & A \== D & D \== X & D \== Y & on(A, D) & crate(D) & surface(D) & at(V10, V7) & A \== V10 & D \== V10 & V10 \== X & V10 \== Y & on(V10, X) & crate(V10) & surface(V10) & at(V8, V7) & A \== V8 & D \== V8 & V10 \== V8 & V8 \== X & V8 \== Y & truck(V8) & at(V9, V7) & A \== V9 & D \== V9 & V10 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(D, V9) & on(V9, V10) & crate(V9) & surface(V9) & at(Y, V12) & V12 \== V7 & place(V12) & at(B, V12) & A \== B & B \== D & B \== V10 & B \== V8 & B \== V9 & B \== X & available(B) & hoist(B) & at(C, V12) & A \== C & B \== C & C \== D & C \== V10 & C \== V8 & C \== V9 & C \== X & C \== Y & on(C, Y) & clear(C) & crate(C) & at(Z, V7) & A \== Z & B \== Z & D \== Z & V10 \== Z & V9 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V11) & surface(V11) <-
	lift(Z, A, D, V7);
	load(Z, A, V8, V7);
	lift(Z, D, V9, V7);
	load(Z, D, V8, V7);
	lift(Z, V9, V10, V7);
	load(Z, V9, V8, V7);
	lift(Z, V10, X, V7);
	load(Z, V10, V8, V7);
	lift(Z, X, V11, V7);
	load(Z, X, V8, V7);
	drive(V8, V7, V12);
	lift(B, C, Y, V12);
	load(B, C, V8, V12);
	unload(B, X, V8, V12);
	drop(B, X, Y, V12).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, C) & at(Y, C) & place(C) & at(A, C) & A \== X & A \== Y & clear(A) & crate(A) & at(B, C) & A \== B & B \== X & B \== Y & on(A, B) & on(B, X) & crate(B) & surface(B) & at(D, C) & A \== D & B \== D & D \== X & truck(D) & at(V10, C) & A \== V10 & B \== V10 & D \== V10 & V10 \== X & V10 \== Y & on(V10, Y) & crate(V10) & surface(V10) & at(V7, C) & A \== V7 & B \== V7 & D \== V7 & V10 \== V7 & V7 \== X & V7 \== Y & on(X, V7) & crate(V7) & surface(V7) & at(V8, C) & A \== V8 & B \== V8 & D \== V8 & V10 \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & crate(V8) & surface(V8) & at(V9, C) & A \== V9 & B \== V9 & D \== V9 & V10 \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, V10) & crate(V9) & surface(V9) & at(Z, C) & A \== Z & B \== Z & V10 \== Z & V7 \== Z & V8 \== Z & V9 \== Z & X \== Z & available(Z) & hoist(Z) <-
	lift(Z, A, B, C);
	load(Z, A, D, C);
	lift(Z, B, X, C);
	load(Z, B, D, C);
	lift(Z, X, V7, C);
	load(Z, X, D, C);
	lift(Z, V7, V8, C);
	load(Z, V7, D, C);
	lift(Z, V8, V9, C);
	load(Z, V8, D, C);
	lift(Z, V9, V10, C);
	load(Z, V9, D, C);
	lift(Z, V10, Y, C);
	load(Z, V10, D, C);
	unload(Z, X, D, C);
	drop(Z, X, Y, C).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, V8) & place(V8) & at(V10, V8) & V10 \== X & V10 \== Y & on(V10, X) & crate(V10) & surface(V10) & at(V7, V8) & V10 \== V7 & V7 \== X & V7 \== Y & truck(V7) & at(V9, V8) & V10 \== V9 & V7 \== V9 & V9 \== X & V9 \== Y & on(V9, V10) & clear(V9) & crate(V9) & at(Y, V12) & V12 \== V8 & place(V12) & at(B, V12) & B \== V10 & B \== V7 & B \== V9 & B \== X & B \== Y & clear(B) & crate(B) & at(C, V12) & B \== C & C \== V10 & C \== V7 & C \== V9 & C \== X & C \== Y & on(B, C) & crate(C) & surface(C) & at(D, V12) & B \== D & C \== D & D \== V10 & D \== V7 & D \== V9 & D \== X & D \== Y & on(C, D) & on(D, Y) & crate(D) & surface(D) & at(V13, V12) & B \== V13 & C \== V13 & D \== V13 & V10 \== V13 & V13 \== V7 & V13 \== V9 & V13 \== X & available(V13) & hoist(V13) & at(Z, V8) & V10 \== Z & V13 \== Z & V9 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== V10 & A \== V9 & A \== X & crate(A) & on(X, V11) & surface(V11) <-
	load(Z, A, V7, V8);
	lift(Z, V9, V10, V8);
	load(Z, V9, V7, V8);
	lift(Z, V10, X, V8);
	load(Z, V10, V7, V8);
	lift(Z, X, V11, V8);
	load(Z, X, V7, V8);
	drive(V7, V8, V12);
	lift(V13, B, C, V12);
	load(V13, B, V7, V12);
	lift(V13, C, D, V12);
	load(V13, C, V7, V12);
	lift(V13, D, Y, V12);
	load(V13, D, V7, V12);
	unload(V13, X, V7, V12);
	drop(V13, X, Y, V12).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, V8) & place(V8) & at(V7, V8) & V7 \== X & V7 \== Y & truck(V7) & at(V9, V8) & V7 \== V9 & V9 \== X & V9 \== Y & on(V9, X) & clear(V9) & crate(V9) & at(Y, V11) & V11 \== V8 & place(V11) & at(B, V11) & B \== V7 & B \== V9 & B \== X & B \== Y & crate(B) & surface(B) & at(C, V11) & B \== C & C \== V7 & C \== V9 & C \== X & C \== Y & on(B, C) & crate(C) & surface(C) & at(D, V11) & B \== D & C \== D & D \== V7 & D \== V9 & D \== X & D \== Y & on(C, D) & on(D, Y) & crate(D) & surface(D) & at(V12, V11) & B \== V12 & C \== V12 & D \== V12 & V12 \== V7 & V12 \== V9 & V12 \== X & available(V12) & hoist(V12) & at(V13, V11) & B \== V13 & C \== V13 & D \== V13 & V12 \== V13 & V13 \== V7 & V13 \== V9 & V13 \== X & V13 \== Y & on(V13, B) & clear(V13) & crate(V13) & at(Z, V8) & V12 \== Z & V9 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== V9 & A \== X & crate(A) & on(X, V10) & surface(V10) <-
	load(Z, A, V7, V8);
	lift(Z, V9, X, V8);
	load(Z, V9, V7, V8);
	lift(Z, X, V10, V8);
	load(Z, X, V7, V8);
	drive(V7, V8, V11);
	lift(V12, V13, B, V11);
	load(V12, V13, V7, V11);
	lift(V12, B, C, V11);
	load(V12, B, V7, V11);
	lift(V12, C, D, V11);
	load(V12, C, V7, V11);
	lift(V12, D, Y, V11);
	load(V12, D, V7, V11);
	unload(V12, X, V7, V11);
	drop(V12, X, Y, V11).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, V8) & place(V8) & at(V10, V8) & V10 \== X & V10 \== Y & clear(V10) & crate(V10) & at(V11, V8) & V10 \== V11 & V11 \== X & V11 \== Y & on(V10, V11) & on(V11, X) & crate(V11) & surface(V11) & at(V9, V8) & V10 \== V9 & V11 \== V9 & V9 \== X & available(V9) & hoist(V9) & at(Y, B) & B \== V8 & place(B) & at(C, B) & C \== V10 & C \== V11 & truck(C) & at(V12, B) & V10 \== V12 & V11 \== V12 & V12 \== V9 & V12 \== X & available(V12) & hoist(V12) & at(V13, B) & C \== V13 & V10 \== V13 & V11 \== V13 & V12 \== V13 & V13 \== V9 & V13 \== X & V13 \== Y & clear(V13) & crate(V13) & at(V14, B) & V10 \== V14 & V11 \== V14 & V12 \== V14 & V13 \== V14 & V14 \== X & V14 \== Y & on(V13, V14) & crate(V14) & surface(V14) & at(V7, B) & V10 \== V7 & V11 \== V7 & V12 \== V7 & V13 \== V7 & V14 \== V7 & V7 \== X & V7 \== Y & on(V14, V7) & on(V7, Y) & crate(V7) & surface(V7) & on(X, D) & surface(D) & place(A) & A \== B & A \== V8 & at(Z, A) & C \== Z & V10 \== Z & V11 \== Z & V12 \== Z & V13 \== Z & V14 \== Z & V7 \== Z & V9 \== Z & X \== Z & Y \== Z & truck(Z) <-
	drive(Z, A, V8);
	lift(V9, V10, V11, V8);
	load(V9, V10, Z, V8);
	lift(V9, V11, X, V8);
	load(V9, V11, Z, V8);
	lift(V12, V13, V14, B);
	load(V12, V13, C, B);
	lift(V9, X, D, V8);
	load(V9, X, Z, V8);
	drive(Z, V8, B);
	lift(V12, V14, V7, B);
	load(V12, V14, Z, B);
	lift(V12, V7, Y, B);
	load(V12, V7, Z, B);
	unload(V12, X, Z, B);
	drop(V12, X, Y, B).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, D) & at(Y, D) & place(D) & at(B, D) & B \== X & B \== Y & on(B, Y) & crate(B) & surface(B) & at(C, D) & B \== C & C \== X & truck(C) & at(V10, D) & B \== V10 & C \== V10 & V10 \== X & V10 \== Y & crate(V10) & surface(V10) & at(V11, D) & B \== V11 & C \== V11 & V10 \== V11 & V11 \== X & V11 \== Y & on(V10, V11) & on(V11, B) & crate(V11) & surface(V11) & at(V7, D) & B \== V7 & C \== V7 & V10 \== V7 & V11 \== V7 & V7 \== X & V7 \== Y & clear(V7) & crate(V7) & at(V8, D) & B \== V8 & C \== V8 & V10 \== V8 & V11 \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(V7, V8) & on(V8, X) & crate(V8) & surface(V8) & at(V9, D) & B \== V9 & C \== V9 & V10 \== V9 & V11 \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V9, V10) & on(X, V9) & crate(V9) & surface(V9) & at(Z, D) & B \== Z & V10 \== Z & V11 \== Z & V7 \== Z & V8 \== Z & V9 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== B & A \== V10 & A \== V11 & A \== V7 & A \== V8 & A \== V9 & A \== X & crate(A) <-
	load(Z, A, C, D);
	lift(Z, V7, V8, D);
	load(Z, V7, C, D);
	lift(Z, V8, X, D);
	load(Z, V8, C, D);
	lift(Z, X, V9, D);
	load(Z, X, C, D);
	lift(Z, V9, V10, D);
	load(Z, V9, C, D);
	lift(Z, V10, V11, D);
	load(Z, V10, C, D);
	lift(Z, V11, B, D);
	load(Z, V11, C, D);
	lift(Z, B, Y, D);
	load(Z, B, C, D);
	unload(Z, X, C, D);
	drop(Z, X, Y, D).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, V8) & place(V8) & at(A, V8) & A \== X & A \== Y & clear(A) & crate(A) & at(V7, V8) & A \== V7 & V7 \== X & V7 \== Y & on(A, V7) & on(V7, X) & crate(V7) & surface(V7) & at(V9, V8) & A \== V9 & V7 \== V9 & V9 \== X & V9 \== Y & truck(V9) & at(Y, V11) & V11 \== V8 & place(V11) & at(B, V11) & A \== B & B \== V7 & B \== V9 & B \== X & B \== Y & crate(B) & surface(B) & at(C, V11) & A \== C & B \== C & C \== V7 & C \== V9 & C \== X & C \== Y & on(B, C) & crate(C) & surface(C) & at(D, V11) & A \== D & B \== D & C \== D & D \== V7 & D \== V9 & D \== X & D \== Y & on(C, D) & on(D, Y) & crate(D) & surface(D) & at(V12, V11) & A \== V12 & B \== V12 & C \== V12 & D \== V12 & V12 \== V7 & V12 \== V9 & V12 \== X & available(V12) & hoist(V12) & at(V13, V11) & A \== V13 & B \== V13 & C \== V13 & D \== V13 & V12 \== V13 & V13 \== V7 & V13 \== V9 & V13 \== X & V13 \== Y & on(V13, B) & clear(V13) & crate(V13) & at(Z, V8) & A \== Z & V12 \== Z & V7 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V10) & surface(V10) <-
	lift(Z, A, V7, V8);
	load(Z, A, V9, V8);
	lift(Z, V7, X, V8);
	load(Z, V7, V9, V8);
	lift(Z, X, V10, V8);
	load(Z, X, V9, V8);
	drive(V9, V8, V11);
	lift(V12, V13, B, V11);
	load(V12, V13, V9, V11);
	lift(V12, B, C, V11);
	load(V12, B, V9, V11);
	lift(V12, C, D, V11);
	load(V12, C, V9, V11);
	lift(V12, D, Y, V11);
	load(V12, D, V9, V11);
	unload(V12, X, V9, V11);
	drop(V12, X, Y, V11).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, V12) & place(V12) & at(V13, V12) & V13 \== X & available(V13) & hoist(V13) & at(V14, V12) & V13 \== V14 & V14 \== X & V14 \== Y & clear(V14) & crate(V14) & at(V15, V12) & V13 \== V15 & V14 \== V15 & V15 \== X & V15 \== Y & on(V14, V15) & on(V15, X) & crate(V15) & surface(V15) & at(Y, V9) & V12 \== V9 & place(V9) & at(B, V9) & B \== V13 & B \== V14 & B \== V15 & B \== X & B \== Y & clear(B) & crate(B) & at(C, V9) & B \== C & C \== V14 & C \== V15 & C \== X & C \== Y & on(B, C) & crate(C) & surface(C) & at(V7, V9) & B \== V7 & C \== V7 & V14 \== V7 & V15 \== V7 & V7 \== X & V7 \== Y & on(C, V7) & on(V7, Y) & crate(V7) & surface(V7) & at(V8, V9) & B \== V8 & V14 \== V8 & V15 \== V8 & truck(V8) & at(Z, V9) & B \== Z & C \== Z & V13 \== Z & V14 \== Z & V15 \== Z & V7 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== B & A \== C & A \== V7 & A \== X & crate(A) & on(X, D) & surface(D) & place(V11) & V11 \== V12 & V11 \== V9 & at(V10, V11) & B \== V10 & C \== V10 & V10 \== V13 & V10 \== V14 & V10 \== V15 & V10 \== V7 & V10 \== V8 & V10 \== X & V10 \== Y & V10 \== Z & truck(V10) <-
	load(Z, A, V8, V9);
	drive(V10, V11, V12);
	lift(V13, V14, V15, V12);
	load(V13, V14, V10, V12);
	lift(V13, V15, X, V12);
	load(V13, V15, V10, V12);
	lift(Z, B, C, V9);
	load(Z, B, V8, V9);
	lift(V13, X, D, V12);
	load(V13, X, V10, V12);
	drive(V10, V12, V9);
	lift(Z, C, V7, V9);
	load(Z, C, V10, V9);
	lift(Z, V7, Y, V9);
	load(Z, V7, V10, V9);
	unload(Z, X, V10, V9);
	drop(Z, X, Y, V9).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, V8) & place(V8) & at(A, V8) & A \== X & A \== Y & clear(A) & crate(A) & at(V10, V8) & A \== V10 & V10 \== X & V10 \== Y & on(V10, X) & crate(V10) & surface(V10) & at(V7, V8) & A \== V7 & V10 \== V7 & V7 \== X & V7 \== Y & on(A, V7) & on(V7, V10) & crate(V7) & surface(V7) & at(V9, V8) & A \== V9 & V10 \== V9 & V7 \== V9 & V9 \== X & V9 \== Y & truck(V9) & at(Y, V12) & V12 \== V8 & place(V12) & at(B, V12) & A \== B & B \== V10 & B \== V7 & B \== V9 & B \== X & B \== Y & clear(B) & crate(B) & at(C, V12) & A \== C & B \== C & C \== V10 & C \== V7 & C \== V9 & C \== X & C \== Y & on(B, C) & crate(C) & surface(C) & at(D, V12) & A \== D & B \== D & C \== D & D \== V10 & D \== V7 & D \== V9 & D \== X & D \== Y & on(C, D) & on(D, Y) & crate(D) & surface(D) & at(V13, V12) & A \== V13 & B \== V13 & C \== V13 & D \== V13 & V10 \== V13 & V13 \== V7 & V13 \== V9 & V13 \== X & available(V13) & hoist(V13) & at(Z, V8) & A \== Z & V10 \== Z & V13 \== Z & V7 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V11) & surface(V11) <-
	lift(Z, A, V7, V8);
	load(Z, A, V9, V8);
	lift(Z, V7, V10, V8);
	load(Z, V7, V9, V8);
	lift(Z, V10, X, V8);
	load(Z, V10, V9, V8);
	lift(Z, X, V11, V8);
	load(Z, X, V9, V8);
	drive(V9, V8, V12);
	lift(V13, B, C, V12);
	load(V13, B, V9, V12);
	lift(V13, C, D, V12);
	load(V13, C, V9, V12);
	lift(V13, D, Y, V12);
	load(V13, D, V9, V12);
	unload(V13, X, V9, V12);
	drop(V13, X, Y, V12).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, D) & at(Y, D) & place(D) & at(A, D) & A \== X & A \== Y & clear(A) & crate(A) & at(B, D) & A \== B & B \== X & B \== Y & on(B, Y) & crate(B) & surface(B) & at(C, D) & A \== C & B \== C & C \== X & C \== Y & on(A, C) & crate(C) & surface(C) & at(V10, D) & A \== V10 & B \== V10 & C \== V10 & V10 \== X & V10 \== Y & crate(V10) & surface(V10) & at(V11, D) & A \== V11 & B \== V11 & C \== V11 & V10 \== V11 & V11 \== X & V11 \== Y & on(V10, V11) & on(V11, B) & crate(V11) & surface(V11) & at(V7, D) & A \== V7 & B \== V7 & C \== V7 & V10 \== V7 & V11 \== V7 & V7 \== X & truck(V7) & at(V8, D) & A \== V8 & B \== V8 & C \== V8 & V10 \== V8 & V11 \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(C, V8) & on(V8, X) & crate(V8) & surface(V8) & at(V9, D) & A \== V9 & B \== V9 & C \== V9 & V10 \== V9 & V11 \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V9, V10) & on(X, V9) & crate(V9) & surface(V9) & at(Z, D) & A \== Z & B \== Z & C \== Z & V10 \== Z & V11 \== Z & V8 \== Z & V9 \== Z & X \== Z & available(Z) & hoist(Z) <-
	lift(Z, A, C, D);
	load(Z, A, V7, D);
	lift(Z, C, V8, D);
	load(Z, C, V7, D);
	lift(Z, V8, X, D);
	load(Z, V8, V7, D);
	lift(Z, X, V9, D);
	load(Z, X, V7, D);
	lift(Z, V9, V10, D);
	load(Z, V9, V7, D);
	lift(Z, V10, V11, D);
	load(Z, V10, V7, D);
	lift(Z, V11, B, D);
	load(Z, V11, V7, D);
	lift(Z, B, Y, D);
	load(Z, B, V7, D);
	unload(Z, X, V7, D);
	drop(Z, X, Y, D).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, V9) & place(V9) & at(V10, V9) & V10 \== X & V10 \== Y & clear(V10) & crate(V10) & at(V11, V9) & V10 \== V11 & V11 \== X & V11 \== Y & on(V10, V11) & on(V11, X) & crate(V11) & surface(V11) & at(V8, V9) & V10 \== V8 & V11 \== V8 & V8 \== X & V8 \== Y & truck(V8) & at(Y, V13) & V13 \== V9 & place(V13) & at(B, V13) & B \== V10 & B \== V11 & B \== V8 & B \== X & B \== Y & clear(B) & crate(B) & at(C, V13) & B \== C & C \== V10 & C \== V11 & C \== V8 & C \== X & C \== Y & on(B, C) & crate(C) & surface(C) & at(D, V13) & B \== D & C \== D & D \== V10 & D \== V11 & D \== V8 & D \== X & D \== Y & on(C, D) & crate(D) & surface(D) & at(V14, V13) & B \== V14 & C \== V14 & D \== V14 & V10 \== V14 & V11 \== V14 & V14 \== V8 & V14 \== X & available(V14) & hoist(V14) & at(V7, V13) & B \== V7 & C \== V7 & D \== V7 & V10 \== V7 & V11 \== V7 & V14 \== V7 & V7 \== V8 & V7 \== X & V7 \== Y & on(D, V7) & on(V7, Y) & crate(V7) & surface(V7) & at(Z, V9) & V10 \== Z & V11 \== Z & V14 \== Z & X \== Z & hoist(Z) & lifting(Z, A) & A \== V10 & A \== V11 & A \== X & crate(A) & on(X, V12) & surface(V12) <-
	load(Z, A, V8, V9);
	lift(Z, V10, V11, V9);
	load(Z, V10, V8, V9);
	lift(Z, V11, X, V9);
	load(Z, V11, V8, V9);
	lift(Z, X, V12, V9);
	load(Z, X, V8, V9);
	drive(V8, V9, V13);
	lift(V14, B, C, V13);
	load(V14, B, V8, V13);
	lift(V14, C, D, V13);
	load(V14, C, V8, V13);
	lift(V14, D, V7, V13);
	load(V14, D, V8, V13);
	lift(V14, V7, Y, V13);
	load(V14, V7, V8, V13);
	unload(V14, X, V8, V13);
	drop(V14, X, Y, V13).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, V13) & place(V13) & at(B, V13) & B \== X & B \== Y & on(B, X) & crate(B) & surface(B) & at(V14, V13) & B \== V14 & V14 \== X & available(V14) & hoist(V14) & at(V15, V13) & B \== V15 & V14 \== V15 & V15 \== X & V15 \== Y & on(V15, B) & clear(V15) & crate(V15) & at(Y, V9) & V13 \== V9 & place(V9) & at(A, V9) & A \== B & A \== V14 & A \== V15 & A \== X & A \== Y & clear(A) & crate(A) & at(C, V9) & A \== C & B \== C & C \== V15 & C \== X & C \== Y & crate(C) & surface(C) & at(V10, V9) & A \== V10 & B \== V10 & V10 \== V15 & truck(V10) & at(V7, V9) & A \== V7 & B \== V7 & C \== V7 & V15 \== V7 & V7 \== X & V7 \== Y & on(C, V7) & on(V7, Y) & crate(V7) & surface(V7) & at(V8, V9) & A \== V8 & B \== V8 & C \== V8 & V10 \== V8 & V14 \== V8 & V15 \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & on(A, V8) & on(V8, C) & crate(V8) & surface(V8) & at(Z, V9) & A \== Z & B \== Z & C \== Z & V14 \== Z & V15 \== Z & V7 \== Z & V8 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, D) & surface(D) & place(V12) & V12 \== V13 & V12 \== V9 & at(V11, V12) & A \== V11 & B \== V11 & C \== V11 & V10 \== V11 & V11 \== V14 & V11 \== V15 & V11 \== V7 & V11 \== V8 & V11 \== X & V11 \== Y & V11 \== Z & truck(V11) <-
	lift(Z, A, V8, V9);
	load(Z, A, V10, V9);
	drive(V11, V12, V13);
	lift(V14, V15, B, V13);
	load(V14, V15, V11, V13);
	lift(V14, B, X, V13);
	load(V14, B, V11, V13);
	lift(Z, V8, C, V9);
	load(Z, V8, V10, V9);
	lift(V14, X, D, V13);
	load(V14, X, V11, V13);
	drive(V11, V13, V9);
	lift(Z, C, V7, V9);
	load(Z, C, V11, V9);
	lift(Z, V7, Y, V9);
	load(Z, V7, V11, V9);
	unload(Z, X, V11, V9);
	drop(Z, X, Y, V9).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, D) & at(Y, D) & place(D) & at(B, D) & B \== X & B \== Y & crate(B) & surface(B) & at(C, D) & B \== C & C \== X & C \== Y & on(B, C) & on(C, Y) & crate(C) & surface(C) & at(V10, D) & B \== V10 & C \== V10 & V10 \== X & V10 \== Y & on(V10, X) & crate(V10) & surface(V10) & at(V11, D) & B \== V11 & C \== V11 & V10 \== V11 & V11 \== X & V11 \== Y & on(X, V11) & crate(V11) & surface(V11) & at(V12, D) & B \== V12 & C \== V12 & V10 \== V12 & V11 \== V12 & V12 \== X & V12 \== Y & on(V11, V12) & on(V12, B) & crate(V12) & surface(V12) & at(V7, D) & B \== V7 & C \== V7 & V10 \== V7 & V11 \== V7 & V12 \== V7 & V7 \== X & available(V7) & hoist(V7) & at(V8, D) & B \== V8 & C \== V8 & V10 \== V8 & V11 \== V8 & V12 \== V8 & V7 \== V8 & V8 \== X & V8 \== Y & clear(V8) & crate(V8) & at(V9, D) & B \== V9 & C \== V9 & V10 \== V9 & V11 \== V9 & V12 \== V9 & V7 \== V9 & V8 \== V9 & V9 \== X & V9 \== Y & on(V8, V9) & on(V9, V10) & crate(V9) & surface(V9) & place(A) & A \== D & at(Z, A) & B \== Z & C \== Z & V10 \== Z & V11 \== Z & V12 \== Z & V7 \== Z & V8 \== Z & V9 \== Z & X \== Z & Y \== Z & truck(Z) <-
	drive(Z, A, D);
	lift(V7, V8, V9, D);
	load(V7, V8, Z, D);
	lift(V7, V9, V10, D);
	load(V7, V9, Z, D);
	lift(V7, V10, X, D);
	load(V7, V10, Z, D);
	lift(V7, X, V11, D);
	load(V7, X, Z, D);
	lift(V7, V11, V12, D);
	load(V7, V11, Z, D);
	lift(V7, V12, B, D);
	load(V7, V12, Z, D);
	lift(V7, B, C, D);
	load(V7, B, Z, D);
	lift(V7, C, Y, D);
	load(V7, C, Z, D);
	unload(V7, X, Z, D);
	drop(V7, X, Y, D).

+!on(X, Y) : X \== Y & crate(X) & surface(X) & surface(Y) & at(X, V9) & place(V9) & at(A, V9) & A \== X & A \== Y & clear(A) & crate(A) & at(V10, V9) & A \== V10 & V10 \== X & V10 \== Y & truck(V10) & at(V11, V9) & A \== V11 & V10 \== V11 & V11 \== X & V11 \== Y & on(V11, X) & crate(V11) & surface(V11) & at(V8, V9) & A \== V8 & V10 \== V8 & V11 \== V8 & V8 \== X & V8 \== Y & on(A, V8) & on(V8, V11) & crate(V8) & surface(V8) & at(Y, V13) & V13 \== V9 & place(V13) & at(B, V13) & A \== B & B \== V10 & B \== V11 & B \== V8 & B \== X & B \== Y & clear(B) & crate(B) & at(C, V13) & A \== C & B \== C & C \== V10 & C \== V11 & C \== V8 & C \== X & C \== Y & on(B, C) & crate(C) & surface(C) & at(D, V13) & A \== D & B \== D & C \== D & D \== V10 & D \== V11 & D \== V8 & D \== X & D \== Y & on(C, D) & crate(D) & surface(D) & at(V14, V13) & A \== V14 & B \== V14 & C \== V14 & D \== V14 & V10 \== V14 & V11 \== V14 & V14 \== V8 & V14 \== X & available(V14) & hoist(V14) & at(V7, V13) & A \== V7 & B \== V7 & C \== V7 & D \== V7 & V10 \== V7 & V11 \== V7 & V14 \== V7 & V7 \== V8 & V7 \== X & V7 \== Y & on(D, V7) & on(V7, Y) & crate(V7) & surface(V7) & at(Z, V9) & A \== Z & V11 \== Z & V14 \== Z & V8 \== Z & X \== Z & available(Z) & hoist(Z) & on(X, V12) & surface(V12) <-
	lift(Z, A, V8, V9);
	load(Z, A, V10, V9);
	lift(Z, V8, V11, V9);
	load(Z, V8, V10, V9);
	lift(Z, V11, X, V9);
	load(Z, V11, V10, V9);
	lift(Z, X, V12, V9);
	load(Z, X, V10, V9);
	drive(V10, V9, V13);
	lift(V14, B, C, V13);
	load(V14, B, V10, V13);
	lift(V14, C, D, V13);
	load(V14, C, V10, V13);
	lift(V14, D, V7, V13);
	load(V14, D, V10, V13);
	lift(V14, V7, Y, V13);
	load(V14, V7, V10, V13);
	unload(V14, X, V10, V13);
	drop(V14, X, Y, V13).

+!at(X, Y) : crate(X) & place(Y) & at(A, Y) & clear(A) & surface(A) & at(Z, Y) & hoist(Z) & not available(Z) & at(Z, C) & place(C) & at(B, C) & in(X, B) & truck(B) <-
	!available(Z);
	!at(X, Y).

+!at(X, Y) : crate(X) & place(Y) & at(A, Y) & surface(A) & not clear(A) & at(Z, Y) & lifting(Z, X) & hoist(Z) <-
	!clear(A);
	!at(X, Y).

+!at(X, Y) : crate(X) & place(Y) & at(A, Y) & surface(A) & not clear(A) & at(Z, Y) & available(Z) & hoist(Z) & at(Z, C) & place(C) & at(B, C) & in(X, B) & truck(B) <-
	!clear(A);
	!at(X, Y).

+!at(X, Y) : crate(X) & place(Y) & at(A, Y) & clear(A) & surface(A) & at(Z, Y) & available(Z) & hoist(Z) & at(Z, C) & place(C) & at(B, C) & truck(B) & not in(X, B) <-
	!in(X, B);
	!at(X, Y).

+!at(X, Y) : crate(X) & place(Y) & at(A, Y) & clear(A) & surface(A) & at(Z, Y) & hoist(Z) & not lifting(Z, X) <-
	!lifting(Z, X);
	!at(X, Y).

+!available(X) : hoist(X) & at(X, A) & available(A) & hoist(A) & place(A) & at(Z, A) & clear(Z) & surface(Z) & lifting(X, Y) & crate(Y) & at(Y, B) & place(B) & not at(A, B) <-
	!at(A, B);
	!available(X).

+!available(X) : hoist(X) & lifting(X, Y) & crate(Y) & at(Y, B) & place(B) & at(A, B) & available(A) & hoist(A) & place(A) & not at(X, A) & at(Z, A) & clear(Z) & surface(Z) <-
	!at(X, A);
	!available(X).

+!available(X) : hoist(X) & lifting(X, Y) & crate(Y) & place(A) & not at(X, A) & at(Z, A) & truck(Z) <-
	!at(X, A);
	!available(X).

+!available(X) : hoist(X) & at(X, A) & available(A) & hoist(A) & place(A) & at(A, B) & place(B) & at(Z, A) & clear(Z) & surface(Z) & lifting(X, Y) & crate(Y) & not at(Y, B) <-
	!at(Y, B);
	!available(X).

+!available(X) : hoist(X) & at(X, A) & available(A) & hoist(A) & place(A) & at(A, B) & place(B) & at(Y, B) & lifting(X, Y) & crate(Y) & clear(Z) & surface(Z) & not at(Z, A) <-
	!at(Z, A);
	!available(X).

+!available(X) : hoist(X) & at(X, A) & place(A) & lifting(X, Y) & crate(Y) & truck(Z) & not at(Z, A) <-
	!at(Z, A);
	!available(X).

+!available(X) : hoist(X) & at(X, A) & available(A) & hoist(A) & place(A) & at(A, B) & place(B) & at(Y, B) & lifting(X, Y) & crate(Y) & at(Z, A) & surface(Z) & not clear(Z) <-
	!clear(Z);
	!available(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(Y, A) & available(Y) & hoist(Y) & clear(B) & surface(B) & not at(B, A) <-
	!at(B, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(Y, A) & available(Y) & hoist(Y) & truck(B) & not at(B, A) <-
	!at(B, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(Y, A) & hoist(Y) & at(Y, D) & place(D) & at(C, D) & clear(C) & surface(C) & lifting(Y, B) & crate(B) & surface(B) & not at(B, A) <-
	!at(B, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(Y, A) & hoist(Y) & at(Y, D) & place(D) & at(C, D) & clear(C) & surface(C) & lifting(Y, B) & crate(B) & truck(B) & not at(B, A) <-
	!at(B, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(Y, A) & hoist(Y) & at(Y, D) & place(D) & at(C, D) & truck(C) & lifting(Y, B) & clear(B) & crate(B) & surface(B) & not at(B, A) <-
	!at(B, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(Y, A) & hoist(Y) & at(Y, D) & place(D) & at(C, D) & truck(C) & lifting(Y, B) & crate(B) & truck(B) & not at(B, A) <-
	!at(B, A);
	!clear(X).

+!clear(X) : crate(X) & in(X, B) & truck(B) & available(Y) & hoist(Y) & at(Y, A) & place(A) & at(Y, C) & place(C) & not at(B, C) & at(Z, A) & clear(Z) & surface(Z) <-
	!at(B, C);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(Y, A) & hoist(Y) & at(Y, D) & place(D) & at(C, D) & truck(C) & not at(C, A) & lifting(Y, B) & crate(B) <-
	!at(C, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & crate(B) & surface(B) & at(Y, A) & lifting(Y, B) & hoist(Y) & at(Y, D) & place(D) & clear(C) & surface(C) & not at(C, D) <-
	!at(C, D);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & crate(B) & truck(B) & at(Y, A) & lifting(Y, B) & hoist(Y) & at(Y, D) & place(D) & clear(C) & surface(C) & not at(C, D) <-
	!at(C, D);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(Y, A) & hoist(Y) & truck(Y) & at(Y, D) & place(D) & lifting(Y, B) & crate(B) & clear(C) & surface(C) & not at(C, D) <-
	!at(C, D);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & clear(B) & crate(B) & surface(B) & at(Y, A) & lifting(Y, B) & hoist(Y) & at(Y, D) & place(D) & truck(C) & not at(C, D) <-
	!at(C, D);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(C, A) & truck(C) & at(Y, A) & hoist(Y) & at(Y, D) & place(D) & not at(C, D) & lifting(Y, B) & crate(B) <-
	!at(C, D);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & crate(B) & truck(B) & at(Y, A) & lifting(Y, B) & hoist(Y) & at(Y, D) & place(D) & truck(C) & not at(C, D) <-
	!at(C, D);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(Y, A) & hoist(Y) & truck(Y) & at(Y, D) & place(D) & lifting(Y, B) & crate(B) & truck(C) & not at(C, D) <-
	!at(C, D);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & clear(B) & surface(B) & available(Y) & hoist(Y) & not at(Y, A) <-
	!at(Y, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & truck(B) & available(Y) & hoist(Y) & not at(Y, A) <-
	!at(Y, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & available(Y) & hoist(Y) & truck(Y) & not at(Y, A) <-
	!at(Y, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & crate(B) & surface(B) & lifting(Y, B) & hoist(Y) & not at(Y, A) & at(Y, D) & place(D) & at(C, D) & clear(C) & surface(C) <-
	!at(Y, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & crate(B) & truck(B) & lifting(Y, B) & hoist(Y) & not at(Y, A) & at(Y, D) & place(D) & at(C, D) & clear(C) & surface(C) <-
	!at(Y, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & clear(C) & surface(C) & at(C, D) & place(D) & at(Y, D) & hoist(Y) & truck(Y) & not at(Y, A) & lifting(Y, B) & crate(B) <-
	!at(Y, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & clear(B) & crate(B) & surface(B) & lifting(Y, B) & hoist(Y) & not at(Y, A) & at(Y, D) & place(D) & at(C, D) & truck(C) <-
	!at(Y, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(C, A) & truck(C) & at(C, D) & place(D) & at(Y, D) & hoist(Y) & not at(Y, A) & lifting(Y, B) & crate(B) <-
	!at(Y, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & crate(B) & truck(B) & lifting(Y, B) & hoist(Y) & not at(Y, A) & at(Y, D) & place(D) & at(C, D) & truck(C) <-
	!at(Y, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & crate(B) & lifting(Y, B) & hoist(Y) & truck(Y) & not at(Y, A) & at(Y, D) & place(D) & at(C, D) & truck(C) <-
	!at(Y, A);
	!clear(X).

+!clear(X) : crate(X) & lifting(Y, X) & hoist(Y) & clear(Z) & surface(Z) & at(Z, A) & place(A) & not at(Y, A) <-
	!at(Y, A);
	!clear(X).

+!clear(X) : crate(X) & in(X, B) & truck(B) & at(B, C) & place(C) & at(Y, C) & available(Y) & hoist(Y) & clear(Z) & surface(Z) & at(Z, A) & place(A) & not at(Y, A) <-
	!at(Y, A);
	!clear(X).

+!clear(X) : crate(X) & in(X, B) & truck(B) & at(B, C) & place(C) & available(Y) & hoist(Y) & not at(Y, C) & at(Y, A) & place(A) & at(Z, A) & clear(Z) & surface(Z) <-
	!at(Y, C);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & crate(B) & surface(B) & at(Y, A) & lifting(Y, B) & hoist(Y) & clear(C) & surface(C) & at(C, D) & place(D) & not at(Y, D) <-
	!at(Y, D);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & crate(B) & truck(B) & at(Y, A) & lifting(Y, B) & hoist(Y) & clear(C) & surface(C) & at(C, D) & place(D) & not at(Y, D) <-
	!at(Y, D);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(Y, A) & hoist(Y) & truck(Y) & lifting(Y, B) & crate(B) & clear(C) & surface(C) & at(C, D) & place(D) & not at(Y, D) <-
	!at(Y, D);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & clear(B) & crate(B) & surface(B) & at(Y, A) & lifting(Y, B) & hoist(Y) & place(D) & not at(Y, D) & at(C, D) & truck(C) <-
	!at(Y, D);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(C, A) & truck(C) & at(C, D) & place(D) & at(Y, A) & hoist(Y) & not at(Y, D) & lifting(Y, B) & crate(B) <-
	!at(Y, D);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & crate(B) & truck(B) & at(Y, A) & lifting(Y, B) & hoist(Y) & place(D) & not at(Y, D) & at(C, D) & truck(C) <-
	!at(Y, D);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(Y, A) & hoist(Y) & truck(Y) & lifting(Y, B) & crate(B) & place(D) & not at(Y, D) & at(C, D) & truck(C) <-
	!at(Y, D);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & available(Y) & hoist(Y) & at(Y, A) & place(A) & not at(Z, A) & at(B, A) & clear(B) & surface(B) <-
	!at(Z, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & available(Y) & hoist(Y) & at(Y, A) & place(A) & not at(Z, A) & at(B, A) & truck(B) <-
	!at(Z, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & available(Y) & hoist(Y) & truck(Y) & at(Y, A) & place(A) & not at(Z, A) <-
	!at(Z, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & clear(C) & surface(C) & at(C, D) & place(D) & at(Y, D) & hoist(Y) & at(Y, A) & place(A) & not at(Z, A) & at(B, A) & lifting(Y, B) & crate(B) & surface(B) <-
	!at(Z, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & clear(C) & surface(C) & at(C, D) & place(D) & at(Y, D) & hoist(Y) & at(Y, A) & place(A) & not at(Z, A) & at(B, A) & lifting(Y, B) & crate(B) & truck(B) <-
	!at(Z, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & clear(C) & surface(C) & at(C, D) & place(D) & at(Y, D) & hoist(Y) & truck(Y) & at(Y, A) & place(A) & not at(Z, A) & lifting(Y, B) & crate(B) <-
	!at(Z, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & clear(B) & crate(B) & surface(B) & at(B, A) & place(A) & not at(Z, A) & at(Y, A) & lifting(Y, B) & hoist(Y) & at(Y, D) & place(D) & at(C, D) & truck(C) <-
	!at(Z, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & crate(B) & lifting(Y, B) & hoist(Y) & at(Y, A) & place(A) & not at(Z, A) & at(C, A) & truck(C) & at(C, D) & at(Y, D) & place(D) <-
	!at(Z, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & crate(B) & truck(B) & at(B, A) & place(A) & not at(Z, A) & at(Y, A) & lifting(Y, B) & hoist(Y) & at(Y, D) & place(D) & at(C, D) & truck(C) <-
	!at(Z, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & crate(B) & lifting(Y, B) & hoist(Y) & truck(Y) & at(Y, A) & place(A) & not at(Z, A) & at(Y, D) & place(D) & at(C, D) & truck(C) <-
	!at(Z, A);
	!clear(X).

+!clear(X) : crate(X) & lifting(Y, X) & hoist(Y) & at(Y, A) & place(A) & clear(Z) & surface(Z) & not at(Z, A) <-
	!at(Z, A);
	!clear(X).

+!clear(X) : crate(X) & in(X, B) & truck(B) & at(B, C) & place(C) & at(Y, C) & available(Y) & hoist(Y) & at(Y, A) & place(A) & clear(Z) & surface(Z) & not at(Z, A) <-
	!at(Z, A);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & clear(B) & surface(B) & at(Y, A) & hoist(Y) & not available(Y) <-
	!available(Y);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & truck(B) & at(Y, A) & hoist(Y) & not available(Y) <-
	!available(Y);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(Y, A) & hoist(Y) & truck(Y) & not available(Y) <-
	!available(Y);
	!clear(X).

+!clear(X) : crate(X) & in(X, B) & truck(B) & at(B, C) & place(C) & at(Y, C) & hoist(Y) & not available(Y) & at(Y, A) & place(A) & at(Z, A) & clear(Z) & surface(Z) <-
	!available(Y);
	!clear(X).

+!clear(X) : crate(X) & available(Y) & hoist(Y) & at(Y, A) & place(A) & at(Y, C) & place(C) & at(B, C) & truck(B) & not in(X, B) & at(Z, A) & clear(Z) & surface(Z) <-
	!in(X, B);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & crate(B) & surface(B) & at(Y, A) & hoist(Y) & not lifting(Y, B) & at(Y, D) & place(D) & at(C, D) & clear(C) & surface(C) <-
	!lifting(Y, B);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & crate(B) & truck(B) & at(Y, A) & hoist(Y) & not lifting(Y, B) & at(Y, D) & place(D) & at(C, D) & clear(C) & surface(C) <-
	!lifting(Y, B);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(Y, A) & hoist(Y) & truck(Y) & at(Y, D) & place(D) & at(C, D) & clear(C) & surface(C) & crate(B) & not lifting(Y, B) <-
	!lifting(Y, B);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & clear(B) & crate(B) & surface(B) & at(Y, A) & hoist(Y) & not lifting(Y, B) & at(Y, D) & place(D) & at(C, D) & truck(C) <-
	!lifting(Y, B);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(C, A) & truck(C) & at(C, D) & place(D) & at(Y, A) & at(Y, D) & hoist(Y) & crate(B) & not lifting(Y, B) <-
	!lifting(Y, B);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(B, A) & crate(B) & truck(B) & at(Y, A) & hoist(Y) & not lifting(Y, B) & at(Y, D) & place(D) & at(C, D) & truck(C) <-
	!lifting(Y, B);
	!clear(X).

+!clear(X) : surface(X) & on(Z, X) & clear(Z) & crate(Z) & at(Z, A) & place(A) & at(Y, A) & hoist(Y) & truck(Y) & at(Y, D) & place(D) & at(C, D) & truck(C) & crate(B) & not lifting(Y, B) <-
	!lifting(Y, B);
	!clear(X).

+!clear(X) : crate(X) & clear(Z) & surface(Z) & at(Z, A) & place(A) & at(Y, A) & hoist(Y) & not lifting(Y, X) <-
	!lifting(Y, X);
	!clear(X).

+!in(X, Y) : crate(X) & truck(Y) & at(Y, A) & place(A) & at(Z, A) & available(Z) & hoist(Z) & at(Z, C) & place(C) & in(X, B) & truck(B) & not at(B, C) <-
	!at(B, C);
	!in(X, Y).

+!in(X, Y) : crate(X) & truck(Y) & lifting(Z, X) & hoist(Z) & at(Z, A) & place(A) & not at(Y, A) <-
	!at(Y, A);
	!in(X, Y).

+!in(X, Y) : crate(X) & truck(Y) & in(X, B) & truck(B) & at(B, C) & place(C) & at(Z, C) & available(Z) & hoist(Z) & at(Z, A) & place(A) & not at(Y, A) <-
	!at(Y, A);
	!in(X, Y).

+!in(X, Y) : crate(X) & truck(Y) & at(Y, A) & place(A) & lifting(Z, X) & hoist(Z) & not at(Z, A) <-
	!at(Z, A);
	!in(X, Y).

+!in(X, Y) : crate(X) & truck(Y) & at(Y, A) & place(A) & in(X, B) & truck(B) & at(B, C) & place(C) & at(Z, C) & available(Z) & hoist(Z) & not at(Z, A) <-
	!at(Z, A);
	!in(X, Y).

+!in(X, Y) : crate(X) & truck(Y) & at(Y, A) & place(A) & at(Z, A) & available(Z) & hoist(Z) & in(X, B) & truck(B) & at(B, C) & place(C) & not at(Z, C) <-
	!at(Z, C);
	!in(X, Y).

+!in(X, Y) : crate(X) & truck(Y) & at(Y, A) & place(A) & at(Z, A) & hoist(Z) & not available(Z) & at(Z, C) & place(C) & at(B, C) & in(X, B) & truck(B) <-
	!available(Z);
	!in(X, Y).

+!in(X, Y) : crate(X) & truck(Y) & at(Y, A) & place(A) & at(Z, A) & hoist(Z) & not lifting(Z, X) <-
	!lifting(Z, X);
	!in(X, Y).

+!lifting(X, Y) : available(X) & crate(Y) & hoist(X) & at(X, A) & place(A) & at(Z, A) & truck(Z) & at(Z, C) & place(C) & lifting(B, Y) & hoist(B) & not at(B, C) <-
	!at(B, C);
	!lifting(X, Y).

+!lifting(X, Y) : clear(Y) & crate(Y) & hoist(X) & at(X, A) & at(Y, A) & place(A) & at(X, D) & place(D) & lifting(X, B) & crate(B) & on(Y, Z) & surface(Z) & truck(C) & not at(C, D) <-
	!at(C, D);
	!lifting(X, Y).

+!lifting(X, Y) : crate(Y) & hoist(X) & at(X, A) & place(A) & at(X, D) & place(D) & at(Z, A) & in(Y, Z) & truck(Z) & lifting(X, B) & crate(B) & clear(C) & surface(C) & not at(C, D) <-
	!at(C, D);
	!lifting(X, Y).

+!lifting(X, Y) : crate(Y) & hoist(X) & at(X, A) & place(A) & at(X, D) & place(D) & at(Z, A) & in(Y, Z) & truck(Z) & lifting(X, B) & crate(B) & truck(C) & not at(C, D) <-
	!at(C, D);
	!lifting(X, Y).

+!lifting(X, Y) : available(X) & clear(Y) & crate(Y) & hoist(X) & at(Y, A) & place(A) & not at(X, A) & on(Y, Z) & surface(Z) <-
	!at(X, A);
	!lifting(X, Y).

+!lifting(X, Y) : clear(Y) & crate(Y) & hoist(X) & at(X, D) & place(D) & at(C, D) & truck(C) & at(Y, A) & place(A) & not at(X, A) & lifting(X, B) & crate(B) & on(Y, Z) & surface(Z) <-
	!at(X, A);
	!lifting(X, Y).

+!lifting(X, Y) : available(X) & crate(Y) & hoist(X) & in(Y, Z) & truck(Z) & at(Z, A) & place(A) & not at(X, A) <-
	!at(X, A);
	!lifting(X, Y).

+!lifting(X, Y) : crate(Y) & hoist(X) & at(X, D) & place(D) & at(C, D) & clear(C) & surface(C) & in(Y, Z) & truck(Z) & at(Z, A) & place(A) & not at(X, A) & lifting(X, B) & crate(B) <-
	!at(X, A);
	!lifting(X, Y).

+!lifting(X, Y) : crate(Y) & hoist(X) & at(X, D) & place(D) & at(C, D) & truck(C) & in(Y, Z) & truck(Z) & at(Z, A) & place(A) & not at(X, A) & lifting(X, B) & crate(B) <-
	!at(X, A);
	!lifting(X, Y).

+!lifting(X, Y) : available(X) & crate(Y) & hoist(X) & lifting(B, Y) & hoist(B) & at(B, C) & place(C) & at(Z, C) & truck(Z) & at(Z, A) & place(A) & not at(X, A) <-
	!at(X, A);
	!lifting(X, Y).

+!lifting(X, Y) : clear(Y) & crate(Y) & hoist(X) & at(X, A) & at(Y, A) & place(A) & lifting(X, B) & crate(B) & on(Y, Z) & surface(Z) & place(D) & not at(X, D) & at(C, D) & truck(C) <-
	!at(X, D);
	!lifting(X, Y).

+!lifting(X, Y) : crate(Y) & hoist(X) & at(X, A) & place(A) & at(Z, A) & in(Y, Z) & truck(Z) & lifting(X, B) & crate(B) & clear(C) & surface(C) & at(C, D) & place(D) & not at(X, D) <-
	!at(X, D);
	!lifting(X, Y).

+!lifting(X, Y) : crate(Y) & hoist(X) & at(X, A) & place(A) & at(Z, A) & in(Y, Z) & truck(Z) & lifting(X, B) & crate(B) & place(D) & not at(X, D) & at(C, D) & truck(C) <-
	!at(X, D);
	!lifting(X, Y).

+!lifting(X, Y) : available(X) & clear(Y) & crate(Y) & hoist(X) & at(X, A) & place(A) & not at(Y, A) & on(Y, Z) & surface(Z) <-
	!at(Y, A);
	!lifting(X, Y).

+!lifting(X, Y) : clear(Y) & crate(Y) & hoist(X) & at(X, A) & place(A) & not at(Y, A) & at(X, D) & place(D) & at(C, D) & truck(C) & lifting(X, B) & crate(B) & on(Y, Z) & surface(Z) <-
	!at(Y, A);
	!lifting(X, Y).

+!lifting(X, Y) : available(X) & crate(Y) & hoist(X) & at(X, A) & place(A) & in(Y, Z) & truck(Z) & not at(Z, A) <-
	!at(Z, A);
	!lifting(X, Y).

+!lifting(X, Y) : crate(Y) & hoist(X) & at(X, A) & place(A) & at(X, D) & place(D) & at(C, D) & clear(C) & surface(C) & in(Y, Z) & truck(Z) & not at(Z, A) & lifting(X, B) & crate(B) <-
	!at(Z, A);
	!lifting(X, Y).

+!lifting(X, Y) : crate(Y) & hoist(X) & at(X, A) & place(A) & at(X, D) & place(D) & at(C, D) & truck(C) & in(Y, Z) & truck(Z) & not at(Z, A) & lifting(X, B) & crate(B) <-
	!at(Z, A);
	!lifting(X, Y).

+!lifting(X, Y) : available(X) & crate(Y) & hoist(X) & at(X, A) & place(A) & lifting(B, Y) & hoist(B) & at(B, C) & place(C) & at(Z, C) & truck(Z) & not at(Z, A) <-
	!at(Z, A);
	!lifting(X, Y).

+!lifting(X, Y) : available(X) & crate(Y) & hoist(X) & at(X, A) & place(A) & at(Z, A) & truck(Z) & lifting(B, Y) & hoist(B) & at(B, C) & place(C) & not at(Z, C) <-
	!at(Z, C);
	!lifting(X, Y).

+!lifting(X, Y) : crate(Y) & hoist(X) & at(X, A) & place(A) & at(X, D) & place(D) & at(C, D) & surface(C) & not clear(C) & at(Z, A) & in(Y, Z) & truck(Z) & lifting(X, B) & crate(B) <-
	!clear(C);
	!lifting(X, Y).

+!lifting(X, Y) : not clear(Y) <-
	!clear(Y);
	!lifting(X, Y).

+!on(X, Y) : clear(Y) & crate(X) & surface(Y) & at(Y, A) & place(A) & at(Z, A) & available(Z) & hoist(Z) & at(Z, C) & place(C) & in(X, B) & truck(B) & not at(B, C) <-
	!at(B, C);
	!on(X, Y).

+!on(X, Y) : clear(Y) & crate(X) & surface(Y) & lifting(Z, X) & hoist(Z) & at(Z, A) & place(A) & not at(Y, A) <-
	!at(Y, A);
	!on(X, Y).

+!on(X, Y) : clear(Y) & crate(X) & surface(Y) & in(X, B) & truck(B) & at(B, C) & place(C) & at(Z, C) & available(Z) & hoist(Z) & at(Z, A) & place(A) & not at(Y, A) <-
	!at(Y, A);
	!on(X, Y).

+!on(X, Y) : clear(Y) & crate(X) & surface(Y) & at(Y, A) & place(A) & lifting(Z, X) & hoist(Z) & not at(Z, A) <-
	!at(Z, A);
	!on(X, Y).

+!on(X, Y) : clear(Y) & crate(X) & surface(Y) & at(Y, A) & place(A) & in(X, B) & truck(B) & at(B, C) & place(C) & at(Z, C) & available(Z) & hoist(Z) & not at(Z, A) <-
	!at(Z, A);
	!on(X, Y).

+!on(X, Y) : clear(Y) & crate(X) & surface(Y) & at(Y, A) & place(A) & at(Z, A) & available(Z) & hoist(Z) & in(X, B) & truck(B) & at(B, C) & place(C) & not at(Z, C) <-
	!at(Z, C);
	!on(X, Y).

+!on(X, Y) : clear(Y) & crate(X) & surface(Y) & at(Y, A) & place(A) & at(Z, A) & hoist(Z) & not available(Z) & at(Z, C) & place(C) & at(B, C) & in(X, B) & truck(B) <-
	!available(Z);
	!on(X, Y).

+!on(X, Y) : not clear(Y) <-
	!clear(Y);
	!on(X, Y).

+!on(X, Y) : clear(Y) & crate(X) & surface(Y) & at(Y, A) & place(A) & at(Z, A) & available(Z) & hoist(Z) & at(Z, C) & place(C) & at(B, C) & truck(B) & not in(X, B) <-
	!in(X, B);
	!on(X, Y).

+!on(X, Y) : clear(Y) & crate(X) & surface(Y) & at(Y, A) & place(A) & at(Z, A) & hoist(Z) & not lifting(Z, X) <-
	!lifting(Z, X);
	!on(X, Y).
