from __future__ import annotations

from temporal_specification.pddl_mapping import map_event_atom_to_pddl_fluent


def test_transport_delivery_event_maps_to_package_location_fluent() -> None:
	assert map_event_atom_to_pddl_fluent(
		"deliver(package-0, city-loc-0)",
		domain_key="transport",
	) == "at(package-0, city-loc-0)"


def test_flattened_blocks_event_maps_to_on_fluent() -> None:
	assert map_event_atom_to_pddl_fluent(
		"do_put_on_b4_b2",
		domain_key="blocksworld",
	) == "on(b4, b2)"


def test_blocks_on_table_event_maps_to_official_ontable_fluent() -> None:
	assert map_event_atom_to_pddl_fluent(
		"do_on_table(b4)",
		domain_key="blocksworld",
	) == "ontable(b4)"


def test_negated_event_mapping_preserves_agent_speak_negation() -> None:
	assert map_event_atom_to_pddl_fluent(
		"~get_soil_data(waypoint2)",
		domain_key="marsrover",
	) == "not communicated_soil_data(waypoint2)"
