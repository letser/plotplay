import pytest

from app.runtime.types import PlayerAction


@pytest.mark.skip(reason="Time decay per slot/day not yet exposed by runtime state.")
@pytest.mark.asyncio
async def test_meter_decay_over_slots_and_days(started_fixture_engine):
    """
    Spec coverage: meter decay per slot/day, slot rollover, weekday progression.
    Expectation: decay_per_slot/day applied and weekday increments after 1440 minutes.
    """
    engine, _ = started_fixture_engine
    for _ in range(6):
        await engine.process_action(PlayerAction(action_type="do", action_text="Advance slot"))
    state = engine.runtime.state_manager.state
    _ = state.time.slot


@pytest.mark.skip(reason="Time multiplier stacking/clamp not yet verified in runtime.")
@pytest.mark.asyncio
async def test_time_multiplier_stacking_and_clamp(started_fixture_engine):
    """
    Spec coverage: modifiers time_multiplier multiplicative clamp to [0.5, 2.0].
    Expectation: overlapping modifiers capped and applied to action time costs.
    """
    engine, _ = started_fixture_engine
    await engine.process_action(PlayerAction(action_type="do", action_text="Apply time modifiers"))
    state = engine.runtime.state_manager.state
    _ = state.current_visit_minutes


@pytest.mark.skip(reason="Visit cap enforcement not yet surfaced for assertions.")
@pytest.mark.asyncio
async def test_visit_cap_prevents_excess_time(started_fixture_engine):
    """
    Spec coverage: cap_per_visit for conversation/default actions.
    Expectation: accumulated minutes in a node do not exceed cap, resets on transition.
    """
    engine, _ = started_fixture_engine
    for _ in range(10):
        await engine.process_action(PlayerAction(action_type="do", action_text="Chat loop"))
    state = engine.runtime.state_manager.state
    _ = state.current_visit_minutes
