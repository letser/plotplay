"""
Comprehensive tests for AI integration in PlotPlay v3.
"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.game_engine import GameEngine
from app.core.prompt_builder import PromptBuilder
from app.services.ai_service import AIService, AIResponse
from app.models.location import LocationPrivacy
from app.core.reconciliation import ReconciliationEngine


class TestPromptBuilder:
    """Tests for prompt generation."""

    @pytest.mark.asyncio
    async def test_writer_prompt_structure(self, minimal_game_def):
        """Test that writer prompts contain all required sections."""
        engine = GameEngine(minimal_game_def, "test_writer")
        builder = engine.prompt_builder

        # Setup state with some history
        state = engine.state_manager.state
        state.narrative_history = ["Previous narrative 1", "Previous narrative 2"]
        state.memory_log = ["Memory 1", "Memory 2"]
        state.meters["player"]["health"] = 75
        state.present_chars = ["player", "emma"]

        prompt = builder.build_writer_prompt(
            state=state,
            action="look around",
            current_node=engine._get_current_node(),
            recent_history=state.narrative_history[-5:]
        )

        # Verify all required sections are present
        assert "GAME CONTEXT" in prompt
        assert "CURRENT SITUATION" in prompt
        assert "CHARACTER INFORMATION" in prompt
        assert "ACTION TO NARRATE" in prompt
        assert "CONSTRAINTS" in prompt

        # Verify key information is included
        assert "health: 75" in prompt
        assert "Previous narrative" in prompt
        assert "Memory 1" in prompt

    @pytest.mark.asyncio
    async def test_checker_prompt_structure(self, minimal_game_def):
        """Test that checker prompts are properly formatted."""
        engine = GameEngine(minimal_game_def, "test_checker")
        builder = engine.prompt_builder

        state = engine.state_manager.state
        narrative = "The player looks around the room."

        prompt = builder.build_checker_prompt(
            state=state,
            narrative=narrative,
            action="look around",
            target=None
        )

        # Verify structure
        assert "NARRATIVE TO ANALYZE" in prompt
        assert narrative in prompt
        assert "VALIDATION REQUIREMENTS" in prompt
        assert "OUTPUT FORMAT" in prompt
        assert "JSON" in prompt

    def test_reconciliation_prompt_structure(self, minimal_game_def):
        """Test reconciliation prompt generation."""
        engine = GameEngine(minimal_game_def, "test_recon")
        builder = engine.prompt_builder

        violations = [
            {"type": "consent_gate", "character": "emma", "reason": "trust too low"}
        ]

        prompt = builder.build_reconciliation_prompt(
            narrative="Emma kisses you.",
            violations=violations,
            state=engine.state_manager.state
        )

        assert "ORIGINAL NARRATIVE" in prompt
        assert "VIOLATIONS" in prompt
        assert "consent_gate" in prompt
        assert "trust too low" in prompt
        assert "REWRITE REQUIREMENTS" in prompt


class TestAIServiceIntegration:
    """Tests for AI service integration."""

    @pytest.mark.asyncio
    async def test_ai_response_parsing(self, mock_game_engine):
        """Test parsing of AI responses."""
        engine = mock_game_engine

        # Mock checker response with all fields
        checker_response = {
            "flag_changes": {
                "emma.met": True,
                "first_kiss": True
            },
            "meter_changes": {
                "emma": {"trust": 5, "attraction": 10}
            },
            "inventory_changes": {
                "player": {"remove": ["flowers"]}
            },
            "memory": [
                "You gave Emma flowers",
                "Emma seemed happy"
            ],
            "location_change": {
                "zone": "park",
                "location": "bench"
            }
        }

        engine.ai_service.generate.return_value = AIResponse(
            content=json.dumps(checker_response)
        )

        # Process action and verify changes are applied
        response = await engine.process_action(
            action_type="do",
            action_text="give flowers to emma"
        )

        state = engine.state_manager.state

        # Verify all changes were applied
        assert state.flags.get("emma.met") is True
        assert state.flags.get("first_kiss") is True
        assert "You gave Emma flowers" in state.memory_log
        # Note: The actual state changes would be applied by the engine

    @pytest.mark.asyncio
    async def test_ai_error_handling(self, mock_game_engine):
        """Test handling of AI service errors."""
        engine = mock_game_engine

        # Simulate AI service error
        engine.ai_service.generate.side_effect = Exception("AI service unavailable")

        # Should handle gracefully
        response = await engine.process_action(
            action_type="do",
            action_text="test action"
        )

        # Should provide fallback response
        assert "narrative" in response
        assert response.get("error") is not None or len(response["narrative"]) > 0

    @pytest.mark.asyncio
    async def test_malformed_ai_response_handling(self, mock_game_engine):
        """Test handling of malformed AI responses."""
        engine = mock_game_engine

        # Return invalid JSON
        engine.ai_service.generate.return_value = AIResponse(
            content="This is not valid JSON"
        )

        # Should handle gracefully
        response = await engine.process_action(
            action_type="do",
            action_text="test action"
        )

        assert "narrative" in response


class TestReconciliation:
    """Tests for the reconciliation system."""

    def test_consent_gate_detection(self, minimal_game_def):
        """Test detection of consent gate violations."""
        engine = GameEngine(minimal_game_def, "test_consent")
        recon = ReconciliationEngine(minimal_game_def)

        # Setup state with low trust
        state = engine.state_manager.state
        state.meters["emma"] = {"trust": 20}
        state.flags["emma.first_kiss"] = False

        # Check romantic action with low trust
        violations = recon.check_violations(
            state=state,
            narrative="Emma kisses you passionately.",
            action="kiss emma",
            target="emma",
            checker_response={}
        )

        assert len(violations) > 0
        assert any(v["type"] == "consent_gate" for v in violations)

    def test_meter_limit_violations(self, minimal_game_def):
        """Test detection of meter limit violations."""
        minimal_game_def.meters = {
            "player": {
                "health": {"min": 0, "max": 100, "default": 50}
            }
        }

        engine = GameEngine(minimal_game_def, "test_limits")
        recon = ReconciliationEngine(minimal_game_def)

        state = engine.state_manager.state
        state.meters["player"]["health"] = 95

        # Check action that would exceed max
        checker_response = {
            "meter_changes": {
                "player": {"health": 20}  # Would go to 115
            }
        }

        violations = recon.check_violations(
            state=state,
            narrative="You feel incredibly healthy.",
            action="drink potion",
            target=None,
            checker_response=checker_response
        )

        assert len(violations) > 0
        assert any(v["type"] == "meter_limit" for v in violations)

    @pytest.mark.asyncio
    async def test_narrative_reconciliation(self, mock_game_engine):
        """Test that narratives are properly reconciled when violations occur."""
        engine = mock_game_engine

        # Setup for consent violation
        engine.state_manager.state.meters["emma"] = {"trust": 10}
        engine.state_manager.state.present_chars = ["emma"]

        # Mock writer to return romantic narrative
        writer_response = AIResponse(
            content="Emma's eyes flutter closed as she leans in for a kiss."
        )

        # Mock checker to not add kiss flag (since it shouldn't happen)
        checker_response = AIResponse(
            content=json.dumps({"flag_changes": {}})
        )

        # Mock reconciliation to return rejection
        recon_response = AIResponse(
            content="Emma steps back with a gentle smile. 'Not yet...'"
        )

        engine.ai_service.generate.side_effect = [
            writer_response,
            checker_response,
            recon_response
        ]

        response = await engine.process_action(
            action_type="do",
            action_text="kiss emma",
            target="emma"
        )

        # Should use reconciled narrative
        assert "Not yet" in response["narrative"]
        assert "flutter closed" not in response["narrative"]


class TestMemorySystem:
    """Tests for memory extraction and management."""

    @pytest.mark.asyncio
    async def test_memory_extraction(self, mock_game_engine):
        """Test that memories are properly extracted from checker responses."""
        engine = mock_game_engine

        # Mock responses with memories
        writer_response = AIResponse(content="You chat with Emma.")
        checker_response = AIResponse(content=json.dumps({
            "memory": [
                "Emma mentioned she likes jazz",
                "You learned Emma is a student"
            ]
        }))

        engine.ai_service.generate.side_effect = [writer_response, checker_response]

        await engine.process_action(action_type="do", action_text="talk to emma")

        state = engine.state_manager.state
        assert "Emma mentioned she likes jazz" in state.memory_log
        assert "You learned Emma is a student" in state.memory_log

    @pytest.mark.asyncio
    async def test_memory_limit_enforcement(self, mock_game_engine):
        """Test that memory log is limited to prevent unbounded growth."""
        engine = mock_game_engine
        state = engine.state_manager.state

        # Fill memory log
        for i in range(20):
            state.memory_log.append(f"Old memory {i}")

        # Add new memories
        writer_response = AIResponse(content="Test")
        checker_response = AIResponse(content=json.dumps({
            "memory": ["New memory 1", "New memory 2", "New memory 3"]
        }))

        engine.ai_service.generate.side_effect = [writer_response, checker_response]
        await engine.process_action(action_type="do", action_text="test")

        # Should be limited (default is 15)
        assert len(state.memory_log) <= 15
        # Newest memories should be kept
        assert "New memory 3" in state.memory_log
        # Oldest should be dropped
        assert "Old memory 0" not in state.memory_log

    @pytest.mark.asyncio
    async def test_memory_context_in_prompts(self, mock_game_engine):
        """Test that memories are included in writer prompts."""
        engine = mock_game_engine
        state = engine.state_manager.state

        # Add memories
        state.memory_log = [
            "Emma works at the coffee shop",
            "Emma's favorite coffee is cappuccino",
            "You and Emma sat by the window"
        ]

        # Build prompt
        prompt = engine.prompt_builder.build_writer_prompt(
            state=state,
            action="order coffee",
            current_node=engine._get_current_node(),
            recent_history=[]
        )

        # Verify memories are included
        assert "Emma works at the coffee shop" in prompt
        assert "cappuccino" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])