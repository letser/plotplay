from pathlib import Path

import pytest
import yaml

from app.core.state_manager import GameState
from app.models.locations import LocationPrivacy


def write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def minimal_game(tmp_path: Path) -> Path:
    """Create a minimal spec-compliant game for loader tests."""
    game_dir = tmp_path / "campus_story"
    game_dir.mkdir()

    write_yaml(
        game_dir / "game.yaml",
        {
            "meta": {
                "id": "campus_story",
                "title": "Campus Story",
                "authors": ["Test Author"],
                "nsfw_allowed": False,
            },
            "narration": {"pov": "second", "tense": "present", "paragraphs": "1-2"},
            "start": {
                "location": "campus_quad",
                "node": "intro",
                "day": 1,
                "slot": "morning",
                "time": "08:00",
            },
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
        },
    )

    write_yaml(
        game_dir / "items.yaml",
        {
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
        },
    )

    write_yaml(
        game_dir / "characters.yaml",
        {
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
        },
    )

    write_yaml(
        game_dir / "locations.yaml",
        {
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
        },
    )

    write_yaml(
        game_dir / "nodes.yaml",
        {
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
        },
    )

    return game_dir


@pytest.fixture
def sample_game_state() -> GameState:
    state = GameState()
    state.day = 3
    state.time_slot = "evening"
    state.time_hhmm = "19:30"
    state.weekday = "wednesday"

    state.location_current = "campus_quad"
    state.zone_current = "campus"
    state.location_privacy = LocationPrivacy.MEDIUM

    state.present_chars = ["player", "emma"]

    state.meters = {
        "player": {"energy": 65, "money": 40},
        "emma": {"trust": 55, "attraction": 42},
    }

    state.flags = {
        "met_emma": True,
        "invitation_sent": False,
    }

    state.inventory = {
        "player": {"coffee": 1, "ticket": 0},
    }

    state.modifiers = {
        "player": [{"id": "inspired"}],
        "emma": [],
    }

    state.clothing_states = {
        "player": {"layers": {"top": "intact"}, "current_outfit": "campus_ready"}
    }

    state.active_arcs = {"emma_path": "study_buddies"}
    state.completed_milestones = ["intro_scene"]

    state.cooldowns = {}
    state.actions_this_slot = 0
    state.current_node = "quad_intro"
    state.turn_count = 5

    return state
