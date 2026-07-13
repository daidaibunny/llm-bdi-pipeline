/* Generated AgentSpeak(L) Plan Library */
/* Domain: satellite */

+!calibrated(X) : calibrated(X) <-
	true.

+!have_image(X, Y) : have_image(X, Y) <-
	true.

+!pointing(X, Y) : pointing(X, Y) <-
	true.

+!power_avail(X) : power_avail(X) <-
	true.

+!power_on(X) : power_on(X) <-
	true.

+!calibrated(X) : obj_tp(X, instrument) & power_on(X) & calibration_target(X, Z) & obj_tp(Z, direction) & on_board(X, Y) & obj_tp(Y, satellite) & pointing(Y, Z) <-
	calibrate(Y, X, Z).

+!calibrated(X) : obj_tp(X, instrument) & calibration_target(X, Z) & obj_tp(Z, direction) & on_board(X, A) & obj_tp(A, satellite) & power_avail(A) & on_board(X, Y) & obj_tp(Y, satellite) & pointing(Y, Z) <-
	switch_on(X, A);
	calibrate(Y, X, Z).

+!have_image(X, Y) : obj_tp(X, direction) & obj_tp(Y, mode) & pointing(Z, X) & obj_tp(Z, satellite) & on_board(A, Z) & obj_tp(A, instrument) & supports(A, Y) & power_on(A) & calibration_target(A, C) & obj_tp(C, direction) & on_board(A, B) & obj_tp(B, satellite) & pointing(B, C) <-
	calibrate(B, A, C);
	take_image(Z, X, A, Y).

+!have_image(X, Y) : obj_tp(X, direction) & obj_tp(Y, mode) & pointing(A, X) & obj_tp(A, satellite) & on_board(Z, A) & obj_tp(Z, instrument) & supports(Z, Y) & calibrated(Z) & power_on(Z) <-
	take_image(A, X, Z, Y).

+!have_image(X, Y) : obj_tp(X, direction) & obj_tp(Y, mode) & supports(A, Y) & obj_tp(A, instrument) & calibrated(A) & power_on(A) & on_board(A, B) & obj_tp(B, satellite) & pointing(B, Z) & obj_tp(Z, direction) & X \== Z <-
	turn_to(B, X, Z);
	take_image(B, X, A, Y).

+!have_image(X, Y) : obj_tp(X, direction) & obj_tp(Y, mode) & calibration_target(Z, X) & obj_tp(Z, instrument) & supports(Z, Y) & power_on(Z) & on_board(Z, A) & obj_tp(A, satellite) & pointing(A, X) <-
	calibrate(A, Z, X);
	take_image(A, X, Z, Y).

+!have_image(X, Y) : obj_tp(X, direction) & obj_tp(Y, mode) & calibration_target(A, X) & obj_tp(A, instrument) & supports(A, Y) & power_on(A) & on_board(A, B) & obj_tp(B, satellite) & pointing(B, Z) & obj_tp(Z, direction) & X \== Z <-
	turn_to(B, X, Z);
	calibrate(B, A, X);
	take_image(B, X, A, Y).

+!have_image(X, Y) : obj_tp(X, direction) & obj_tp(Y, mode) & calibration_target(Z, X) & obj_tp(Z, instrument) & supports(Z, Y) & on_board(Z, A) & obj_tp(A, satellite) & pointing(A, X) & power_avail(A) <-
	switch_on(Z, A);
	calibrate(A, Z, X);
	take_image(A, X, Z, Y).

+!have_image(X, Y) : obj_tp(X, direction) & obj_tp(Y, mode) & supports(A, Y) & obj_tp(A, instrument) & power_on(A) & calibration_target(A, Z) & obj_tp(Z, direction) & X \== Z & on_board(A, B) & obj_tp(B, satellite) & pointing(B, Z) <-
	calibrate(B, A, Z);
	turn_to(B, X, Z);
	take_image(B, X, A, Y).

+!have_image(X, Y) : obj_tp(X, direction) & obj_tp(Y, mode) & supports(B, Y) & obj_tp(B, instrument) & power_on(B) & calibration_target(B, Z) & obj_tp(Z, direction) & X \== Z & on_board(B, C) & obj_tp(C, satellite) & pointing(C, A) & obj_tp(A, direction) & A \== X & A \== Z <-
	turn_to(C, Z, A);
	calibrate(C, B, Z);
	turn_to(C, X, Z);
	take_image(C, X, B, Y).

