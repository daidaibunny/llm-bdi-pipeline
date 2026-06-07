(define (problem sat_A)
 (:domain satellite)
 (:objects
  instrument0 - instrument
  satellite0 - satellite
  thermograph0 - mode
  GroundStation2 Phenomenon6 Phenomenon4 - direction
 )
 (:init
  (on_board instrument0 satellite0)
  (supports instrument0 thermograph0)
  (calibration_target instrument0 GroundStation2)
  (power_avail satellite0)
  (pointing satellite0 Phenomenon6)
 )
 (:goal (and
  (have_image Phenomenon4 thermograph0)
 ))
)
