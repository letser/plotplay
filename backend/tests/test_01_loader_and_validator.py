import re

import pytest

from app.core.validator import GameValidator


def test_fixture_game_loads_and_validates(fixture_loader):
    """Verify Fixture game loads and validates."""
    game = fixture_loader.load_game("checklist_demo")
    assert game.meta.id == "checklist_demo"
    GameValidator(game).validate()
    # the include file should have been merged, so the intro node is available
    intro = [node for node in game.nodes if node.id == "intro"]
    assert intro, "Included nodes were not merged into the manifest"


def test_fixture_game_has_expected_start_state(fixture_loader):
    """Verify Fixture game has the expected start state."""
    game = fixture_loader.load_game("checklist_demo")
    state = game.index
    # start location/node exist and are wired into indices
    assert game.start.location in state.locations
    assert game.start.node in state.nodes
    assert state.location_to_zone.get(game.start.location) == "campus"


def test_loader_rejects_unknown_game(fixture_loader):
    """Verify Loader rejects an unknown game."""
    with pytest.raises(ValueError):
        fixture_loader.load_game("does_not_exist")


# ============================================================================
# VALIDATION & SECURITY TESTS
# ============================================================================

def test_enforce_max_include_depth_no_nested_includes(fixture_loader):
    """Verify Nested includes beyond depth 1 are rejected."""
    with pytest.raises(ValueError, match="Nested includes"):
        fixture_loader.load_game("nested_depth")


def test_validate_file_paths_reject_parent_directory(fixture_loader):
    """Verify Include paths with parent directory traversal are rejected."""
    with pytest.raises(ValueError, match="Invalid include file path"):
        fixture_loader.load_game("bad_include_parent")


def test_validate_file_paths_reject_absolute_paths(fixture_loader):
    """Verify Absolute include paths are rejected."""
    with pytest.raises(ValueError, match="Invalid include file path"):
        fixture_loader.load_game("bad_include_absolute")


def test_detect_circular_references_in_node_transitions(fixture_loader):
    """Verify Closed goto cycles are detected and reported."""
    game = fixture_loader.load_game("cycle_game")
    validator = GameValidator(game)
    validator.validate()
    assert any("circular" in warning.lower() for warning in validator.warnings)


def test_detect_circular_references_in_arc_stages(fixture_loader):
    """Verify Duplicate arc stage IDs are rejected to avoid cycles."""
    pattern = re.compile(r"duplicate.*stages|stages.*duplicate", re.IGNORECASE)
    with pytest.raises(ValueError, match=pattern):
        fixture_loader.load_game("bad_arc")


def test_validate_time_configuration_sanity(fixture_loader):
    """Verify Time configuration enforces sane defaults and ranges."""
    with pytest.raises(ValueError) as exc_info:
        fixture_loader.load_game("bad_time")
    message = str(exc_info.value)
    assert "slot_windows" in message.lower() or "overlap" in message.lower()
    assert "week_days" in message.lower()
    assert "start.time" in message.lower()
    assert "category" in message.lower()


def test_validate_cross_references_item_ids(fixture_loader):
    """Verify Item IDs referenced in effects must exist."""
    pattern = re.compile(r"unknown item|does not exist", re.IGNORECASE)
    with pytest.raises(ValueError, match=pattern):
        fixture_loader.load_game("bad_item_ref")


def test_validate_cross_references_character_ids(fixture_loader):
    """Verify Character IDs referenced in effects must exist."""
    pattern = re.compile(r"unknown character|does not exist|not a defined character", re.IGNORECASE)
    with pytest.raises(ValueError, match=pattern):
        fixture_loader.load_game("bad_character_ref")


def test_validate_cross_references_location_ids(fixture_loader):
    """Verify Location references must resolve."""
    with pytest.raises(ValueError) as exc_info:
        fixture_loader.load_game("bad_location_ref")
    assert "start location 'missing_loc'" in str(exc_info.value).lower()


def test_validate_cross_references_node_ids(fixture_loader):
    """Verify Node references (start and goto) must resolve."""
    with pytest.raises(ValueError) as exc_info:
        fixture_loader.load_game("bad_node_ref")
    assert "start node 'missing_start' does not exist" in str(exc_info.value).lower()
