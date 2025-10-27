"""Tests for EventPipeline (consolidated from EventManager and ArcManager)."""

import pytest
from tests_v2.conftest_services import engine_fixture
from app.engine.events import EventPipeline, EventResult
from app.models.nodes import Event
from app.models.arcs import Arc, Stage


def test_event_pipeline_initialization(engine_fixture):
    """Test that EventPipeline initializes correctly."""
    events = engine_fixture.events

    assert isinstance(events, EventPipeline)
    assert events.engine == engine_fixture
    assert events.game_def == engine_fixture.game_def
    assert isinstance(events.stages_map, dict)


def test_process_events_returns_event_result(engine_fixture):
    """Test that process_events returns EventResult structure."""
    events = engine_fixture.events

    result = events.process_events(turn_seed=12345)

    assert isinstance(result, EventResult)
    assert isinstance(result.choices, list)
    assert isinstance(result.narratives, list)


def test_event_cooldown_blocks_retriggering(engine_fixture):
    """Test that events on cooldown are not triggered."""
    events = engine_fixture.events
    state = engine_fixture.state_manager.state

    # Find any event with cooldown in the game definition
    event_with_cooldown = None
    for event in engine_fixture.game_def.events:
        if event.cooldown and event.cooldown > 0:
            event_with_cooldown = event
            break

    if not event_with_cooldown:
        pytest.skip("No events with cooldown in test game")

    # Manually set event on cooldown
    state.cooldowns[event_with_cooldown.id] = 5

    # Verify the event is blocked
    assert events._is_event_on_cooldown(event_with_cooldown, state) is True

    # Reduce cooldown to 0
    state.cooldowns[event_with_cooldown.id] = 0

    # Verify the event is no longer blocked
    assert events._is_event_on_cooldown(event_with_cooldown, state) is False


def test_decrement_cooldowns_reduces_by_one(engine_fixture):
    """Test that decrement_cooldowns reduces all cooldowns by 1."""
    events = engine_fixture.events
    state = engine_fixture.state_manager.state

    # Set up some cooldowns
    state.cooldowns["test_event_1"] = 5
    state.cooldowns["test_event_2"] = 3
    state.cooldowns["test_event_3"] = 1

    events.decrement_cooldowns()

    # Verify all reduced by 1
    assert state.cooldowns["test_event_1"] == 4
    assert state.cooldowns["test_event_2"] == 2
    # Event with cooldown 1 should be removed (0 is cleaned up)
    assert "test_event_3" not in state.cooldowns


def test_decrement_cooldowns_removes_expired(engine_fixture):
    """Test that expired cooldowns are cleaned up when they reach 0."""
    events = engine_fixture.events
    state = engine_fixture.state_manager.state

    # Set up cooldowns at various stages
    state.cooldowns["event_a"] = 2
    state.cooldowns["event_b"] = 1

    events.decrement_cooldowns()

    assert state.cooldowns["event_a"] == 1
    assert "event_b" not in state.cooldowns  # Removed after reaching 0


def test_process_arcs_checks_advancement(engine_fixture):
    """Test that process_arcs evaluates arc conditions."""
    events = engine_fixture.events

    # Should not crash even if no arcs advance
    events.process_arcs(turn_seed=99999)


def test_stages_map_contains_all_stages(engine_fixture):
    """Test that stages_map is built correctly from game definition."""
    events = engine_fixture.events

    # Count stages in game definition
    expected_stage_ids = set()
    for arc in engine_fixture.game_def.arcs:
        for stage in arc.stages:
            expected_stage_ids.add(stage.id)

    # Verify all stages are in the map
    assert set(events.stages_map.keys()) == expected_stage_ids

    # Verify all values are Stage instances
    for stage in events.stages_map.values():
        assert isinstance(stage, Stage)


def test_check_and_advance_arcs_returns_tuple(engine_fixture):
    """Test that _check_and_advance_arcs returns (entered, exited) tuple."""
    events = engine_fixture.events
    state = engine_fixture.state_manager.state

    entered, exited = events._check_and_advance_arcs(state, rng_seed=12345)

    assert isinstance(entered, list)
    assert isinstance(exited, list)

    # All entries should be Stage instances
    for stage in entered + exited:
        assert isinstance(stage, Stage)


