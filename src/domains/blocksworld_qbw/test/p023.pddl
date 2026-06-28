

(define (problem blocksworld_qbw-p023)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 b5 b6 b7 b8 b9 b10 b11 )
(:init
(arm-empty)
(on b1 b2)
(on b2 b7)
(on b3 b6)
(on-table b4)
(on-table b5)
(on b6 b1)
(on b7 b8)
(on b8 b10)
(on b9 b4)
(on b10 b11)
(on b11 b5)
(clear b3)
(clear b9)
)
(:goal
(and
(on b1 b5)
(on b4 b11)
(on b5 b2)
(on b6 b8)
(on b7 b3)
(on b8 b4)
(on b9 b10)
(on b11 b1))
)
)


