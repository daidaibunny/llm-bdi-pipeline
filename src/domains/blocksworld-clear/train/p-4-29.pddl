

(define (problem BW-rand-4)
(:domain blocksworld)
(:objects b1 b2 b3 b4 )
(:init
(arm-empty)
(on b1 b3)
(on b2 b1)
(on-table b3)
(on-table b4)
(clear b2)
(clear b4)
)
(:goal
(and
(clear b1))
)
)
