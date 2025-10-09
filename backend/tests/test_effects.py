"""
Tests for §13 Effects - PlotPlay v3 Spec

Effects are atomic, declarative state changes that are:
- Deterministic (applied in order, validated)
- Declarative (describe what, not how)
- Guarded (can have 'when' conditions)
- Validated (invalid effects rejected with warnings)

§13.1: Effect Definition & Structure
§13.2: Catalog of Effect Types
  - meter_change
  - flag_set
  - inventory_add/remove
  - apply_modifier/remove_modifier
  - outfit_change/clothing_set
  - move_to
  - advance_time
  - goto_node
  - conditional
  - random
  - unlock_outfit/actions/ending
§13.3: Execution Order
§13.4: Constraints & Validation
"""

import pytest
import yaml
from pathlib import Path

from unicodedata import category

from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine
from app.core.state_manager import StateManager
from app.models.effects import (
    MeterChangeEffect, FlagSetEffect, InventoryChangeEffect,
    ClothingChangeEffect, MoveToEffect, AdvanceTimeEffect,
    GotoNodeEffect, UnlockEffect, ApplyModifierEffect,
    RemoveModifierEffect, ConditionalEffect, RandomEffect, RandomChoice
)
from app.models.enums import ItemCategory
from app.models.game import GameDefinition, MetaConfig, StartConfig
from app.models.node import Node, NodeType
from app.models.location import Zone, Location, LocationPrivacy
from app.models.character import Character, Wardrobe, Outfit
from app.models.modifier import Modifier
from app.models.item import Item


# =============================================================================
# § 13.1: Effect Definition & Structure
# =============================================================================

def test_effect_has_when_guard(tmp_path: Path):
    """
    §13.1: Effects can have 'when' guard conditions using Expression DSL.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'meters': {'player': {'health': {'min': 0, 'max': 100, 'default': 50}}},
        'flags': {'test_flag': {'type': 'bool', 'default': False}}
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    # Effect with guard that should pass
    effect_pass = MeterChangeEffect(
        when="meters.player.health < 60",
        target="player",
        meter="health",
        op="add",
        value=10
    )

    # Effect with guard that should fail
    effect_fail = MeterChangeEffect(
        when="meters.player.health > 60",
        target="player",
        meter="health",
        op="add",
        value=10
    )

    initial_health = engine.state_manager.state.meters["player"]["health"]
    engine.apply_effects([effect_pass, effect_fail])

    # Only first effect should apply (50 + 10 = 60)
    assert engine.state_manager.state.meters["player"]["health"] == initial_health + 10
    print("✅ Effect guard conditions work correctly")


# =============================================================================
# § 13.2: Catalog of Effect Types - Meter Change
# =============================================================================

def test_meter_change_add_operation(tmp_path: Path):
    """
    §13.2: Test meter_change with 'add' operation.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'meters': {'player': {'health': {'min': 0, 'max': 100, 'default': 50}}}
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    effect = MeterChangeEffect(target="player", meter="health", op="add", value=15)
    engine.apply_effects([effect])

    assert engine.state_manager.state.meters["player"]["health"] == 65
    print("✅ Meter change 'add' operation works")


def test_meter_change_subtract_operation(tmp_path: Path):
    """
    §13.2: Test meter_change with 'subtract' operation.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'meters': {'player': {'health': {'min': 0, 'max': 100, 'default': 50}}}
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    effect = MeterChangeEffect(target="player", meter="health", op="subtract", value=20)
    engine.apply_effects([effect])

    assert engine.state_manager.state.meters["player"]["health"] == 30
    print("✅ Meter change 'subtract' operation works")


def test_meter_change_set_operation(tmp_path: Path):
    """
    §13.2: Test meter_change with 'set' operation.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'meters': {'player': {'health': {'min': 0, 'max': 100, 'default': 50}}}
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    effect = MeterChangeEffect(target="player", meter="health", op="set", value=75)
    engine.apply_effects([effect])

    assert engine.state_manager.state.meters["player"]["health"] == 75
    print("✅ Meter change 'set' operation works")


