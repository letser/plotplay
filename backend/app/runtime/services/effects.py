"""
Minimal effect resolver for the new runtime engine.

This is a trimmed version of the legacy resolver so we can keep iterating on
the turn pipeline without pulling every legacy detail at once.
"""

from __future__ import annotations

import random
from typing import Iterable

from app.core.conditions import ConditionEvaluator
from app.models.effects import (
    AnyEffect,
    ConditionalEffect,
    RandomEffect,
    MeterChangeEffect,
    FlagSetEffect,
    GotoEffect,
    InventoryAddEffect,
    InventoryRemoveEffect,
    InventoryTakeEffect,
    InventoryDropEffect,
    InventoryPurchaseEffect,
    InventorySellEffect,
    InventoryGiveEffect,
    AdvanceTimeEffect,
    MoveEffect,
    MoveToEffect,
    TravelToEffect,
    ApplyModifierEffect,
    RemoveModifierEffect,
    LockEffect,
    UnlockEffect,
    ClothingPutOnEffect,
    ClothingTakeOffEffect,
    ClothingStateEffect,
    ClothingSlotStateEffect,
    OutfitPutOnEffect,
    OutfitTakeOffEffect,
)
from app.runtime.session import SessionRuntime
from app.runtime.services.inventory import InventoryService


