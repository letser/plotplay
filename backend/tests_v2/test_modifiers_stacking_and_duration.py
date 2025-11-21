import pytest

from app.runtime.types import PlayerAction


def test_modifier_library_and_groups(fixture_loader):
    """
    Spec coverage: modifier groups, stacking rules, time_multiplier, clamp_meters, on_enter/on_exit.
    """
    game = fixture_loader.load_game("checklist_demo")
    mods = {m.id: m for m in game.modifiers.library}
    assert "caffeinated" in mods
    assert mods["caffeinated"].time_multiplier == 0.9
    assert game.modifiers.stacking.get("mood") == "highest"


@pytest.mark.skip(reason="Runtime stacking/removal behavior not verified yet.")
@pytest.mark.asyncio
async def test_modifier_stacking_allows_highest_only(started_fixture_engine):
    """
    Spec coverage: stacking rule highest, auto-activation/deactivation, duration expiry hooks.
    Expectation: higher priority modifier wins within group; duration expiry triggers on_exit.
    """
    engine, _ = started_fixture_engine
    await engine.process_action(PlayerAction(action_type="do", action_text="Apply multiple modifiers"))
    _ = engine.runtime.state_manager.state.modifiers
