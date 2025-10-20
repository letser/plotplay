import yaml
from pathlib import Path

import pytest

from app.core.game_loader import GameLoader
from app.models.game import GameDefinition


def write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def create_minimal_game(tmp_path: Path) -> Path:
    game_dir = tmp_path / "campus_story"
    game_dir.mkdir()

    game_manifest = {
        "meta": {
            "id": "campus_story",
            "title": "Campus Story",
            "authors": ["Test Author"],
            "nsfw_allowed": False,
        },
        "narration": {"pov": "second", "tense": "present", "paragraphs": "1-2"},
        "start": {"location": "campus_quad", "node": "intro", "day": 1, "slot": "morning", "time": "08:00"},
        "meters": {
            "player": {
                "energy": {"min": 0, "max": 100, "default": 70},
            },
            "template": {
                "trust": {"min": 0, "max": 100, "default": 10},
            },
        },
        "flags": {
            "met_friend": {"type": "bool", "default": False},
        },
        "time": {
            "mode": "slots",
            "slots": ["morning", "evening"],
            "actions_per_slot": 3,
        },
        "economy": {"enabled": True},
        "movement": {
            "base_time": 1,
            "use_entry_exit": False,
            "methods": [{"walk": 1}],
        },
        "includes": ["items.yaml", "characters.yaml", "locations.yaml", "nodes.yaml"],
    }
    write_yaml(game_dir / "game.yaml", game_manifest)

    items_yaml = {
        "items": [
            {"id": "coffee", "name": "Coffee", "category": "drink", "value": 5},
        ],
        "wardrobe": {
            "slots": ["top", "bottom", "feet"],
            "items": [
                {
                    "id": "player_top",
                    "name": "T-Shirt",
                    "value": 10,
                    "look": {"intact": "A comfy tee."},
                    "occupies": ["top"],
                    "conceals": [],
                },
            ],
            "outfits": [
                {
                    "id": "player_outfit",
                    "name": "Campus Casual",
                    "items": ["player_top"],
                    "grant_items": True,
                },
            ],
        },
    }
    write_yaml(game_dir / "items.yaml", items_yaml)

    characters_yaml = {
        "characters": [
            {
                "id": "player",
                "name": "You",
                "age": 20,
                "gender": "unspecified",
                "clothing": {"outfit": "player_outfit"},
                "inventory": {"items": []},
            },
            {
                "id": "friend",
                "name": "Friend",
                "age": 20,
                "gender": "female",
                "inventory": {"items": []},
            },
        ]
    }
    write_yaml(game_dir / "characters.yaml", characters_yaml)

    locations_yaml = {
        "zones": [
            {
                "id": "campus",
                "name": "Campus",
                "summary": "Central campus spaces.",
                "privacy": "low",
                "access": {"discovered": True},
                "locations": [
                    {
                        "id": "campus_quad",
                        "name": "Campus Quad",
                        "summary": "Students scurry between classes.",
                        "privacy": "low",
                        "access": {"discovered": True},
                    }
                ],
                "entrances": ["campus_quad"],
                "exits": ["campus_quad"],
            }
        ]
    }
    write_yaml(game_dir / "locations.yaml", locations_yaml)

    nodes_yaml = {
        "nodes": [
            {
                "id": "intro",
                "type": "scene",
                "title": "First Morning",
                "characters_present": [],
                "beats": ["You step onto the quad, ready for the day."],
                "choices": [],
            }
        ]
    }
    write_yaml(game_dir / "nodes.yaml", nodes_yaml)

    return game_dir

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


def test_game_loader_parses_minimal_spec(tmp_path: Path):
    game_dir = create_minimal_game(tmp_path)
    loader = GameLoader(games_dir=tmp_path)

    game_def = loader.load_game(game_dir.name)

    assert game_def.meta.title == "Campus Story"
    assert game_def.start.location == "campus_quad"
    assert game_def.start.node == "intro"
    assert game_def.wardrobe.outfits[0].id == "player_outfit"
    assert any(char.id == "friend" for char in game_def.characters)


def test_game_loader_raises_for_missing_start_location(tmp_path: Path):
    game_dir = create_minimal_game(tmp_path)
    manifest = yaml.safe_load((game_dir / "game.yaml").read_text(encoding="utf-8"))
    del manifest["start"]["location"]
    write_yaml(game_dir / "game.yaml", manifest)

    loader = GameLoader(games_dir=tmp_path)

    with pytest.raises(ValueError, match="start.location") as exc:
        loader.load_game(game_dir.name)
