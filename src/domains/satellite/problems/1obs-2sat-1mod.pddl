(define (problem 1obs_2sat_1mod)
 (:domain satellite)
 (:objects
  instrument0 instrument1 - instrument
  satellite0 satellite1 - satellite
  image1 - mode
  star0 star5 phenomenon1 phenomenon2 - direction
 )
 (:init
  (on_board instrument0 satellite0)
  (supports instrument0 image1)
  (calibration_target instrument0 star0)
  (power_avail satellite0)
  (pointing satellite0 phenomenon1)
  (on_board instrument1 satellite1)
  (supports instrument1 image1)
  (calibration_target instrument1 star0)
  (power_avail satellite1)
  (pointing satellite1 phenomenon2)
 )
 (:goal (and
  (have_image phenomenon1 image1)
 ))
)
