"""Modifier management for the new runtime."""

from __future__ import annotations

from typing import Any
from types import SimpleNamespace

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
            self._apply_modifier(
                effect.target,
                effect.modifier_id,
                target_state,
                duration_override=effect.duration,
                source="manual",
            )
        elif isinstance(effect, RemoveModifierEffect):
            self._remove_modifier(effect.target, effect.modifier_id, target_state)

    def update_modifiers_for_turn(self, state) -> None:
        """Auto-activate/deactivate modifiers based on their conditions."""
        evaluator = self.runtime.state_manager.create_evaluator()
        character_ids = list(state.characters.keys())

        for char_id in character_ids:
            active_mods = state.modifiers.setdefault(char_id, [])
            active_map = {m["id"]: m for m in active_mods if m.get("id")}

            for modifier_id, modifier_def in self.library.items():
                if not self._has_conditions(modifier_def):
                    continue

                conditioned_def = self._conditioned_definition(modifier_def, char_id)
                is_active_now = evaluator.evaluate_object_conditions(conditioned_def)
                active_entry = active_map.get(modifier_id)
                source = active_entry.get("source") if active_entry else None

                if is_active_now and not active_entry:
                    self._apply_modifier(char_id, modifier_id, state, source="auto")
                elif not is_active_now and active_entry and source == "auto":
                    self._remove_modifier(char_id, modifier_id, state)

            # Keep CharacterState modifiers in sync
            self._sync_character_modifiers(state, char_id)

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
            self._sync_character_modifiers(state, char_id)
            for mod_id in expired:
                self._remove_modifier(char_id, mod_id, state)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _apply_modifier(
        self,
        char_id: str,
        modifier_id: str,
        state,
        *,
        duration_override: int | None = None,
        source: str = "auto",
    ) -> None:
        """Activate a modifier, honoring stacking rules and entry effects."""
        modifier_def = self.library.get(modifier_id)
        if not modifier_def:
            return

        active_mods = state.modifiers.setdefault(char_id, [])
        existing = next((mod for mod in active_mods if mod.get("id") == modifier_id), None)
        if existing:
            if duration_override is not None:
                existing["duration"] = duration_override
                self._sync_character_modifiers(state, char_id)
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
                active_mods = state.modifiers.setdefault(char_id, [])
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
        active_mods.append({"id": modifier_id, "duration": duration, "source": source})

        if modifier_def.on_enter:
            self.runtime.effect_resolver.apply_effects(modifier_def.on_enter)

        # Keep CharacterState modifiers keys in sync for DSL context
        self._sync_character_modifiers(state, char_id)

    def _remove_modifier(self, char_id: str, modifier_id: str, state) -> None:
        """Deactivate a modifier and run exit effects."""
        active_mods = state.modifiers.setdefault(char_id, [])
        existing = next((mod for mod in active_mods if mod.get("id") == modifier_id), None)
        if not existing:
            return

        modifier_def = self.library.get(modifier_id)
        if modifier_def and modifier_def.on_exit:
            self.runtime.effect_resolver.apply_effects(modifier_def.on_exit)

        remaining = [mod for mod in active_mods if mod.get("id") != modifier_id]
        active_mods[:] = remaining
        state.modifiers[char_id] = active_mods

        # Keep CharacterState modifiers keys in sync for DSL context
        self._sync_character_modifiers(state, char_id)

    @staticmethod
    def _has_conditions(modifier_def) -> bool:
        """Auto-activation only applies when a modifier declares conditions."""
        return bool(
            (modifier_def.when and modifier_def.when.strip())
            or (modifier_def.when_all and any(modifier_def.when_all))
            or (modifier_def.when_any and any(modifier_def.when_any))
        )

    @staticmethod
    def _substitute_character(expr: str | None, char_id: str) -> str | None:
        if not expr or "{character}" not in expr:
            return expr
        return expr.replace("{character}", char_id)

    def _conditioned_definition(self, modifier_def, char_id: str) -> SimpleNamespace:
        when = self._substitute_character(modifier_def.when, char_id)
        when_all = [self._substitute_character(expr, char_id) for expr in (modifier_def.when_all or []) if expr]
        when_any = [self._substitute_character(expr, char_id) for expr in (modifier_def.when_any or []) if expr]
        return SimpleNamespace(
            when=when,
            when_all=when_all or None,
            when_any=when_any or None,
        )

    def _sync_character_modifiers(self, state, char_id: str) -> None:
        """Update CharacterState.modifiers mapping for DSL context."""
        char_state = state.characters.get(char_id)
        if not char_state:
            return
        active = state.modifiers.get(char_id, [])
        char_state.modifiers = {mod.get("id"): mod.get("duration") for mod in active if mod.get("id")}
