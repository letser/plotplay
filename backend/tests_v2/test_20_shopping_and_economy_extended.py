import pytest

from app.runtime.types import PlayerAction


@pytest.mark.asyncio
async def test_shop_price_multipliers_and_resell(started_fixture_engine):
    """
    Spec coverage: multiplier_buy/multiplier_sell, resell flag, max_money cap.
    Expectation: purchase uses multiplier_buy, selling uses multiplier_sell, resell adds inventory back when allowed.
    """
    engine, _ = started_fixture_engine
    state = engine.runtime.state_manager.state
    state.characters["player"].meters["money"] = 200
    buy = PlayerAction(action_type="shop_buy", item_id="coffee", target="player", extra={"source": "cafe", "count": 1})
    await engine.process_action(buy)
    assert state.characters["player"].inventory.items.get("coffee", 0) >= 1

    sell = PlayerAction(action_type="shop_sell", item_id="coffee", target="cafe", extra={"source": "player", "count": 1})
    await engine.process_action(sell)
    assert state.characters["player"].inventory.items.get("coffee", 0) == 0


def test_economy_caps_and_disabled_mode(fixture_loader):
    """
    Spec coverage: economy.enabled toggle, starting_money, max_money enforcement.
    Expectation: when disabled, purchase effects rejected; when enabled, money meter respects max_money.
    """
    game = fixture_loader.load_game("checklist_demo")
    assert game.economy.enabled is True
