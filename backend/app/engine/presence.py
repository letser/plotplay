"""NPC presence utilities for PlotPlay sessions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.conditions import ConditionEvaluator
from app.models.characters import Character

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine


class PresenceService:
    """Updates NPC presence based on schedules and current location."""

    def __init__(self, engine: "GameEngine") -> None:
        self.engine = engine
        self.logger = engine.logger

    def refresh(self) -> None:
        state = self.engine.state_manager.state
        current_loc = state.location_current
        evaluator = ConditionEvaluator(state, rng_seed=self.engine.get_turn_seed())

        for char in self.engine.game_def.characters:
            if char.id == "player" or not char.schedule:
                continue

            for rule in char.schedule:
                if rule.location != current_loc:
                    continue

                if evaluator.evaluate(rule.when):
                    if char.id not in state.present_chars:
                        state.present_chars.append(char.id)
                        self.logger.info(
                            "NPC '%s' appeared in '%s' based on schedule.",
                            char.id,
                            current_loc,
                        )
                    break
