"""
Tests for the v3 GameLoader and Pydantic models.
"""
import pytest
from app.core.game_loader import GameLoader
from app.models.game import GameDefinition

# List of all game IDs that should be successfully loaded
VALID_GAME_IDS = [
    "coffeeshop_date",
    "college_romance"
]


@pytest.mark.parametrize("game_id", VALID_GAME_IDS)
def test_load_valid_game(game_id: str):
    """
    Tests that the GameLoader can successfully load a valid, converted game
    and parse it into the correct Pydantic models without errors.
    """
    loader = GameLoader()
    game_def = None

    try:
        game_def = loader.load_game(game_id)
    except Exception as e:
        pytest.fail(f"GameLoader failed to load '{game_id}': {e}")

    # --- Assertions to validate the loaded data ---

    assert isinstance(game_def, GameDefinition), "Loader did not return a GameDefinition object."

    # 1. Validate MetaConfig
    # The coffee shop game id is 'coffee_test' in its meta block
    expected_id = "coffee_test" if game_id == "coffeeshop_date" else game_id
    assert game_def.meta.id == expected_id, f"Incorrect game ID loaded for {game_id}."
    assert game_def.meta.title is not None, f"Game title for {game_id} is missing."

    # 2. Validate StartConfig
    assert game_def.start.node is not None, f"Start node for {game_id} is missing."
    assert game_def.start.location is not None, f"Start location for {game_id} is missing."

    # 3. Validate that content lists were populated from included files
    assert len(game_def.characters) > 0, f"Characters were not loaded for {game_id}."
    assert len(game_def.nodes) > 0, f"Nodes were not loaded for {game_id}."
    assert len(game_def.zones) > 0, f"Zones were not loaded for {game_id}."
    assert len(game_def.items) > 0, f"Items were not loaded for {game_id}."

    # college_romance also has arcs and events
    if game_id == "college_romance":
        assert len(game_def.arcs) > 0, f"Arcs were not loaded for {game_id}."
        assert len(game_def.events) > 0, f"Events were not loaded for {game_id}."

    print(f"\n✅ Successfully loaded and validated '{game_id}' game definition.")