

(define (problem blocksworld_qclear-p011)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 b5 b6 b7 )
(:init
(arm-empty)
(on b1 b7)
(on b2 b1)
(on b3 b2)
(on-table b4)
(on b5 b3)
(on-table b6)
(on-table b7)
(clear b4)
(clear b5)
(clear b6)
)
(:goal
(and
(clear b3)
)
)
)


