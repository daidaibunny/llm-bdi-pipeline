/* Generated AgentSpeak(L) Plan Library */
/* Domain: rovers */

+!at(X, Y) : at(X, Y) <-
	true.

+!calibrated(X, Y) : calibrated(X, Y) <-
	true.

+!communicated_image_data(X, Y) : communicated_image_data(X, Y) <-
	true.

+!communicated_rock_data(X) : communicated_rock_data(X) <-
	true.

+!communicated_soil_data(X) : communicated_soil_data(X) <-
	true.

+!empty(X) : empty(X) <-
	true.

+!full(X) : full(X) <-
	true.

+!have_image(X, Y, Z) : have_image(X, Y, Z) <-
	true.

+!have_rock_analysis(X, Y) : have_rock_analysis(X, Y) <-
	true.

+!have_soil_analysis(X, Y) : have_soil_analysis(X, Y) <-
	true.

+!at(X, Y) : obj_tp(X, rover) & obj_tp(Y, waypoint) & at(X, Z) & obj_tp(Z, waypoint) & Y \== Z <-
	navigate(X, Z, Y).

+!calibrated(X, Y) : obj_tp(X, camera) & obj_tp(Y, rover) & on_board(X, Y) & equipped_for_imaging(Y) & at(Y, A) & obj_tp(A, waypoint) & calibration_target(X, Z) & obj_tp(Z, objective) & visible_from(Z, A) <-
	calibrate(Y, X, Z, A).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & have_image(Z, X, Y) & obj_tp(Z, rover) & at(Z, B) & obj_tp(B, waypoint) & visible(B, C) & obj_tp(C, waypoint) & at_lander(A, C) & obj_tp(A, lander) <-
	communicate_image_data(Z, A, X, Y, B, C).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibrated(Z, B) & obj_tp(B, rover) & on_board(Z, B) & equipped_for_imaging(B) & at(B, C) & obj_tp(C, waypoint) & visible_from(X, C) & visible(C, D) & obj_tp(D, waypoint) & at_lander(A, D) & obj_tp(A, lander) <-
	take_image(B, C, X, Z, Y);
	communicate_image_data(B, A, X, Y, C, D).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & have_image(A, X, Y) & obj_tp(A, rover) & at(A, B) & obj_tp(B, waypoint) & at_lander(Z, D) & obj_tp(D, waypoint) & obj_tp(Z, lander) & visible(C, D) & obj_tp(C, waypoint) & B \== C <-
	navigate(A, B, C);
	communicate_image_data(A, Z, X, Y, C, D).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & have_image(A, X, Y) & obj_tp(A, rover) & at(A, B) & obj_tp(B, waypoint) & at_lander(Z, B) & obj_tp(Z, lander) & visible(C, B) & obj_tp(C, waypoint) & B \== C <-
	navigate(A, B, C);
	communicate_image_data(A, Z, X, Y, C, B).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & calibration_target(Z, X) & obj_tp(Z, camera) & supports(Z, Y) & on_board(Z, B) & obj_tp(B, rover) & equipped_for_imaging(B) & at(B, C) & obj_tp(C, waypoint) & visible_from(X, C) & visible(C, D) & obj_tp(D, waypoint) & at_lander(A, D) & obj_tp(A, lander) <-
	calibrate(B, Z, X, C);
	take_image(B, C, X, Z, Y);
	communicate_image_data(B, A, X, Y, C, D).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibrated(Z, B) & obj_tp(B, rover) & on_board(Z, B) & equipped_for_imaging(B) & at(B, C) & obj_tp(C, waypoint) & visible_from(X, D) & obj_tp(D, waypoint) & C \== D & visible(D, V7) & obj_tp(V7, waypoint) & at_lander(A, V7) & obj_tp(A, lander) <-
	navigate(B, C, D);
	take_image(B, D, X, Z, Y);
	communicate_image_data(B, A, X, Y, D, V7).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibrated(Z, B) & obj_tp(B, rover) & on_board(Z, B) & equipped_for_imaging(B) & at(B, C) & obj_tp(C, waypoint) & visible_from(X, C) & at_lander(A, C) & obj_tp(A, lander) & visible(D, C) & obj_tp(D, waypoint) & C \== D <-
	take_image(B, C, X, Z, Y);
	navigate(B, C, D);
	communicate_image_data(B, A, X, Y, D, C).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & visible_from(B, D) & visible_from(X, D) & visible(D, V7) & obj_tp(V7, waypoint) & at_lander(A, V7) & obj_tp(A, lander) <-
	calibrate(C, Z, B, D);
	take_image(C, D, X, Z, Y);
	communicate_image_data(C, A, X, Y, D, V7).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibrated(Z, B) & obj_tp(B, rover) & on_board(Z, B) & equipped_for_imaging(B) & at(B, C) & obj_tp(C, waypoint) & visible_from(X, C) & at_lander(A, V7) & obj_tp(A, lander) & obj_tp(V7, waypoint) & visible(D, V7) & obj_tp(D, waypoint) & C \== D <-
	take_image(B, C, X, Z, Y);
	navigate(B, C, D);
	communicate_image_data(B, A, X, Y, D, V7).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibrated(Z, B) & obj_tp(B, rover) & on_board(Z, B) & equipped_for_imaging(B) & at(B, C) & obj_tp(C, waypoint) & at_lander(A, C) & obj_tp(A, lander) & visible(D, C) & obj_tp(D, waypoint) & C \== D & visible_from(X, D) <-
	navigate(B, C, D);
	take_image(B, D, X, Z, Y);
	communicate_image_data(B, A, X, Y, D, C).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & at_lander(A, D) & obj_tp(A, lander) & visible(V7, D) & obj_tp(V7, waypoint) & D \== V7 & visible_from(B, V7) & visible_from(X, V7) <-
	navigate(C, D, V7);
	calibrate(C, Z, B, V7);
	take_image(C, V7, X, Z, Y);
	communicate_image_data(C, A, X, Y, V7, D).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibrated(Z, B) & obj_tp(B, rover) & on_board(Z, B) & equipped_for_imaging(B) & at(B, C) & obj_tp(C, waypoint) & visible_from(X, D) & obj_tp(D, waypoint) & C \== D & at_lander(A, V8) & obj_tp(A, lander) & obj_tp(V8, waypoint) & visible(V7, V8) & obj_tp(V7, waypoint) & C \== V7 & D \== V7 <-
	navigate(B, C, D);
	take_image(B, D, X, Z, Y);
	navigate(B, D, V7);
	communicate_image_data(B, A, X, Y, V7, V8).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & calibration_target(Z, X) & obj_tp(Z, camera) & supports(Z, Y) & on_board(Z, B) & obj_tp(B, rover) & equipped_for_imaging(B) & at(B, C) & obj_tp(C, waypoint) & visible_from(X, D) & obj_tp(D, waypoint) & C \== D & visible(D, V7) & obj_tp(V7, waypoint) & at_lander(A, V7) & obj_tp(A, lander) <-
	navigate(B, C, D);
	calibrate(B, Z, X, D);
	take_image(B, D, X, Z, Y);
	communicate_image_data(B, A, X, Y, D, V7).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & visible_from(B, D) & visible_from(X, D) & at_lander(A, V8) & obj_tp(A, lander) & obj_tp(V8, waypoint) & visible(V7, V8) & obj_tp(V7, waypoint) & D \== V7 <-
	calibrate(C, Z, B, D);
	take_image(C, D, X, Z, Y);
	navigate(C, D, V7);
	communicate_image_data(C, A, X, Y, V7, V8).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & calibration_target(Z, X) & obj_tp(Z, camera) & supports(Z, Y) & on_board(Z, B) & obj_tp(B, rover) & equipped_for_imaging(B) & at(B, C) & obj_tp(C, waypoint) & visible_from(X, C) & at_lander(A, C) & obj_tp(A, lander) & visible(D, C) & obj_tp(D, waypoint) & C \== D <-
	calibrate(B, Z, X, C);
	take_image(B, C, X, Z, Y);
	navigate(B, C, D);
	communicate_image_data(B, A, X, Y, D, C).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibrated(Z, B) & obj_tp(B, rover) & on_board(Z, B) & equipped_for_imaging(B) & at(B, C) & obj_tp(C, waypoint) & visible(C, D) & obj_tp(D, waypoint) & C \== D & visible_from(X, D) & at_lander(A, D) & obj_tp(A, lander) <-
	navigate(B, C, D);
	take_image(B, D, X, Z, Y);
	navigate(B, D, C);
	communicate_image_data(B, A, X, Y, C, D).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & calibration_target(Z, X) & obj_tp(Z, camera) & supports(Z, Y) & on_board(Z, B) & obj_tp(B, rover) & equipped_for_imaging(B) & at(B, C) & obj_tp(C, waypoint) & at_lander(A, C) & obj_tp(A, lander) & visible(D, C) & obj_tp(D, waypoint) & C \== D & visible_from(X, D) <-
	navigate(B, C, D);
	calibrate(B, Z, X, D);
	take_image(B, D, X, Z, Y);
	communicate_image_data(B, A, X, Y, D, C).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibrated(Z, B) & obj_tp(B, rover) & on_board(Z, B) & equipped_for_imaging(B) & at(B, C) & obj_tp(C, waypoint) & visible_from(X, D) & obj_tp(D, waypoint) & C \== D & at_lander(A, D) & obj_tp(A, lander) & visible(V7, D) & obj_tp(V7, waypoint) & C \== V7 & D \== V7 <-
	navigate(B, C, D);
	take_image(B, D, X, Z, Y);
	navigate(B, D, V7);
	communicate_image_data(B, A, X, Y, V7, D).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & calibration_target(Z, X) & obj_tp(Z, camera) & supports(Z, Y) & on_board(Z, B) & obj_tp(B, rover) & equipped_for_imaging(B) & at(B, C) & obj_tp(C, waypoint) & visible_from(X, C) & at_lander(A, C) & obj_tp(A, lander) & visible(D, C) & obj_tp(D, waypoint) & C \== D & visible_from(X, D) <-
	calibrate(B, Z, X, C);
	navigate(B, C, D);
	take_image(B, D, X, Z, Y);
	communicate_image_data(B, A, X, Y, D, C).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & visible_from(B, D) & visible_from(X, D) & at_lander(A, D) & obj_tp(A, lander) & visible(V7, D) & obj_tp(V7, waypoint) & D \== V7 <-
	calibrate(C, Z, B, D);
	take_image(C, D, X, Z, Y);
	navigate(C, D, V7);
	communicate_image_data(C, A, X, Y, V7, D).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & visible_from(B, V7) & obj_tp(V7, waypoint) & D \== V7 & visible_from(X, V7) & visible(V7, V8) & obj_tp(V8, waypoint) & at_lander(A, V8) & obj_tp(A, lander) <-
	navigate(C, D, V7);
	calibrate(C, Z, B, V7);
	take_image(C, V7, X, Z, Y);
	communicate_image_data(C, A, X, Y, V7, V8).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & visible_from(B, D) & visible_from(X, V7) & obj_tp(V7, waypoint) & D \== V7 & visible(V7, V8) & obj_tp(V8, waypoint) & at_lander(A, V8) & obj_tp(A, lander) <-
	calibrate(C, Z, B, D);
	navigate(C, D, V7);
	take_image(C, V7, X, Z, Y);
	communicate_image_data(C, A, X, Y, V7, V8).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & calibration_target(Z, X) & obj_tp(Z, camera) & supports(Z, Y) & on_board(Z, B) & obj_tp(B, rover) & equipped_for_imaging(B) & at(B, C) & obj_tp(C, waypoint) & visible_from(X, C) & at_lander(A, V7) & obj_tp(A, lander) & obj_tp(V7, waypoint) & visible(D, V7) & obj_tp(D, waypoint) & C \== D <-
	calibrate(B, Z, X, C);
	take_image(B, C, X, Z, Y);
	navigate(B, C, D);
	communicate_image_data(B, A, X, Y, D, V7).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibrated(Z, B) & obj_tp(B, rover) & on_board(Z, B) & equipped_for_imaging(B) & at(B, C) & obj_tp(C, waypoint) & visible(C, V7) & obj_tp(V7, waypoint) & at_lander(A, V7) & obj_tp(A, lander) & visible_from(X, D) & obj_tp(D, waypoint) & C \== D <-
	navigate(B, C, D);
	take_image(B, D, X, Z, Y);
	navigate(B, D, C);
	communicate_image_data(B, A, X, Y, C, V7).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & visible_from(B, D) & at_lander(A, D) & obj_tp(A, lander) & visible(V7, D) & obj_tp(V7, waypoint) & D \== V7 & visible_from(X, V7) <-
	calibrate(C, Z, B, D);
	navigate(C, D, V7);
	take_image(C, V7, X, Z, Y);
	communicate_image_data(C, A, X, Y, V7, D).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & calibration_target(Z, X) & obj_tp(Z, camera) & supports(Z, Y) & on_board(Z, B) & obj_tp(B, rover) & equipped_for_imaging(B) & at(B, C) & obj_tp(C, waypoint) & visible_from(X, C) & visible_from(X, D) & obj_tp(D, waypoint) & C \== D & visible(D, V7) & obj_tp(V7, waypoint) & at_lander(A, V7) & obj_tp(A, lander) <-
	calibrate(B, Z, X, C);
	navigate(B, C, D);
	take_image(B, D, X, Z, Y);
	communicate_image_data(B, A, X, Y, D, V7).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & visible_from(B, D) & visible_from(X, V7) & obj_tp(V7, waypoint) & D \== V7 & at_lander(A, V9) & obj_tp(A, lander) & obj_tp(V9, waypoint) & visible(V8, V9) & obj_tp(V8, waypoint) & D \== V8 & V7 \== V8 <-
	calibrate(C, Z, B, D);
	navigate(C, D, V7);
	take_image(C, V7, X, Z, Y);
	navigate(C, V7, V8);
	communicate_image_data(C, A, X, Y, V8, V9).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & visible_from(B, V7) & obj_tp(V7, waypoint) & D \== V7 & visible_from(X, V7) & at_lander(A, V9) & obj_tp(A, lander) & obj_tp(V9, waypoint) & visible(V8, V9) & obj_tp(V8, waypoint) & D \== V8 & V7 \== V8 <-
	navigate(C, D, V7);
	calibrate(C, Z, B, V7);
	take_image(C, V7, X, Z, Y);
	navigate(C, V7, V8);
	communicate_image_data(C, A, X, Y, V8, V9).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & calibration_target(Z, X) & obj_tp(Z, camera) & supports(Z, Y) & on_board(Z, B) & obj_tp(B, rover) & equipped_for_imaging(B) & at(B, C) & obj_tp(C, waypoint) & visible(C, D) & obj_tp(D, waypoint) & C \== D & visible_from(X, D) & at_lander(A, D) & obj_tp(A, lander) <-
	navigate(B, C, D);
	calibrate(B, Z, X, D);
	take_image(B, D, X, Z, Y);
	navigate(B, D, C);
	communicate_image_data(B, A, X, Y, C, D).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & visible_from(B, V7) & obj_tp(V7, waypoint) & D \== V7 & at_lander(A, V7) & obj_tp(A, lander) & visible(V8, V7) & obj_tp(V8, waypoint) & D \== V8 & V7 \== V8 & visible_from(X, V8) <-
	navigate(C, D, V7);
	calibrate(C, Z, B, V7);
	navigate(C, V7, V8);
	take_image(C, V8, X, Z, Y);
	communicate_image_data(C, A, X, Y, V8, V7).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & visible_from(B, D) & visible(D, V7) & obj_tp(V7, waypoint) & D \== V7 & visible_from(X, V7) & at_lander(A, V7) & obj_tp(A, lander) <-
	calibrate(C, Z, B, D);
	navigate(C, D, V7);
	take_image(C, V7, X, Z, Y);
	navigate(C, V7, D);
	communicate_image_data(C, A, X, Y, D, V7).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & visible(D, V7) & obj_tp(V7, waypoint) & D \== V7 & visible_from(B, V7) & visible_from(X, V7) & at_lander(A, V7) & obj_tp(A, lander) <-
	navigate(C, D, V7);
	calibrate(C, Z, B, V7);
	take_image(C, V7, X, Z, Y);
	navigate(C, V7, D);
	communicate_image_data(C, A, X, Y, D, V7).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & visible_from(B, V7) & obj_tp(V7, waypoint) & D \== V7 & visible_from(X, V8) & obj_tp(V8, waypoint) & D \== V8 & V7 \== V8 & visible(V8, V9) & obj_tp(V9, waypoint) & at_lander(A, V9) & obj_tp(A, lander) <-
	navigate(C, D, V7);
	calibrate(C, Z, B, V7);
	navigate(C, V7, V8);
	take_image(C, V8, X, Z, Y);
	communicate_image_data(C, A, X, Y, V8, V9).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & visible_from(X, D) & visible(D, V7) & obj_tp(V7, waypoint) & D \== V7 & visible_from(B, V7) & at_lander(A, V7) & obj_tp(A, lander) <-
	navigate(C, D, V7);
	calibrate(C, Z, B, V7);
	navigate(C, V7, D);
	take_image(C, D, X, Z, Y);
	communicate_image_data(C, A, X, Y, D, V7).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & visible_from(X, D) & visible(D, V8) & obj_tp(V8, waypoint) & at_lander(A, V8) & obj_tp(A, lander) & visible_from(B, V7) & obj_tp(V7, waypoint) & D \== V7 <-
	navigate(C, D, V7);
	calibrate(C, Z, B, V7);
	navigate(C, V7, D);
	take_image(C, D, X, Z, Y);
	communicate_image_data(C, A, X, Y, D, V8).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & calibration_target(Z, X) & obj_tp(Z, camera) & supports(Z, Y) & on_board(Z, B) & obj_tp(B, rover) & equipped_for_imaging(B) & at(B, C) & obj_tp(C, waypoint) & visible_from(X, D) & obj_tp(D, waypoint) & C \== D & at_lander(A, V8) & obj_tp(A, lander) & obj_tp(V8, waypoint) & visible(V7, V8) & obj_tp(V7, waypoint) & C \== V7 & D \== V7 <-
	navigate(B, C, D);
	calibrate(B, Z, X, D);
	take_image(B, D, X, Z, Y);
	navigate(B, D, V7);
	communicate_image_data(B, A, X, Y, V7, V8).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & at_lander(A, D) & obj_tp(A, lander) & visible(V8, D) & obj_tp(V8, waypoint) & D \== V8 & visible_from(X, V8) & visible_from(B, V7) & obj_tp(V7, waypoint) & D \== V7 & V7 \== V8 <-
	navigate(C, D, V7);
	calibrate(C, Z, B, V7);
	navigate(C, V7, V8);
	take_image(C, V8, X, Z, Y);
	communicate_image_data(C, A, X, Y, V8, D).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & visible_from(B, D) & visible_from(X, V7) & obj_tp(V7, waypoint) & D \== V7 & at_lander(A, V7) & obj_tp(A, lander) & visible(V8, V7) & obj_tp(V8, waypoint) & D \== V8 & V7 \== V8 <-
	calibrate(C, Z, B, D);
	navigate(C, D, V7);
	take_image(C, V7, X, Z, Y);
	navigate(C, V7, V8);
	communicate_image_data(C, A, X, Y, V8, V7).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & visible(D, V8) & obj_tp(V8, waypoint) & at_lander(A, V8) & obj_tp(A, lander) & visible_from(B, V7) & obj_tp(V7, waypoint) & D \== V7 & visible_from(X, V7) <-
	navigate(C, D, V7);
	calibrate(C, Z, B, V7);
	take_image(C, V7, X, Z, Y);
	navigate(C, V7, D);
	communicate_image_data(C, A, X, Y, D, V8).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & visible_from(B, V7) & obj_tp(V7, waypoint) & D \== V7 & visible_from(X, V7) & at_lander(A, V7) & obj_tp(A, lander) & visible(V8, V7) & obj_tp(V8, waypoint) & D \== V8 & V7 \== V8 <-
	navigate(C, D, V7);
	calibrate(C, Z, B, V7);
	take_image(C, V7, X, Z, Y);
	navigate(C, V7, V8);
	communicate_image_data(C, A, X, Y, V8, V7).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & calibration_target(Z, X) & obj_tp(Z, camera) & supports(Z, Y) & on_board(Z, B) & obj_tp(B, rover) & equipped_for_imaging(B) & at(B, C) & obj_tp(C, waypoint) & visible_from(X, D) & obj_tp(D, waypoint) & C \== D & at_lander(A, D) & obj_tp(A, lander) & visible(V7, D) & obj_tp(V7, waypoint) & C \== V7 & D \== V7 <-
	navigate(B, C, D);
	calibrate(B, Z, X, D);
	take_image(B, D, X, Z, Y);
	navigate(B, D, V7);
	communicate_image_data(B, A, X, Y, V7, D).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & visible_from(B, D) & visible(D, V8) & obj_tp(V8, waypoint) & at_lander(A, V8) & obj_tp(A, lander) & visible_from(X, V7) & obj_tp(V7, waypoint) & D \== V7 <-
	calibrate(C, Z, B, D);
	navigate(C, D, V7);
	take_image(C, V7, X, Z, Y);
	navigate(C, V7, D);
	communicate_image_data(C, A, X, Y, D, V8).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & calibration_target(Z, X) & obj_tp(Z, camera) & supports(Z, Y) & on_board(Z, B) & obj_tp(B, rover) & equipped_for_imaging(B) & at(B, C) & obj_tp(C, waypoint) & visible(C, V7) & obj_tp(V7, waypoint) & at_lander(A, V7) & obj_tp(A, lander) & visible_from(X, D) & obj_tp(D, waypoint) & C \== D <-
	navigate(B, C, D);
	calibrate(B, Z, X, D);
	take_image(B, D, X, Z, Y);
	navigate(B, D, C);
	communicate_image_data(B, A, X, Y, C, V7).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & visible_from(X, D) & at_lander(A, D) & obj_tp(A, lander) & visible(V7, D) & obj_tp(V7, waypoint) & D \== V7 & visible_from(B, V7) <-
	navigate(C, D, V7);
	calibrate(C, Z, B, V7);
	navigate(C, V7, D);
	take_image(C, D, X, Z, Y);
	navigate(C, D, V7);
	communicate_image_data(C, A, X, Y, V7, D).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & at_lander(A, D) & obj_tp(A, lander) & visible(V7, D) & obj_tp(V7, waypoint) & D \== V7 & visible_from(B, V7) & visible_from(X, V8) & obj_tp(V8, waypoint) & D \== V8 & V7 \== V8 <-
	navigate(C, D, V7);
	calibrate(C, Z, B, V7);
	navigate(C, V7, V8);
	take_image(C, V8, X, Z, Y);
	navigate(C, V8, V7);
	communicate_image_data(C, A, X, Y, V7, D).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & visible_from(B, V7) & obj_tp(V7, waypoint) & D \== V7 & visible(V7, V9) & obj_tp(V9, waypoint) & at_lander(A, V9) & obj_tp(A, lander) & visible_from(X, V8) & obj_tp(V8, waypoint) & D \== V8 & V7 \== V8 <-
	navigate(C, D, V7);
	calibrate(C, Z, B, V7);
	navigate(C, V7, V8);
	take_image(C, V8, X, Z, Y);
	navigate(C, V8, V7);
	communicate_image_data(C, A, X, Y, V7, V9).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & at_lander(A, D) & obj_tp(A, lander) & visible(V9, D) & obj_tp(V9, waypoint) & D \== V9 & visible_from(B, V7) & obj_tp(V7, waypoint) & D \== V7 & V7 \== V9 & visible_from(X, V8) & obj_tp(V8, waypoint) & D \== V8 & V7 \== V8 & V8 \== V9 <-
	navigate(C, D, V7);
	calibrate(C, Z, B, V7);
	navigate(C, V7, V8);
	take_image(C, V8, X, Z, Y);
	navigate(C, V8, V9);
	communicate_image_data(C, A, X, Y, V9, D).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(Z, Y) & obj_tp(Z, camera) & calibration_target(Z, B) & obj_tp(B, objective) & on_board(Z, C) & obj_tp(C, rover) & equipped_for_imaging(C) & at(C, D) & obj_tp(D, waypoint) & visible(D, V9) & obj_tp(V9, waypoint) & at_lander(A, V9) & obj_tp(A, lander) & visible_from(B, V7) & obj_tp(V7, waypoint) & D \== V7 & visible_from(X, V8) & obj_tp(V8, waypoint) & D \== V8 & V7 \== V8 <-
	navigate(C, D, V7);
	calibrate(C, Z, B, V7);
	navigate(C, V7, V8);
	take_image(C, V8, X, Z, Y);
	navigate(C, V8, D);
	communicate_image_data(C, A, X, Y, D, V9).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & at_lander(Y, X) & obj_tp(Y, lander) & have_rock_analysis(Z, X) & obj_tp(Z, rover) & at(Z, A) & obj_tp(A, waypoint) & visible(A, X) <-
	communicate_rock_data(Z, Y, X, A, X).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & at(Z, X) & obj_tp(Z, rover) & have_rock_analysis(Z, X) & visible(X, A) & obj_tp(A, waypoint) & at_lander(Y, A) & obj_tp(Y, lander) <-
	communicate_rock_data(Z, Y, X, X, A).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & have_rock_analysis(Z, X) & obj_tp(Z, rover) & at(Z, A) & obj_tp(A, waypoint) & visible(A, B) & obj_tp(B, waypoint) & at_lander(Y, B) & obj_tp(Y, lander) <-
	communicate_rock_data(Z, Y, X, A, B).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & at_rock_sample(X) & at(Z, X) & obj_tp(Z, rover) & equipped_for_rock_analysis(Z) & store_of(A, Z) & obj_tp(A, store) & empty(A) & visible(X, B) & obj_tp(B, waypoint) & at_lander(Y, B) & obj_tp(Y, lander) <-
	sample_rock(Z, A, X);
	communicate_rock_data(Z, Y, X, X, B).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & at(Z, X) & obj_tp(Z, rover) & have_rock_analysis(Z, X) & at_lander(Y, B) & obj_tp(B, waypoint) & obj_tp(Y, lander) & visible(A, B) & obj_tp(A, waypoint) & A \== X <-
	navigate(Z, X, A);
	communicate_rock_data(Z, Y, X, A, B).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & at(Z, X) & obj_tp(Z, rover) & have_rock_analysis(Z, X) & at_lander(Y, X) & obj_tp(Y, lander) & visible(A, X) & obj_tp(A, waypoint) & A \== X <-
	navigate(Z, X, A);
	communicate_rock_data(Z, Y, X, A, X).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & at_rock_sample(X) & at(Z, X) & obj_tp(Z, rover) & equipped_for_rock_analysis(Z) & store_of(A, Z) & obj_tp(A, store) & full(A) & visible(X, B) & obj_tp(B, waypoint) & at_lander(Y, B) & obj_tp(Y, lander) <-
	drop(Z, A);
	sample_rock(Z, A, X);
	communicate_rock_data(Z, Y, X, X, B).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & at_rock_sample(X) & at(Z, X) & obj_tp(Z, rover) & equipped_for_rock_analysis(Z) & store_of(A, Z) & obj_tp(A, store) & empty(A) & at_lander(Y, C) & obj_tp(C, waypoint) & obj_tp(Y, lander) & visible(B, C) & obj_tp(B, waypoint) & B \== X <-
	sample_rock(Z, A, X);
	navigate(Z, X, B);
	communicate_rock_data(Z, Y, X, B, C).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & at_rock_sample(X) & visible(X, B) & obj_tp(B, waypoint) & B \== X & at(Z, B) & obj_tp(Z, rover) & equipped_for_rock_analysis(Z) & at_lander(Y, B) & obj_tp(Y, lander) & store_of(A, Z) & obj_tp(A, store) & empty(A) <-
	navigate(Z, B, X);
	sample_rock(Z, A, X);
	communicate_rock_data(Z, Y, X, X, B).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & at_rock_sample(X) & visible(X, C) & obj_tp(C, waypoint) & at_lander(Y, C) & obj_tp(Y, lander) & empty(A) & obj_tp(A, store) & store_of(A, Z) & obj_tp(Z, rover) & equipped_for_rock_analysis(Z) & at(Z, B) & obj_tp(B, waypoint) & B \== X <-
	navigate(Z, B, X);
	sample_rock(Z, A, X);
	communicate_rock_data(Z, Y, X, X, C).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & at_rock_sample(X) & at(Z, X) & obj_tp(Z, rover) & equipped_for_rock_analysis(Z) & at_lander(Y, X) & obj_tp(Y, lander) & store_of(A, Z) & obj_tp(A, store) & empty(A) & visible(B, X) & obj_tp(B, waypoint) & B \== X <-
	sample_rock(Z, A, X);
	navigate(Z, X, B);
	communicate_rock_data(Z, Y, X, B, X).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & at_rock_sample(X) & empty(A) & obj_tp(A, store) & store_of(A, Z) & obj_tp(Z, rover) & equipped_for_rock_analysis(Z) & at(Z, B) & obj_tp(B, waypoint) & B \== X & at_lander(Y, D) & obj_tp(D, waypoint) & obj_tp(Y, lander) & visible(C, D) & obj_tp(C, waypoint) & B \== C & C \== X <-
	navigate(Z, B, X);
	sample_rock(Z, A, X);
	navigate(Z, X, C);
	communicate_rock_data(Z, Y, X, C, D).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & at_rock_sample(X) & at_lander(Y, X) & obj_tp(Y, lander) & visible(B, X) & obj_tp(B, waypoint) & B \== X & at(Z, B) & obj_tp(Z, rover) & equipped_for_rock_analysis(Z) & store_of(A, Z) & obj_tp(A, store) & empty(A) <-
	navigate(Z, B, X);
	sample_rock(Z, A, X);
	navigate(Z, X, B);
	communicate_rock_data(Z, Y, X, B, X).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & at_rock_sample(X) & visible(X, C) & obj_tp(C, waypoint) & at_lander(Y, C) & obj_tp(Y, lander) & equipped_for_rock_analysis(Z) & obj_tp(Z, rover) & at(Z, B) & obj_tp(B, waypoint) & B \== X & store_of(A, Z) & obj_tp(A, store) & full(A) <-
	navigate(Z, B, X);
	drop(Z, A);
	sample_rock(Z, A, X);
	communicate_rock_data(Z, Y, X, X, C).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & at_rock_sample(X) & empty(A) & obj_tp(A, store) & store_of(A, Z) & obj_tp(Z, rover) & equipped_for_rock_analysis(Z) & at(Z, B) & obj_tp(B, waypoint) & B \== X & at_lander(Y, B) & obj_tp(Y, lander) & visible(C, B) & obj_tp(C, waypoint) & B \== C & C \== X <-
	navigate(Z, B, X);
	sample_rock(Z, A, X);
	navigate(Z, X, C);
	communicate_rock_data(Z, Y, X, C, B).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & at_rock_sample(X) & at_lander(Y, X) & obj_tp(Y, lander) & visible(C, X) & obj_tp(C, waypoint) & C \== X & empty(A) & obj_tp(A, store) & store_of(A, Z) & obj_tp(Z, rover) & equipped_for_rock_analysis(Z) & at(Z, B) & obj_tp(B, waypoint) & B \== C & B \== X <-
	navigate(Z, B, X);
	sample_rock(Z, A, X);
	navigate(Z, X, C);
	communicate_rock_data(Z, Y, X, C, X).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & at_rock_sample(X) & empty(A) & obj_tp(A, store) & store_of(A, Z) & obj_tp(Z, rover) & equipped_for_rock_analysis(Z) & at(Z, B) & obj_tp(B, waypoint) & B \== X & visible(B, C) & obj_tp(C, waypoint) & at_lander(Y, C) & obj_tp(Y, lander) <-
	navigate(Z, B, X);
	sample_rock(Z, A, X);
	navigate(Z, X, B);
	communicate_rock_data(Z, Y, X, B, C).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & at_rock_sample(X) & at_lander(Y, X) & obj_tp(Y, lander) & visible(B, X) & obj_tp(B, waypoint) & B \== X & at(Z, B) & obj_tp(Z, rover) & equipped_for_rock_analysis(Z) & store_of(A, Z) & obj_tp(A, store) & full(A) <-
	drop(Z, A);
	navigate(Z, B, X);
	sample_rock(Z, A, X);
	navigate(Z, X, B);
	communicate_rock_data(Z, Y, X, B, X).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & at_rock_sample(X) & equipped_for_rock_analysis(Z) & obj_tp(Z, rover) & at(Z, B) & obj_tp(B, waypoint) & B \== X & store_of(A, Z) & obj_tp(A, store) & full(A) & visible(B, C) & obj_tp(C, waypoint) & at_lander(Y, C) & obj_tp(Y, lander) <-
	drop(Z, A);
	navigate(Z, B, X);
	sample_rock(Z, A, X);
	navigate(Z, X, B);
	communicate_rock_data(Z, Y, X, B, C).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & at_rock_sample(X) & equipped_for_rock_analysis(Z) & obj_tp(Z, rover) & at(Z, B) & obj_tp(B, waypoint) & B \== X & store_of(A, Z) & obj_tp(A, store) & full(A) & at_lander(Y, D) & obj_tp(D, waypoint) & obj_tp(Y, lander) & visible(C, D) & obj_tp(C, waypoint) & B \== C & C \== X <-
	drop(Z, A);
	navigate(Z, B, X);
	sample_rock(Z, A, X);
	navigate(Z, X, C);
	communicate_rock_data(Z, Y, X, C, D).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & at_rock_sample(X) & at_lander(Y, X) & obj_tp(Y, lander) & visible(C, X) & obj_tp(C, waypoint) & C \== X & equipped_for_rock_analysis(Z) & obj_tp(Z, rover) & at(Z, B) & obj_tp(B, waypoint) & B \== C & B \== X & store_of(A, Z) & obj_tp(A, store) & full(A) <-
	drop(Z, A);
	navigate(Z, B, X);
	sample_rock(Z, A, X);
	navigate(Z, X, C);
	communicate_rock_data(Z, Y, X, C, X).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & have_soil_analysis(Z, X) & obj_tp(Z, rover) & at(Z, A) & obj_tp(A, waypoint) & visible(A, B) & obj_tp(B, waypoint) & at_lander(Y, B) & obj_tp(Y, lander) <-
	communicate_soil_data(Z, Y, X, A, B).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & at_lander(Y, X) & obj_tp(Y, lander) & have_soil_analysis(Z, X) & obj_tp(Z, rover) & at(Z, A) & obj_tp(A, waypoint) & visible(A, X) <-
	communicate_soil_data(Z, Y, X, A, X).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & at(Z, X) & obj_tp(Z, rover) & have_soil_analysis(Z, X) & visible(X, A) & obj_tp(A, waypoint) & at_lander(Y, A) & obj_tp(Y, lander) <-
	communicate_soil_data(Z, Y, X, X, A).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & at(Z, X) & obj_tp(Z, rover) & have_soil_analysis(Z, X) & at_lander(Y, B) & obj_tp(B, waypoint) & obj_tp(Y, lander) & visible(A, B) & obj_tp(A, waypoint) & A \== X <-
	navigate(Z, X, A);
	communicate_soil_data(Z, Y, X, A, B).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & at_soil_sample(X) & at(Z, X) & obj_tp(Z, rover) & equipped_for_soil_analysis(Z) & store_of(A, Z) & obj_tp(A, store) & empty(A) & visible(X, B) & obj_tp(B, waypoint) & at_lander(Y, B) & obj_tp(Y, lander) <-
	sample_soil(Z, A, X);
	communicate_soil_data(Z, Y, X, X, B).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & at(Z, X) & obj_tp(Z, rover) & have_soil_analysis(Z, X) & at_lander(Y, X) & obj_tp(Y, lander) & visible(A, X) & obj_tp(A, waypoint) & A \== X <-
	navigate(Z, X, A);
	communicate_soil_data(Z, Y, X, A, X).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & at_soil_sample(X) & at(Z, X) & obj_tp(Z, rover) & equipped_for_soil_analysis(Z) & at_lander(Y, X) & obj_tp(Y, lander) & store_of(A, Z) & obj_tp(A, store) & empty(A) & visible(B, X) & obj_tp(B, waypoint) & B \== X <-
	sample_soil(Z, A, X);
	navigate(Z, X, B);
	communicate_soil_data(Z, Y, X, B, X).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & at_soil_sample(X) & at(Z, X) & obj_tp(Z, rover) & equipped_for_soil_analysis(Z) & store_of(A, Z) & obj_tp(A, store) & full(A) & visible(X, B) & obj_tp(B, waypoint) & at_lander(Y, B) & obj_tp(Y, lander) <-
	drop(Z, A);
	sample_soil(Z, A, X);
	communicate_soil_data(Z, Y, X, X, B).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & at_soil_sample(X) & visible(X, C) & obj_tp(C, waypoint) & at_lander(Y, C) & obj_tp(Y, lander) & empty(A) & obj_tp(A, store) & store_of(A, Z) & obj_tp(Z, rover) & equipped_for_soil_analysis(Z) & at(Z, B) & obj_tp(B, waypoint) & B \== X <-
	navigate(Z, B, X);
	sample_soil(Z, A, X);
	communicate_soil_data(Z, Y, X, X, C).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & at_soil_sample(X) & at(Z, X) & obj_tp(Z, rover) & equipped_for_soil_analysis(Z) & store_of(A, Z) & obj_tp(A, store) & empty(A) & at_lander(Y, C) & obj_tp(C, waypoint) & obj_tp(Y, lander) & visible(B, C) & obj_tp(B, waypoint) & B \== X <-
	sample_soil(Z, A, X);
	navigate(Z, X, B);
	communicate_soil_data(Z, Y, X, B, C).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & at_soil_sample(X) & visible(X, B) & obj_tp(B, waypoint) & B \== X & at(Z, B) & obj_tp(Z, rover) & equipped_for_soil_analysis(Z) & at_lander(Y, B) & obj_tp(Y, lander) & store_of(A, Z) & obj_tp(A, store) & empty(A) <-
	navigate(Z, B, X);
	sample_soil(Z, A, X);
	communicate_soil_data(Z, Y, X, X, B).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & at_soil_sample(X) & empty(A) & obj_tp(A, store) & store_of(A, Z) & obj_tp(Z, rover) & equipped_for_soil_analysis(Z) & at(Z, B) & obj_tp(B, waypoint) & B \== X & visible(B, C) & obj_tp(C, waypoint) & at_lander(Y, C) & obj_tp(Y, lander) <-
	navigate(Z, B, X);
	sample_soil(Z, A, X);
	navigate(Z, X, B);
	communicate_soil_data(Z, Y, X, B, C).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & at_soil_sample(X) & empty(A) & obj_tp(A, store) & store_of(A, Z) & obj_tp(Z, rover) & equipped_for_soil_analysis(Z) & at(Z, B) & obj_tp(B, waypoint) & B \== X & at_lander(Y, D) & obj_tp(D, waypoint) & obj_tp(Y, lander) & visible(C, D) & obj_tp(C, waypoint) & B \== C & C \== X <-
	navigate(Z, B, X);
	sample_soil(Z, A, X);
	navigate(Z, X, C);
	communicate_soil_data(Z, Y, X, C, D).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & at_soil_sample(X) & visible(X, C) & obj_tp(C, waypoint) & at_lander(Y, C) & obj_tp(Y, lander) & equipped_for_soil_analysis(Z) & obj_tp(Z, rover) & at(Z, B) & obj_tp(B, waypoint) & B \== X & store_of(A, Z) & obj_tp(A, store) & full(A) <-
	navigate(Z, B, X);
	drop(Z, A);
	sample_soil(Z, A, X);
	communicate_soil_data(Z, Y, X, X, C).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & at_soil_sample(X) & empty(A) & obj_tp(A, store) & store_of(A, Z) & obj_tp(Z, rover) & equipped_for_soil_analysis(Z) & at(Z, B) & obj_tp(B, waypoint) & B \== X & at_lander(Y, B) & obj_tp(Y, lander) & visible(C, B) & obj_tp(C, waypoint) & B \== C & C \== X <-
	navigate(Z, B, X);
	sample_soil(Z, A, X);
	navigate(Z, X, C);
	communicate_soil_data(Z, Y, X, C, B).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & at_soil_sample(X) & at_lander(Y, X) & obj_tp(Y, lander) & visible(C, X) & obj_tp(C, waypoint) & C \== X & empty(A) & obj_tp(A, store) & store_of(A, Z) & obj_tp(Z, rover) & equipped_for_soil_analysis(Z) & at(Z, B) & obj_tp(B, waypoint) & B \== C & B \== X <-
	navigate(Z, B, X);
	sample_soil(Z, A, X);
	navigate(Z, X, C);
	communicate_soil_data(Z, Y, X, C, X).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & at_soil_sample(X) & at_lander(Y, X) & obj_tp(Y, lander) & visible(B, X) & obj_tp(B, waypoint) & B \== X & at(Z, B) & obj_tp(Z, rover) & equipped_for_soil_analysis(Z) & store_of(A, Z) & obj_tp(A, store) & empty(A) <-
	navigate(Z, B, X);
	sample_soil(Z, A, X);
	navigate(Z, X, B);
	communicate_soil_data(Z, Y, X, B, X).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & at_soil_sample(X) & equipped_for_soil_analysis(Z) & obj_tp(Z, rover) & at(Z, B) & obj_tp(B, waypoint) & B \== X & store_of(A, Z) & obj_tp(A, store) & full(A) & visible(B, C) & obj_tp(C, waypoint) & at_lander(Y, C) & obj_tp(Y, lander) <-
	drop(Z, A);
	navigate(Z, B, X);
	sample_soil(Z, A, X);
	navigate(Z, X, B);
	communicate_soil_data(Z, Y, X, B, C).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & at_soil_sample(X) & at_lander(Y, X) & obj_tp(Y, lander) & visible(B, X) & obj_tp(B, waypoint) & B \== X & at(Z, B) & obj_tp(Z, rover) & equipped_for_soil_analysis(Z) & store_of(A, Z) & obj_tp(A, store) & full(A) <-
	drop(Z, A);
	navigate(Z, B, X);
	sample_soil(Z, A, X);
	navigate(Z, X, B);
	communicate_soil_data(Z, Y, X, B, X).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & at_soil_sample(X) & equipped_for_soil_analysis(Z) & obj_tp(Z, rover) & at(Z, B) & obj_tp(B, waypoint) & B \== X & store_of(A, Z) & obj_tp(A, store) & full(A) & at_lander(Y, D) & obj_tp(D, waypoint) & obj_tp(Y, lander) & visible(C, D) & obj_tp(C, waypoint) & B \== C & C \== X <-
	drop(Z, A);
	navigate(Z, B, X);
	sample_soil(Z, A, X);
	navigate(Z, X, C);
	communicate_soil_data(Z, Y, X, C, D).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & at_soil_sample(X) & at_lander(Y, X) & obj_tp(Y, lander) & visible(C, X) & obj_tp(C, waypoint) & C \== X & equipped_for_soil_analysis(Z) & obj_tp(Z, rover) & at(Z, B) & obj_tp(B, waypoint) & B \== C & B \== X & store_of(A, Z) & obj_tp(A, store) & full(A) <-
	drop(Z, A);
	navigate(Z, B, X);
	sample_soil(Z, A, X);
	navigate(Z, X, C);
	communicate_soil_data(Z, Y, X, C, X).

