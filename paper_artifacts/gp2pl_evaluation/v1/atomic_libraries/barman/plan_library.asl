/* Generated AgentSpeak(L) Plan Library */
/* Domain: barman */

+!clean(X) : clean(X) <-
	true.

+!contains(X, Y) : contains(X, Y) <-
	true.

+!empty(X) : empty(X) <-
	true.

+!handempty(X) : handempty(X) <-
	true.

+!holding(X, Y) : holding(X, Y) <-
	true.

+!ontable(X) : ontable(X) <-
	true.

+!shaked(X) : shaked(X) <-
	true.

+!shaker_level(X, Y) : shaker_level(X, Y) <-
	true.

+!unshaked(X) : unshaked(X) <-
	true.

+!used(X, Y) : used(X, Y) <-
	true.

+!clean(X) : obj_tp(X, shaker) & empty(X) & holding(Y, X) & obj_tp(Y, hand) & handempty(Z) & obj_tp(Z, hand) <-
	clean_shaker(Y, Z, X).

+!clean(X) : obj_tp(X, shot) & empty(X) & holding(Z, X) & obj_tp(Z, hand) & used(X, Y) & obj_tp(Y, beverage) & handempty(A) & obj_tp(A, hand) <-
	clean_shot(X, Y, Z, A).

+!clean(X) : obj_tp(X, shaker) & empty(X) & ontable(X) & handempty(Y) & obj_tp(Y, hand) & handempty(Z) & obj_tp(Z, hand) & Y \== Z <-
	grasp(Y, X);
	clean_shaker(Y, Z, X).

