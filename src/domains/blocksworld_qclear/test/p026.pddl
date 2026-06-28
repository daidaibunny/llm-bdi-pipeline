

(define (problem blocksworld_qclear-p026)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 b5 b6 b7 b8 b9 b10 b11 b12 )
(:init
(arm-empty)
(on b1 b11)
(on b2 b10)
(on b3 b12)
(on b4 b9)
(on b5 b6)
(on b6 b3)
(on-table b7)
(on b8 b5)
(on-table b9)
(on b10 b8)
(on b11 b7)
(on-table b12)
(clear b1)
(clear b2)
(clear b4)
)
(:goal
(and
(clear b6)
)
)
)


