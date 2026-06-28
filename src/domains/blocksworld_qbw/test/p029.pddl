

(define (problem blocksworld_qbw-p029)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 b5 b6 b7 b8 b9 b10 b11 b12 b13 )
(:init
(arm-empty)
(on b1 b8)
(on b2 b4)
(on-table b3)
(on-table b4)
(on-table b5)
(on b6 b12)
(on-table b7)
(on b8 b9)
(on b9 b5)
(on b10 b3)
(on-table b11)
(on b12 b13)
(on b13 b10)
(clear b1)
(clear b2)
(clear b6)
(clear b7)
(clear b11)
)
(:goal
(and
(on b2 b5)
(on b3 b7)
(on b4 b1)
(on b5 b6)
(on b7 b11)
(on b9 b3)
(on b11 b8))
)
)


