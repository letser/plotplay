import pytest

from app.runtime.types import PlayerAction


@pytest.mark.asyncio
async def test_start_returns_choices_and_state(started_fixture_engine):
    """Verify Start returns choices and state."""
    engine, initial = started_fixture_engine
    assert initial.state_summary["location"]["id"] == "quad"
    assert initial.state_summary["location"]["zone"] == "campus"
    choice_ids = {choice["id"] for choice in initial.choices}
    # Greet Alex should be available from the intro node per fixture data
    assert "greet_alex" in choice_ids


@pytest.mark.asyncio
async def test_greeting_progresses_flags_and_arcs(started_fixture_engine):
    """Verify Greeting progresses flags and arcs."""
    engine, initial = started_fixture_engine
    greet_choice = next(choice for choice in initial.choices if choice["id"] == "greet_alex")
    result = await engine.process_action(
        PlayerAction(action_type="choice", choice_id=greet_choice["id"])
    )
    flags = engine.runtime.state_manager.state.flags
    assert flags.get("met_alex") is True
    arc_state = engine.runtime.state_manager.state.arcs.get("friendship")
    assert arc_state and arc_state.stage == "met"
    # Follow-up choices should reflect hub transitions once greeting completes
    followup_ids = {choice["id"] for choice in result.choices}
    assert "chat_alex" in followup_ids


@pytest.mark.asyncio
async def test_inventory_and_modifier_effects_apply_through_choices(started_fixture_engine):
    """Verify Inventory and modifier effects apply through choices."""
    engine, initial = started_fixture_engine
    # Move into chat_alex then give map to exercise inventory_give + apply_modifier + time advance
    chat_choice = next(choice for choice in initial.choices if choice["id"] == "greet_alex")
    await engine.process_action(PlayerAction(action_type="choice", choice_id=chat_choice["id"]))
    hub_result = await engine.process_action(
        PlayerAction(action_type="choice", choice_id="chat_alex")
    )
    give_choice = next(choice for choice in hub_result.choices if choice["id"] == "give_map")
    final_result = await engine.process_action(
        PlayerAction(action_type="choice", choice_id=give_choice["id"])
    )
    state_summary = final_result.state_summary
    player_inventory = state_summary["inventory"].get("player", {})
    # Map should have been given away
    assert player_inventory.get("map", 0) == 0
    # Modifier from chat node should be active on player
    assert "player" in state_summary.get("modifiers", {})
    assert "caffeinated" in state_summary["modifiers"]["player"]
