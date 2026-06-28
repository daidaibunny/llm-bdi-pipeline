

(define (problem blocksworld_qclear-p027)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 b5 b6 b7 b8 b9 b10 b11 b12 )
(:init
(arm-empty)
(on-table b1)
(on-table b2)
(on b3 b2)
(on b4 b7)
(on b5 b6)
(on-table b6)
(on b7 b12)
(on b8 b5)
(on b9 b10)
(on b10 b4)
(on b11 b3)
(on-table b12)
(clear b1)
(clear b8)
(clear b9)
(clear b11)
)
(:goal
(and
(clear b3)
)
)
)


