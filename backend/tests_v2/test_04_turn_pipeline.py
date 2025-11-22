import pytest

from app.runtime.types import PlayerAction


@pytest.mark.asyncio
async def test_turn_initialization_increments_counter(started_fixture_engine):
    """Verify Turn initialization increments counter."""
    engine, initial = started_fixture_engine
    assert engine.runtime.state_manager.state.turn_count == 1
    await engine.process_action(PlayerAction(action_type="do", action_text="Look around again"))
    assert engine.runtime.state_manager.state.turn_count >= 2


@pytest.mark.asyncio
async def test_time_advances_and_visit_cap_respected(started_fixture_engine):
    """Verify Time advances and visit cap respected."""
    engine, _ = started_fixture_engine
    for _ in range(5):
        await engine.process_action(PlayerAction(action_type="do", action_text="Small talk"))
    state = engine.runtime.state_manager.state
    assert state.time.time_hhmm != "08:00"
    assert state.current_visit_minutes <= 45


@pytest.mark.asyncio
async def test_state_summary_contains_required_fields(started_fixture_engine):
    """Verify State summary contains required fields."""
    engine, initial = started_fixture_engine
    summary = initial.state_summary
    assert "turn" in summary
    assert "time" in summary
    assert "location" in summary
    assert "meters" in summary
    assert "inventory" in summary
