import pytest

from app.runtime.types import PlayerAction


def test_money_meter_auto_generated_when_economy_enabled(fixture_loader):
    game = fixture_loader.load_game("checklist_demo")
    assert "money" in game.meters.player
    money = game.meters.player["money"]
    assert money.max == int(game.economy.max_money)
    assert money.default == int(game.economy.starting_money)


def test_item_lock_and_on_give_effects(fixture_loader):
    game = fixture_loader.load_game("checklist_demo")
    keycard = next(item for item in game.items if item.id == "keycard")
    assert keycard.locked is True
    assert keycard.when == "flags.hidden_clue == true"
    assert any(effect["type"] == "flag_set" for effect in next(item for item in game.items if item.id == "map").on_give)


@pytest.mark.asyncio
async def test_clothing_and_outfit_effects(started_fixture_engine):
    engine, initial = started_fixture_engine
    change = next(choice for choice in initial.choices if choice["id"] == "change_outfit")
    result = await engine.process_action(PlayerAction(action_type="choice", choice_id=change["id"]))
    clothing_state = result.state_summary.get("clothing", {}).get("player", {})
    assert clothing_state.get("outfit") == "formal"
    assert clothing_state.get("items", {}).get("dress") in {"opened", "intact"}
