from pathlib import Path
import os

import pytest
import yaml

from app.core.state import GameState
from app.models.locations import LocationPrivacy
from app.services.mock_ai_service import MockAIService


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
                "version": "1.0.0",
                "authors": ["Test Author"],
                "description": "A minimal test game for loader tests.",
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
                "quad_event_seen": {"type": "bool", "default": False},
                "arc_stage_meet": {"type": "bool", "default": False},
                "arc_stage_bond": {"type": "bool", "default": False},
            },
            "time": {
                "slots_enabled": True,
                "slots": ["morning", "afternoon", "evening"],
                "slot_windows": {
                    "morning": {"start": "06:00", "end": "11:59"},
                    "afternoon": {"start": "12:00", "end": "17:59"},
                    "evening": {"start": "18:00", "end": "21:59"},
                },
                "categories": {
                    "instant": 0,
                    "trivial": 2,
                    "quick": 5,
                    "standard": 15,
                    "significant": 30,
                    "major": 60,
                },
                "defaults": {
                    "conversation": "instant",
                    "choice": "quick",
                    "movement": "standard",
                    "default": "trivial",
                    "cap_per_visit": 30,
                },
            },
            "economy": {
                "enabled": True,
                "starting_money": 50,
                "max_money": 500,
                "currency_name": "dollars",
                "currency_symbol": "$",
            },
            "movement": {
                "use_entry_exit": False,
                "base_unit": "km",
                "methods": [
                    {"name": "walk", "active": True, "time_cost": 20}
                ],
            },
            "includes": ["items.yaml", "characters.yaml", "locations.yaml", "nodes.yaml", "events.yaml"],
        },
    )

    write_yaml(
        game_dir / "items.yaml",
        {
            "items": [
                {"id": "coffee", "name": "Coffee", "category": "drink", "value": 5, "stackable": True},
                {"id": "sword", "name": "Iron Sword", "category": "weapon", "value": 150, "stackable": False},
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
                        "items": {"player_top": "intact"},
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
                    "inventory": {"items": {}},
                },
                {
                    "id": "friend",
                    "name": "Friend",
                    "age": 20,
                    "gender": "female",
                    "inventory": {"items": {}},
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

    write_yaml(
        game_dir / "events.yaml",
        {
            "events": [
                {
                    "id": "energy_boost",
                    "title": "Morning Energy",
                    "when": "meters.player.energy < 50",
                    "cooldown": 5,
                    "on_enter": [
                        {
                            "type": "meter_change",
                            "target": "player",
                            "meter": "energy",
                            "op": "add",
                            "value": 10
                        }
                    ]
                },
                {
                    "id": "location_event",
                    "title": "Quad Event",
                    "when": "meters.player.energy > 30 and location.id == 'campus_quad'",
                    "on_enter": [
                        {
                            "type": "flag_set",
                            "key": "quad_event_seen",
                            "value": True
                        }
                    ]
                },
                {
                    "id": "random_event_1",
                    "title": "Random Event 1",
                    "probability": 67,
                    "cooldown": 3,
                    "effects": []
                },
                {
                    "id": "random_event_2",
                    "title": "Random Event 2",
                    "probability": 33,
                    "cooldown": 3,
                    "effects": []
                }
            ],
            "arcs": [
                {
                    "id": "friendship_arc",
                    "title": "Building Friendship",
                    "character": "friend",
                    "description": "Develop friendships on campus",
                    "repeatable": False,
                    "stages": [
                        {
                            "id": "meet",
                            "title": "First Meeting",
                            "description": "Meet someone new",
                            "when": "visited_node:intro",
                            "on_exit": [
                                {
                                    "type": "flag_set",
                                    "key": "arc_stage_meet",
                                    "value": True
                                }
                            ]
                        },
                        {
                            "id": "bond",
                            "title": "Bonding",
                            "description": "Form a connection",
                            "when": "met_friend == true",
                            "on_exit": [
                                {
                                    "type": "flag_set",
                                    "key": "arc_stage_bond",
                                    "value": True
                                }
                            ]
                        }
                    ]
                }
            ]
        },
    )

    return game_dir


@pytest.fixture
def sample_game_state() -> GameState:
    from app.models.characters import CharacterState
    from app.models.clothing import ClothingState
    from app.models.inventory import InventoryState

    state = GameState()
    state.day = 3
    state.time_slot = "evening"
    state.time_hhmm = "19:30"
    state.weekday = "wednesday"

    state.current_location = "campus_quad"
    state.current_zone = "campus"
    state.location_privacy = LocationPrivacy.MEDIUM

    state.present_characters = ["player", "emma"]

    # Set up character states (which contain meters, inventory, clothing, modifiers)
    state.characters = {
        "player": CharacterState(
            meters={"energy": 65, "money": 40},
            inventory=InventoryState(items={"coffee": 1, "ticket": 0}),
            modifiers=[{"id": "inspired"}],
            clothing=ClothingState(outfit="campus_ready", items={"top": "intact"})
        ),
        "emma": CharacterState(
            meters={"trust": 55, "attraction": 42},
            inventory=InventoryState(),
            modifiers=[],
            clothing=ClothingState()
        ),
    }

    state.flags = {
        "met_emma": True,
        "invitation_sent": False,
    }

    state.active_arcs = {"emma_path": "study_buddies"}
    state.completed_milestones = ["intro_scene"]

    state.cooldowns = {}
    state.actions_this_slot = 0
    state.current_node = "quad_intro"
    state.turn_count = 5

    return state


# AI Service Mocking
@pytest.fixture(scope="session")
def mock_ai_service():
    """Provide mock AI service for fast tests (session-scoped)."""
    return MockAIService()


@pytest.fixture(scope="session")
def use_real_ai():
    """Check if tests should use real AI service."""
    return os.environ.get("USE_REAL_AI", "false").lower() == "true"
