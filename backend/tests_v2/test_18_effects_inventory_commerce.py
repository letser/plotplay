import pytest

from app.runtime.types import PlayerAction


@pytest.mark.asyncio
async def test_inventory_give_effect_executes(started_fixture_engine):
    """Verify Inventory give effect executes."""
    engine, initial = started_fixture_engine
    greet = next(choice for choice in initial.choices if choice["id"] == "greet_alex")
    await engine.process_action(PlayerAction(action_type="choice", choice_id=greet["id"]))
    hub = await engine.process_action(PlayerAction(action_type="choice", choice_id="chat_alex"))
    give_choice = next(choice for choice in hub.choices if choice["id"] == "give_map")
    result = await engine.process_action(PlayerAction(action_type="choice", choice_id=give_choice["id"]))
    # map should be gone from player inventory and possibly held by alex
    inventory = result.state_summary["inventory"]
    assert inventory["player"].get("map", 0) == 0
    assert inventory.get("alex", {}).get("map", 0) >= 1


@pytest.mark.asyncio
async def test_shop_purchase_path(started_fixture_engine):
    """Verify Shop purchase path."""
    engine, initial = started_fixture_engine
    # take a deterministic choice to unlock cafe (greet alex)
    greet = next(choice for choice in initial.choices if choice["id"] == "greet_alex")
    await engine.process_action(PlayerAction(action_type="choice", choice_id=greet["id"]))
    hub = await engine.process_action(PlayerAction(action_type="do", action_text="Head toward the cafe"))
    movement_choice = next(choice for choice in hub.choices if choice["type"] == "movement")
    await engine.process_action(PlayerAction(action_type="choice", choice_id=movement_choice["id"]))
    # After moving, simulate a shop buy action
    buy_action = PlayerAction(
        action_type="shop_buy",
        item_id="coffee",
        target="player",
        extra={"source": "cafe", "count": 1},
    )
    result = await engine.process_action(buy_action)
    assert result.state_summary["inventory"]["player"].get("coffee", 0) >= 1


@pytest.mark.asyncio
async def test_item_use_applies_effects(started_fixture_engine):
    """Verify Item use applies effects."""
    engine, initial = started_fixture_engine
    # Ensure player has coffee, then use it
    engine.runtime.effect_resolver.apply_effects(
        [
            {"type": "inventory_add", "target": "player", "item_type": "item", "item": "coffee", "count": 1}
        ]
    )
    use_action = PlayerAction(action_type="use", item_id="coffee", target="player")
    state = engine.runtime.state_manager.state
    start_energy = state.characters["player"].meters["energy"]
    result = await engine.process_action(use_action)
    meters = result.state_summary["meters"]["player"]
    assert meters["energy"]["value"] == start_energy + 5
