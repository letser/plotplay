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

            # Handle outfit grant_items on acquisition
            if effect.item_type == "outfit" and getattr(item_def, "grant_items", False):
                granted = self._grant_outfit_items(owner_state, effect.item, item_def)
                if granted:
                    self.runtime.logger.info(f"Outfit '{effect.item}' granted missing items: {granted}")

        elif effect.type == "inventory_remove":
            on_lost = getattr(item_def, "on_lost", None)
            if on_lost:
                triggered.extend(on_lost)

            # Handle outfit grant_items on loss
            if effect.item_type == "outfit" and getattr(item_def, "grant_items", False):
                removed = self._remove_granted_outfit_items(owner_state, effect.item)
                if removed:
                    self.runtime.logger.info(f"Outfit '{effect.item}' removed granted items: {removed}")

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

    def _grant_outfit_items(self, owner_state, outfit_id: str, outfit_def) -> list[str]:
        """
        Grant missing clothing items when acquiring an outfit with grant_items=true.
        Only adds items that are not already owned (Option 1).
        Tracks which items were granted for proper removal later.
        Returns list of granted item IDs.
        """
        granted_items = []
        outfit_items = getattr(outfit_def, "items", {})

        for clothing_id in outfit_items.keys():
            # Only grant if not already owned
            if owner_state.inventory.clothing.get(clothing_id, 0) <= 0:
                owner_state.inventory.clothing[clothing_id] = 1
                granted_items.append(clothing_id)

        # Track what was granted for this outfit
        if granted_items:
            if outfit_id not in owner_state.outfit_granted_items:
                owner_state.outfit_granted_items[outfit_id] = set()
            owner_state.outfit_granted_items[outfit_id].update(granted_items)

        return granted_items

    def _remove_granted_outfit_items(self, owner_state, outfit_id: str) -> list[str]:
        """
        Remove clothing items that were granted by this outfit.
        Only removes items that were originally granted (tracked in outfit_granted_items).
        Returns list of removed item IDs.
        """
        removed_items = []
        granted = owner_state.outfit_granted_items.get(outfit_id, set())

        for clothing_id in granted:
            # Only remove if still owned
            if owner_state.inventory.clothing.get(clothing_id, 0) > 0:
                owner_state.inventory.clothing[clothing_id] -= 1
                if owner_state.inventory.clothing[clothing_id] <= 0:
                    owner_state.inventory.clothing.pop(clothing_id, None)
                removed_items.append(clothing_id)

        # Clear tracking for this outfit
        if outfit_id in owner_state.outfit_granted_items:
            owner_state.outfit_granted_items.pop(outfit_id)

        return removed_items
