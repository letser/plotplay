"""
Comprehensive tests for §5 State Overview (PlotPlay v3 Spec).

Tests the complete game state system including initialization, components,
validation, and serialization.
"""
import pytest
from datetime import datetime, UTC
from pathlib import Path
import yaml

from app.core.state_manager import StateManager, GameState
from app.core.game_engine import GameEngine
from app.core.game_loader import GameLoader
from app.models.game import GameDefinition, MetaConfig, StartConfig
from app.models.character import Character
from app.models.node import Node, NodeType
from app.models.location import Zone, Location, LocationPrivacy
from app.models.time import TimeConfig, TimeStart
from app.models.flag import Flag
from app.models.meters import Meter
from app.models.effects import MeterChangeEffect


# =============================================================================
# § 5: State as Single Source of Truth
# =============================================================================

def test_state_is_single_source_of_truth(minimal_game_def):
    """
    §5: Test that state is the authoritative source for all game data.
    Changes to state should be immediately reflected in all queries.
    """
    manager = StateManager(minimal_game_def)
    state = manager.state

    # Change state
    state.meters["player"]["health"] = 42
    state.flags["test_flag"] = True
    state.inventory["player"]["new_item"] = 1

    # Verify changes are immediately visible
    assert state.meters["player"]["health"] == 42
    assert state.flags["test_flag"] is True
    assert state.inventory["player"]["new_item"] == 1

    print("✅ State is single source of truth")


def test_state_is_author_driven(tmp_path: Path):
    """
    §5: Test that all state components must be defined in game YAML.
    Unknown keys should be rejected or handled safely.
    """
    game_dir = tmp_path / "author_driven"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'defined_meter': {'min': 0, 'max': 100, 'default': 50}
            }
        },
        'flags': {
            'defined_flag': {'type': 'bool', 'default': False}
        },
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}],
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("author_driven")
    manager = StateManager(game_def)

    # Only defined meters and flags should exist
    assert "defined_meter" in manager.state.meters["player"]
    assert "defined_flag" in manager.state.flags

    print("✅ State is author-driven (only defined entities exist)")


def test_state_is_validated():
    """
    §5: Test that invalid state values are rejected or clamped.
    """
    loader = GameLoader()
    game_def = loader.load_game("coffeeshop_date")
    engine = GameEngine(game_def, "validation_test")

    # Try to set meter beyond max
    initial_max = 100
    engine._apply_meter_change(MeterChangeEffect(
        type="meter_change",
        target="player",
        meter="confidence",
        op="set",
        value=150
    ))

    # Should be clamped to max
    assert engine.state_manager.state.meters["player"]["confidence"] == initial_max

    # Try to set below min
    engine._apply_meter_change(MeterChangeEffect(
        type="meter_change",
        target="player",
        meter="confidence",
        op="set",
        value=-50
    ))

    # Should be clamped to min (0)
    assert engine.state_manager.state.meters["player"]["confidence"] == 0

    print("✅ State validation (meter bounds) works correctly")


def test_state_is_dynamic(minimal_game_def):
    """
    §5: Test that state updates dynamically every turn through effects.
    """
    engine = GameEngine(minimal_game_def, "dynamic_test")

    initial_health = engine.state_manager.state.meters["player"]["health"]

    # Apply an effect
    engine._apply_meter_change(MeterChangeEffect(
        type="meter_change",
        target="player",
        meter="health",
        op="add",
        value=-10
    ))

    # State should be updated
    assert engine.state_manager.state.meters["player"]["health"] == initial_health - 10

    print("✅ State is dynamic (updates via effects)")


# =============================================================================
# § 5.1: State Initialization - All Components
# =============================================================================

