

(define (problem blocksworld_qclear-p025)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 b5 b6 b7 b8 b9 b10 b11 b12 )
(:init
(arm-empty)
(on b1 b9)
(on b2 b8)
(on b3 b1)
(on b4 b7)
(on b5 b11)
(on-table b6)
(on b7 b6)
(on b8 b5)
(on b9 b4)
(on-table b10)
(on-table b11)
(on b12 b2)
(clear b3)
(clear b10)
(clear b12)
)
(:goal
(and
(clear b2)
)
)
)


