(define (domain temporal-conformance)
 (:requirements :strips :typing :numeric-fluents)
 (:types item)
 (:predicates
  (ready ?x - item)
  (done ?x - item)
 )
 (:functions (level))
 (:action finish
  :parameters (?x - item)
  :precondition (ready ?x)
  :effect (and
   (done ?x)
   (not (ready ?x))
  )
 )
)
