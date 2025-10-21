"""Modifier management service for PlotPlay."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.conditions import ConditionEvaluator
from app.core.state_manager import GameState
from app.models.effects import ApplyModifierEffect, RemoveModifierEffect

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine


class ModifierService:
    """
    Manages the activation, duration, and effects of character modifiers.

    Responsibilities:
    - Auto-activation of modifiers based on conditions
    - Duration tracking and expiration
    - Exclusive group enforcement
    - Entry/exit effect triggering
    """

    def __init__(self, engine: "GameEngine") -> None:
        self.engine = engine
        self.game_def = engine.game_def

        modifiers_config = getattr(self.game_def, "modifiers", None)
        if modifiers_config and modifiers_config.library:
            self.library = modifiers_config.library
            self.exclusions = modifiers_config.exclusions or []
        else:
            self.library = {}
            self.exclusions = []

    def update_modifiers_for_turn(self, state: GameState, rng_seed: int | None = None) -> None:
        """
        Check all defined modifiers for auto-activation based on their 'when' conditions.

        Called once per turn to evaluate condition-based modifier activation/deactivation.

        Args:
            state: Current game state
            rng_seed: RNG seed for deterministic condition evaluation
        """
        all_character_ids = list(state.meters.keys())

        for char_id in all_character_ids:
            evaluator = ConditionEvaluator(state, rng_seed=rng_seed)

            if char_id not in state.modifiers:
                state.modifiers[char_id] = []

            active_modifier_ids = {m["id"] for m in state.modifiers[char_id]}

            for modifier_id, modifier_def in self.library.items():
                if modifier_def.when:
                    expression = modifier_def.when.replace("{character}", char_id)

                    if evaluator.evaluate(expression):
                        if modifier_id not in active_modifier_ids:
                            self._apply_modifier(char_id, modifier_id, state)
                    else:
                        if modifier_id in active_modifier_ids:
                            self._remove_modifier(char_id, modifier_id, state)

    def tick_durations(self, state: GameState, minutes_passed: int) -> None:
        """
        Tick down the duration of active modifiers.

        Args:
            state: Current game state
            minutes_passed: Number of minutes elapsed
        """
        if minutes_passed == 0:
            return

        for char_id, active_mods in state.modifiers.items():
            mods_to_remove = []
            for mod in active_mods:
                if "duration" in mod and mod["duration"] is not None:
                    mod["duration"] -= minutes_passed
                    if mod["duration"] <= 0:
                        mods_to_remove.append(mod["id"])

            for mod_id in mods_to_remove:
                self._remove_modifier(char_id, mod_id, state)

    def apply_effect(self, effect: ApplyModifierEffect | RemoveModifierEffect, state: GameState) -> None:
        """
        Apply a single modifier-related effect to the state.

        Args:
            effect: ApplyModifierEffect or RemoveModifierEffect to process
            state: Current game state
        """
        if isinstance(effect, ApplyModifierEffect):
            self._apply_modifier(
                effect.target,
                effect.modifier_id,
                state,
                duration_override=effect.duration
            )
        elif isinstance(effect, RemoveModifierEffect):
            self._remove_modifier(effect.target, effect.modifier_id, state)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _apply_modifier(
        self,
        char_id: str,
        modifier_id: str,
        state: GameState,
        duration_override: int | None = None
    ) -> None:
        """
        Add a modifier to a character's active list.

        Handles exclusion groups and triggers entry effects.

        Args:
            char_id: Character to apply modifier to
            modifier_id: ID of the modifier to apply
            state: Current game state
            duration_override: Optional duration override (in minutes)
        """
        if char_id not in state.modifiers:
            state.modifiers[char_id] = []

        modifier_def = self.library.get(modifier_id)
        if not modifier_def:
            return

        active_mods = state.modifiers[char_id]
        active_ids = {m["id"] for m in active_mods}
        if modifier_id in active_ids:
            return  # Already active

        # Exclusion logic: remove other modifiers in the same exclusive group
        if modifier_def.group:
            for exclusion_rule in self.exclusions:
                if exclusion_rule.group == modifier_def.group and exclusion_rule.exclusive:
                    # Find and remove any other modifier from the same exclusive group
                    mods_to_remove = [
                        m["id"] for m in active_mods
                        if self.library.get(m["id"]) and self.library[m["id"]].group == modifier_def.group
                    ]
                    for mod_to_remove_id in mods_to_remove:
                        self._remove_modifier(char_id, mod_to_remove_id, state)

        # Add modifier with duration
        duration = duration_override if duration_override is not None else modifier_def.duration_default_min
        state.modifiers[char_id].append({"id": modifier_id, "duration": duration})

        # Trigger entry effects
        if modifier_def.entry_effects:
            self.engine.apply_effects(modifier_def.entry_effects)

    def _remove_modifier(self, char_id: str, modifier_id: str, state: GameState) -> None:
        """
        Remove a modifier from a character's active list.

        Triggers exit effects before removal.

        Args:
            char_id: Character to remove modifier from
            modifier_id: ID of the modifier to remove
            state: Current game state
        """
        if char_id in state.modifiers:
            modifier_def = self.library.get(modifier_id)

            # Trigger exit effects
            if modifier_def and modifier_def.exit_effects:
                self.engine.apply_effects(modifier_def.exit_effects)

            state.modifiers[char_id] = [m for m in state.modifiers[char_id] if m.get("id") != modifier_id]
