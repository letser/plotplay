"""
Inventory management service for the new runtime engine.
"""

from __future__ import annotations

from typing import Any, Iterable, List

from app.models.effects import (
    InventoryAddEffect,
    InventoryRemoveEffect,
    InventoryTakeEffect,
    InventoryDropEffect,
    InventoryChangeEffect,
    AnyEffect,
)
from app.runtime.session import SessionRuntime


class InventoryService:
    """
    Manages character inventories and item definitions.
    Ported from the legacy engine with minimal changes to integrate with
    SessionRuntime instead of the old GameEngine object.
    """

    def __init__(self, runtime: SessionRuntime) -> None:
        self.runtime = runtime
        index = runtime.index

        self.item_defs = dict(index.items)
        self.clothing_defs = dict(index.clothing)
        self.outfit_defs = dict(index.outfits)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def use_item(self, owner_id: str, item_id: str) -> List[AnyEffect]:
        state = self.runtime.state_manager.state
        owner_state = state.characters.get(owner_id)
        if not owner_state:
            return []

        bucket = owner_state.inventory.items
        if bucket.get(item_id, 0) <= 0:
            return []

        item_def = self.get_item_definition(item_id)
        if not item_def:
            return []

        effects: List[AnyEffect] = []
        on_use = getattr(item_def, "on_use", None)
        if on_use:
            effects.extend(on_use)
        if getattr(item_def, "consumable", False):
            effects.append(
                InventoryRemoveEffect(
                    target=owner_id,
                    item_type="item",
                    item=item_id,
                    count=1,
                )
            )
        return effects

    def apply_effect(self, effect: InventoryAddEffect | InventoryRemoveEffect) -> List[AnyEffect]:
        """
        Apply a single inventory effect to state and trigger item hooks.
        """
        state = self.runtime.state_manager.state

        item_def = self.get_item_definition(effect.item)
        if not item_def:
            return []

        owner = getattr(effect, "target", getattr(effect, "owner", None))
        if not owner or owner not in state.characters:
            return []

        owner_state = state.characters[owner]
        bucket = self._resolve_bucket(owner_state, effect.item_type)
        if bucket is None:
            return []

        current_count = bucket.get(effect.item, 0)
        if effect.type == "inventory_add":
            new_count = current_count + effect.count
        elif effect.type == "inventory_remove":
            new_count = current_count - effect.count
        else:
            return []

        if effect.item_type in (None, "item") and not self._is_stackable(item_def):
            new_count = max(0, min(1, new_count))

        bucket[effect.item] = max(0, new_count)
        if bucket[effect.item] == 0:
            bucket.pop(effect.item, None)

        triggered: List[AnyEffect] = []
        if effect.type == "inventory_add":
            on_get = getattr(item_def, "on_get", None)
            if on_get:
                triggered.extend(on_get)
        elif effect.type == "inventory_remove":
            on_lost = getattr(item_def, "on_lost", None)
            if on_lost:
                triggered.extend(on_lost)
        return triggered

    # Legacy helper compatibility
    def apply_legacy_effect(self, effect: InventoryChangeEffect) -> List[AnyEffect]:
        """Support for legacy deterministic helpers that still rely on InventoryChangeEffect."""
        new_effect: InventoryAddEffect | InventoryRemoveEffect
        if effect.type == "inventory_add":
            new_effect = InventoryAddEffect(
                target=effect.owner,
                item_type=effect.item_type or "item",
                item=effect.item,
                count=effect.count,
            )
        else:
            new_effect = InventoryRemoveEffect(
                target=effect.owner,
                item_type=effect.item_type or "item",
                item=effect.item,
                count=effect.count,
            )
        return self.apply_effect(new_effect)

    # ------------------------------------------------------------------ #
    # Additional helpers used by actions/effects
    # ------------------------------------------------------------------ #
    def give_item(self, source: str, target: str, item_id: str, *, count: int = 1) -> List[AnyEffect]:
        """Transfer an item between characters."""
        item_type = self.get_item_type(item_id) or "item"
        triggered: List[AnyEffect] = []
        triggered.extend(
            self.apply_effect(
                InventoryRemoveEffect(
                    target=source,
                    item_type=item_type,
                    item=item_id,
                    count=count,
                )
            )
        )
        triggered.extend(
            self.apply_effect(
                InventoryAddEffect(
                    target=target,
                    item_type=item_type,
                    item=item_id,
                    count=count,
                )
            )
        )
        return triggered

    def take_from_location(self, owner_id: str, item_id: str, *, count: int = 1) -> List[AnyEffect]:
        state = self.runtime.state_manager.state
        location_state = state.locations.get(state.current_location)
        if not location_state:
            return []

        bucket = location_state.inventory.items
        if bucket.get(item_id, 0) < count:
            return []

        bucket[item_id] -= count
        if bucket[item_id] <= 0:
            bucket.pop(item_id, None)

        return self.apply_effect(
            InventoryAddEffect(
                target=owner_id,
                item_type=self.get_item_type(item_id) or "item",
                item=item_id,
                count=count,
            )
        )

    def drop_to_location(self, owner_id: str, item_id: str, *, count: int = 1) -> List[AnyEffect]:
        state = self.runtime.state_manager.state
        location_state = state.locations.get(state.current_location)
        if not location_state:
            return []

        triggered = self.apply_effect(
            InventoryRemoveEffect(
                target=owner_id,
                item_type=self.get_item_type(item_id) or "item",
                item=item_id,
                count=count,
            )
        )

        bucket = location_state.inventory.items
        bucket[item_id] = bucket.get(item_id, 0) + count
        return triggered

    # Utility helpers -----------------------------------------------------------
    def get_item_definition(self, item_id: str) -> Any | None:
        if item_id in self.item_defs:
            return self.item_defs[item_id]
        if item_id in self.clothing_defs:
            return self.clothing_defs[item_id]
        if item_id in self.outfit_defs:
            return self.outfit_defs[item_id]
        return None

    def get_item_type(self, item_id: str) -> str | None:
        if item_id in self.item_defs:
            return "item"
        if item_id in self.clothing_defs:
            return "clothing"
        if item_id in self.outfit_defs:
            return "outfit"
        return None

    @staticmethod
    def _is_stackable(item_def: Any) -> bool:
        return bool(getattr(item_def, "stackable", False))

    @staticmethod
    def _resolve_bucket(owner_state, item_type: str | None):
        inventory = owner_state.inventory
        if item_type == "clothing":
            return inventory.clothing
        if item_type == "outfit":
            return inventory.outfits
        return inventory.items
