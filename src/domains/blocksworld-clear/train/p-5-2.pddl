

(define (problem BW-rand-5)
(:domain blocksworld)
(:objects b1 b2 b3 b4 b5 )
(:init
(arm-empty)
(on-table b1)
(on-table b2)
(on b3 b5)
(on b4 b1)
(on b5 b2)
(clear b3)
(clear b4)
)
(:goal
(and
(clear b1))
)
)
