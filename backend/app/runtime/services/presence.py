"""
NPC presence updates for the new runtime engine.
"""

from __future__ import annotations

from app.runtime.session import SessionRuntime


class PresenceService:
    """Refreshes state.present_characters based on schedules and location."""

    def __init__(self, runtime: SessionRuntime) -> None:
        self.runtime = runtime
        self.logger = runtime.logger

    def refresh(self) -> None:
        state = self.runtime.state_manager.state
        current_location = state.current_location
        present = ["player"]

        evaluator = self.runtime.state_manager.create_evaluator()

        for character in self.runtime.index.characters.values():
            if character.id == "player" or not character.schedule:
                continue

            for rule in character.schedule:
                if rule.location != current_location:
                    continue
                if evaluator.evaluate_object_conditions(rule):
                    present.append(character.id)
                    break

        state.present_characters = present
