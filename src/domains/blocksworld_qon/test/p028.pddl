

(define (problem blocksworld_qon-p028)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 b5 b6 b7 b8 b9 b10 b11 b12 b13 )
(:init
(arm-empty)
(on b1 b13)
(on b2 b10)
(on-table b3)
(on b4 b9)
(on-table b5)
(on-table b6)
(on b7 b4)
(on b8 b3)
(on b9 b5)
(on-table b10)
(on b11 b1)
(on-table b12)
(on b13 b12)
(clear b2)
(clear b6)
(clear b7)
(clear b8)
(clear b11)
)
(:goal
(and
(on b3 b4)
)
)
)


