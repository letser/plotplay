"""
Tests for inventory validation edge cases:
- Taking items from locations
- Clothing/outfit grant_items behavior (FIXED)
- Clothing ownership validation (no auto-grant)
"""
import pytest
from app.runtime.types import PlayerAction
from app.models.effects import (
    InventoryTakeEffect,
    ClothingPutOnEffect,
    OutfitPutOnEffect,
)


@pytest.mark.asyncio
async def test_take_from_location_validates_item_exists(engine_factory):
    """
    Test that taking an item from a location validates the item exists there.
    """
    engine = engine_factory("coffeeshop_date")
    await engine.start()

    # Navigate to cafe counter
    await engine.process_action(PlayerAction(action_type="goto", location="cafe_counter"))

    # Try to take an item that DOES exist at the location
    state = engine.runtime.state_manager.state
    location_state = state.locations.get("cafe_counter")

    # Cafe counter should have vanilla_latte and spiced_matcha
    assert location_state.inventory.items.get("vanilla_latte", 0) == 2

    # Take effect should succeed
    trade_service = engine.trade_service
    effect = InventoryTakeEffect(
        target="player",
        item_type="item",
        item="vanilla_latte",
        count=1
    )
    hooks = trade_service.take_from_location(effect)

    # Should return add effect
    assert len(hooks) > 0
    assert location_state.inventory.items.get("vanilla_latte", 0) == 1


@pytest.mark.asyncio
async def test_take_from_location_with_missing_item_fails_silently(engine_factory):
    """
    Test that taking an item not at the location returns empty hooks (silent fail).
    """
    engine = engine_factory("coffeeshop_date")
    await engine.start()

    # Navigate to cafe patio (has no items)
    state = engine.runtime.state_manager.state

    # Try to take an item that doesn't exist
    trade_service = engine.trade_service
    effect = InventoryTakeEffect(
        target="player",
        item_type="item",
        item="nonexistent_item",
        count=1
    )
    hooks = trade_service.take_from_location(effect)

    # Should return empty list (silent fail)
    assert hooks == []


@pytest.mark.asyncio
async def test_outfit_grant_items_on_acquisition(engine_factory):
    """
    Test that acquiring an outfit with grant_items=true grants missing clothing items.
    This happens on ACQUISITION, not on equipping.
    """
    engine = engine_factory("coffeeshop_date")
    await engine.start()

    state = engine.runtime.state_manager.state
    player_state = state.characters.get("player")

    # Remove player's current outfit and all clothing to test from scratch
    player_state.inventory.outfits.clear()
    player_state.inventory.clothing.clear()
    player_state.outfit_granted_items.clear()
    player_state.clothing.outfit = None
    player_state.clothing.items.clear()

    # Give player a new outfit (this should trigger grant_items)
    from app.models.effects import InventoryAddEffect
    effect = InventoryAddEffect(
        target="player",
        item_type="outfit",
        item="player_date_casual",
        count=1
    )
    engine.runtime.inventory_service.apply_effect(effect)

    # Check that the outfit was added
    assert player_state.inventory.outfits.get("player_date_casual", 0) == 1

    # Check that the clothing items were granted (outfit definition has grant_items=true)
    assert "player_top_button_up" in player_state.inventory.clothing
    assert "player_bottom_chinos" in player_state.inventory.clothing
    assert "player_shoes_leather" in player_state.inventory.clothing

    # Check tracking - items should be tracked as granted
    assert "player_date_casual" in player_state.outfit_granted_items
    granted = player_state.outfit_granted_items["player_date_casual"]
    assert "player_top_button_up" in granted
    assert "player_bottom_chinos" in granted
    assert "player_shoes_leather" in granted


@pytest.mark.asyncio
async def test_clothing_put_on_requires_ownership(engine_factory):
    """
    Test that putting on a clothing item requires ownership.
    Clothing items act as regular items - must be owned before wearing.
    """
    engine = engine_factory("coffeeshop_date")
    await engine.start()

    state = engine.runtime.state_manager.state
    player_state = state.characters.get("player")

    # Remove a clothing item from both inventory and worn state
    player_state.inventory.clothing.pop("player_top_button_up", None)
    player_state.clothing.items.pop("player_top_button_up", None)
    assert "player_top_button_up" not in player_state.inventory.clothing

    # Try to put it on (should fail with ValueError)
    clothing_service = engine.clothing_service
    effect = ClothingPutOnEffect(
        target="player",
        item="player_top_button_up",
        condition="intact"
    )

    with pytest.raises(ValueError, match="Cannot put on 'player_top_button_up': not in inventory"):
        clothing_service.apply_effect(effect)

    # Should still not be in inventory
    assert "player_top_button_up" not in player_state.inventory.clothing

    # And should not be equipped
    assert "player_top_button_up" not in player_state.clothing.items


@pytest.mark.asyncio
async def test_give_validates_source_has_item(engine_factory):
    """
    Test that giving an item validates the source (player) has it.
    This was fixed in the previous session.
    """
    engine = engine_factory("coffeeshop_date")
    await engine.start()

    # Try to give an item we don't have
    action = PlayerAction(action_type="give", item_id="vanilla_latte", target="alex")

    with pytest.raises(ValueError, match="Cannot give item 'vanilla_latte': not in inventory"):
        await engine.process_action(action)


