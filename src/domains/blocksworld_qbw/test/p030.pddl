

(define (problem blocksworld_qbw-p030)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 b5 b6 b7 b8 b9 b10 b11 b12 b13 )
(:init
(arm-empty)
(on-table b1)
(on b2 b1)
(on b3 b9)
(on b4 b2)
(on b5 b7)
(on b6 b11)
(on b7 b4)
(on-table b8)
(on b9 b5)
(on-table b10)
(on b11 b13)
(on b12 b6)
(on b13 b8)
(clear b3)
(clear b10)
(clear b12)
)
(:goal
(and
(on b1 b6)
(on b3 b1)
(on b5 b7)
(on b6 b10)
(on b7 b2)
(on b10 b9)
(on b12 b5)
(on b13 b11))
)
)


