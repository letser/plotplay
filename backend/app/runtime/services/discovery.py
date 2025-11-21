"""
Discovery utilities for the new runtime engine.
"""

from __future__ import annotations

from app.runtime.session import SessionRuntime


class DiscoveryService:
    """Marks zones/locations/actions as discovered when their conditions are met."""

    def __init__(self, runtime: SessionRuntime) -> None:
        self.runtime = runtime

    def refresh(self) -> None:
        state = self.runtime.state_manager.state
        evaluator = self.runtime.state_manager.create_evaluator()

        # Always ensure the current zone/location are marked as discovered
        if state.current_zone:
            state.discovered_zones.add(state.current_zone)
            if state.current_zone in state.zones:
                state.zones[state.current_zone].discovered = True
        if state.current_location:
            state.discovered_locations.add(state.current_location)
            if state.current_location in state.locations:
                state.locations[state.current_location].discovered = True

        for zone in self.runtime.game.zones:
            access = getattr(zone, "access", None)
            zone_state = state.zones.get(zone.id)
            auto_discovered = getattr(access, "discovered", True) if access else True
            hidden_until = getattr(access, "hidden_until_discovered", False) if access else False
            condition = getattr(access, "discovered_when", None) if access else None

            if zone.id not in state.discovered_zones:
                if auto_discovered or (condition and evaluator.evaluate(condition)):
                    state.discovered_zones.add(zone.id)
                    if zone_state:
                        zone_state.discovered = True
                    for loc in zone.locations:
                        state.discovered_locations.add(loc.id)
                elif hidden_until:
                    continue

            for location in zone.locations:
                loc_access = getattr(location, "access", None)
                loc_state = state.locations.get(location.id)
                loc_condition = getattr(loc_access, "discovered_when", None) if loc_access else None
                hidden_loc = getattr(loc_access, "hidden_until_discovered", False) if loc_access else False
                auto_loc = getattr(loc_access, "discovered", True) if loc_access else True

                if location.id in state.discovered_locations:
                    continue
                if auto_loc or (loc_condition and evaluator.evaluate(loc_condition)):
                    state.discovered_locations.add(location.id)
                    if loc_state:
                        loc_state.discovered = True
                elif hidden_loc:
                    continue
