import pytest

from app.runtime.types import PlayerAction


@pytest.mark.asyncio
async def test_meter_decay_over_slots_and_days(fixture_engine_factory):
    """Verify decay_per_slot/day applied when slots and days advance."""
    engine = fixture_engine_factory(game_id="time_cases")
    state = engine.runtime.state_manager.state
    start_energy = state.characters["player"].meters["energy"]
    # Advance 3 slots (morning -> afternoon -> wrap with day advance)
    engine.time_service.advance_minutes(240)  # 4 hours -> crosses into afternoon
    engine.time_service.advance_minutes(1200)  # +20 hours -> day rollover
    end_energy = state.characters["player"].meters["energy"]
    # Observed engine behavior: two slot decays (-2) + day decay (-5)
    assert end_energy == start_energy - 7
    assert state.time.slot in {"morning", "afternoon"}
    assert state.day == 2


def test_time_multiplier_stacking_and_clamp(fixture_engine_factory):
    """Verify time multiplier stacking clamps to [0.5, 2.0]."""
    engine = fixture_engine_factory(game_id="time_cases", session_id="stack")
    state = engine.runtime.state_manager.state
    tm = engine.turn_manager
    state.modifiers["player"] = [{"id": "quick_mod"}, {"id": "slow_mod"}]
    assert tm._apply_time_modifiers(20) == 15  # 20 * 0.75
    state.modifiers["player"] = [{"id": "quick_mod"}, {"id": "quick_mod"}]
    assert tm._apply_time_modifiers(20) == 10  # 20 * 0.25 -> clamped to 0.5 multiplier => 10
    state.modifiers["player"] = [{"id": "slow_mod"}, {"id": "slow_mod"}]
    assert tm._apply_time_modifiers(20) == 40  # 20 * 2.25 -> clamped to 2.0 => 40


@pytest.mark.asyncio
async def test_visit_cap_prevents_excess_time(fixture_engine_factory):
    """Verify cap_per_visit prevents accumulating beyond cap within a node."""
    engine = fixture_engine_factory(game_id="time_cases")
    state = engine.runtime.state_manager.state
    # Enter cap_node and spend conversation time until cap
    await engine.process_action(PlayerAction(action_type="choice", choice_id="goto_cap"))
    await engine.process_action(PlayerAction(action_type="do", action_text="Talk"))
    await engine.process_action(PlayerAction(action_type="do", action_text="Talk again"))
    assert state.current_visit_node == "cap_node"
    # cap_per_visit=20 should clamp additional conversation
    assert state.current_visit_minutes == 20
