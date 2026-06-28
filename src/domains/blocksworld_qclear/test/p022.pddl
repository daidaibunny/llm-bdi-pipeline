

(define (problem blocksworld_qclear-p022)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 b5 b6 b7 b8 b9 b10 b11 )
(:init
(arm-empty)
(on b1 b4)
(on b2 b1)
(on b3 b2)
(on b4 b8)
(on b5 b3)
(on-table b6)
(on b7 b5)
(on-table b8)
(on b9 b11)
(on b10 b9)
(on b11 b7)
(clear b6)
(clear b10)
)
(:goal
(and
(clear b4)
)
)
)


