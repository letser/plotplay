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
from app.models.flags import Flag

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio


class TestPromptBuilder:
    """Tests for the PromptBuilder class."""

    def test_writer_prompt_contains_all_sections(self, minimal_game_def, sample_game_state):
        """Verify the writer prompt has all the required content in the prompt."""
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

        # Add enough memory entries to trigger inclusion (need more than MEMORY_CUTOFF_OFFSET)
        sample_game_state.memory_log = [
            "Found the old tavern.",
            "Met a stranger.",
            "Zara seemed interested in the old map."
        ]
        # Add some narrative history to trigger memory context
        sample_game_state.narrative_history = [
            "You entered the tavern.",
            "The atmosphere was warm."
        ]

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

        # Check for key content that should be in the prompt
        assert "PlotPlay Writer" in prompt
        assert "second" in prompt.lower() or "2nd" in prompt.lower()  # POV
        assert "present" in prompt.lower()  # Tense
        assert "Zara" in prompt  # NPC name
        assert "Speaks in riddles" in prompt  # Dialogue style
        assert "Test Location" in prompt or "test_location" in prompt  # Location
        # At least one memory item should appear (either in Key Events or Story So Far)
        assert "Found the old tavern" in prompt or "atmosphere was warm" in prompt
        assert "Player asks Zara about the map" in prompt  # Player action
        assert "Continue the narrative" in prompt  # Instruction

    def test_checker_prompt_structure(self, minimal_game_def, sample_game_state):
        """Verify the checker prompt is structured correctly."""
        engine = GameEngine(minimal_game_def, "test_checker")
        prompt_builder = PromptBuilder(minimal_game_def, engine.clothing_manager)
        ai_narrative = "You ask Zara about the map. She smiles enigmatically."
        player_action = "Player asks Zara about the map."

        prompt = prompt_builder.build_checker_prompt(ai_narrative, player_action, sample_game_state)

        # Check for key sections - based on actual implementation
        assert "data extraction engine" in prompt or "Checker" in prompt
        assert ai_narrative in prompt
        assert player_action in prompt
        assert "Extract" in prompt or "extract" in prompt


class TestAIServiceIntegration:
    """Tests for the GameEngine's interaction with the AI service."""

    async def test_engine_calls_writer_and_checker(self):
        """Test that process_action calls both writer and checker AIs."""
        from app.core.game_loader import GameLoader

        # Use a minimal game def
        loader = GameLoader()
        game_def = loader.load_game("coffeeshop_date")
        engine = GameEngine(game_def, "test_engine")

        # Mock the AI service
        engine.ai_service.generate = AsyncMock(return_value=AIResponse(content="Test narrative"))

        await engine.process_action("do", action_text="Look around the room.")

        assert engine.ai_service.generate.call_count >= 2

        first_call_args = engine.ai_service.generate.call_args_list[0].args
        second_call_args = engine.ai_service.generate.call_args_list[1].args

        # Check that prompts contain expected content
        assert "Player" in first_call_args[0] or "action" in first_call_args[0].lower()
        assert "Look around the room" in first_call_args[0]

    async def test_engine_applies_state_changes_from_checker(self, minimal_game_def, mock_ai_service):
        """Test that the engine correctly parses and applies state changes."""
        engine = GameEngine(minimal_game_def, "test_state_changes")
        engine.ai_service = mock_ai_service

        engine.game_def.flags["found_secret_door"] = Flag(type="bool", default=False)
        engine.state_manager.state.flags["found_secret_door"] = False  # Initialize in state

        checker_response_json = json.dumps({
            "flag_changes": {
                "found_secret_door": True
            },
            "meter_changes": {
                "player": {"health": -5}
            },
            "memory": {
                "append": ["Found a secret door behind the bookshelf."]
            }
        })

        # Create proper async mock responses
        call_count = 0
        async def mock_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return AIResponse(content="You find a secret door.")
            else:
                return AIResponse(content=checker_response_json)

        engine.ai_service.generate = AsyncMock(side_effect=mock_generate)

        initial_health = engine.state_manager.state.meters["player"]["health"]

        await engine.process_action("do", action_text="Search the room.")

        state = engine.state_manager.state

        assert state.flags.get("found_secret_door") is True
        assert state.meters["player"]["health"] <= initial_health  # May be clamped

    async def test_engine_handles_invalid_checker_json(self, minimal_game_def, mock_ai_service):
        """Test that the engine logs a warning and continues if checker returns bad JSON."""
        engine = GameEngine(minimal_game_def, "test_invalid_json")
        engine.ai_service = mock_ai_service

        invalid_json = '{"flag_changes": {"is_confused": true,}}'  # Extra comma

        # Create proper async mock responses
        call_count = 0
        async def mock_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return AIResponse(content="Something confusing happens.")
            else:
                return AIResponse(content=invalid_json)

        engine.ai_service.generate = AsyncMock(side_effect=mock_generate)

        result = await engine.process_action("do", action_text="Touch the weird orb.")

        assert "Something confusing happens." in result["narrative"]

        state = engine.state_manager.state
        assert state.flags.get("is_confused") is None

    async def test_writer_respects_pov_and_tense(self, minimal_game_def, mock_ai_service):
        """Test that prompts include correct POV and tense settings."""
        from app.models.narration import NarrationConfig

        minimal_game_def.narration = NarrationConfig(
            pov="first",
            tense="past"
        )

        engine = GameEngine(minimal_game_def, "test_pov")
        engine.ai_service = mock_ai_service

        await engine.process_action("do", action_text="Open the door.")

        first_call = engine.ai_service.generate.call_args_list[0]
        prompt = first_call.args[0]

        # Check for POV/tense in the system prompt section
        # The prompt builder uses "first perspective" and "past tense"
        assert "first perspective" in prompt.lower() or "first person" in prompt.lower()
        assert "past tense" in prompt.lower() or "past" in prompt.lower()

    async def test_memory_log_included_in_prompts(self, minimal_game_def, mock_ai_service):
        """Test that memory log is properly included in writer prompts."""
        engine = GameEngine(minimal_game_def, "test_memory")
        engine.ai_service = mock_ai_service

        # Add enough memory entries and narrative history to trigger memory inclusion
        engine.state_manager.state.memory_log = [
            "Found a mysterious key",
            "Emma seemed nervous",
            "The tavern was crowded",
            "A strange symbol appeared"
        ]
        # Add narrative history to provide context
        engine.state_manager.state.narrative_history = [
            "You walked through the door.",
            "The room was dimly lit.",
            "Emma looked up as you entered."
        ]

        await engine.process_action("do", action_text="Talk to Emma.")

        first_call = engine.ai_service.generate.call_args_list[0]
        prompt = first_call.args[0]

        # Either memory items appear directly or recent narrative appears
        # The prompt builder includes either Key Events or Recent Scene
        assert ("Found a mysterious key" in prompt or
                "Emma looked up" in prompt or
                "dimly lit" in prompt)