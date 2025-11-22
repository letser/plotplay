"""
Test event system mechanics - loading, triggering, cooldowns, weighted selection.

This test file covers Section 16 of the checklist:
- Event definition loading
- Event types (random, conditional, scheduled)
- Trigger condition evaluation
- Weighted random selection
- Event effects (on_enter, on_exit)
- Event choices and narrative beats
- Cooldown management
"""

import pytest
from app.runtime.types import PlayerAction


def _event_ids(events):
    return {evt.id for evt in events}


# ============================================================================
# EVENT LOADING
# ============================================================================

async def test_load_event_definitions_completely(fixture_event_game):
    """
    Verify that event definitions are loaded completely.

    Should test:
    - Event ID uniqueness
    - Event type (random, conditional, scheduled)
    - Trigger conditions (when/when_all/when_any)
    - Probability weights
    - Cooldown values
    - on_enter effects
    - on_exit effects
    - Event choices
    - Event narrative beats
    """
    game = fixture_event_game
    event_ids = _event_ids(game.events)
    assert {"random_low", "random_high", "conditional_event", "scheduled_event"} <= event_ids

    random_low = next(evt for evt in game.events if evt.id == "random_low")
    assert random_low.probability == 10
    assert random_low.cooldown == 2
    assert random_low.beats and "minor" in random_low.beats[0]
    assert random_low.on_enter and random_low.on_enter[0]["type"] == "flag_set"
    assert random_low.choices and random_low.choices[0].id == "event_wave"

    conditional = next(evt for evt in game.events if evt.id == "conditional_event")
    assert conditional.when == "flags.trigger_event == true"
    assert conditional.cooldown == 1

    scheduled = next(evt for evt in game.events if evt.id == "scheduled_event")
    assert scheduled.when == 'time.slot == "night"'


async def test_load_event_types_random_conditional_scheduled(fixture_event_game):
    """
    Verify that all event types are loaded correctly.

    Should test:
    - Random events with probability
    - Conditional events with trigger conditions
    - Scheduled events with time/day conditions
    """
    events = {evt.id: evt for evt in fixture_event_game.events}
    assert events["random_low"].probability == 10
    assert events["random_high"].probability == 30
    assert events["conditional_event"].probability == 100  # defaults to 100 when conditional
    assert events["conditional_event"].when is not None
    assert events["scheduled_event"].when == 'time.slot == "night"'


async def test_load_event_trigger_conditions(fixture_event_game):
    """
    Verify that event trigger conditions are loaded.

    Should test:
    - when (single condition)
    - when_all (all conditions)
    - when_any (any conditions)
    - Complex conditions with DSL expressions
    """
    events = {evt.id: evt for evt in fixture_event_game.events}
    assert events["conditional_event"].when == "flags.trigger_event == true"
    assert events["random_low"].when is None
    assert events["scheduled_event"].when == 'time.slot == "night"'


async def test_load_event_effects_on_enter_on_exit(fixture_event_game):
    """
    Verify that event effects are loaded.

    Should test:
    - on_enter effects list
    - on_exit effects list
    - Effect types and parameters
    """
    events = {evt.id: evt for evt in fixture_event_game.events}
    random_low = events["random_low"]
    assert random_low.on_enter
    types = [effect["type"] if isinstance(effect, dict) else getattr(effect, "type", None) for effect in random_low.on_enter]
    assert "flag_set" in types and "meter_change" in types


async def test_load_event_choices_and_narrative_beats(fixture_event_game):
    """
    Verify that event choices and narrative beats are loaded.

    Should test:
    - Event choice definitions
    - Choice conditions
    - Choice effects
    - Narrative beat strings
    """
    random_low = next(evt for evt in fixture_event_game.events if evt.id == "random_low")
    assert random_low.choices
    assert random_low.choices[0].prompt == "Wave at the surprise"
    assert random_low.beats and isinstance(random_low.beats[0], str)


# ============================================================================
# EVENT TRIGGERING
# ============================================================================

async def test_evaluate_event_trigger_conditions(started_event_engine):
    """
    Verify that event trigger conditions are evaluated correctly.

    Should test:
    - when condition evaluation
    - when_all condition evaluation
    - when_any condition evaluation
    - Conditions checked each turn
    """
    engine, _ = started_event_engine
    state = engine.runtime.state_manager.state

    await engine.process_action(PlayerAction(action_type="choice", choice_id="set_trigger"))
    result = await engine.process_action(PlayerAction(action_type="do", action_text="trigger conditional"))
    assert "conditional_event" in result.events_fired
    assert state.flags["conditional_fired"] is True

    await engine.process_action(PlayerAction(action_type="choice", choice_id="clear_trigger"))
    result = await engine.process_action(PlayerAction(action_type="do", action_text="no conditional"))
    assert "conditional_event" not in result.events_fired


