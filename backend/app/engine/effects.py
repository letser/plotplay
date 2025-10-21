"""Effect resolution helpers for the PlotPlay engine."""

from __future__ import annotations

import random
from typing import Iterable, TYPE_CHECKING

from app.core.conditions import ConditionEvaluator
from app.models.effects import (
    AnyEffect,
    AdvanceTimeEffect,
    ApplyModifierEffect,
    ClothingChangeEffect,
    ConditionalEffect,
    FlagSetEffect,
    GotoEffect,
    InventoryAddEffect,
    InventoryRemoveEffect,
    InventoryChangeEffect,
    MeterChangeEffect,
    MoveToEffect,
    RandomEffect,
    RemoveModifierEffect,
    UnlockEffect,
)

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine


class EffectResolver:
    """Encapsulates effect application logic."""

    def __init__(self, engine: "GameEngine") -> None:
        self.engine = engine

    def apply_effects(self, effects: Iterable[AnyEffect]) -> None:
        state = self.engine.state_manager.state
        evaluator = ConditionEvaluator(state, rng_seed=self.engine._get_turn_seed())

        for effect in effects:
            if isinstance(effect, ConditionalEffect):
                self._apply_conditional_effect(effect)
                continue

            if not evaluator.evaluate(effect.when):
                continue

            match effect:
                case RandomEffect():
                    self._apply_random_effect(effect)
                case MeterChangeEffect():
                    self.apply_meter_change(effect)
                case FlagSetEffect():
                    self.apply_flag_set(effect)
                case GotoEffect():
                    self.apply_goto_node(effect)
                case MoveToEffect():
                    self._apply_move_to(effect)
                case InventoryAddEffect() | InventoryRemoveEffect():
                    # Convert new effect types to legacy InventoryChangeEffect
                    legacy_effect = InventoryChangeEffect(
                        type="inventory_add" if isinstance(effect, InventoryAddEffect) else "inventory_remove",
                        owner=effect.target,
                        item=effect.item,
                        count=effect.count
                    )
                    self.engine.inventory.apply_effect(legacy_effect)
                case InventoryChangeEffect():
                    self.engine.inventory.apply_effect(effect)
                case ClothingChangeEffect():
                    self.engine.clothing.apply_effect(effect)
                case ApplyModifierEffect() | RemoveModifierEffect():
                    self.engine.modifiers.apply_effect(effect, state)
                case UnlockEffect():
                    self._apply_unlock(effect)
                case AdvanceTimeEffect():
                    self.apply_advance_time(effect)

    def apply_meter_change(self, effect: MeterChangeEffect) -> None:
        target_meters = self.engine.state_manager.state.meters.get(effect.target)
        if target_meters is None:
            return

        meter_def = self.engine._get_meter_def(effect.target, effect.meter)
        if meter_def is None:
            return

        value_to_apply = effect.value
        op_to_apply = effect.op

        if meter_def.delta_cap_per_turn is not None:
            cap = meter_def.delta_cap_per_turn
            self.engine.turn_meter_deltas.setdefault(effect.target, {}).setdefault(effect.meter, 0)
            current_turn_delta = self.engine.turn_meter_deltas[effect.target][effect.meter]
            remaining_cap = cap - abs(current_turn_delta)

            if remaining_cap <= 0:
                self.engine.logger.warning(
                    "Meter change for '%s.%s' blocked by delta cap.",
                    effect.target,
                    effect.meter,
                )
                return

            if op_to_apply in {"add", "subtract"}:
                change_sign = 1 if op_to_apply == "add" else -1
                actual_change = max(-remaining_cap, min(remaining_cap, value_to_apply * change_sign))

                value_to_apply = abs(actual_change)
                op_to_apply = "add" if actual_change > 0 else "subtract"

                self.engine.turn_meter_deltas[effect.target][effect.meter] += actual_change

        current_value = target_meters.get(effect.meter, 0)
        op_map = {
            "add": lambda a, b: a + b,
            "subtract": lambda a, b: a - b,
            "multiply": lambda a, b: a * b,
            "divide": lambda a, b: a / b if b != 0 else a,
            "set": lambda a, b: b,
        }

        operation = op_map.get(op_to_apply)
        if not operation:
            return

        new_value = operation(current_value, value_to_apply)

        effective_min = meter_def.min
        effective_max = meter_def.max

        active_modifiers = self.engine.state_manager.state.modifiers.get(effect.target, [])
        for mod_state in active_modifiers:
            mod_def = self.engine.modifiers.library.get(mod_state["id"])
            if mod_def and mod_def.clamp_meters:
                if meter_clamp := mod_def.clamp_meters.get(effect.meter):
                    if "min" in meter_clamp:
                        effective_min = max(effective_min, meter_clamp["min"])
                    if "max" in meter_clamp:
                        effective_max = min(effective_max, meter_clamp["max"])

        new_value = max(effective_min, min(new_value, effective_max))
        target_meters[effect.meter] = new_value

    def apply_flag_set(self, effect: FlagSetEffect) -> None:
        if effect.key in self.engine.state_manager.state.flags:
            self.engine.state_manager.state.flags[effect.key] = effect.value

    def apply_goto_node(self, effect: GotoNodeEffect) -> None:
        if effect.node in self.engine.nodes_map:
            self.engine.state_manager.state.current_node = effect.node

    def apply_advance_time(self, effect: AdvanceTimeEffect) -> None:
        self.engine.logger.info("Applying AdvanceTimeEffect: %s minutes.", effect.minutes)
        self.engine._advance_time(minutes=effect.minutes)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _apply_conditional_effect(self, effect: ConditionalEffect) -> None:
        evaluator = ConditionEvaluator(self.engine.state_manager.state, rng_seed=self.engine._get_turn_seed())
        if evaluator.evaluate(effect.when):
            self.apply_effects(effect.then)
        else:
            self.apply_effects(effect.otherwise)

    def _apply_random_effect(self, effect: RandomEffect) -> None:
        total_weight = sum(choice.weight for choice in effect.choices)
        if total_weight <= 0:
            return

        roll = random.Random(self.engine._get_turn_seed()).uniform(0, total_weight)
        current_weight = 0

        for choice in effect.choices:
            current_weight += choice.weight
            if roll <= current_weight:
                self.apply_effects(choice.effects)
                return

    def _apply_unlock(self, effect: UnlockEffect) -> None:
        if effect.type == "unlock_outfit":
            self._apply_unlock_outfit(effect)
        elif effect.type == "unlock_ending":
            self._apply_unlock_ending(effect)
        elif effect.type == "unlock_actions":
            self._apply_unlock_actions(effect)
        elif effect.type == "unlock" and effect.actions:
            # fall back to global unlock for authored lists
            self._apply_unlock_actions(effect)

    def _apply_move_to(self, effect: MoveToEffect) -> None:
        state = self.engine.state_manager.state

        if effect.location not in state.discovered_locations:
            return

        chars_to_move = [char for char in effect.with_characters if char in state.present_chars]

        state.location_current = effect.location
        state.location_privacy = self.engine._get_location_privacy(effect.location)

        self.engine._update_npc_presence()

        current_node = self.engine._get_current_node()
        current_node.characters_present.extend(chars_to_move)

        if current_node.characters_present:
            state.present_chars = [
                char for char in current_node.characters_present if char in self.engine.characters_map
            ]
