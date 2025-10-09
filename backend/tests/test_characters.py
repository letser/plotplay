"""
Comprehensive tests for §7 Characters (PlotPlay v3 Spec).

Tests character definitions, required/optional fields, meters, flags,
gates, behaviors, schedules, movement, and validation.
"""
import pytest
from pathlib import Path
import yaml

from app.core.game_loader import GameLoader
from app.core.state_manager import StateManager
from app.core.game_engine import GameEngine
from app.core.conditions import ConditionEvaluator
from app.models.character import Character, BehaviorGate, Behaviors, BehaviorRefusals, Schedule, MovementWillingness


# =============================================================================
# § 7.1-7.2: Character Definition & Required Fields
# =============================================================================

def test_character_required_fields():
    """
    §7.2: Test that id, name, age, and gender are required for characters.
    """
    # Valid character with all required fields
    char = Character(
        id="test_char",
        name="Test Character",
        age=25,
        gender="female"
    )

    assert char.id == "test_char"
    assert char.name == "Test Character"
    assert char.age == 25
    assert char.gender == "female"

    print("✅ Required character fields work")


def test_character_age_validation_18_plus():
    """
    §7.5: Test that age >= 18 is enforced for NPCs (not player).
    """
    # Valid adult character
    char = Character(id="adult", name="Adult", age=18, gender="female")
    assert char.age == 18

    char2 = Character(id="older", name="Older", age=25, gender="male")
    assert char2.age == 25

    # Underage should fail validation for NPCs
    with pytest.raises(ValueError, match="must be 18\\+"):
        Character(id="minor", name="Minor", age=17, gender="female")

    # Player character can have None age
    player = Character(id="player", name="You", age=None, gender="any")
    assert player.age is None

    print("✅ Age validation (18+) works")


def test_character_without_optional_fields():
    """
    §7.2: Test that optional fields can be omitted.
    """
    char = Character(
        id="minimal",
        name="Minimal Character",
        age=20,
        gender="nonbinary"
    )

    # All optional fields should be None or default
    assert char.description is None
    assert char.tags == []
    assert char.dialogue_style is None
    assert char.author_notes is None
    assert char.pronouns is None
    assert char.role is None
    assert char.meters is None
    assert char.flags is None
    assert char.inventory is None
    assert char.wardrobe is None
    assert char.behaviors is None
    assert char.schedule is None
    assert char.movement is None

    print("✅ Optional fields can be omitted")


# =============================================================================
# § 7.2: Optional Identity Fields
# =============================================================================

def test_character_optional_identity_fields():
    """
    §7.2: Test optional identity fields (description, tags, pronouns, role).
    """
    char = Character(
        id="detailed",
        name="Detailed Character",
        age=22,
        gender="female",
        description="A shy literature student",
        tags=["student", "shy", "conservative"],
        pronouns=["she", "her"],
        role="love_interest"
    )

    assert char.description == "A shy literature student"
    assert "student" in char.tags
    assert "shy" in char.tags
    assert char.pronouns == ["she", "her"]
    assert char.role == "love_interest"

    print("✅ Optional identity fields work")


def test_character_dialogue_style_and_author_notes():
    """
    §7.2: Test dialogue_style and author_notes fields.
    """
    char = Character(
        id="emma",
        name="Emma",
        age=19,
        gender="female",
        dialogue_style="warm, teasing, uses coffee metaphors",
        author_notes="Emma starts shy but becomes flirty when trust > 50."
    )

    assert char.dialogue_style == "warm, teasing, uses coffee metaphors"
    assert "trust > 50" in char.author_notes

    print("✅ dialogue_style and author_notes work")


# =============================================================================
# § 7.2: Per-Character Meters
# =============================================================================

def test_character_specific_meters(tmp_path: Path):
    """
    §7.2: Test that characters can define their own meters.
    These override/supplement character_template meters.
    """
    game_dir = tmp_path / "char_meters"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'health': {'min': 0, 'max': 100, 'default': 50}
            },
            'character_template': {
                'trust': {'min': 0, 'max': 100, 'default': 10}
            }
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'},
            {
                'id': 'emma',
                'name': 'Emma',
                'age': 19,
                'gender': 'female',
                'meters': {
                    'trust': {'min': 0, 'max': 100, 'default': 20},  # Override template
                    'attraction': {'min': 0, 'max': 100, 'default': 5}  # Additional meter
                }
            }
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("char_meters")
    manager = StateManager(game_def)

    # Emma's trust should use her specific default (20), not template (10)
    assert manager.state.meters["emma"]["trust"] == 20
    assert manager.state.meters["emma"]["attraction"] == 5

    print("✅ Per-character meters work")