+!empty(X) : obj_tp(X, store) & full(X) & store_of(X, Y) & obj_tp(Y, rover) <-
	drop(Y, X).

+!full(X) : obj_tp(X, store) & empty(X) & store_of(X, Y) & obj_tp(Y, rover) & equipped_for_rock_analysis(Y) & at(Y, Z) & obj_tp(Z, waypoint) & at_rock_sample(Z) <-
	sample_rock(Y, X, Z).

+!full(X) : obj_tp(X, store) & empty(X) & store_of(X, Y) & obj_tp(Y, rover) & equipped_for_soil_analysis(Y) & at(Y, Z) & obj_tp(Z, waypoint) & at_soil_sample(Z) <-
	sample_soil(Y, X, Z).

+!have_image(X, Y, Z) : obj_tp(X, rover) & obj_tp(Y, objective) & obj_tp(Z, mode) & equipped_for_imaging(X) & at(X, A) & obj_tp(A, waypoint) & visible_from(Y, A) & calibrated(B, X) & obj_tp(B, camera) & on_board(B, X) & supports(B, Z) <-
	take_image(X, A, Y, B, Z).

+!have_rock_analysis(X, Y) : obj_tp(X, rover) & obj_tp(Y, waypoint) & at(X, Y) & at_rock_sample(Y) & equipped_for_rock_analysis(X) & store_of(Z, X) & obj_tp(Z, store) & empty(Z) <-
	sample_rock(X, Z, Y).