def test_meter_change_multiply_operation(tmp_path: Path):
    """
    §13.2: Test meter_change with 'multiply' operation.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'meters': {'player': {'health': {'min': 0, 'max': 100, 'default': 50}}}
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    effect = MeterChangeEffect(target="player", meter="health", op="multiply", value=1.5)
    engine.apply_effects([effect])

    assert engine.state_manager.state.meters["player"]["health"] == 75  # 50 * 1.5
    print("✅ Meter change 'multiply' operation works")


def test_meter_change_divide_operation(tmp_path: Path):
    """
    §13.2: Test meter_change with 'divide' operation.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'meters': {'player': {'health': {'min': 0, 'max': 100, 'default': 50}}}
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    effect = MeterChangeEffect(target="player", meter="health", op="divide", value=2)
    engine.apply_effects([effect])

    assert engine.state_manager.state.meters["player"]["health"] == 25  # 50 / 2
    print("✅ Meter change 'divide' operation works")


def test_meter_change_respects_caps(tmp_path: Path):
    """
    §13.2: Test that meter_change respects min/max caps when respect_caps=True.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'meters': {'player': {'health': {'min': 0, 'max': 100, 'default': 50}}}
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    # Try to exceed max
    effect_over = MeterChangeEffect(
        target="player", meter="health", op="add", value=100, respect_caps=True
    )
    engine.apply_effects([effect_over])
    assert engine.state_manager.state.meters["player"]["health"] == 100  # Capped at max

    # Try to go below min
    effect_under = MeterChangeEffect(
        target="player", meter="health", op="subtract", value=200, respect_caps=True
    )
    engine.apply_effects([effect_under])
    assert engine.state_manager.state.meters["player"]["health"] == 0  # Capped at min

    print("✅ Meter changes respect caps")


# =============================================================================
# § 13.2: Catalog of Effect Types - Flag Set
# =============================================================================

def test_flag_set_bool_value(tmp_path: Path):
    """
    §13.2: Test flag_set with boolean value.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'flags': {'completed_quest': {'type': 'bool', 'default': False}}
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    effect = FlagSetEffect(key="completed_quest", value=True)
    engine.apply_effects([effect])

    assert engine.state_manager.state.flags["completed_quest"] is True
    print("✅ Flag set with boolean value works")


def test_flag_set_number_value(tmp_path: Path):
    """
    §13.2: Test flag_set with number value.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'flags': {'score': {'type': 'number', 'default': 0}}
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    effect = FlagSetEffect(key="score", value=100)
    engine.apply_effects([effect])

    assert engine.state_manager.state.flags["score"] == 100
    print("✅ Flag set with number value works")


def test_flag_set_string_value(tmp_path: Path):
    """
    §13.2: Test flag_set with string value.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'flags': {'relationship_status': {'type': 'string', 'default': 'single'}}
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    effect = FlagSetEffect(key="relationship_status", value="dating")
    engine.apply_effects([effect])

    assert engine.state_manager.state.flags["relationship_status"] == "dating"
    print("✅ Flag set with string value works")


# =============================================================================
# § 13.2: Catalog of Effect Types - Inventory
# =============================================================================

def test_inventory_add_effect(tmp_path: Path):
    """
    §13.2: Test inventory_add effect adds items to inventory.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'items': [{'id': 'potion', 'name': 'Health Potion', 'stackable': True, 'category': ItemCategory.CONSUMABLE.value}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    effect = InventoryChangeEffect(type="inventory_add", owner="player", item="potion", count=3)
    engine.apply_effects([effect])

    assert engine.state_manager.state.inventory["player"]["potion"] == 3
    print("✅ Inventory add effect works")


def test_inventory_remove_effect(tmp_path: Path):
    """
    §13.2: Test inventory_remove effect removes items from inventory.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'items': [{'id': 'potion', 'name': 'Health Potion', 'stackable': True, 'category': ItemCategory.CONSUMABLE.value}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    # Add items first
    engine.state_manager.state.inventory["player"]["potion"] = 5

    # Remove some
    effect = InventoryChangeEffect(type="inventory_remove", owner="player", item="potion", count=2)
    engine.apply_effects([effect])

    assert engine.state_manager.state.inventory["player"]["potion"] == 3
    print("✅ Inventory remove effect works")


# =============================================================================
# § 13.2: Catalog of Effect Types - Modifiers
# =============================================================================

def test_apply_modifier_effect(tmp_path: Path):
    """
    §13.2: Test apply_modifier effect applies modifiers to characters.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'},
            {'id': 'emma', 'name': 'Emma', 'age': 24, 'gender': 'female'}
        ],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'modifier_system': {
            'library': {
                'aroused': {
                    'id': 'aroused',
                    'group': 'state',
                    'duration_default_min': 60
                }
            }
        }
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    print(game_def.modifier_system)

    effect = ApplyModifierEffect(character="emma", modifier_id="aroused", duration_min=30)
    engine.apply_effects([effect])

    assert "aroused" in [m['id'] for m in engine.state_manager.state.modifiers.get("emma", [])]
    print("✅ Apply modifier effect works")


def test_remove_modifier_effect(tmp_path: Path):
    """
    §13.2: Test remove_modifier effect removes modifiers from characters.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'},
            {'id': 'emma', 'name': 'Emma', 'age': 24, 'gender': 'female'}
        ],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'modifiers': {
            'library': {
                'aroused': {
                    'id': 'aroused',
                    'group': 'state',
                    'duration_default_min': 60
                }
            }
        }
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    # Apply modifier first
    engine.state_manager.state.modifiers["emma"] = [
        {'id': 'aroused', 'expires_turn': None}
    ]

    # Remove it
    effect = RemoveModifierEffect(character="emma", modifier_id="aroused")
    engine.apply_effects([effect])

    assert "aroused" not in [m['id'] for m in engine.state_manager.state.modifiers.get("emma", [])]
    print("✅ Remove modifier effect works")


