(define (problem 4obs_2sat_3mod)
 (:domain satellite)
 (:objects
  instrument0 instrument1 instrument2 instrument3 - instrument
  satellite0 satellite1 - satellite
  infrared2 thermograph1 spectrograph0 - mode
  groundstation1 star0 star2 phenomenon3 planet4 phenomenon5 - direction
 )
 (:init
  (supports instrument0 spectrograph0)
  (calibration_target instrument0 star0)
  (supports instrument1 thermograph1)
  (supports instrument1 spectrograph0)
  (calibration_target instrument1 groundstation1)
  (on_board instrument0 satellite0)
  (on_board instrument1 satellite0)
  (power_avail satellite0)
  (pointing satellite0 phenomenon3)
  (supports instrument2 thermograph1)
  (calibration_target instrument2 groundstation1)
  (supports instrument3 spectrograph0)
  (supports instrument3 thermograph1)
  (supports instrument3 infrared2)
  (calibration_target instrument3 star0)
  (on_board instrument2 satellite1)
  (on_board instrument3 satellite1)
  (power_avail satellite1)
  (pointing satellite1 groundstation1)
 )
 (:goal (and
  (have_image star2 infrared2)
  (have_image phenomenon3 spectrograph0)
  (have_image planet4 thermograph1)
  (have_image phenomenon5 thermograph1)
 ))
)
