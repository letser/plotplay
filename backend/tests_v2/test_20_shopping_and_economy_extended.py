import pytest

from app.runtime.types import PlayerAction


@pytest.mark.skip(reason="Shop price calculations and resell logic not yet implemented in runtime.")
@pytest.mark.asyncio
async def test_shop_price_multipliers_and_resell(started_fixture_engine):
    """
    Spec coverage: multiplier_buy/multiplier_sell, resell flag, max_money cap.
    Expectation: purchase uses multiplier_buy, selling uses multiplier_sell, resell adds inventory back when allowed.
    """
    engine, _ = started_fixture_engine
    buy = PlayerAction(action_type="shop_buy", item_id="coffee", target="player", extra={"source": "cafe", "count": 1})
    await engine.process_action(buy)
    sell = PlayerAction(action_type="shop_sell", item_id="coffee", target="cafe", extra={"source": "player", "count": 1})
    await engine.process_action(sell)


@pytest.mark.skip(reason="Money cap and economy enabled/disabled toggles not yet enforced.")
def test_economy_caps_and_disabled_mode(fixture_loader):
    """
    Spec coverage: economy.enabled toggle, starting_money, max_money enforcement.
    Expectation: when disabled, purchase effects rejected; when enabled, money meter respects max_money.
    """
    game = fixture_loader.load_game("checklist_demo")
    assert game.economy.enabled is True
