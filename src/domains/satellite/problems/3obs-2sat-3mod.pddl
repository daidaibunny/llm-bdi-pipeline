(define (problem 3obs_2sat_3mod)
 (:domain satellite)
 (:objects
  instrument11 instrument01 instrument12 instrument03 instrument02 - instrument
  satellite0 satellite1 - satellite
  thermograph x_ray hd_video - mode
  GroundStation0 GroundStation1 Phenomenon6 Phenomenon7 Phenomenon4 Star5 - direction
 )
 (:init
  (on_board instrument01 satellite0)
  (supports instrument01 thermograph)
  (calibration_target instrument01 GroundStation0)
  (on_board instrument02 satellite0)
  (supports instrument02 x_ray)
  (calibration_target instrument02 GroundStation0)
  (on_board instrument03 satellite0)
  (supports instrument03 hd_video)
  (calibration_target instrument03 GroundStation0)
  (power_avail satellite0)
  (pointing satellite0 Phenomenon6)
  (on_board instrument11 satellite1)
  (supports instrument11 thermograph)
  (calibration_target instrument11 GroundStation1)
  (on_board instrument12 satellite1)
  (supports instrument12 x_ray)
  (calibration_target instrument12 GroundStation1)
  (power_avail satellite1)
  (pointing satellite1 Phenomenon7)
 )
 (:goal (and
  (have_image Phenomenon4 thermograph)
  (have_image Star5 x_ray)
  (have_image Phenomenon6 hd_video)
 ))
)
