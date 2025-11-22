import pytest

from app.core.loader import GameLoader
from app.core.validator import GameValidator


def test_fixture_game_loads_and_validates(fixture_loader):
    game = fixture_loader.load_game("checklist_demo")
    assert game.meta.id == "checklist_demo"
    GameValidator(game).validate()
    # include file should have been merged, so intro node is available
    intro = [node for node in game.nodes if node.id == "intro"]
    assert intro, "Included nodes were not merged into the manifest"


def test_fixture_game_has_expected_start_state(fixture_loader):
    game = fixture_loader.load_game("checklist_demo")
    state = game.index
    # start location/node exist and are wired into indices
    assert game.start.location in state.locations
    assert game.start.node in state.nodes
    assert state.location_to_zone.get(game.start.location) == "campus"


def test_loader_rejects_unknown_game(tmp_path, loader):
    game_dir = tmp_path / "bad_game"
    game_dir.mkdir()
    manifest = game_dir / "game.yaml"
    manifest.write_text(
        "meta:\n"
        "  id: bad_game\n"
        "unknown_root: true\n",
        encoding="utf-8",
    )
    sandbox_loader = GameLoader(games_dir=tmp_path)
    with pytest.raises(ValueError):
        sandbox_loader.load_game(game_dir.name)


# ============================================================================
# VALIDATION & SECURITY TESTS
# ============================================================================

@pytest.mark.skip("TODO: Implement max include depth enforcement test")
def test_enforce_max_include_depth_no_nested_includes(tmp_path):
    """
    Verify that nested includes (depth > 1) are rejected.

    Should test:
    - game.yaml includes file_a.yaml
    - file_a.yaml includes file_b.yaml (nested)
    - Loader rejects with error
    - Error message mentions include depth
    """
    pass


@pytest.mark.skip("TODO: Implement file path security test - parent directory")
def test_validate_file_paths_reject_parent_directory(tmp_path):
    """
    Verify that include paths with .. are rejected.

    Should test:
    - game.yaml includes "../outside.yaml"
    - Loader rejects with security error
    - File outside game folder not loaded
    """
    pass


@pytest.mark.skip("TODO: Implement file path security test - absolute paths")
def test_validate_file_paths_reject_absolute_paths(tmp_path):
    """
    Verify that absolute include paths are rejected.

    Should test:
    - game.yaml includes "/etc/passwd"
    - game.yaml includes "C:\\Windows\\system.ini"
    - Loader rejects with security error
    """
    pass


@pytest.mark.skip("TODO: Implement circular reference detection test - nodes")
def test_detect_circular_references_in_node_transitions(tmp_path):
    """
    Verify that circular node transitions are detected.

    Should test:
    - Node A transitions to Node B
    - Node B transitions to Node A
    - Validator detects circular transition
    - Warning or error logged
    """
    pass


@pytest.mark.skip("TODO: Implement circular reference detection test - arcs")
def test_detect_circular_references_in_arc_stages(tmp_path):
    """
    Verify that circular arc stage progressions are detected.

    Should test:
    - Arc stage A progresses to stage B
    - Stage B condition references stage A
    - Validator detects potential circular progression
    """
    pass


@pytest.mark.skip("TODO: Implement time configuration sanity test")
def test_validate_time_configuration_sanity(tmp_path):
    """
    Verify that time configuration is validated.

    Should test:
    - Slot windows non-overlapping
    - Time categories all have positive values
    - Start time within valid range [0, 1439]
    - Week_days list has 7 entries
    - Start_day exists in week_days
    """
    pass


@pytest.mark.skip("TODO: Implement cross-reference validation - items")
def test_validate_cross_references_item_ids(tmp_path):
    """
    Verify that item ID references are validated.

    Should test:
    - Node effect references non-existent item
    - Validator rejects with clear error
    - Error message identifies missing item ID
    """
    pass


@pytest.mark.skip("TODO: Implement cross-reference validation - characters")
def test_validate_cross_references_character_ids(tmp_path):
    """
    Verify that character ID references are validated.

    Should test:
    - Effect references non-existent character
    - Schedule references non-existent character
    - Validator rejects with clear error
    """
    pass


@pytest.mark.skip("TODO: Implement cross-reference validation - locations")
def test_validate_cross_references_location_ids(tmp_path):
    """
    Verify that location ID references are validated.

    Should test:
    - Start location doesn't exist
    - Connection to non-existent location
    - Validator rejects with clear error
    """
    pass


@pytest.mark.skip("TODO: Implement cross-reference validation - nodes")
def test_validate_cross_references_node_ids(tmp_path):
    """
    Verify that node ID references are validated.

    Should test:
    - Start node doesn't exist
    - Transition to non-existent node
    - goto effect to non-existent node
    - Validator rejects with clear error
    """
    pass
