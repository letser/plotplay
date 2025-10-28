"""Location and zone discovery utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.conditions import ConditionEvaluator

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine


class DiscoveryService:
    """Updates discovered zones/locations based on current state."""

    def __init__(self, engine: "GameEngine") -> None:
        self.engine = engine
        self.logger = engine.logger

    def refresh(self) -> None:
        state = self.engine.state_manager.state
        evaluator = ConditionEvaluator(state, rng_seed=self.engine._get_turn_seed())

        for zone in self.engine.game_def.zones:
            if zone.id not in state.discovered_zones:
                # Support both old test format (discovery_conditions) and new format (access.discovered_when)
                zone_conditions = getattr(zone, "discovery_conditions", None)
                if zone_conditions:
                    # Old format: list of conditions
                    for condition in zone_conditions:
                        if evaluator.evaluate(condition):
                            state.discovered_zones.append(zone.id)
                            self.logger.info("Discovered new zone '%s'.", zone.id)
                            for loc in zone.locations:
                                if loc.id not in state.discovered_locations:
                                    state.discovered_locations.append(loc.id)
                                    self.logger.info(
                                        "Discovered new location '%s' in zone '%s'.",
                                        loc.id,
                                        zone.id,
                                    )
                            break
                else:
                    # New format: zone.access.discovered_when
                    zone_condition = getattr(zone.access, 'discovered_when', None) if hasattr(zone, 'access') else None
                    if zone_condition and evaluator.evaluate(zone_condition):
                        state.discovered_zones.append(zone.id)
                        self.logger.info("Discovered new zone '%s'.", zone.id)
                        for loc in zone.locations:
                            if loc.id not in state.discovered_locations:
                                state.discovered_locations.append(loc.id)
                                self.logger.info(
                                    "Discovered new location '%s' in zone '%s'.",
                                    loc.id,
                                    zone.id,
                                )

            # Check individual location discovery conditions
            for loc in zone.locations:
                if loc.id in state.discovered_locations:
                    continue
                # Support both old and new formats
                loc_conditions = getattr(loc, "discovery_conditions", None)
                if loc_conditions:
                    # Old format: list of conditions
                    for condition in loc_conditions:
                        if evaluator.evaluate(condition):
                            state.discovered_locations.append(loc.id)
                            self.logger.info("Discovered new location: '%s'.", loc.id)
                            break
                else:
                    # New format: loc.access.discovered_when
                    loc_condition = getattr(loc.access, 'discovered_when', None) if hasattr(loc, 'access') else None
                    if loc_condition and evaluator.evaluate(loc_condition):
                        state.discovered_locations.append(loc.id)
                        self.logger.info("Discovered new location: '%s'.", loc.id)