# =============================================================================
# § 13.2: Catalog of Effect Types - Clothing
# =============================================================================

def test_outfit_change_effect(tmp_path: Path):
    """
    §13.2: Test outfit_change effect changes character's outfit.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'},
            {
                'id': 'emma',
                'name': 'Emma',
                'age': 24,
                'gender': 'female',
                'wardrobe': {
                    'outfits': [
                        {
                            'id': 'casual',
                            'name': 'Casual',
                            'layers': {'top': {'item': 'shirt'}, 'bottom': {'item': 'jeans'}}
                        },
                        {
                            'id': 'formal',
                            'name': 'Formal',
                            'layers': {'dress': {'item': 'dress'}}
                        }
                    ]
                }
            }
        ],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    effect = ClothingChangeEffect(type="outfit_change", character="emma", outfit="formal")
    engine.apply_effects([effect])

    assert engine.state_manager.state.clothing_states["emma"]["current_outfit"] == "formal"
    print("✅ Outfit change effect works")


def test_clothing_set_effect(tmp_path: Path):
    """
    §13.2: Test clothing_set effect changes individual clothing layer state.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'},
            {
                'id': 'emma',
                'name': 'Emma',
                'age': 24,
                'gender': 'female',
                'wardrobe': {
                    'outfits': [
                        {
                            'id': 'casual',
                            'name': 'Casual',
                            'layers': {'top': {'item': 'shirt'}, 'bottom': {'item': 'jeans'}}
                        }
                    ]
                }
            }
        ],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    effect = ClothingChangeEffect(
        type="clothing_set",
        character="emma",
        layer="top",
        state="displaced"
    )
    engine.apply_effects([effect])

    assert engine.state_manager.state.clothing_states["emma"]["layers"]["top"] == "displaced"
    print("✅ Clothing set effect works")


# =============================================================================
# § 13.2: Catalog of Effect Types - Movement & Time
# =============================================================================

def test_move_to_effect(tmp_path: Path):
    """
    §13.2: Test move_to effect moves player to new location.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{
            'id': 'z1',
            'name': 'Zone 1',
            'locations': [
                {'id': 'l1', 'name': 'Location 1'},
                {'id': 'l2', 'name': 'Location 2'}
            ]
        }],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    assert engine.state_manager.state.location_current == "l1"

    effect = MoveToEffect(location="l2")
    engine.apply_effects([effect])

    assert engine.state_manager.state.location_current == "l2"
    print("✅ Move to effect works")


def test_advance_time_effect(tmp_path: Path):
    """
    §13.2: Test advance_time effect advances game time.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'time': {'mode': 'clock', 'clock': {'minutes_per_day': 1440}, 'start': {'day': 1, 'time': '00:00'}}
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    # Check the initial time was read correctly
    assert engine.state_manager.state.time_hhmm == "00:00"

    effect = AdvanceTimeEffect(minutes=30)
    engine.apply_effects([effect])

    # Check that time advanced for 30 minutes
    assert engine.state_manager.state.time_hhmm == "00:30"

    print("✅ Advance time effect works")