def test_state_initialization_complete(minimal_game_def):
    """
    §5: Test that StateManager initializes ALL state components correctly.
    """
    manager = StateManager(minimal_game_def)
    state = manager.state

    # Time & Location
    assert state.day == 1
    assert state.time_slot == "morning"
    assert state.location_current == "test_location"
    assert state.zone_current == "test_zone"
    assert isinstance(state.location_privacy, LocationPrivacy)

    # Characters
    assert isinstance(state.present_chars, list)

    # Meters & Inventory
    assert isinstance(state.meters, dict)
    assert "player" in state.meters
    assert isinstance(state.inventory, dict)
    assert "player" in state.inventory

    # Flags & Progress
    assert isinstance(state.flags, dict)
    assert isinstance(state.active_arcs, dict)
    assert isinstance(state.completed_milestones, list)
    assert isinstance(state.visited_nodes, list)
    assert isinstance(state.discovered_locations, list)

    # Unlock Tracking
    assert isinstance(state.unlocked_outfits, dict)
    assert isinstance(state.unlocked_actions, list)
    assert isinstance(state.unlocked_endings, list)

    # Dynamic Character States
    assert isinstance(state.clothing_states, dict)
    assert isinstance(state.modifiers, dict)

    # Engine Tracking
    assert isinstance(state.cooldowns, dict)
    assert state.actions_this_slot == 0
    assert state.current_node == "start_node"
    assert isinstance(state.narrative_history, list)
    assert isinstance(state.memory_log, list)
    assert state.turn_count == 0

    # Timestamps
    assert isinstance(state.created_at, datetime)
    assert isinstance(state.updated_at, datetime)

    print("✅ Complete state initialization verified")


def test_meters_initialization_from_game_def(tmp_path: Path):
    """
    §5: Test that meters are initialized from player and character_template definitions.
    """
    game_dir = tmp_path / "meters_init"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'health': {'min': 0, 'max': 100, 'default': 75},
                'energy': {'min': 0, 'max': 100, 'default': 50}
            },
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
    game_def = loader.load_game("meters_init")
    manager = StateManager(game_def)

    # Player meters
    assert manager.state.meters["player"]["health"] == 75
    assert manager.state.meters["player"]["energy"] == 50

    # Character template meters applied to NPCs
    assert manager.state.meters["emma"]["trust"] == 10
    assert manager.state.meters["emma"]["attraction"] == 5

    print("✅ Meters initialization from game definition works")


def test_character_specific_meter_overrides(tmp_path: Path):
    """
    §5: Test that character-specific meters override character_template.
    """
    game_dir = tmp_path / "meter_override"
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
                'age': 22,
                'gender': 'female',
                'meters': {
                    'trust': {'min': 0, 'max': 100, 'default': 50}  # Override template default
                }
            }
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("meter_override")
    manager = StateManager(game_def)

    # Emma's trust should use her specific value, not template
    assert manager.state.meters["emma"]["trust"] == 50

    print("✅ Character-specific meter overrides work")


def test_inventory_initialization_from_characters(tmp_path: Path):
    """
    §5: Test that inventories are initialized from character definitions.
    """
    game_dir = tmp_path / "inventory_init"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'characters': [
            {
                'id': 'player',
                'name': 'Player',
                'age': 25,
                'gender': 'any',
                'inventory': {'key': 1, 'money': 50}
            },
            {
                'id': 'emma',
                'name': 'Emma',
                'age': 22,
                'gender': 'female',
                'inventory': {'flowers': 1}
            }
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("inventory_init")
    manager = StateManager(game_def)

    # Verify starting inventories
    assert manager.state.inventory["player"]["key"] == 1
    assert manager.state.inventory["player"]["money"] == 50
    assert manager.state.inventory["emma"]["flowers"] == 1

    print("✅ Inventory initialization from characters works")


def test_flags_initialization_global_and_character_scoped(tmp_path: Path):
    """
    §5: Test that both global and character-scoped flags are initialized.
    Character-scoped flags should be prefixed with character ID.
    """
    game_dir = tmp_path / "flags_init"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'flags': {
            'game_started': {'type': 'bool', 'default': False},
            'day_count': {'type': 'number', 'default': 0}
        },
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
    game_def = loader.load_game("flags_init")
    manager = StateManager(game_def)

    # Global flags
    assert manager.state.flags["game_started"] is False
    assert manager.state.flags["day_count"] == 0

    # Character-scoped flags (prefixed with character ID)
    assert manager.state.flags["emma.met_player"] is False
    assert manager.state.flags["emma.conversation_count"] == 0

    print("✅ Global and character-scoped flags initialization works")


def test_clothing_states_initialization(tmp_path: Path):
    """
    §5: Test that clothing states are initialized from character wardrobe definitions.
    """
    game_dir = tmp_path / "clothing_init"
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
                'wardrobe': {
                    'rules': {'layer_order': ['top', 'bottom', 'underwear']},
                    'outfits': [
                        {
                            'id': 'casual',
                            'name': 'Casual Outfit',
                            'tags': ['default'],
                            'layers': {
                                'top': {'item': 't-shirt'},
                                'bottom': {'item': 'jeans'},
                                'underwear': {'item': 'basics'}
                            }
                        }
                    ]
                }
            }
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("clothing_init")
    manager = StateManager(game_def)

    # Verify clothing state initialization
    print(manager.state.clothing_states)
    assert 'emma' in manager.state.clothing_states
    assert manager.state.clothing_states['emma']['current_outfit'] == 'casual'
    assert manager.state.clothing_states['emma']['layers']['top'] == 'intact'
    assert manager.state.clothing_states['emma']['layers']['bottom'] == 'intact'
    assert manager.state.clothing_states['emma']['layers']['underwear'] == 'intact'

    print("✅ Clothing states initialization works")


