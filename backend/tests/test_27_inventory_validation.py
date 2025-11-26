"""
Tests for inventory action validation (use/give with missing items).
"""
import pytest
from app.runtime.types import PlayerAction


@pytest.mark.asyncio
async def test_use_item_not_in_inventory(engine_factory):
    """
    Test that using an item not in inventory raises an error.
    """
    engine = engine_factory("coffeeshop_date")
    await engine.start()

    # Try to use an item the player doesn't have
    action = PlayerAction(action_type="use", item_id="vanilla_latte")

    with pytest.raises(ValueError, match="Cannot use item 'vanilla_latte': not in inventory"):
        await engine.process_action(action)


@pytest.mark.asyncio
async def test_give_item_not_in_inventory(engine_factory):
    """
    Test that giving an item not in inventory raises an error.
    """
    engine = engine_factory("coffeeshop_date")
    await engine.start()

    # Try to give an item the player doesn't have
    action = PlayerAction(action_type="give", item_id="vanilla_latte", target="alex")

    with pytest.raises(ValueError, match="Cannot give item 'vanilla_latte': not in inventory"):
        await engine.process_action(action)


@pytest.mark.asyncio
async def test_use_item_success(engine_factory):
    """
    Test that using an item in inventory succeeds.
    """
    engine = engine_factory("coffeeshop_date")
    result = await engine.start()

    # Player starts with a phone
    assert "phone" in result.state_summary["inventory"]["player"]

    # Use the phone (it's not consumable, so should still be there after)
    action = PlayerAction(action_type="use", item_id="phone")
    result = await engine.process_action(action)

    # Phone should still be in inventory (not consumable)
    assert "phone" in result.state_summary["inventory"]["player"]


@pytest.mark.asyncio
async def test_use_consumable_item_removes_from_inventory(engine_factory):
    """
    Test that using a consumable item removes it from inventory.
    """
    engine = engine_factory("coffeeshop_date")
    await engine.start()

    # Manually add the item for testing (since we're using mock AI that won't add it)
    state = engine.runtime.state_manager.state
    state.characters["player"].inventory.items["vanilla_latte"] = 1

    # Now use the vanilla latte
    use_action = PlayerAction(action_type="use", item_id="vanilla_latte")
    result = await engine.process_action(use_action)

    # Vanilla latte should be gone (consumable)
    assert "vanilla_latte" not in result.state_summary["inventory"]["player"]


@pytest.mark.asyncio
async def test_give_item_success(engine_factory):
    """
    Test that giving an item in inventory succeeds.
    """
    engine = engine_factory("coffeeshop_date")
    await engine.start()

    # Manually add an item for testing
    state = engine.runtime.state_manager.state
    state.characters["player"].inventory.items["vanilla_latte"] = 1

    # Give the latte to Alex
    action = PlayerAction(action_type="give", item_id="vanilla_latte", target="alex")
    result = await engine.process_action(action)

    # Player should no longer have the latte
    assert "vanilla_latte" not in result.state_summary["inventory"]["player"]

    # Alex should have it (check internal state since state_summary doesn't show NPC inventory)
    alex_state = engine.runtime.state_manager.state.characters.get("alex")
    assert alex_state.inventory.items.get("vanilla_latte", 0) == 1
