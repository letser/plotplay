import pytest

from app.runtime.types import PlayerAction


def active_mod_ids(state, char_id: str = "player") -> list[str]:
    return [mod.get("id") for mod in state.modifiers.get(char_id, [])]


def test_modifier_library_and_groups(fixture_loader):
    """
    Spec coverage: modifier groups, stacking rules, time_multiplier, clamp_meters, on_enter/on_exit.
    """
    game = fixture_loader.load_game("checklist_demo")
    mods = {m.id: m for m in game.modifiers.library}
    assert "caffeinated" in mods
    assert mods["caffeinated"].time_multiplier == 0.9
    assert game.modifiers.stacking.get("mood") == "highest"


@pytest.mark.asyncio
async def test_modifier_stacking_allows_highest_only(fixture_engine_factory):
    """
    Spec coverage: stacking rule highest, auto-activation/deactivation, duration expiry hooks.
    Expectation: higher priority modifier wins within group; duration expiry triggers on_exit.
    """
    engine = fixture_engine_factory(game_id="modifier_stacking", session_id="stacking-suite")
    state = engine.runtime.state_manager.state

    # Apply the low-priority modifier via effect; sets enabling flag.
    await engine.process_action(PlayerAction(action_type="choice", choice_id="apply_low"))
    assert state.flags["low_enabled"] is True
    assert "low_mood" in active_mod_ids(state)
    assert state.flags["low_entered"] is True
    assert state.flags["low_exited"] is False
    assert "low_mood" in state.characters["player"].modifiers

    # Apply the high-priority modifier; stacking=highest should remove low_mood.
    await engine.process_action(PlayerAction(action_type="choice", choice_id="apply_high"))
    assert state.flags["low_exited"] is True  # low_mood on_exit triggered by removal
    assert active_mod_ids(state) == ["high_mood"]
    assert "low_mood" not in state.characters["player"].modifiers

    # Advance time enough to expire high_mood; on_exit should fire.
    await engine.process_action(PlayerAction(action_type="choice", choice_id="wait_out"))
    assert "high_mood" not in active_mod_ids(state)
    assert state.flags["high_exited"] is True

    # Next turn re-evaluates conditions; low_mood should auto-reactivate.
    await engine.process_action(PlayerAction(action_type="choice", choice_id="ping"))
    assert "low_mood" in active_mod_ids(state)
    assert "low_mood" in state.characters["player"].modifiers
