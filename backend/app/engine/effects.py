"""Effect resolution helpers for the PlotPlay engine."""

from __future__ import annotations

import random
from typing import Iterable, TYPE_CHECKING

from app.core.conditions import ConditionEvaluator
from app.models.effects import (
    AnyEffect,
    AdvanceTimeEffect,
    ApplyModifierEffect,
    ClothingPutOnEffect,
    ClothingTakeOffEffect,
    ClothingStateEffect,
    ClothingSlotStateEffect,
    ConditionalEffect,
    FlagSetEffect,
    GotoEffect,
    InventoryAddEffect,
    InventoryRemoveEffect,
    InventoryPurchaseEffect,
    InventorySellEffect,
    InventoryGiveEffect,
    InventoryTakeEffect,
    InventoryDropEffect,
    LockEffect,
    MeterChangeEffect,
    MoveEffect,
    MoveToEffect,
    OutfitPutOnEffect,
    OutfitTakeOffEffect,
    RandomEffect,
    RemoveModifierEffect,
    TravelToEffect,
    UnlockEffect,
)

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine


class EffectResolver:
    """Encapsulates effect application logic."""

    def __init__(self, engine: "GameEngine") -> None:
        self.engine = engine

    def apply_effects(self, effects: Iterable[AnyEffect]) -> None:
        from app.models.effects import parse_effect

        state = self.engine.state_manager.state
        evaluator = ConditionEvaluator(state, rng_seed=self.engine.get_turn_seed())

        for effect in effects:
            # Handle both dict and parsed effect objects
            if isinstance(effect, dict):
                effect = parse_effect(effect)

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
                    hook_effects = self.engine.inventory.apply_effect(legacy_effect)
                    if hook_effects:
                        self.apply_effects(hook_effects)
                case InventoryChangeEffect():
                    hook_effects = self.engine.inventory.apply_effect(effect)
                    if hook_effects:
                        self.apply_effects(hook_effects)
                case InventoryPurchaseEffect():
                    self._apply_purchase(effect)
                case InventorySellEffect():
                    self._apply_sell(effect)
                case InventoryGiveEffect():
                    self._apply_give(effect)
                case InventoryTakeEffect():
                    self._apply_inventory_take(effect)
                case InventoryDropEffect():
                    self._apply_inventory_drop(effect)
                case ClothingChangeEffect():
                    self.engine.clothing.apply_effect(effect)
                case ClothingPutOnEffect():
                    self._apply_clothing_put_on(effect)
                case ClothingTakeOffEffect():
                    self._apply_clothing_take_off(effect)
                case ClothingStateEffect():
                    self._apply_clothing_state(effect)
                case ClothingSlotStateEffect():
                    self._apply_clothing_slot_state(effect)
                case OutfitPutOnEffect():
                    self._apply_outfit_put_on(effect)
                case OutfitTakeOffEffect():
                    self._apply_outfit_take_off(effect)
                case MoveEffect():
                    self._apply_move(effect)
                case TravelToEffect():
                    self._apply_travel_to(effect)
                case LockEffect():
                    self._apply_lock(effect)
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

        # Get modifiers from character state
        char_state = self.engine.state_manager.state.characters.get(effect.target)
        active_modifiers = char_state.modifiers if char_state else {}
        for mod_id, mod_state in active_modifiers.items():
            mod_def = self.engine.modifiers.library.get(mod_id)
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

    def apply_goto_node(self, effect: GotoEffect) -> None:
        if effect.node in self.engine.nodes_map:
            self.engine.state_manager.state.current_node = effect.node
            # Apply on_enter effects of the new node
            new_node = self.engine.nodes_map[effect.node]
            if hasattr(new_node, 'on_enter') and new_node.on_enter:
                self.engine.logger.info(f"Applying on_enter effects for node '{effect.node}'")
                self.apply_effects(list(new_node.on_enter))

    def apply_advance_time(self, effect: AdvanceTimeEffect) -> None:
        self.engine.logger.info("Applying AdvanceTimeEffect: %s minutes.", effect.minutes)
        self.engine._advance_time(minutes=effect.minutes)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _apply_conditional_effect(self, effect: ConditionalEffect) -> None:
        evaluator = ConditionEvaluator(self.engine.state_manager.state, rng_seed=self.engine.get_turn_seed())
        if evaluator.evaluate(effect.when):
            self.apply_effects(effect.then)
        else:
            self.apply_effects(effect.otherwise)

    def _apply_random_effect(self, effect: RandomEffect) -> None:
        total_weight = sum(choice.weight for choice in effect.choices)
        if total_weight <= 0:
            return

        roll = random.Random(self.engine.get_turn_seed()).uniform(0, total_weight)
        current_weight = 0

        for choice in effect.choices:
            current_weight += choice.weight
            if roll <= current_weight:
                self.apply_effects(choice.effects)
                return

    def _apply_unlock(self, effect: UnlockEffect) -> None:
        """Handle unlock effect: unlock items, clothing, outfits, zones, locations, actions, endings."""
        state = self.engine.state_manager.state

        # Unlock items
        if effect.items:
            for item_id in effect.items:
                if item_id not in state.unlocked_items:
                    state.unlocked_items.append(item_id)

        # Unlock clothing
        if effect.clothing:
            for clothing_id in effect.clothing:
                if clothing_id not in state.unlocked_clothing:
                    state.unlocked_clothing.append(clothing_id)

        # Unlock outfits (uses specialized method with character targeting)
        if effect.outfit or effect.outfits:
            self._apply_unlock_outfit(effect)

        # Unlock zones (adds to discovered_zones)
        if effect.zones:
            state.discovered_zones.update(effect.zones)

        # Unlock locations (adds to discovered_locations)
        if effect.locations:
            state.discovered_locations.update(effect.locations)

        # Unlock actions
        if effect.actions:
            for action_id in effect.actions:
                if action_id not in state.unlocked_actions:
                    state.unlocked_actions.append(action_id)

        # Unlock endings
        if effect.ending or effect.endings:
            self._apply_unlock_ending(effect)

    def _apply_move_to(self, effect: MoveToEffect) -> None:
        state = self.engine.state_manager.state

        if effect.location not in state.discovered_locations:
            return

        chars_to_move = [char for char in effect.with_characters if char in state.present_chars]

        state.location_current = effect.location
        state.location_privacy = self.engine._get_location_privacy(effect.location)

        self.engine._update_npc_presence()

        current_node = self.engine.get_current_node()
        current_node.characters_present.extend(chars_to_move)

        if current_node.characters_present:
            state.present_chars = [
                char for char in current_node.characters_present if char in self.engine.characters_map
            ]

    def _apply_purchase(self, effect: InventoryPurchaseEffect) -> None:
        """Handle inventory_purchase effect: deduct money and add item."""
        state = self.engine.state_manager.state
        economy = self.engine.game_def.economy

        if not economy or not economy.enabled:
            return

        evaluator = ConditionEvaluator(state, rng_seed=self.engine.get_turn_seed())
        shop = self._resolve_shop(effect.source)
        if shop:
            if not evaluator.evaluate(shop.when):
                return
            multiplier = self._evaluate_multiplier(evaluator, shop.multiplier_buy)
        else:
            multiplier = 1.0

        item_def = self.engine.inventory.get_item_definition(effect.item)
        if not item_def:
            return

        actual_type = self.engine.inventory.get_item_type(effect.item)
        if effect.item_type and actual_type and actual_type != effect.item_type:
            self.engine.logger.warning(
                "Purchase blocked: item '%s' expected type '%s' but resolved to '%s'",
                effect.item,
                effect.item_type,
                actual_type,
            )
            return

        base_value = getattr(item_def, "value", 0) or 0
        if effect.price is not None:
            total_price = effect.price
        else:
            total_price = base_value * effect.count * multiplier

        # Check if buyer has enough money
        buyer_meters = state.meters.get(effect.target)
        if not buyer_meters or "money" not in buyer_meters:
            return

        if buyer_meters["money"] < total_price:
            return  # Insufficient funds

        # Deduct money from buyer
        buyer_meters["money"] -= total_price
        if economy.max_money:
            buyer_meters["money"] = min(buyer_meters["money"], economy.max_money)

        # Add item to buyer's inventory
        add_effect = InventoryChangeEffect(
            type="inventory_add",
            owner=effect.target,
            item=effect.item,
            count=effect.count
        )
        hook_effects = self.engine.inventory.apply_effect(add_effect)
        if hook_effects:
            self.apply_effects(hook_effects)

        # Remove item from seller's inventory (if source is a character)
        if effect.source in state.characters:
            remove_effect = InventoryChangeEffect(
                type="inventory_remove",
                owner=effect.source,
                item=effect.item,
                count=effect.count
            )
            hook_effects = self.engine.inventory.apply_effect(remove_effect)
            if hook_effects:
                self.apply_effects(hook_effects)

    def _apply_sell(self, effect: InventorySellEffect) -> None:
        """Handle inventory_sell effect: add money and remove item."""
        state = self.engine.state_manager.state
        economy = self.engine.game_def.economy

        if not economy or not economy.enabled:
            return

        evaluator = ConditionEvaluator(state, rng_seed=self.engine.get_turn_seed())
        shop = self._resolve_shop(effect.target)
        if shop:
            if not evaluator.evaluate(shop.when):
                return
            if shop.can_buy and not evaluator.evaluate(shop.can_buy):
                return
            multiplier = self._evaluate_multiplier(evaluator, shop.multiplier_sell)
        else:
            multiplier = 1.0

        item_def = self.engine.inventory.get_item_definition(effect.item)
        if not item_def:
            return

        actual_type = self.engine.inventory.get_item_type(effect.item)
        if effect.item_type and actual_type and actual_type != effect.item_type:
            self.engine.logger.warning(
                "Sell blocked: item '%s' expected type '%s' but resolved to '%s'",
                effect.item,
                effect.item_type,
                actual_type,
            )
            return

        base_value = getattr(item_def, "value", 0) or 0
        if effect.price is not None:
            total_price = effect.price
        else:
            total_price = base_value * effect.count * multiplier

        # Check if seller has the item
        seller_inventory = state.inventory.get(effect.source, {})
        if seller_inventory.get(effect.item, 0) < effect.count:
            return  # Don't have enough items

        # Remove item from seller's inventory
        remove_effect = InventoryChangeEffect(
            type="inventory_remove",
            owner=effect.source,
            item=effect.item,
            count=effect.count
        )
        hook_effects = self.engine.inventory.apply_effect(remove_effect)
        if hook_effects:
            self.apply_effects(hook_effects)

        # Add money to seller
        seller_meters = state.meters.get(effect.source)
        if seller_meters and "money" in seller_meters:
            seller_meters["money"] += total_price
            if economy.max_money:
                seller_meters["money"] = min(seller_meters["money"], economy.max_money)

        # Add item to buyer's inventory (if target is a character)
        if effect.target in state.characters:
            add_effect = InventoryChangeEffect(
                type="inventory_add",
                owner=effect.target,
                item=effect.item,
                count=effect.count
            )
            hook_effects = self.engine.inventory.apply_effect(add_effect)
            if hook_effects:
                self.apply_effects(hook_effects)

    def _apply_give(self, effect: InventoryGiveEffect) -> None:
        """Handle inventory_give effect: give item from one character to another."""
        state = self.engine.state_manager.state

        # Validation 1: Both source and target must be valid characters
        if effect.source not in state.characters:
            self.engine.logger.warning(f"Give effect failed: source '{effect.source}' is not a valid character")
            return
        if effect.target not in state.characters:
            self.engine.logger.warning(f"Give effect failed: target '{effect.target}' is not a valid character")
            return

        # Validation 2: Source and target must be different
        if effect.source == effect.target:
            self.engine.logger.warning(f"Give effect failed: cannot give to self (source=target='{effect.source}')")
            return

        # Validation 3: Source and target must be present together (same location)
        source_location = None
        target_location = None

        # Find source location
        if effect.source == "player":
            source_location = state.location_current
        else:
            # Check if source is in present_chars at current location
            if effect.source in state.present_chars:
                source_location = state.location_current

        # Find target location
        if effect.target == "player":
            target_location = state.location_current
        else:
            # Check if target is in present_chars at current location
            if effect.target in state.present_chars:
                target_location = state.location_current

        # Both must be at the same location
        if not source_location or not target_location or source_location != target_location:
            self.engine.logger.warning(
                f"Give effect failed: '{effect.source}' and '{effect.target}' are not present together"
            )
            return

        # Get item definition to check can_give
        item_def = self.engine.inventory.get_item_definition(effect.item)
        if not item_def:
            self.engine.logger.warning(f"Give effect failed: item '{effect.item}' not found")
            return

        # Ensure type matches item definition
        actual_type = self.engine.inventory.get_item_type(effect.item)
        if actual_type and effect.item_type and actual_type != effect.item_type:
            self.engine.logger.warning(
                "Give effect failed: item '%s' expected type '%s' but got '%s'",
                effect.item,
                actual_type,
                effect.item_type,
            )
            return

        # Validation 4: Check if item can be given (if can_give is explicitly False, block)
        if getattr(item_def, "can_give", True) is False:
            self.engine.logger.warning(f"Give effect failed: item '{effect.item}' cannot be given (can_give=False)")
            return

        # Validation 5: Check if source has the item
        source_inventory = state.inventory.get(effect.source, {})
        if source_inventory.get(effect.item, 0) < effect.count:
            self.engine.logger.warning(
                f"Give effect failed: '{effect.source}' does not have {effect.count}x '{effect.item}'"
            )
            return

        # Remove item from source inventory (triggers on_lost hook)
        remove_effect = InventoryChangeEffect(
            type="inventory_remove",
            owner=effect.source,
            item=effect.item,
            count=effect.count
        )
        hook_effects = self.engine.inventory.apply_effect(remove_effect)
        if hook_effects:
            self.apply_effects(hook_effects)

        # Add item to target inventory (triggers on_get hook)
        add_effect = InventoryChangeEffect(
            type="inventory_add",
            owner=effect.target,
            item=effect.item,
            count=effect.count
        )
        hook_effects = self.engine.inventory.apply_effect(add_effect)
        if hook_effects:
            self.apply_effects(hook_effects)

        # Trigger on_give hook from the item
        on_give = getattr(item_def, "on_give", None)
        if on_give:
            self.apply_effects(on_give)

    def _apply_unlock_outfit(self, effect: UnlockEffect) -> None:
        state = self.engine.state_manager.state
        target_char = effect.character or "player"

        outfits: list[str] = []
        if effect.outfit:
            outfits.append(effect.outfit)
        if effect.outfits:
            outfits.extend(effect.outfits)

        if not outfits:
            return

        unlocked = state.unlocked_outfits.setdefault(target_char, [])
        for outfit_id in outfits:
            if outfit_id not in unlocked:
                unlocked.append(outfit_id)
                # Grant clothing items if the outfit has grant_items=True
                self.engine.clothing.grant_outfit_items(target_char, outfit_id)

    def _apply_unlock_ending(self, effect: UnlockEffect) -> None:
        state = self.engine.state_manager.state

        endings: list[str] = []
        if effect.ending:
            endings.append(effect.ending)
        if effect.endings:
            endings.extend(effect.endings)

        for ending_id in endings:
            if ending_id not in state.unlocked_endings:
                state.unlocked_endings.append(ending_id)

    def _apply_unlock_actions(self, effect: UnlockEffect) -> None:
        state = self.engine.state_manager.state
        if not effect.actions:
            return

        for action_id in effect.actions:
            if action_id not in state.unlocked_actions:
                state.unlocked_actions.append(action_id)

    def _resolve_shop(self, owner_id: str | None):
        if not owner_id:
            return None
        if owner_id in self.engine.locations_map:
            location = self.engine.locations_map[owner_id]
            return getattr(location, "shop", None)
        if owner_id in self.engine.characters_map:
            character = self.engine.characters_map[owner_id]
            return getattr(character, "shop", None)
        return None

    @staticmethod
    def _evaluate_multiplier(evaluator: ConditionEvaluator, expression: str | None) -> float:
        if not expression:
            return 1.0
        value = evaluator.evaluate_value(expression)
        try:
            return float(value)
        except (TypeError, ValueError):
            return 1.0

    def _apply_inventory_take(self, effect: InventoryTakeEffect) -> None:
        """Handle inventory_take effect: take item from current location."""
        state = self.engine.state_manager.state
        current_location = state.location_current

        if not current_location:
            return

        # Check if location has this item
        loc_inventory = state.location_inventory.get(current_location, {})
        if loc_inventory.get(effect.item, 0) < effect.count:
            return  # Not enough items at location

        # Remove from location inventory
        loc_inventory[effect.item] -= effect.count
        if loc_inventory[effect.item] <= 0:
            del loc_inventory[effect.item]

        # Add to character inventory
        add_effect = InventoryChangeEffect(
            type="inventory_add",
            owner=effect.target,
            item=effect.item,
            count=effect.count
        )
        hook_effects = self.engine.inventory.apply_effect(add_effect)
        if hook_effects:
            self.apply_effects(hook_effects)

    def _apply_inventory_drop(self, effect: InventoryDropEffect) -> None:
        """Handle inventory_drop effect: drop item at current location."""
        state = self.engine.state_manager.state
        current_location = state.location_current

        if not current_location:
            return

        # Check if character has this item
        char_inventory = state.inventory.get(effect.target, {})
        if char_inventory.get(effect.item, 0) < effect.count:
            return  # Not enough items in inventory

        # Remove from character inventory
        remove_effect = InventoryChangeEffect(
            type="inventory_remove",
            owner=effect.target,
            item=effect.item,
            count=effect.count
        )
        hook_effects = self.engine.inventory.apply_effect(remove_effect)
        if hook_effects:
            self.apply_effects(hook_effects)

        # Add to location inventory
        state.location_inventory.setdefault(current_location, {})
        state.location_inventory[current_location].setdefault(effect.item, 0)
        state.location_inventory[current_location][effect.item] += effect.count

    def _apply_clothing_put_on(self, effect: ClothingPutOnEffect) -> None:
        """Handle clothing_put_on effect: put on a clothing item."""
        self.engine.clothing.put_on_clothing(
            char_id=effect.target,
            clothing_id=effect.item,
            state=effect.state or "intact"
        )

    def _apply_clothing_take_off(self, effect: ClothingTakeOffEffect) -> None:
        """Handle clothing_take_off effect: take off a clothing item."""
        self.engine.clothing.take_off_clothing(
            char_id=effect.target,
            clothing_id=effect.item
        )

    def _apply_clothing_state(self, effect: ClothingStateEffect) -> None:
        """Handle clothing_state effect: change state of a clothing item."""
        self.engine.clothing.set_clothing_state(
            char_id=effect.target,
            clothing_id=effect.item,
            state=effect.state
        )

    def _apply_clothing_slot_state(self, effect: ClothingSlotStateEffect) -> None:
        """Handle clothing_slot_state effect: change state of slot's clothing."""
        self.engine.clothing.set_slot_state(
            char_id=effect.target,
            slot=effect.slot,
            state=effect.state
        )

    def _apply_outfit_put_on(self, effect: OutfitPutOnEffect) -> None:
        """Handle outfit_put_on effect: put on an entire outfit."""
        self.engine.clothing.put_on_outfit(
            char_id=effect.target,
            outfit_id=effect.item
        )

    def _apply_outfit_take_off(self, effect: OutfitTakeOffEffect) -> None:
        """Handle outfit_take_off effect: take off an entire outfit."""
        self.engine.clothing.take_off_outfit(
            char_id=effect.target,
            outfit_id=effect.item
        )

    def _apply_move(self, effect: MoveEffect) -> None:
        """Handle move effect: cardinal direction movement."""
        self.engine.movement.move_by_direction(
            direction=effect.direction,
            with_characters=effect.with_characters or []
        )

    def _apply_travel_to(self, effect: TravelToEffect) -> None:
        """Handle travel_to effect: zone travel with method."""
        self.engine.movement.travel_to_zone(
            location_id=effect.location,
            method=effect.method,
            with_characters=effect.with_characters or []
        )

    def _apply_lock(self, effect: LockEffect) -> None:
        """Handle lock effect: re-lock items, clothing, outfits, zones, locations, actions, endings."""
        state = self.engine.state_manager.state

        # Lock items (remove from unlocked list)
        if effect.items:
            state.unlocked_items = [item_id for item_id in state.unlocked_items if item_id not in effect.items]

        # Lock clothing (remove from unlocked list)
        if effect.clothing:
            state.unlocked_clothing = [clothing_id for clothing_id in state.unlocked_clothing
                                       if clothing_id not in effect.clothing]

        # Lock outfits (remove from unlocked_outfits per character)
        if effect.outfits:
            for char_id in state.unlocked_outfits:
                state.unlocked_outfits[char_id] = [
                    outfit_id for outfit_id in state.unlocked_outfits[char_id]
                    if outfit_id not in effect.outfits
                ]

        # Lock zones (remove from discovered_zones)
        if effect.zones:
            state.discovered_zones.difference_update(effect.zones)

        # Lock locations (remove from discovered_locations)
        if effect.locations:
            state.discovered_locations.difference_update(effect.locations)

        # Lock actions (remove from unlocked list)
        if effect.actions:
            state.unlocked_actions = [action_id for action_id in state.unlocked_actions
                                       if action_id not in effect.actions]

        # Lock endings (remove from unlocked list)
        if effect.endings:
            state.unlocked_endings = [ending_id for ending_id in state.unlocked_endings
                                       if ending_id not in effect.endings]
