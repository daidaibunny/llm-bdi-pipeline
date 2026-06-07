(define (problem 2obs_2sat_1mod)
 (:domain satellite)
 (:objects
  instrument0 instrument1 - instrument
  satellite0 satellite1 - satellite
  thermograph - mode
  GroundStation0 GroundStation1 Phenomenon6 Phenomenon7 Phenomenon4 Star5 - direction
 )
 (:init
  (on_board instrument0 satellite0)
  (supports instrument0 thermograph)
  (calibration_target instrument0 GroundStation0)
  (power_avail satellite0)
  (pointing satellite0 Phenomenon6)
  (on_board instrument1 satellite1)
  (supports instrument1 thermograph)
  (calibration_target instrument1 GroundStation1)
  (power_avail satellite1)
  (pointing satellite1 Phenomenon7)
 )
 (:goal (and
  (have_image Phenomenon4 thermograph)
  (have_image Star5 thermograph)
 ))
)
