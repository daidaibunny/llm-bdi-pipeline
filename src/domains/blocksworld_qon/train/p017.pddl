

(define (problem blocksworld_qon-p017)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 b5 b6 b7 b8 b9 )
(:init
(arm-empty)
(on b1 b4)
(on b2 b7)
(on-table b3)
(on-table b4)
(on b5 b3)
(on b6 b5)
(on-table b7)
(on b8 b2)
(on b9 b1)
(clear b6)
(clear b8)
(clear b9)
)
(:goal
(and
(on b1 b9)
)
)
)