+!have_image(X, Y) : obj_tp(X, direction) & obj_tp(Y, mode) & pointing(B, X) & obj_tp(B, satellite) & on_board(A, B) & obj_tp(A, instrument) & supports(A, Y) & power_on(A) & calibration_target(A, Z) & obj_tp(Z, direction) & X \== Z <-
	turn_to(B, Z, X);
	calibrate(B, A, Z);
	turn_to(B, X, Z);
	take_image(B, X, A, Y).

+!have_image(X, Y) : obj_tp(X, direction) & obj_tp(Y, mode) & calibration_target(A, X) & obj_tp(A, instrument) & supports(A, Y) & on_board(A, B) & obj_tp(B, satellite) & power_avail(B) & pointing(B, Z) & obj_tp(Z, direction) & X \== Z <-
	switch_on(A, B);
	turn_to(B, X, Z);
	calibrate(B, A, X);
	take_image(B, X, A, Y).

+!have_image(X, Y) : obj_tp(X, direction) & obj_tp(Y, mode) & supports(A, Y) & obj_tp(A, instrument) & calibration_target(A, Z) & obj_tp(Z, direction) & X \== Z & on_board(A, B) & obj_tp(B, satellite) & pointing(B, Z) & power_avail(B) <-
	switch_on(A, B);
	calibrate(B, A, Z);
	turn_to(B, X, Z);
	take_image(B, X, A, Y).

+!have_image(X, Y) : obj_tp(X, direction) & obj_tp(Y, mode) & supports(B, Y) & obj_tp(B, instrument) & calibration_target(B, Z) & obj_tp(Z, direction) & X \== Z & on_board(B, C) & obj_tp(C, satellite) & power_avail(C) & pointing(C, A) & obj_tp(A, direction) & A \== X & A \== Z <-
	switch_on(B, C);
	turn_to(C, Z, A);
	calibrate(C, B, Z);
	turn_to(C, X, Z);
	take_image(C, X, B, Y).

+!have_image(X, Y) : obj_tp(X, direction) & obj_tp(Y, mode) & supports(B, Y) & obj_tp(B, instrument) & calibration_target(B, Z) & obj_tp(Z, direction) & X \== Z & on_board(B, C) & obj_tp(C, satellite) & pointing(C, Z) & on_board(A, C) & obj_tp(A, instrument) & A \== B & power_on(A) <-
	switch_off(A, C);
	switch_on(B, C);
	calibrate(C, B, Z);
	turn_to(C, X, Z);
	take_image(C, X, B, Y).

+!have_image(X, Y) : obj_tp(X, direction) & obj_tp(Y, mode) & pointing(B, X) & obj_tp(B, satellite) & power_avail(B) & on_board(A, B) & obj_tp(A, instrument) & supports(A, Y) & calibration_target(A, Z) & obj_tp(Z, direction) & X \== Z <-
	switch_on(A, B);
	turn_to(B, Z, X);
	calibrate(B, A, Z);
	turn_to(B, X, Z);
	take_image(B, X, A, Y).

+!have_image(X, Y) : obj_tp(X, direction) & obj_tp(Y, mode) & calibration_target(B, X) & obj_tp(B, instrument) & supports(B, Y) & on_board(B, C) & obj_tp(C, satellite) & on_board(A, C) & obj_tp(A, instrument) & A \== B & power_on(A) & pointing(C, Z) & obj_tp(Z, direction) & X \== Z <-
	switch_off(A, C);
	switch_on(B, C);
	turn_to(C, X, Z);
	calibrate(C, B, X);
	take_image(C, X, B, Y).

+!pointing(X, Y) : obj_tp(X, satellite) & obj_tp(Y, direction) & not pointing(X, Y) & pointing(X, Z) & obj_tp(Z, direction) & Y \== Z <-
	turn_to(X, Y, Z).

+!pointing(X, Y) : obj_tp(X, satellite) & obj_tp(Y, direction) & pointing(X, Z) & obj_tp(Z, direction) & Y \== Z <-
	turn_to(X, Y, Z).

+!power_avail(X) : obj_tp(X, satellite) & on_board(Y, X) & obj_tp(Y, instrument) & power_on(Y) <-
	switch_off(Y, X).

+!power_avail(X) : obj_tp(X, satellite) & on_board(Y, X) & obj_tp(Y, instrument) & on_board(Y, Z) & obj_tp(Z, satellite) & X \== Z & power_avail(Z) <-
	switch_on(Y, Z);
	switch_off(Y, X).

