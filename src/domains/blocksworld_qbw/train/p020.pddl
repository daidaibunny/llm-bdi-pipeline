

(define (problem blocksworld_qbw-p020)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 b5 b6 b7 b8 b9 b10 )
(:init
(arm-empty)
(on b1 b5)
(on-table b2)
(on-table b3)
(on b4 b2)
(on b5 b9)
(on b6 b4)
(on b7 b10)
(on b8 b1)
(on b9 b3)
(on-table b10)
(clear b6)
(clear b7)
(clear b8)
)
(:goal
(and
(on b1 b2)
(on b3 b1)
(on b4 b7)
(on b5 b6)
(on b7 b9)
(on b9 b5)
(on b10 b8))
)
)


