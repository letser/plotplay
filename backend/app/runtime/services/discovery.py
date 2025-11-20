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

        for zone in self.runtime.game.zones:
            if zone.id not in state.discovered_zones:
                condition = getattr(zone.access, "discovered_when", None) if getattr(zone, "access", None) else None
                if not condition or evaluator.evaluate(condition):
                    state.discovered_zones.add(zone.id)
                    for loc in zone.locations:
                        state.discovered_locations.add(loc.id)

            for location in zone.locations:
                if location.id in state.discovered_locations:
                    continue
                condition = getattr(location.access, "discovered_when", None) if getattr(location, "access", None) else None
                if condition and evaluator.evaluate(condition):
                    state.discovered_locations.add(location.id)
