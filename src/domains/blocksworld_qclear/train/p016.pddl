

(define (problem blocksworld_qclear-p016)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 b5 b6 b7 b8 b9 )
(:init
(arm-empty)
(on b1 b8)
(on-table b2)
(on b3 b7)
(on b4 b9)
(on b5 b4)
(on b6 b1)
(on b7 b2)
(on b8 b5)
(on b9 b3)
(clear b6)
)
(:goal
(and
(clear b1)
)
)
)