# =============================================================================
# § 13.2: Catalog of Effect Types - Flow Control
# =============================================================================

def test_goto_node_effect(tmp_path: Path):
    """
    §13.2: Test goto_node effect transitions to another node.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [
            {'id': 'n1', 'type': 'scene', 'title': 'Scene 1', 'transitions': []},
            {'id': 'n2', 'type': 'scene', 'title': 'Scene 2', 'transitions': []}
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    assert engine.state_manager.state.current_node == "n1"

    effect = GotoNodeEffect(node="n2")
    engine.apply_effects([effect])

    assert engine.state_manager.state.current_node == "n2"
    print("✅ Goto node effect works")


def test_conditional_effect_then_branch(tmp_path: Path):
    """
    §13.2: Test conditional effect executes 'then' branch when condition is true.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'meters': {'player': {'health': {'min': 0, 'max': 100, 'default': 30}}},
        'flags': {'low_health': {'type': 'bool', 'default': False}}
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    effect = ConditionalEffect(
        when="meters.player.health < 50",
        then=[FlagSetEffect(key="low_health", value=True)],
        otherwise=[]
    )
    engine.apply_effects([effect])

    assert engine.state_manager.state.flags["low_health"] is True
    print("✅ Conditional effect 'then' branch works")


def test_conditional_effect_otherwise_branch(tmp_path: Path):
    """
    §13.2: Test conditional effect executes 'otherwise' branch when condition is false.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'meters': {'player': {'health': {'min': 0, 'max': 100, 'default': 80}}},
        'flags': {'high_health': {'type': 'bool', 'default': False}}
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    effect = ConditionalEffect(
        when="meters.player.health < 50",
        then=[],
        otherwise=[FlagSetEffect(key="high_health", value=True)]
    )
    engine.apply_effects([effect])

    assert engine.state_manager.state.flags["high_health"] is True
    print("✅ Conditional effect 'otherwise' branch works")


def test_random_effect_deterministic(tmp_path: Path):
    """
    §13.2: Test random effect is deterministic with same seed.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'flags': {
            'outcome_a': {'type': 'bool', 'default': False},
            'outcome_b': {'type': 'bool', 'default': False}
        }
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    # Two engines with same session ID should produce same results
    engine1 = GameEngine(game_def, "same_session")
    engine2 = GameEngine(game_def, "same_session")

    effect = RandomEffect(
        choices=[
            RandomChoice(weight=50, effects=[FlagSetEffect(key="outcome_a", value=True)]),
            RandomChoice(weight=50, effects=[FlagSetEffect(key="outcome_b", value=True)])
        ]
    )

    engine1.apply_effects([effect])
    engine2.apply_effects([effect])

    # Both should have identical outcomes
    assert engine1.state_manager.state.flags["outcome_a"] == engine2.state_manager.state.flags["outcome_a"]
    assert engine1.state_manager.state.flags["outcome_b"] == engine2.state_manager.state.flags["outcome_b"]
    print("✅ Random effect is deterministic with same seed")


# =============================================================================
# § 13.2: Catalog of Effect Types - Unlocks
# =============================================================================

