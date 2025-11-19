"""Inventory management service for PlotPlay."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Any

from app.models.effects import (
    InventoryAddEffect,
    InventoryRemoveEffect,
    AnyEffect
)

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
        index = engine.index

        # Cache lookups for items, clothing, and outfits
        self.item_defs = dict(index.items)
        self.clothing_defs = dict(index.clothing)
        self.outfit_defs = dict(index.outfits)

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

        item_def = self._get_item_definition(item_id)
        if not item_def:
            return []

        effects_to_apply: List[AnyEffect] = []
        on_use = getattr(item_def, "on_use", None)
        if on_use:
            effects_to_apply.extend(on_use)

        if getattr(item_def, "consumable", False):
            remove_effect = InventoryRemoveEffect(
                target=owner_id,
                item_type="item",
                item=item_id,
                count=1
            )
            effects_to_apply.append(remove_effect)

        return effects_to_apply

    def apply_effect(self, effect: InventoryAddEffect | InventoryRemoveEffect) -> List[AnyEffect]:
        """
        Applies a single inventory change effect to the state.
        Triggers item hooks (on_get, on_lost) and returns their effects.

        Args:
            effect: The inventory change effect to apply

        Returns:
            List of effects from triggered item hooks
        """
        state = self.engine.state_manager.state

        item_def = self._get_item_definition(effect.item)
        if not item_def:
            return []

        # Get the owner (target for new effects, owner for legacy)
        owner = getattr(effect, 'target', getattr(effect, 'owner', None))
        if not owner:
            return []

        # Ignore invalid owner references
        existent_character = owner in self.engine.characters_map
        if not existent_character:
            return []

        owner_inventory = state.inventory.setdefault(owner, {})
        current_count = owner_inventory.get(effect.item, 0)

        if effect.type == "inventory_add":
            new_count = current_count + effect.count
        elif effect.type == "inventory_remove":
            new_count = current_count - effect.count
        else:
            return []

        if not self._is_stackable(item_def):
            new_count = max(0, min(1, new_count))

        owner_inventory[effect.item] = max(0, new_count)

        # Trigger item hooks after inventory change
        triggered_effects: List[AnyEffect] = []
        if effect.type == "inventory_add":
            on_get = getattr(item_def, "on_get", None)
            if on_get:
                triggered_effects.extend(on_get)
        elif effect.type == "inventory_remove":
            on_lost = getattr(item_def, "on_lost", None)
            if on_lost:
                triggered_effects.extend(on_lost)

        return triggered_effects

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _get_item_definition(self, item_id: str) -> Any | None:
        if item_id in self.item_defs:
            return self.item_defs[item_id]
        if item_id in self.clothing_defs:
            return self.clothing_defs[item_id]
        if item_id in self.outfit_defs:
            return self.outfit_defs[item_id]
        return None

    @staticmethod
    def _is_stackable(item_def: Any) -> bool:
        return bool(getattr(item_def, "stackable", False))

    # Public helper for other engine services
    def get_item_definition(self, item_id: str) -> Any | None:
        return self._get_item_definition(item_id)

    def get_item_type(self, item_id: str) -> str | None:
        if item_id in self.item_defs:
            return "item"
        if item_id in self.clothing_defs:
            return "clothing"
        if item_id in self.outfit_defs:
            return "outfit"
        return None