+!have_rock_analysis(X, Y) : obj_tp(X, rover) & obj_tp(Y, waypoint) & at(X, Y) & at_rock_sample(Y) & equipped_for_rock_analysis(X) & store_of(Z, X) & obj_tp(Z, store) & full(Z) & store_of(Z, A) & obj_tp(A, rover) <-
	drop(A, Z);
	sample_rock(X, Z, Y).

+!have_soil_analysis(X, Y) : obj_tp(X, rover) & obj_tp(Y, waypoint) & at(X, Y) & at_soil_sample(Y) & equipped_for_soil_analysis(X) & store_of(Z, X) & obj_tp(Z, store) & empty(Z) <-
	sample_soil(X, Z, Y).

+!have_soil_analysis(X, Y) : obj_tp(X, rover) & obj_tp(Y, waypoint) & at(X, Y) & at_soil_sample(Y) & equipped_for_soil_analysis(X) & store_of(Z, X) & obj_tp(Z, store) & full(Z) & store_of(Z, A) & obj_tp(A, rover) <-
	drop(A, Z);
	sample_soil(X, Z, Y).

+!calibrated(X, Y) : obj_tp(X, camera) & obj_tp(Y, rover) & on_board(X, Y) & equipped_for_imaging(Y) & calibration_target(X, Z) & obj_tp(Z, objective) & visible_from(Z, A) & obj_tp(A, waypoint) & not at(Y, A) <-
	!at(Y, A);
	!calibrated(X, Y).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & supports(V8, Y) & on_board(V8, Z) & obj_tp(Z, rover) & equipped_for_imaging(Z) & not have_image(Z, X, Y) & at(Z, B) & obj_tp(B, waypoint) & visible(B, C) & obj_tp(C, waypoint) & at_lander(A, C) & obj_tp(A, lander) & visible_from(X, V7) <-
	!have_image(Z, X, Y);
	!communicated_image_data(X, Y).

