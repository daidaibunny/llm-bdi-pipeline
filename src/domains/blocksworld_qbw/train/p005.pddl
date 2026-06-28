

(define (problem blocksworld_qbw-p005)
(:domain blocksworld-4ops)
(:objects b1 b2 b3 b4 b5 )
(:init
(arm-empty)
(on-table b1)
(on-table b2)
(on-table b3)
(on b4 b3)
(on b5 b4)
(clear b1)
(clear b2)
(clear b5)
)
(:goal
(and
(on b3 b5)
(on b5 b2))
)
)


