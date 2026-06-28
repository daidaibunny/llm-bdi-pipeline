

(define (problem blocksworld_qon-p014)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 b5 b6 b7 b8 )
(:init
(arm-empty)
(on-table b1)
(on b2 b6)
(on b3 b7)
(on b4 b3)
(on b5 b1)
(on b6 b8)
(on-table b7)
(on b8 b5)
(clear b2)
(clear b4)
)
(:goal
(and
(on b2 b3)
)
)
)


