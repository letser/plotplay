"""
Placeholder movement/inventory interaction service.
"""

from __future__ import annotations

from typing import List, Iterable

from app.models.effects import (
    MoveToEffect,
    MoveEffect,
    TravelToEffect,
    InventoryTakeEffect,
    InventoryDropEffect,
    InventoryPurchaseEffect,
    InventorySellEffect,
    InventoryGiveEffect,
    LockEffect,
    UnlockEffect,
)
from app.runtime.session import SessionRuntime


class MovementService:
    """Handles movement and location inventory helpers. Currently stubbed."""

    def __init__(self, runtime: SessionRuntime) -> None:
        self.runtime = runtime

    def move_to(self, effect: MoveToEffect) -> None:
        state = self.runtime.state_manager.state
        state.current_location = effect.location

    def move_relative(self, effect: MoveEffect) -> None:
        self.runtime.logger.debug("Relative movement not implemented yet: %s", effect.direction)

    def travel(self, effect: TravelToEffect) -> None:
        state = self.runtime.state_manager.state
        state.current_location = effect.location

    def take_from_location(self, effect: InventoryTakeEffect) -> List:
        state = self.runtime.state_manager.state
        location_state = state.locations.get(state.current_location)
        if not location_state:
            return []
        bucket = location_state.inventory.items
        if bucket.get(effect.item, 0) <= 0:
            return []
        bucket[effect.item] -= effect.count
        if bucket[effect.item] <= 0:
            bucket.pop(effect.item, None)
        return [
            {
                "type": "inventory_add",
                "target": effect.target,
                "item_type": effect.item_type,
                "item": effect.item,
                "count": effect.count,
            }
        ]

    def drop_to_location(self, effect: InventoryDropEffect) -> List:
        state = self.runtime.state_manager.state
        location_state = state.locations.get(state.current_location)
        if not location_state:
            return []
        bucket = location_state.inventory.items
        bucket[effect.item] = bucket.get(effect.item, 0) + effect.count
        return [
            {
                "type": "inventory_remove",
                "target": effect.target,
                "item_type": effect.item_type,
                "item": effect.item,
                "count": effect.count,
            }
        ]

    def purchase(self, effect: InventoryPurchaseEffect) -> List:
        self.runtime.logger.debug("TODO: implement purchase logic")
        return []

    def sell(self, effect: InventorySellEffect) -> List:
        self.runtime.logger.debug("TODO: implement sell logic")
        return []

    def give(self, effect: InventoryGiveEffect) -> List:
        return [
            {
                "type": "inventory_remove",
                "target": effect.source,
                "item_type": effect.item_type,
                "item": effect.item,
                "count": effect.count,
            },
            {
                "type": "inventory_add",
                "target": effect.target,
                "item_type": effect.item_type,
                "item": effect.item,
                "count": effect.count,
            },
        ]

    def apply_lock(self, effect: LockEffect) -> None:
        self.runtime.logger.debug("TODO: implement lock effect")

    def apply_unlock(self, effect: UnlockEffect) -> None:
        self.runtime.logger.debug("TODO: implement unlock effect")
