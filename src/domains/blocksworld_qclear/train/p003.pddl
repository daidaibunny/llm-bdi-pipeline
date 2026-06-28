

(define (problem blocksworld_qclear-p003)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 )
(:init
(arm-empty)
(on-table b1)
(on b2 b1)
(on b3 b4)
(on-table b4)
(clear b2)
(clear b3)
)
(:goal
(and
(clear b1)
)
)
)


