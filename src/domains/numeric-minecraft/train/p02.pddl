(define (problem prob2)
    (:domain numeric-minecraft)
    (:requirements :disjunctive-preconditions :fluents :negative-preconditions :strips :typing)
    (:objects
        cell0 cell1 cell2 cell3 - cell
    )
    (:init
        (= (count_log_in_inventory) 0)
        (= (count_planks_in_inventory) 0)
        (= (count_sack_polyisoprene_pellets_in_inventory) 0)
        (= (count_stick_in_inventory) 0)
        (= (count_tree_tap_in_inventory) 0)
        (= (pogo_sticks_to_make) 1)
        (air_cell cell0)
        (position cell0)
        (tree_cell cell2)
        (tree_cell cell1)
        (tree_cell cell3)
    )
    (:goal
        (= (pogo_sticks_to_make) 0)
    )
)
