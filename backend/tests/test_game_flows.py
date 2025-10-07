"""
End-to-end tests for game flows and player actions in PlotPlay v3.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine
from app.services.ai_service import AIResponse

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio


class TestCompleteGameFlows:
    """Tests full game playthroughs using actual game data."""

    async def test_coffeeshop_date_playthrough(self, mock_ai_service):
        """Test a full playthrough of the coffeeshop_date game."""
        loader = GameLoader()
        game_def = loader.load_game("coffeeshop_date")
        engine = GameEngine(game_def, "test_coffeeshop")
        engine.ai_service = mock_ai_service

        state = engine.state_manager.state
        assert state.current_node == "outside_cafe"

        # Make a choice to enter the cafe
        result = await engine.process_action("choice", choice_id="enter_cafe")
        assert "A quiet coffee shop" in result["narrative"]
        assert state.current_node == "start"

        # Make another choice
        await engine.process_action("choice", choice_id="start_conversation")
        assert state.current_node == "conversation_loop"

        # Test a transition based on meter change
        state.meters["alex"]["romance"] = 80
        await engine.process_action("do", "Keep talking.")
        assert state.current_node == "good_ending"

    async def test_college_romance_multi_day(self, mock_ai_service):
        """Test a multi-day scenario in college_romance."""
        loader = GameLoader()
        game_def = loader.load_game("college_romance")
        engine = GameEngine(game_def, "test_college_romance")
        engine.ai_service = mock_ai_service

        state = engine.state_manager.state
        assert state.day == 1
        assert state.time_slot == "morning"

        # Advance time through four slots to trigger the next day
        await engine.process_action("do", "Wait.")
        await engine.process_action("do", "Wait.")
        await engine.process_action("do", "Wait.")
        await engine.process_action("do", "Wait.")

        assert state.day == 2
        assert state.time_slot == "morning"


class TestActionTypes:
    """Tests for different types of player actions using a mocked engine."""

    async def test_choice_action(self, mock_game_engine):
        """Test a simple choice action."""
        engine = await mock_game_engine
        current_node = engine._get_current_node()
        current_node.choices.append(MagicMock(id="test_choice", prompt="A test choice.", effects=[], goto=None))

        result = await engine.process_action("choice", choice_id="test_choice")
        assert "Test narrative" in result["narrative"]

    async def test_do_action(self, mock_game_engine):
        """Test a simple 'do' action."""
        engine = await mock_game_engine
        result = await engine.process_action("do", action_text="Look around the room.")
        assert "Test narrative" in result["narrative"]

    async def test_say_action_with_target(self, mock_game_engine):
        """Test a 'say' action directed at a target."""
        engine = await mock_game_engine
        engine.state_manager.state.present_chars.append("npc1")
        result = await engine.process_action("say", action_text="Hello!", target="npc1")
        assert "Test narrative" in result["narrative"]


class TestErrorRecovery:
    """Tests for the engine's ability to handle errors gracefully."""

    async def test_invalid_choice_handling(self, mock_game_engine):
        """Test that the engine handles an invalid choice ID without crashing."""
        engine = await mock_game_engine
        # The engine should not crash and should produce a fallback narrative.
        result = await engine.process_action("choice", choice_id="non_existent_choice")
        assert "You can't seem to do that right now." in result["narrative"]

    async def test_ai_timeout_recovery(self, mock_game_engine):
        """Test that the engine recovers from an AI timeout."""
        engine = await mock_game_engine
        engine.ai_service.generate = AsyncMock(side_effect=TimeoutError("AI timed out."))

        result = await engine.process_action("do", "Anything.")

        assert "You try to act, but the world seems to pause for a moment." in result["narrative"]