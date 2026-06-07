(define (problem sat_B)
 (:domain satellite)
 (:objects
  instrument0_1 instrument0_2 instrument1_1 instrument1_2 - instrument
  satellite0 satellite1 - satellite
  thermograph0 - mode
  GroundStation2 Phenomenon6 Phenomenon4 - direction
 )
 (:init
  (on_board instrument0_1 satellite0)
  (supports instrument0_1 thermograph0)
  (on_board instrument0_2 satellite0)
  (supports instrument0_2 thermograph0)
  (calibration_target instrument0_1 GroundStation2)
  (calibration_target instrument0_2 GroundStation2)
  (power_avail satellite0)
  (pointing satellite0 Phenomenon6)
  (on_board instrument1_1 satellite1)
  (supports instrument1_1 thermograph0)
  (on_board instrument1_2 satellite1)
  (supports instrument1_2 thermograph0)
  (calibration_target instrument1_1 GroundStation2)
  (calibration_target instrument1_2 GroundStation2)
  (power_avail satellite1)
  (pointing satellite1 Phenomenon6)
 )
 (:goal (and
  (have_image Phenomenon4 thermograph0)
 ))
)