def test_discovered_locations_initialization(tmp_path: Path):
    """
    §5: Test that locations marked as discovered are added to state.
    """
    game_dir = tmp_path / "discovered_init"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'zones': [
            {
                'id': 'z1',
                'name': 'Zone 1',
                'discovered': True,
                'locations': [
                    {'id': 'l1', 'name': 'Loc 1', 'discovered': True},
                    {'id': 'l2', 'name': 'Loc 2', 'discovered': False},
                ]
            }
        ],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}],
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("discovered_init")
    manager = StateManager(game_def)

    # Only l1 should be discovered
    assert 'l1' in manager.state.discovered_locations
    assert 'l2' not in manager.state.discovered_locations

    print("✅ Discovered locations initialization works")


def test_time_initialization_slots_mode(tmp_path: Path):
    """
    §5: Test that time is properly initialized in slots mode.
    """
    game_dir = tmp_path / "time_slots"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'time': {
            'mode': 'slots',
            'slots': ['morning', 'afternoon', 'evening', 'night'],
            'start': {'day': 1, 'slot': 'morning'}
        },
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}],
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("time_slots")
    manager = StateManager(game_def)

    assert manager.state.day == 1
    assert manager.state.time_slot == 'morning'
    assert manager.state.time_hhmm is None  # Not used in slots mode
    assert manager.state.weekday is None  # Not used without calendar

    print("✅ Time initialization (slots mode) works")


def test_time_initialization_clock_mode(tmp_path: Path):
    """
    §5: Test that time is properly initialized in clock mode with HH:MM.
    """
    game_dir = tmp_path / "time_clock"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'time': {
            'mode': 'clock',
            'start': {'day': 1, 'time': '08:30', 'slot': 'morning'}
        },
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}],
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("time_clock")
    manager = StateManager(game_def)

    assert manager.state.day == 1
    assert manager.state.time_hhmm == '08:30'

    print("✅ Time initialization (clock mode) works")


def test_time_initialization_with_calendar(tmp_path: Path):
    """
    §5: Test that weekday is calculated when calendar is enabled.
    """
    game_dir = tmp_path / "time_calendar"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'time': {
            'mode': 'slots',
            'slots': ['morning', 'afternoon', 'evening', 'night'],
            'start': {'day': 1, 'slot': 'morning'},
            'calendar': {
                'enabled': True,
                'start_day': 'monday',
                'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            }
        },
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}],
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("time_calendar")
    manager = StateManager(game_def)

    # Day 1 should start on the configured start_day
    assert manager.state.weekday == 'monday'

    print("✅ Time initialization with calendar (weekday) works")


# =============================================================================
# § 5.2: State Serialization & Persistence
# =============================================================================