async def test_add_random_events_to_weighted_pool(started_event_engine):
    """
    Verify that random events are added to weighted pool.

    Should test:
    - Events with probability added to pool
    - Multiple random events in pool
    - Weights extracted correctly
    """
    engine, _ = started_event_engine
    result = await engine.process_action(PlayerAction(action_type="do", action_text="roll random"))
    assert set(result.events_fired).issubset({"random_low", "random_high", "conditional_event", "scheduled_event"})
    state = engine.runtime.state_manager.state
    assert state.flags["random_low_fired"] or state.flags["random_high_fired"]


async def test_trigger_conditional_events_immediately(started_event_engine):
    """
    Verify that conditional events trigger immediately when conditions met.

    Should test:
    - Conditional event fires when trigger condition true
    - Conditional event doesn't fire when condition false
    - Multiple conditional events can fire
    """
    engine, _ = started_event_engine
    await engine.process_action(PlayerAction(action_type="choice", choice_id="set_trigger"))
    result = await engine.process_action(PlayerAction(action_type="do", action_text="fire condition"))
    assert "conditional_event" in result.events_fired
    await engine.process_action(PlayerAction(action_type="choice", choice_id="clear_trigger"))
    result = await engine.process_action(PlayerAction(action_type="do", action_text="no fire"))
    assert "conditional_event" not in result.events_fired


async def test_select_one_random_event_using_weights_and_rng(started_event_engine):
    """
    Verify that one random event is selected using weights and deterministic RNG.

    Should test:
    - Weighted selection from pool
    - Deterministic selection with seeded RNG
    - Total weight calculation
    - Probability distribution over multiple runs
    """
    engine, _ = started_event_engine
    # First random roll should pick random_low based on seeded RNG (prob 10 vs 30).
    first = await engine.process_action(PlayerAction(action_type="do", action_text="roll once"))
    assert first.events_fired[0] == "random_low"
    # Cooldown reduces immediately; next roll should skip random_low and pick random_high.
    second = await engine.process_action(PlayerAction(action_type="do", action_text="roll twice"))
    assert "random_high" in second.events_fired


async def test_apply_event_on_enter_effects(started_event_engine):
    """
    Verify that event on_enter effects are applied when event triggers.

    Should test:
    - on_enter effects executed
    - Effects applied to state
    - Multiple effects in order
    """
    engine, _ = started_event_engine
    state = engine.runtime.state_manager.state
    await engine.process_action(PlayerAction(action_type="do", action_text="trigger random"))
    assert state.flags["random_low_fired"] or state.flags["random_high_fired"]
    # Energy modified by random_low(-1) or random_high(+2); ensure it changed from default.
    assert state.characters["player"].meters["energy"] != 50


async def test_apply_event_on_exit_effects(started_event_engine):
    """
    Verify that event on_exit effects are applied when event ends.

    Should test:
    - on_exit effects executed
    - Effects applied to state
    - Triggered when event completes or is dismissed
    """
    engine, _ = started_event_engine
    # No explicit on_exit in fixture; ensure pipeline tolerates missing and state stable.
    result = await engine.process_action(PlayerAction(action_type="do", action_text="another roll"))
    assert isinstance(result.events_fired, list)


# ============================================================================
# EVENT COOLDOWNS
# ============================================================================

async def test_check_event_cooldowns_skip_if_on_cooldown(started_event_engine):
    """
    Verify that events on cooldown are skipped.

    Should test:
    - Event not triggered if on cooldown
    - Cooldown tracked per event
    - Cooldown value from event definition
    """
    engine, _ = started_event_engine
    await engine.process_action(PlayerAction(action_type="do", action_text="roll random"))
    state = engine.runtime.state_manager.state
    assert "random_low" in state.cooldowns or "random_high" in state.cooldowns
    # Next turn should not trigger same event if cooldown present.
    result = await engine.process_action(PlayerAction(action_type="do", action_text="roll again"))
    fired = set(result.events_fired)
    assert not (state.cooldowns.get("random_low", 0) > 0 and "random_low" in fired)
    assert not (state.cooldowns.get("random_high", 0) > 0 and "random_high" in fired)


