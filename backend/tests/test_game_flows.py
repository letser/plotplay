"""
End-to-end game flow tests for PlotPlay v3.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock
from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine
from app.services.ai_service import AIResponse


class TestCompleteGameFlows:
    """Test complete game scenarios end-to-end."""

    @pytest.mark.asyncio
    async def test_coffeeshop_date_playthrough(self, mocker):
        """Test a complete playthrough of the coffeeshop date game."""
        loader = GameLoader()
        game_def = loader.load_game("coffeeshop_date")
        engine = GameEngine(game_def, "test_coffeeshop_flow")

        # Mock AI responses for consistent testing
        writer_responses = [
            AIResponse(content="You walk into the coffee shop confidently."),
            AIResponse(content="Emma smiles at your greeting."),
            AIResponse(content="You both order coffee together."),
            AIResponse(content="The conversation flows naturally."),
        ]

        checker_responses = [
            AIResponse(content=json.dumps({
                "meter_changes": {"player": {"confidence": 10}},
                "memory": ["Met Emma at the coffee shop"]
            })),
            AIResponse(content=json.dumps({
                "meter_changes": {"emma": {"trust": 5}},
                "memory": ["Emma responded well to greeting"]
            })),
            AIResponse(content=json.dumps({
                "meter_changes": {"player": {"money": -10}},
                "flag_changes": {"coffee_ordered": True}
            })),
            AIResponse(content=json.dumps({
                "meter_changes": {"emma": {"trust": 10, "attraction": 5}},
                "memory": ["Had a great conversation with Emma"]
            }))
        ]

        # Interleave writer and checker responses
        all_responses = []
        for w, c in zip(writer_responses, checker_responses):
            all_responses.extend([w, c])

        mocker.patch.object(engine.ai_service, 'generate',
                            side_effect=all_responses)

        # Start game
        state = engine.state_manager.state
        assert state.current_node == "start"

        # Make confident greeting
        response = await engine.process_action(
            action_type="choice",
            choice_id="confident_greeting"
        )

        assert state.current_node == "conversation_1"
        assert state.meters["player"]["confidence"] > 50
        assert "Met Emma at the coffee shop" in state.memory_log

        # Continue conversation
        response = await engine.process_action(
            action_type="do",
            action_text="compliment Emma's choice of coffee"
        )

        assert state.meters["emma"]["trust"] > 30

        # Order coffee
        response = await engine.process_action(
            action_type="choice",
            choice_id="pay_for_both"
        )

        assert state.flags.get("coffee_ordered") is True
        assert state.meters["player"]["money"] < 50

        # Have conversation
        response = await engine.process_action(
            action_type="say",
            action_text="Tell me about your favorite coffee shops",
            target="emma"
        )

        assert state.meters["emma"]["attraction"] > 40
        assert len(state.memory_log) >= 3

    @pytest.mark.asyncio
    async def test_college_romance_multi_day(self, mocker):
        """Test multi-day progression in college romance."""
        loader = GameLoader()
        game_def = loader.load_game("college_romance")
        engine = GameEngine(game_def, "test_college_flow")

        # Mock simplified AI responses
        async def mock_generate(*args, **kwargs):
            return AIResponse(content=json.dumps({}))

        mocker.patch.object(engine.ai_service, 'generate',
                            side_effect=mock_generate)

        state = engine.state_manager.state

        # Day 1 - Morning
        assert state.day == 1
        assert state.time_slot == "morning"

        # Go to class
        state.location_current = "classroom"
        response = await engine.process_action(
            action_type="wait"
        )

        assert state.time_slot == "afternoon"

        # Study in afternoon
        response = await engine.process_action(
            action_type="do",
            action_text="study for upcoming exam"
        )

        # Evening - social time
        response = await engine.process_action(
            action_type="wait"
        )
        assert state.time_slot == "evening"

        # Night - sleep
        response = await engine.process_action(
            action_type="wait"
        )
        assert state.time_slot == "night"

        # Should advance to Day 2
        response = await engine.process_action(
            action_type="wait"
        )
        assert state.day == 2
        assert state.time_slot == "morning"

    @pytest.mark.asyncio
    async def test_save_and_load_mid_game(self, tmp_path, mocker):
        """Test saving and loading game state mid-playthrough."""
        loader = GameLoader()
        game_def = loader.load_game("coffeeshop_date")
        engine = GameEngine(game_def, "test_save_load")

        # Mock AI
        mocker.patch.object(engine.ai_service, 'generate',
                            return_value=AIResponse(content="Test"))

        # Play a bit
        state = engine.state_manager.state
        state.meters["emma"]["trust"] = 65
        state.flags["first_meeting"] = True
        state.memory_log = ["Met Emma", "Had coffee"]
        state.narrative_history = ["Story so far..."]
        state.current_node = "conversation_2"

        # Save game
        save_file = tmp_path / "test_save.json"
        engine.state_manager.save_state(str(save_file))

        # Create new engine and load
        new_engine = GameEngine(game_def, "test_save_load_new")
        new_engine.state_manager.load_state(str(save_file))

        new_state = new_engine.state_manager.state

        # Verify everything was restored
        assert new_state.meters["emma"]["trust"] == 65
        assert new_state.flags["first_meeting"] is True
        assert "Met Emma" in new_state.memory_log
        assert "Story so far..." in new_state.narrative_history
        assert new_state.current_node == "conversation_2"


class TestActionTypes:
    """Test all different action types."""

    @pytest.mark.asyncio
    async def test_choice_action(self, mock_game_engine):
        """Test choice action processing."""
        engine = mock_game_engine

        # Add a choice to current node
        from app.models.node import Choice
        current_node = engine._get_current_node()
        current_node.choices = [
            Choice(
                id="test_choice",
                text="Test Choice",
                to="start_node",
                effects=[
                    MeterChangeEffect(
                        target="player",
                        meter="energy",
                        op="add",
                        value=10
                    )
                ]
            )
        ]

        response = await engine.process_action(
            action_type="choice",
            choice_id="test_choice"
        )

        assert engine.state_manager.state.meters["player"]["energy"] == 85
        assert "choices" in response

    @pytest.mark.asyncio
    async def test_do_action(self, mock_game_engine):
        """Test 'do' action processing."""
        engine = mock_game_engine

        response = await engine.process_action(
            action_type="do",
            action_text="examine the room carefully"
        )

        assert "narrative" in response
        assert response["action_type"] == "do"
        # Verify it was processed through AI
        engine.ai_service.generate.assert_called()

    @pytest.mark.asyncio
    async def test_say_action_with_target(self, mock_game_engine):
        """Test 'say' action with target NPC."""
        engine = mock_game_engine
        engine.state_manager.state.present_chars = ["emma"]

        response = await engine.process_action(
            action_type="say",
            action_text="How are you today?",
            target="emma"
        )

        assert response["action_type"] == "say"
        assert response.get("target") == "emma"

    @pytest.mark.asyncio
    async def test_wait_action(self, mock_game_engine):
        """Test wait action advances time."""
        engine = mock_game_engine
        engine.game_def.time.slots = ["morning", "afternoon", "evening"]

        initial_slot = engine.state_manager.state.time_slot

        response = await engine.process_action(
            action_type="wait"
        )

        # Time should advance
        new_slot = engine.state_manager.state.time_slot
        assert new_slot != initial_slot or engine.state_manager.state.day > 1


class TestErrorRecovery:
    """Test error handling and recovery."""

    @pytest.mark.asyncio
    async def test_invalid_choice_handling(self, mock_game_engine):
        """Test handling of invalid choice IDs."""
        engine = mock_game_engine

        response = await engine.process_action(
            action_type="choice",
            choice_id="non_existent_choice"
        )

        # Should handle gracefully
        assert "error" in response or "narrative" in response
        # State should not be corrupted
        assert engine.state_manager.state.current_node == "start_node"

    @pytest.mark.asyncio
    async def test_missing_node_reference(self, minimal_game_def):
        """Test handling of missing node references."""
        from app.models.node import Node, Transition

        # Add node with bad transition
        minimal_game_def.nodes.append(
            Node(
                id="bad_node",
                type="normal",
                transitions=[
                    Transition(
                        to="missing_node",
                        type="auto"
                    )
                ]
            )
        )

        engine = GameEngine(minimal_game_def, "test_missing")
        engine.state_manager.state.current_node = "bad_node"

        # Should not crash when trying to transition
        with pytest.raises(ValueError):
            engine._get_current_node()

    @pytest.mark.asyncio
    async def test_ai_timeout_recovery(self, mock_game_engine):
        """Test recovery from AI service timeout."""
        engine = mock_game_engine

        # Simulate timeout
        engine.ai_service.generate.side_effect = TimeoutError("AI timeout")

        response = await engine.process_action(
            action_type="do",
            action_text="test action"
        )

        # Should provide fallback response
        assert "narrative" in response
        # Game should remain playable
        assert engine.state_manager.state is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])