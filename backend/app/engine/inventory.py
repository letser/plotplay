"""Inventory management service for PlotPlay."""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from app.models.effects import InventoryChangeEffect, AnyEffect

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine


class InventoryService:
    """
    Manages character and player inventories.

    Responsibilities:
    - Process item usage and return effects to apply
    - Apply inventory add/remove effects to state
    - Validate item and owner references
    - Enforce stackable limits
    """

    def __init__(self, engine: "GameEngine"):
        self.engine = engine
        self.game_def = engine.game_def
        self.item_defs = {item.id: item for item in self.game_def.items}

    def use_item(self, owner_id: str, item_id: str) -> List[AnyEffect]:
        """
        Handles the logic for a character using an item.
        Returns a list of effects to be applied.

        Args:
            owner_id: The character/player using the item
            item_id: The ID of the item to use

        Returns:
            List of effects to apply (item effects + consumable removal)
        """
        state = self.engine.state_manager.state
        owner_inventory = state.inventory.setdefault(owner_id, {})

        if owner_inventory.get(item_id, 0) <= 0:
            return []

        item_def = self.item_defs.get(item_id)
        if not item_def:
            return []

        effects_to_apply = list(item_def.effects_on_use) if item_def.effects_on_use else []

        if item_def.consumable:
            remove_effect = InventoryChangeEffect(
                type="inventory_remove",
                owner=owner_id,
                item=item_id,
                count=1
            )
            effects_to_apply.append(remove_effect)

        return effects_to_apply

    def apply_effect(self, effect: InventoryChangeEffect):
        """
        Applies a single inventory change effect to the state.

        Args:
            effect: The inventory change effect to apply
        """
        state = self.engine.state_manager.state

        # Ignore invalid item references
        if effect.item not in self.item_defs:
            return

        # Ignore invalid owner references
        existent_character = effect.owner in self.game_def.characters or effect.owner == "player"
        if not existent_character:
            return

        owner_inventory = state.inventory.setdefault(effect.owner, {})
        current_count = owner_inventory.get(effect.item, 0)

        if effect.type == "inventory_add":
            new_count = current_count + effect.count
        elif effect.type == "inventory_remove":
            new_count = current_count - effect.count
        else:
            return

        item_def = self.item_defs.get(effect.item)
        if item_def and not item_def.stackable:
            new_count = max(0, min(1, new_count))

        owner_inventory[effect.item] = max(0, new_count)
