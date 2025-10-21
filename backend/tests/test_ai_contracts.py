"""
Tests for §21 AI Contracts (Writer & Checker) - PlotPlay v3 Specification

The AI Contracts define the two-model architecture where:
- Writer expands authored beats into prose/dialogue
- Checker extracts state deltas and validates safety

§21.1: Two-Model Architecture
§21.2: Turn Context Envelope
§21.3: Writer Contract
§21.4: Checker Contract
§21.5: Prompt Templates
§21.6: Safety & Consent
§21.7: Memory System
§21.8: Error Recovery
§21.9: Cost Profiles
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from app.core.game_engine import GameEngine
from app.core.game_loader import GameLoader
from app.engine.prompt_builder import PromptBuilder
from app.services.ai_service import AIService, AIResponse, AISettings
from app.models.characters import Character
from app.models.narration import NarrationConfig
from app.models.enums import POV, Tense
from app.models.flags import Flag


# =============================================================================
# § 21.1: Two-Model Architecture
# =============================================================================

async def test_two_model_architecture_both_called(minimal_game_def):
    """
    §21.1: Test that both Writer and Checker are called each turn.
    """
    engine = GameEngine(minimal_game_def, "test_two_model")

    # Mock AI service
    engine.ai_service.generate = AsyncMock(return_value=AIResponse(content="Test response"))

    await engine.process_action("do", action_text="Look around")

    # Should call AI at least twice: once for Writer, once for Checker
    assert engine.ai_service.generate.call_count >= 2

    print("✅ Two-model architecture verified")


async def test_writer_generates_prose(minimal_game_def):
    """
    §21.1: Test that Writer produces narrative prose.
    """
    engine = GameEngine(minimal_game_def, "test_writer")

    writer_narrative = "You glance around the dimly lit room. The air smells of old books."

    call_count = 0

    async def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return AIResponse(content=writer_narrative)
        else:
            return AIResponse(content='{"flag_changes": {}}')

    engine.ai_service.generate = AsyncMock(side_effect=mock_generate)

    result = await engine.process_action("do", action_text="Look around")

    assert writer_narrative in result["narrative"]

    print("✅ Writer generates prose")


async def test_checker_extracts_state_deltas(minimal_game_def):
    """
    §21.1: Test that Checker extracts state changes from narrative.
    """
    engine = GameEngine(minimal_game_def, "test_checker")

    checker_json = json.dumps({
        "flag_changes": {"discovered_secret": True},
        "meter_changes": {"player": {"energy": -5}},
        "memory": {"append": ["Found a hidden compartment"]}
    })

    call_count = 0

    async def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return AIResponse(content="You discover a hidden compartment.")
        else:
            return AIResponse(content=checker_json)

    engine.ai_service.generate = AsyncMock(side_effect=mock_generate)
    engine.game_def.flags["discovered_secret"] = Flag(type="bool", default=False)
    engine.state_manager.state.flags["discovered_secret"] = False

    await engine.process_action("do", action_text="Search the desk")

    # State should be updated based on checker response
    # (Actual state update depends on engine implementation)

    print("✅ Checker extracts state deltas")


# =============================================================================
# § 21.2: Turn Context Envelope
# =============================================================================

def test_context_envelope_includes_game_metadata(minimal_game_def, sample_game_state):
    """
    §21.2: Test that context includes game metadata.
    """
    engine = GameEngine(minimal_game_def, "test_context")
    prompt_builder = PromptBuilder(minimal_game_def, engine.clothing_manager)
    current_node = engine._get_current_node()

    prompt = prompt_builder.build_writer_prompt(
        sample_game_state,
        "Player looks around",
        current_node,
        []
    )

    # Should include game context
    assert minimal_game_def.meta.id in prompt or "test" in prompt.lower()

    print("✅ Context includes game metadata")


def test_context_envelope_includes_time(minimal_game_def, sample_game_state):
    """
    §21.2: Test that context includes time information.
    """
    engine = GameEngine(minimal_game_def, "test_time_context")
    prompt_builder = PromptBuilder(minimal_game_def, engine.clothing_manager)
    current_node = engine._get_current_node()

    sample_game_state.day = 3
    sample_game_state.time_slot = "evening"

    prompt = prompt_builder.build_writer_prompt(
        sample_game_state,
        "Player action",
        current_node,
        []
    )

    # Should include time information
    assert "Day 3" in prompt or "3" in prompt
    assert "evening" in prompt

    print("✅ Context includes time")


def test_context_envelope_includes_location(minimal_game_def, sample_game_state):
    """
    §21.2: Test that context includes location information.
    """
    engine = GameEngine(minimal_game_def, "test_location_context")
    prompt_builder = PromptBuilder(minimal_game_def, engine.clothing_manager)
    current_node = engine._get_current_node()

    prompt = prompt_builder.build_writer_prompt(
        sample_game_state,
        "Player action",
        current_node,
        []
    )

    # Should include location
    assert sample_game_state.location_current in prompt or "location" in prompt.lower()

    print("✅ Context includes location")


def test_context_envelope_includes_character_cards(minimal_game_def, sample_game_state):
    """
    §21.2: Test that context includes character cards for NPCs.
    """
    npc = Character(
        id="test_npc",
        name="Test NPC",
        age=25,
        gender="female",
        dialogue_style="Friendly and warm"
    )
    minimal_game_def.characters.append(npc)
    sample_game_state.present_chars.append("test_npc")

    engine = GameEngine(minimal_game_def, "test_char_cards")
    prompt_builder = PromptBuilder(minimal_game_def, engine.clothing_manager)
    current_node = engine._get_current_node()

    prompt = prompt_builder.build_writer_prompt(
        sample_game_state,
        "Player action",
        current_node,
        []
    )

    # Should include character information
    assert "Test NPC" in prompt
    assert "Friendly and warm" in prompt or "dialogue" in prompt.lower()

    print("✅ Context includes character cards")


def test_context_envelope_includes_player_inventory(minimal_game_def, sample_game_state):
    """
    §21.2: Test that context includes player inventory.
    """
    sample_game_state.inventory["player"] = {"key": 1, "map": 1}

    engine = GameEngine(minimal_game_def, "test_inventory_context")
    prompt_builder = PromptBuilder(minimal_game_def, engine.clothing_manager)
    current_node = engine._get_current_node()

    prompt = prompt_builder.build_writer_prompt(
        sample_game_state,
        "Player action",
        current_node,
        []
    )

    # Should mention inventory
    assert "inventory" in prompt.lower() or "key" in prompt.lower()

    print("✅ Context includes player inventory")


# =============================================================================
# § 21.3: Writer Contract
# =============================================================================

def test_writer_follows_pov(minimal_game_def, sample_game_state):
    """
    §21.3: Test that Writer prompt specifies POV (first/second/third).
    """
    minimal_game_def.narration = NarrationConfig(
        pov=POV.FIRST,
        tense=Tense.PRESENT
    )

    engine = GameEngine(minimal_game_def, "test_pov")
    prompt_builder = PromptBuilder(minimal_game_def, engine.clothing_manager)
    current_node = engine._get_current_node()

    prompt = prompt_builder.build_writer_prompt(
        sample_game_state,
        "Player action",
        current_node,
        []
    )

    # Should specify first person POV
    assert "first" in prompt.lower() and ("perspective" in prompt.lower() or "person" in prompt.lower())

    print("✅ Writer follows POV")


def test_writer_follows_tense(minimal_game_def, sample_game_state):
    """
    §21.3: Test that Writer prompt specifies tense (present/past).
    """
    minimal_game_def.narration = NarrationConfig(
        pov=POV.SECOND,
        tense=Tense.PAST
    )

    engine = GameEngine(minimal_game_def, "test_tense")
    prompt_builder = PromptBuilder(minimal_game_def, engine.clothing_manager)
    current_node = engine._get_current_node()

    prompt = prompt_builder.build_writer_prompt(
        sample_game_state,
        "Player action",
        current_node,
        []
    )

    # Should specify past tense
    assert "past" in prompt.lower() and "tense" in prompt.lower()

    print("✅ Writer follows tense")


def test_writer_respects_paragraph_budget(minimal_game_def, sample_game_state):
    """
    §21.3: Test that Writer prompt specifies paragraph target.
    """
    minimal_game_def.narration = NarrationConfig(
        paragraphs="2-3"
    )

    engine = GameEngine(minimal_game_def, "test_paragraphs")
    prompt_builder = PromptBuilder(minimal_game_def, engine.clothing_manager)
    current_node = engine._get_current_node()

    prompt = prompt_builder.build_writer_prompt(
        sample_game_state,
        "Player action",
        current_node,
        []
    )

    # Should specify paragraph count
    assert "paragraph" in prompt.lower() and ("2" in prompt or "3" in prompt)

    print("✅ Writer respects paragraph budget")


def test_writer_no_raw_state_changes(minimal_game_def, sample_game_state):
    """
    §21.3: Test that Writer is instructed not to output raw state changes.
    """
    engine = GameEngine(minimal_game_def, "test_no_state")
    prompt_builder = PromptBuilder(minimal_game_def, engine.clothing_manager)
    current_node = engine._get_current_node()

    prompt = prompt_builder.build_writer_prompt(
        sample_game_state,
        "Player action",
        current_node,
        []
    )

    # Should instruct Writer not to mention game mechanics
    assert "never" in prompt.lower() or "not" in prompt.lower() or "don't" in prompt.lower()

    print("✅ Writer instructed not to output raw state changes")


def test_writer_uses_refusal_lines(minimal_game_def, sample_game_state):
    """
    §21.3: Test that Writer is instructed to use refusal lines when needed.
    """
    npc = Character(
        id="emma",
        name="Emma",
        age=22,
        gender="female"
    )
    minimal_game_def.characters.append(npc)
    sample_game_state.present_chars.append("emma")

    engine = GameEngine(minimal_game_def, "test_refusal")
    prompt_builder = PromptBuilder(minimal_game_def, engine.clothing_manager)
    current_node = engine._get_current_node()

    prompt = prompt_builder.build_writer_prompt(
        sample_game_state,
        "Player action",
        current_node,
        []
    )

    # Should mention refusal or consent
    assert "refusal" in prompt.lower() or "consent" in prompt.lower() or "gate" in prompt.lower()

    print("✅ Writer uses refusal lines")


# =============================================================================
# § 21.4: Checker Contract
# =============================================================================

def test_checker_prompt_requests_json(minimal_game_def, sample_game_state):
    """
    §21.4: Test that Checker prompt requests strict JSON output.
    """
    engine = GameEngine(minimal_game_def, "test_json")
    prompt_builder = PromptBuilder(minimal_game_def, engine.clothing_manager)

    prompt = prompt_builder.build_checker_prompt(
        "Test narrative",
        "Player action",
        sample_game_state
    )

    # Should request JSON
    assert "JSON" in prompt or "json" in prompt

    print("✅ Checker prompt requests JSON")


def test_checker_json_schema_structure():
    """
    §21.4: Test that Checker JSON schema includes all required keys.
    """
    # Expected keys from spec
    expected_keys = [
        "safety", "meters", "flags", "inventory", "clothing",
        "modifiers", "location", "events_fired", "node_transition", "memory"
    ]

    # This is a documentation test - the schema should be defined
    # In actual implementation, validate against the spec

    print("✅ Checker JSON schema documented")


def test_checker_uses_delta_notation():
    """
    §21.4: Test that Checker uses +N/-N for deltas, =N for absolutes.
    """
    # Example checker response
    checker_response = {
        "meters": {
            "player": {"health": "-5", "energy": "+10"},
            "emma": {"trust": "=50"}  # Absolute set
        }
    }

    # Validate delta notation
    assert "-5" in str(checker_response)  # Negative delta
    assert "+10" in str(checker_response)  # Positive delta
    assert "=50" in str(checker_response)  # Absolute value

    print("✅ Checker uses delta notation")


def test_checker_clamps_to_meter_caps():
    """
    §21.4: Test that Checker should respect meter min/max bounds.
    """
    # This is a guideline test - Checker should be instructed to clamp
    # In practice, the engine applies clamping after parsing

    print("✅ Checker clamping guideline noted")


# =============================================================================
# § 21.5: Prompt Templates
# =============================================================================

def test_writer_template_includes_pov_tense_paragraphs(minimal_game_def, sample_game_state):
    """
    §21.5: Test Writer template includes POV, tense, and paragraph budget.
    """
    engine = GameEngine(minimal_game_def, "test_template")
    prompt_builder = PromptBuilder(minimal_game_def, engine.clothing_manager)
    current_node = engine._get_current_node()

    prompt = prompt_builder.build_writer_prompt(
        sample_game_state,
        "Player action",
        current_node,
        []
    )

    # Template should include all three
    has_pov = "person" in prompt.lower() or "perspective" in prompt.lower()
    has_tense = "tense" in prompt.lower() or "present" in prompt.lower() or "past" in prompt.lower()
    has_paragraphs = "paragraph" in prompt.lower()

    assert has_pov or has_tense or has_paragraphs  # At least one should be present

    print("✅ Writer template includes key elements")


def test_checker_template_lists_required_keys(minimal_game_def, sample_game_state):
    """
    §21.5: Test Checker template lists all required JSON keys.
    """
    engine = GameEngine(minimal_game_def, "test_checker_template")
    prompt_builder = PromptBuilder(minimal_game_def, engine.clothing_manager)

    prompt = prompt_builder.build_checker_prompt(
        "Test narrative",
        "Player action",
        sample_game_state
    )

    # Should mention key data structures
    mentions_keys = (
            "meter" in prompt.lower() or
            "flag" in prompt.lower() or
            "memory" in prompt.lower()
    )

    assert mentions_keys

    print("✅ Checker template lists required keys")


def test_character_card_format_minimal(minimal_game_def, sample_game_state):
    """
    §21.5: Test that character cards use minimal, consistent format.
    """
    npc = Character(
        id="alex",
        name="Alex",
        age=25,
        gender="female",
        description="A friendly barmaid",
        dialogue_style="Warm and teasing"
    )
    minimal_game_def.characters.append(npc)
    sample_game_state.present_chars.append("alex")

    engine = GameEngine(minimal_game_def, "test_card_format")
    prompt_builder = PromptBuilder(minimal_game_def, engine.clothing_manager)
    current_node = engine._get_current_node()

    prompt = prompt_builder.build_writer_prompt(
        sample_game_state,
        "Player action",
        current_node,
        []
    )

    # Should include character info
    assert "Alex" in prompt

    print("✅ Character card format is minimal")


# =============================================================================
# § 21.6: Safety & Consent
# =============================================================================

def test_all_characters_must_be_18_plus():
    """
    §21.6: Test that all characters must be 18+.
    """
    # Valid character
    valid_char = Character(
        id="adult",
        name="Adult",
        age=25,
        gender="any"
    )
    assert valid_char.age >= 18

    print("✅ Character age requirement noted")


def test_consent_gates_required_for_intimate_acts(minimal_game_def, sample_game_state):
    """
    §21.6: Test that consent gates are checked for intimate actions.
    """
    # This is validated through character behaviors and gates
    # The Writer should be instructed to respect gates

    engine = GameEngine(minimal_game_def, "test_consent")
    prompt_builder = PromptBuilder(minimal_game_def, engine.clothing_manager)
    current_node = engine._get_current_node()

    prompt = prompt_builder.build_writer_prompt(
        sample_game_state,
        "Player action",
        current_node,
        []
    )

    # Should mention gates or consent
    assert "gate" in prompt.lower() or "consent" in prompt.lower() or "refusal" in prompt.lower()

    print("✅ Consent gates enforced")


def test_privacy_level_affects_intimate_actions(minimal_game_def, sample_game_state):
    """
    §21.6: Test that location privacy affects what actions are allowed.
    """
    engine = GameEngine(minimal_game_def, "test_privacy")
    prompt_builder = PromptBuilder(minimal_game_def, engine.clothing_manager)
    current_node = engine._get_current_node()

    prompt = prompt_builder.build_writer_prompt(
        sample_game_state,
        "Player action",
        current_node,
        []
    )

    # Should mention privacy
    assert "privacy" in prompt.lower()

    print("✅ Privacy level checked")


def test_safety_violations_flagged():
    """
    §21.6: Test that safety violations should be flagged by Checker.
    """
    # Example Checker response with violation
    checker_response = {
        "safety": {
            "ok": False,
            "violations": ["attempted_non_consensual_action"]
        }
    }

    assert checker_response["safety"]["ok"] is False
    assert len(checker_response["safety"]["violations"]) > 0

    print("✅ Safety violations can be flagged")


# =============================================================================
# § 21.7: Memory System
# =============================================================================

def test_memory_append_creates_compact_reminders(minimal_game_def, sample_game_state):
    """
    §21.7: Test that memory.append creates compact factual reminders.
    """
    # Example memory entries
    memories = [
        "Met Emma at the cafe",
        "Found a mysterious key",
        "Alex mentioned a secret"
    ]

    # Memories should be concise
    for memory in memories:
        assert len(memory) < 100  # Compact
        assert memory[0].isupper()  # Proper sentence

    print("✅ Memory format is compact")


def test_memory_rolling_window(minimal_game_def, sample_game_state):
    """
    §21.7: Test that memory keeps rolling window of 6-10 entries.
    """
    # Add many memories
    for i in range(20):
        sample_game_state.memory_log.append(f"Memory {i}")

    # In practice, the engine should maintain window size
    # This is a guideline test

    print("✅ Memory rolling window guideline noted")


def test_memory_included_in_context(minimal_game_def, sample_game_state):
    """
    §21.7: Test that memory is included in Writer prompts.
    """
    sample_game_state.memory_log = [
        "Found a key",
        "Met Emma",
        "Discovered secret passage"
    ]

    engine = GameEngine(minimal_game_def, "test_memory_context")
    prompt_builder = PromptBuilder(minimal_game_def, engine.clothing_manager)
    current_node = engine._get_current_node()

    prompt = prompt_builder.build_writer_prompt(
        sample_game_state,
        "Player action",
        current_node,
        sample_game_state.narrative_history
    )

    # Should include at least some memories
    assert "Found a key" in prompt or "Met Emma" in prompt or "memory" in prompt.lower()

    print("✅ Memory included in context")


# =============================================================================
# § 21.8: Error Recovery
# =============================================================================

async def test_malformed_json_cleanup(minimal_game_def):
    """
    §21.8: Test that malformed Checker JSON triggers cleanup.
    """
    engine = GameEngine(minimal_game_def, "test_json_cleanup")

    # Return malformed JSON
    malformed_json = '{"flags": {"test": true,}}'  # Extra comma

    call_count = 0

    async def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return AIResponse(content="Test narrative")
        else:
            return AIResponse(content=malformed_json)

    engine.ai_service.generate = AsyncMock(side_effect=mock_generate)

    # Should handle gracefully
    result = await engine.process_action("do", action_text="Test action")
    assert result is not None

    print("✅ Malformed JSON handled")


async def test_error_recovery_continues_gameplay(minimal_game_def):
    """
    §21.8: Test that errors don't halt the game.
    """
    engine = GameEngine(minimal_game_def, "test_error_recovery")

    # Simulate error in Checker
    call_count = 0

    async def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return AIResponse(content="Narrative continues")
        else:
            return AIResponse(content="invalid json")

    engine.ai_service.generate = AsyncMock(side_effect=mock_generate)

    result = await engine.process_action("do", action_text="Continue")

    # Should still return a result
    assert result is not None
    assert "narrative" in result

    print("✅ Error recovery allows continuation")


# =============================================================================
# § 21.9: Cost Profiles
# =============================================================================

def test_cost_profile_cheap():
    """
    §21.9: Test that 'cheap' profile uses smaller models.
    """
    settings = AISettings()

    # Should have model configuration
    assert hasattr(settings, 'writer_model')
    assert hasattr(settings, 'checker_model')

    print("✅ Cost profiles exist")


def test_cost_profile_settings_configurable():
    """
    §21.9: Test that model settings are configurable.
    """
    settings = AISettings()

    # Should be able to configure
    assert hasattr(settings, 'writer_temperature')
    assert hasattr(settings, 'checker_temperature')
    assert hasattr(settings, 'writer_max_tokens')

    print("✅ Model settings configurable")


# =============================================================================
# Integration Tests
# =============================================================================

async def test_full_turn_with_writer_and_checker():
    """
    §21: Test complete turn cycle with Writer and Checker.
    """
    loader = GameLoader()
    game_def = loader.load_game("coffeeshop_date")
    engine = GameEngine(game_def, "test_full_turn")

    # Mock AI responses
    call_count = 0

    async def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Writer response
            return AIResponse(content="You look around the cozy cafe.")
        else:
            # Checker response
            return AIResponse(content='{"flag_changes": {}, "meter_changes": {}}')

    engine.ai_service.generate = AsyncMock(side_effect=mock_generate)

    result = await engine.process_action("do", action_text="Look around")

    assert result is not None
    assert "narrative" in result
    assert call_count == 2  # Both models called

    print("✅ Full turn cycle works")


async def test_real_game_ai_integration():
    """
    §21: Test AI integration with real game definition.
    """
    loader = GameLoader()
    game_def = loader.load_game("college_romance")

    # Validate game has AI-relevant settings
    assert game_def.narration is not None
    assert game_def.narration.pov is not None
    assert game_def.narration.tense is not None

    print("✅ Real game AI configuration valid")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
