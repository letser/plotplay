from pathlib import Path

import pytest

from app.core.game_loader import GameLoader
from app.models.game import GameDefinition

from tests.conftest import minimal_game, load_yaml, write_yaml

# List of all game IDs that should be successfully loaded
VALID_GAME_IDS = [
    "coffeeshop_date",
    "college_romance"
]


@pytest.mark.parametrize("game_id", VALID_GAME_IDS)
def test_load_valid_game(game_id: str):
    """
    §4.4: Test that the GameLoader can successfully load valid games.
    Tests a basic loading and validation pipeline.
    """
    loader = GameLoader()
    game_def = loader.load_game(game_id)

    # Verify it returns a GameDefinition
    assert isinstance(game_def, GameDefinition)

    # Verify required meta fields are present
    assert game_def.meta.id == game_id
    assert game_def.meta.title
    assert game_def.meta.version
    assert len(game_def.meta.authors) > 0

    # Verify start config exists
    assert game_def.start.node
    assert game_def.start.location

    print(f"✅ Successfully loaded '{game_id}' with all required fields")


def test_game_loader_parses_minimal_spec(tmp_path):
    game_dir = minimal_game(tmp_path)
    loader = GameLoader(games_dir=tmp_path)

    game_def = loader.load_game(game_dir.name)

    assert game_def.meta.title == "Campus Story"
    assert game_def.start.location == "campus_quad"
    assert game_def.start.node == "intro"
    assert game_def.wardrobe.outfits[0].id == "player_outfit"
    assert any(char.id == "friend" for char in game_def.characters)


def test_game_loader_raises_for_missing_start_location(tmp_path):
    game_dir = minimal_game(tmp_path)
    manifest = load_yaml(game_dir / "game.yaml")
    del manifest["start"]["location"]
    write_yaml(game_dir / "game.yaml", manifest)

    loader = GameLoader(games_dir=tmp_path)

    with pytest.raises(ValueError, match="start.location") as exc:
        loader.load_game(game_dir.name)


def test_game_loader_rejects_unknown_root_in_manifest(tmp_path: Path):
    game_dir = minimal_game(tmp_path)
    manifest = load_yaml(game_dir / "game.yaml")
    manifest["mystery_block"] = {}
    write_yaml(game_dir / "game.yaml", manifest)

    loader = GameLoader(games_dir=tmp_path)

    with pytest.raises(ValueError, match="Unknown top-level keys"):
        loader.load_game(game_dir.name)


def test_game_loader_rejects_unknown_root_in_include(tmp_path: Path):
    game_dir = minimal_game(tmp_path)
    write_yaml(game_dir / "extra.yaml", {"bogus": {"value": 1}})

    manifest = load_yaml(game_dir / "game.yaml")
    manifest["includes"].append("extra.yaml")
    write_yaml(game_dir / "game.yaml", manifest)

    loader = GameLoader(games_dir=tmp_path)

    with pytest.raises(ValueError, match="Unknown top-level keys"):
        loader.load_game(game_dir.name)


def test_game_loader_rejects_nested_includes(tmp_path: Path):
    game_dir = minimal_game(tmp_path)
    write_yaml(game_dir / "nested.yaml", {"nodes": [], "includes": ["other.yaml"]})

    manifest = load_yaml(game_dir / "game.yaml")
    manifest["includes"].append("nested.yaml")
    write_yaml(game_dir / "game.yaml", manifest)

    loader = GameLoader(games_dir=tmp_path)

    with pytest.raises(ValueError, match="Nested includes detected"):
        loader.load_game(game_dir.name)


def test_game_loader_requires_matching_meta_id(tmp_path: Path):
    game_dir = minimal_game(tmp_path)
    manifest = load_yaml(game_dir / "game.yaml")
    manifest["meta"]["id"] = "other_story"
    write_yaml(game_dir / "game.yaml", manifest)

    loader = GameLoader(games_dir=tmp_path)

    with pytest.raises(ValueError, match="does not match folder name"):
        loader.load_game(game_dir.name)


def test_game_loader_append_mode_prevents_duplicates(tmp_path: Path):
    game_dir = minimal_game(tmp_path)

    duplicate_nodes = {
        "__merge__": {"mode": "append"},
        "nodes": [
            {
                "id": "intro",
                "type": "scene",
                "title": "Duplicate Intro",
                "characters_present": [],
                "choices": [],
            }
        ],
    }
    write_yaml(game_dir / "duplicate_nodes.yaml", duplicate_nodes)

    manifest = load_yaml(game_dir / "game.yaml")
    manifest["includes"].append("duplicate_nodes.yaml")
    write_yaml(game_dir / "game.yaml", manifest)

    loader = GameLoader(games_dir=tmp_path)

    with pytest.raises(ValueError, match="Duplicate ID 'intro'"):
        loader.load_game(game_dir.name)
