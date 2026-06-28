

(define (problem blocksworld_qbw-p008)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 b5 b6 )
(:init
(arm-empty)
(on-table b1)
(on b2 b3)
(on b3 b4)
(on b4 b1)
(on-table b5)
(on b6 b2)
(clear b5)
(clear b6)
)
(:goal
(and
(on b2 b6)
(on b4 b1)
(on b5 b2)
(on b6 b4))
)
)