# =============================================================================
# § 7.2: Character-Scoped Flags
# =============================================================================

def test_character_scoped_flags(tmp_path: Path):
    """
    §7.2: Test that character-scoped flags are prefixed with character ID.
    """
    game_dir = tmp_path / "char_flags"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'},
            {
                'id': 'emma',
                'name': 'Emma',
                'age': 22,
                'gender': 'female',
                'flags': {
                    'met_player': {'type': 'bool', 'default': False},
                    'conversation_count': {'type': 'number', 'default': 0}
                }
            }
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("char_flags")
    manager = StateManager(game_def)

    # Character-scoped flags should be prefixed
    assert "emma.met_player" in manager.state.flags
    assert "emma.conversation_count" in manager.state.flags
    assert manager.state.flags["emma.met_player"] is False
    assert manager.state.flags["emma.conversation_count"] == 0

    print("✅ Character-scoped flags work")


# =============================================================================
# § 7.2: Behaviors & Gates (Consent System)
# =============================================================================

def test_behavior_gates_single_condition():
    """
    §7.2: Test behavior gates with single 'when' condition.
    """
    gate = BehaviorGate(
        id="accept_kiss",
        when="meters.emma.trust >= 50 and meters.emma.attraction >= 40"
    )

    assert gate.id == "accept_kiss"
    assert gate.when is not None
    assert "trust" in gate.when

    print("✅ Behavior gates with single condition work")


def test_behavior_gates_when_any():
    """
    §7.2: Test behavior gates with when_any (OR logic).
    """
    gate = BehaviorGate(
        id="accept_date",
        when_any=[
            "meters.emma.trust >= 30",
            "meters.emma.attraction >= 50"
        ]
    )

    assert gate.id == "accept_date"
    assert len(gate.when_any) == 2
    assert "trust" in gate.when_any[0]

    print("✅ Behavior gates with when_any work")


def test_behavior_gates_when_all():
    """
    §7.2: Test behavior gates with when_all (AND logic).
    """
    gate = BehaviorGate(
        id="accept_sex",
        when_all=[
            "meters.emma.trust >= 70",
            "meters.emma.attraction >= 70",
            "meters.emma.arousal >= 50",
            "location.privacy == 'high'"
        ]
    )

    assert gate.id == "accept_sex"
    assert len(gate.when_all) == 4
    assert "privacy" in gate.when_all[3]

    print("✅ Behavior gates with when_all work")


def test_behavior_refusals():
    """
    §7.2: Test behavior refusal templates.
    """
    refusals = BehaviorRefusals(
        generic="She pulls back. 'Not yet.'",
        low_trust="She shakes her head. 'Slow down.'",
        wrong_place="She glances around. 'Not here.'",
        too_forward="'That's too much, too fast.'"
    )

    assert refusals.generic is not None
    assert refusals.low_trust is not None
    assert refusals.wrong_place is not None
    assert refusals.too_forward is not None

    print("✅ Behavior refusals work")


def test_complete_behaviors_system():
    """
    §7.2: Test complete behaviors system with gates and refusals.
    """
    behaviors = Behaviors(
        gates=[
            BehaviorGate(id="accept_date", when="meters.emma.trust >= 30"),
            BehaviorGate(
                id="accept_kiss",
                when_any=[
                    "meters.emma.trust >= 50 and meters.emma.attraction >= 40",
                    "meters.emma.corruption >= 50"
                ]
            )
        ],
        refusals=BehaviorRefusals(
            generic="She smiles but hesitates.",
            low_trust="'I don't know you well enough yet.'",
            wrong_place="'Not in public.'"
        )
    )

    assert len(behaviors.gates) == 2
    assert behaviors.gates[0].id == "accept_date"
    assert behaviors.refusals.generic is not None

    print("✅ Complete behaviors system works")


def test_gates_required_for_nsfw_characters():
    """
    §7.5: Test that NSFW characters should have gates defined.
    This is a spec requirement but not enforced by code validation.
    """
    # Good practice: NSFW character with gates
    char = Character(
        id="emma",
        name="Emma",
        age=19,
        gender="female",
        behaviors=Behaviors(
            gates=[
                BehaviorGate(id="accept_kiss", when="meters.emma.trust >= 50"),
                BehaviorGate(id="accept_sex", when="meters.emma.trust >= 70")
            ]
        )
    )

    assert char.behaviors is not None
    assert len(char.behaviors.gates) >= 2

    print("✅ NSFW characters have gates (best practice)")


# =============================================================================
# § 7.2: Schedule & Availability
# =============================================================================

