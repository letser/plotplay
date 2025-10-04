"""
Tests for the v3 GameLoader, Models, and Validator.
"""
import pytest
import yaml
from pathlib import Path
from app.core.game_loader import GameLoader

# List of all game IDs that should be successfully loaded
VALID_GAME_IDS = [
    "coffeeshop_date",
    "college_romance"
]

@pytest.fixture
def broken_game_loader(tmp_path: Path) -> GameLoader:
    """
    Creates a temporary game directory with a broken node reference
    for testing the GameValidator.
    """
    game_id = "broken_game"
    game_dir = tmp_path / game_id
    game_dir.mkdir()

    # Create a minimal, valid manifest
    manifest_data = {
        'meta': {'id': 'broken', 'title': 'Broken Game', 'author': 'tester'},
        'start': {'node': 'start', 'location': {'zone': 'test', 'id': 'test'}},
        'includes': ['nodes.yaml']
    }
    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest_data, f)

    # Load the valid 'coffeeshop_date' nodes file
    with open("games/coffeeshop_date/nodes.yaml", "r") as f:
        nodes_data = yaml.safe_load(f)

    # Deliberately break a reference
    nodes_data["nodes"][0]["transitions"][0]["to"] = "non_existent_node_id"

    # Write the broken nodes file to the temp directory
    with open(game_dir / "nodes.yaml", "w") as f:
        yaml.dump(nodes_data, f)

    # Return a GameLoader pointed at the temporary directory
    return GameLoader(games_dir=tmp_path)


@pytest.mark.parametrize("game_id", VALID_GAME_IDS)
def test_load_valid_game(game_id: str):
    """
    Tests that the GameLoader can successfully load a valid, converted game.
    """
    loader = GameLoader()
    try:
        loader.load_game(game_id)
    except Exception as e:
        pytest.fail(f"GameLoader failed to load '{game_id}': {e}")
    print(f"\n✅ Successfully loaded and validated '{game_id}' game definition.")


def test_validator_catches_bad_node_reference(broken_game_loader: GameLoader):
    """
    Tests that the GameValidator raises a ValueError when loading a game
    with a broken internal reference.
    """
    with pytest.raises(ValueError, match="Game validation failed"):
        broken_game_loader.load_game("broken_game")

    print("\n✅ Successfully caught broken node reference as expected.")


def test_loader_raises_error_for_non_existent_game():
    """
    Tests that the GameLoader raises an error for a non-existent game.
    """
    loader = GameLoader()
    with pytest.raises(ValueError, match="not found or does not contain a game.yaml"):
        loader.load_game("non_existent_game")

    print("\n✅ Successfully caught non-existent game directory as expected.")