+!communicated_image_data(X, Y) : obj_tp(X, objective) & obj_tp(Y, mode) & have_image(Z, X, Y) & obj_tp(Z, rover) & equipped_for_imaging(Z) & on_board(V8, Z) & supports(V8, Y) & visible_from(X, V7) & at_lander(A, C) & obj_tp(A, lander) & obj_tp(C, waypoint) & visible(B, C) & obj_tp(B, waypoint) & not at(Z, B) <-
	!at(Z, B);
	!communicated_image_data(X, Y).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & equipped_for_rock_analysis(Y) & obj_tp(Y, rover) & not have_rock_analysis(Y, X) & at(Y, A) & obj_tp(A, waypoint) & store_of(D, Y) & visible(A, B) & obj_tp(B, waypoint) & at_lander(Z, B) & obj_tp(Z, lander) <-
	!have_rock_analysis(Y, X);
	!communicated_rock_data(X).

+!communicated_rock_data(X) : obj_tp(X, waypoint) & have_rock_analysis(Y, X) & obj_tp(Y, rover) & equipped_for_rock_analysis(Y) & store_of(D, Y) & at_lander(Z, B) & obj_tp(B, waypoint) & obj_tp(Z, lander) & visible(A, B) & obj_tp(A, waypoint) & not at(Y, A) <-
	!at(Y, A);
	!communicated_rock_data(X).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & equipped_for_soil_analysis(Y) & obj_tp(Y, rover) & not have_soil_analysis(Y, X) & at(Y, A) & obj_tp(A, waypoint) & store_of(D, Y) & visible(A, B) & obj_tp(B, waypoint) & at_lander(Z, B) & obj_tp(Z, lander) <-
	!have_soil_analysis(Y, X);
	!communicated_soil_data(X).