def test_character_schedule():
    """
    §7.2: Test character schedule system for time-based location.
    """
    schedule = [
        Schedule(when="time.slot == 'morning'", location="library"),
        Schedule(when="time.slot == 'afternoon'", location="cafeteria"),
        Schedule(when="time.slot == 'night'", location="dorm_room")
    ]

    char = Character(
        id="emma",
        name="Emma",
        age=22,
        gender="female",
        schedule=schedule
    )

    assert char.schedule is not None
    assert len(char.schedule) == 3
    assert char.schedule[0].location == "library"
    assert "morning" in char.schedule[0].when

    print("✅ Character schedule works")


def test_schedule_with_complex_conditions():
    """
    §7.2: Test schedule with complex Expression DSL conditions.
    """
    schedule = [
        Schedule(
            when="time.weekday in ['monday', 'wednesday', 'friday'] and time.slot == 'morning'",
            location="lecture_hall"
        ),
        Schedule(
            when="time.weekday == 'saturday' or time.weekday == 'sunday'",
            location="home"
        )
    ]

    char = Character(
        id="student",
        name="Student",
        age=20,
        gender="male",
        schedule=schedule
    )

    assert len(char.schedule) == 2
    assert "weekday" in char.schedule[0].when

    print("✅ Schedule with complex conditions works")


# =============================================================================
# § 7.2: Movement Willingness
# =============================================================================

def test_movement_willing_zones():
    """
    §7.2: Test movement willingness for zones.
    """
    movement = MovementWillingness(
        willing_zones=[
            {"zone": "campus", "when": "always"},
            {"zone": "downtown", "when": "meters.emma.trust >= 50"}
        ]
    )

    char = Character(
        id="emma",
        name="Emma",
        age=22,
        gender="female",
        movement=movement
    )

    assert char.movement is not None
    assert len(char.movement.willing_zones) == 2
    assert char.movement.willing_zones[0]["zone"] == "campus"
    assert char.movement.willing_zones[0]["when"] == "always"

    print("✅ Movement willing_zones work")


def test_movement_willing_locations():
    """
    §7.2: Test movement willingness for specific locations.
    """
    movement = MovementWillingness(
        willing_locations=[
            {"location": "player_room", "when": "meters.emma.trust >= 40"},
            {"location": "library", "when": "always"}
        ],
        refusal_text={
            "low_trust": "I don't feel comfortable going there with you yet.",
            "wrong_time": "Now isn't a good time."
        }
    )

    char = Character(
        id="emma",
        name="Emma",
        age=22,
        gender="female",
        movement=movement
    )

    assert len(char.movement.willing_locations) == 2
    assert char.movement.willing_locations[0]["location"] == "player_room"
    assert char.movement.refusal_text is not None
    assert "comfortable" in char.movement.refusal_text["low_trust"]

    print("✅ Movement willing_locations work")


# =============================================================================
# § 7.2: Per-Character Inventory
# =============================================================================

def test_character_inventory():
    """
    §7.2: Test per-character starting inventory.
    """
    char = Character(
        id="emma",
        name="Emma",
        age=22,
        gender="female",
        inventory={"flowers": 1, "book": 1, "phone": 1}
    )

    assert char.inventory is not None
    assert char.inventory["flowers"] == 1
    assert char.inventory["book"] == 1

    print("✅ Character inventory works")


def test_character_inventory_initialization_in_state(tmp_path: Path):
    """
    §7.2: Test that character inventory is initialized in game state.
    """
    game_dir = tmp_path / "char_inv"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'},
            {
                'id': 'emma',
                'name': 'Emma',
                'age': 22,
                'gender': 'female',
                'inventory': {'flowers': 2, 'note': 1}
            }
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("char_inv")
    manager = StateManager(game_def)

    # Emma's inventory should be initialized
    assert "emma" in manager.state.inventory
    assert manager.state.inventory["emma"]["flowers"] == 2
    assert manager.state.inventory["emma"]["note"] == 1

    print("✅ Character inventory initialized in state")


# =============================================================================
# § 7.2: Wardrobe (Basic Reference)
# =============================================================================

def test_character_wardrobe_basic():
    """
    §7.2: Test basic wardrobe reference (detailed tests in §12).
    """
    from app.models.character import Wardrobe, Outfit, ClothingLayer

    wardrobe = Wardrobe(
        outfits=[
            Outfit(
                id="casual",
                name="Casual Outfit",
                tags=["default"],
                layers={
                    "top": ClothingLayer(item="t-shirt", color="white"),
                    "bottom": ClothingLayer(item="jeans", color="blue")
                }
            )
        ]
    )

    char = Character(
        id="emma",
        name="Emma",
        age=22,
        gender="female",
        wardrobe=wardrobe
    )

    assert char.wardrobe is not None
    assert len(char.wardrobe.outfits) == 1
    assert char.wardrobe.outfits[0].id == "casual"

    print("✅ Character wardrobe (basic) works")


