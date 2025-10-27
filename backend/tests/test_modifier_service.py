"""Tests for ModifierService (migrated from ModifierManager)."""

import pytest
from tests_v2.conftest_services import engine_fixture, engine_with_modifiers
from app.engine.modifiers import ModifierService
from app.models.effects import ApplyModifierEffect, RemoveModifierEffect


def test_modifier_service_initialization(engine_fixture):
    """Test that ModifierService initializes correctly."""
    modifiers = engine_fixture.modifiers

    assert isinstance(modifiers, ModifierService)
    assert modifiers.engine == engine_fixture
    assert modifiers.game_def == engine_fixture.game_def
    assert isinstance(modifiers.library, dict)


def test_modifier_library_loads_from_game_def(engine_fixture):
    """Test that modifier library is populated from game definition."""
    modifiers = engine_fixture.modifiers

    # If game has modifiers config with library, library should be populated
    if (hasattr(engine_fixture.game_def, "modifiers") and
        engine_fixture.game_def.modifiers and
        hasattr(engine_fixture.game_def.modifiers, "library") and
        engine_fixture.game_def.modifiers.library):
        assert len(modifiers.library) > 0
    else:
        # If no modifiers in game, library should be empty
        assert len(modifiers.library) == 0


def test_apply_effect_adds_modifier_to_character(engine_with_modifiers):
    """Test that ApplyModifierEffect adds a modifier to character state."""
    modifiers = engine_with_modifiers.modifiers
    state = engine_with_modifiers.state_manager.state

    # Use a known modifier from the fixture
    modifier_id = "energized"

    # Ensure player has modifiers list
    if "player" not in state.modifiers:
        state.modifiers["player"] = []

    # Apply modifier
    effect = ApplyModifierEffect(
        type="apply_modifier",
        target="player",
        modifier_id=modifier_id,
        duration=60
    )
    modifiers.apply_effect(effect, state)

    # Verify modifier was added
    active_ids = [m["id"] for m in state.modifiers["player"]]
    assert modifier_id in active_ids

    # Verify duration was set
    active_mod = next(m for m in state.modifiers["player"] if m["id"] == modifier_id)
    assert active_mod["duration"] == 60


def test_apply_effect_removes_modifier_from_character(engine_with_modifiers):
    """Test that RemoveModifierEffect removes a modifier from character state."""
    modifiers = engine_with_modifiers.modifiers
    state = engine_with_modifiers.state_manager.state

    # Use a known modifier from the fixture
    modifier_id = "energized"

    # Ensure player has modifiers list and add a test modifier
    if "player" not in state.modifiers:
        state.modifiers["player"] = []

    state.modifiers["player"].append({"id": modifier_id, "duration": 100})

    # Remove modifier
    effect = RemoveModifierEffect(
        type="remove_modifier",
        target="player",
        modifier_id=modifier_id
    )
    modifiers.apply_effect(effect, state)

    # Verify modifier was removed
    active_ids = [m["id"] for m in state.modifiers["player"]]
    assert modifier_id not in active_ids


def test_modifier_not_added_twice(engine_with_modifiers):
    """Test that applying the same modifier twice doesn't duplicate it."""
    modifiers = engine_with_modifiers.modifiers
    state = engine_with_modifiers.state_manager.state

    # Use a known modifier from the fixture
    modifier_id = "energized"

    if "player" not in state.modifiers:
        state.modifiers["player"] = []

    # Apply same modifier twice
    effect = ApplyModifierEffect(
        type="apply_modifier",
        target="player",
        modifier_id=modifier_id,
        duration=60
    )
    modifiers.apply_effect(effect, state)
    initial_count = len(state.modifiers["player"])

    modifiers.apply_effect(effect, state)  # Apply again

    # Should still have same count (not duplicated)
    assert len(state.modifiers["player"]) == initial_count


def test_tick_durations_decrements_time(engine_with_modifiers):
    """Test that tick_durations reduces modifier durations."""
    modifiers = engine_with_modifiers.modifiers
    state = engine_with_modifiers.state_manager.state

    # Use a known modifier from the fixture
    modifier_id = "energized"

    if "player" not in state.modifiers:
        state.modifiers["player"] = []

    state.modifiers["player"].append({"id": modifier_id, "duration": 100})

    # Tick 30 minutes
    modifiers.tick_durations(state, 30)

    # Verify duration decreased
    active_mod = next(m for m in state.modifiers["player"] if m["id"] == modifier_id)
    assert active_mod["duration"] == 70