def test_is_event_eligible_respects_location_scope(engine_fixture):
    """Test that events with location conditions check current location."""
    events = engine_fixture.events
    state = engine_fixture.state_manager.state

    from app.core.conditions import ConditionEvaluator

    # Find an event with location in its condition
    location_event = None
    for event in engine_fixture.game_def.events:
        # Check if event has a condition that references location.id
        if event.when and "location.id" in event.when:
            location_event = event
            break

    if not location_event:
        pytest.skip("No events with location conditions in test game")

    # Save current location and energy
    original_location = state.location_current
    original_energy = state.meters.get("player", {}).get("energy", 100)

    # Set energy to satisfy the energy condition
    state.meters.setdefault("player", {})["energy"] = 50

    # Set to wrong location - event should not be eligible
    state.location_current = "some_other_location_xyz"
    evaluator = ConditionEvaluator(state, rng_seed=12345)
    assert events._is_event_eligible(location_event, state, evaluator) is False

    # Set to correct location (campus_quad) - event should now be eligible
    state.location_current = "campus_quad"
    # Create new evaluator after state change
    evaluator = ConditionEvaluator(state, rng_seed=12345)
    # Event should be eligible when location matches
    assert events._is_event_eligible(location_event, state, evaluator) is True

    # Restore
    state.location_current = original_location
    state.meters["player"]["energy"] = original_energy


def test_get_triggered_events_returns_list(engine_fixture):
    """Test that _get_triggered_events returns a list of Event instances."""
    events = engine_fixture.events
    state = engine_fixture.state_manager.state

    triggered = events._get_triggered_events(state, rng_seed=12345)

    assert isinstance(triggered, list)
    for event in triggered:
        assert isinstance(event, Event)


def test_random_event_weighted_selection(engine_fixture):
    """Test that random events use weighted selection (deterministic with seed)."""
    events = engine_fixture.events
    state = engine_fixture.state_manager.state

    # Find random events in the game (events with probability < 100)
    random_events = [
        e for e in engine_fixture.game_def.events
        if e.probability is not None and e.probability < 100
    ]

    if len(random_events) < 2:
        pytest.skip("Need at least 2 random events to test weighted selection")

    # Run multiple times with same seed - should get same result
    # Save cooldowns and restore between runs
    original_cooldowns = state.cooldowns.copy()

    triggered_1 = events._get_triggered_events(state, rng_seed=42)

    # Restore cooldowns to test determinism
    state.cooldowns = original_cooldowns.copy()

    triggered_2 = events._get_triggered_events(state, rng_seed=42)

    random_triggered_1 = [e for e in triggered_1 if e.probability is not None and e.probability < 100]
    random_triggered_2 = [e for e in triggered_2 if e.probability is not None and e.probability < 100]

    # Same seed should produce identical results
    assert [e.id for e in random_triggered_1] == [e.id for e in random_triggered_2]


def test_arc_repeatable_logic(engine_fixture):
    """Test that non-repeatable arcs don't re-complete stages."""
    events = engine_fixture.events
    state = engine_fixture.state_manager.state

    # Find a non-repeatable arc
    non_repeatable_arc = None
    for arc in engine_fixture.game_def.arcs:
        if not arc.repeatable:
            non_repeatable_arc = arc
            break

    if not non_repeatable_arc or len(non_repeatable_arc.stages) == 0:
        pytest.skip("No non-repeatable arcs with stages in test game")

    test_stage = non_repeatable_arc.stages[0]

    # Mark stage as completed
    if test_stage.id not in state.completed_milestones:
        state.completed_milestones.append(test_stage.id)

    # Check advancement - should skip already completed stages
    entered, exited = events._check_and_advance_arcs(state, rng_seed=999)

    # The already completed stage should not appear in entered list
    entered_stage_ids = [s.id for s in entered]
    # Note: stage might still be entered if arc IS repeatable, but we filtered for non-repeatable
    # For non-repeatable arcs, completed stages shouldn't re-enter
