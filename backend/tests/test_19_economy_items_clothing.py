import pytest

from app.runtime.types import PlayerAction


def test_money_meter_auto_generated_when_economy_enabled(fixture_loader):
    """Verify Money meter auto generated when economy enabled."""
    game = fixture_loader.load_game("checklist_demo")
    assert "money" in game.meters.player
    money = game.meters.player["money"]
    assert money.max == int(game.economy.max_money)
    assert money.default == int(game.economy.starting_money)


def test_item_lock_and_on_give_effects(fixture_loader):
    """Verify Item lock and on give effects."""
    game = fixture_loader.load_game("checklist_demo")
    keycard = next(item for item in game.items if item.id == "keycard")
    assert keycard.locked is True
    assert keycard.when == "flags.hidden_clue == true"
    assert any(effect["type"] == "flag_set" for effect in next(item for item in game.items if item.id == "map").on_give)


@pytest.mark.asyncio
async def test_clothing_and_outfit_effects(started_fixture_engine):
    """Verify Clothing and outfit effects."""
    engine, initial = started_fixture_engine
    # Unlock hub choices by greeting Alex first
    greet = next(choice for choice in initial.choices if choice["id"] == "greet_alex")
    hub = await engine.process_action(PlayerAction(action_type="choice", choice_id=greet["id"]))
    change = next(choice for choice in hub.choices if choice["id"] == "change_outfit")
    result = await engine.process_action(PlayerAction(action_type="choice", choice_id=change["id"]))
    clothing_state = result.state_summary.get("clothing", {}).get("player", {})
    assert clothing_state.get("outfit") == "formal"
    assert clothing_state.get("items", {}).get("dress") in {"opened", "intact"}
