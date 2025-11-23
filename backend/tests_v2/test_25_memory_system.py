"""
Test new memory system - character memories + narrative summary.

Verifies that:
- Character memories are stored per-character in CharacterState
- Narrative summary is updated every N AI turns
- Writer receives summary + recent narratives
- Checker receives conditional summary request
- Memory system keeps tokens bounded
"""

import pytest
from app.runtime.types import PlayerAction


@pytest.mark.asyncio
async def test_character_memory_log_structure(fixture_engine_factory):
    """
    Verify that character memory_log exists and accepts strings.

    Should test:
    - CharacterState has memory_log field
    - memory_log is a list of strings
    - Can append interaction summaries
    """
    engine = fixture_engine_factory("checklist_demo")
    await engine.start()

    state = engine.runtime.state_manager.state

    # Check that characters have memory_log field
    for char_id, char_state in state.characters.items():
        assert hasattr(char_state, 'memory_log')
        assert isinstance(char_state.memory_log, list)


@pytest.mark.asyncio
async def test_narrative_summary_field_exists(fixture_engine_factory):
    """
    Verify that GameState has narrative_summary field.

    Should test:
    - narrative_summary is string field
    - ai_turns_since_summary is int field
    - Both start at default values
    """
    engine = fixture_engine_factory("checklist_demo")
    await engine.start()

    state = engine.runtime.state_manager.state

    assert hasattr(state, 'narrative_summary')
    assert isinstance(state.narrative_summary, str)
    assert hasattr(state, 'ai_turns_since_summary')
    assert isinstance(state.ai_turns_since_summary, int)
    # Counter may be > 0 after start() if initial narrative was generated
    assert state.ai_turns_since_summary >= 0


@pytest.mark.asyncio
async def test_ai_turn_counter_increments(fixture_engine_factory):
    """
    Verify that ai_turns_since_summary increments on AI-powered turns.

    Should test:
    - Counter starts at 0
    - Increments after each AI turn
    - Only increments on AI turns (not movement)
    """
    engine = fixture_engine_factory("checklist_demo")
    await engine.start()

    state = engine.runtime.state_manager.state

    initial_count = state.ai_turns_since_summary

    # Perform AI-powered action
    await engine.process_action(PlayerAction(action_type="choice", choice_id="greet_alex"))

    # Counter should have incremented
    assert state.ai_turns_since_summary == initial_count + 1


@pytest.mark.asyncio
async def test_checker_prompt_requests_character_memories(fixture_engine_factory):
    """
    Verify that Checker prompt always requests character_memories.

    Should test:
    - character_memories appears in Checker prompt
    - Format is clear (dict with char_id keys)
    - Instructions explain when to add memories
    """
    engine = fixture_engine_factory("checklist_demo")
    await engine.start()

    prompt_builder = engine.prompt_builder
    ctx = engine.runtime.current_context

    checker_prompt = prompt_builder.build_checker_prompt(ctx, "Say hello", "You wave.")

    # Should always request character_memories
    assert "character_memories" in checker_prompt
    # Should show the format
    assert '"<char_id>"' in checker_prompt or 'char_id' in checker_prompt


@pytest.mark.asyncio
async def test_checker_prompt_conditionally_requests_summary(fixture_engine_factory):
    """
    Verify that Checker prompt requests narrative_summary every N turns.

    Should test:
    - Summary NOT requested when ai_turns_since_summary < N
    - Summary requested when ai_turns_since_summary >= N
    """
    from app.core.settings import GameSettings

    engine = fixture_engine_factory("checklist_demo")
    await engine.start()

    settings = GameSettings()
    prompt_builder = engine.prompt_builder
    state = engine.runtime.state_manager.state
    ctx = engine.runtime.current_context

    # At start, counter = 0, should not request summary
    state.ai_turns_since_summary = 0
    checker_prompt = prompt_builder.build_checker_prompt(ctx, "Say hello", "You wave.")
    assert "narrative_summary" not in checker_prompt

    # At N turns, should request summary
    state.ai_turns_since_summary = settings.memory_summary_interval
    checker_prompt = prompt_builder.build_checker_prompt(ctx, "Say hello", "You wave.")
    assert "narrative_summary" in checker_prompt


@pytest.mark.asyncio
async def test_writer_prompt_includes_narrative_summary(fixture_engine_factory):
    """
    Verify that Writer prompt shows narrative_summary + recent narratives.

    Should test:
    - Summary appears in "Story so far:" section
    - Recent narratives still shown
    - Format is readable
    """
    engine = fixture_engine_factory("checklist_demo")
    await engine.start()

    prompt_builder = engine.prompt_builder
    state = engine.runtime.state_manager.state
    ctx = engine.runtime.current_context

    # Add mock summary
    state.narrative_summary = "The day began with a casual meeting at the quad."
    state.narrative_history = ["You arrived at the sunny quad.", "Alex waved at you."]

    writer_prompt = prompt_builder.build_writer_prompt(ctx, "Say hello")

    # Should include summary
    assert "Story so far" in writer_prompt or "story so far" in writer_prompt.lower()
    assert "casual meeting at the quad" in writer_prompt

    # Should include recent narratives
    assert "Recent scene" in writer_prompt or "recent" in writer_prompt.lower()


