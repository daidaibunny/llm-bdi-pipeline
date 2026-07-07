

(define (problem BW-rand-3)
(:domain blocksworld)
(:objects b1 b2 b3 )
(:init
(arm-empty)
(on b1 b2)
(on-table b2)
(on-table b3)
(clear b1)
(clear b3)
)
(:goal
(and
(clear b1))
)
)