+!communicated_soil_data(X) : obj_tp(X, waypoint) & have_soil_analysis(Y, X) & obj_tp(Y, rover) & equipped_for_soil_analysis(Y) & store_of(D, Y) & at_lander(Z, B) & obj_tp(B, waypoint) & obj_tp(Z, lander) & visible(A, B) & obj_tp(A, waypoint) & not at(Y, A) <-
	!at(Y, A);
	!communicated_soil_data(X).

+!full(X) : obj_tp(X, store) & empty(X) & store_of(X, B) & store_of(X, Y) & obj_tp(Y, rover) & equipped_for_soil_analysis(Y) & at_soil_sample(Z) & obj_tp(Z, waypoint) & not at(Y, Z) <-
	!at(Y, Z);
	!full(X).

+!full(X) : obj_tp(X, store) & empty(X) & store_of(X, B) & store_of(X, Y) & obj_tp(Y, rover) & equipped_for_rock_analysis(Y) & at_rock_sample(Z) & obj_tp(Z, waypoint) & not at(Y, Z) <-
	!at(Y, Z);
	!full(X).

+!have_image(X, Y, Z) : obj_tp(X, rover) & obj_tp(Y, objective) & obj_tp(Z, mode) & equipped_for_imaging(X) & on_board(B, X) & obj_tp(B, camera) & supports(B, Z) & not calibrated(B, X) & calibration_target(B, C) & visible_from(C, D) & visible_from(Y, A) & obj_tp(A, waypoint) <-
	!calibrated(B, X);
	!have_image(X, Y, Z).

