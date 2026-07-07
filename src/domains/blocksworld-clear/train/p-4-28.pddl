

(define (problem BW-rand-4)
(:domain blocksworld)
(:objects b1 b2 b3 b4 )
(:init
(arm-empty)
(on-table b1)
(on b2 b4)
(on-table b3)
(on b4 b3)
(clear b1)
(clear b2)
)
(:goal
(and
(clear b1))
)
)
