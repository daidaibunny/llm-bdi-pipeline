


(define (problem miconic-p001)
   (:domain miconic)
   (:objects p0 - passenger
             f0 f1 - floor)


(:init
(above f0 f1)



(origin p0 f0)
(destin p0 f1)






(lift-at f0)
)


(:goal


(and
(served p0)
))
)