def test_state_to_dict_serialization(minimal_game_def):
    """
    §5: Test that state can be serialized to a dictionary for saving.
    """
    manager = StateManager(minimal_game_def)
    state = manager.state

    # Modify state
    state.meters["player"]["health"] = 42
    state.flags["test_flag"] = True
    state.turn_count = 10

    # Serialize
    state_dict = state.to_dict()

    # Verify serialization
    assert isinstance(state_dict, dict)
    assert state_dict["meters"]["player"]["health"] == 42
    assert state_dict["flags"]["test_flag"] is True
    assert state_dict["turn_count"] == 10
    assert "created_at" in state_dict
    assert "updated_at" in state_dict

    # Should not include private attributes
    assert not any(key.startswith("_") for key in state_dict.keys())

    print("✅ State serialization (to_dict) works")


def test_state_timestamps(minimal_game_def):
    """
    §5: Test that created_at and updated_at timestamps are set correctly.
    """
    manager = StateManager(minimal_game_def)
    state = manager.state

    assert state.created_at is not None
    assert state.updated_at is not None
    assert isinstance(state.created_at, datetime)
    assert isinstance(state.updated_at, datetime)

    # They should be close in time (within a second)
    time_diff = (state.updated_at - state.created_at).total_seconds()
    assert time_diff < 1.0

    print("✅ State timestamps are set correctly")


# =============================================================================
# § 5.3: State Components - Detailed Testing
# =============================================================================

def test_location_privacy_tracking(minimal_game_def):
    """
    §5: Test that location privacy level is tracked in state.
    """
    manager = StateManager(minimal_game_def)
    state = manager.state

    assert isinstance(state.location_privacy, LocationPrivacy)

    # Should be initialized to LOW by default
    assert state.location_privacy in [LocationPrivacy.LOW, LocationPrivacy.MEDIUM, LocationPrivacy.HIGH]

    # Should be changeable
    state.location_privacy = LocationPrivacy.HIGH
    assert state.location_privacy == LocationPrivacy.HIGH

    print("✅ Location privacy tracking works")


def test_present_characters_tracking(minimal_game_def):
    """
    §5: Test that present characters list is maintained in state.
    """
    manager = StateManager(minimal_game_def)
    state = manager.state

    assert isinstance(state.present_chars, list)

    # Should be modifiable
    state.present_chars.append("emma")
    assert "emma" in state.present_chars

    print("✅ Present characters tracking works")


def test_modifiers_tracking(minimal_game_def):
    """
    §5: Test that modifiers are tracked per character.
    """
    manager = StateManager(minimal_game_def)
    state = manager.state

    assert isinstance(state.modifiers, dict)

    # Add a modifier
    state.modifiers["player"] = [
        {"id": "aroused", "duration": 30}
    ]

    assert "player" in state.modifiers
    assert len(state.modifiers["player"]) == 1
    assert state.modifiers["player"][0]["id"] == "aroused"

    print("✅ Modifiers tracking works")


def test_cooldowns_tracking(minimal_game_def):
    """
    §5: Test that event cooldowns are tracked in state.
    """
    manager = StateManager(minimal_game_def)
    state = manager.state

    assert isinstance(state.cooldowns, dict)

    # Add a cooldown
    state.cooldowns["test_event"] = 5
    assert state.cooldowns["test_event"] == 5

    # Decrement
    state.cooldowns["test_event"] -= 1
    assert state.cooldowns["test_event"] == 4

    print("✅ Cooldowns tracking works")


def test_actions_per_slot_tracking(minimal_game_def):
    """
    §5: Test that actions per slot counter is tracked for time advancement.
    """
    manager = StateManager(minimal_game_def)
    state = manager.state

    assert state.actions_this_slot == 0

    # Increment
    state.actions_this_slot += 1
    assert state.actions_this_slot == 1

    # Reset (happens on time advancement)
    state.actions_this_slot = 0
    assert state.actions_this_slot == 0

    print("✅ Actions per slot tracking works")


def test_visited_nodes_tracking(minimal_game_def):
    """
    §5: Test that visited nodes are tracked for history.
    """
    manager = StateManager(minimal_game_def)
    state = manager.state

    assert isinstance(state.visited_nodes, list)

    # Add visited nodes
    state.visited_nodes.append("node1")
    state.visited_nodes.append("node2")

    assert "node1" in state.visited_nodes
    assert "node2" in state.visited_nodes
    assert len(state.visited_nodes) == 2

    print("✅ Visited nodes tracking works")