def test_unlock_outfit_effect(tmp_path: Path):
    """
    §13.2: Test unlock_outfit effect unlocks new outfit for character.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'},
            {
                'id': 'emma',
                'name': 'Emma',
                'age': 24,
                'gender': 'female',
                'wardrobe': {
                    'outfits': [
                        {
                            'id': 'casual',
                            'name': 'Casual',
                            'layers': {'top': {'item': 'shirt'}}
                        },
                        {
                            'id': 'sexy',
                            'name': 'Sexy',
                            'unlock_when': 'false',
                            'layers': {'dress': {'item': 'dress'}}
                        }
                    ]
                }
            }
        ],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    # Initially locked
    assert "sexy" not in engine.state_manager.state.unlocked_outfits.get("emma", [])

    effect = UnlockEffect(type="unlock_outfit", character="emma", outfit="sexy")
    engine.apply_effects([effect])

    # Should now be unlocked
    assert "sexy" in engine.state_manager.state.unlocked_outfits.get("emma", [])
    print("✅ Unlock outfit effect works")


def test_unlock_actions_effect(tmp_path: Path):
    """
    §13.2: Test unlock_actions effect unlocks new actions.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'actions': [
            {'id': 'flirt', 'prompt': 'Flirt'}
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    effect = UnlockEffect(type="unlock_actions", actions=["flirt"])
    engine.apply_effects([effect])

    assert "flirt" in engine.state_manager.state.unlocked_actions
    print("✅ Unlock actions effect works")


def test_unlock_ending_effect(tmp_path: Path):
    """
    §13.2: Test unlock_ending effect unlocks new ending.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [
            {'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []},
            {'id': 'ending1', 'type': 'ending', 'ending_id': 'ending1', 'title': 'Happy Ending', 'transitions': []}
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    effect = UnlockEffect(type="unlock_ending", ending="ending1")
    engine.apply_effects([effect])

    assert "ending1" in engine.state_manager.state.unlocked_endings
    print("✅ Unlock ending effect works")


# =============================================================================
# § 13.3: Execution Order
# =============================================================================

def test_effects_execute_in_order(tmp_path: Path):
    """
    §13.3: Test that effects execute in the order they are defined.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'meters': {'player': {'health': {'min': 0, 'max': 100, 'default': 50}}}
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    # Effects that depend on order
    effects = [
        MeterChangeEffect(target="player", meter="health", op="add", value=20),  # 50 -> 70
        MeterChangeEffect(target="player", meter="health", op="multiply", value=2),  # 70 -> 140 (capped at 100)
        MeterChangeEffect(target="player", meter="health", op="subtract", value=10)  # 100 -> 90
    ]

    engine.apply_effects(effects)

    # Final result should be 90 if order is respected
    assert engine.state_manager.state.meters["player"]["health"] == 90
    print("✅ Effects execute in order")


# =============================================================================
# § 13.4: Constraints & Validation
# =============================================================================

def test_invalid_meter_reference_rejected(tmp_path: Path, caplog):
    """
    §13.4: Test that effects with invalid meter references are rejected and logged.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'meters': {'player': {'health': {'min': 0, 'max': 100, 'default': 50}}}
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    # Effect with invalid meter reference
    effect = MeterChangeEffect(target="player", meter="nonexistent", op="add", value=10)

    initial_meters = dict(engine.state_manager.state.meters["player"])
    engine.apply_effects([effect])

    # Meters should be unchanged
    assert engine.state_manager.state.meters["player"] == initial_meters
    print("✅ Invalid meter references are rejected")


def test_invalid_item_reference_rejected(tmp_path: Path):
    """
    §13.4: Test that effects with invalid item references are rejected.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'items': [{'id': 'potion', 'name': 'Potion', 'stackable': True, 'category': ItemCategory.CONSUMABLE.value}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    # Effect with invalid item reference
    effect = InventoryChangeEffect(type="inventory_add", owner="player", item="nonexistent", count=1)

    engine.apply_effects([effect])
    inventory = dict(engine.state_manager.state.inventory.get("player", {}))
    print(inventory)

    # Inventory should be unchanged or item not added
    assert "nonexistent" not in engine.state_manager.state.inventory.get("player", {})
    print("✅ Invalid item references are rejected")


def test_invalid_location_reference_rejected(tmp_path: Path):
    """
    §13.4: Test that effects with invalid location references are rejected.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    initial_location = engine.state_manager.state.location_current

    # Effect with invalid location reference
    effect = MoveToEffect(location="nonexistent")
    engine.apply_effects([effect])

    # Location should be unchanged
    assert engine.state_manager.state.location_current == initial_location
    print("✅ Invalid location references are rejected")


def test_guard_condition_false_skips_effect(tmp_path: Path):
    """
    §13.4: Test that effects with false guard conditions are skipped silently.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'meters': {'player': {'health': {'min': 0, 'max': 100, 'default': 50}}}
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    # Effect with false guard condition
    effect = MeterChangeEffect(
        when="meters.player.health > 100",  # This is false (50 > 100)
        target="player",
        meter="health",
        op="add",
        value=10
    )

    initial_health = engine.state_manager.state.meters["player"]["health"]
    engine.apply_effects([effect])

    # Health should be unchanged because guard was false
    assert engine.state_manager.state.meters["player"]["health"] == initial_health
    print("✅ False guard conditions skip effects silently")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])