def test_tick_durations_removes_expired_modifiers(engine_with_modifiers):
    """Test that expired modifiers are removed after ticking."""
    modifiers = engine_with_modifiers.modifiers
    state = engine_with_modifiers.state_manager.state

    # Use a known modifier from the fixture
    modifier_id = "energized"

    if "player" not in state.modifiers:
        state.modifiers["player"] = []

    state.modifiers["player"].append({"id": modifier_id, "duration": 20})

    # Tick past expiration
    modifiers.tick_durations(state, 30)

    # Verify modifier was removed
    active_ids = [m["id"] for m in state.modifiers["player"]]
    assert modifier_id not in active_ids


def test_tick_durations_with_zero_minutes(engine_with_modifiers):
    """Test that ticking 0 minutes does nothing."""
    modifiers = engine_with_modifiers.modifiers
    state = engine_with_modifiers.state_manager.state

    # Use a known modifier from the fixture
    modifier_id = "energized"

    if "player" not in state.modifiers:
        state.modifiers["player"] = []

    state.modifiers["player"].append({"id": modifier_id, "duration": 100})

    # Tick 0 minutes
    modifiers.tick_durations(state, 0)

    # Verify duration unchanged
    active_mod = next(m for m in state.modifiers["player"] if m["id"] == modifier_id)
    assert active_mod["duration"] == 100


def test_update_modifiers_for_turn_evaluates_conditions(engine_fixture):
    """Test that update_modifiers_for_turn checks auto-activation conditions."""
    modifiers = engine_fixture.modifiers
    state = engine_fixture.state_manager.state

    # Should not crash even if no modifiers have 'when' conditions
    modifiers.update_modifiers_for_turn(state, rng_seed=12345)


def test_apply_effect_ignores_unknown_modifier(engine_fixture):
    """Test that applying an unknown modifier is safely ignored."""
    modifiers = engine_fixture.modifiers
    state = engine_fixture.state_manager.state

    if "player" not in state.modifiers:
        state.modifiers["player"] = []

    initial_count = len(state.modifiers["player"])

    # Try to apply non-existent modifier
    effect = ApplyModifierEffect(
        type="apply_modifier",
        target="player",
        modifier_id="nonexistent_modifier_xyz",
        duration=60
    )
    modifiers.apply_effect(effect, state)

    # Should not have added anything
    assert len(state.modifiers["player"]) == initial_count


def test_remove_effect_ignores_unknown_modifier(engine_fixture):
    """Test that removing an unknown modifier is safely ignored."""
    modifiers = engine_fixture.modifiers
    state = engine_fixture.state_manager.state

    if "player" not in state.modifiers:
        state.modifiers["player"] = []

    # Try to remove non-existent modifier (should not crash)
    effect = RemoveModifierEffect(
        type="remove_modifier",
        target="player",
        modifier_id="nonexistent_modifier_xyz"
    )
    modifiers.apply_effect(effect, state)


def test_modifier_duration_uses_default_if_not_specified(engine_with_modifiers):
    """Test that modifiers use default duration when no override provided."""
    modifiers = engine_with_modifiers.modifiers
    state = engine_with_modifiers.state_manager.state

    # Use a known modifier with default duration from the fixture
    modifier_with_default = "energized"  # Has duration=60

    if "player" not in state.modifiers:
        state.modifiers["player"] = []

    # Apply without duration override
    effect = ApplyModifierEffect(
        type="apply_modifier",
        target="player",
        modifier_id=modifier_with_default,
        duration=None  # No override
    )
    modifiers.apply_effect(effect, state)

    # Should use default duration
    active_mod = next(m for m in state.modifiers["player"] if m["id"] == modifier_with_default)
    expected_duration = modifiers.library[modifier_with_default].duration
    assert active_mod["duration"] == expected_duration


def test_tick_durations_handles_none_duration(engine_with_modifiers):
    """Test that modifiers with None duration are not decremented."""
    modifiers = engine_with_modifiers.modifiers
    state = engine_with_modifiers.state_manager.state

    # Use a known modifier from the fixture
    modifier_id = "energized"

    if "player" not in state.modifiers:
        state.modifiers["player"] = []

    # Add modifier with None duration (permanent)
    state.modifiers["player"].append({"id": modifier_id, "duration": None})

    # Tick time
    modifiers.tick_durations(state, 30)

    # Verify modifier still exists with None duration
    active_mod = next(m for m in state.modifiers["player"] if m["id"] == modifier_id)
    assert active_mod["duration"] is None
