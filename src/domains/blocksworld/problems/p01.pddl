(define (problem p01)
 (:domain BLOCKS)
 (:objects
  b1 b2 b3 b4 b5 - block
 )
 (:init
  (handempty)
  (ontable b1)
  (on b2 b3)
  (on b3 b5)
  (on b4 b1)
  (on b5 b4)
  (clear b2)
 )
 (:goal (and
  (on b4 b2)
  (on b1 b4)
  (on b3 b1)
 ))
)
