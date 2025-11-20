"""NPC presence utilities for PlotPlay sessions."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine


class PresenceService:
    """Updates NPC presence based on schedules and current location."""

    def __init__(self, engine: GameEngine) -> None:
        self.engine = engine
        self.logger = engine.logger

    def refresh(self) -> None:

        for char in self.engine.index.characters.values():
            if char.id == "player" or not char.schedule:
                continue

            for rule in char.schedule:
                if rule.location != self.engine.state.current_location:
                    continue

                if self.engine.evaluator.evaluate_object_conditions(rule):
                    if char.id not in self.engine.state.present_characters:
                        self.engine.state.present_characters.append(char.id)
                        self.logger.info(
                            "NPC '%s' appeared in '%s' based on schedule.",
                            char.id,
                            self.engine.state.current_location,
                        )
                    break
