

(define (problem blocksworld_qbw-p019)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 b5 b6 b7 b8 b9 b10 )
(:init
(arm-empty)
(on b1 b9)
(on-table b2)
(on b3 b6)
(on-table b4)
(on b5 b2)
(on b6 b8)
(on b7 b5)
(on b8 b4)
(on b9 b7)
(on-table b10)
(clear b1)
(clear b3)
(clear b10)
)
(:goal
(and
(on b1 b4)
(on b4 b10)
(on b6 b1)
(on b8 b3)
(on b9 b2)
(on b10 b9))
)
)