+!power_on(X) : obj_tp(X, instrument) & on_board(X, Y) & obj_tp(Y, satellite) & power_avail(Y) <-
	switch_on(X, Y).

+!power_on(X) : obj_tp(X, instrument) & on_board(X, Y) & obj_tp(Y, satellite) & on_board(Z, Y) & obj_tp(Z, instrument) & X \== Z & power_on(Z) <-
	switch_off(Z, Y);
	switch_on(X, Y).

+!calibrated(X) : obj_tp(X, instrument) & power_on(X) & calibration_target(X, Z) & obj_tp(Z, direction) & on_board(X, Y) & obj_tp(Y, satellite) & not pointing(Y, Z) <-
	!pointing(Y, Z);
	!calibrated(X).

+!calibrated(X) : obj_tp(X, instrument) & calibration_target(X, Z) & obj_tp(Z, direction) & on_board(X, A) & obj_tp(A, satellite) & power_avail(A) & on_board(X, Y) & obj_tp(Y, satellite) & not pointing(Y, Z) <-
	!pointing(Y, Z);
	!calibrated(X).

+!calibrated(X) : obj_tp(X, instrument) & calibration_target(X, Z) & obj_tp(Z, direction) & on_board(X, A) & obj_tp(A, satellite) & not power_avail(A) & on_board(X, Y) & obj_tp(Y, satellite) & pointing(Y, Z) <-
	!power_avail(A);
	!calibrated(X).

+!calibrated(X) : obj_tp(X, instrument) & not power_on(X) <-
	!power_on(X);
	!calibrated(X).

+!have_image(X, Y) : obj_tp(X, direction) & obj_tp(Y, mode) & supports(A, Y) & obj_tp(A, instrument) & power_on(A) & not calibrated(A) & calibration_target(A, C) & on_board(A, B) & on_board(A, D) & on_board(A, Z) & obj_tp(Z, satellite) <-
	!calibrated(A);
	!have_image(X, Y).

+!have_image(X, Y) : obj_tp(X, direction) & obj_tp(Y, mode) & pointing(Z, X) & obj_tp(Z, satellite) & on_board(A, Z) & obj_tp(A, instrument) & supports(A, Y) & power_on(A) & calibration_target(A, C) & obj_tp(C, direction) & on_board(A, B) & obj_tp(B, satellite) & not pointing(B, C) <-
	!pointing(B, C);
	!have_image(X, Y).

+!have_image(X, Y) : obj_tp(X, direction) & obj_tp(Y, mode) & supports(A, Y) & obj_tp(A, instrument) & calibration_target(A, C) & on_board(A, B) & on_board(A, D) & on_board(A, Z) & obj_tp(Z, satellite) & not pointing(Z, X) <-
	!pointing(Z, X);
	!have_image(X, Y).

+!have_image(X, Y) : obj_tp(X, direction) & obj_tp(Y, mode) & supports(A, Y) & obj_tp(A, instrument) & power_on(A) & calibration_target(A, C) & obj_tp(C, direction) & on_board(A, B) & obj_tp(B, satellite) & pointing(B, C) & on_board(A, Z) & obj_tp(Z, satellite) & not pointing(Z, X) <-
	!pointing(Z, X);
	!have_image(X, Y).

+!have_image(X, Y) : obj_tp(X, direction) & obj_tp(Y, mode) & supports(A, Y) & obj_tp(A, instrument) & calibrated(A) & not power_on(A) & calibration_target(A, C) & on_board(A, B) & on_board(A, D) & on_board(A, Z) & obj_tp(Z, satellite) <-
	!power_on(A);
	!have_image(X, Y).

+!have_image(X, Y) : obj_tp(X, direction) & obj_tp(Y, mode) & pointing(Z, X) & obj_tp(Z, satellite) & on_board(A, Z) & obj_tp(A, instrument) & supports(A, Y) & not power_on(A) & calibration_target(A, C) & obj_tp(C, direction) & on_board(A, B) & obj_tp(B, satellite) & pointing(B, C) <-
	!power_on(A);
	!have_image(X, Y).

+!power_avail(X) : obj_tp(X, satellite) & on_board(Y, X) & obj_tp(Y, instrument) & not power_on(Y) <-
	!power_on(Y);
	!power_avail(X).

+!power_on(X) : obj_tp(X, instrument) & on_board(X, Y) & obj_tp(Y, satellite) & not power_avail(Y) <-
	!power_avail(Y);
	!power_on(X).
