(define (problem ferry_01-problem)
 (:domain numeric-ferry)
 (:objects
   car1 - car
   loc1 loc2 - location
 )
 (:init (at-ferry loc1) (at car1 loc1) (= (ferry-capacity) 4))
 (:goal (and (at car1 loc2)))
)