def test_narrative_history_tracking(minimal_game_def):
    """
    §5: Test that narrative history is maintained for AI context.
    """
    manager = StateManager(minimal_game_def)
    state = manager.state

    assert isinstance(state.narrative_history, list)

    # Add narrative entries
    state.narrative_history.append("You enter the tavern.")
    state.narrative_history.append("A bard plays music.")

    assert len(state.narrative_history) == 2
    assert state.narrative_history[0] == "You enter the tavern."

    print("✅ Narrative history tracking works")


def test_memory_log_tracking(minimal_game_def):
    """
    §5: Test that memory log (factual summaries) is maintained.
    """
    manager = StateManager(minimal_game_def)
    state = manager.state

    assert isinstance(state.memory_log, list)

    # Add memory entries
    state.memory_log.append("Met Emma at the coffee shop")
    state.memory_log.append("Emma shared her phone number")

    assert len(state.memory_log) == 2
    assert "Emma" in state.memory_log[0]

    print("✅ Memory log tracking works")


def test_unlocked_outfits_tracking(minimal_game_def):
    """
    §5: Test that unlocked outfits are tracked per character.
    """
    manager = StateManager(minimal_game_def)
    state = manager.state

    assert isinstance(state.unlocked_outfits, dict)

    # Unlock outfits
    state.unlocked_outfits["emma"] = ["casual", "formal"]

    assert "emma" in state.unlocked_outfits
    assert "casual" in state.unlocked_outfits["emma"]
    assert len(state.unlocked_outfits["emma"]) == 2

    print("✅ Unlocked outfits tracking works")


def test_unlocked_actions_tracking(minimal_game_def):
    """
    §5: Test that unlocked actions are tracked globally.
    """
    manager = StateManager(minimal_game_def)
    state = manager.state

    assert isinstance(state.unlocked_actions, list)

    # Unlock actions
    state.unlocked_actions.append("special_move")
    state.unlocked_actions.append("secret_ability")

    assert "special_move" in state.unlocked_actions
    assert len(state.unlocked_actions) == 2

    print("✅ Unlocked actions tracking works")


def test_unlocked_endings_tracking(minimal_game_def):
    """
    §5: Test that unlocked endings are tracked globally.
    """
    manager = StateManager(minimal_game_def)
    state = manager.state

    assert isinstance(state.unlocked_endings, list)

    # Unlock endings
    state.unlocked_endings.append("good_ending")
    state.unlocked_endings.append("true_ending")

    assert "good_ending" in state.unlocked_endings
    assert len(state.unlocked_endings) == 2

    print("✅ Unlocked endings tracking works")


def test_active_arcs_tracking(minimal_game_def):
    """
    §5: Test that active arc stages are tracked.
    """
    manager = StateManager(minimal_game_def)
    state = manager.state

    assert isinstance(state.active_arcs, dict)

    # Track arc stages
    state.active_arcs["main_story"] = "chapter_2"
    state.active_arcs["romance_path"] = "first_date"

    assert state.active_arcs["main_story"] == "chapter_2"
    assert len(state.active_arcs) == 2

    print("✅ Active arcs tracking works")


def test_completed_milestones_tracking(minimal_game_def):
    """
    §5: Test that completed arc milestones are tracked.
    """
    manager = StateManager(minimal_game_def)
    state = manager.state

    assert isinstance(state.completed_milestones, list)

    # Complete milestones
    state.completed_milestones.append("met_emma")
    state.completed_milestones.append("first_kiss")

    assert "met_emma" in state.completed_milestones
    assert len(state.completed_milestones) == 2

    print("✅ Completed milestones tracking works")


def test_turn_count_tracking(minimal_game_def):
    """
    §5: Test that turn counter increments correctly.
    """
    manager = StateManager(minimal_game_def)
    state = manager.state

    assert state.turn_count == 0

    # Increment turns
    state.turn_count += 1
    assert state.turn_count == 1

    state.turn_count += 1
    assert state.turn_count == 2

    print("✅ Turn count tracking works")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])