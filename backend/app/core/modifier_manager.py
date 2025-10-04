from __future__ import annotations
from typing import TYPE_CHECKING
from app.models.game import GameDefinition
from app.core.state_manager import GameState
from app.core.conditions import ConditionEvaluator
from app.models.effects import ApplyModifierEffect, RemoveModifierEffect

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine


class ModifierManager:
    """
    Manages the activation, duration, and effects of character modifiers.
    """

    def __init__(self, game_def: GameDefinition, engine: GameEngine):
        self.game_def = game_def
        self.engine = engine  # Keep a reference to the engine to apply effects
        if not self.game_def.modifier_system:
            self.library = {}
            self.exclusions = []
        else:
            self.library = self.game_def.modifier_system.library
            self.exclusions = self.game_def.modifier_system.exclusions or []

    def update_modifiers_for_turn(self, state: GameState):
        """
        Checks all defined modifiers for auto-activation based on their 'when' conditions.
        This should be called once per turn.
        """
        all_character_ids = list(state.meters.keys())

        for char_id in all_character_ids:
            evaluator = ConditionEvaluator(state, state.present_chars)

            if char_id not in state.modifiers:
                state.modifiers[char_id] = []

            active_modifier_ids = {m['id'] for m in state.modifiers[char_id]}

            for modifier_id, modifier_def in self.library.items():
                if modifier_def.when:
                    expression = modifier_def.when.replace("{character}", char_id)

                    if evaluator.evaluate(expression):
                        if modifier_id not in active_modifier_ids:
                            self._apply_modifier(char_id, modifier_id, state)
                    else:
                        if modifier_id in active_modifier_ids:
                            self._remove_modifier(char_id, modifier_id, state)

    def tick_durations(self, state: GameState, minutes_passed: int):
        """Ticks down the duration of active modifiers."""
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

    def apply_effect(self, effect: ApplyModifierEffect | RemoveModifierEffect, state: GameState):
        """Applies a single modifier-related effect to the state."""
        if isinstance(effect, ApplyModifierEffect):
            self._apply_modifier(effect.character, effect.modifier_id, state, duration_override=effect.duration_min)
        elif isinstance(effect, RemoveModifierEffect):
            self._remove_modifier(effect.character, effect.modifier_id, state)

    def _apply_modifier(self, char_id: str, modifier_id: str, state: GameState, duration_override: int | None = None):
        """Helper to add a modifier to a character's active list."""
        if char_id not in state.modifiers:
            state.modifiers[char_id] = []

        modifier_def = self.library.get(modifier_id)
        if not modifier_def:
            return

        active_mods = state.modifiers[char_id]
        active_ids = {m['id'] for m in active_mods}
        if modifier_id in active_ids:
            return  # Already active

        # --- NEW: Exclusion Logic ---
        if modifier_def.group:
            for exclusion_rule in self.exclusions:
                if exclusion_rule.group == modifier_def.group and exclusion_rule.exclusive:
                    # Find and remove any other modifier from the same exclusive group
                    mods_to_remove = [
                        m['id'] for m in active_mods
                        if self.library.get(m['id']) and self.library[m['id']].group == modifier_def.group
                    ]
                    for mod_to_remove_id in mods_to_remove:
                        self._remove_modifier(char_id, mod_to_remove_id, state)

        # --- Add Modifier with Duration ---
        duration = duration_override if duration_override is not None else modifier_def.duration_default_min
        state.modifiers[char_id].append({"id": modifier_id, "duration": duration})

        # --- NEW: Trigger Entry Effects ---
        if modifier_def.entry_effects:
            self.engine._apply_effects(modifier_def.entry_effects)

    def _remove_modifier(self, char_id: str, modifier_id: str, state: GameState):
        """Helper to remove a modifier from a character's active list."""
        if char_id in state.modifiers:
            modifier_def = self.library.get(modifier_id)

            # --- NEW: Trigger Exit Effects ---
            if modifier_def and modifier_def.exit_effects:
                self.engine._apply_effects(modifier_def.exit_effects)

            state.modifiers[char_id] = [m for m in state.modifiers[char_id] if m.get('id') != modifier_id]