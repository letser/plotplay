"""Clothing helpers for the new runtime."""

from __future__ import annotations

from app.models.effects import (
    ClothingPutOnEffect,
    ClothingTakeOffEffect,
    ClothingStateEffect,
    ClothingSlotStateEffect,
    OutfitPutOnEffect,
    OutfitTakeOffEffect,
)
from app.runtime.session import SessionRuntime


class ClothingService:
    """Applies clothing and outfit effects to character state."""

    def __init__(self, runtime: SessionRuntime) -> None:
        self.runtime = runtime
        self.logger = runtime.logger
        self.inventory = runtime.inventory_service

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def apply_effect(self, effect: ClothingPutOnEffect | ClothingTakeOffEffect | ClothingStateEffect | ClothingSlotStateEffect) -> None:
        """Handle single clothing effect."""
        if isinstance(effect, ClothingPutOnEffect):
            self._put_on(effect.target, effect.item, effect.condition)
        elif isinstance(effect, ClothingTakeOffEffect):
            self._take_off(effect.target, effect.item)
        elif isinstance(effect, ClothingStateEffect):
            self._set_item_state(effect.target, effect.item, effect.condition)
        elif isinstance(effect, ClothingSlotStateEffect):
            self._set_slot_state(effect.target, effect.slot, effect.condition)

    def apply_outfit_effect(self, effect: OutfitPutOnEffect | OutfitTakeOffEffect) -> None:
        if isinstance(effect, OutfitPutOnEffect):
            self._put_on_outfit(effect.target, effect.item)
        elif isinstance(effect, OutfitTakeOffEffect):
            self._take_off_outfit(effect.target, effect.item)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _put_on(self, char_id: str, clothing_id: str, condition) -> None:
        state = self.runtime.state_manager.state
        char_state = state.characters.get(char_id)
        if not char_state:
            return

        clothing_def = self.inventory and self.inventory.clothing_defs.get(clothing_id)
        if not clothing_def:
            return

        # Validate ownership - clothing items must be owned before wearing
        if char_state.inventory.clothing.get(clothing_id, 0) <= 0:
            raise ValueError(f"Cannot put on '{clothing_id}': not in inventory")

        char_state.clothing.items[clothing_id] = condition or clothing_def.condition
        slot_state = state.clothing_states.setdefault(char_id, {"slot_to_item": {}, "slot_state": {}})
        for slot in clothing_def.occupies:
            slot_state["slot_to_item"][slot] = clothing_id
            slot_state["slot_state"][slot] = (condition or clothing_def.condition).value if hasattr(condition, "value") else (condition or clothing_def.condition)

        if clothing_def.on_put_on:
            self.runtime.effect_resolver.apply_effects(clothing_def.on_put_on)

    def _take_off(self, char_id: str, clothing_id: str) -> None:
        state = self.runtime.state_manager.state
        char_state = state.characters.get(char_id)
        if not char_state:
            return

        clothing_def = self.inventory and self.inventory.clothing_defs.get(clothing_id)
        if not clothing_def:
            return

        if clothing_id in char_state.clothing.items:
            char_state.clothing.items[clothing_id] = "removed"

        slot_state = state.clothing_states.get(char_id, {})
        slot_to_item = slot_state.get("slot_to_item", {})
        slot_map = slot_state.get("slot_state", {})
        for slot, item in list(slot_to_item.items()):
            if item == clothing_id:
                slot_to_item.pop(slot, None)
                slot_map.pop(slot, None)

        if clothing_def.on_take_off:
            self.runtime.effect_resolver.apply_effects(clothing_def.on_take_off)

    def _set_item_state(self, char_id: str, clothing_id: str, condition) -> None:
        state = self.runtime.state_manager.state
        char_state = state.characters.get(char_id)
        if not char_state:
            return
        if clothing_id not in char_state.clothing.items:
            return
        char_state.clothing.items[clothing_id] = condition
        clothing_def = self.inventory and self.inventory.clothing_defs.get(clothing_id)
        if clothing_def:
            slot_state = state.clothing_states.setdefault(char_id, {"slot_to_item": {}, "slot_state": {}})
            for slot in clothing_def.occupies:
                if slot_state["slot_to_item"].get(slot) == clothing_id:
                    slot_state["slot_state"][slot] = condition.value if hasattr(condition, "value") else condition

    def _set_slot_state(self, char_id: str, slot: str, condition) -> None:
        state = self.runtime.state_manager.state
        slot_state = state.clothing_states.setdefault(char_id, {"slot_to_item": {}, "slot_state": {}})
        slot_state["slot_state"][slot] = condition.value if hasattr(condition, "value") else condition

    def _put_on_outfit(self, char_id: str, outfit_id: str) -> None:
        state = self.runtime.state_manager.state
        char_state = state.characters.get(char_id)
        if not char_state:
            return

        outfit_def = self.inventory and self.inventory.outfit_defs.get(outfit_id)
        if not outfit_def:
            return

        # Validate all outfit items are owned - outfit cannot be worn if incomplete
        missing_items = []
        for clothing_id in outfit_def.items.keys():
            if char_state.inventory.clothing.get(clothing_id, 0) <= 0:
                missing_items.append(clothing_id)

        if missing_items:
            raise ValueError(
                f"Cannot wear outfit '{outfit_id}': missing required clothing items {missing_items}. "
                f"Outfit is incomplete and cannot be worn until all items are acquired."
            )

        char_state.clothing.outfit = outfit_id
        char_state.clothing.items.update({item_id: state_val for item_id, state_val in outfit_def.items.items()})

        slot_state = state.clothing_states.setdefault(char_id, {"slot_to_item": {}, "slot_state": {}})
        for clothing_id, cond in outfit_def.items.items():
            clothing_def = self.inventory and self.inventory.clothing_defs.get(clothing_id)
            if not clothing_def:
                continue
            for slot in clothing_def.occupies:
                slot_state["slot_to_item"][slot] = clothing_id
                slot_state["slot_state"][slot] = cond.value if hasattr(cond, "value") else cond

        if outfit_def.on_put_on:
            self.runtime.effect_resolver.apply_effects(outfit_def.on_put_on)

    def _take_off_outfit(self, char_id: str, outfit_id: str) -> None:
        state = self.runtime.state_manager.state
        char_state = state.characters.get(char_id)
        if not char_state or char_state.clothing.outfit != outfit_id:
            return

        outfit_def = self.inventory and self.inventory.outfit_defs.get(outfit_id)
        char_state.clothing.outfit = None

        if outfit_def:
            if outfit_def.on_take_off:
                self.runtime.effect_resolver.apply_effects(outfit_def.on_take_off)
            for clothing_id in outfit_def.items.keys():
                if clothing_id in char_state.clothing.items:
                    char_state.clothing.items[clothing_id] = "removed"

        slot_state = state.clothing_states.get(char_id)
        if slot_state:
            slot_state["slot_to_item"].clear()
            slot_state["slot_state"].clear()
