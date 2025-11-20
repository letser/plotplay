"""Trading and inventory transfer helpers for the new runtime."""

from __future__ import annotations

from typing import List, Tuple, Any

from app.models.effects import (
    InventoryAddEffect,
    InventoryRemoveEffect,
    InventoryTakeEffect,
    InventoryDropEffect,
    InventoryPurchaseEffect,
    InventorySellEffect,
    InventoryGiveEffect,
    MeterChangeEffect,
)
from app.runtime.session import SessionRuntime


class TradeService:
    """Handles item transfers, shop purchases/sales, and gives."""

    def __init__(self, runtime: SessionRuntime) -> None:
        self.runtime = runtime
        self.logger = runtime.logger

    # ------------------------------------------------------------------ #
    # Location and direct transfers
    # ------------------------------------------------------------------ #
    def take_from_location(self, effect: InventoryTakeEffect) -> List:
        state = self.runtime.state_manager.state
        location_state = state.locations.get(state.current_location)
        if not location_state:
            return []

        bucket = location_state.inventory.items
        if bucket.get(effect.item, 0) < effect.count:
            return []

        bucket[effect.item] -= effect.count
        if bucket[effect.item] <= 0:
            bucket.pop(effect.item, None)

        return [
            InventoryAddEffect(
                target=effect.target,
                item_type=effect.item_type,
                item=effect.item,
                count=effect.count,
            )
        ]

    def drop_to_location(self, effect: InventoryDropEffect) -> List:
        state = self.runtime.state_manager.state
        location_state = state.locations.get(state.current_location)
        if not location_state:
            return []

        bucket = location_state.inventory.items
        bucket[effect.item] = bucket.get(effect.item, 0) + effect.count

        return [
            InventoryRemoveEffect(
                target=effect.target,
                item_type=effect.item_type,
                item=effect.item,
                count=effect.count,
            )
        ]

    def give(self, effect: InventoryGiveEffect) -> List:
        return [
            InventoryRemoveEffect(
                target=effect.source,
                item_type=effect.item_type,
                item=effect.item,
                count=effect.count,
            ),
            InventoryAddEffect(
                target=effect.target,
                item_type=effect.item_type,
                item=effect.item,
                count=effect.count,
            ),
        ]

    # ------------------------------------------------------------------ #
    # Commerce helpers
    # ------------------------------------------------------------------ #
    def purchase(self, effect: InventoryPurchaseEffect) -> List:
        """Transfer an item from seller (merchant/location shop) to buyer with pricing rules."""
        state = self.runtime.state_manager.state
        buyer_state = state.characters.get(effect.target)
        if not buyer_state:
            return []

        item_def = getattr(self.runtime, "inventory_service", None)
        item_def = item_def.get_item_definition(effect.item) if item_def else None
        unit_price = effect.price if effect.price is not None else getattr(item_def, "value", 0) or 0

        shop_bucket, shop_def = self._resolve_shop_inventory(effect.source)
        evaluator = self.runtime.state_manager.create_evaluator()
        multiplier = 1.0
        if shop_def and getattr(shop_def, "multiplier_buy", None):
            mult_val = evaluator.evaluate_value(shop_def.multiplier_buy, default=1)
            try:
                multiplier = float(mult_val)
            except (TypeError, ValueError):
                multiplier = 1.0

        total_price = unit_price * multiplier * effect.count

        # Stock check
        if shop_bucket is not None:
            available = shop_bucket.get(effect.item, 0)
            resell = getattr(shop_def, "resell", False) if shop_def else False
            if not resell and available < effect.count:
                return []

        # Money check
        money_before = buyer_state.meters.get("money") if buyer_state.meters else None
        if money_before is not None and total_price and money_before < total_price:
            return []

        transfer_effects: List = [
            InventoryAddEffect(
                target=effect.target,
                item_type=effect.item_type,
                item=effect.item,
                count=effect.count,
            )
        ]

        if shop_bucket is not None and shop_bucket.get(effect.item, 0) >= effect.count:
            shop_bucket[effect.item] -= effect.count
            if shop_bucket[effect.item] <= 0:
                shop_bucket.pop(effect.item, None)

        if money_before is not None and total_price:
            transfer_effects.append(
                MeterChangeEffect(target=effect.target, meter="money", op="subtract", value=total_price)
            )

        seller_state = state.characters.get(effect.source) if effect.source else None
        if seller_state and seller_state.meters.get("money") is not None and total_price:
            transfer_effects.append(
                MeterChangeEffect(target=effect.source, meter="money", op="add", value=total_price)
            )

        return transfer_effects

    def sell(self, effect: InventorySellEffect) -> List:
        """Sell an item from source to a merchant/location shop."""
        state = self.runtime.state_manager.state
        seller_state = state.characters.get(effect.source)
        if not seller_state:
            return []

        shop_bucket, shop_def = self._resolve_shop_inventory(effect.target or state.current_location)
        evaluator = self.runtime.state_manager.create_evaluator()

        item_def = getattr(self.runtime, "inventory_service", None)
        item_def = item_def.get_item_definition(effect.item) if item_def else None
        unit_price = effect.price if effect.price is not None else getattr(item_def, "value", 0) or 0

        multiplier = 1.0
        if shop_def and getattr(shop_def, "multiplier_sell", None):
            mult_val = evaluator.evaluate_value(shop_def.multiplier_sell, default=1)
            try:
                multiplier = float(mult_val)
            except (TypeError, ValueError):
                multiplier = 1.0

        total_price = unit_price * multiplier * effect.count

        buyer_state = state.characters.get(effect.target) if effect.target else None
        buyer_money = buyer_state.meters.get("money") if buyer_state and buyer_state.meters else None
        if buyer_money is not None and total_price and buyer_money < total_price:
            return []

        transfer_effects: List = [
            InventoryRemoveEffect(
                target=effect.source,
                item_type=effect.item_type,
                item=effect.item,
                count=effect.count,
            )
        ]

        if shop_bucket is not None:
            shop_bucket[effect.item] = shop_bucket.get(effect.item, 0) + effect.count
        elif effect.target and effect.target in state.characters:
            transfer_effects.append(
                InventoryAddEffect(
                    target=effect.target,
                    item_type=effect.item_type,
                    item=effect.item,
                    count=effect.count,
                )
            )

        if seller_state.meters.get("money") is not None and total_price:
            transfer_effects.append(
                MeterChangeEffect(target=effect.source, meter="money", op="add", value=total_price)
            )

        if buyer_state and buyer_money is not None and total_price:
            transfer_effects.append(
                MeterChangeEffect(target=effect.target, meter="money", op="subtract", value=total_price)
            )

        return transfer_effects

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _resolve_shop_inventory(self, source_id: str | None) -> Tuple[Any, Any]:
        """
        Resolve an appropriate shop bucket and shop definition for a seller/buyer.
        Returns (bucket_dict, shop_def) or (None, None) if not a shop.
        """
        state = self.runtime.state_manager.state

        if source_id and source_id in state.characters:
            char_state = state.characters[source_id]
            char_def = self.runtime.index.characters.get(source_id)
            if char_state.shop:
                return char_state.shop.items, getattr(char_def, "shop", None)

        location_state = state.locations.get(state.current_location)
        location_def = self.runtime.index.locations.get(state.current_location)
        if location_state and location_state.shop:
            return location_state.shop.items, getattr(location_def, "shop", None)

        return None, None
