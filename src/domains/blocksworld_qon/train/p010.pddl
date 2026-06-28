

(define (problem blocksworld_qon-p010)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 b5 b6 b7 )
(:init
(arm-empty)
(on b1 b3)
(on b2 b5)
(on b3 b2)
(on b4 b6)
(on-table b5)
(on b6 b1)
(on-table b7)
(clear b4)
(clear b7)
)
(:goal
(and
(on b1 b4)
)
)
)