@pytest.mark.asyncio
async def test_take_from_location_insufficient_quantity_fails(engine_factory):
    """
    Test that trying to take more items than available fails silently.
    """
    engine = engine_factory("coffeeshop_date")
    await engine.start()

    # Navigate to cafe counter
    await engine.process_action(PlayerAction(action_type="goto", location="cafe_counter"))

    state = engine.runtime.state_manager.state
    location_state = state.locations.get("cafe_counter")

    # Cafe counter has 2 vanilla lattes
    assert location_state.inventory.items.get("vanilla_latte", 0) == 2

    # Try to take 5 (more than available)
    trade_service = engine.trade_service
    effect = InventoryTakeEffect(
        target="player",
        item_type="item",
        item="vanilla_latte",
        count=5
    )
    hooks = trade_service.take_from_location(effect)

    # Should fail silently (return empty list)
    assert hooks == []

    # Location should still have 2
    assert location_state.inventory.items.get("vanilla_latte", 0) == 2


@pytest.mark.asyncio
async def test_outfit_equip_requires_all_items(engine_factory):
    """
    Test that equipping an outfit validates all items exist.
    Cannot wear incomplete outfit.
    """
    engine = engine_factory("coffeeshop_date")
    await engine.start()

    state = engine.runtime.state_manager.state
    player_state = state.characters.get("player")

    # Give player an outfit but remove one clothing item
    from app.models.effects import InventoryAddEffect
    effect = InventoryAddEffect(
        target="player",
        item_type="outfit",
        item="player_date_casual",
        count=1
    )
    engine.runtime.inventory_service.apply_effect(effect)

    # Remove one of the required items
    player_state.inventory.clothing.pop("player_shoes_leather", None)

    # Try to equip the outfit (should fail)
    clothing_service = engine.clothing_service
    outfit_effect = OutfitPutOnEffect(
        target="player",
        item="player_date_casual"
    )

    with pytest.raises(ValueError, match="Cannot wear outfit 'player_date_casual': missing required clothing items"):
        clothing_service.apply_outfit_effect(outfit_effect)


@pytest.mark.asyncio
async def test_outfit_only_grants_missing_items(engine_factory):
    """
    Test that acquiring an outfit only grants missing items (Option 1).
    Items already owned are not duplicated.
    """
    engine = engine_factory("coffeeshop_date")
    await engine.start()

    state = engine.runtime.state_manager.state
    player_state = state.characters.get("player")

    # Clear inventory and add only one item
    player_state.inventory.clothing.clear()
    player_state.outfit_granted_items.clear()
    player_state.inventory.clothing["player_top_button_up"] = 1

    # Acquire outfit (should only grant missing items)
    from app.models.effects import InventoryAddEffect
    effect = InventoryAddEffect(
        target="player",
        item_type="outfit",
        item="player_date_casual",
        count=1
    )
    engine.runtime.inventory_service.apply_effect(effect)

    # Check that top is still 1 (not duplicated)
    assert player_state.inventory.clothing["player_top_button_up"] == 1

    # Check that missing items were granted
    assert "player_bottom_chinos" in player_state.inventory.clothing
    assert "player_shoes_leather" in player_state.inventory.clothing

    # Check tracking - only missing items should be tracked
    granted = player_state.outfit_granted_items.get("player_date_casual", set())
    assert "player_top_button_up" not in granted  # Was already owned
    assert "player_bottom_chinos" in granted      # Was granted
    assert "player_shoes_leather" in granted      # Was granted


@pytest.mark.asyncio
async def test_outfit_loss_removes_only_granted_items(engine_factory):
    """
    Test that losing an outfit only removes items that were originally granted.
    Items owned before outfit acquisition are retained.
    """
    engine = engine_factory("coffeeshop_date")
    await engine.start()

    state = engine.runtime.state_manager.state
    player_state = state.characters.get("player")

    # Clear inventory and add one item that player already owned
    player_state.inventory.clothing.clear()
    player_state.outfit_granted_items.clear()
    player_state.inventory.clothing["player_top_button_up"] = 1

    # Acquire outfit
    from app.models.effects import InventoryAddEffect, InventoryRemoveEffect
    add_effect = InventoryAddEffect(
        target="player",
        item_type="outfit",
        item="player_date_casual",
        count=1
    )
    engine.runtime.inventory_service.apply_effect(add_effect)

    # Verify all items present
    assert "player_top_button_up" in player_state.inventory.clothing
    assert "player_bottom_chinos" in player_state.inventory.clothing
    assert "player_shoes_leather" in player_state.inventory.clothing

    # Lose the outfit
    remove_effect = InventoryRemoveEffect(
        target="player",
        item_type="outfit",
        item="player_date_casual",
        count=1
    )
    engine.runtime.inventory_service.apply_effect(remove_effect)

    # Originally owned item should still be there
    assert "player_top_button_up" in player_state.inventory.clothing

    # Granted items should be removed
    assert "player_bottom_chinos" not in player_state.inventory.clothing
    assert "player_shoes_leather" not in player_state.inventory.clothing

    # Tracking should be cleared
    assert "player_date_casual" not in player_state.outfit_granted_items
