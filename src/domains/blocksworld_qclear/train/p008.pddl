

(define (problem blocksworld_qclear-p008)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 b5 b6 )
(:init
(arm-empty)
(on-table b1)
(on b2 b3)
(on b3 b4)
(on b4 b1)
(on-table b5)
(on b6 b2)
(clear b5)
(clear b6)
)
(:goal
(and
(clear b3)
)
)
)


