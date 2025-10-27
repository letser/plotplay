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
            zone_conditions = getattr(zone, "discovery_conditions", None)
            if zone_conditions and zone.id not in state.discovered_zones:
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
            for loc in zone.locations:
                if loc.id in state.discovered_locations:
                    continue
                loc_conditions = getattr(loc, "discovery_conditions", None)
                if not loc_conditions:
                    continue
                for condition in loc_conditions:
                    if evaluator.evaluate(condition):
                        state.discovered_locations.append(loc.id)
                        self.logger.info("Discovered new location: '%s'.", loc.id)
                        break