# =============================================================================
# § 7.3-7.4: Complete Character Examples
# =============================================================================

def test_complete_character_definition():
    """
    §7.4: Test a complete character with all fields defined.
    """
    from app.models.character import (
        Wardrobe, Outfit, ClothingLayer,
        Behaviors, BehaviorGate, BehaviorRefusals,
        Schedule, MovementWillingness
    )

    char = Character(
        id="emma",
        name="Emma Chen",
        age=19,
        gender="female",
        pronouns=["she", "her"],
        description="A shy and conservative literature student",
        tags=["student", "shy", "conservative"],
        dialogue_style="soft-spoken, thoughtful",
        author_notes="Emma gradually opens up as trust increases",

        meters={
            "trust": {"min": 0, "max": 100, "default": 10},
            "attraction": {"min": 0, "max": 100, "default": 0}
        },

        flags={
            "met_player": {"type": "bool", "default": False}
        },

        behaviors=Behaviors(
            gates=[
                BehaviorGate(id="accept_date", when="meters.emma.trust >= 30"),
                BehaviorGate(
                    id="accept_kiss",
                    when_any=[
                        "meters.emma.trust >= 50 and meters.emma.attraction >= 40"
                    ]
                )
            ],
            refusals=BehaviorRefusals(
                generic="She pulls back. 'Not yet.'",
                low_trust="She shakes her head. 'Slow down.'"
            )
        ),

        wardrobe=Wardrobe(
            outfits=[
                Outfit(
                    id="casual_day",
                    name="Casual Outfit",
                    tags=["default"],
                    layers={
                        "top": ClothingLayer(item="tank top", color="white"),
                        "bottom": ClothingLayer(item="jeans")
                    }
                )
            ]
        ),

        schedule=[
            Schedule(when="time.slot == 'morning'", location="library"),
            Schedule(when="time.slot == 'night'", location="dorm_room")
        ],

        movement=MovementWillingness(
            willing_zones=[
                {"zone": "campus", "when": "always"}
            ],
            willing_locations=[
                {"location": "player_room", "when": "meters.emma.trust >= 40"}
            ]
        ),

        inventory={"book": 1, "phone": 1}
    )

    # Verify all major sections
    assert char.id == "emma"
    assert char.age == 19
    assert char.description is not None
    assert char.meters is not None
    assert char.flags is not None
    assert char.behaviors is not None
    assert len(char.behaviors.gates) == 2
    assert char.wardrobe is not None
    assert char.schedule is not None
    assert char.movement is not None
    assert char.inventory is not None

    print("✅ Complete character definition works")


def test_player_character_special_case():
    """
    §7.2: Test that player character can omit age and has special handling.
    """
    player = Character(
        id="player",
        name="You",
        age=None,  # Can be None for player
        gender="any",
        pronouns=["you"]
    )

    assert player.id == "player"
    assert player.age is None
    assert player.gender == "any"

    print("✅ Player character special case works")


# =============================================================================
# § 7.5: Loading Real Game Characters
# =============================================================================

def test_load_real_game_characters():
    """
    §7: Test loading characters from actual game files.
    """
    loader = GameLoader()
    game_def = loader.load_game("coffeeshop_date")

    # Find characters
    char_ids = [c.id for c in game_def.characters]

    assert "player" in char_ids
    assert "alex" in char_ids

    # Get Alex character
    alex = next(c for c in game_def.characters if c.id == "alex")

    assert alex.name == "Alex"
    assert alex.age == 22
    assert alex.gender == "female"
    assert alex.dialogue_style is not None
    assert alex.behaviors is not None
    assert len(alex.behaviors.gates) > 0

    print("✅ Real game characters load correctly")


# =============================================================================
# § 7: Character in Game State
# =============================================================================

def test_character_meters_in_game_state(tmp_path: Path):
    """
    §7.3: Test that character meters are properly initialized in game state.
    """
    game_dir = tmp_path / "char_state"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'character_template': {
                'trust': {'min': 0, 'max': 100, 'default': 10},
                'attraction': {'min': 0, 'max': 100, 'default': 5}
            }
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'},
            {'id': 'emma', 'name': 'Emma', 'age': 22, 'gender': 'female'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("char_state")
    manager = StateManager(game_def)

    # Character template meters should be applied
    assert "emma" in manager.state.meters
    assert manager.state.meters["emma"]["trust"] == 10
    assert manager.state.meters["emma"]["attraction"] == 5

    print("✅ Character meters in game state work")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])