+!have_image(X, Y, Z) : obj_tp(X, rover) & obj_tp(Y, objective) & obj_tp(Z, mode) & equipped_for_imaging(X) & on_board(B, X) & obj_tp(B, camera) & supports(B, Z) & calibration_target(B, C) & visible_from(C, D) & visible_from(Y, A) & obj_tp(A, waypoint) & not at(X, A) <-
	!at(X, A);
	!have_image(X, Y, Z).

+!have_rock_analysis(X, Y) : obj_tp(X, rover) & obj_tp(Y, waypoint) & not at(X, Y) <-
	!at(X, Y);
	!have_rock_analysis(X, Y).

+!have_rock_analysis(X, Y) : obj_tp(X, rover) & obj_tp(Y, waypoint) & at(X, Y) & at_rock_sample(Y) & equipped_for_rock_analysis(X) & store_of(Z, X) & obj_tp(Z, store) & not full(Z) & store_of(Z, A) & obj_tp(A, rover) <-
	!full(Z);
	!have_rock_analysis(X, Y).

+!have_rock_analysis(X, Y) : obj_tp(X, rover) & obj_tp(Y, waypoint) & at(X, Y) & at_rock_sample(Y) & equipped_for_rock_analysis(X) & store_of(Z, X) & obj_tp(Z, store) & not empty(Z) & store_of(Z, B) <-
	!empty(Z);
	!have_rock_analysis(X, Y).

+!have_soil_analysis(X, Y) : obj_tp(X, rover) & obj_tp(Y, waypoint) & not at(X, Y) <-
	!at(X, Y);
	!have_soil_analysis(X, Y).

+!have_soil_analysis(X, Y) : obj_tp(X, rover) & obj_tp(Y, waypoint) & at(X, Y) & at_soil_sample(Y) & equipped_for_soil_analysis(X) & store_of(Z, X) & obj_tp(Z, store) & not full(Z) & store_of(Z, A) & obj_tp(A, rover) <-
	!full(Z);
	!have_soil_analysis(X, Y).

+!have_soil_analysis(X, Y) : obj_tp(X, rover) & obj_tp(Y, waypoint) & at(X, Y) & at_soil_sample(Y) & equipped_for_soil_analysis(X) & store_of(Z, X) & obj_tp(Z, store) & not empty(Z) & store_of(Z, B) <-
	!empty(Z);
	!have_soil_analysis(X, Y).
