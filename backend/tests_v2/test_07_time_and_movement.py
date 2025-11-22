import pytest

from app.runtime.types import PlayerAction


@pytest.mark.asyncio
async def test_start_time_slot_and_defaults(started_fixture_engine):
    _, initial = started_fixture_engine
    time_info = initial.state_summary["time"]
    # Starts at day 1, morning slot per fixture config
    assert time_info["day"] == 1
    assert time_info["slot"] == "morning"
    assert time_info["time_hhmm"] == "08:00"


@pytest.mark.asyncio
async def test_movement_choice_advances_location_and_time(started_fixture_engine):
    engine, initial = started_fixture_engine
    movement_choice = next(choice for choice in initial.choices if choice["type"] == "movement")
    result = await engine.process_action(
        PlayerAction(action_type="choice", choice_id=movement_choice["id"])
    )
    # expect zone/location to reflect movement choice
    assert result.state_summary["location"]["id"] != "quad"
    # time should have progressed based on movement category (fixture uses travel)
    assert result.state_summary["time"]["time_hhmm"] != "08:00"


@pytest.mark.asyncio
async def test_zone_travel_connection_metadata(started_fixture_engine):
    engine, initial = started_fixture_engine
    # travel between zones should be available once discoveries allow; this asserts metadata shape
    movement_choice = next(choice for choice in initial.choices if choice["type"] == "movement")
    assert "metadata" in movement_choice
    assert "direction" in movement_choice["metadata"]
