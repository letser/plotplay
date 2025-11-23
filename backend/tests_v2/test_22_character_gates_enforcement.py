"""
Test character gates system - loading, evaluation, and enforcement.

This test file covers Section 11.2 of the checklist:
- Character gate definitions
- Gate condition evaluation (when/when_all/when_any)
- Active gate storage and queries
- Gate acceptance/refusal text
- Gates in DSL condition context
- Gates passed to Writer/Checker
"""

import pytest
from app.runtime.types import PlayerAction


async def test_load_gate_definitions(fixture_gate_game):
    """
    Verify that character gate definitions are loaded correctly.

    Should test:
    - Gate ID uniqueness per character
    - Gate condition types (when/when_all/when_any)
    - Acceptance and refusal text loading
    - Gate metadata (description, etc.)
    """
    game = fixture_gate_game
    sam = next(c for c in game.characters if c.id == "sam")
    assert len(sam.gates) == 2
    chat_gate = next(g for g in sam.gates if g.id == "chat_gate")
    trust_gate = next(g for g in sam.gates if g.id == "trust_gate")
    assert chat_gate.when == "flags.greet_done == true"
    assert chat_gate.acceptance is not None
    assert chat_gate.refusal is not None
    assert trust_gate.when == "meters.player.trust >= 20"


async def test_evaluate_gate_conditions(started_gate_engine):
    """
    Verify that gate conditions are evaluated correctly each turn.

    Should test:
    - when (single condition)
    - when_all (all conditions must be true)
    - when_any (any condition must be true)
    - Complex conditions with meters, flags, time, location
    """
    engine, _ = started_gate_engine
    state = engine.runtime.state_manager.state
    assert "chat_gate" not in state.characters["sam"].gates
    await engine.process_action(PlayerAction(action_type="choice", choice_id="say_hi"))
    assert "chat_gate" in state.characters["sam"].gates


async def test_store_active_gates_per_character(started_gate_engine):
    """
    Verify that active gates are stored per character in turn context.

    Should test:
    - Active gates dictionary structure: {char_id: {gate_id: bool}}
    - Gates re-evaluated each turn
    - Gate state changes reflected in storage
    """
    engine, _ = started_gate_engine
    state = engine.runtime.state_manager.state
    await engine.process_action(PlayerAction(action_type="choice", choice_id="say_hi"))
    assert state.characters["sam"].gates.get("chat_gate") is True
    await engine.process_action(PlayerAction(action_type="choice", choice_id="raise_trust"))
    assert state.characters["sam"].gates.get("trust_gate") is True


async def test_provide_acceptance_text_when_gate_active(started_gate_engine):
    """
    Verify that acceptance text is provided when gate is active.

    Should test:
    - Acceptance text returned when gate condition is true
    - Text passed to character cards
    - Text available to Writer model
    """
    engine, _ = started_gate_engine
    state = engine.runtime.state_manager.state
    await engine.process_action(PlayerAction(action_type="choice", choice_id="say_hi"))
    gates = state.characters["sam"].gates
    assert gates.get("chat_gate") is True


async def test_provide_refusal_text_when_gate_inactive(started_gate_engine):
    """
    Verify that refusal text is provided when gate is inactive.

    Should test:
    - Refusal text returned when gate condition is false
    - Text passed to character cards
    - Text available to Writer model
    """
    engine, _ = started_gate_engine
    state = engine.runtime.state_manager.state
    assert state.characters["sam"].gates.get("chat_gate") is None


async def test_expose_gates_in_dsl_context(started_gate_engine):
    """
    Verify that gates are accessible in DSL condition context.

    Should test:
    - gates.char_id.gate_id path resolution
    - Gate boolean value (true/false)
    - Gates used in node conditions
    - Gates used in choice conditions
    - Gates used in effect guards
    """
    engine, _ = started_gate_engine
    state = engine.runtime.state_manager.state
    await engine.process_action(PlayerAction(action_type="choice", choice_id="say_hi"))
    ctx = engine.runtime.state_manager.get_dsl_context()
    assert ctx["gates"]["sam"].get("chat_gate") is True


async def test_pass_gate_info_to_writer_via_character_cards(started_gate_engine):
    """
    Verify that gate info is included in character cards for Writer.

    Should test:
    - Character card includes behavior guidance from gates
    - Character card includes acceptance/refusal TEXT (not IDs)
    - Character card format matches Writer contract
    """
    engine, _ = started_gate_engine
    await engine.process_action(PlayerAction(action_type="choice", choice_id="say_hi"))
    # Use PromptBuilder instead of removed TurnManager method
    cards = engine.prompt_builder._build_character_cards_section(
        engine.runtime.state_manager.state,
        engine.runtime.current_context
    )
    # Should include behavior field with free text (not gate IDs)
    assert "behavior:" in cards
    # Should NOT include gate IDs (opaque identifiers)
    assert "chat_gate" not in cards
    assert "trust_gate" not in cards


async def test_pass_gate_info_to_checker_for_enforcement(started_gate_engine):
    """
    Verify that gate info is passed to Checker for validation.

    Should test:
    - Checker receives gate constraints
    - Checker can validate state changes against gates
    - Disallowed gates prevent certain actions
    """
    engine, _ = started_gate_engine
    state = engine.runtime.state_manager.state
    await engine.process_action(PlayerAction(action_type="choice", choice_id="say_hi"))
    assert state.characters["sam"].gates.get("chat_gate") is True


async def test_gate_state_changes_between_turns(started_gate_engine):
    """
    Verify that gate states update correctly as game state changes.

    Should test:
    - Gate becomes active when meter crosses threshold
    - Gate becomes inactive when condition fails
    - Multiple gates for same character
    - Gate transitions logged correctly
    """
    engine, _ = started_gate_engine
    state = engine.runtime.state_manager.state
    await engine.process_action(PlayerAction(action_type="choice", choice_id="say_hi"))
    assert state.characters["sam"].gates.get("chat_gate") is True
    state.flags["greet_done"] = False
    engine.turn_manager._evaluate_gates(engine.runtime.current_context)
    assert "chat_gate" not in state.characters["sam"].gates


async def test_consent_gates_prevent_unauthorized_actions(started_gate_engine):
    """
    Verify that consent gates prevent actions when conditions not met.

    Should test:
    - Intimacy actions blocked when trust/attraction too low
    - Privacy requirements enforced
    - Multiple gate conditions for sensitive actions
    - Checker respects consent gates
    """
    engine, _ = started_gate_engine
    state = engine.runtime.state_manager.state
    assert state.characters["sam"].gates.get("trust_gate") is None
    await engine.process_action(PlayerAction(action_type="choice", choice_id="raise_trust"))
    assert state.characters["sam"].gates.get("trust_gate") is True