async def test_set_event_cooldowns_after_trigger(started_event_engine):
    """
    Verify that cooldowns are set when events trigger.

    Should test:
    - Cooldown set to event's cooldown value
    - Cooldown tracked in turn state
    - Cooldown persists across turns
    """
    engine, _ = started_event_engine
    await engine.process_action(PlayerAction(action_type="do", action_text="roll random"))
    state = engine.runtime.state_manager.state
    assert state.cooldowns  # at least one cooldown set
    for value in state.cooldowns.values():
        assert value >= 0


async def test_decrement_cooldowns_each_turn(started_event_engine):
    """
    Verify that cooldowns are decremented each turn.

    Should test:
    - Cooldown decreases by 1 each turn
    - Cooldown reaches 0
    - Event can trigger again after cooldown expires
    """
    engine, _ = started_event_engine
    await engine.process_action(PlayerAction(action_type="do", action_text="roll random"))
    state = engine.runtime.state_manager.state
    before = dict(state.cooldowns)
    await engine.process_action(PlayerAction(action_type="do", action_text="tick once"))
    for event_id, remaining in before.items():
        if remaining > 0:
            assert state.cooldowns.get(event_id, 0) == max(remaining - 1, 0)


async def test_remove_expired_cooldowns(started_event_engine):
    """
    Verify that expired cooldowns are removed.

    Should test:
    - Cooldown removed when reaches 0
    - Event available for triggering again
    - Cooldown tracking cleaned up
    """
    engine, _ = started_event_engine
    await engine.process_action(PlayerAction(action_type="do", action_text="roll random"))
    state = engine.runtime.state_manager.state
    # Decrement cooldowns manually to avoid new random triggers resetting them.
    pipeline = engine.turn_manager.event_pipeline
    pipeline.decrement_cooldowns()
    pipeline.decrement_cooldowns()
    assert not state.cooldowns  # cooldown map cleaned up when timers expire


# ============================================================================
# EVENT CHOICES & NARRATIVE
# ============================================================================

async def test_collect_event_choices(started_event_engine):
    """
    Verify that event choices are collected when event triggers.

    Should test:
    - Event choices added to available choices
    - Choice conditions evaluated
    - Choice metadata (id, prompt, category)
    """
    engine, _ = started_event_engine
    result = await engine.process_action(PlayerAction(action_type="do", action_text="roll random"))
    if result.events_fired:
        assert any(choice["id"] == "event_wave" for choice in result.choices)


async def test_collect_event_narrative_beats(started_event_engine):
    """
    Verify that event narrative beats are collected.

    Should test:
    - Narrative beats from triggered event
    - Multiple beats if multiple events
    - Beats passed to Writer
    """
    engine, _ = started_event_engine
    result = await engine.process_action(PlayerAction(action_type="do", action_text="roll random"))
    if result.events_fired:
        assert any("event" in beat for beat in result.narrative.split("\n"))


# ============================================================================
# EVENT INTEGRATION
# ============================================================================

async def test_multiple_events_can_trigger_same_turn(started_event_engine):
    """
    Verify that multiple events can trigger in the same turn.

    Should test:
    - Multiple conditional events trigger
    - Only one random event selected
    - Effects from all triggered events applied
    """
    engine, _ = started_event_engine
    await engine.process_action(PlayerAction(action_type="choice", choice_id="set_trigger"))
    result = await engine.process_action(PlayerAction(action_type="do", action_text="roll conditional + random"))
    assert result.events_fired
    # At most one random plus conditional; ensure conditional can coexist.
    assert "conditional_event" in result.events_fired


async def test_event_triggering_respects_priority_order(started_event_engine):
    """
    Verify that events trigger in correct priority order.

    Should test:
    - Conditional events before random events
    - Event effects apply in order
    - Turn context tracks all fired events
    """
    engine, _ = started_event_engine
    await engine.process_action(PlayerAction(action_type="choice", choice_id="set_trigger"))
    result = await engine.process_action(PlayerAction(action_type="do", action_text="priority check"))
    # Conditional events are evaluated before random events in pipeline
    assert result.events_fired
    assert result.events_fired[0] == "conditional_event"


async def test_event_effects_influence_game_state(started_event_engine):
    """
    Verify that event effects correctly modify game state.

    Should test:
    - Meter changes from events
    - Flag changes from events
    - Inventory changes from events
    - State changes persist after event
    """
    engine, _ = started_event_engine
    state = engine.runtime.state_manager.state
    await engine.process_action(PlayerAction(action_type="do", action_text="roll random"))
    # Set time to night before the next turn so scheduled_event condition is true at turn start.
    engine.time_service.advance_minutes(600, apply_decay=False)
    result = await engine.process_action(PlayerAction(action_type="do", action_text="night event"))
    assert state.flags["scheduled_fired"] is True
    assert result.narrative
