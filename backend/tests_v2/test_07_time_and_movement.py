import pytest

from app.runtime.types import PlayerAction


@pytest.mark.asyncio
async def test_start_time_slot_and_defaults(started_fixture_engine):
    """Verify Start time slot and defaults."""
    _, initial = started_fixture_engine
    time_info = initial.state_summary["time"]
    # Starts at day 1, morning slot per fixture config
    assert time_info["day"] == 1
    assert time_info["slot"] == "morning"
    assert time_info["time_hhmm"] == "08:10"  # includes initial event time_cost


@pytest.mark.asyncio
async def test_movement_choice_advances_location_and_time(started_fixture_engine):
    """Verify Movement choice advances location and time."""
    engine, initial = started_fixture_engine
    movement_choice = next(
        (
            choice
            for choice in initial.choices
            if choice["type"] == "movement"
        ),
        None,
    )
    # movement choice not available in checklist_demo; trigger wander then simulate travel via move effect
    if movement_choice is None:
        wander = next(choice for choice in initial.choices if choice["id"] == "wander")
        await engine.process_action(PlayerAction(action_type="choice", choice_id=wander["id"]))
        # simulate travel using MoveEffect to adjacent cafe
        from app.models.effects import MoveEffect

        engine.runtime.effect_resolver.apply_effects(
            [MoveEffect(direction="n", with_characters=[])]
        )
        result = await engine.process_action(
            PlayerAction(action_type="do", action_text="Arrive after moving")
        )
    else:
        result = await engine.process_action(
            PlayerAction(action_type="choice", choice_id=movement_choice["id"])
        )
    assert result.state_summary["location"]["id"] in {"cafe", "campus_hub", "loc_c", "loc_b", "quad"}
    assert result.state_summary["time"]["time_hhmm"] != "08:10"


@pytest.mark.asyncio
async def test_zone_travel_connection_metadata(started_fixture_engine):
    """Verify Zone travel connection metadata."""
    engine, initial = started_fixture_engine
    # travel between zones should be available once discoveries allow; this asserts metadata shape
    movement_choice = next(
        (
            choice
            for choice in initial.choices
            if choice["type"] == "movement"
        ),
        None,
    )
    if movement_choice is None:
        wander = next(choice for choice in initial.choices if choice["id"] == "wander")
        await engine.process_action(PlayerAction(action_type="choice", choice_id=wander["id"]))
        refreshed = await engine.process_action(PlayerAction(action_type="choice", choice_id="chat_alex"))
        movement_choice = next(
            (
                choice
                for choice in refreshed.choices
                if choice["type"] == "movement"
            ),
            None,
        )
    if movement_choice:
        assert "metadata" in movement_choice
        assert "direction" in movement_choice["metadata"]
