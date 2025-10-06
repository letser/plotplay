import pytest
import json
from unittest.mock import AsyncMock
from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine
from app.services.ai_service import AIResponse


@pytest.mark.asyncio
async def test_memory_extraction_and_persistence(mocker):
    """Test that memories are properly extracted and persisted across turns."""
    loader = GameLoader()
    game_def = loader.load_game('coffeeshop_date')
    engine = GameEngine(game_def, "test_memory")

    # Mock AI responses with memory field
    writer_response = AIResponse(content="Emma smiles and gives you her phone number.")
    checker_response = AIResponse(content=json.dumps({
        "memory": [
            "Emma shared her phone number with you",
            "You complimented Emma's coffee choice"
        ]
    }))

    mocker.patch.object(engine.ai_service, 'generate',
                        side_effect=[writer_response, checker_response])

    # Process action
    await engine.process_action(action_type="do", action_text="Ask for Emma's number")

    # Verify memories were extracted
    state = engine.state_manager.state
    assert len(state.memory_log) == 2
    assert "Emma shared her phone number with you" in state.memory_log
    assert "You complimented Emma's coffee choice" in state.memory_log


@pytest.mark.asyncio
async def test_memory_context_in_writer_prompt(mocker):
    """Test that memories are properly included in writer prompts."""
    loader = GameLoader()
    game_def = loader.load_game('coffeeshop_date')
    engine = GameEngine(game_def, "test_context")

    # Add some memories to state
    state = engine.state_manager.state
    state.memory_log = [
        "You met Emma at the coffee shop",
        "Emma ordered a cappuccino",
        "You sat by the window together",
        "Emma mentioned she likes jazz music"
    ]
    state.narrative_history = ["Recent narrative here"]

    # Build prompt and verify memory inclusion
    prompt = engine.prompt_builder.build_writer_prompt(
        state, "Continue conversation",
        engine._get_current_node(),
        state.narrative_history
    )

    # Check that older memories are included
    assert "Key Events:" in prompt
    assert "You met Emma at the coffee shop" in prompt
    assert "Emma ordered a cappuccino" in prompt


@pytest.mark.asyncio
async def test_memory_limit_enforcement(mocker):
    """Test that memory log is properly limited to prevent unbounded growth."""
    loader = GameLoader()
    game_def = loader.load_game('coffeeshop_date')
    engine = GameEngine(game_def, "test_limit")

    # Fill memory log beyond limit
    state = engine.state_manager.state
    for i in range(25):
        state.memory_log.append(f"Memory {i}")

    # Mock responses with new memories
    writer_response = AIResponse(content="Narrative")
    checker_response = AIResponse(content=json.dumps({
        "memory": ["New memory 1", "New memory 2"]
    }))

    mocker.patch.object(engine.ai_service, 'generate',
                        side_effect=[writer_response, checker_response])

    await engine.process_action(action_type="do", action_text="test")

    # Verify memory limit is enforced (should be 15 based on current implementation)
    assert len(state.memory_log) <= 15
    assert "New memory 1" in state.memory_log
    assert "New memory 2" in state.memory_log