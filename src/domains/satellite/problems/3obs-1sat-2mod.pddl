(define (problem 3obs_1sat_2mod)
 (:domain satellite)
 (:objects
  instrument01 instrument02 - instrument
  satellite0 - satellite
  thermograph x_ray - mode
  GroundStation0 GroundStation1 Phenomenon6 Phenomenon7 Phenomenon4 Star5 - direction
 )
 (:init
  (on_board instrument01 satellite0)
  (supports instrument01 thermograph)
  (calibration_target instrument01 GroundStation0)
  (on_board instrument02 satellite0)
  (supports instrument02 x_ray)
  (calibration_target instrument02 GroundStation0)
  (power_avail satellite0)
  (pointing satellite0 Phenomenon6)
 )
 (:goal (and
  (have_image Phenomenon4 thermograph)
  (have_image Star5 x_ray)
  (have_image Phenomenon6 x_ray)
 ))
)
