(define (problem 6obs_2sat_2mod)
 (:domain satellite)
 (:objects
  instrument0 instrument1 - instrument
  satellite0 satellite1 - satellite
  spectrograph0 infrared1 - mode
  star0 star3 phenomenon5 star1 star4 phenomenon6 star7 star2 - direction
 )
 (:init
  (supports instrument0 spectrograph0)
  (supports instrument0 infrared1)
  (calibration_target instrument0 star0)
  (on_board instrument0 satellite0)
  (power_avail satellite0)
  (pointing satellite0 star3)
  (supports instrument1 infrared1)
  (calibration_target instrument1 star0)
  (on_board instrument1 satellite1)
  (power_avail satellite1)
  (pointing satellite1 star2)
 )
 (:goal (and
  (have_image star2 infrared1)
  (have_image star3 infrared1)
  (have_image star4 spectrograph0)
  (have_image phenomenon5 spectrograph0)
  (have_image phenomenon6 infrared1)
  (have_image star7 spectrograph0)
 ))
)
