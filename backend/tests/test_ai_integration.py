"""
Tests for AI service integration and prompt building in PlotPlay v3.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from app.models.character import Character, Appearance, AppearanceBase
from app.core.game_engine import GameEngine
from app.services.prompt_builder import PromptBuilder
from app.services.ai_service import AIResponse

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio


class TestPromptBuilder:
    """Tests for the PromptBuilder class."""

    def test_writer_prompt_contains_all_sections(self, minimal_game_def, sample_game_state):
        """Verify the writer prompt has all the required markdown sections."""
        # Add more detail to the game def for a richer prompt
        player = minimal_game_def.characters[0]
        player.description = "A curious adventurer."
        player.appearance = Appearance(base=AppearanceBase(style=["practical"]))

        npc = Character(
            id="zara",
            name="Zara",
            age=30,
            gender="female",
            description="A mysterious merchant.",
            dialogue_style="Speaks in riddles."
        )
        minimal_game_def.characters.append(npc)
        sample_game_state.present_chars.append("zara")
        sample_game_state.memory_log.append("Zara seemed interested in the old map.")

        engine = GameEngine(minimal_game_def, "test_prompt")
        prompt_builder = PromptBuilder(minimal_game_def, engine.clothing_manager)
        current_node = engine._get_current_node()
        player_action = "Player asks Zara about the map."

        prompt = prompt_builder.build_writer_prompt(
            sample_game_state,
            player_action,
            current_node,
            sample_game_state.narrative_history,
            rng_seed=123
        )

        # Check for key markdown headers and content
        assert "**Game Title:** Test Game" in prompt
        assert "**PLAYER CHARACTER: Player**" in prompt
        assert "A curious adventurer." in prompt
        assert "**NON-PLAYER CHARACTERS**" in prompt
        assert "Zara (female)" in prompt
        assert "Speaks in riddles." in prompt
        assert "**CURRENT SITUATION**" in prompt
        assert "Location: Test Location" in prompt
        assert "Present: Player, Zara" in prompt
        assert "**MEMORY LOG**" in prompt
        assert "Zara seemed interested in the old map." in prompt
        assert "**Player's Action:**" in prompt
        assert "Player asks Zara about the map." in prompt
        assert "Continue the narrative." in prompt

    def test_checker_prompt_structure(self):
        """Verify the checker prompt is structured correctly."""
        prompt_builder = PromptBuilder(MagicMock(), MagicMock())
        ai_narrative = "You ask Zara about the map. She smiles enigmatically."
        player_action = "Player asks Zara about the map."

        prompt = prompt_builder.build_checker_prompt(ai_narrative, player_action, MagicMock())

        assert "You are the PlotPlay Checker" in prompt
        assert "[NARRATIVE TO CHECK]" in prompt
        assert ai_narrative in prompt
        assert "[PLAYER ACTION THAT PROMPTED THIS]" in prompt
        assert player_action in prompt
        assert "[TASK]" in prompt
        assert "Extract all concrete, factual state changes" in prompt


class TestAIServiceIntegration:
    """Tests for the GameEngine's interaction with the AI service."""

    async def test_engine_calls_writer_and_checker(self, mock_game_engine: GameEngine):
        """Test that process_action calls both writer and checker AIs."""
        await mock_game_engine.process_action("do", "Look around the room.")

        assert mock_game_engine.ai_service.generate.call_count >= 2

        first_call_args = mock_game_engine.ai_service.generate.call_args_list[0].args
        second_call_args = mock_game_engine.ai_service.generate.call_args_list[1].args

        assert "**Player's Action:**" in first_call_args[0]
        assert "Look around the room." in first_call_args[0]

        assert "[NARRATIVE TO CHECK]" in second_call_args[0]
        assert "Test narrative" in second_call_args[0]

    async def test_engine_applies_state_changes_from_checker(self, mock_game_engine: GameEngine):
        """Test that the engine correctly parses and applies state changes."""
        mock_game_engine.game_def.flags["found_secret_door"] = MagicMock(default=False)

        checker_response_json = json.dumps({
            "flag_changes": {
                "found_secret_door": True
            },
            "meter_changes": {
                "player": {"health": -5}
            }
        })

        mock_game_engine.ai_service.generate.side_effect = [
            AsyncMock(return_value=AIResponse(content="You find a secret door.")),
            AsyncMock(return_value=AIResponse(content=checker_response_json))
        ]

        initial_health = mock_game_engine.state_manager.state.meters["player"]["health"]

        await mock_game_engine.process_action("do", "Search the room.")

        state = mock_game_engine.state_manager.state

        assert state.flags.get("found_secret_door") is True
        assert state.meters["player"]["health"] == initial_health - 5

    async def test_engine_handles_invalid_checker_json(self, mock_game_engine: GameEngine):
        """Test that the engine logs a warning and continues if checker returns bad JSON."""
        invalid_json = '{"flag_changes": {"is_confused": true,}}' # Extra comma

        mock_game_engine.ai_service.generate.side_effect = [
            AsyncMock(return_value=AIResponse(content="Something confusing happens.")),
            AsyncMock(return_value=AIResponse(content=invalid_json))
        ]

        result = await mock_game_engine.process_action("do", "Touch the weird orb.")

        assert "Something confusing happens." in result["narrative"]

        state = mock_game_engine.state_manager.state
        assert state.flags.get("is_confused") is None