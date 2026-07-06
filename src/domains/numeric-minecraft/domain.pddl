; https://github.com/SPL-BGU/PDDL-Minecraft/blob/main/planning/pogo_stick/advanced_minecraft_domain.pddl
; With the following modifications:
; - split craft_tree_tap and craft_wooden_pogo into two actions (move -> craft)
; - flip goal of crafting pogo sticks to decrement rather than increment

(define (domain numeric-minecraft)

    (:requirements :strips :typing :negative-preconditions :fluents :disjunctive-preconditions)

    (:types
        cell - object
    )

    (:constants
        crafting_table - cell
    )

    (:predicates
        (position ?c - cell)

        ; Map
        (tree_cell ?c - cell)
        (air_cell ?c - cell)
    )

    (:functions
        ; Items
        (count_log_in_inventory)
        (count_planks_in_inventory)
        (count_stick_in_inventory)
        (count_sack_polyisoprene_pellets_in_inventory)
        (count_tree_tap_in_inventory)
        (pogo_sticks_to_make)
    )

    ; Actions
    (:action TP_TO
        :parameters (?from - cell ?to - cell)
        :precondition (and
            (position ?from)
            (not (position ?to))
        )
        :effect (and
            (not (position ?from))
            (position ?to)
        )
    )

    (:action BREAK
        :parameters (?pos - cell)
        :precondition (and
            (position ?pos)
            (tree_cell ?pos)
        )
        :effect (and
            (not (tree_cell ?pos))
            (air_cell ?pos)
            (increase (count_log_in_inventory) 1)
        )
    )

    (:action CRAFT_PLANK
        :parameters ()
        :precondition (and
            (>= (count_log_in_inventory) 1)
        )
        :effect (and
            (decrease (count_log_in_inventory) 1)
            (increase (count_planks_in_inventory) 4)
        )
    )

    (:action CRAFT_STICK
        :parameters ()
        :precondition (and
            (>= (count_planks_in_inventory) 2)
        )
        :effect (and
            (decrease (count_planks_in_inventory) 2)
            (increase (count_stick_in_inventory) 4)
        )
    )

    (:action CRAFT_TREE_TAP
        :parameters ()
        :precondition (and
            (position crafting_table)
            (>= (count_planks_in_inventory) 5)
            (>= (count_stick_in_inventory) 1)
        )
        :effect (and
            (decrease (count_planks_in_inventory) 5)
            (decrease (count_stick_in_inventory) 1)
            (increase (count_tree_tap_in_inventory) 1)
        )
    )

    (:action CRAFT_WOODEN_POGO
        :parameters ()
        :precondition (and
            (position crafting_table)
            (>= (count_planks_in_inventory) 2)
            (>= (count_stick_in_inventory) 4)
            (>= (count_sack_polyisoprene_pellets_in_inventory) 1)
        )
        :effect (and
            (decrease (count_planks_in_inventory) 2)
            (decrease (count_stick_in_inventory) 4)
            (decrease
                (count_sack_polyisoprene_pellets_in_inventory)
                1)
            (decrease (pogo_sticks_to_make) 1)
        )
    )

    (:action PLACE_TREE_TAP
        :parameters (?pos - cell)
        :precondition (and
            (position ?pos)
            (tree_cell ?pos)
            (>= (count_tree_tap_in_inventory) 1)
        )
        :effect (and
            (increase
                (count_sack_polyisoprene_pellets_in_inventory)
                1)
        )
    )
)
