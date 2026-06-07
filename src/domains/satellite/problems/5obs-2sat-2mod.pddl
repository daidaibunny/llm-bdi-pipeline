(define (problem 5obs_2sat_2mod)
 (:domain satellite)
 (:objects
  instrument0 instrument1 instrument2 instrument3 - instrument
  satellite0 satellite1 - satellite
  thermograph1 spectrograph0 - mode
  star1 star0 star5 star6 planet2 star4 planet3 - direction
 )
 (:init
  (supports instrument0 thermograph1)
  (supports instrument0 spectrograph0)
  (calibration_target instrument0 star1)
  (supports instrument1 spectrograph0)
  (supports instrument1 thermograph1)
  (calibration_target instrument1 star1)
  (on_board instrument0 satellite0)
  (on_board instrument1 satellite0)
  (power_avail satellite0)
  (pointing satellite0 star6)
  (supports instrument2 thermograph1)
  (supports instrument2 spectrograph0)
  (calibration_target instrument2 star1)
  (supports instrument3 spectrograph0)
  (supports instrument3 thermograph1)
  (calibration_target instrument3 star0)
  (on_board instrument2 satellite1)
  (on_board instrument3 satellite1)
  (power_avail satellite1)
  (pointing satellite1 star4)
 )
 (:goal (and
  (have_image planet2 spectrograph0)
  (have_image planet3 spectrograph0)
  (have_image star4 spectrograph0)
  (have_image star5 spectrograph0)
  (have_image star6 thermograph1)
 ))
)
