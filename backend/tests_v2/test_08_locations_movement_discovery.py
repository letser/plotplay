import pytest

from app.runtime.types import PlayerAction


def test_discovery_rules_defined(fixture_loader):
    """Verify Discovery rules defined."""
    game = fixture_loader.load_game("checklist_demo")
    campus = next(zone for zone in game.zones if zone.id == "campus")
    assert campus.access.discovered is True
    cafe = next(loc for loc in campus.locations if loc.id == "cafe")
    assert cafe.access.discovered is False
    assert cafe.access.discovered_when == "flags.met_alex == true"


@pytest.mark.asyncio
async def test_movement_choice_includes_direction(started_fixture_engine):
    """Verify Movement choice includes direction."""
    _, initial = started_fixture_engine
    movement_choice = next(choice for choice in initial.choices if choice["type"] == "movement")
    assert "metadata" in movement_choice
    assert movement_choice["metadata"].get("direction") is not None


@pytest.mark.asyncio
async def test_zone_travel_and_discovery_progression(started_fixture_engine):
    """Verify Zone travel and discovery progression."""
    engine, initial = started_fixture_engine
    greet = next(choice for choice in initial.choices if choice["id"] == "greet_alex")
    await engine.process_action(PlayerAction(action_type="choice", choice_id=greet["id"]))
    hub_turn = await engine.process_action(PlayerAction(action_type="do", action_text="Look around the hub"))
    movement_choice = next(choice for choice in hub_turn.choices if choice["type"] == "movement")
    await engine.process_action(PlayerAction(action_type="choice", choice_id=movement_choice["id"]))
    state = engine.runtime.state_manager.state
    assert "cafe" in state.discovered_locations
