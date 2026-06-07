(define (problem 3obs_2sat_1mod)
 (:domain satellite)
 (:objects
  instrument01 instrument11 - instrument
  satellite0 satellite1 - satellite
  thermograph - mode
  GroundStation0 GroundStation1 Phenomenon6 Phenomenon7 Phenomenon4 Star5 - direction
 )
 (:init
  (on_board instrument01 satellite0)
  (supports instrument01 thermograph)
  (calibration_target instrument01 GroundStation0)
  (power_avail satellite0)
  (pointing satellite0 Phenomenon6)
  (on_board instrument11 satellite1)
  (supports instrument11 thermograph)
  (calibration_target instrument11 GroundStation1)
  (power_avail satellite1)
  (pointing satellite1 Phenomenon7)
 )
 (:goal (and
  (have_image Phenomenon4 thermograph)
  (have_image Star5 thermograph)
  (have_image Phenomenon6 thermograph)
 ))
)
