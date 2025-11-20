"""
Placeholder modifier service.
"""

from __future__ import annotations

from app.models.effects import ApplyModifierEffect, RemoveModifierEffect
from app.runtime.session import SessionRuntime


class ModifierService:
    """Stub modifier manager for the new runtime."""

    def __init__(self, runtime: SessionRuntime) -> None:
        self.runtime = runtime

    def apply_effect(self, effect: ApplyModifierEffect | RemoveModifierEffect) -> None:
        self.runtime.logger.debug("TODO: implement modifier application for %s", effect)

    def update_modifiers_for_turn(self, state) -> None:
        """Placeholder for auto-activation logic."""
        return

    def tick_durations(self, state, minutes: int) -> None:
        """Placeholder for duration ticking."""
        return
