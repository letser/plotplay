# backend/app/core/inventory_manager.py
from typing import List
from app.models.game import GameDefinition
from app.core.state_manager import GameState
from app.models.effects import InventoryChangeEffect, AnyEffect


class InventoryManager:
    """
    Manages character and player inventories.
    """

    def __init__(self, game_def: GameDefinition):
        self.game_def = game_def
        self.item_defs = {item.id: item for item in self.game_def.items}

    def use_item(self, owner_id: str, item_id: str, state: GameState) -> List[AnyEffect]:
        """
        Handles the logic for a character using an item.
        Returns a list of effects to be applied.
        """
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

    def apply_effect(self, effect: InventoryChangeEffect, state: GameState):
        """Applies a single inventory change effect to the state."""
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