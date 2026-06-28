

(define (problem blocksworld_qclear-p013)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 b5 b6 b7 b8 )
(:init
(arm-empty)
(on b1 b2)
(on-table b2)
(on b3 b6)
(on b4 b8)
(on-table b5)
(on-table b6)
(on b7 b3)
(on b8 b7)
(clear b1)
(clear b4)
(clear b5)
)
(:goal
(and
(clear b3)
)
)
)


