

(define (problem blocksworld_qclear-p004)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 b5 )
(:init
(arm-empty)
(on-table b1)
(on b2 b1)
(on b3 b4)
(on-table b4)
(on-table b5)
(clear b2)
(clear b3)
(clear b5)
)
(:goal
(and
(clear b1)
)
)
)


