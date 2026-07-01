(define (domain sokoban-sequential)
  (:requirements :typing)
  (:types stone location direction)
  (:predicates (clear ?l - location)
               (player ?l - location)
         (at ?s - stone ?l - location)
         (at-goal ?s - stone)
         (IS-GOAL ?l - location)
         (IS-NONGOAL ?l - location)
               (ADJ-RIGHT ?from ?to - location)
               (ADJ-DOWN ?from ?to - location)
  )

  (:action move-RIGHT
   :parameters   (?from ?to - location)
   :precondition (and (player ?from) (clear ?to) (ADJ-RIGHT ?from ?to))
   :effect       (and (not (player ?from)) (not (clear ?to)) (player ?to) (clear ?from))
  )
  (:action move-DOWN
   :parameters   (?from ?to - location)
   :precondition (and (player ?from) (clear ?to) (ADJ-DOWN ?from ?to))
   :effect       (and (not (player ?from)) (not (clear ?to)) (player ?to) (clear ?from))
  )
  (:action move-LEFT
   :parameters   (?from ?to - location)
   :precondition (and (player ?from) (clear ?to) (ADJ-RIGHT ?to ?from))
   :effect       (and (not (player ?from)) (not (clear ?to)) (player ?to) (clear ?from))
  )
  (:action move-UP
   :parameters   (?from ?to - location)
   :precondition (and (player ?from) (clear ?to) (ADJ-DOWN ?to ?from))
   :effect       (and (not (player ?from)) (not (clear ?to)) (player ?to) (clear ?from))
  )

  (:action push-to-nongoal-RIGHT
   :parameters   (?s - stone ?ppos ?from ?to - location)
   :precondition (and (player ?ppos) (at ?s ?from) (clear ?to) (ADJ-RIGHT ?ppos ?from) (ADJ-RIGHT ?from ?to) (IS-NONGOAL ?to))
   :effect       (and (not (player ?ppos)) (not (at ?s ?from)) (not (clear ?to)) (player ?from) (at ?s ?to) (clear ?ppos) (not (at-goal ?s)))
  )
  (:action push-to-nongoal-DOWN
   :parameters   (?s - stone ?ppos ?from ?to - location)
   :precondition (and (player ?ppos) (at ?s ?from) (clear ?to) (ADJ-DOWN ?ppos ?from) (ADJ-DOWN ?from ?to) (IS-NONGOAL ?to))
   :effect       (and (not (player ?ppos)) (not (at ?s ?from)) (not (clear ?to)) (player ?from) (at ?s ?to) (clear ?ppos) (not (at-goal ?s)))
  )
  (:action push-to-nongoal-LEFT
   :parameters   (?s - stone ?ppos ?from ?to - location)
   :precondition (and (player ?ppos) (at ?s ?from) (clear ?to) (ADJ-RIGHT ?from ?ppos) (ADJ-RIGHT ?to ?from) (IS-NONGOAL ?to))
   :effect       (and (not (player ?ppos)) (not (at ?s ?from)) (not (clear ?to)) (player ?from) (at ?s ?to) (clear ?ppos) (not (at-goal ?s)))
  )
  (:action push-to-nongoal-UP
   :parameters   (?s - stone ?ppos ?from ?to - location)
   :precondition (and (player ?ppos) (at ?s ?from) (clear ?to) (ADJ-DOWN ?from ?ppos) (ADJ-DOWN ?to ?from) (IS-NONGOAL ?to))
   :effect       (and (not (player ?ppos)) (not (at ?s ?from)) (not (clear ?to)) (player ?from) (at ?s ?to) (clear ?ppos) (not (at-goal ?s)))
  )

  (:action push-to-goal-RIGHT
   :parameters   (?s - stone ?ppos ?from ?to - location)
   :precondition (and (player ?ppos) (at ?s ?from) (clear ?to) (ADJ-RIGHT ?ppos ?from) (ADJ-RIGHT ?from ?to) (IS-GOAL ?to))
   :effect       (and (not (player ?ppos)) (not (at ?s ?from)) (not (clear ?to)) (player ?from) (at ?s ?to) (clear ?ppos) (at-goal ?s))
  )
  (:action push-to-goal-DOWN
   :parameters   (?s - stone ?ppos ?from ?to - location)
   :precondition (and (player ?ppos) (at ?s ?from) (clear ?to) (ADJ-DOWN ?ppos ?from) (ADJ-DOWN ?from ?to) (IS-GOAL ?to))
   :effect       (and (not (player ?ppos)) (not (at ?s ?from)) (not (clear ?to)) (player ?from) (at ?s ?to) (clear ?ppos) (at-goal ?s))
  )
  (:action push-to-goal-LEFT
   :parameters   (?s - stone ?ppos ?from ?to - location)
   :precondition (and (player ?ppos) (at ?s ?from) (clear ?to) (ADJ-RIGHT ?from ?ppos) (ADJ-RIGHT ?to ?from) (IS-GOAL ?to))
   :effect       (and (not (player ?ppos)) (not (at ?s ?from)) (not (clear ?to)) (player ?from) (at ?s ?to) (clear ?ppos) (at-goal ?s))
  )
  (:action push-to-goal-UP
   :parameters   (?s - stone ?ppos ?from ?to - location)
   :precondition (and (player ?ppos) (at ?s ?from) (clear ?to) (ADJ-DOWN ?from ?ppos) (ADJ-DOWN ?to ?from) (IS-GOAL ?to))
   :effect       (and (not (player ?ppos)) (not (at ?s ?from)) (not (clear ?to)) (player ?from) (at ?s ?to) (clear ?ppos) (at-goal ?s))
  )
)