+!clean(X) : obj_tp(X, shot) & empty(X) & ontable(X) & used(X, Y) & obj_tp(Y, beverage) & handempty(A) & obj_tp(A, hand) & handempty(Z) & obj_tp(Z, hand) & A \== Z <-
	grasp(Z, X);
	clean_shot(X, Y, Z, A).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, ingredient) & clean(X) & empty(X) & dispenses(B, Y) & obj_tp(B, dispenser) & holding(Z, X) & obj_tp(Z, hand) & handempty(A) & obj_tp(A, hand) <-
	fill_shot(X, Y, Z, A, B).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & clean(X) & empty(X) & contains(Z, Y) & obj_tp(Z, shot) & holding(A, Z) & obj_tp(A, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	pour_shot_to_clean_shaker(Z, Y, X, A, B, C).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & unshaked(X) & contains(Z, Y) & obj_tp(Z, shot) & holding(A, Z) & obj_tp(A, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	pour_shot_to_used_shaker(Z, Y, X, A, B, C).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, ingredient) & used(X, Y) & empty(X) & dispenses(B, Y) & obj_tp(B, dispenser) & holding(Z, X) & obj_tp(Z, hand) & handempty(A) & obj_tp(A, hand) <-
	refill_shot(X, Y, Z, A, B).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, cocktail) & unshaked(X) & cocktail_part1(Y, Z) & obj_tp(Z, ingredient) & contains(X, Z) & cocktail_part2(Y, A) & obj_tp(A, ingredient) & contains(X, A) & holding(B, X) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) <-
	shake(Y, Z, A, X, B, C).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & contains(Z, Y) & obj_tp(Z, shot) & holding(A, Z) & obj_tp(A, hand) & holding(D, X) & obj_tp(D, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & handempty(V7) & obj_tp(V7, hand) <-
	clean_shaker(D, V7, X);
	pour_shot_to_clean_shaker(Z, Y, X, A, B, C).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, ingredient) & empty(X) & dispenses(B, Y) & obj_tp(B, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(Z, X) & obj_tp(Z, hand) & used(X, C) & obj_tp(C, beverage) & handempty(A) & obj_tp(A, hand) & handempty(V7) & obj_tp(V7, hand) <-
	clean_shot(X, C, D, V7);
	fill_shot(X, Y, Z, A, B).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & shaked(A) & holding(V7, X) & obj_tp(V7, hand) & holding(Z, A) & obj_tp(Z, hand) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) & used(X, D) & obj_tp(D, beverage) & handempty(V8) & obj_tp(V8, hand) <-
	clean_shot(X, D, V7, V8);
	pour_shaker_to_shot(Y, X, Z, A, B, C).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, ingredient) & clean(X) & empty(X) & ontable(X) & dispenses(B, Y) & obj_tp(B, dispenser) & handempty(A) & obj_tp(A, hand) & handempty(Z) & obj_tp(Z, hand) & A \== Z <-
	grasp(Z, X);
	fill_shot(X, Y, Z, A, B).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & ontable(A) & shaked(A) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) & handempty(Z) & obj_tp(Z, hand) <-
	grasp(Z, A);
	pour_shaker_to_shot(Y, X, Z, A, B, C).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & clean(X) & empty(X) & contains(Z, Y) & obj_tp(Z, shot) & X \== Z & ontable(Z) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & handempty(A) & obj_tp(A, hand) <-
	grasp(A, Z);
	pour_shot_to_clean_shaker(Z, Y, X, A, B, C).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & unshaked(X) & contains(Z, Y) & obj_tp(Z, shot) & X \== Z & ontable(Z) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & handempty(A) & obj_tp(A, hand) <-
	grasp(A, Z);
	pour_shot_to_used_shaker(Z, Y, X, A, B, C).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, ingredient) & used(X, Y) & empty(X) & ontable(X) & dispenses(B, Y) & obj_tp(B, dispenser) & handempty(A) & obj_tp(A, hand) & handempty(Z) & obj_tp(Z, hand) & A \== Z <-
	grasp(Z, X);
	refill_shot(X, Y, Z, A, B).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, cocktail) & ontable(X) & unshaked(X) & cocktail_part1(Y, Z) & obj_tp(Z, ingredient) & contains(X, Z) & cocktail_part2(Y, A) & obj_tp(A, ingredient) & contains(X, A) & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, X);
	shake(Y, Z, A, X, B, C).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & unshaked(A) & contains(A, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part1(D, V7) & obj_tp(D, cocktail) & cocktail_part2(D, V8) & obj_tp(V8, ingredient) & V8 \== Y & contains(A, V8) & holding(V9, A) & obj_tp(V9, hand) & holding(Z, A) & obj_tp(Z, hand) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) & handempty(V10) & obj_tp(V10, hand) <-
	shake(D, V7, V8, A, V9, V10);
	pour_shaker_to_shot(Y, X, Z, A, B, C).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & clean(Z) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & handempty(V7) & obj_tp(V7, hand) <-
	clean_shaker(D, V7, X);
	fill_shot(Z, Y, D, V7, V8);
	pour_shot_to_clean_shaker(Z, Y, X, A, B, C).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & used(Z, Y) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & handempty(V7) & obj_tp(V7, hand) <-
	clean_shaker(D, V7, X);
	refill_shot(Z, Y, D, V7, V8);
	pour_shot_to_clean_shaker(Z, Y, X, A, B, C).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(V10, Z) & obj_tp(V10, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & used(Z, V9) & obj_tp(V9, beverage) & handempty(V11) & obj_tp(V11, hand) & handempty(V7) & obj_tp(V7, hand) <-
	clean_shot(Z, V9, V10, V11);
	clean_shaker(D, V7, X);
	fill_shot(Z, Y, D, V7, V8);
	pour_shot_to_clean_shaker(Z, Y, X, A, B, C).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & shaked(X) & contains(X, V10) & obj_tp(V10, cocktail) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & clean(Z) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(V9, X) & obj_tp(V9, hand) & shaker_empty_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & shaker_level(X, V11) & obj_tp(V11, level) & B \== V11 & handempty(V7) & obj_tp(V7, hand) <-
	empty_shaker(V9, X, V10, V11, B);
	clean_shaker(D, V7, X);
	fill_shot(Z, Y, D, V7, V8);
	pour_shot_to_clean_shaker(Z, Y, X, A, B, C).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & shaked(X) & contains(X, V10) & obj_tp(V10, cocktail) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & used(Z, Y) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(V9, X) & obj_tp(V9, hand) & shaker_empty_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & shaker_level(X, V11) & obj_tp(V11, level) & B \== V11 & handempty(V7) & obj_tp(V7, hand) <-
	empty_shaker(V9, X, V10, V11, B);
	clean_shaker(D, V7, X);
	refill_shot(Z, Y, D, V7, V8);
	pour_shot_to_clean_shaker(Z, Y, X, A, B, C).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & clean(Z) & contains(Z, V10) & obj_tp(V10, beverage) & V10 \== Y & holding(A, Z) & obj_tp(A, hand) & holding(V9, Z) & obj_tp(V9, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & handempty(V7) & obj_tp(V7, hand) <-
	empty_shot(V9, Z, V10);
	clean_shaker(D, V7, X);
	fill_shot(Z, Y, D, V7, V8);
	pour_shot_to_clean_shaker(Z, Y, X, A, B, C).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & used(Z, Y) & contains(Z, V10) & obj_tp(V10, beverage) & V10 \== Y & holding(A, Z) & obj_tp(A, hand) & holding(V9, Z) & obj_tp(V9, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & handempty(V7) & obj_tp(V7, hand) <-
	empty_shot(V9, Z, V10);
	clean_shaker(D, V7, X);
	refill_shot(Z, Y, D, V7, V8);
	pour_shot_to_clean_shaker(Z, Y, X, A, B, C).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & ontable(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & clean(Z) & obj_tp(Z, shot) & X \== Z & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(D, Z) & obj_tp(D, hand) & handempty(D) & handempty(V7) & obj_tp(V7, hand) & D \== V7 <-
	grasp(D, X);
	clean_shaker(D, V7, X);
	fill_shot(Z, Y, D, V7, V8);
	pour_shot_to_clean_shaker(Z, Y, X, A, B, C).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & handempty(D) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & clean(Z) & obj_tp(Z, shot) & X \== Z & empty(Z) & ontable(Z) & holding(A, Z) & obj_tp(A, hand) & handempty(V7) & obj_tp(V7, hand) & D \== V7 <-
	grasp(D, Z);
	clean_shaker(D, V7, X);
	fill_shot(Z, Y, D, V7, V8);
	pour_shot_to_clean_shaker(Z, Y, X, A, B, C).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & X \== Z & clean(Z) & empty(Z) & ontable(Z) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & handempty(A) & obj_tp(A, hand) & handempty(V7) & obj_tp(V7, hand) & A \== V7 <-
	grasp(A, Z);
	clean_shaker(D, V7, X);
	fill_shot(Z, Y, D, V7, V8);
	pour_shot_to_clean_shaker(Z, Y, X, A, B, C).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & ontable(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & used(Z, Y) & obj_tp(Z, shot) & X \== Z & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(D, Z) & obj_tp(D, hand) & handempty(D) & handempty(V7) & obj_tp(V7, hand) & D \== V7 <-
	grasp(D, X);
	clean_shaker(D, V7, X);
	refill_shot(Z, Y, D, V7, V8);
	pour_shot_to_clean_shaker(Z, Y, X, A, B, C).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & handempty(D) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & used(Z, Y) & obj_tp(Z, shot) & X \== Z & empty(Z) & ontable(Z) & holding(A, Z) & obj_tp(A, hand) & handempty(V7) & obj_tp(V7, hand) & D \== V7 <-
	grasp(D, Z);
	clean_shaker(D, V7, X);
	refill_shot(Z, Y, D, V7, V8);
	pour_shot_to_clean_shaker(Z, Y, X, A, B, C).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & X \== Z & used(Z, Y) & empty(Z) & ontable(Z) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & handempty(A) & obj_tp(A, hand) & handempty(V7) & obj_tp(V7, hand) & A \== V7 <-
	grasp(A, Z);
	clean_shaker(D, V7, X);
	refill_shot(Z, Y, D, V7, V8);
	pour_shot_to_clean_shaker(Z, Y, X, A, B, C).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & shaked(X) & contains(X, V9) & obj_tp(V9, beverage) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & clean(Z) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(V11, X) & obj_tp(V11, hand) & shaker_level(X, V12) & obj_tp(V12, level) & next(B, V12) & obj_tp(B, level) & B \== V12 & next(B, C) & obj_tp(C, level) & clean(V10) & obj_tp(V10, shot) & V10 \== Z & empty(V10) & handempty(V7) & obj_tp(V7, hand) <-
	pour_shaker_to_shot(V9, V10, V11, X, V12, B);
	clean_shaker(D, V7, X);
	fill_shot(Z, Y, D, V7, V8);
	pour_shot_to_clean_shaker(Z, Y, X, A, B, C).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & shaked(X) & contains(X, V9) & obj_tp(V9, beverage) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & used(Z, Y) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(V11, X) & obj_tp(V11, hand) & shaker_level(X, V12) & obj_tp(V12, level) & next(B, V12) & obj_tp(B, level) & B \== V12 & next(B, C) & obj_tp(C, level) & clean(V10) & obj_tp(V10, shot) & V10 \== Z & empty(V10) & handempty(V7) & obj_tp(V7, hand) <-
	pour_shaker_to_shot(V9, V10, V11, X, V12, B);
	clean_shaker(D, V7, X);
	refill_shot(Z, Y, D, V7, V8);
	pour_shot_to_clean_shaker(Z, Y, X, A, B, C).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(C, Y) & obj_tp(C, shaker) & shaked(C) & holding(Z, C) & obj_tp(Z, hand) & shaker_level(C, A) & obj_tp(A, level) & next(B, A) & obj_tp(B, level) <-
	pour_shaker_to_shot(Y, X, Z, C, A, B).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, B) & obj_tp(B, ingredient) & B \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(V8, B) & obj_tp(V8, shaker) & contains(V8, C) & unshaked(V8) & holding(Z, V8) & obj_tp(Z, hand) & shaker_level(V8, D) & obj_tp(D, level) & next(V7, D) & obj_tp(V7, level) & handempty(A) & obj_tp(A, hand) <-
	shake(Y, B, C, V8, Z, A);
	pour_shaker_to_shot(Y, X, Z, V8, D, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, B) & obj_tp(B, ingredient) & B \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(V8, B) & obj_tp(V8, shaker) & contains(V8, C) & ontable(V8) & unshaked(V8) & shaker_level(V8, D) & obj_tp(D, level) & next(V7, D) & obj_tp(V7, level) & handempty(A) & obj_tp(A, hand) & handempty(Z) & obj_tp(Z, hand) & A \== Z <-
	grasp(Z, V8);
	shake(Y, B, C, V8, Z, A);
	pour_shaker_to_shot(Y, X, Z, V8, D, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, B) & obj_tp(B, ingredient) & B \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(V8, B) & obj_tp(V8, shaker) & contains(V8, C) & unshaked(V8) & holding(A, V8) & obj_tp(A, hand) & holding(Z, X) & obj_tp(Z, hand) & A \== Z & shaker_level(V8, D) & obj_tp(D, level) & next(V7, D) & obj_tp(V7, level) <-
	leave(Z, X);
	shake(Y, B, C, V8, A, Z);
	pour_shaker_to_shot(Y, X, A, V8, D, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, B) & obj_tp(B, ingredient) & B \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(V8, B) & obj_tp(V8, shaker) & contains(V8, C) & unshaked(V8) & holding(A, V8) & obj_tp(A, hand) & shaker_level(V8, D) & obj_tp(D, level) & next(V7, D) & obj_tp(V7, level) & holding(Z, V9) & obj_tp(V9, container) & obj_tp(Z, hand) & A \== Z <-
	leave(Z, V9);
	shake(Y, B, C, V8, A, Z);
	pour_shaker_to_shot(Y, X, A, V8, D, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, B) & obj_tp(B, ingredient) & B \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(V8, B) & obj_tp(V8, shaker) & V8 \== X & contains(V8, C) & ontable(V8) & unshaked(V8) & holding(Z, X) & obj_tp(Z, hand) & shaker_level(V8, D) & obj_tp(D, level) & next(V7, D) & obj_tp(V7, level) & handempty(A) & obj_tp(A, hand) & A \== Z <-
	leave(Z, X);
	grasp(Z, V8);
	shake(Y, B, C, V8, Z, A);
	pour_shaker_to_shot(Y, X, Z, V8, D, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, B) & obj_tp(B, ingredient) & B \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(V8, B) & obj_tp(V8, shaker) & contains(V8, C) & ontable(V8) & unshaked(V8) & shaker_level(V8, D) & obj_tp(D, level) & next(V7, D) & obj_tp(V7, level) & handempty(A) & obj_tp(A, hand) & holding(Z, V9) & obj_tp(V9, container) & obj_tp(Z, hand) & A \== Z & V8 \== V9 <-
	leave(Z, V9);
	grasp(Z, V8);
	shake(Y, B, C, V8, Z, A);
	pour_shaker_to_shot(Y, X, Z, V8, D, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, B) & obj_tp(B, ingredient) & B \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(V8, C) & obj_tp(V8, shaker) & unshaked(V8) & contains(V9, B) & obj_tp(V9, shot) & V8 \== V9 & holding(A, V8) & obj_tp(A, hand) & holding(Z, V9) & obj_tp(Z, hand) & A \== Z & shaker_level(V8, D) & obj_tp(D, level) & next(D, V7) & obj_tp(V7, level) & D \== V7 <-
	pour_shot_to_used_shaker(V9, B, V8, Z, D, V7);
	leave(Z, V9);
	shake(Y, B, C, V8, A, Z);
	pour_shaker_to_shot(Y, X, A, V8, V7, D).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, B) & obj_tp(B, ingredient) & B \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(V8, B) & obj_tp(V8, shaker) & contains(V8, C) & ontable(V8) & unshaked(V8) & holding(A, X) & obj_tp(A, hand) & shaker_level(V8, D) & obj_tp(D, level) & next(V7, D) & obj_tp(V7, level) & handempty(Z) & obj_tp(Z, hand) & A \== Z <-
	grasp(Z, V8);
	leave(A, X);
	shake(Y, B, C, V8, Z, A);
	pour_shaker_to_shot(Y, X, Z, V8, D, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, C) & obj_tp(C, ingredient) & C \== Y & cocktail_part2(Y, B) & obj_tp(B, ingredient) & B \== Y & contains(V8, C) & obj_tp(V8, shaker) & unshaked(V8) & contains(V9, B) & obj_tp(V9, shot) & V8 \== V9 & holding(A, V8) & obj_tp(A, hand) & holding(Z, V9) & obj_tp(Z, hand) & A \== Z & shaker_level(V8, D) & obj_tp(D, level) & next(D, V7) & obj_tp(V7, level) & D \== V7 <-
	pour_shot_to_used_shaker(V9, B, V8, Z, D, V7);
	leave(Z, V9);
	shake(Y, C, B, V8, A, Z);
	pour_shaker_to_shot(Y, X, A, V8, V7, D).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, C) & obj_tp(C, ingredient) & C \== Y & cocktail_part2(Y, B) & obj_tp(B, ingredient) & B \== Y & contains(V8, C) & obj_tp(V8, shaker) & ontable(V8) & unshaked(V8) & contains(V9, B) & obj_tp(V9, shot) & V8 \== V9 & holding(A, V9) & obj_tp(A, hand) & shaker_level(V8, D) & obj_tp(D, level) & next(D, V7) & obj_tp(V7, level) & D \== V7 & handempty(Z) & obj_tp(Z, hand) & A \== Z <-
	grasp(Z, V8);
	pour_shot_to_used_shaker(V9, B, V8, A, D, V7);
	leave(A, V9);
	shake(Y, C, B, V8, Z, A);
	pour_shaker_to_shot(Y, X, Z, V8, V7, D).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, C) & obj_tp(C, ingredient) & C \== Y & cocktail_part2(Y, B) & obj_tp(B, ingredient) & B \== Y & contains(V8, C) & obj_tp(V8, shaker) & ontable(V8) & unshaked(V8) & contains(V9, B) & obj_tp(V9, shot) & V8 \== V9 & holding(Z, V9) & obj_tp(Z, hand) & shaker_level(V8, D) & obj_tp(D, level) & next(D, V7) & obj_tp(V7, level) & D \== V7 & handempty(A) & obj_tp(A, hand) & A \== Z <-
	pour_shot_to_used_shaker(V9, B, V8, Z, D, V7);
	leave(Z, V9);
	grasp(Z, V8);
	shake(Y, C, B, V8, Z, A);
	pour_shaker_to_shot(Y, X, Z, V8, V7, D).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, B) & obj_tp(B, ingredient) & B \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(V8, C) & obj_tp(V8, shaker) & ontable(V8) & unshaked(V8) & contains(V9, B) & obj_tp(V9, shot) & V8 \== V9 & holding(A, V9) & obj_tp(A, hand) & shaker_level(V8, D) & obj_tp(D, level) & next(D, V7) & obj_tp(V7, level) & D \== V7 & handempty(Z) & obj_tp(Z, hand) & A \== Z <-
	grasp(Z, V8);
	pour_shot_to_used_shaker(V9, B, V8, A, D, V7);
	leave(A, V9);
	shake(Y, B, C, V8, Z, A);
	pour_shaker_to_shot(Y, X, Z, V8, V7, D).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, B) & obj_tp(B, ingredient) & B \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(V8, C) & obj_tp(V8, shaker) & ontable(V8) & unshaked(V8) & contains(V9, B) & obj_tp(V9, shot) & V8 \== V9 & holding(Z, V9) & obj_tp(Z, hand) & shaker_level(V8, D) & obj_tp(D, level) & next(D, V7) & obj_tp(V7, level) & D \== V7 & handempty(A) & obj_tp(A, hand) & A \== Z <-
	pour_shot_to_used_shaker(V9, B, V8, Z, D, V7);
	leave(Z, V9);
	grasp(Z, V8);
	shake(Y, B, C, V8, Z, A);
	pour_shaker_to_shot(Y, X, Z, V8, V7, D).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & cocktail_part1(Y, B) & obj_tp(B, ingredient) & B \== Y & used(X, B) & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(V8, B) & obj_tp(V8, shaker) & V8 \== X & contains(V8, C) & ontable(V8) & unshaked(V8) & holding(Z, X) & obj_tp(Z, hand) & shaker_level(V8, D) & obj_tp(D, level) & next(V7, D) & obj_tp(V7, level) & handempty(A) & obj_tp(A, hand) & A \== Z <-
	clean_shot(X, B, Z, A);
	leave(Z, X);
	grasp(Z, V8);
	shake(Y, B, C, V8, Z, A);
	pour_shaker_to_shot(Y, X, Z, V8, D, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & cocktail_part1(Y, C) & obj_tp(C, ingredient) & C \== Y & cocktail_part2(Y, B) & obj_tp(B, ingredient) & B \== Y & used(X, B) & contains(V8, B) & obj_tp(V8, shaker) & contains(V8, C) & ontable(V8) & unshaked(V8) & holding(Z, X) & obj_tp(Z, hand) & shaker_level(V8, D) & obj_tp(D, level) & next(V7, D) & obj_tp(V7, level) & handempty(A) & obj_tp(A, hand) & A \== Z <-
	clean_shot(X, B, Z, A);
	grasp(A, V8);
	leave(Z, X);
	shake(Y, C, B, V8, A, Z);
	pour_shaker_to_shot(Y, X, A, V8, D, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & cocktail_part1(Y, B) & obj_tp(B, ingredient) & B \== Y & used(X, B) & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(V8, B) & obj_tp(V8, shaker) & contains(V8, C) & ontable(V8) & unshaked(V8) & holding(Z, X) & obj_tp(Z, hand) & shaker_level(V8, D) & obj_tp(D, level) & next(V7, D) & obj_tp(V7, level) & handempty(A) & obj_tp(A, hand) & A \== Z <-
	clean_shot(X, B, Z, A);
	grasp(A, V8);
	leave(Z, X);
	shake(Y, B, C, V8, A, Z);
	pour_shaker_to_shot(Y, X, A, V8, D, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & cocktail_part1(Y, C) & obj_tp(C, ingredient) & C \== Y & cocktail_part2(Y, B) & obj_tp(B, ingredient) & B \== Y & used(X, B) & contains(V8, B) & obj_tp(V8, shaker) & V8 \== X & contains(V8, C) & ontable(V8) & unshaked(V8) & holding(Z, X) & obj_tp(Z, hand) & shaker_level(V8, D) & obj_tp(D, level) & next(V7, D) & obj_tp(V7, level) & handempty(A) & obj_tp(A, hand) & A \== Z <-
	clean_shot(X, B, Z, A);
	leave(Z, X);
	grasp(Z, V8);
	shake(Y, C, B, V8, Z, A);
	pour_shaker_to_shot(Y, X, Z, V8, D, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(V9, D) & obj_tp(V9, shaker) & ontable(V9) & unshaked(V9) & dispenses(Z, C) & obj_tp(Z, dispenser) & shaker_level(V9, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & clean(V10) & obj_tp(V10, shot) & V10 \== V9 & V10 \== X & empty(V10) & holding(A, V10) & obj_tp(A, hand) & handempty(B) & obj_tp(B, hand) & A \== B <-
	fill_shot(V10, C, A, B, Z);
	grasp(B, V9);
	pour_shot_to_used_shaker(V10, C, V9, A, V7, V8);
	leave(A, V10);
	shake(Y, D, C, V9, B, A);
	pour_shaker_to_shot(Y, X, B, V9, V8, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, C) & obj_tp(C, ingredient) & C \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== Y & contains(V9, D) & obj_tp(V9, shaker) & ontable(V9) & unshaked(V9) & dispenses(Z, C) & obj_tp(Z, dispenser) & shaker_level(V9, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & clean(V10) & obj_tp(V10, shot) & V10 \== V9 & V10 \== X & empty(V10) & holding(A, V10) & obj_tp(A, hand) & handempty(B) & obj_tp(B, hand) & A \== B <-
	fill_shot(V10, C, A, B, Z);
	grasp(B, V9);
	pour_shot_to_used_shaker(V10, C, V9, A, V7, V8);
	leave(A, V10);
	shake(Y, C, D, V9, B, A);
	pour_shaker_to_shot(Y, X, B, V9, V8, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & cocktail_part1(Y, B) & obj_tp(B, ingredient) & B \== Y & contains(X, B) & used(X, B) & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(V8, C) & obj_tp(V8, shaker) & V8 \== X & ontable(V8) & unshaked(V8) & holding(Z, X) & obj_tp(Z, hand) & shaker_level(V8, D) & obj_tp(D, level) & next(D, V7) & obj_tp(V7, level) & D \== V7 & handempty(A) & obj_tp(A, hand) & A \== Z <-
	pour_shot_to_used_shaker(X, B, V8, Z, D, V7);
	clean_shot(X, B, Z, A);
	leave(Z, X);
	grasp(Z, V8);
	shake(Y, B, C, V8, Z, A);
	pour_shaker_to_shot(Y, X, Z, V8, V7, D).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & cocktail_part1(Y, C) & obj_tp(C, ingredient) & C \== Y & cocktail_part2(Y, B) & obj_tp(B, ingredient) & B \== Y & contains(X, B) & used(X, B) & contains(V8, C) & obj_tp(V8, shaker) & V8 \== X & ontable(V8) & unshaked(V8) & holding(Z, X) & obj_tp(Z, hand) & shaker_level(V8, D) & obj_tp(D, level) & next(D, V7) & obj_tp(V7, level) & D \== V7 & handempty(A) & obj_tp(A, hand) & A \== Z <-
	pour_shot_to_used_shaker(X, B, V8, Z, D, V7);
	clean_shot(X, B, Z, A);
	grasp(A, V8);
	leave(Z, X);
	shake(Y, C, B, V8, A, Z);
	pour_shaker_to_shot(Y, X, A, V8, V7, D).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(V9, D) & obj_tp(V9, shaker) & ontable(V9) & unshaked(V9) & dispenses(Z, C) & obj_tp(Z, dispenser) & shaker_level(V9, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & clean(V10) & obj_tp(V10, shot) & V10 \== V9 & V10 \== X & empty(V10) & holding(A, V10) & obj_tp(A, hand) & handempty(B) & obj_tp(B, hand) & A \== B <-
	fill_shot(V10, C, A, B, Z);
	pour_shot_to_used_shaker(V10, C, V9, A, V7, V8);
	leave(A, V10);
	grasp(A, V9);
	shake(Y, D, C, V9, A, B);
	pour_shaker_to_shot(Y, X, A, V9, V8, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, C) & obj_tp(C, ingredient) & C \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== Y & contains(V9, D) & obj_tp(V9, shaker) & ontable(V9) & unshaked(V9) & dispenses(Z, C) & obj_tp(Z, dispenser) & shaker_level(V9, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & clean(V10) & obj_tp(V10, shot) & V10 \== V9 & V10 \== X & empty(V10) & holding(A, V10) & obj_tp(A, hand) & handempty(B) & obj_tp(B, hand) & A \== B <-
	fill_shot(V10, C, A, B, Z);
	pour_shot_to_used_shaker(V10, C, V9, A, V7, V8);
	leave(A, V10);
	grasp(A, V9);
	shake(Y, C, D, V9, A, B);
	pour_shaker_to_shot(Y, X, A, V9, V8, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & cocktail_part1(Y, B) & obj_tp(B, ingredient) & B \== Y & contains(X, B) & used(X, B) & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(V8, C) & obj_tp(V8, shaker) & V8 \== X & ontable(V8) & unshaked(V8) & holding(Z, X) & obj_tp(Z, hand) & shaker_level(V8, D) & obj_tp(D, level) & next(D, V7) & obj_tp(V7, level) & D \== V7 & handempty(A) & obj_tp(A, hand) & A \== Z <-
	pour_shot_to_used_shaker(X, B, V8, Z, D, V7);
	clean_shot(X, B, Z, A);
	grasp(A, V8);
	leave(Z, X);
	shake(Y, B, C, V8, A, Z);
	pour_shaker_to_shot(Y, X, A, V8, V7, D).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & cocktail_part1(Y, C) & obj_tp(C, ingredient) & C \== Y & cocktail_part2(Y, B) & obj_tp(B, ingredient) & B \== Y & contains(X, B) & used(X, B) & contains(V8, C) & obj_tp(V8, shaker) & V8 \== X & ontable(V8) & unshaked(V8) & holding(Z, X) & obj_tp(Z, hand) & shaker_level(V8, D) & obj_tp(D, level) & next(D, V7) & obj_tp(V7, level) & D \== V7 & handempty(A) & obj_tp(A, hand) & A \== Z <-
	pour_shot_to_used_shaker(X, B, V8, Z, D, V7);
	clean_shot(X, B, Z, A);
	leave(Z, X);
	grasp(Z, V8);
	shake(Y, C, B, V8, Z, A);
	pour_shaker_to_shot(Y, X, Z, V8, V7, D).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(V9, C) & obj_tp(V9, shaker) & ontable(V9) & unshaked(V9) & dispenses(Z, D) & obj_tp(Z, dispenser) & shaker_level(V9, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & used(V10, C) & obj_tp(V10, shot) & V10 \== V9 & V10 \== X & empty(V10) & holding(A, V10) & obj_tp(A, hand) & handempty(B) & obj_tp(B, hand) & A \== B <-
	clean_shot(V10, C, A, B);
	fill_shot(V10, D, A, B, Z);
	grasp(B, V9);
	pour_shot_to_used_shaker(V10, D, V9, A, V7, V8);
	leave(A, V10);
	shake(Y, D, C, V9, B, A);
	pour_shaker_to_shot(Y, X, B, V9, V8, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(V9, D) & obj_tp(V9, shaker) & V9 \== X & ontable(V9) & unshaked(V9) & dispenses(Z, C) & obj_tp(Z, dispenser) & holding(A, X) & obj_tp(A, hand) & shaker_level(V9, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & handempty(B) & obj_tp(B, hand) & A \== B <-
	fill_shot(X, C, A, B, Z);
	pour_shot_to_used_shaker(X, C, V9, A, V7, V8);
	clean_shot(X, C, A, B);
	grasp(B, V9);
	leave(A, X);
	shake(Y, D, C, V9, B, A);
	pour_shaker_to_shot(Y, X, B, V9, V8, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, C) & obj_tp(C, ingredient) & C \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== Y & contains(V9, C) & obj_tp(V9, shaker) & ontable(V9) & unshaked(V9) & dispenses(Z, D) & obj_tp(Z, dispenser) & shaker_level(V9, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & used(V10, C) & obj_tp(V10, shot) & V10 \== V9 & V10 \== X & empty(V10) & holding(A, V10) & obj_tp(A, hand) & handempty(B) & obj_tp(B, hand) & A \== B <-
	clean_shot(V10, C, A, B);
	fill_shot(V10, D, A, B, Z);
	pour_shot_to_used_shaker(V10, D, V9, A, V7, V8);
	leave(A, V10);
	grasp(A, V9);
	shake(Y, C, D, V9, A, B);
	pour_shaker_to_shot(Y, X, A, V9, V8, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, C) & obj_tp(C, ingredient) & C \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== Y & contains(V9, C) & obj_tp(V9, shaker) & ontable(V9) & unshaked(V9) & dispenses(Z, D) & obj_tp(Z, dispenser) & shaker_level(V9, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & used(V10, C) & obj_tp(V10, shot) & V10 \== V9 & V10 \== X & empty(V10) & holding(A, V10) & obj_tp(A, hand) & handempty(B) & obj_tp(B, hand) & A \== B <-
	clean_shot(V10, C, A, B);
	fill_shot(V10, D, A, B, Z);
	grasp(B, V9);
	pour_shot_to_used_shaker(V10, D, V9, A, V7, V8);
	leave(A, V10);
	shake(Y, C, D, V9, B, A);
	pour_shaker_to_shot(Y, X, B, V9, V8, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, C) & obj_tp(C, ingredient) & C \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== Y & contains(V9, D) & obj_tp(V9, shaker) & V9 \== X & ontable(V9) & unshaked(V9) & dispenses(Z, C) & obj_tp(Z, dispenser) & holding(A, X) & obj_tp(A, hand) & shaker_level(V9, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & handempty(B) & obj_tp(B, hand) & A \== B <-
	fill_shot(X, C, A, B, Z);
	pour_shot_to_used_shaker(X, C, V9, A, V7, V8);
	clean_shot(X, C, A, B);
	leave(A, X);
	grasp(A, V9);
	shake(Y, C, D, V9, A, B);
	pour_shaker_to_shot(Y, X, A, V9, V8, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, C) & obj_tp(C, ingredient) & C \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== Y & contains(V9, D) & obj_tp(V9, shaker) & V9 \== X & ontable(V9) & unshaked(V9) & dispenses(Z, C) & obj_tp(Z, dispenser) & holding(A, X) & obj_tp(A, hand) & shaker_level(V9, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & handempty(B) & obj_tp(B, hand) & A \== B <-
	fill_shot(X, C, A, B, Z);
	pour_shot_to_used_shaker(X, C, V9, A, V7, V8);
	clean_shot(X, C, A, B);
	grasp(B, V9);
	leave(A, X);
	shake(Y, C, D, V9, B, A);
	pour_shaker_to_shot(Y, X, B, V9, V8, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(V9, D) & obj_tp(V9, shaker) & V9 \== X & ontable(V9) & unshaked(V9) & dispenses(Z, C) & obj_tp(Z, dispenser) & holding(A, X) & obj_tp(A, hand) & shaker_level(V9, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & handempty(B) & obj_tp(B, hand) & A \== B <-
	fill_shot(X, C, A, B, Z);
	pour_shot_to_used_shaker(X, C, V9, A, V7, V8);
	clean_shot(X, C, A, B);
	leave(A, X);
	grasp(A, V9);
	shake(Y, D, C, V9, A, B);
	pour_shaker_to_shot(Y, X, A, V9, V8, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(V9, C) & obj_tp(V9, shaker) & ontable(V9) & unshaked(V9) & dispenses(Z, D) & obj_tp(Z, dispenser) & shaker_level(V9, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & used(V10, C) & obj_tp(V10, shot) & V10 \== V9 & V10 \== X & empty(V10) & holding(A, V10) & obj_tp(A, hand) & handempty(B) & obj_tp(B, hand) & A \== B <-
	clean_shot(V10, C, A, B);
	fill_shot(V10, D, A, B, Z);
	pour_shot_to_used_shaker(V10, D, V9, A, V7, V8);
	leave(A, V10);
	grasp(A, V9);
	shake(Y, D, C, V9, A, B);
	pour_shaker_to_shot(Y, X, A, V9, V8, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== D & C \== Y & used(X, C) & contains(V9, C) & obj_tp(V9, shaker) & V9 \== X & ontable(V9) & unshaked(V9) & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(A, X) & obj_tp(A, hand) & shaker_level(V9, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & handempty(B) & obj_tp(B, hand) & A \== B <-
	clean_shot(X, C, A, B);
	fill_shot(X, D, A, B, Z);
	pour_shot_to_used_shaker(X, D, V9, A, V7, V8);
	clean_shot(X, D, A, B);
	grasp(B, V9);
	leave(A, X);
	shake(Y, D, C, V9, B, A);
	pour_shaker_to_shot(Y, X, B, V9, V8, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, C) & obj_tp(C, ingredient) & C \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & C \== D & D \== Y & contains(V11, C) & obj_tp(V11, shot) & V11 \== X & used(V11, C) & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(A, V11) & obj_tp(A, hand) & clean(V10) & obj_tp(V10, shaker) & V10 \== V11 & V10 \== X & empty(V10) & ontable(V10) & shaker_level(V10, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & next(V8, V9) & obj_tp(V9, level) & V7 \== V9 & V8 \== V9 & handempty(B) & obj_tp(B, hand) & A \== B <-
	pour_shot_to_clean_shaker(V11, C, V10, A, V7, V8);
	clean_shot(V11, C, A, B);
	fill_shot(V11, D, A, B, Z);
	pour_shot_to_used_shaker(V11, D, V10, A, V8, V9);
	leave(A, V11);
	grasp(A, V10);
	shake(Y, C, D, V10, A, B);
	pour_shaker_to_shot(Y, X, A, V10, V9, V8).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== D & C \== Y & contains(V11, C) & obj_tp(V11, shot) & V11 \== X & used(V11, C) & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(A, V11) & obj_tp(A, hand) & clean(V10) & obj_tp(V10, shaker) & V10 \== V11 & V10 \== X & empty(V10) & ontable(V10) & shaker_level(V10, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & next(V8, V9) & obj_tp(V9, level) & V7 \== V9 & V8 \== V9 & handempty(B) & obj_tp(B, hand) & A \== B <-
	pour_shot_to_clean_shaker(V11, C, V10, A, V7, V8);
	clean_shot(V11, C, A, B);
	fill_shot(V11, D, A, B, Z);
	grasp(B, V10);
	pour_shot_to_used_shaker(V11, D, V10, A, V8, V9);
	leave(A, V11);
	shake(Y, D, C, V10, B, A);
	pour_shaker_to_shot(Y, X, B, V10, V9, V8).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== D & C \== Y & used(X, C) & contains(V9, C) & obj_tp(V9, shaker) & V9 \== X & ontable(V9) & unshaked(V9) & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(A, X) & obj_tp(A, hand) & shaker_level(V9, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & handempty(B) & obj_tp(B, hand) & A \== B <-
	clean_shot(X, C, A, B);
	fill_shot(X, D, A, B, Z);
	pour_shot_to_used_shaker(X, D, V9, A, V7, V8);
	clean_shot(X, D, A, B);
	leave(A, X);
	grasp(A, V9);
	shake(Y, D, C, V9, A, B);
	pour_shaker_to_shot(Y, X, A, V9, V8, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== D & C \== Y & contains(V11, C) & obj_tp(V11, shot) & V11 \== X & used(V11, C) & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(A, V11) & obj_tp(A, hand) & clean(V10) & obj_tp(V10, shaker) & V10 \== V11 & V10 \== X & empty(V10) & ontable(V10) & shaker_level(V10, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & next(V8, V9) & obj_tp(V9, level) & V7 \== V9 & V8 \== V9 & handempty(B) & obj_tp(B, hand) & A \== B <-
	pour_shot_to_clean_shaker(V11, C, V10, A, V7, V8);
	clean_shot(V11, C, A, B);
	fill_shot(V11, D, A, B, Z);
	pour_shot_to_used_shaker(V11, D, V10, A, V8, V9);
	leave(A, V11);
	grasp(A, V10);
	shake(Y, D, C, V10, A, B);
	pour_shaker_to_shot(Y, X, A, V10, V9, V8).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & cocktail_part1(Y, C) & obj_tp(C, ingredient) & C \== Y & used(X, C) & cocktail_part2(Y, D) & obj_tp(D, ingredient) & C \== D & D \== Y & contains(V9, C) & obj_tp(V9, shaker) & V9 \== X & ontable(V9) & unshaked(V9) & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(A, X) & obj_tp(A, hand) & shaker_level(V9, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & handempty(B) & obj_tp(B, hand) & A \== B <-
	clean_shot(X, C, A, B);
	fill_shot(X, D, A, B, Z);
	pour_shot_to_used_shaker(X, D, V9, A, V7, V8);
	clean_shot(X, D, A, B);
	leave(A, X);
	grasp(A, V9);
	shake(Y, C, D, V9, A, B);
	pour_shaker_to_shot(Y, X, A, V9, V8, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & cocktail_part1(Y, C) & obj_tp(C, ingredient) & C \== Y & used(X, C) & cocktail_part2(Y, D) & obj_tp(D, ingredient) & C \== D & D \== Y & contains(V9, C) & obj_tp(V9, shaker) & V9 \== X & ontable(V9) & unshaked(V9) & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(A, X) & obj_tp(A, hand) & shaker_level(V9, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & handempty(B) & obj_tp(B, hand) & A \== B <-
	clean_shot(X, C, A, B);
	fill_shot(X, D, A, B, Z);
	pour_shot_to_used_shaker(X, D, V9, A, V7, V8);
	clean_shot(X, D, A, B);
	grasp(B, V9);
	leave(A, X);
	shake(Y, C, D, V9, B, A);
	pour_shaker_to_shot(Y, X, B, V9, V8, V7).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, C) & obj_tp(C, ingredient) & C \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & C \== D & D \== Y & contains(V11, C) & obj_tp(V11, shot) & V11 \== X & used(V11, C) & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(A, V11) & obj_tp(A, hand) & clean(V10) & obj_tp(V10, shaker) & V10 \== V11 & V10 \== X & empty(V10) & ontable(V10) & shaker_level(V10, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & next(V8, V9) & obj_tp(V9, level) & V7 \== V9 & V8 \== V9 & handempty(B) & obj_tp(B, hand) & A \== B <-
	pour_shot_to_clean_shaker(V11, C, V10, A, V7, V8);
	clean_shot(V11, C, A, B);
	fill_shot(V11, D, A, B, Z);
	grasp(B, V10);
	pour_shot_to_used_shaker(V11, D, V10, A, V8, V9);
	leave(A, V11);
	shake(Y, C, D, V10, B, A);
	pour_shaker_to_shot(Y, X, B, V10, V9, V8).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & used(V12, D) & obj_tp(V12, shot) & V12 \== X & empty(V12) & holding(B, V12) & obj_tp(B, hand) & clean(V11) & obj_tp(V11, shaker) & V11 \== V12 & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	refill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	grasp(B, V11);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & cocktail_part1(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(X, C) & used(X, C) & cocktail_part2(Y, D) & obj_tp(D, ingredient) & C \== D & D \== Y & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(A, X) & obj_tp(A, hand) & clean(V10) & obj_tp(V10, shaker) & V10 \== X & empty(V10) & ontable(V10) & shaker_level(V10, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & next(V8, V9) & obj_tp(V9, level) & V7 \== V9 & V8 \== V9 & handempty(B) & obj_tp(B, hand) & A \== B <-
	pour_shot_to_clean_shaker(X, C, V10, A, V7, V8);
	clean_shot(X, C, A, B);
	fill_shot(X, D, A, B, Z);
	pour_shot_to_used_shaker(X, D, V10, A, V8, V9);
	clean_shot(X, D, A, B);
	leave(A, X);
	grasp(A, V10);
	shake(Y, C, D, V10, A, B);
	pour_shaker_to_shot(Y, X, A, V10, V9, V8).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & used(V12, D) & obj_tp(V12, shot) & V12 \== X & empty(V12) & holding(B, V12) & obj_tp(B, hand) & clean(V11) & obj_tp(V11, shaker) & V11 \== V12 & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	refill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	grasp(B, V11);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & cocktail_part1(Y, C) & obj_tp(C, ingredient) & C \== Y & contains(X, C) & used(X, C) & cocktail_part2(Y, D) & obj_tp(D, ingredient) & C \== D & D \== Y & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(A, X) & obj_tp(A, hand) & clean(V10) & obj_tp(V10, shaker) & V10 \== X & empty(V10) & ontable(V10) & shaker_level(V10, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & next(V8, V9) & obj_tp(V9, level) & V7 \== V9 & V8 \== V9 & handempty(B) & obj_tp(B, hand) & A \== B <-
	pour_shot_to_clean_shaker(X, C, V10, A, V7, V8);
	clean_shot(X, C, A, B);
	fill_shot(X, D, A, B, Z);
	pour_shot_to_used_shaker(X, D, V10, A, V8, V9);
	clean_shot(X, D, A, B);
	grasp(B, V10);
	leave(A, X);
	shake(Y, C, D, V10, B, A);
	pour_shaker_to_shot(Y, X, B, V10, V9, V8).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & clean(V12) & obj_tp(V12, shot) & V11 \== V12 & V12 \== X & empty(V12) & holding(B, V12) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	fill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	grasp(C, V11);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	shake(Y, D, V7, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & used(V12, D) & obj_tp(V12, shot) & V12 \== X & empty(V12) & holding(B, V12) & obj_tp(B, hand) & clean(V11) & obj_tp(V11, shaker) & V11 \== V12 & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	refill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	grasp(C, V11);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	shake(Y, V7, D, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & clean(V12) & obj_tp(V12, shot) & V11 \== V12 & V12 \== X & empty(V12) & holding(B, V12) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	fill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	grasp(B, V11);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & clean(V12) & obj_tp(V12, shot) & V11 \== V12 & V12 \== X & empty(V12) & holding(B, V12) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	fill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	grasp(C, V11);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	shake(Y, V7, D, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== D & C \== Y & contains(X, C) & used(X, C) & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(A, X) & obj_tp(A, hand) & clean(V10) & obj_tp(V10, shaker) & V10 \== X & empty(V10) & ontable(V10) & shaker_level(V10, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & next(V8, V9) & obj_tp(V9, level) & V7 \== V9 & V8 \== V9 & handempty(B) & obj_tp(B, hand) & A \== B <-
	pour_shot_to_clean_shaker(X, C, V10, A, V7, V8);
	clean_shot(X, C, A, B);
	fill_shot(X, D, A, B, Z);
	pour_shot_to_used_shaker(X, D, V10, A, V8, V9);
	clean_shot(X, D, A, B);
	grasp(B, V10);
	leave(A, X);
	shake(Y, D, C, V10, B, A);
	pour_shaker_to_shot(Y, X, B, V10, V9, V8).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & clean(V12) & obj_tp(V12, shot) & V11 \== V12 & V12 \== X & empty(V12) & holding(B, V12) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	fill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	grasp(B, V11);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & used(V12, D) & obj_tp(V12, shot) & V12 \== X & empty(V12) & holding(B, V12) & obj_tp(B, hand) & clean(V11) & obj_tp(V11, shaker) & V11 \== V12 & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	refill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	grasp(C, V11);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	shake(Y, D, V7, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, C) & obj_tp(C, ingredient) & C \== D & C \== Y & contains(X, C) & used(X, C) & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(A, X) & obj_tp(A, hand) & clean(V10) & obj_tp(V10, shaker) & V10 \== X & empty(V10) & ontable(V10) & shaker_level(V10, V7) & obj_tp(V7, level) & next(V7, V8) & obj_tp(V8, level) & V7 \== V8 & next(V8, V9) & obj_tp(V9, level) & V7 \== V9 & V8 \== V9 & handempty(B) & obj_tp(B, hand) & A \== B <-
	pour_shot_to_clean_shaker(X, C, V10, A, V7, V8);
	clean_shot(X, C, A, B);
	fill_shot(X, D, A, B, Z);
	pour_shot_to_used_shaker(X, D, V10, A, V8, V9);
	clean_shot(X, D, A, B);
	leave(A, X);
	grasp(A, V10);
	shake(Y, D, C, V10, A, B);
	pour_shaker_to_shot(Y, X, A, V10, V9, V8).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & used(X, D) & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(B, X) & obj_tp(B, hand) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	refill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	leave(B, X);
	grasp(B, V11);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & clean(V12) & obj_tp(V12, shaker) & V12 \== X & empty(V12) & ontable(V12) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & empty(V13) & obj_tp(V13, shot) & V12 \== V13 & V13 \== X & holding(B, V13) & obj_tp(B, hand) & used(V13, D) & obj_tp(D, beverage) & D \== V7 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shot(V13, D, B, C);
	fill_shot(V13, V7, B, C, Z);
	pour_shot_to_clean_shaker(V13, V7, V12, B, V9, V10);
	clean_shot(V13, V7, B, C);
	fill_shot(V13, V8, B, C, A);
	grasp(C, V12);
	pour_shot_to_used_shaker(V13, V8, V12, B, V10, V11);
	leave(B, V13);
	shake(Y, V7, V8, V12, C, B);
	pour_shaker_to_shot(Y, X, C, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & clean(V12) & obj_tp(V12, shot) & V11 \== V12 & V12 \== X & empty(V12) & ontable(V12) & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, V12);
	fill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	grasp(B, V11);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & used(V12, D) & obj_tp(V12, shot) & V12 \== X & empty(V12) & ontable(V12) & clean(V11) & obj_tp(V11, shaker) & V11 \== V12 & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, V12);
	refill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	grasp(B, V11);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & clean(V12) & obj_tp(V12, shot) & V11 \== V12 & V12 \== X & empty(V12) & holding(C, V12) & obj_tp(C, hand) & B \== C <-
	leave(B, V11);
	fill_shot(V12, D, C, B, Z);
	pour_shot_to_clean_shaker(V12, D, V11, C, V8, V9);
	clean_shot(V12, D, C, B);
	fill_shot(V12, V7, C, B, A);
	grasp(B, V11);
	pour_shot_to_used_shaker(V12, V7, V11, C, V9, V10);
	leave(C, V12);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & used(V12, D) & obj_tp(V12, shot) & V12 \== X & empty(V12) & ontable(V12) & clean(V11) & obj_tp(V11, shaker) & V11 \== V12 & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, V12);
	refill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	grasp(B, V11);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & used(X, D) & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(B, X) & obj_tp(B, hand) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	refill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	grasp(C, V11);
	leave(B, X);
	shake(Y, D, V7, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & clean(V12) & obj_tp(V12, shot) & V11 \== V12 & V12 \== X & empty(V12) & holding(C, V12) & obj_tp(C, hand) & B \== C <-
	leave(B, V11);
	fill_shot(V12, D, C, B, Z);
	pour_shot_to_clean_shaker(V12, D, V11, C, V8, V9);
	clean_shot(V12, D, C, B);
	fill_shot(V12, V7, C, B, A);
	grasp(B, V11);
	pour_shot_to_used_shaker(V12, V7, V11, C, V9, V10);
	leave(C, V12);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & used(V12, D) & obj_tp(V12, shot) & V12 \== X & empty(V12) & ontable(V12) & clean(V11) & obj_tp(V11, shaker) & V11 \== V12 & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, V12);
	refill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	grasp(C, V11);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	shake(Y, D, V7, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(B, X) & obj_tp(B, hand) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	fill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	leave(B, X);
	grasp(B, V11);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & clean(V12) & obj_tp(V12, shot) & V11 \== V12 & V12 \== X & empty(V12) & ontable(V12) & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, V12);
	fill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	grasp(C, V11);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	shake(Y, D, V7, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & clean(V12) & obj_tp(V12, shot) & V11 \== V12 & V12 \== X & empty(V12) & ontable(V12) & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, V12);
	fill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	grasp(B, V11);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & used(V12, D) & obj_tp(V12, shot) & V12 \== X & empty(V12) & ontable(V12) & clean(V11) & obj_tp(V11, shaker) & V11 \== V12 & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, V12);
	refill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	grasp(C, V11);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	shake(Y, V7, D, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(B, X) & obj_tp(B, hand) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	fill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	leave(B, X);
	grasp(B, V11);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & used(X, D) & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(B, X) & obj_tp(B, hand) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	refill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	grasp(C, V11);
	leave(B, X);
	shake(Y, V7, D, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(B, X) & obj_tp(B, hand) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	fill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	grasp(C, V11);
	leave(B, X);
	shake(Y, V7, D, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(B, X) & obj_tp(B, hand) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	fill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	grasp(C, V11);
	leave(B, X);
	shake(Y, D, V7, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & clean(V12) & obj_tp(V12, shot) & V11 \== V12 & V12 \== X & empty(V12) & ontable(V12) & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, V12);
	fill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	grasp(C, V11);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	shake(Y, V7, D, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & used(X, D) & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(B, X) & obj_tp(B, hand) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	refill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	leave(B, X);
	grasp(B, V11);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & used(X, D) & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(C, X) & obj_tp(C, hand) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & holding(B, V11) & obj_tp(B, hand) & B \== C & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 <-
	leave(B, V11);
	refill_shot(X, D, C, B, Z);
	pour_shot_to_clean_shaker(X, D, V11, C, V8, V9);
	clean_shot(X, D, C, B);
	fill_shot(X, V7, C, B, A);
	pour_shot_to_used_shaker(X, V7, V11, C, V9, V10);
	clean_shot(X, V7, C, B);
	grasp(B, V11);
	leave(C, X);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & used(V12, D) & obj_tp(V12, shot) & V12 \== X & empty(V12) & ontable(V12) & clean(V11) & obj_tp(V11, shaker) & V11 \== V12 & V11 \== X & empty(V11) & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	leave(B, V11);
	grasp(B, V12);
	refill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	grasp(B, V11);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & used(V12, D) & obj_tp(V12, shot) & V12 \== X & empty(V12) & ontable(V12) & clean(V11) & obj_tp(V11, shaker) & V11 \== V12 & V11 \== X & empty(V11) & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	leave(B, V11);
	grasp(C, V12);
	refill_shot(V12, D, C, B, Z);
	pour_shot_to_clean_shaker(V12, D, V11, C, V8, V9);
	clean_shot(V12, D, C, B);
	fill_shot(V12, V7, C, B, A);
	grasp(B, V11);
	pour_shot_to_used_shaker(V12, V7, V11, C, V9, V10);
	leave(C, V12);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & clean(V12) & obj_tp(V12, shaker) & V12 \== X & empty(V12) & holding(B, V12) & obj_tp(B, hand) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & empty(V13) & obj_tp(V13, shot) & V12 \== V13 & V13 \== X & holding(C, V13) & obj_tp(C, hand) & B \== C & used(V13, D) & obj_tp(D, beverage) & D \== V7 <-
	leave(B, V12);
	clean_shot(V13, D, C, B);
	fill_shot(V13, V7, C, B, Z);
	pour_shot_to_clean_shaker(V13, V7, V12, C, V9, V10);
	clean_shot(V13, V7, C, B);
	fill_shot(V13, V8, C, B, A);
	grasp(B, V12);
	pour_shot_to_used_shaker(V13, V8, V12, C, V10, V11);
	leave(C, V13);
	shake(Y, V7, V8, V12, B, C);
	pour_shaker_to_shot(Y, X, B, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(C, X) & obj_tp(C, hand) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & holding(B, V11) & obj_tp(B, hand) & B \== C & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 <-
	leave(B, V11);
	fill_shot(X, D, C, B, Z);
	pour_shot_to_clean_shaker(X, D, V11, C, V8, V9);
	clean_shot(X, D, C, B);
	fill_shot(X, V7, C, B, A);
	pour_shot_to_used_shaker(X, V7, V11, C, V9, V10);
	clean_shot(X, V7, C, B);
	grasp(B, V11);
	leave(C, X);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & ontable(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, X);
	fill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	grasp(C, V11);
	leave(B, X);
	shake(Y, D, V7, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & used(X, D) & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, X);
	refill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	leave(B, X);
	grasp(B, V11);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & used(V12, D) & obj_tp(V12, shot) & V12 \== X & empty(V12) & ontable(V12) & clean(V11) & obj_tp(V11, shaker) & V11 \== V12 & V11 \== X & empty(V11) & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	leave(B, V11);
	grasp(B, V12);
	refill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	grasp(B, V11);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & clean(V12) & obj_tp(V12, shot) & V11 \== V12 & V12 \== X & empty(V12) & ontable(V12) & handempty(C) & obj_tp(C, hand) & B \== C <-
	leave(B, V11);
	grasp(C, V12);
	fill_shot(V12, D, C, B, Z);
	pour_shot_to_clean_shaker(V12, D, V11, C, V8, V9);
	clean_shot(V12, D, C, B);
	fill_shot(V12, V7, C, B, A);
	grasp(B, V11);
	pour_shot_to_used_shaker(V12, V7, V11, C, V9, V10);
	leave(C, V12);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & used(X, D) & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & holding(C, X) & obj_tp(C, hand) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & holding(B, V11) & obj_tp(B, hand) & B \== C & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 <-
	leave(B, V11);
	refill_shot(X, D, C, B, Z);
	pour_shot_to_clean_shaker(X, D, V11, C, V8, V9);
	clean_shot(X, D, C, B);
	fill_shot(X, V7, C, B, A);
	pour_shot_to_used_shaker(X, V7, V11, C, V9, V10);
	clean_shot(X, V7, C, B);
	grasp(B, V11);
	leave(C, X);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & holding(C, V11) & obj_tp(C, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & clean(V12) & obj_tp(V12, shot) & V11 \== V12 & V12 \== X & empty(V12) & ontable(V12) & handempty(B) & obj_tp(B, hand) & B \== C <-
	grasp(B, V12);
	leave(C, V11);
	fill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	grasp(C, V11);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	shake(Y, D, V7, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & V7 \== V8 & V7 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & holding(B, X) & obj_tp(B, hand) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & clean(V12) & obj_tp(V12, shaker) & V12 \== X & empty(V12) & ontable(V12) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, Z);
	pour_shot_to_clean_shaker(X, V7, V12, B, V9, V10);
	clean_shot(X, V7, B, C);
	fill_shot(X, V8, B, C, A);
	pour_shot_to_used_shaker(X, V8, V12, B, V10, V11);
	clean_shot(X, V8, B, C);
	grasp(C, V12);
	leave(B, X);
	shake(Y, V8, V7, V12, C, B);
	pour_shaker_to_shot(Y, X, C, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, X);
	fill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	grasp(C, V11);
	leave(B, X);
	shake(Y, V7, D, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & used(V12, D) & obj_tp(V12, shot) & V12 \== X & empty(V12) & ontable(V12) & clean(V11) & obj_tp(V11, shaker) & V11 \== V12 & V11 \== X & empty(V11) & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	leave(B, V11);
	grasp(C, V12);
	refill_shot(V12, D, C, B, Z);
	pour_shot_to_clean_shaker(V12, D, V11, C, V8, V9);
	clean_shot(V12, D, C, B);
	fill_shot(V12, V7, C, B, A);
	grasp(B, V11);
	pour_shot_to_used_shaker(V12, V7, V11, C, V9, V10);
	leave(C, V12);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & ontable(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, X);
	fill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	leave(B, X);
	grasp(B, V11);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & holding(B, X) & obj_tp(B, hand) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & clean(V12) & obj_tp(V12, shaker) & V12 \== X & empty(V12) & ontable(V12) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, Z);
	pour_shot_to_clean_shaker(X, V7, V12, B, V9, V10);
	clean_shot(X, V7, B, C);
	fill_shot(X, V8, B, C, A);
	pour_shot_to_used_shaker(X, V8, V12, B, V10, V11);
	clean_shot(X, V8, B, C);
	grasp(C, V12);
	leave(B, X);
	shake(Y, V7, V8, V12, C, B);
	pour_shaker_to_shot(Y, X, C, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & used(X, D) & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, X);
	refill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	leave(B, X);
	grasp(B, V11);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & holding(C, V11) & obj_tp(C, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & clean(V12) & obj_tp(V12, shot) & V11 \== V12 & V12 \== X & empty(V12) & ontable(V12) & handempty(B) & obj_tp(B, hand) & B \== C <-
	grasp(B, V12);
	leave(C, V11);
	fill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	grasp(C, V11);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	shake(Y, V7, D, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & used(X, D) & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, X);
	refill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	grasp(C, V11);
	leave(B, X);
	shake(Y, V7, D, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & holding(B, X) & obj_tp(B, hand) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & clean(V12) & obj_tp(V12, shaker) & V12 \== X & empty(V12) & ontable(V12) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, Z);
	pour_shot_to_clean_shaker(X, V7, V12, B, V9, V10);
	clean_shot(X, V7, B, C);
	fill_shot(X, V8, B, C, A);
	pour_shot_to_used_shaker(X, V8, V12, B, V10, V11);
	clean_shot(X, V8, B, C);
	leave(B, X);
	grasp(B, V12);
	shake(Y, V7, V8, V12, B, C);
	pour_shaker_to_shot(Y, X, B, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & used(X, D) & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, X);
	refill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	grasp(C, V11);
	leave(B, X);
	shake(Y, D, V7, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & ontable(V11) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, X);
	fill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	leave(B, X);
	grasp(B, V11);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & clean(V12) & obj_tp(V12, shot) & V11 \== V12 & V12 \== X & empty(V12) & ontable(V12) & handempty(C) & obj_tp(C, hand) & B \== C <-
	leave(B, V11);
	grasp(B, V12);
	fill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	grasp(C, V11);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	shake(Y, V7, D, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & V7 \== V8 & V7 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & holding(B, X) & obj_tp(B, hand) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & clean(V12) & obj_tp(V12, shaker) & V12 \== X & empty(V12) & ontable(V12) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, Z);
	pour_shot_to_clean_shaker(X, V7, V12, B, V9, V10);
	clean_shot(X, V7, B, C);
	fill_shot(X, V8, B, C, A);
	pour_shot_to_used_shaker(X, V8, V12, B, V10, V11);
	clean_shot(X, V8, B, C);
	leave(B, X);
	grasp(B, V12);
	shake(Y, V8, V7, V12, B, C);
	pour_shaker_to_shot(Y, X, B, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & clean(V12) & obj_tp(V12, shot) & V11 \== V12 & V12 \== X & empty(V12) & ontable(V12) & handempty(C) & obj_tp(C, hand) & B \== C <-
	leave(B, V11);
	grasp(C, V12);
	fill_shot(V12, D, C, B, Z);
	pour_shot_to_clean_shaker(V12, D, V11, C, V8, V9);
	clean_shot(V12, D, C, B);
	fill_shot(V12, V7, C, B, A);
	grasp(B, V11);
	pour_shot_to_used_shaker(V12, V7, V11, C, V9, V10);
	leave(C, V12);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	leave(B, V11);
	grasp(B, X);
	fill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	grasp(C, V11);
	leave(B, X);
	shake(Y, V7, D, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & V7 \== V8 & V7 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & holding(C, X) & obj_tp(C, hand) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & clean(V12) & obj_tp(V12, shaker) & V12 \== X & empty(V12) & holding(B, V12) & obj_tp(B, hand) & B \== C & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	leave(B, V12);
	clean_shot(X, D, C, B);
	fill_shot(X, V7, C, B, Z);
	pour_shot_to_clean_shaker(X, V7, V12, C, V9, V10);
	clean_shot(X, V7, C, B);
	fill_shot(X, V8, C, B, A);
	pour_shot_to_used_shaker(X, V8, V12, C, V10, V11);
	clean_shot(X, V8, C, B);
	grasp(B, V12);
	leave(C, X);
	shake(Y, V8, V7, V12, B, C);
	pour_shaker_to_shot(Y, X, B, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & clean(V12) & obj_tp(V12, shaker) & V12 \== X & empty(V12) & holding(C, V12) & obj_tp(C, hand) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & empty(V13) & obj_tp(V13, shot) & V12 \== V13 & V13 \== X & ontable(V13) & used(V13, D) & obj_tp(D, beverage) & D \== V7 & handempty(B) & obj_tp(B, hand) & B \== C <-
	grasp(B, V13);
	leave(C, V12);
	clean_shot(V13, D, B, C);
	fill_shot(V13, V7, B, C, Z);
	pour_shot_to_clean_shaker(V13, V7, V12, B, V9, V10);
	clean_shot(V13, V7, B, C);
	fill_shot(V13, V8, B, C, A);
	grasp(C, V12);
	pour_shot_to_used_shaker(V13, V8, V12, B, V10, V11);
	leave(B, V13);
	shake(Y, V7, V8, V12, C, B);
	pour_shaker_to_shot(Y, X, C, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & used(X, D) & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & holding(C, V11) & obj_tp(C, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(B) & obj_tp(B, hand) & B \== C <-
	grasp(B, X);
	leave(C, V11);
	refill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	grasp(C, V11);
	leave(B, X);
	shake(Y, V7, D, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & used(V12, D) & obj_tp(V12, shot) & V12 \== X & empty(V12) & ontable(V12) & empty(V11) & obj_tp(V11, shaker) & V11 \== V12 & V11 \== X & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V11);
	leave(B, V11);
	grasp(C, V12);
	refill_shot(V12, D, C, B, Z);
	pour_shot_to_clean_shaker(V12, D, V11, C, V8, V9);
	clean_shot(V12, D, C, B);
	fill_shot(V12, V7, C, B, A);
	grasp(B, V11);
	pour_shot_to_used_shaker(V12, V7, V11, C, V9, V10);
	leave(C, V12);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & clean(V12) & obj_tp(V12, shaker) & V12 \== X & empty(V12) & ontable(V12) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, X);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, Z);
	pour_shot_to_clean_shaker(X, V7, V12, B, V9, V10);
	clean_shot(X, V7, B, C);
	fill_shot(X, V8, B, C, A);
	pour_shot_to_used_shaker(X, V8, V12, B, V10, V11);
	clean_shot(X, V8, B, C);
	grasp(C, V12);
	leave(B, X);
	shake(Y, V7, V8, V12, C, B);
	pour_shaker_to_shot(Y, X, C, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & ontable(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	leave(B, V11);
	grasp(B, X);
	fill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	grasp(C, V11);
	leave(B, X);
	shake(Y, D, V7, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & used(X, D) & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	leave(B, V11);
	grasp(B, X);
	refill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	grasp(C, V11);
	leave(B, X);
	shake(Y, V7, D, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & used(V12, D) & obj_tp(V12, shot) & V12 \== X & empty(V12) & ontable(V12) & empty(V11) & obj_tp(V11, shaker) & V11 \== V12 & V11 \== X & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V11);
	leave(B, V11);
	grasp(B, V12);
	refill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	grasp(B, V11);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & V7 \== V8 & V7 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & clean(V12) & obj_tp(V12, shaker) & V12 \== X & empty(V12) & ontable(V12) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, X);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, Z);
	pour_shot_to_clean_shaker(X, V7, V12, B, V9, V10);
	clean_shot(X, V7, B, C);
	fill_shot(X, V8, B, C, A);
	pour_shot_to_used_shaker(X, V8, V12, B, V10, V11);
	clean_shot(X, V8, B, C);
	grasp(C, V12);
	leave(B, X);
	shake(Y, V8, V7, V12, C, B);
	pour_shaker_to_shot(Y, X, C, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & holding(C, X) & obj_tp(C, hand) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & clean(V12) & obj_tp(V12, shaker) & V12 \== X & empty(V12) & holding(B, V12) & obj_tp(B, hand) & B \== C & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	leave(B, V12);
	clean_shot(X, D, C, B);
	fill_shot(X, V7, C, B, Z);
	pour_shot_to_clean_shaker(X, V7, V12, C, V9, V10);
	clean_shot(X, V7, C, B);
	fill_shot(X, V8, C, B, A);
	pour_shot_to_used_shaker(X, V8, V12, C, V10, V11);
	clean_shot(X, V8, C, B);
	grasp(B, V12);
	leave(C, X);
	shake(Y, V7, V8, V12, B, C);
	pour_shaker_to_shot(Y, X, B, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V12) & obj_tp(V12, shot) & V12 \== X & empty(V12) & ontable(V12) & empty(V11) & obj_tp(V11, shaker) & V11 \== V12 & V11 \== X & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V11);
	leave(B, V11);
	grasp(B, V12);
	fill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	grasp(C, V11);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	shake(Y, V7, D, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & used(V12, D) & obj_tp(V12, shot) & V12 \== X & empty(V12) & ontable(V12) & empty(V11) & obj_tp(V11, shaker) & V11 \== V12 & V11 \== X & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V11);
	leave(B, V11);
	grasp(B, V12);
	refill_shot(V12, D, B, C, Z);
	pour_shot_to_clean_shaker(V12, D, V11, B, V8, V9);
	clean_shot(V12, D, B, C);
	fill_shot(V12, V7, B, C, A);
	pour_shot_to_used_shaker(V12, V7, V11, B, V9, V10);
	leave(B, V12);
	grasp(B, V11);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & V7 \== V8 & V7 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & clean(V12) & obj_tp(V12, shaker) & V12 \== X & empty(V12) & ontable(V12) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, X);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, Z);
	pour_shot_to_clean_shaker(X, V7, V12, B, V9, V10);
	clean_shot(X, V7, B, C);
	fill_shot(X, V8, B, C, A);
	pour_shot_to_used_shaker(X, V8, V12, B, V10, V11);
	clean_shot(X, V8, B, C);
	leave(B, X);
	grasp(B, V12);
	shake(Y, V8, V7, V12, B, C);
	pour_shaker_to_shot(Y, X, B, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & used(X, D) & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	leave(B, V11);
	grasp(B, X);
	refill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	leave(B, X);
	grasp(B, V11);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & used(X, D) & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & holding(C, V11) & obj_tp(C, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(B) & obj_tp(B, hand) & B \== C <-
	grasp(B, X);
	leave(C, V11);
	refill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	grasp(C, V11);
	leave(B, X);
	shake(Y, D, V7, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & used(X, D) & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	leave(B, V11);
	grasp(B, X);
	refill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	grasp(C, V11);
	leave(B, X);
	shake(Y, D, V7, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V12) & obj_tp(V12, shot) & V12 \== X & empty(V12) & ontable(V12) & empty(V11) & obj_tp(V11, shaker) & V11 \== V12 & V11 \== X & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V11);
	grasp(C, V12);
	leave(B, V11);
	fill_shot(V12, D, C, B, Z);
	pour_shot_to_clean_shaker(V12, D, V11, C, V8, V9);
	clean_shot(V12, D, C, B);
	fill_shot(V12, V7, C, B, A);
	grasp(B, V11);
	pour_shot_to_used_shaker(V12, V7, V11, C, V9, V10);
	leave(C, V12);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V12) & obj_tp(V12, shot) & V12 \== X & empty(V12) & ontable(V12) & empty(V11) & obj_tp(V11, shaker) & V11 \== V12 & V11 \== X & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V11);
	leave(B, V11);
	grasp(C, V12);
	fill_shot(V12, D, C, B, Z);
	pour_shot_to_clean_shaker(V12, D, V11, C, V8, V9);
	clean_shot(V12, D, C, B);
	fill_shot(V12, V7, C, B, A);
	grasp(B, V11);
	pour_shot_to_used_shaker(V12, V7, V11, C, V9, V10);
	leave(C, V12);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & ontable(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	leave(B, V11);
	grasp(B, X);
	fill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	leave(B, X);
	grasp(B, V11);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	leave(B, V11);
	grasp(B, X);
	fill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	leave(B, X);
	grasp(B, V11);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & used(V12, D) & obj_tp(V12, shot) & V12 \== X & empty(V12) & ontable(V12) & empty(V11) & obj_tp(V11, shaker) & V11 \== V12 & V11 \== X & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V11);
	leave(B, V11);
	grasp(C, V12);
	refill_shot(V12, D, C, B, Z);
	pour_shot_to_clean_shaker(V12, D, V11, C, V8, V9);
	clean_shot(V12, D, C, B);
	fill_shot(V12, V7, C, B, A);
	grasp(B, V11);
	pour_shot_to_used_shaker(V12, V7, V11, C, V9, V10);
	leave(C, V12);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & used(X, D) & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	leave(B, V11);
	grasp(B, X);
	refill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	leave(B, X);
	grasp(B, V11);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & clean(V12) & obj_tp(V12, shaker) & V12 \== X & empty(V12) & ontable(V12) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, X);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, Z);
	pour_shot_to_clean_shaker(X, V7, V12, B, V9, V10);
	clean_shot(X, V7, B, C);
	fill_shot(X, V8, B, C, A);
	pour_shot_to_used_shaker(X, V8, V12, B, V10, V11);
	clean_shot(X, V8, B, C);
	leave(B, X);
	grasp(B, V12);
	shake(Y, V7, V8, V12, B, C);
	pour_shaker_to_shot(Y, X, B, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V12) & obj_tp(V12, shot) & V12 \== X & empty(V12) & ontable(V12) & empty(V11) & obj_tp(V11, shaker) & V11 \== V12 & V11 \== X & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V11);
	grasp(C, V12);
	leave(B, V11);
	fill_shot(V12, D, C, B, Z);
	pour_shot_to_clean_shaker(V12, D, V11, C, V8, V9);
	clean_shot(V12, D, C, B);
	fill_shot(V12, V7, C, B, A);
	grasp(B, V11);
	pour_shot_to_used_shaker(V12, V7, V11, C, V9, V10);
	leave(C, V12);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V12) & obj_tp(V12, shot) & V12 \== X & empty(V12) & ontable(V12) & empty(V11) & obj_tp(V11, shaker) & V11 \== V12 & V11 \== X & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V11);
	leave(B, V11);
	grasp(C, V12);
	fill_shot(V12, D, C, B, Z);
	pour_shot_to_clean_shaker(V12, D, V11, C, V8, V9);
	clean_shot(V12, D, C, B);
	fill_shot(V12, V7, C, B, A);
	grasp(B, V11);
	pour_shot_to_used_shaker(V12, V7, V11, C, V9, V10);
	leave(C, V12);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & ontable(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & clean(V11) & obj_tp(V11, shaker) & V11 \== X & empty(V11) & holding(C, V11) & obj_tp(C, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(B) & obj_tp(B, hand) & B \== C <-
	grasp(B, X);
	leave(C, V11);
	fill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	grasp(C, V11);
	leave(B, X);
	shake(Y, D, V7, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & empty(V12) & obj_tp(V12, shaker) & V12 \== X & holding(B, V12) & obj_tp(B, hand) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & empty(V13) & obj_tp(V13, shot) & V12 \== V13 & V13 \== X & ontable(V13) & used(V13, D) & obj_tp(D, beverage) & D \== V7 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V12);
	grasp(C, V13);
	leave(B, V12);
	clean_shot(V13, D, C, B);
	fill_shot(V13, V7, C, B, Z);
	pour_shot_to_clean_shaker(V13, V7, V12, C, V9, V10);
	clean_shot(V13, V7, C, B);
	fill_shot(V13, V8, C, B, A);
	grasp(B, V12);
	pour_shot_to_used_shaker(V13, V8, V12, C, V10, V11);
	leave(C, V13);
	shake(Y, V7, V8, V12, B, C);
	pour_shaker_to_shot(Y, X, B, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & clean(V12) & obj_tp(V12, shaker) & V12 \== X & empty(V12) & holding(B, V12) & obj_tp(B, hand) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	leave(B, V12);
	grasp(B, X);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, Z);
	pour_shot_to_clean_shaker(X, V7, V12, B, V9, V10);
	clean_shot(X, V7, B, C);
	fill_shot(X, V8, B, C, A);
	pour_shot_to_used_shaker(X, V8, V12, B, V10, V11);
	clean_shot(X, V8, B, C);
	grasp(C, V12);
	leave(B, X);
	shake(Y, V7, V8, V12, C, B);
	pour_shaker_to_shot(Y, X, C, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(B, V8) & obj_tp(B, dispenser) & clean(V13) & obj_tp(V13, shot) & V13 \== X & empty(V13) & ontable(V13) & handempty(D) & obj_tp(D, hand) & shaked(V12) & obj_tp(V12, shaker) & V12 \== V13 & V12 \== X & contains(V12, Z) & obj_tp(Z, cocktail) & V7 \== Z & V8 \== Z & Y \== Z & holding(C, V12) & obj_tp(C, hand) & C \== D & shaker_empty_level(V12, V10) & obj_tp(V10, level) & next(V10, V9) & obj_tp(V9, level) & V10 \== V9 & shaker_level(V12, V9) & next(V9, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	empty_shaker(C, V12, Z, V9, V10);
	clean_shaker(C, D, V12);
	grasp(D, V13);
	leave(C, V12);
	fill_shot(V13, V7, D, C, A);
	pour_shot_to_clean_shaker(V13, V7, V12, D, V10, V9);
	clean_shot(V13, V7, D, C);
	fill_shot(V13, V8, D, C, B);
	grasp(C, V12);
	pour_shot_to_used_shaker(V13, V8, V12, D, V9, V11);
	leave(D, V13);
	shake(Y, V7, V8, V12, C, D);
	pour_shaker_to_shot(Y, X, C, V12, V11, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & used(X, D) & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & empty(V11) & obj_tp(V11, shaker) & V11 \== X & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V11);
	leave(B, V11);
	grasp(B, X);
	refill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	grasp(C, V11);
	leave(B, X);
	shake(Y, D, V7, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & empty(V11) & obj_tp(V11, shaker) & V11 \== X & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V11);
	leave(B, V11);
	grasp(B, X);
	fill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	leave(B, X);
	grasp(B, V11);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & V7 \== V8 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(B, V8) & obj_tp(B, dispenser) & clean(V13) & obj_tp(V13, shot) & V13 \== X & empty(V13) & ontable(V13) & handempty(D) & obj_tp(D, hand) & shaked(V12) & obj_tp(V12, shaker) & V12 \== V13 & V12 \== X & contains(V12, Z) & obj_tp(Z, cocktail) & V7 \== Z & V8 \== Z & Y \== Z & holding(C, V12) & obj_tp(C, hand) & C \== D & shaker_empty_level(V12, V10) & obj_tp(V10, level) & next(V10, V9) & obj_tp(V9, level) & V10 \== V9 & shaker_level(V12, V9) & next(V9, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	empty_shaker(C, V12, Z, V9, V10);
	clean_shaker(C, D, V12);
	leave(C, V12);
	grasp(D, V13);
	fill_shot(V13, V7, D, C, A);
	pour_shot_to_clean_shaker(V13, V7, V12, D, V10, V9);
	clean_shot(V13, V7, D, C);
	fill_shot(V13, V8, D, C, B);
	grasp(C, V12);
	pour_shot_to_used_shaker(V13, V8, V12, D, V9, V11);
	leave(D, V13);
	shake(Y, V8, V7, V12, C, D);
	pour_shaker_to_shot(Y, X, C, V12, V11, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & V7 \== V8 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(B, V8) & obj_tp(B, dispenser) & used(V13, V7) & obj_tp(V13, shot) & V13 \== X & empty(V13) & ontable(V13) & handempty(D) & obj_tp(D, hand) & shaked(V12) & obj_tp(V12, shaker) & V12 \== V13 & V12 \== X & contains(V12, Z) & obj_tp(Z, cocktail) & V7 \== Z & V8 \== Z & Y \== Z & holding(C, V12) & obj_tp(C, hand) & C \== D & shaker_empty_level(V12, V10) & obj_tp(V10, level) & next(V10, V9) & obj_tp(V9, level) & V10 \== V9 & shaker_level(V12, V9) & next(V9, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	empty_shaker(C, V12, Z, V9, V10);
	clean_shaker(C, D, V12);
	leave(C, V12);
	grasp(C, V13);
	refill_shot(V13, V7, C, D, A);
	pour_shot_to_clean_shaker(V13, V7, V12, C, V10, V9);
	clean_shot(V13, V7, C, D);
	fill_shot(V13, V8, C, D, B);
	pour_shot_to_used_shaker(V13, V8, V12, C, V9, V11);
	leave(C, V13);
	grasp(C, V12);
	shake(Y, V8, V7, V12, C, D);
	pour_shaker_to_shot(Y, X, C, V12, V11, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & used(X, D) & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & empty(V11) & obj_tp(V11, shaker) & V11 \== X & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V11);
	leave(B, V11);
	grasp(B, X);
	refill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	leave(B, X);
	grasp(B, V11);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & used(X, D) & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & empty(V11) & obj_tp(V11, shaker) & V11 \== X & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V11);
	grasp(C, X);
	leave(B, V11);
	refill_shot(X, D, C, B, Z);
	pour_shot_to_clean_shaker(X, D, V11, C, V8, V9);
	clean_shot(X, D, C, B);
	fill_shot(X, V7, C, B, A);
	pour_shot_to_used_shaker(X, V7, V11, C, V9, V10);
	clean_shot(X, V7, C, B);
	grasp(B, V11);
	leave(C, X);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & V7 \== V8 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(B, V8) & obj_tp(B, dispenser) & used(V13, V7) & obj_tp(V13, shot) & V13 \== X & empty(V13) & ontable(V13) & handempty(D) & obj_tp(D, hand) & shaked(V12) & obj_tp(V12, shaker) & V12 \== V13 & V12 \== X & contains(V12, Z) & obj_tp(Z, cocktail) & V7 \== Z & V8 \== Z & Y \== Z & holding(C, V12) & obj_tp(C, hand) & C \== D & shaker_empty_level(V12, V10) & obj_tp(V10, level) & next(V10, V9) & obj_tp(V9, level) & V10 \== V9 & shaker_level(V12, V9) & next(V9, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	empty_shaker(C, V12, Z, V9, V10);
	clean_shaker(C, D, V12);
	leave(C, V12);
	grasp(D, V13);
	refill_shot(V13, V7, D, C, A);
	pour_shot_to_clean_shaker(V13, V7, V12, D, V10, V9);
	clean_shot(V13, V7, D, C);
	fill_shot(V13, V8, D, C, B);
	grasp(C, V12);
	pour_shot_to_used_shaker(V13, V8, V12, D, V9, V11);
	leave(D, V13);
	shake(Y, V8, V7, V12, C, D);
	pour_shaker_to_shot(Y, X, C, V12, V11, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(B, V8) & obj_tp(B, dispenser) & used(V13, V7) & obj_tp(V13, shot) & V13 \== X & empty(V13) & ontable(V13) & handempty(D) & obj_tp(D, hand) & shaked(V12) & obj_tp(V12, shaker) & V12 \== V13 & V12 \== X & contains(V12, Z) & obj_tp(Z, cocktail) & V7 \== Z & V8 \== Z & Y \== Z & holding(C, V12) & obj_tp(C, hand) & C \== D & shaker_empty_level(V12, V10) & obj_tp(V10, level) & next(V10, V9) & obj_tp(V9, level) & V10 \== V9 & shaker_level(V12, V9) & next(V9, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	empty_shaker(C, V12, Z, V9, V10);
	clean_shaker(C, D, V12);
	leave(C, V12);
	grasp(C, V13);
	refill_shot(V13, V7, C, D, A);
	pour_shot_to_clean_shaker(V13, V7, V12, C, V10, V9);
	clean_shot(V13, V7, C, D);
	fill_shot(V13, V8, C, D, B);
	pour_shot_to_used_shaker(V13, V8, V12, C, V9, V11);
	leave(C, V13);
	grasp(C, V12);
	shake(Y, V7, V8, V12, C, D);
	pour_shaker_to_shot(Y, X, C, V12, V11, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & clean(V12) & obj_tp(V12, shaker) & V12 \== X & empty(V12) & holding(C, V12) & obj_tp(C, hand) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & handempty(B) & obj_tp(B, hand) & B \== C <-
	grasp(B, X);
	leave(C, V12);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, Z);
	pour_shot_to_clean_shaker(X, V7, V12, B, V9, V10);
	clean_shot(X, V7, B, C);
	fill_shot(X, V8, B, C, A);
	pour_shot_to_used_shaker(X, V8, V12, B, V10, V11);
	clean_shot(X, V8, B, C);
	grasp(C, V12);
	leave(B, X);
	shake(Y, V7, V8, V12, C, B);
	pour_shaker_to_shot(Y, X, C, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & V7 \== V8 & V7 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & clean(V12) & obj_tp(V12, shaker) & V12 \== X & empty(V12) & holding(C, V12) & obj_tp(C, hand) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & handempty(B) & obj_tp(B, hand) & B \== C <-
	grasp(B, X);
	leave(C, V12);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, Z);
	pour_shot_to_clean_shaker(X, V7, V12, B, V9, V10);
	clean_shot(X, V7, B, C);
	fill_shot(X, V8, B, C, A);
	pour_shot_to_used_shaker(X, V8, V12, B, V10, V11);
	clean_shot(X, V8, B, C);
	grasp(C, V12);
	leave(B, X);
	shake(Y, V8, V7, V12, C, B);
	pour_shaker_to_shot(Y, X, C, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(B, V8) & obj_tp(B, dispenser) & clean(V13) & obj_tp(V13, shot) & V13 \== X & empty(V13) & ontable(V13) & handempty(D) & obj_tp(D, hand) & shaked(V12) & obj_tp(V12, shaker) & V12 \== V13 & V12 \== X & contains(V12, Z) & obj_tp(Z, cocktail) & V7 \== Z & V8 \== Z & Y \== Z & holding(C, V12) & obj_tp(C, hand) & C \== D & shaker_empty_level(V12, V10) & obj_tp(V10, level) & next(V10, V9) & obj_tp(V9, level) & V10 \== V9 & shaker_level(V12, V9) & next(V9, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	empty_shaker(C, V12, Z, V9, V10);
	clean_shaker(C, D, V12);
	leave(C, V12);
	grasp(D, V13);
	fill_shot(V13, V7, D, C, A);
	pour_shot_to_clean_shaker(V13, V7, V12, D, V10, V9);
	clean_shot(V13, V7, D, C);
	fill_shot(V13, V8, D, C, B);
	grasp(C, V12);
	pour_shot_to_used_shaker(V13, V8, V12, D, V9, V11);
	leave(D, V13);
	shake(Y, V7, V8, V12, C, D);
	pour_shaker_to_shot(Y, X, C, V12, V11, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & V7 \== V8 & V7 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & clean(V12) & obj_tp(V12, shaker) & V12 \== X & empty(V12) & holding(B, V12) & obj_tp(B, hand) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	leave(B, V12);
	grasp(B, X);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, Z);
	pour_shot_to_clean_shaker(X, V7, V12, B, V9, V10);
	clean_shot(X, V7, B, C);
	fill_shot(X, V8, B, C, A);
	pour_shot_to_used_shaker(X, V8, V12, B, V10, V11);
	clean_shot(X, V8, B, C);
	grasp(C, V12);
	leave(B, X);
	shake(Y, V8, V7, V12, C, B);
	pour_shaker_to_shot(Y, X, C, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & ontable(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & empty(V11) & obj_tp(V11, shaker) & V11 \== X & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V11);
	leave(B, V11);
	grasp(B, X);
	fill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	grasp(C, V11);
	leave(B, X);
	shake(Y, D, V7, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & ontable(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & empty(V11) & obj_tp(V11, shaker) & V11 \== X & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V11);
	grasp(C, X);
	leave(B, V11);
	fill_shot(X, D, C, B, Z);
	pour_shot_to_clean_shaker(X, D, V11, C, V8, V9);
	clean_shot(X, D, C, B);
	fill_shot(X, V7, C, B, A);
	pour_shot_to_used_shaker(X, V7, V11, C, V9, V10);
	clean_shot(X, V7, C, B);
	grasp(B, V11);
	leave(C, X);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & ontable(X) & cocktail_part1(Y, D) & obj_tp(D, ingredient) & D \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & D \== V7 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & empty(V11) & obj_tp(V11, shaker) & V11 \== X & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V11);
	leave(B, V11);
	grasp(B, X);
	fill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	leave(B, X);
	grasp(B, V11);
	shake(Y, D, V7, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & V7 \== V8 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(B, V8) & obj_tp(B, dispenser) & clean(V13) & obj_tp(V13, shot) & V13 \== X & empty(V13) & ontable(V13) & handempty(D) & obj_tp(D, hand) & shaked(V12) & obj_tp(V12, shaker) & V12 \== V13 & V12 \== X & contains(V12, Z) & obj_tp(Z, cocktail) & V7 \== Z & V8 \== Z & Y \== Z & holding(C, V12) & obj_tp(C, hand) & C \== D & shaker_empty_level(V12, V10) & obj_tp(V10, level) & next(V10, V9) & obj_tp(V9, level) & V10 \== V9 & shaker_level(V12, V9) & next(V9, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	empty_shaker(C, V12, Z, V9, V10);
	clean_shaker(C, D, V12);
	grasp(D, V13);
	leave(C, V12);
	fill_shot(V13, V7, D, C, A);
	pour_shot_to_clean_shaker(V13, V7, V12, D, V10, V9);
	clean_shot(V13, V7, D, C);
	fill_shot(V13, V8, D, C, B);
	grasp(C, V12);
	pour_shot_to_used_shaker(V13, V8, V12, D, V9, V11);
	leave(D, V13);
	shake(Y, V8, V7, V12, C, D);
	pour_shaker_to_shot(Y, X, C, V12, V11, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & V7 \== V8 & V7 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & clean(V12) & obj_tp(V12, shaker) & V12 \== X & empty(V12) & holding(B, V12) & obj_tp(B, hand) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	leave(B, V12);
	grasp(B, X);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, Z);
	pour_shot_to_clean_shaker(X, V7, V12, B, V9, V10);
	clean_shot(X, V7, B, C);
	fill_shot(X, V8, B, C, A);
	pour_shot_to_used_shaker(X, V8, V12, B, V10, V11);
	clean_shot(X, V8, B, C);
	leave(B, X);
	grasp(B, V12);
	shake(Y, V8, V7, V12, B, C);
	pour_shaker_to_shot(Y, X, B, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & empty(V11) & obj_tp(V11, shaker) & V11 \== X & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V11);
	leave(B, V11);
	grasp(B, X);
	fill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	grasp(C, V11);
	leave(B, X);
	shake(Y, V7, D, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & used(X, D) & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & empty(V11) & obj_tp(V11, shaker) & V11 \== X & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V11);
	leave(B, V11);
	grasp(B, X);
	refill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	leave(B, X);
	grasp(B, V11);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & used(X, D) & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & empty(V11) & obj_tp(V11, shaker) & V11 \== X & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V11);
	leave(B, V11);
	grasp(B, X);
	refill_shot(X, D, B, C, Z);
	pour_shot_to_clean_shaker(X, D, V11, B, V8, V9);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, A);
	pour_shot_to_used_shaker(X, V7, V11, B, V9, V10);
	clean_shot(X, V7, B, C);
	grasp(C, V11);
	leave(B, X);
	shake(Y, V7, D, V11, C, B);
	pour_shaker_to_shot(Y, X, C, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & clean(V12) & obj_tp(V12, shaker) & V12 \== X & empty(V12) & holding(B, V12) & obj_tp(B, hand) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	leave(B, V12);
	grasp(B, X);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, Z);
	pour_shot_to_clean_shaker(X, V7, V12, B, V9, V10);
	clean_shot(X, V7, B, C);
	fill_shot(X, V8, B, C, A);
	pour_shot_to_used_shaker(X, V8, V12, B, V10, V11);
	clean_shot(X, V8, B, C);
	leave(B, X);
	grasp(B, V12);
	shake(Y, V7, V8, V12, B, C);
	pour_shaker_to_shot(Y, X, B, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, D) & obj_tp(D, ingredient) & D \== V7 & D \== Y & used(X, D) & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(Z, D) & obj_tp(Z, dispenser) & empty(V11) & obj_tp(V11, shaker) & V11 \== X & holding(B, V11) & obj_tp(B, hand) & shaker_level(V11, V8) & obj_tp(V8, level) & next(V8, V9) & obj_tp(V9, level) & V8 \== V9 & next(V9, V10) & obj_tp(V10, level) & V10 \== V8 & V10 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V11);
	grasp(C, X);
	leave(B, V11);
	refill_shot(X, D, C, B, Z);
	pour_shot_to_clean_shaker(X, D, V11, C, V8, V9);
	clean_shot(X, D, C, B);
	fill_shot(X, V7, C, B, A);
	pour_shot_to_used_shaker(X, V7, V11, C, V9, V10);
	clean_shot(X, V7, C, B);
	grasp(B, V11);
	leave(C, X);
	shake(Y, V7, D, V11, B, C);
	pour_shaker_to_shot(Y, X, B, V11, V10, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & V7 \== V8 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(B, V8) & obj_tp(B, dispenser) & clean(V13) & obj_tp(V13, shot) & V13 \== X & empty(V13) & ontable(V13) & handempty(D) & obj_tp(D, hand) & shaked(V12) & obj_tp(V12, shaker) & V12 \== V13 & V12 \== X & contains(V12, Z) & obj_tp(Z, cocktail) & V7 \== Z & V8 \== Z & Y \== Z & holding(C, V12) & obj_tp(C, hand) & C \== D & shaker_empty_level(V12, V10) & obj_tp(V10, level) & next(V10, V9) & obj_tp(V9, level) & V10 \== V9 & shaker_level(V12, V9) & next(V9, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	empty_shaker(C, V12, Z, V9, V10);
	clean_shaker(C, D, V12);
	leave(C, V12);
	grasp(C, V13);
	fill_shot(V13, V7, C, D, A);
	pour_shot_to_clean_shaker(V13, V7, V12, C, V10, V9);
	clean_shot(V13, V7, C, D);
	fill_shot(V13, V8, C, D, B);
	grasp(D, V12);
	pour_shot_to_used_shaker(V13, V8, V12, C, V9, V11);
	leave(C, V13);
	shake(Y, V8, V7, V12, D, C);
	pour_shaker_to_shot(Y, X, D, V12, V11, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(B, V8) & obj_tp(B, dispenser) & used(V13, V7) & obj_tp(V13, shot) & V13 \== X & empty(V13) & ontable(V13) & handempty(D) & obj_tp(D, hand) & shaked(V12) & obj_tp(V12, shaker) & V12 \== V13 & V12 \== X & contains(V12, Z) & obj_tp(Z, cocktail) & V7 \== Z & V8 \== Z & Y \== Z & holding(C, V12) & obj_tp(C, hand) & C \== D & shaker_empty_level(V12, V10) & obj_tp(V10, level) & next(V10, V9) & obj_tp(V9, level) & V10 \== V9 & shaker_level(V12, V9) & next(V9, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	empty_shaker(C, V12, Z, V9, V10);
	clean_shaker(C, D, V12);
	leave(C, V12);
	grasp(D, V13);
	refill_shot(V13, V7, D, C, A);
	pour_shot_to_clean_shaker(V13, V7, V12, D, V10, V9);
	clean_shot(V13, V7, D, C);
	fill_shot(V13, V8, D, C, B);
	grasp(C, V12);
	pour_shot_to_used_shaker(V13, V8, V12, D, V9, V11);
	leave(D, V13);
	shake(Y, V7, V8, V12, C, D);
	pour_shaker_to_shot(Y, X, C, V12, V11, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(B, V8) & obj_tp(B, dispenser) & handempty(D) & obj_tp(D, hand) & shaked(V12) & obj_tp(V12, shaker) & V12 \== X & contains(V12, Z) & obj_tp(Z, cocktail) & V7 \== Z & V8 \== Z & Y \== Z & holding(C, V12) & obj_tp(C, hand) & C \== D & shaker_empty_level(V12, V10) & obj_tp(V10, level) & next(V10, V9) & obj_tp(V9, level) & V10 \== V9 & shaker_level(V12, V9) & next(V9, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	empty_shaker(C, V12, Z, V9, V10);
	clean_shaker(C, D, V12);
	leave(C, V12);
	grasp(C, X);
	fill_shot(X, V7, C, D, A);
	pour_shot_to_clean_shaker(X, V7, V12, C, V10, V9);
	clean_shot(X, V7, C, D);
	fill_shot(X, V8, C, D, B);
	pour_shot_to_used_shaker(X, V8, V12, C, V9, V11);
	clean_shot(X, V8, C, D);
	leave(C, X);
	grasp(C, V12);
	shake(Y, V7, V8, V12, C, D);
	pour_shaker_to_shot(Y, X, C, V12, V11, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & V7 \== V8 & V7 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & empty(V12) & obj_tp(V12, shaker) & V12 \== X & holding(B, V12) & obj_tp(B, hand) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V12);
	leave(B, V12);
	grasp(B, X);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, Z);
	pour_shot_to_clean_shaker(X, V7, V12, B, V9, V10);
	clean_shot(X, V7, B, C);
	fill_shot(X, V8, B, C, A);
	pour_shot_to_used_shaker(X, V8, V12, B, V10, V11);
	clean_shot(X, V8, B, C);
	grasp(C, V12);
	leave(B, X);
	shake(Y, V8, V7, V12, C, B);
	pour_shaker_to_shot(Y, X, C, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & V7 \== V8 & V7 \== Y & used(X, V7) & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(B, V8) & obj_tp(B, dispenser) & handempty(D) & obj_tp(D, hand) & shaked(V12) & obj_tp(V12, shaker) & V12 \== X & contains(V12, Z) & obj_tp(Z, cocktail) & V7 \== Z & V8 \== Z & Y \== Z & holding(C, V12) & obj_tp(C, hand) & C \== D & shaker_empty_level(V12, V10) & obj_tp(V10, level) & next(V10, V9) & obj_tp(V9, level) & V10 \== V9 & shaker_level(V12, V9) & next(V9, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	empty_shaker(C, V12, Z, V9, V10);
	clean_shaker(C, D, V12);
	grasp(D, X);
	leave(C, V12);
	refill_shot(X, V7, D, C, A);
	pour_shot_to_clean_shaker(X, V7, V12, D, V10, V9);
	clean_shot(X, V7, D, C);
	fill_shot(X, V8, D, C, B);
	pour_shot_to_used_shaker(X, V8, V12, D, V9, V11);
	clean_shot(X, V8, D, C);
	grasp(C, V12);
	leave(D, X);
	shake(Y, V8, V7, V12, C, D);
	pour_shaker_to_shot(Y, X, C, V12, V11, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & V7 \== V8 & V7 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & empty(V12) & obj_tp(V12, shaker) & V12 \== X & holding(B, V12) & obj_tp(B, hand) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V12);
	grasp(C, X);
	leave(B, V12);
	clean_shot(X, D, C, B);
	fill_shot(X, V7, C, B, Z);
	pour_shot_to_clean_shaker(X, V7, V12, C, V9, V10);
	clean_shot(X, V7, C, B);
	fill_shot(X, V8, C, B, A);
	pour_shot_to_used_shaker(X, V8, V12, C, V10, V11);
	clean_shot(X, V8, C, B);
	grasp(B, V12);
	leave(C, X);
	shake(Y, V8, V7, V12, B, C);
	pour_shaker_to_shot(Y, X, B, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & used(X, V7) & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(B, V8) & obj_tp(B, dispenser) & handempty(D) & obj_tp(D, hand) & shaked(V12) & obj_tp(V12, shaker) & V12 \== X & contains(V12, Z) & obj_tp(Z, cocktail) & V7 \== Z & V8 \== Z & Y \== Z & holding(C, V12) & obj_tp(C, hand) & C \== D & shaker_empty_level(V12, V10) & obj_tp(V10, level) & next(V10, V9) & obj_tp(V9, level) & V10 \== V9 & shaker_level(V12, V9) & next(V9, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	empty_shaker(C, V12, Z, V9, V10);
	clean_shaker(C, D, V12);
	grasp(D, X);
	leave(C, V12);
	refill_shot(X, V7, D, C, A);
	pour_shot_to_clean_shaker(X, V7, V12, D, V10, V9);
	clean_shot(X, V7, D, C);
	fill_shot(X, V8, D, C, B);
	pour_shot_to_used_shaker(X, V8, V12, D, V9, V11);
	clean_shot(X, V8, D, C);
	grasp(C, V12);
	leave(D, X);
	shake(Y, V7, V8, V12, C, D);
	pour_shaker_to_shot(Y, X, C, V12, V11, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & used(X, V7) & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(B, V8) & obj_tp(B, dispenser) & handempty(D) & obj_tp(D, hand) & shaked(V12) & obj_tp(V12, shaker) & V12 \== X & contains(V12, Z) & obj_tp(Z, cocktail) & V7 \== Z & V8 \== Z & Y \== Z & holding(C, V12) & obj_tp(C, hand) & C \== D & shaker_empty_level(V12, V10) & obj_tp(V10, level) & next(V10, V9) & obj_tp(V9, level) & V10 \== V9 & shaker_level(V12, V9) & next(V9, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	empty_shaker(C, V12, Z, V9, V10);
	clean_shaker(C, D, V12);
	leave(C, V12);
	grasp(C, X);
	refill_shot(X, V7, C, D, A);
	pour_shot_to_clean_shaker(X, V7, V12, C, V10, V9);
	clean_shot(X, V7, C, D);
	fill_shot(X, V8, C, D, B);
	pour_shot_to_used_shaker(X, V8, V12, C, V9, V11);
	clean_shot(X, V8, C, D);
	leave(C, X);
	grasp(C, V12);
	shake(Y, V7, V8, V12, C, D);
	pour_shaker_to_shot(Y, X, C, V12, V11, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & empty(V12) & obj_tp(V12, shaker) & V12 \== X & holding(B, V12) & obj_tp(B, hand) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V12);
	grasp(C, X);
	leave(B, V12);
	clean_shot(X, D, C, B);
	fill_shot(X, V7, C, B, Z);
	pour_shot_to_clean_shaker(X, V7, V12, C, V9, V10);
	clean_shot(X, V7, C, B);
	fill_shot(X, V8, C, B, A);
	pour_shot_to_used_shaker(X, V8, V12, C, V10, V11);
	clean_shot(X, V8, C, B);
	grasp(B, V12);
	leave(C, X);
	shake(Y, V7, V8, V12, B, C);
	pour_shaker_to_shot(Y, X, B, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & V7 \== V8 & V7 \== Y & used(X, V7) & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(B, V8) & obj_tp(B, dispenser) & handempty(D) & obj_tp(D, hand) & shaked(V12) & obj_tp(V12, shaker) & V12 \== X & contains(V12, Z) & obj_tp(Z, cocktail) & V7 \== Z & V8 \== Z & Y \== Z & holding(C, V12) & obj_tp(C, hand) & C \== D & shaker_empty_level(V12, V10) & obj_tp(V10, level) & next(V10, V9) & obj_tp(V9, level) & V10 \== V9 & shaker_level(V12, V9) & next(V9, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	empty_shaker(C, V12, Z, V9, V10);
	clean_shaker(C, D, V12);
	leave(C, V12);
	grasp(C, X);
	refill_shot(X, V7, C, D, A);
	pour_shot_to_clean_shaker(X, V7, V12, C, V10, V9);
	clean_shot(X, V7, C, D);
	fill_shot(X, V8, C, D, B);
	pour_shot_to_used_shaker(X, V8, V12, C, V9, V11);
	clean_shot(X, V8, C, D);
	leave(C, X);
	grasp(C, V12);
	shake(Y, V8, V7, V12, C, D);
	pour_shaker_to_shot(Y, X, C, V12, V11, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(B, V8) & obj_tp(B, dispenser) & handempty(D) & obj_tp(D, hand) & shaked(V12) & obj_tp(V12, shaker) & V12 \== X & contains(V12, Z) & obj_tp(Z, cocktail) & V7 \== Z & V8 \== Z & Y \== Z & holding(C, V12) & obj_tp(C, hand) & C \== D & shaker_empty_level(V12, V10) & obj_tp(V10, level) & next(V10, V9) & obj_tp(V9, level) & V10 \== V9 & shaker_level(V12, V9) & next(V9, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	empty_shaker(C, V12, Z, V9, V10);
	clean_shaker(C, D, V12);
	grasp(D, X);
	leave(C, V12);
	fill_shot(X, V7, D, C, A);
	pour_shot_to_clean_shaker(X, V7, V12, D, V10, V9);
	clean_shot(X, V7, D, C);
	fill_shot(X, V8, D, C, B);
	pour_shot_to_used_shaker(X, V8, V12, D, V9, V11);
	clean_shot(X, V8, D, C);
	grasp(C, V12);
	leave(D, X);
	shake(Y, V7, V8, V12, C, D);
	pour_shaker_to_shot(Y, X, C, V12, V11, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & ontable(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & V7 \== V8 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(B, V8) & obj_tp(B, dispenser) & handempty(D) & obj_tp(D, hand) & shaked(V12) & obj_tp(V12, shaker) & V12 \== X & contains(V12, Z) & obj_tp(Z, cocktail) & V7 \== Z & V8 \== Z & Y \== Z & holding(C, V12) & obj_tp(C, hand) & C \== D & shaker_empty_level(V12, V10) & obj_tp(V10, level) & next(V10, V9) & obj_tp(V9, level) & V10 \== V9 & shaker_level(V12, V9) & next(V9, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	empty_shaker(C, V12, Z, V9, V10);
	clean_shaker(C, D, V12);
	leave(C, V12);
	grasp(C, X);
	fill_shot(X, V7, C, D, A);
	pour_shot_to_clean_shaker(X, V7, V12, C, V10, V9);
	clean_shot(X, V7, C, D);
	fill_shot(X, V8, C, D, B);
	pour_shot_to_used_shaker(X, V8, V12, C, V9, V11);
	clean_shot(X, V8, C, D);
	grasp(D, V12);
	leave(C, X);
	shake(Y, V8, V7, V12, D, C);
	pour_shaker_to_shot(Y, X, D, V12, V11, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & empty(V12) & obj_tp(V12, shaker) & V12 \== X & holding(B, V12) & obj_tp(B, hand) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V12);
	leave(B, V12);
	grasp(B, X);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, Z);
	pour_shot_to_clean_shaker(X, V7, V12, B, V9, V10);
	clean_shot(X, V7, B, C);
	fill_shot(X, V8, B, C, A);
	pour_shot_to_used_shaker(X, V8, V12, B, V10, V11);
	clean_shot(X, V8, B, C);
	grasp(C, V12);
	leave(B, X);
	shake(Y, V7, V8, V12, C, B);
	pour_shaker_to_shot(Y, X, C, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & ontable(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & V7 \== V8 & V7 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(B, V8) & obj_tp(B, dispenser) & handempty(D) & obj_tp(D, hand) & shaked(V12) & obj_tp(V12, shaker) & V12 \== X & contains(V12, Z) & obj_tp(Z, cocktail) & V7 \== Z & V8 \== Z & Y \== Z & holding(C, V12) & obj_tp(C, hand) & C \== D & shaker_empty_level(V12, V10) & obj_tp(V10, level) & next(V10, V9) & obj_tp(V9, level) & V10 \== V9 & shaker_level(V12, V9) & next(V9, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	empty_shaker(C, V12, Z, V9, V10);
	clean_shaker(C, D, V12);
	leave(C, V12);
	grasp(C, X);
	fill_shot(X, V7, C, D, A);
	pour_shot_to_clean_shaker(X, V7, V12, C, V10, V9);
	clean_shot(X, V7, C, D);
	fill_shot(X, V8, C, D, B);
	pour_shot_to_used_shaker(X, V8, V12, C, V9, V11);
	clean_shot(X, V8, C, D);
	leave(C, X);
	grasp(C, V12);
	shake(Y, V8, V7, V12, C, D);
	pour_shaker_to_shot(Y, X, C, V12, V11, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & empty(V12) & obj_tp(V12, shaker) & V12 \== X & holding(B, V12) & obj_tp(B, hand) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V12);
	leave(B, V12);
	grasp(B, X);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, Z);
	pour_shot_to_clean_shaker(X, V7, V12, B, V9, V10);
	clean_shot(X, V7, B, C);
	fill_shot(X, V8, B, C, A);
	pour_shot_to_used_shaker(X, V8, V12, B, V10, V11);
	clean_shot(X, V8, B, C);
	leave(B, X);
	grasp(B, V12);
	shake(Y, V7, V8, V12, B, C);
	pour_shaker_to_shot(Y, X, B, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & V7 \== V8 & V7 \== Y & used(X, V7) & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(B, V8) & obj_tp(B, dispenser) & handempty(D) & obj_tp(D, hand) & shaked(V12) & obj_tp(V12, shaker) & V12 \== X & contains(V12, Z) & obj_tp(Z, cocktail) & V7 \== Z & V8 \== Z & Y \== Z & holding(C, V12) & obj_tp(C, hand) & C \== D & shaker_empty_level(V12, V10) & obj_tp(V10, level) & next(V10, V9) & obj_tp(V9, level) & V10 \== V9 & shaker_level(V12, V9) & next(V9, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	empty_shaker(C, V12, Z, V9, V10);
	clean_shaker(C, D, V12);
	leave(C, V12);
	grasp(C, X);
	refill_shot(X, V7, C, D, A);
	pour_shot_to_clean_shaker(X, V7, V12, C, V10, V9);
	clean_shot(X, V7, C, D);
	fill_shot(X, V8, C, D, B);
	pour_shot_to_used_shaker(X, V8, V12, C, V9, V11);
	clean_shot(X, V8, C, D);
	grasp(D, V12);
	leave(C, X);
	shake(Y, V8, V7, V12, D, C);
	pour_shaker_to_shot(Y, X, D, V12, V11, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V9) & obj_tp(V9, ingredient) & V8 \== V9 & V9 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(B, V9) & obj_tp(B, dispenser) & empty(V14) & obj_tp(V14, shot) & V14 \== X & ontable(V14) & used(V14, V7) & obj_tp(V7, beverage) & V7 \== V8 & handempty(D) & obj_tp(D, hand) & shaked(V13) & obj_tp(V13, shaker) & V13 \== V14 & V13 \== X & contains(V13, Z) & obj_tp(Z, cocktail) & V8 \== Z & V9 \== Z & Y \== Z & holding(C, V13) & obj_tp(C, hand) & C \== D & shaker_empty_level(V13, V11) & obj_tp(V11, level) & next(V11, V10) & obj_tp(V10, level) & V10 \== V11 & shaker_level(V13, V10) & next(V10, V12) & obj_tp(V12, level) & V10 \== V12 & V11 \== V12 <-
	empty_shaker(C, V13, Z, V10, V11);
	clean_shaker(C, D, V13);
	grasp(D, V14);
	leave(C, V13);
	clean_shot(V14, V7, D, C);
	fill_shot(V14, V8, D, C, A);
	pour_shot_to_clean_shaker(V14, V8, V13, D, V11, V10);
	clean_shot(V14, V8, D, C);
	fill_shot(V14, V9, D, C, B);
	grasp(C, V13);
	pour_shot_to_used_shaker(V14, V9, V13, D, V10, V12);
	leave(D, V14);
	shake(Y, V8, V9, V13, C, D);
	pour_shaker_to_shot(Y, X, C, V13, V12, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & used(X, V7) & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(B, V8) & obj_tp(B, dispenser) & handempty(D) & obj_tp(D, hand) & shaked(V12) & obj_tp(V12, shaker) & V12 \== X & contains(V12, Z) & obj_tp(Z, cocktail) & V7 \== Z & V8 \== Z & Y \== Z & holding(C, V12) & obj_tp(C, hand) & C \== D & shaker_empty_level(V12, V10) & obj_tp(V10, level) & next(V10, V9) & obj_tp(V9, level) & V10 \== V9 & shaker_level(V12, V9) & next(V9, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	empty_shaker(C, V12, Z, V9, V10);
	clean_shaker(C, D, V12);
	leave(C, V12);
	grasp(C, X);
	refill_shot(X, V7, C, D, A);
	pour_shot_to_clean_shaker(X, V7, V12, C, V10, V9);
	clean_shot(X, V7, C, D);
	fill_shot(X, V8, C, D, B);
	pour_shot_to_used_shaker(X, V8, V12, C, V9, V11);
	clean_shot(X, V8, C, D);
	grasp(D, V12);
	leave(C, X);
	shake(Y, V7, V8, V12, D, C);
	pour_shaker_to_shot(Y, X, D, V12, V11, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V7) & obj_tp(V7, ingredient) & V7 \== V8 & V7 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(Z, V7) & obj_tp(Z, dispenser) & used(X, D) & obj_tp(D, beverage) & D \== V7 & D \== V8 & empty(V12) & obj_tp(V12, shaker) & V12 \== X & holding(B, V12) & obj_tp(B, hand) & shaker_level(V12, V9) & obj_tp(V9, level) & next(V9, V10) & obj_tp(V10, level) & V10 \== V9 & next(V10, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 & handempty(C) & obj_tp(C, hand) & B \== C <-
	clean_shaker(B, C, V12);
	leave(B, V12);
	grasp(B, X);
	clean_shot(X, D, B, C);
	fill_shot(X, V7, B, C, Z);
	pour_shot_to_clean_shaker(X, V7, V12, B, V9, V10);
	clean_shot(X, V7, B, C);
	fill_shot(X, V8, B, C, A);
	pour_shot_to_used_shaker(X, V8, V12, B, V10, V11);
	clean_shot(X, V8, B, C);
	leave(B, X);
	grasp(B, V12);
	shake(Y, V8, V7, V12, B, C);
	pour_shaker_to_shot(Y, X, B, V12, V11, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & clean(X) & empty(X) & ontable(X) & cocktail_part1(Y, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V7 \== V8 & V8 \== Y & dispenses(A, V7) & obj_tp(A, dispenser) & dispenses(B, V8) & obj_tp(B, dispenser) & handempty(D) & obj_tp(D, hand) & shaked(V12) & obj_tp(V12, shaker) & V12 \== X & contains(V12, Z) & obj_tp(Z, cocktail) & V7 \== Z & V8 \== Z & Y \== Z & holding(C, V12) & obj_tp(C, hand) & C \== D & shaker_empty_level(V12, V10) & obj_tp(V10, level) & next(V10, V9) & obj_tp(V9, level) & V10 \== V9 & shaker_level(V12, V9) & next(V9, V11) & obj_tp(V11, level) & V10 \== V11 & V11 \== V9 <-
	empty_shaker(C, V12, Z, V9, V10);
	clean_shaker(C, D, V12);
	leave(C, V12);
	grasp(C, X);
	fill_shot(X, V7, C, D, A);
	pour_shot_to_clean_shaker(X, V7, V12, C, V10, V9);
	clean_shot(X, V7, C, D);
	fill_shot(X, V8, C, D, B);
	pour_shot_to_used_shaker(X, V8, V12, C, V9, V11);
	clean_shot(X, V8, C, D);
	grasp(D, V12);
	leave(C, X);
	shake(Y, V7, V8, V12, D, C);
	pour_shaker_to_shot(Y, X, D, V12, V11, V9).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V9) & obj_tp(V9, ingredient) & V9 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V8 \== V9 & V8 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(B, V9) & obj_tp(B, dispenser) & used(X, V7) & obj_tp(V7, beverage) & V7 \== V8 & V7 \== V9 & handempty(D) & obj_tp(D, hand) & shaked(V13) & obj_tp(V13, shaker) & V13 \== X & contains(V13, Z) & obj_tp(Z, cocktail) & V8 \== Z & V9 \== Z & Y \== Z & holding(C, V13) & obj_tp(C, hand) & C \== D & shaker_empty_level(V13, V11) & obj_tp(V11, level) & next(V11, V10) & obj_tp(V10, level) & V10 \== V11 & shaker_level(V13, V10) & next(V10, V12) & obj_tp(V12, level) & V10 \== V12 & V11 \== V12 <-
	empty_shaker(C, V13, Z, V10, V11);
	clean_shaker(C, D, V13);
	grasp(D, X);
	leave(C, V13);
	clean_shot(X, V7, D, C);
	fill_shot(X, V8, D, C, A);
	pour_shot_to_clean_shaker(X, V8, V13, D, V11, V10);
	clean_shot(X, V8, D, C);
	fill_shot(X, V9, D, C, B);
	pour_shot_to_used_shaker(X, V9, V13, D, V10, V12);
	clean_shot(X, V9, D, C);
	grasp(C, V13);
	leave(D, X);
	shake(Y, V9, V8, V13, C, D);
	pour_shaker_to_shot(Y, X, C, V13, V12, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V9) & obj_tp(V9, ingredient) & V8 \== V9 & V9 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(B, V9) & obj_tp(B, dispenser) & used(X, V7) & obj_tp(V7, beverage) & V7 \== V8 & V7 \== V9 & handempty(D) & obj_tp(D, hand) & shaked(V13) & obj_tp(V13, shaker) & V13 \== X & contains(V13, Z) & obj_tp(Z, cocktail) & V8 \== Z & V9 \== Z & Y \== Z & holding(C, V13) & obj_tp(C, hand) & C \== D & shaker_empty_level(V13, V11) & obj_tp(V11, level) & next(V11, V10) & obj_tp(V10, level) & V10 \== V11 & shaker_level(V13, V10) & next(V10, V12) & obj_tp(V12, level) & V10 \== V12 & V11 \== V12 <-
	empty_shaker(C, V13, Z, V10, V11);
	clean_shaker(C, D, V13);
	leave(C, V13);
	grasp(C, X);
	clean_shot(X, V7, C, D);
	fill_shot(X, V8, C, D, A);
	pour_shot_to_clean_shaker(X, V8, V13, C, V11, V10);
	clean_shot(X, V8, C, D);
	fill_shot(X, V9, C, D, B);
	pour_shot_to_used_shaker(X, V9, V13, C, V10, V12);
	clean_shot(X, V9, C, D);
	leave(C, X);
	grasp(C, V13);
	shake(Y, V8, V9, V13, C, D);
	pour_shaker_to_shot(Y, X, C, V13, V12, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V9) & obj_tp(V9, ingredient) & V8 \== V9 & V9 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(B, V9) & obj_tp(B, dispenser) & used(X, V7) & obj_tp(V7, beverage) & V7 \== V8 & V7 \== V9 & handempty(D) & obj_tp(D, hand) & shaked(V13) & obj_tp(V13, shaker) & V13 \== X & contains(V13, Z) & obj_tp(Z, cocktail) & V8 \== Z & V9 \== Z & Y \== Z & holding(C, V13) & obj_tp(C, hand) & C \== D & shaker_empty_level(V13, V11) & obj_tp(V11, level) & next(V11, V10) & obj_tp(V10, level) & V10 \== V11 & shaker_level(V13, V10) & next(V10, V12) & obj_tp(V12, level) & V10 \== V12 & V11 \== V12 <-
	empty_shaker(C, V13, Z, V10, V11);
	clean_shaker(C, D, V13);
	leave(C, V13);
	grasp(C, X);
	clean_shot(X, V7, C, D);
	fill_shot(X, V8, C, D, A);
	pour_shot_to_clean_shaker(X, V8, V13, C, V11, V10);
	clean_shot(X, V8, C, D);
	fill_shot(X, V9, C, D, B);
	pour_shot_to_used_shaker(X, V9, V13, C, V10, V12);
	clean_shot(X, V9, C, D);
	grasp(D, V13);
	leave(C, X);
	shake(Y, V8, V9, V13, D, C);
	pour_shaker_to_shot(Y, X, D, V13, V12, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V9) & obj_tp(V9, ingredient) & V9 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V8 \== V9 & V8 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(B, V9) & obj_tp(B, dispenser) & used(X, V7) & obj_tp(V7, beverage) & V7 \== V8 & V7 \== V9 & handempty(D) & obj_tp(D, hand) & shaked(V13) & obj_tp(V13, shaker) & V13 \== X & contains(V13, Z) & obj_tp(Z, cocktail) & V8 \== Z & V9 \== Z & Y \== Z & holding(C, V13) & obj_tp(C, hand) & C \== D & shaker_empty_level(V13, V11) & obj_tp(V11, level) & next(V11, V10) & obj_tp(V10, level) & V10 \== V11 & shaker_level(V13, V10) & next(V10, V12) & obj_tp(V12, level) & V10 \== V12 & V11 \== V12 <-
	empty_shaker(C, V13, Z, V10, V11);
	clean_shaker(C, D, V13);
	leave(C, V13);
	grasp(C, X);
	clean_shot(X, V7, C, D);
	fill_shot(X, V8, C, D, A);
	pour_shot_to_clean_shaker(X, V8, V13, C, V11, V10);
	clean_shot(X, V8, C, D);
	fill_shot(X, V9, C, D, B);
	pour_shot_to_used_shaker(X, V9, V13, C, V10, V12);
	clean_shot(X, V9, C, D);
	grasp(D, V13);
	leave(C, X);
	shake(Y, V9, V8, V13, D, C);
	pour_shaker_to_shot(Y, X, D, V13, V12, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V9) & obj_tp(V9, ingredient) & V9 \== Y & cocktail_part2(Y, V8) & obj_tp(V8, ingredient) & V8 \== V9 & V8 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(B, V9) & obj_tp(B, dispenser) & used(X, V7) & obj_tp(V7, beverage) & V7 \== V8 & V7 \== V9 & handempty(D) & obj_tp(D, hand) & shaked(V13) & obj_tp(V13, shaker) & V13 \== X & contains(V13, Z) & obj_tp(Z, cocktail) & V8 \== Z & V9 \== Z & Y \== Z & holding(C, V13) & obj_tp(C, hand) & C \== D & shaker_empty_level(V13, V11) & obj_tp(V11, level) & next(V11, V10) & obj_tp(V10, level) & V10 \== V11 & shaker_level(V13, V10) & next(V10, V12) & obj_tp(V12, level) & V10 \== V12 & V11 \== V12 <-
	empty_shaker(C, V13, Z, V10, V11);
	clean_shaker(C, D, V13);
	leave(C, V13);
	grasp(C, X);
	clean_shot(X, V7, C, D);
	fill_shot(X, V8, C, D, A);
	pour_shot_to_clean_shaker(X, V8, V13, C, V11, V10);
	clean_shot(X, V8, C, D);
	fill_shot(X, V9, C, D, B);
	pour_shot_to_used_shaker(X, V9, V13, C, V10, V12);
	clean_shot(X, V9, C, D);
	leave(C, X);
	grasp(C, V13);
	shake(Y, V9, V8, V13, C, D);
	pour_shaker_to_shot(Y, X, C, V13, V12, V10).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, cocktail) & empty(X) & ontable(X) & cocktail_part1(Y, V8) & obj_tp(V8, ingredient) & V8 \== Y & cocktail_part2(Y, V9) & obj_tp(V9, ingredient) & V8 \== V9 & V9 \== Y & dispenses(A, V8) & obj_tp(A, dispenser) & dispenses(B, V9) & obj_tp(B, dispenser) & used(X, V7) & obj_tp(V7, beverage) & V7 \== V8 & V7 \== V9 & handempty(D) & obj_tp(D, hand) & shaked(V13) & obj_tp(V13, shaker) & V13 \== X & contains(V13, Z) & obj_tp(Z, cocktail) & V8 \== Z & V9 \== Z & Y \== Z & holding(C, V13) & obj_tp(C, hand) & C \== D & shaker_empty_level(V13, V11) & obj_tp(V11, level) & next(V11, V10) & obj_tp(V10, level) & V10 \== V11 & shaker_level(V13, V10) & next(V10, V12) & obj_tp(V12, level) & V10 \== V12 & V11 \== V12 <-
	empty_shaker(C, V13, Z, V10, V11);
	clean_shaker(C, D, V13);
	grasp(D, X);
	leave(C, V13);
	clean_shot(X, V7, D, C);
	fill_shot(X, V8, D, C, A);
	pour_shot_to_clean_shaker(X, V8, V13, D, V11, V10);
	clean_shot(X, V8, D, C);
	fill_shot(X, V9, D, C, B);
	pour_shot_to_used_shaker(X, V9, V13, D, V10, V12);
	clean_shot(X, V9, D, C);
	grasp(C, V13);
	leave(D, X);
	shake(Y, V8, V9, V13, C, D);
	pour_shaker_to_shot(Y, X, C, V13, V12, V10).

+!empty(X) : obj_tp(X, shaker) & shaked(X) & contains(X, Z) & obj_tp(Z, cocktail) & holding(Y, X) & obj_tp(Y, hand) & shaker_empty_level(X, B) & obj_tp(B, level) & shaker_level(X, A) & obj_tp(A, level) <-
	empty_shaker(Y, X, Z, A, B).

+!empty(X) : obj_tp(X, shot) & contains(X, Z) & obj_tp(Z, beverage) & holding(Y, X) & obj_tp(Y, hand) <-
	empty_shot(Y, X, Z).

+!empty(X) : obj_tp(X, shot) & contains(X, Y) & obj_tp(Y, ingredient) & holding(A, X) & obj_tp(A, hand) & clean(Z) & obj_tp(Z, shaker) & empty(Z) & shaker_level(Z, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	pour_shot_to_clean_shaker(X, Y, Z, A, B, C).

+!empty(X) : obj_tp(X, shot) & contains(X, Y) & obj_tp(Y, ingredient) & holding(A, X) & obj_tp(A, hand) & unshaked(Z) & obj_tp(Z, shaker) & shaker_level(Z, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	pour_shot_to_used_shaker(X, Y, Z, A, B, C).

+!empty(X) : obj_tp(X, shot) & contains(X, Y) & obj_tp(Y, ingredient) & holding(A, X) & obj_tp(A, hand) & empty(Z) & obj_tp(Z, shaker) & holding(D, Z) & obj_tp(D, hand) & shaker_level(Z, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & handempty(V7) & obj_tp(V7, hand) <-
	clean_shaker(D, V7, Z);
	pour_shot_to_clean_shaker(X, Y, Z, A, B, C).

+!empty(X) : obj_tp(X, shaker) & ontable(X) & shaked(X) & contains(X, Z) & obj_tp(Z, cocktail) & shaker_empty_level(X, B) & obj_tp(B, level) & shaker_level(X, A) & obj_tp(A, level) & handempty(Y) & obj_tp(Y, hand) <-
	grasp(Y, X);
	empty_shaker(Y, X, Z, A, B).

+!empty(X) : obj_tp(X, shot) & ontable(X) & contains(X, Z) & obj_tp(Z, beverage) & handempty(Y) & obj_tp(Y, hand) <-
	grasp(Y, X);
	empty_shot(Y, X, Z).

+!empty(X) : obj_tp(X, shot) & ontable(X) & contains(X, Y) & obj_tp(Y, ingredient) & clean(Z) & obj_tp(Z, shaker) & X \== Z & empty(Z) & shaker_level(Z, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & handempty(A) & obj_tp(A, hand) <-
	grasp(A, X);
	pour_shot_to_clean_shaker(X, Y, Z, A, B, C).

+!empty(X) : obj_tp(X, shot) & ontable(X) & contains(X, Y) & obj_tp(Y, ingredient) & handempty(A) & obj_tp(A, hand) & unshaked(Z) & obj_tp(Z, shaker) & shaker_level(Z, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	grasp(A, X);
	pour_shot_to_used_shaker(X, Y, Z, A, B, C).

+!empty(X) : obj_tp(X, shaker) & unshaked(X) & contains(X, D) & obj_tp(D, ingredient) & cocktail_part1(C, D) & obj_tp(C, cocktail) & cocktail_part2(C, V7) & obj_tp(V7, ingredient) & contains(X, V7) & contains(X, Z) & obj_tp(Z, cocktail) & holding(V8, X) & obj_tp(V8, hand) & holding(Y, X) & obj_tp(Y, hand) & shaker_empty_level(X, B) & obj_tp(B, level) & shaker_level(X, A) & obj_tp(A, level) & handempty(V9) & obj_tp(V9, hand) <-
	shake(C, D, V7, X, V8, V9);
	empty_shaker(Y, X, Z, A, B).

+!handempty(X) : obj_tp(X, hand) & holding(X, Y) & obj_tp(Y, container) <-
	leave(X, Y).

+!holding(X, Y) : obj_tp(X, hand) & obj_tp(Y, container) & handempty(X) & ontable(Y) <-
	grasp(X, Y).

+!holding(X, Y) : obj_tp(X, hand) & obj_tp(Y, container) & handempty(X) & holding(Z, Y) & obj_tp(Z, hand) & X \== Z <-
	leave(Z, Y);
	grasp(X, Y).

+!holding(X, Y) : obj_tp(X, hand) & obj_tp(Y, container) & ontable(Y) & holding(X, Z) & obj_tp(Z, container) & Y \== Z <-
	leave(X, Z);
	grasp(X, Y).

+!ontable(X) : obj_tp(X, container) & holding(Y, X) & obj_tp(Y, hand) <-
	leave(Y, X).

+!shaked(X) : obj_tp(X, shaker) & unshaked(X) & contains(X, A) & obj_tp(A, ingredient) & cocktail_part2(Y, A) & obj_tp(Y, cocktail) & cocktail_part1(Y, Z) & obj_tp(Z, ingredient) & contains(X, Z) & holding(B, X) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) <-
	shake(Y, Z, A, X, B, C).

+!shaked(X) : obj_tp(X, shaker) & ontable(X) & unshaked(X) & contains(X, A) & obj_tp(A, ingredient) & cocktail_part2(Y, A) & obj_tp(Y, cocktail) & cocktail_part1(Y, Z) & obj_tp(Z, ingredient) & contains(X, Z) & handempty(B) & obj_tp(B, hand) & handempty(C) & obj_tp(C, hand) & B \== C <-
	grasp(B, X);
	shake(Y, Z, A, X, B, C).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & shaker_empty_level(X, Y) & shaked(X) & contains(X, A) & obj_tp(A, cocktail) & holding(Z, X) & obj_tp(Z, hand) & shaker_level(X, B) & obj_tp(B, level) & B \== Y <-
	empty_shaker(Z, X, A, B, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & shaked(X) & contains(X, Z) & obj_tp(Z, beverage) & holding(B, X) & obj_tp(B, hand) & next(Y, C) & obj_tp(C, level) & C \== Y & shaker_level(X, C) & clean(A) & obj_tp(A, shot) & empty(A) <-
	pour_shaker_to_shot(Z, A, B, X, C, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & shaked(X) & contains(X, Z) & obj_tp(Z, beverage) & holding(B, X) & obj_tp(B, hand) & next(Y, C) & obj_tp(C, level) & C \== Y & shaker_level(X, C) & empty(A) & obj_tp(A, shot) & holding(V7, A) & obj_tp(V7, hand) & used(A, D) & obj_tp(D, beverage) & handempty(V8) & obj_tp(V8, hand) <-
	clean_shot(A, D, V7, V8);
	pour_shaker_to_shot(Z, A, B, X, C, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & shaker_empty_level(X, Y) & ontable(X) & shaked(X) & contains(X, A) & obj_tp(A, cocktail) & shaker_level(X, B) & obj_tp(B, level) & B \== Y & handempty(Z) & obj_tp(Z, hand) <-
	grasp(Z, X);
	empty_shaker(Z, X, A, B, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & ontable(X) & shaked(X) & contains(X, Z) & obj_tp(Z, beverage) & next(Y, C) & obj_tp(C, level) & C \== Y & shaker_level(X, C) & clean(A) & obj_tp(A, shot) & empty(A) & handempty(B) & obj_tp(B, hand) <-
	grasp(B, X);
	pour_shaker_to_shot(Z, A, B, X, C, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & shaked(X) & contains(X, Z) & obj_tp(Z, beverage) & holding(B, X) & obj_tp(B, hand) & holding(B, A) & obj_tp(A, shot) & clean(A) & empty(A) & next(Y, C) & obj_tp(C, level) & C \== Y & shaker_level(X, C) <-
	pour_shaker_to_shot(Z, A, B, X, C, Y);
	empty_shot(B, A, Z).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & shaker_empty_level(X, Y) & unshaked(X) & contains(X, A) & obj_tp(A, cocktail) & contains(X, D) & obj_tp(D, ingredient) & cocktail_part1(C, D) & obj_tp(C, cocktail) & cocktail_part2(C, V7) & obj_tp(V7, ingredient) & contains(X, V7) & holding(V8, X) & obj_tp(V8, hand) & holding(Z, X) & obj_tp(Z, hand) & shaker_level(X, B) & obj_tp(B, level) & B \== Y & handempty(V9) & obj_tp(V9, hand) <-
	shake(C, D, V7, X, V8, V9);
	empty_shaker(Z, X, A, B, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & unshaked(X) & contains(X, V7) & obj_tp(V7, ingredient) & cocktail_part1(D, V7) & obj_tp(D, cocktail) & cocktail_part2(D, V8) & obj_tp(V8, ingredient) & contains(X, V8) & contains(X, Z) & obj_tp(Z, beverage) & V7 \== Z & V8 \== Z & holding(B, X) & obj_tp(B, hand) & holding(V9, X) & obj_tp(V9, hand) & next(Y, C) & obj_tp(C, level) & C \== Y & shaker_level(X, C) & clean(A) & obj_tp(A, shot) & empty(A) & handempty(V10) & obj_tp(V10, hand) <-
	shake(D, V7, V8, X, V9, V10);
	pour_shaker_to_shot(Z, A, B, X, C, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & shaked(X) & contains(X, Z) & obj_tp(Z, beverage) & holding(B, X) & obj_tp(B, hand) & next(Y, C) & obj_tp(C, level) & C \== Y & shaker_level(X, C) & empty(A) & obj_tp(A, shot) & holding(V7, A) & obj_tp(V7, hand) & used(A, D) & obj_tp(D, beverage) & handempty(V8) & obj_tp(V8, hand) <-
	clean_shot(A, D, V7, V8);
	pour_shaker_to_shot(Z, A, B, X, C, Y);
	empty_shot(V7, A, Z).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & ontable(X) & shaked(X) & contains(X, Z) & obj_tp(Z, beverage) & next(Y, C) & obj_tp(C, level) & C \== Y & shaker_level(X, C) & clean(A) & obj_tp(A, shot) & empty(A) & holding(B, A) & obj_tp(B, hand) & handempty(B) <-
	grasp(B, X);
	pour_shaker_to_shot(Z, A, B, X, C, Y);
	empty_shot(B, A, Z).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & unshaked(X) & contains(X, V7) & obj_tp(V7, ingredient) & cocktail_part1(D, V7) & obj_tp(D, cocktail) & cocktail_part2(D, V8) & obj_tp(V8, ingredient) & contains(X, V8) & contains(X, Z) & obj_tp(Z, beverage) & V7 \== Z & V8 \== Z & holding(B, X) & obj_tp(B, hand) & holding(B, A) & obj_tp(A, shot) & clean(A) & empty(A) & holding(V9, X) & obj_tp(V9, hand) & next(Y, C) & obj_tp(C, level) & C \== Y & shaker_level(X, C) & handempty(V10) & obj_tp(V10, hand) <-
	shake(D, V7, V8, X, V9, V10);
	pour_shaker_to_shot(Z, A, B, X, C, Y);
	empty_shot(B, A, Z).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, ingredient) & clean(X) & empty(X) & dispenses(B, Y) & obj_tp(B, dispenser) & holding(Z, X) & obj_tp(Z, hand) & handempty(A) & obj_tp(A, hand) <-
	fill_shot(X, Y, Z, A, B).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & shaked(A) & holding(Z, A) & obj_tp(Z, hand) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	pour_shaker_to_shot(Y, X, Z, A, B, C).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, ingredient) & empty(X) & dispenses(B, Y) & obj_tp(B, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(Z, X) & obj_tp(Z, hand) & used(X, C) & obj_tp(C, beverage) & C \== Y & handempty(A) & obj_tp(A, hand) & handempty(V7) & obj_tp(V7, hand) <-
	clean_shot(X, C, D, V7);
	fill_shot(X, Y, Z, A, B).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & shaked(A) & holding(V7, X) & obj_tp(V7, hand) & holding(Z, A) & obj_tp(Z, hand) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) & used(X, D) & obj_tp(D, beverage) & D \== Y & handempty(V8) & obj_tp(V8, hand) <-
	clean_shot(X, D, V7, V8);
	pour_shaker_to_shot(Y, X, Z, A, B, C).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, ingredient) & clean(X) & empty(X) & dispenses(B, Y) & obj_tp(B, dispenser) & holding(Z, X) & obj_tp(Z, hand) & handempty(A) & obj_tp(A, hand) <-
	fill_shot(X, Y, Z, A, B);
	empty_shot(Z, X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, ingredient) & clean(X) & empty(X) & ontable(X) & dispenses(B, Y) & obj_tp(B, dispenser) & handempty(A) & obj_tp(A, hand) & handempty(Z) & obj_tp(Z, hand) & A \== Z <-
	grasp(Z, X);
	fill_shot(X, Y, Z, A, B).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & ontable(A) & shaked(A) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) & handempty(Z) & obj_tp(Z, hand) <-
	grasp(Z, A);
	pour_shaker_to_shot(Y, X, Z, A, B, C).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & shaked(A) & holding(Z, A) & obj_tp(Z, hand) & holding(Z, X) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	pour_shaker_to_shot(Y, X, Z, A, B, C);
	empty_shot(Z, X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & unshaked(A) & contains(A, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part1(D, V7) & obj_tp(D, cocktail) & cocktail_part2(D, V8) & obj_tp(V8, ingredient) & V8 \== Y & contains(A, V8) & holding(V9, A) & obj_tp(V9, hand) & holding(Z, A) & obj_tp(Z, hand) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) & handempty(V10) & obj_tp(V10, hand) <-
	shake(D, V7, V8, A, V9, V10);
	pour_shaker_to_shot(Y, X, Z, A, B, C).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, ingredient) & empty(X) & dispenses(B, Y) & obj_tp(B, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(Z, X) & obj_tp(Z, hand) & used(X, C) & obj_tp(C, beverage) & C \== Y & handempty(A) & obj_tp(A, hand) & handempty(V7) & obj_tp(V7, hand) <-
	clean_shot(X, C, D, V7);
	fill_shot(X, Y, Z, A, B);
	empty_shot(D, X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & shaked(A) & holding(V7, X) & obj_tp(V7, hand) & holding(Z, A) & obj_tp(Z, hand) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) & used(X, D) & obj_tp(D, beverage) & D \== Y & handempty(V8) & obj_tp(V8, hand) <-
	clean_shot(X, D, V7, V8);
	pour_shaker_to_shot(Y, X, Z, A, B, C);
	empty_shot(V7, X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, ingredient) & clean(X) & empty(X) & ontable(X) & dispenses(B, Y) & obj_tp(B, dispenser) & handempty(A) & obj_tp(A, hand) & handempty(Z) & obj_tp(Z, hand) & A \== Z <-
	grasp(Z, X);
	fill_shot(X, Y, Z, A, B);
	empty_shot(Z, X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & ontable(A) & shaked(A) & holding(Z, X) & obj_tp(Z, hand) & handempty(Z) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	grasp(Z, A);
	pour_shaker_to_shot(Y, X, Z, A, B, C);
	empty_shot(Z, X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & unshaked(A) & contains(A, V7) & obj_tp(V7, ingredient) & V7 \== Y & cocktail_part1(D, V7) & obj_tp(D, cocktail) & cocktail_part2(D, V8) & obj_tp(V8, ingredient) & V8 \== Y & contains(A, V8) & holding(V9, A) & obj_tp(V9, hand) & holding(Z, A) & obj_tp(Z, hand) & holding(Z, X) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) & handempty(V10) & obj_tp(V10, hand) <-
	shake(D, V7, V8, A, V9, V10);
	pour_shaker_to_shot(Y, X, Z, A, B, C);
	empty_shot(Z, X, Y).

+!clean(X) : obj_tp(X, shaker) & not empty(X) <-
	!empty(X);
	!clean(X).

+!clean(X) : obj_tp(X, shot) & not empty(X) <-
	!empty(X);
	!clean(X).

+!clean(X) : obj_tp(X, shaker) & not ontable(X) <-
	!ontable(X);
	!clean(X).

+!clean(X) : obj_tp(X, shot) & not ontable(X) <-
	!ontable(X);
	!clean(X).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & shaked(X) & contains(X, V9) & obj_tp(V9, beverage) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & clean(Z) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(V11, X) & obj_tp(V11, hand) & shaker_level(X, V12) & obj_tp(V12, level) & next(B, V12) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & empty(V10) & obj_tp(V10, shot) & not clean(V10) <-
	!clean(V10);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & shaked(X) & contains(X, V9) & obj_tp(V9, beverage) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & used(Z, Y) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(V11, X) & obj_tp(V11, hand) & shaker_level(X, V12) & obj_tp(V12, level) & next(B, V12) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & empty(V10) & obj_tp(V10, shot) & not clean(V10) <-
	!clean(V10);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, ingredient) & not clean(X) <-
	!clean(X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & not clean(X) <-
	!clean(X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & not clean(X) <-
	!clean(X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & empty(Z) & not clean(Z) & holding(A, Z) & obj_tp(A, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	!clean(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & ontable(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & empty(Z) & obj_tp(Z, shot) & not clean(Z) & holding(A, Z) & obj_tp(A, hand) & holding(D, Z) & obj_tp(D, hand) & handempty(D) <-
	!clean(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & handempty(D) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & empty(Z) & obj_tp(Z, shot) & ontable(Z) & not clean(Z) & holding(A, Z) & obj_tp(A, hand) <-
	!clean(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & not clean(Z) & contains(Z, V10) & obj_tp(V10, beverage) & holding(A, Z) & obj_tp(A, hand) & holding(V9, Z) & obj_tp(V9, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	!clean(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & empty(Z) & ontable(Z) & not clean(Z) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	!clean(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & shaked(X) & contains(X, V10) & obj_tp(V10, cocktail) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & empty(Z) & not clean(Z) & holding(A, Z) & obj_tp(A, hand) & holding(V9, X) & obj_tp(V9, hand) & shaker_empty_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & shaker_level(X, V11) & obj_tp(V11, level) <-
	!clean(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & shaked(X) & contains(X, V9) & obj_tp(V9, beverage) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & empty(Z) & not clean(Z) & holding(A, Z) & obj_tp(A, hand) & holding(V11, X) & obj_tp(V11, hand) & shaker_level(X, V12) & obj_tp(V12, level) & next(B, V12) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	!clean(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & shaked(X) & contains(X, V9) & obj_tp(V9, beverage) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & clean(Z) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(V11, X) & obj_tp(V11, hand) & shaker_level(X, V12) & obj_tp(V12, level) & next(B, V12) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & clean(V10) & obj_tp(V10, shot) & not empty(V10) <-
	!empty(V10);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & shaked(X) & contains(X, V9) & obj_tp(V9, beverage) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & used(Z, Y) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(V11, X) & obj_tp(V11, hand) & shaker_level(X, V12) & obj_tp(V12, level) & next(B, V12) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & clean(V10) & obj_tp(V10, shot) & not empty(V10) <-
	!empty(V10);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, ingredient) & not empty(X) <-
	!empty(X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & not empty(X) <-
	!empty(X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & not empty(X) <-
	!empty(X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & clean(Z) & not empty(Z) & holding(A, Z) & obj_tp(A, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	!empty(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & ontable(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & clean(Z) & obj_tp(Z, shot) & not empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(D, Z) & obj_tp(D, hand) & handempty(D) <-
	!empty(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & handempty(D) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & clean(Z) & obj_tp(Z, shot) & ontable(Z) & not empty(Z) & holding(A, Z) & obj_tp(A, hand) <-
	!empty(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & not empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(V10, Z) & obj_tp(V10, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & used(Z, V9) & obj_tp(V9, beverage) <-
	!empty(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & clean(Z) & ontable(Z) & not empty(Z) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	!empty(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & shaked(X) & contains(X, V10) & obj_tp(V10, cocktail) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & clean(Z) & not empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(V9, X) & obj_tp(V9, hand) & shaker_empty_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & shaker_level(X, V11) & obj_tp(V11, level) <-
	!empty(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & shaked(X) & contains(X, V9) & obj_tp(V9, beverage) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & clean(Z) & not empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(V11, X) & obj_tp(V11, hand) & shaker_level(X, V12) & obj_tp(V12, level) & next(B, V12) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	!empty(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & used(Z, Y) & not empty(Z) & holding(A, Z) & obj_tp(A, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	!empty(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & ontable(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & used(Z, Y) & obj_tp(Z, shot) & not empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(D, Z) & obj_tp(D, hand) & handempty(D) <-
	!empty(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & handempty(D) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & used(Z, Y) & obj_tp(Z, shot) & ontable(Z) & not empty(Z) & holding(A, Z) & obj_tp(A, hand) <-
	!empty(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & used(Z, Y) & ontable(Z) & not empty(Z) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	!empty(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & shaked(X) & contains(X, V10) & obj_tp(V10, cocktail) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & used(Z, Y) & not empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(V9, X) & obj_tp(V9, hand) & shaker_empty_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & shaker_level(X, V11) & obj_tp(V11, level) <-
	!empty(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & shaked(X) & contains(X, V9) & obj_tp(V9, beverage) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & used(Z, Y) & not empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(V11, X) & obj_tp(V11, hand) & shaker_level(X, V12) & obj_tp(V12, level) & next(B, V12) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	!empty(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & ontable(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & clean(Z) & obj_tp(Z, shot) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(D, Z) & obj_tp(D, hand) & not handempty(D) <-
	!handempty(D);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & not handempty(D) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	!handempty(D);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & ontable(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & used(Z, Y) & obj_tp(Z, shot) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(D, Z) & obj_tp(D, hand) & not handempty(D) <-
	!handempty(D);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & clean(Z) & obj_tp(Z, shot) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(D, Z) & obj_tp(D, hand) & not holding(D, X) <-
	!holding(D, X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & handempty(D) & obj_tp(D, hand) & not holding(D, X) <-
	!holding(D, X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & clean(Z) & obj_tp(Z, shot) & contains(Z, V10) & obj_tp(V10, beverage) & holding(A, Z) & obj_tp(A, hand) & holding(D, Z) & obj_tp(D, hand) & not holding(D, X) & holding(V9, Z) & obj_tp(V9, hand) <-
	!holding(D, X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & empty(Z) & obj_tp(Z, shot) & holding(A, Z) & obj_tp(A, hand) & holding(D, Z) & obj_tp(D, hand) & not holding(D, X) & holding(V10, Z) & obj_tp(V10, hand) & used(Z, V9) & obj_tp(V9, beverage) <-
	!holding(D, X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & clean(Z) & obj_tp(Z, shot) & empty(Z) & ontable(Z) & holding(D, Z) & obj_tp(D, hand) & not holding(D, X) <-
	!holding(D, X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & shaked(X) & contains(X, V10) & obj_tp(V10, cocktail) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(V9, X) & obj_tp(V9, hand) & shaker_empty_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & shaker_level(X, V11) & obj_tp(V11, level) & clean(Z) & obj_tp(Z, shot) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(D, Z) & obj_tp(D, hand) & not holding(D, X) <-
	!holding(D, X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & shaked(X) & contains(X, V9) & obj_tp(V9, beverage) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(V11, X) & obj_tp(V11, hand) & shaker_level(X, V12) & obj_tp(V12, level) & next(B, V12) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & clean(Z) & obj_tp(Z, shot) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(D, Z) & obj_tp(D, hand) & not holding(D, X) <-
	!holding(D, X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & used(Z, Y) & obj_tp(Z, shot) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(D, Z) & obj_tp(D, hand) & not holding(D, X) <-
	!holding(D, X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & used(Z, Y) & obj_tp(Z, shot) & contains(Z, V10) & obj_tp(V10, beverage) & holding(A, Z) & obj_tp(A, hand) & holding(D, Z) & obj_tp(D, hand) & not holding(D, X) & holding(V9, Z) & obj_tp(V9, hand) <-
	!holding(D, X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & used(Z, Y) & obj_tp(Z, shot) & empty(Z) & ontable(Z) & holding(D, Z) & obj_tp(D, hand) & not holding(D, X) <-
	!holding(D, X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & shaked(X) & contains(X, V10) & obj_tp(V10, cocktail) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(V9, X) & obj_tp(V9, hand) & shaker_empty_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & shaker_level(X, V11) & obj_tp(V11, level) & used(Z, Y) & obj_tp(Z, shot) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(D, Z) & obj_tp(D, hand) & not holding(D, X) <-
	!holding(D, X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & shaked(X) & contains(X, V9) & obj_tp(V9, beverage) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(V11, X) & obj_tp(V11, hand) & shaker_level(X, V12) & obj_tp(V12, level) & next(B, V12) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & used(Z, Y) & obj_tp(Z, shot) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(D, Z) & obj_tp(D, hand) & not holding(D, X) <-
	!holding(D, X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & clean(Z) & obj_tp(Z, shot) & empty(Z) & not holding(D, Z) & holding(A, Z) & obj_tp(A, hand) <-
	!holding(D, Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & ontable(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & clean(Z) & obj_tp(Z, shot) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & handempty(D) & obj_tp(D, hand) & not holding(D, Z) <-
	!holding(D, Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & clean(Z) & obj_tp(Z, shot) & not holding(D, Z) & contains(Z, V10) & obj_tp(V10, beverage) & holding(A, Z) & obj_tp(A, hand) & holding(V9, Z) & obj_tp(V9, hand) <-
	!holding(D, Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & empty(Z) & obj_tp(Z, shot) & not holding(D, Z) & holding(A, Z) & obj_tp(A, hand) & holding(V10, Z) & obj_tp(V10, hand) & used(Z, V9) & obj_tp(V9, beverage) <-
	!holding(D, Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & clean(Z) & obj_tp(Z, shot) & empty(Z) & ontable(Z) & not holding(D, Z) <-
	!holding(D, Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & shaked(X) & contains(X, V10) & obj_tp(V10, cocktail) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(V9, X) & obj_tp(V9, hand) & shaker_empty_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & shaker_level(X, V11) & obj_tp(V11, level) & clean(Z) & obj_tp(Z, shot) & empty(Z) & not holding(D, Z) & holding(A, Z) & obj_tp(A, hand) <-
	!holding(D, Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & shaked(X) & contains(X, V9) & obj_tp(V9, beverage) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(V11, X) & obj_tp(V11, hand) & shaker_level(X, V12) & obj_tp(V12, level) & next(B, V12) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & clean(Z) & obj_tp(Z, shot) & empty(Z) & not holding(D, Z) & holding(A, Z) & obj_tp(A, hand) <-
	!holding(D, Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & used(Z, Y) & obj_tp(Z, shot) & empty(Z) & not holding(D, Z) & holding(A, Z) & obj_tp(A, hand) <-
	!holding(D, Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & ontable(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & used(Z, Y) & obj_tp(Z, shot) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & handempty(D) & obj_tp(D, hand) & not holding(D, Z) <-
	!holding(D, Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & used(Z, Y) & obj_tp(Z, shot) & not holding(D, Z) & contains(Z, V10) & obj_tp(V10, beverage) & holding(A, Z) & obj_tp(A, hand) & holding(V9, Z) & obj_tp(V9, hand) <-
	!holding(D, Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & used(Z, Y) & obj_tp(Z, shot) & empty(Z) & ontable(Z) & not holding(D, Z) <-
	!holding(D, Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & shaked(X) & contains(X, V10) & obj_tp(V10, cocktail) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(V9, X) & obj_tp(V9, hand) & shaker_empty_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & shaker_level(X, V11) & obj_tp(V11, level) & used(Z, Y) & obj_tp(Z, shot) & empty(Z) & not holding(D, Z) & holding(A, Z) & obj_tp(A, hand) <-
	!holding(D, Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & shaked(X) & contains(X, V9) & obj_tp(V9, beverage) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(V11, X) & obj_tp(V11, hand) & shaker_level(X, V12) & obj_tp(V12, level) & next(B, V12) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & used(Z, Y) & obj_tp(Z, shot) & empty(Z) & not holding(D, Z) & holding(A, Z) & obj_tp(A, hand) <-
	!holding(D, Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & shaked(A) & not ontable(A) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	!ontable(A);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, ingredient) & not ontable(X) <-
	!ontable(X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & not ontable(X) <-
	!ontable(X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, cocktail) & not ontable(X) <-
	!ontable(X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & clean(X) & empty(X) & contains(Z, Y) & obj_tp(Z, shot) & not ontable(Z) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	!ontable(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & handempty(D) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & clean(Z) & obj_tp(Z, shot) & empty(Z) & not ontable(Z) & holding(A, Z) & obj_tp(A, hand) <-
	!ontable(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & clean(Z) & empty(Z) & not ontable(Z) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	!ontable(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & handempty(D) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & used(Z, Y) & obj_tp(Z, shot) & empty(Z) & not ontable(Z) & holding(A, Z) & obj_tp(A, hand) <-
	!ontable(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & used(Z, Y) & empty(Z) & not ontable(Z) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	!ontable(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & unshaked(X) & contains(Z, Y) & obj_tp(Z, shot) & not ontable(Z) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	!ontable(Z);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & not shaked(A) & holding(Z, A) & obj_tp(Z, hand) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	!shaked(A);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & ontable(A) & not shaked(A) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	!shaked(A);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & not shaked(A) & holding(V7, X) & obj_tp(V7, hand) & holding(Z, A) & obj_tp(Z, hand) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) & used(X, D) & obj_tp(D, beverage) <-
	!shaked(A);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & not shaked(X) <-
	!shaked(X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & shaked(A) & holding(Z, A) & obj_tp(Z, hand) & next(C, B) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(A, B) <-
	!shaker_level(A, B);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & ontable(A) & shaked(A) & next(C, B) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(A, B) <-
	!shaker_level(A, B);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & unshaked(A) & contains(A, V7) & obj_tp(V7, ingredient) & cocktail_part1(D, V7) & obj_tp(D, cocktail) & cocktail_part2(D, V8) & obj_tp(V8, ingredient) & contains(A, V8) & holding(V9, A) & obj_tp(V9, hand) & holding(Z, A) & obj_tp(Z, hand) & next(C, B) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(A, B) <-
	!shaker_level(A, B);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & shaked(A) & holding(V7, X) & obj_tp(V7, hand) & holding(Z, A) & obj_tp(Z, hand) & used(X, D) & obj_tp(D, beverage) & next(C, B) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(A, B) <-
	!shaker_level(A, B);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & clean(X) & empty(X) & contains(Z, Y) & obj_tp(Z, shot) & holding(A, Z) & obj_tp(A, hand) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(X, B) <-
	!shaker_level(X, B);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & clean(X) & empty(X) & contains(Z, Y) & obj_tp(Z, shot) & ontable(Z) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(X, B) <-
	!shaker_level(X, B);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & contains(Z, Y) & obj_tp(Z, shot) & holding(A, Z) & obj_tp(A, hand) & holding(D, X) & obj_tp(D, hand) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(X, B) <-
	!shaker_level(X, B);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & clean(Z) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(X, B) <-
	!shaker_level(X, B);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & ontable(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(X, B) <-
	!shaker_level(X, B);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & handempty(D) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(X, B) <-
	!shaker_level(X, B);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & clean(Z) & contains(Z, V10) & obj_tp(V10, beverage) & holding(A, Z) & obj_tp(A, hand) & holding(V9, Z) & obj_tp(V9, hand) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(X, B) <-
	!shaker_level(X, B);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(V10, Z) & obj_tp(V10, hand) & used(Z, V9) & obj_tp(V9, beverage) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(X, B) <-
	!shaker_level(X, B);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & clean(Z) & empty(Z) & ontable(Z) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(X, B) <-
	!shaker_level(X, B);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & used(Z, Y) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(X, B) <-
	!shaker_level(X, B);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & used(Z, Y) & contains(Z, V10) & obj_tp(V10, beverage) & holding(A, Z) & obj_tp(A, hand) & holding(V9, Z) & obj_tp(V9, hand) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(X, B) <-
	!shaker_level(X, B);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & used(Z, Y) & empty(Z) & ontable(Z) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(X, B) <-
	!shaker_level(X, B);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & unshaked(X) & contains(Z, Y) & obj_tp(Z, shot) & holding(A, Z) & obj_tp(A, hand) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(X, B) <-
	!shaker_level(X, B);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & unshaked(X) & contains(Z, Y) & obj_tp(Z, shot) & ontable(Z) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(X, B) <-
	!shaker_level(X, B);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & shaked(X) & contains(X, V9) & obj_tp(V9, beverage) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & clean(Z) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(V11, X) & obj_tp(V11, hand) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & next(B, V12) & obj_tp(V12, level) & not shaker_level(X, V12) <-
	!shaker_level(X, V12);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & shaked(X) & contains(X, V9) & obj_tp(V9, beverage) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & used(Z, Y) & empty(Z) & holding(A, Z) & obj_tp(A, hand) & holding(V11, X) & obj_tp(V11, hand) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & next(B, V12) & obj_tp(V12, level) & not shaker_level(X, V12) <-
	!shaker_level(X, V12);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & not unshaked(A) & contains(A, V7) & obj_tp(V7, ingredient) & cocktail_part1(D, V7) & obj_tp(D, cocktail) & cocktail_part2(D, V8) & obj_tp(V8, ingredient) & contains(A, V8) & holding(V9, A) & obj_tp(V9, hand) & holding(Z, A) & obj_tp(Z, hand) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	!unshaked(A);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & not unshaked(X) <-
	!unshaked(X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, cocktail) & not unshaked(X) <-
	!unshaked(X);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shot) & obj_tp(Y, ingredient) & not used(X, Y) <-
	!used(X, Y);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & empty(Z) & not used(Z, Y) & holding(A, Z) & obj_tp(A, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	!used(Z, Y);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & ontable(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & empty(Z) & obj_tp(Z, shot) & not used(Z, Y) & holding(A, Z) & obj_tp(A, hand) & holding(D, Z) & obj_tp(D, hand) & handempty(D) <-
	!used(Z, Y);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & handempty(D) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & empty(Z) & obj_tp(Z, shot) & ontable(Z) & not used(Z, Y) & holding(A, Z) & obj_tp(A, hand) <-
	!used(Z, Y);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & not used(Z, Y) & contains(Z, V10) & obj_tp(V10, beverage) & holding(A, Z) & obj_tp(A, hand) & holding(V9, Z) & obj_tp(V9, hand) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	!used(Z, Y);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & empty(Z) & ontable(Z) & not used(Z, Y) & shaker_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	!used(Z, Y);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & shaked(X) & contains(X, V10) & obj_tp(V10, cocktail) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & empty(Z) & not used(Z, Y) & holding(A, Z) & obj_tp(A, hand) & holding(V9, X) & obj_tp(V9, hand) & shaker_empty_level(X, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) & shaker_level(X, V11) & obj_tp(V11, level) <-
	!used(Z, Y);
	!contains(X, Y).

+!contains(X, Y) : obj_tp(X, shaker) & obj_tp(Y, ingredient) & empty(X) & shaked(X) & contains(X, V9) & obj_tp(V9, beverage) & dispenses(V8, Y) & obj_tp(V8, dispenser) & holding(D, X) & obj_tp(D, hand) & holding(D, Z) & obj_tp(Z, shot) & empty(Z) & not used(Z, Y) & holding(A, Z) & obj_tp(A, hand) & holding(V11, X) & obj_tp(V11, hand) & shaker_level(X, V12) & obj_tp(V12, level) & next(B, V12) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	!used(Z, Y);
	!contains(X, Y).

+!empty(X) : obj_tp(X, shot) & contains(X, Y) & obj_tp(Y, ingredient) & holding(A, X) & obj_tp(A, hand) & empty(Z) & obj_tp(Z, shaker) & not clean(Z) & shaker_level(Z, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	!clean(Z);
	!empty(X).

+!empty(X) : obj_tp(X, shot) & ontable(X) & contains(X, Y) & obj_tp(Y, ingredient) & empty(Z) & obj_tp(Z, shaker) & not clean(Z) & shaker_level(Z, B) & obj_tp(B, level) & next(B, C) & obj_tp(C, level) <-
	!clean(Z);
	!empty(X).

+!empty(X) : obj_tp(X, shaker) & unshaked(X) & contains(X, V7) & obj_tp(V7, ingredient) & cocktail_part2(C, V7) & obj_tp(C, cocktail) & cocktail_part1(C, D) & obj_tp(D, ingredient) & not contains(X, D) & contains(X, Z) & obj_tp(Z, cocktail) & holding(V8, X) & obj_tp(V8, hand) & holding(Y, X) & obj_tp(Y, hand) & shaker_empty_level(X, B) & obj_tp(B, level) & shaker_level(X, A) & obj_tp(A, level) <-
	!contains(X, D);
	!empty(X).

+!empty(X) : obj_tp(X, shaker) & unshaked(X) & contains(X, D) & obj_tp(D, ingredient) & cocktail_part1(C, D) & obj_tp(C, cocktail) & cocktail_part2(C, V7) & obj_tp(V7, ingredient) & not contains(X, V7) & contains(X, Z) & obj_tp(Z, cocktail) & holding(V8, X) & obj_tp(V8, hand) & holding(Y, X) & obj_tp(Y, hand) & shaker_empty_level(X, B) & obj_tp(B, level) & shaker_level(X, A) & obj_tp(A, level) <-
	!contains(X, V7);
	!empty(X).

+!empty(X) : obj_tp(X, shaker) & not ontable(X) <-
	!ontable(X);
	!empty(X).

+!empty(X) : obj_tp(X, shot) & not ontable(X) <-
	!ontable(X);
	!empty(X).

+!empty(X) : obj_tp(X, shaker) & not shaked(X) <-
	!shaked(X);
	!empty(X).

+!empty(X) : obj_tp(X, shot) & contains(X, Y) & obj_tp(Y, ingredient) & holding(A, X) & obj_tp(A, hand) & clean(Z) & obj_tp(Z, shaker) & empty(Z) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(Z, B) <-
	!shaker_level(Z, B);
	!empty(X).

+!empty(X) : obj_tp(X, shot) & ontable(X) & contains(X, Y) & obj_tp(Y, ingredient) & clean(Z) & obj_tp(Z, shaker) & empty(Z) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(Z, B) <-
	!shaker_level(Z, B);
	!empty(X).

+!empty(X) : obj_tp(X, shot) & contains(X, Y) & obj_tp(Y, ingredient) & holding(A, X) & obj_tp(A, hand) & empty(Z) & obj_tp(Z, shaker) & holding(D, Z) & obj_tp(D, hand) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(Z, B) <-
	!shaker_level(Z, B);
	!empty(X).

+!empty(X) : obj_tp(X, shot) & contains(X, Y) & obj_tp(Y, ingredient) & holding(A, X) & obj_tp(A, hand) & unshaked(Z) & obj_tp(Z, shaker) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(Z, B) <-
	!shaker_level(Z, B);
	!empty(X).

+!empty(X) : obj_tp(X, shot) & ontable(X) & contains(X, Y) & obj_tp(Y, ingredient) & unshaked(Z) & obj_tp(Z, shaker) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(Z, B) <-
	!shaker_level(Z, B);
	!empty(X).

+!empty(X) : obj_tp(X, shot) & contains(X, Y) & obj_tp(Y, ingredient) & holding(A, X) & obj_tp(A, hand) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & shaker_level(Z, B) & obj_tp(Z, shaker) & not unshaked(Z) <-
	!unshaked(Z);
	!empty(X).

+!empty(X) : obj_tp(X, shot) & ontable(X) & contains(X, Y) & obj_tp(Y, ingredient) & next(B, C) & obj_tp(B, level) & obj_tp(C, level) & shaker_level(Z, B) & obj_tp(Z, shaker) & not unshaked(Z) <-
	!unshaked(Z);
	!empty(X).

+!holding(X, Y) : obj_tp(X, hand) & obj_tp(Y, container) & not handempty(X) <-
	!handempty(X);
	!holding(X, Y).

+!holding(X, Y) : obj_tp(X, hand) & obj_tp(Y, container) & not ontable(Y) <-
	!ontable(Y);
	!holding(X, Y).

+!shaked(X) : obj_tp(X, shaker) & unshaked(X) & contains(X, Z) & obj_tp(Z, ingredient) & cocktail_part1(Y, Z) & obj_tp(Y, cocktail) & cocktail_part2(Y, A) & obj_tp(A, ingredient) & not contains(X, A) & holding(B, X) & obj_tp(B, hand) <-
	!contains(X, A);
	!shaked(X).

+!shaked(X) : obj_tp(X, shaker) & ontable(X) & unshaked(X) & contains(X, Z) & obj_tp(Z, ingredient) & cocktail_part1(Y, Z) & obj_tp(Y, cocktail) & cocktail_part2(Y, A) & obj_tp(A, ingredient) & not contains(X, A) <-
	!contains(X, A);
	!shaked(X).

+!shaked(X) : obj_tp(X, shaker) & unshaked(X) & contains(X, A) & obj_tp(A, ingredient) & cocktail_part2(Y, A) & obj_tp(Y, cocktail) & cocktail_part1(Y, Z) & obj_tp(Z, ingredient) & not contains(X, Z) & holding(B, X) & obj_tp(B, hand) <-
	!contains(X, Z);
	!shaked(X).

+!shaked(X) : obj_tp(X, shaker) & ontable(X) & unshaked(X) & contains(X, A) & obj_tp(A, ingredient) & cocktail_part2(Y, A) & obj_tp(Y, cocktail) & cocktail_part1(Y, Z) & obj_tp(Z, ingredient) & not contains(X, Z) <-
	!contains(X, Z);
	!shaked(X).

+!shaked(X) : obj_tp(X, shaker) & not ontable(X) <-
	!ontable(X);
	!shaked(X).

+!shaked(X) : obj_tp(X, shaker) & not unshaked(X) <-
	!unshaked(X);
	!shaked(X).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & shaked(X) & contains(X, Z) & obj_tp(Z, beverage) & holding(B, X) & obj_tp(B, hand) & holding(B, A) & obj_tp(A, shot) & empty(A) & not clean(A) & next(Y, C) & obj_tp(C, level) & shaker_level(X, C) <-
	!clean(A);
	!shaker_level(X, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & ontable(X) & shaked(X) & contains(X, Z) & obj_tp(Z, beverage) & next(Y, C) & obj_tp(C, level) & shaker_level(X, C) & empty(A) & obj_tp(A, shot) & not clean(A) & holding(B, A) & obj_tp(B, hand) & handempty(B) <-
	!clean(A);
	!shaker_level(X, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & unshaked(X) & contains(X, V7) & obj_tp(V7, ingredient) & cocktail_part1(D, V7) & obj_tp(D, cocktail) & cocktail_part2(D, V8) & obj_tp(V8, ingredient) & contains(X, V8) & contains(X, Z) & obj_tp(Z, beverage) & holding(B, X) & obj_tp(B, hand) & holding(B, A) & obj_tp(A, shot) & empty(A) & not clean(A) & holding(V9, X) & obj_tp(V9, hand) & next(Y, C) & obj_tp(C, level) & shaker_level(X, C) <-
	!clean(A);
	!shaker_level(X, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & shaker_empty_level(X, Y) & unshaked(X) & contains(X, A) & obj_tp(A, cocktail) & contains(X, V7) & obj_tp(V7, ingredient) & cocktail_part2(C, V7) & obj_tp(C, cocktail) & cocktail_part1(C, D) & obj_tp(D, ingredient) & not contains(X, D) & holding(V8, X) & obj_tp(V8, hand) & holding(Z, X) & obj_tp(Z, hand) & shaker_level(X, B) & obj_tp(B, level) <-
	!contains(X, D);
	!shaker_level(X, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & shaker_empty_level(X, Y) & unshaked(X) & contains(X, A) & obj_tp(A, cocktail) & contains(X, D) & obj_tp(D, ingredient) & cocktail_part1(C, D) & obj_tp(C, cocktail) & cocktail_part2(C, V7) & obj_tp(V7, ingredient) & not contains(X, V7) & holding(V8, X) & obj_tp(V8, hand) & holding(Z, X) & obj_tp(Z, hand) & shaker_level(X, B) & obj_tp(B, level) <-
	!contains(X, V7);
	!shaker_level(X, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & unshaked(X) & contains(X, V8) & obj_tp(V8, ingredient) & cocktail_part2(D, V8) & obj_tp(D, cocktail) & cocktail_part1(D, V7) & obj_tp(V7, ingredient) & not contains(X, V7) & contains(X, Z) & obj_tp(Z, beverage) & holding(B, X) & obj_tp(B, hand) & holding(B, A) & obj_tp(A, shot) & clean(A) & empty(A) & holding(V9, X) & obj_tp(V9, hand) & next(Y, C) & obj_tp(C, level) & shaker_level(X, C) <-
	!contains(X, V7);
	!shaker_level(X, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & unshaked(X) & contains(X, V7) & obj_tp(V7, ingredient) & cocktail_part1(D, V7) & obj_tp(D, cocktail) & cocktail_part2(D, V8) & obj_tp(V8, ingredient) & not contains(X, V8) & contains(X, Z) & obj_tp(Z, beverage) & holding(B, X) & obj_tp(B, hand) & holding(B, A) & obj_tp(A, shot) & clean(A) & empty(A) & holding(V9, X) & obj_tp(V9, hand) & next(Y, C) & obj_tp(C, level) & shaker_level(X, C) <-
	!contains(X, V8);
	!shaker_level(X, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & shaked(X) & contains(X, Z) & obj_tp(Z, beverage) & holding(B, X) & obj_tp(B, hand) & holding(B, A) & obj_tp(A, shot) & clean(A) & not empty(A) & next(Y, C) & obj_tp(C, level) & shaker_level(X, C) <-
	!empty(A);
	!shaker_level(X, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & ontable(X) & shaked(X) & contains(X, Z) & obj_tp(Z, beverage) & next(Y, C) & obj_tp(C, level) & shaker_level(X, C) & clean(A) & obj_tp(A, shot) & not empty(A) & holding(B, A) & obj_tp(B, hand) & handempty(B) <-
	!empty(A);
	!shaker_level(X, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & unshaked(X) & contains(X, V7) & obj_tp(V7, ingredient) & cocktail_part1(D, V7) & obj_tp(D, cocktail) & cocktail_part2(D, V8) & obj_tp(V8, ingredient) & contains(X, V8) & contains(X, Z) & obj_tp(Z, beverage) & holding(B, X) & obj_tp(B, hand) & holding(B, A) & obj_tp(A, shot) & clean(A) & not empty(A) & holding(V9, X) & obj_tp(V9, hand) & next(Y, C) & obj_tp(C, level) & shaker_level(X, C) <-
	!empty(A);
	!shaker_level(X, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & shaked(X) & contains(X, Z) & obj_tp(Z, beverage) & holding(B, X) & obj_tp(B, hand) & next(Y, C) & obj_tp(C, level) & shaker_level(X, C) & holding(V7, A) & obj_tp(A, shot) & obj_tp(V7, hand) & not empty(A) & used(A, D) & obj_tp(D, beverage) <-
	!empty(A);
	!shaker_level(X, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & ontable(X) & shaked(X) & contains(X, Z) & obj_tp(Z, beverage) & next(Y, C) & obj_tp(C, level) & shaker_level(X, C) & clean(A) & obj_tp(A, shot) & empty(A) & holding(B, A) & obj_tp(B, hand) & not handempty(B) <-
	!handempty(B);
	!shaker_level(X, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & shaked(X) & contains(X, Z) & obj_tp(Z, beverage) & holding(B, X) & obj_tp(B, hand) & next(Y, C) & obj_tp(C, level) & shaker_level(X, C) & clean(A) & obj_tp(A, shot) & empty(A) & not holding(B, A) <-
	!holding(B, A);
	!shaker_level(X, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & ontable(X) & shaked(X) & contains(X, Z) & obj_tp(Z, beverage) & next(Y, C) & obj_tp(C, level) & shaker_level(X, C) & clean(A) & obj_tp(A, shot) & empty(A) & handempty(B) & obj_tp(B, hand) & not holding(B, A) <-
	!holding(B, A);
	!shaker_level(X, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & unshaked(X) & contains(X, V7) & obj_tp(V7, ingredient) & cocktail_part1(D, V7) & obj_tp(D, cocktail) & cocktail_part2(D, V8) & obj_tp(V8, ingredient) & contains(X, V8) & contains(X, Z) & obj_tp(Z, beverage) & holding(B, X) & obj_tp(B, hand) & holding(V9, X) & obj_tp(V9, hand) & next(Y, C) & obj_tp(C, level) & shaker_level(X, C) & clean(A) & obj_tp(A, shot) & empty(A) & not holding(B, A) <-
	!holding(B, A);
	!shaker_level(X, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & shaked(X) & contains(X, Z) & obj_tp(Z, beverage) & holding(B, X) & obj_tp(B, hand) & next(Y, C) & obj_tp(C, level) & shaker_level(X, C) & empty(A) & obj_tp(A, shot) & not holding(B, A) & holding(V7, A) & obj_tp(V7, hand) & used(A, D) & obj_tp(D, beverage) <-
	!holding(B, A);
	!shaker_level(X, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & shaked(X) & contains(X, Z) & obj_tp(Z, beverage) & next(Y, C) & obj_tp(C, level) & shaker_level(X, C) & clean(A) & obj_tp(A, shot) & empty(A) & holding(B, A) & obj_tp(B, hand) & not holding(B, X) <-
	!holding(B, X);
	!shaker_level(X, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & unshaked(X) & contains(X, V7) & obj_tp(V7, ingredient) & cocktail_part1(D, V7) & obj_tp(D, cocktail) & cocktail_part2(D, V8) & obj_tp(V8, ingredient) & contains(X, V8) & contains(X, Z) & obj_tp(Z, beverage) & holding(V9, X) & obj_tp(V9, hand) & next(Y, C) & obj_tp(C, level) & shaker_level(X, C) & clean(A) & obj_tp(A, shot) & empty(A) & holding(B, A) & obj_tp(B, hand) & not holding(B, X) <-
	!holding(B, X);
	!shaker_level(X, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & shaked(X) & contains(X, Z) & obj_tp(Z, beverage) & next(Y, C) & obj_tp(C, level) & shaker_level(X, C) & empty(A) & obj_tp(A, shot) & holding(B, A) & obj_tp(B, hand) & not holding(B, X) & holding(V7, A) & obj_tp(V7, hand) & used(A, D) & obj_tp(D, beverage) <-
	!holding(B, X);
	!shaker_level(X, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & not ontable(X) <-
	!ontable(X);
	!shaker_level(X, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & not shaked(X) <-
	!shaked(X);
	!shaker_level(X, Y).

+!shaker_level(X, Y) : obj_tp(X, shaker) & obj_tp(Y, level) & not unshaked(X) <-
	!unshaked(X);
	!shaker_level(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, ingredient) & not clean(X) <-
	!clean(X);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & not clean(X) <-
	!clean(X);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & unshaked(A) & contains(A, V8) & obj_tp(V8, ingredient) & cocktail_part2(D, V8) & obj_tp(D, cocktail) & cocktail_part1(D, V7) & obj_tp(V7, ingredient) & not contains(A, V7) & holding(V9, A) & obj_tp(V9, hand) & holding(Z, A) & obj_tp(Z, hand) & holding(Z, X) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	!contains(A, V7);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & unshaked(A) & contains(A, V7) & obj_tp(V7, ingredient) & cocktail_part1(D, V7) & obj_tp(D, cocktail) & cocktail_part2(D, V8) & obj_tp(V8, ingredient) & not contains(A, V8) & holding(V9, A) & obj_tp(V9, hand) & holding(Z, A) & obj_tp(Z, hand) & holding(Z, X) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	!contains(A, V8);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & holding(Z, X) & obj_tp(Z, hand) & holding(Z, A) & obj_tp(A, shaker) & shaked(A) & not contains(A, Y) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	!contains(A, Y);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & holding(Z, X) & obj_tp(Z, hand) & handempty(Z) & ontable(A) & obj_tp(A, shaker) & shaked(A) & not contains(A, Y) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	!contains(A, Y);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & holding(Z, X) & obj_tp(Z, hand) & holding(Z, A) & obj_tp(A, shaker) & unshaked(A) & not contains(A, Y) & contains(A, V7) & obj_tp(V7, ingredient) & cocktail_part1(D, V7) & obj_tp(D, cocktail) & cocktail_part2(D, V8) & obj_tp(V8, ingredient) & contains(A, V8) & holding(V9, A) & obj_tp(V9, hand) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	!contains(A, Y);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & empty(X) & holding(V7, X) & obj_tp(V7, hand) & used(X, D) & obj_tp(D, beverage) & shaked(A) & obj_tp(A, shaker) & not contains(A, Y) & holding(Z, A) & obj_tp(Z, hand) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	!contains(A, Y);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, ingredient) & not empty(X) <-
	!empty(X);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & not empty(X) <-
	!empty(X);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & ontable(A) & shaked(A) & holding(Z, X) & obj_tp(Z, hand) & not handempty(Z) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	!handempty(Z);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & shaked(A) & holding(Z, X) & obj_tp(Z, hand) & not holding(Z, A) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	!holding(Z, A);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & unshaked(A) & contains(A, V7) & obj_tp(V7, ingredient) & cocktail_part1(D, V7) & obj_tp(D, cocktail) & cocktail_part2(D, V8) & obj_tp(V8, ingredient) & contains(A, V8) & holding(V9, A) & obj_tp(V9, hand) & holding(Z, X) & obj_tp(Z, hand) & not holding(Z, A) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	!holding(Z, A);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & shaked(A) & holding(V7, X) & obj_tp(V7, hand) & holding(Z, X) & obj_tp(Z, hand) & not holding(Z, A) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) & used(X, D) & obj_tp(D, beverage) <-
	!holding(Z, A);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & shaked(A) & holding(Z, A) & obj_tp(Z, hand) & not holding(Z, X) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	!holding(Z, X);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & ontable(A) & shaked(A) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) & handempty(Z) & obj_tp(Z, hand) & not holding(Z, X) <-
	!holding(Z, X);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & unshaked(A) & contains(A, V7) & obj_tp(V7, ingredient) & cocktail_part1(D, V7) & obj_tp(D, cocktail) & cocktail_part2(D, V8) & obj_tp(V8, ingredient) & contains(A, V8) & holding(V9, A) & obj_tp(V9, hand) & holding(Z, A) & obj_tp(Z, hand) & not holding(Z, X) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	!holding(Z, X);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & shaked(A) & holding(V7, X) & obj_tp(V7, hand) & holding(Z, A) & obj_tp(Z, hand) & not holding(Z, X) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) & used(X, D) & obj_tp(D, beverage) <-
	!holding(Z, X);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & shaked(A) & not ontable(A) & holding(Z, X) & obj_tp(Z, hand) & handempty(Z) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	!ontable(A);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, ingredient) & not ontable(X) <-
	!ontable(X);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & not shaked(A) & holding(Z, A) & obj_tp(Z, hand) & holding(Z, X) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	!shaked(A);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & ontable(A) & not shaked(A) & holding(Z, X) & obj_tp(Z, hand) & handempty(Z) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	!shaked(A);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & not shaked(A) & holding(V7, X) & obj_tp(V7, hand) & holding(Z, A) & obj_tp(Z, hand) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) & used(X, D) & obj_tp(D, beverage) <-
	!shaked(A);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & shaked(A) & holding(Z, A) & obj_tp(Z, hand) & holding(Z, X) & next(C, B) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(A, B) <-
	!shaker_level(A, B);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & ontable(A) & shaked(A) & holding(Z, X) & obj_tp(Z, hand) & handempty(Z) & next(C, B) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(A, B) <-
	!shaker_level(A, B);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & unshaked(A) & contains(A, V7) & obj_tp(V7, ingredient) & cocktail_part1(D, V7) & obj_tp(D, cocktail) & cocktail_part2(D, V8) & obj_tp(V8, ingredient) & contains(A, V8) & holding(V9, A) & obj_tp(V9, hand) & holding(Z, A) & obj_tp(Z, hand) & holding(Z, X) & next(C, B) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(A, B) <-
	!shaker_level(A, B);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & shaked(A) & holding(V7, X) & obj_tp(V7, hand) & holding(Z, A) & obj_tp(Z, hand) & used(X, D) & obj_tp(D, beverage) & next(C, B) & obj_tp(B, level) & obj_tp(C, level) & not shaker_level(A, B) <-
	!shaker_level(A, B);
	!used(X, Y).

+!used(X, Y) : obj_tp(X, shot) & obj_tp(Y, beverage) & clean(X) & empty(X) & contains(A, Y) & obj_tp(A, shaker) & not unshaked(A) & contains(A, V7) & obj_tp(V7, ingredient) & cocktail_part1(D, V7) & obj_tp(D, cocktail) & cocktail_part2(D, V8) & obj_tp(V8, ingredient) & contains(A, V8) & holding(V9, A) & obj_tp(V9, hand) & holding(Z, A) & obj_tp(Z, hand) & holding(Z, X) & shaker_level(A, B) & obj_tp(B, level) & next(C, B) & obj_tp(C, level) <-
	!unshaked(A);
	!used(X, Y).
