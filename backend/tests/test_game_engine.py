"""
Integration tests for the v3 GameEngine, including AI systems.
"""
import pytest
import json
from unittest.mock import AsyncMock
from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine
from app.services.ai_service import AIResponse
from app.models.location import LocationPrivacy


# --- SIMPLEST TESTS FIRST ---

@pytest.mark.asyncio
async def test_engine_processes_choice_and_updates_state(mocker):
    """
    Tests the core, non-AI game loop: processes a choice and verifies state change.
    """
    loader = GameLoader()
    game_def = loader.load_game('coffeeshop_date')
    engine = GameEngine(game_def, "test_session_engine")

    writer_response = AIResponse(content="Placeholder narrative.")
    checker_response = AIResponse(content=json.dumps({}))
    mocker.patch.object(engine.ai_service, 'generate', side_effect=[writer_response, checker_response])

    await engine.process_action(action_type="choice", choice_id="confident_greeting")
    final_state = engine.state_manager.state
    assert final_state.meters["player"]["confidence"] == 60
    assert final_state.current_node == "conversation_1"
    print("\n✅ GameEngine correctly processed a choice and updated state.")

@pytest.mark.asyncio
async def test_conditional_choice_visibility():
    """
    Tests that a conditional choice is only shown when its condition is met.
    """
    loader = GameLoader()
    game_def = loader.load_game('coffeeshop_date')
    engine = GameEngine(game_def, "test_session_conditional")
    engine.state_manager.state.current_node = "order_coffee"

    choices_with_money = engine._generate_choices(engine._get_current_node(), [])
    assert "pay_for_both" in {c["id"] for c in choices_with_money}

    engine.state_manager.state.meters["player"]["money"] = 5
    choices_without_money = engine._generate_choices(engine._get_current_node(), [])
    assert "pay_for_both" not in {c["id"] for c in choices_without_money}
    print("\n✅ GameEngine correctly handled conditional choice visibility.")

# --- MORE COMPLEX DYNAMIC SYSTEMS ---

@pytest.mark.asyncio
async def test_event_triggers_and_applies_effects(mocker):
    """
    Tests that the EventManager triggers an event and its choices are processed.
    """
    loader = GameLoader()
    game_def = loader.load_game('college_romance')
    engine = GameEngine(game_def, "test_session_events")
    engine.state_manager.state.location_current = "gym"
    engine.state_manager.state.location_privacy = LocationPrivacy.LOW
    engine.state_manager.state.present_chars = ["liam"]

    writer_response = AIResponse(content="Placeholder narrative.")
    checker_response = AIResponse(content=json.dumps({}))
    mocker.patch.object(engine.ai_service, 'generate', side_effect=[writer_response, checker_response, writer_response, checker_response])

    response = await engine.process_action(action_type="do", action_text="look around")
    assert "Liam is at the gym, waving you over" in response["narrative"]
    assert "join_workout" in {c['id'] for c in response['choices']}

    await engine.process_action(action_type="choice", choice_id="join_workout")

    final_body = engine.state_manager.state.meters["player"]["body"]
    assert final_body == 40
    print("\n✅ GameEngine correctly triggered an event and processed its choice.")

@pytest.mark.asyncio
async def test_arc_advances_when_condition_met(mocker):
    """
    Tests that the ArcManager correctly advances an arc to the next stage.
    """
    loader = GameLoader()
    game_def = loader.load_game('college_romance')
    engine = GameEngine(game_def, "test_session_arcs")
    engine.state_manager.state.meters["player"]["mind"] = 61

    writer_response = AIResponse(content="Placeholder narrative.")
    checker_response = AIResponse(content=json.dumps({}))
    mocker.patch.object(engine.ai_service, 'generate', side_effect=[writer_response, checker_response])

    await engine.process_action(action_type="do", action_text="study")
    assert "study_hard" in engine.state_manager.state.completed_milestones
    print("\n✅ GameEngine correctly advanced an arc.")

@pytest.mark.asyncio
async def test_ai_reconciliation_overrides_narrative(mocker):
    """
    Tests that the reconciliation logic overrides the Writer's narrative
    when a consent gate is violated.
    """
    loader = GameLoader()
    game_def = loader.load_game('college_romance')
    engine = GameEngine(game_def, "test_session_reconciliation")
    engine.state_manager.state.present_chars = ["emma"]

    writer_response = AIResponse(content="Emma's eyes light up and she kisses you passionately.")
    checker_response = AIResponse(content=json.dumps({ "flag_changes": {} }))
    mocker.patch.object(engine.ai_service, 'generate', side_effect=[writer_response, checker_response])

    response = await engine.process_action(
        action_type="do", action_text="kiss emma", target="emma"
    )

    expected_refusal = "She pulls back, cheeks warm. 'Not yet.'"
    assert response["narrative"] == expected_refusal
    print("\n✅ GameEngine correctly reconciled AI narrative with game rules.")

@pytest.mark.asyncio
async def test_engine_handles_movement_action():
    """
    Tests that the engine correctly handles a movement action,
    updates location, and consumes time.
    """
    loader = GameLoader()
    game_def = loader.load_game('coffeeshop_date')
    engine = GameEngine(game_def, "test_session_movement")

    # --- Initial State Assertions ---
    initial_state = engine.state_manager.state
    assert initial_state.location_current == "coffee_shop"
    assert initial_state.actions_this_slot == 0

    # --- Process a Movement Action ---
    # We use a choice_id that starts with "move_"
    await engine.process_action(action_type="choice", choice_id="move_outside")

    # --- Final State Assertions ---
    final_state = engine.state_manager.state
    assert final_state.location_current == "outside"
    assert final_state.location_previous == "coffee_shop"
    assert final_state.actions_this_slot == 1, "Movement should consume one action point."

    print("\n✅ GameEngine correctly handled a movement action.")