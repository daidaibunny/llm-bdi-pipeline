


(define (problem logistics-c1-s2-p6-a1)
(:domain logistics)
(:objects a0 - airplane
          c0 - city
          t0 - truck
          l0-0 l0-1 - location
          p0 p1 p2 p3 p4 p5 - package
)
(:init
    (in-city  l0-0 c0)
    (in-city  l0-1 c0)
    (has-airport l0-0)
    (at t0 l0-0)
    (at p0 l0-0)
    (at p1 l0-1)
    (at p2 l0-0)
    (at p3 l0-1)
    (at p4 l0-0)
    (at p5 l0-1)
    (at a0 l0-0)
)
(:goal
    (and
        (at p0 l0-1)
        (at p1 l0-0)
        (at p2 l0-1)
        (at p3 l0-0)
        (at p4 l0-1)
        (at p5 l0-1)
    )
)
)



