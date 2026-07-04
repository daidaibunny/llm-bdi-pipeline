(define (domain logistics)
    (:requirements :strips :typing)

    (:types
        locatable - object
        vehicle - locatable

        location - object
        city - object
        package - locatable
        truck - vehicle
        airplane - vehicle
    )

    (:predicates
        (has-airport ?location - location)
        (at ?locatable - locatable ?location - location)
        (in ?package - package ?vehicle - vehicle)
        (in-city ?location - location ?city - city)
    )

    (:action LOAD-TRUCK
        :parameters (?obj - package ?truck - truck ?loc - location)
        :precondition (and
            (at ?truck ?loc) (at ?obj ?loc))
        :effect (and (not (at ?obj ?loc)) (in ?obj ?truck))
    )

    (:action LOAD-AIRPLANE
        :parameters (?obj - package ?airplane - airplane ?loc - location)
        :precondition (and
            (at ?obj ?loc) (at ?airplane ?loc))
        :effect (and (not (at ?obj ?loc)) (in ?obj ?airplane))
    )

    (:action UNLOAD-TRUCK
        :parameters (?obj - package ?truck - truck ?loc - location)
        :precondition (and
            (at ?truck ?loc) (in ?obj ?truck))
        :effect (and (not (in ?obj ?truck)) (at ?obj ?loc))
    )

    (:action UNLOAD-AIRPLANE
        :parameters (?obj - package ?airplane - airplane ?loc - location)
        :precondition (and
            (in ?obj ?airplane) (at ?airplane ?loc))
        :effect (and (not (in ?obj ?airplane)) (at ?obj ?loc))
    )

    (:action DRIVE-TRUCK
        :parameters (?truck - truck ?loc-from - location ?loc-to - location ?city - city)
        :precondition (and
            (at ?truck ?loc-from)
            (in-city ?loc-from ?city)
            (in-city ?loc-to ?city))
        :effect (and (not (at ?truck ?loc-from)) (at ?truck ?loc-to))
    )

    (:action FLY-AIRPLANE
        :parameters (?airplane - airplane ?loc-from - location ?loc-to - location)
        :precondition (and (has-airport ?loc-from) (has-airport ?loc-to)
            (at ?airplane ?loc-from))
        :effect (and (not (at ?airplane ?loc-from)) (at ?airplane ?loc-to))
    )
)