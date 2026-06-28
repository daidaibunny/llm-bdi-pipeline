

(define (problem blocksworld_qbw-p024)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 b5 b6 b7 b8 b9 b10 b11 )
(:init
(arm-empty)
(on b1 b8)
(on-table b2)
(on b3 b7)
(on b4 b9)
(on b5 b6)
(on b6 b11)
(on b7 b4)
(on-table b8)
(on b9 b1)
(on b10 b2)
(on b11 b3)
(clear b5)
(clear b10)
)
(:goal
(and
(on b2 b10)
(on b4 b7)
(on b5 b9)
(on b6 b1)
(on b7 b6)
(on b10 b5)
(on b11 b4))
)
)