class EffectResolver:
    """Applies a limited subset of effects to the current state."""

    def __init__(self, runtime: SessionRuntime, inventory: InventoryService, trade=None, **_unused) -> None:
        self.runtime = runtime
        self.inventory = inventory
        self.trade = trade

    def apply_effects(self, effects: Iterable[AnyEffect]) -> None:
        from app.models.effects import parse_effect

        evaluator = self._evaluator()
        for effect in effects:
            if isinstance(effect, dict):
                effect = parse_effect(effect)

            if isinstance(effect, ConditionalEffect):
                self._apply_conditional(effect)
                continue

            if not evaluator.evaluate(effect.when):
                continue

            if isinstance(effect, RandomEffect):
                self._apply_random(effect)
            elif isinstance(effect, MeterChangeEffect):
                self._apply_meter_change(effect)
            elif isinstance(effect, FlagSetEffect):
                self._apply_flag(effect)
            elif isinstance(effect, GotoEffect):
                self._apply_goto(effect)
            elif isinstance(effect, InventoryAddEffect) or isinstance(effect, InventoryRemoveEffect):
                hooks = self.inventory.apply_effect(effect)
                if hooks:
                    self.apply_effects(hooks)
            elif isinstance(effect, InventoryTakeEffect):
                trade = self.trade or getattr(self.runtime, "trade_service", None)
                hooks = trade.take_from_location(effect) if trade else None
                if hooks:
                    self.apply_effects(hooks)
            elif isinstance(effect, InventoryDropEffect):
                trade = self.trade or getattr(self.runtime, "trade_service", None)
                hooks = trade.drop_to_location(effect) if trade else None
                if hooks:
                    self.apply_effects(hooks)
            elif isinstance(effect, InventoryPurchaseEffect):
                trade = self.trade or getattr(self.runtime, "trade_service", None)
                hooks = trade.purchase(effect) if trade else None
                if hooks:
                    self.apply_effects(hooks)
            elif isinstance(effect, InventorySellEffect):
                trade = self.trade or getattr(self.runtime, "trade_service", None)
                hooks = trade.sell(effect) if trade else None
                if hooks:
                    self.apply_effects(hooks)
            elif isinstance(effect, InventoryGiveEffect):
                trade = self.trade or getattr(self.runtime, "trade_service", None)
                hooks = trade.give(effect) if trade else None
                if hooks:
                    self.apply_effects(hooks)
            elif isinstance(effect, MoveToEffect):
                mover = getattr(self.runtime, "movement_service", None)
                if mover:
                    mover.move_to(effect)
            elif isinstance(effect, MoveEffect):
                mover = getattr(self.runtime, "movement_service", None)
                if mover:
                    mover.move_relative(effect)
            elif isinstance(effect, TravelToEffect):
                mover = getattr(self.runtime, "movement_service", None)
                if mover:
                    mover.travel(effect)
            elif isinstance(effect, AdvanceTimeEffect):
                time_service = getattr(self.runtime, "time_service", None)
                if time_service:
                    info = time_service.advance_minutes(effect.minutes)
                    ctx = getattr(self.runtime, "current_context", None)
                    if ctx:
                        ctx.time_advanced_minutes += info.get("minutes", 0)
                        ctx.day_advanced = ctx.day_advanced or info.get("day_advanced", False)
                        ctx.slot_advanced = ctx.slot_advanced or info.get("slot_advanced", False)
            elif isinstance(effect, ApplyModifierEffect) or isinstance(effect, RemoveModifierEffect):
                modifiers = getattr(self.runtime, "modifier_service", None)
                if modifiers:
                    modifiers.apply_effect(effect, state=self.runtime.state_manager.state)
            elif isinstance(effect, LockEffect):
                mover = getattr(self.runtime, "movement_service", None)
                if mover:
                    mover.apply_lock(effect)
            elif isinstance(effect, UnlockEffect):
                mover = getattr(self.runtime, "movement_service", None)
                if mover:
                    mover.apply_unlock(effect)
            elif isinstance(effect, ClothingPutOnEffect) or isinstance(effect, ClothingTakeOffEffect) or isinstance(effect, ClothingStateEffect) or isinstance(effect, ClothingSlotStateEffect):
                clothing = getattr(self.runtime, "clothing_service", None)
                if clothing:
                    clothing.apply_effect(effect)
            elif isinstance(effect, OutfitPutOnEffect) or isinstance(effect, OutfitTakeOffEffect):
                clothing = getattr(self.runtime, "clothing_service", None)
                if clothing:
                    clothing.apply_outfit_effect(effect)
            else:
                self.runtime.logger.debug("Ignoring unsupported effect type: %s", getattr(effect, "type", type(effect)))

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _evaluator(self) -> ConditionEvaluator:
        return self.runtime.state_manager.create_evaluator()

    def _apply_conditional(self, effect: ConditionalEffect) -> None:
        if self._evaluator().evaluate(effect.when):
            self.apply_effects(effect.then or [])
        else:
            self.apply_effects(effect.otherwise or [])

    def _apply_random(self, effect: RandomEffect) -> None:
        total = sum(choice.weight for choice in effect.choices)
        if total <= 0:
            return
        rng = random.Random(self.runtime.turn_seed())
        roll = rng.uniform(0, total)
        current = 0
        for choice in effect.choices:
            current += choice.weight
            if roll <= current:
                self.apply_effects(choice.effects)
                return

    def _apply_meter_change(self, effect: MeterChangeEffect) -> None:
        state = self.runtime.state_manager.state
        target = state.meters.get(effect.target)
        if target is None:
            return

        meter_def = (
            self.runtime.index.player_meters.get(effect.meter)
            if effect.target == "player"
            else self.runtime.index.template_meters.get(effect.meter)
        )
        if not meter_def:
            return

        current = target.get(effect.meter, 0)
        op_map = {
            "add": lambda a, b: a + b,
            "subtract": lambda a, b: a - b,
            "multiply": lambda a, b: a * b,
            "divide": lambda a, b: a / b if b != 0 else a,
            "set": lambda a, b: b,
        }
        op = op_map.get(effect.op)
        if not op:
            return
        new_value = op(current, effect.value)
        new_value = max(meter_def.min, min(meter_def.max, new_value))
        target[effect.meter] = new_value

    def _apply_flag(self, effect: FlagSetEffect) -> None:
        if effect.key in self.runtime.state_manager.state.flags:
            self.runtime.state_manager.state.flags[effect.key] = effect.value

    def _apply_goto(self, effect: GotoEffect) -> None:
        if effect.node in self.runtime.index.nodes:
            self.runtime.state_manager.state.current_node = effect.node
