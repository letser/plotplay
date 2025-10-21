"""Tests for ClothingService (migrated from ClothingManager)."""

import pytest
from tests_v2.conftest_services import engine_fixture
from app.engine.clothing import ClothingService
from app.models.effects import ClothingChangeEffect


def test_clothing_service_initialization(engine_fixture):
    """Test that ClothingService initializes correctly."""
    clothing = engine_fixture.clothing

    assert isinstance(clothing, ClothingService)
    assert clothing.engine == engine_fixture
    assert clothing.game_def == engine_fixture.game_def
    assert clothing.state == engine_fixture.state_manager.state


def test_get_character_appearance_unknown_character(engine_fixture):
    """Test that unknown characters return default message."""
    clothing = engine_fixture.clothing

    appearance = clothing.get_character_appearance("nonexistent_character_xyz")

    assert appearance == "an unknown outfit"


def test_apply_effect_ignores_unknown_character(engine_fixture):
    """Test that effects for unknown characters are ignored."""
    clothing = engine_fixture.clothing

    effect = ClothingChangeEffect(
        type="outfit_change",
        character="nonexistent_character_xyz",
        outfit="some_outfit"
    )

    # Should not crash
    clothing.apply_effect(effect)


def test_apply_ai_changes_ignores_unknown_character(engine_fixture):
    """Test that AI changes for unknown characters are ignored."""
    clothing = engine_fixture.clothing

    ai_changes = {
        "nonexistent_character_xyz": {
            "removed": ["top"]
        }
    }

    # Should not crash
    clothing.apply_ai_changes(ai_changes)


def test_clothing_state_structure_if_initialized(engine_fixture):
    """Test clothing state structure for initialized characters."""
    state = engine_fixture.state_manager.state

    # If any clothing states exist, verify structure
    for char_id, clothing_state in state.clothing_states.items():
        # State should be a dict
        assert isinstance(clothing_state, dict)

        # If it has the full structure, verify it
        if "current_outfit" in clothing_state:
            assert "layers" in clothing_state
            assert isinstance(clothing_state["layers"], dict)


def test_get_character_appearance_with_valid_character(engine_fixture):
    """Test getting appearance for a character with clothing."""
    clothing = engine_fixture.clothing
    state = engine_fixture.state_manager.state

    # Find any character with proper clothing structure
    valid_char = None
    for char_id, clothing_state in state.clothing_states.items():
        if isinstance(clothing_state, dict) and "current_outfit" in clothing_state:
            valid_char = char_id
            break

    if not valid_char:
        pytest.skip("No characters with full clothing structure in test game")

    appearance = clothing.get_character_appearance(valid_char)

    assert isinstance(appearance, str)
    assert len(appearance) > 0


def test_apply_effect_clothing_set_with_valid_character(engine_fixture):
    """Test changing a specific layer state for a valid character."""
    clothing = engine_fixture.clothing
    state = engine_fixture.state_manager.state

    # Find a character with proper structure
    valid_char = None
    for char_id, clothing_state in state.clothing_states.items():
        if (isinstance(clothing_state, dict) and
            "layers" in clothing_state and
            len(clothing_state["layers"]) > 0):
            valid_char = char_id
            break

    if not valid_char:
        pytest.skip("No characters with layers in test game")

    layers = state.clothing_states[valid_char]["layers"]
    layer_name = list(layers.keys())[0]

    # Change layer state to displaced
    effect = ClothingChangeEffect(
        type="clothing_set",
        character=valid_char,
        layer=layer_name,
        state="displaced"
    )
    clothing.apply_effect(effect)

    # Verify layer state changed
    assert state.clothing_states[valid_char]["layers"][layer_name] == "displaced"


def test_apply_ai_changes_removed_layer_with_valid_character(engine_fixture):
    """Test AI removing a clothing layer for a valid character."""
    clothing = engine_fixture.clothing
    state = engine_fixture.state_manager.state

    # Find a character with layers
    valid_char = None
    for char_id, clothing_state in state.clothing_states.items():
        if (isinstance(clothing_state, dict) and
            "layers" in clothing_state and
            len(clothing_state["layers"]) > 0):
            valid_char = char_id
            break

    if not valid_char:
        pytest.skip("No characters with layers in test game")

    layers = state.clothing_states[valid_char]["layers"]
    layer_name = list(layers.keys())[0]

    # AI removes the layer
    ai_changes = {
        valid_char: {
            "removed": [layer_name]
        }
    }
    clothing.apply_ai_changes(ai_changes)

    # Verify layer is removed
    assert state.clothing_states[valid_char]["layers"][layer_name] == "removed"


def test_apply_ai_changes_displaced_layer_with_valid_character(engine_fixture):
    """Test AI displacing a clothing layer for a valid character."""
    clothing = engine_fixture.clothing
    state = engine_fixture.state_manager.state

    # Find a character with layers
    valid_char = None
    for char_id, clothing_state in state.clothing_states.items():
        if (isinstance(clothing_state, dict) and
            "layers" in clothing_state and
            len(clothing_state["layers"]) > 0):
            valid_char = char_id
            break

    if not valid_char:
        pytest.skip("No characters with layers in test game")

    layers = state.clothing_states[valid_char]["layers"]
    layer_name = list(layers.keys())[0]

    # Ensure layer is intact first
    state.clothing_states[valid_char]["layers"][layer_name] = "intact"

    # AI displaces the layer
    ai_changes = {
        valid_char: {
            "displaced": [layer_name]
        }
    }
    clothing.apply_ai_changes(ai_changes)

    # Verify layer is displaced
    assert state.clothing_states[valid_char]["layers"][layer_name] == "displaced"


def test_apply_ai_changes_wont_displace_removed_layer_with_valid_character(engine_fixture):
    """Test that displaced command won't override removed state."""
    clothing = engine_fixture.clothing
    state = engine_fixture.state_manager.state

    # Find a character with layers
    valid_char = None
    for char_id, clothing_state in state.clothing_states.items():
        if (isinstance(clothing_state, dict) and
            "layers" in clothing_state and
            len(clothing_state["layers"]) > 0):
            valid_char = char_id
            break

    if not valid_char:
        pytest.skip("No characters with layers in test game")

    layers = state.clothing_states[valid_char]["layers"]
    layer_name = list(layers.keys())[0]

    # Set layer to removed
    state.clothing_states[valid_char]["layers"][layer_name] = "removed"

    # AI tries to displace (should be ignored since not intact)
    ai_changes = {
        valid_char: {
            "displaced": [layer_name]
        }
    }
    clothing.apply_ai_changes(ai_changes)

    # Verify layer is still removed (not displaced)
    assert state.clothing_states[valid_char]["layers"][layer_name] == "removed"
