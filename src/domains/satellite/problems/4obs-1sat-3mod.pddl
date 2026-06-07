(define (problem 4obs_1sat_3mod)
 (:domain satellite)
 (:objects
  instrument0 instrument1 - instrument
  satellite0 - satellite
  infrared0 spectrograph1 infrared2 - mode
  star0 groundstation1 planet2 planet3 star4 planet5 - direction
 )
 (:init
  (supports instrument0 infrared2)
  (supports instrument0 spectrograph1)
  (supports instrument0 infrared0)
  (calibration_target instrument0 star0)
  (supports instrument1 infrared2)
  (supports instrument1 spectrograph1)
  (calibration_target instrument1 groundstation1)
  (on_board instrument0 satellite0)
  (on_board instrument1 satellite0)
  (power_avail satellite0)
  (pointing satellite0 star0)
 )
 (:goal (and
  (have_image planet2 infrared2)
  (have_image planet3 infrared2)
  (have_image star4 infrared0)
  (have_image planet5 infrared2)
 ))
)