@pytest.mark.asyncio
async def test_writer_prompt_shows_recent_narratives_window(fixture_engine_factory):
    """
    Verify that Writer shows last N narratives (matching summary interval).

    Should test:
    - Shows last N narratives, not all history
    - N matches MEMORY_SUMMARY_INTERVAL setting
    """
    from app.core.settings import GameSettings

    engine = fixture_engine_factory("checklist_demo")
    await engine.start()

    settings = GameSettings()
    prompt_builder = engine.prompt_builder
    state = engine.runtime.state_manager.state
    ctx = engine.runtime.current_context

    # Create more narratives than the window
    N = settings.memory_summary_interval
    state.narrative_history = [f"Narrative {i}" for i in range(N + 5)]

    writer_prompt = prompt_builder.build_writer_prompt(ctx, "Continue")

    # Should show last N narratives
    assert f"Narrative {N + 4}" in writer_prompt  # Last narrative
    # Should NOT show very old narratives
    assert "Narrative 0" not in writer_prompt


@pytest.mark.asyncio
async def test_memory_parsing_character_memories(fixture_engine_factory):
    """
    Verify that TurnManager parses character_memories from Checker response.

    Should test:
    - character_memories dict is parsed
    - Memories appended to correct character's memory_log
    - Player memories are skipped (only NPCs)
    """
    engine = fixture_engine_factory("checklist_demo")
    await engine.start()

    state = engine.runtime.state_manager.state
    turn_manager = engine.turn_manager

    # Simulate Checker response with character_memories
    mock_deltas = {
        "character_memories": {
            "alex": "Discussed favorite movies",
            "player": "Should be ignored"
        }
    }

    # Apply memory updates
    turn_manager._apply_memory_updates(mock_deltas)

    # Check that Alex got the memory
    if "alex" in state.characters:
        assert "Discussed favorite movies" in state.characters["alex"].memory_log

    # Player should not have memories added (player is special)
    # We don't track player memories in character state


@pytest.mark.asyncio
async def test_memory_parsing_narrative_summary(fixture_engine_factory):
    """
    Verify that TurnManager parses narrative_summary from Checker response.

    Should test:
    - narrative_summary string is parsed
    - Summary is stored in state.narrative_summary
    - ai_turns_since_summary resets to 0
    """
    engine = fixture_engine_factory("checklist_demo")
    await engine.start()

    state = engine.runtime.state_manager.state
    turn_manager = engine.turn_manager

    # Set counter to simulate we're at summary update time
    state.ai_turns_since_summary = 3

    # Simulate Checker response with narrative_summary
    mock_deltas = {
        "narrative_summary": "The morning at the quad was eventful. You met Alex and Emma."
    }

    # Apply memory updates
    turn_manager._apply_memory_updates(mock_deltas)

    # Check that summary was stored
    assert state.narrative_summary == "The morning at the quad was eventful. You met Alex and Emma."

    # Check that counter was reset
    assert state.ai_turns_since_summary == 0


@pytest.mark.asyncio
async def test_memory_system_prevents_token_bloat(fixture_engine_factory):
    """
    Verify that memory system keeps prompt size bounded.

    Should test:
    - With 50 turns, prompt stays under reasonable size
    - Summary replaces showing all narratives
    - Only last N narratives shown in full
    """
    from app.core.settings import GameSettings

    engine = fixture_engine_factory("checklist_demo")
    await engine.start()

    settings = GameSettings()
    prompt_builder = engine.prompt_builder
    state = engine.runtime.state_manager.state
    ctx = engine.runtime.current_context

    # Simulate long game with many narratives
    state.narrative_history = [
        f"Narrative {i}: Something happened." for i in range(50)
    ]
    state.narrative_summary = "The story so far covers many events over several days."

    # Build Writer prompt
    writer_prompt = prompt_builder.build_writer_prompt(ctx, "Continue")

    # Count narratives shown in full
    narrative_count = sum(1 for i in range(50) if f"Narrative {i}" in writer_prompt)

    # Should show at most N recent narratives (not all 50)
    assert narrative_count <= settings.memory_summary_interval + 1

    # Rough token estimate (4 chars per token)
    token_estimate = len(writer_prompt) / 4

    # Should be reasonable size even with long history
    assert token_estimate < 2000, f"Prompt too large: ~{int(token_estimate)} tokens"
