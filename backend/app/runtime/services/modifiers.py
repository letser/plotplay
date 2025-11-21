"""Modifier management for the new runtime."""

from __future__ import annotations

from typing import Any

from app.models.effects import ApplyModifierEffect, RemoveModifierEffect
from app.models.modifiers import ModifierStacking
from app.runtime.session import SessionRuntime


class ModifierService:
    """
    Manages activation, duration, and entry/exit effects for modifiers.
    Mirrors the spec behavior with deterministic evaluation.
    """

    def __init__(self, runtime: SessionRuntime) -> None:
        self.runtime = runtime
        modifiers_cfg = getattr(runtime.game, "modifiers", None)
        self.library = {mod.id: mod for mod in modifiers_cfg.library} if modifiers_cfg and modifiers_cfg.library else {}
        self.stacking = modifiers_cfg.stacking if modifiers_cfg and modifiers_cfg.stacking else {}

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def apply_effect(self, effect: ApplyModifierEffect | RemoveModifierEffect, *, state: Any | None = None) -> None:
        """Apply a modifier-related effect to the state."""
        target_state = state or self.runtime.state_manager.state
        if isinstance(effect, ApplyModifierEffect):
            self._apply_modifier(effect.target, effect.modifier_id, target_state, duration_override=effect.duration)
        elif isinstance(effect, RemoveModifierEffect):
            self._remove_modifier(effect.target, effect.modifier_id, target_state)

    def update_modifiers_for_turn(self, state) -> None:
        """Auto-activate/deactivate modifiers based on their conditions."""
        evaluator = self.runtime.state_manager.create_evaluator()
        character_ids = list(state.characters.keys())

        for char_id in character_ids:
            active_mods = state.modifiers.setdefault(char_id, [])
            active_ids = {m["id"] for m in active_mods}

            for modifier_id, modifier_def in self.library.items():
                conditioned_def = modifier_def
                condition = modifier_def.when
                when_all = modifier_def.when_all
                when_any = modifier_def.when_any
                if condition and "{character}" in condition:
                    condition = condition.replace("{character}", char_id)
                # when_all/when_any may not contain placeholder; reuse evaluator helper
                conditioned_def = type("CondProxy", (), {"when": condition, "when_all": when_all, "when_any": when_any})

                is_active_now = evaluator.evaluate_object_conditions(conditioned_def)
                if is_active_now and modifier_id not in active_ids:
                    self._apply_modifier(char_id, modifier_id, state)
                    active_ids.add(modifier_id)
                elif not is_active_now and modifier_id in active_ids:
                    self._remove_modifier(char_id, modifier_id, state)
                    active_ids.discard(modifier_id)

            # Keep CharacterState modifiers in sync
            char_state = state.characters.get(char_id)
            if char_state:
                char_state.modifiers = {mod.get("id"): mod.get("duration") for mod in state.modifiers.get(char_id, []) if mod.get("id")}

    def tick_durations(self, state, minutes: int) -> None:
        """Reduce modifier durations and trigger exits for expired ones."""
        if minutes <= 0:
            return

        for char_id, active_mods in list(state.modifiers.items()):
            expired: list[str] = []
            for mod in active_mods:
                if mod.get("duration") is None:
                    continue
                mod["duration"] -= minutes
                if mod["duration"] <= 0:
                    expired.append(mod["id"])
            for mod_id in expired:
                self._remove_modifier(char_id, mod_id, state)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _apply_modifier(self, char_id: str, modifier_id: str, state, *, duration_override: int | None = None) -> None:
        """Activate a modifier, honoring stacking rules and entry effects."""
        modifier_def = self.library.get(modifier_id)
        if not modifier_def:
            return

        active_mods = state.modifiers.setdefault(char_id, [])
        if any(mod.get("id") == modifier_id for mod in active_mods):
            return

        if modifier_def.group:
            stacking_rule = self.stacking.get(modifier_def.group)
            group_active = [
                mod for mod in active_mods
                if self.library.get(mod.get("id")) and self.library[mod["id"]].group == modifier_def.group
            ]
            if stacking_rule in (ModifierStacking.HIGHEST, "highest"):
                best = modifier_def
                for mod in group_active:
                    other = self.library.get(mod.get("id"))
                    if other and (best.priority or 0) < (other.priority or 0):
                        best = other
                if best.id != modifier_id:
                    return  # existing higher priority stays
                for mod in group_active:
                    self._remove_modifier(char_id, mod["id"], state)
            elif stacking_rule in (ModifierStacking.LOWEST, "lowest"):
                best = modifier_def
                for mod in group_active:
                    other = self.library.get(mod.get("id"))
                    if other and (best.priority or 0) > (other.priority or 0):
                        best = other
                if best.id != modifier_id:
                    return
                for mod in group_active:
                    self._remove_modifier(char_id, mod["id"], state)

        duration = duration_override if duration_override is not None else modifier_def.duration
        active_mods.append({"id": modifier_id, "duration": duration})

        if modifier_def.on_enter:
            self.runtime.effect_resolver.apply_effects(modifier_def.on_enter)

        # Keep CharacterState modifiers keys in sync for DSL context
        char_state = state.characters.get(char_id)
        if char_state:
            char_state.modifiers = {mod.get("id"): mod.get("duration") for mod in active_mods if mod.get("id")}

    def _remove_modifier(self, char_id: str, modifier_id: str, state) -> None:
        """Deactivate a modifier and run exit effects."""
        active_mods = state.modifiers.setdefault(char_id, [])
        modifier_def = self.library.get(modifier_id)
        if modifier_def and modifier_def.on_exit:
            self.runtime.effect_resolver.apply_effects(modifier_def.on_exit)

        state.modifiers[char_id] = [mod for mod in active_mods if mod.get("id") != modifier_id]

        # Keep CharacterState modifiers keys in sync for DSL context
        char_state = state.characters.get(char_id)
        if char_state:
            char_state.modifiers = {mod.get("id"): mod.get("duration") for mod in state.modifiers.get(char_id, []) if mod.get("id")}
