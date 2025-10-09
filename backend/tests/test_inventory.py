"""
Tests for §11 Inventory & Items - PlotPlay v3 Spec

Items are defined objects that can be owned by player or NPCs:
- Categories: consumable, equipment, key, gift, trophy, misc
- Stackable or unique items
- Effects on use or gifting
- Economy and value system
- Unlocks and access gating

§11.1: Item Definition & Required Fields
§11.2: Item Categories
§11.3: Inventory Structure & State
§11.4: Inventory Effects (add/remove)
§11.5: Consumable Items
§11.6: Gift Items & Gift Effects
§11.7: Key Items & Unlocks
§11.8: Equipment Items
§11.9: Economy (value, stackable, droppable)
§11.10: Obtain Conditions
§11.11: Item Usage Mechanics
"""

import pytest
import yaml
from pathlib import Path

from app.core.game_loader import GameLoader
from app.core.state_manager import StateManager
from app.core.game_engine import GameEngine
from app.models.effects import InventoryChangeEffect


# =============================================================================
# § 11.1: Item Definition & Required Fields
# =============================================================================

def test_item_required_fields(tmp_path: Path):
    """
    §11.1: Test that items MUST have id, name, and category.
    """
    game_dir = tmp_path / "item_required"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'items': [
            {
                'id': 'flowers',
                'name': 'Bouquet of Flowers',
                'category': 'gift'
            },
            {
                'id': 'health_potion',
                'name': 'Health Potion',
                'category': 'consumable'
            }
        ],
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("item_required")

    # Items should be loaded
    assert len(game_def.items) == 2
    assert game_def.items[0].id == 'flowers'
    assert game_def.items[0].name == 'Bouquet of Flowers'
    assert game_def.items[0].category == 'gift'
    assert game_def.items[1].id == 'health_potion'
    assert game_def.items[1].name == 'Health Potion'
    assert game_def.items[1].category == 'consumable'

    print("✅ Item required fields (id, name, category) work")


# =============================================================================
# § 11.2: Item Categories
# =============================================================================

def test_item_categories(tmp_path: Path):
    """
    §11.2: Test all valid item categories.
    """
    game_dir = tmp_path / "item_categories"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'items': [
            {'id': 'potion', 'name': 'Potion', 'category': 'consumable'},
            {'id': 'sword', 'name': 'Sword', 'category': 'equipment'},
            {'id': 'key', 'name': 'Key', 'category': 'key'},
            {'id': 'flowers', 'name': 'Flowers', 'category': 'gift'},
            {'id': 'trophy', 'name': 'Trophy', 'category': 'trophy'},
            {'id': 'note', 'name': 'Note', 'category': 'misc'}
        ],
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("item_categories")

    # All categories should load
    categories = [item.category for item in game_def.items]
    assert 'consumable' in categories
    assert 'equipment' in categories
    assert 'key' in categories
    assert 'gift' in categories
    assert 'trophy' in categories
    assert 'misc' in categories

    print("✅ All item categories work")


def test_item_optional_fields(tmp_path: Path):
    """
    §11.2: Test optional item fields (description, tags, icon).
    """
    game_dir = tmp_path / "item_optional"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'items': [
            {
                'id': 'flowers',
                'name': 'Bouquet of Flowers',
                'category': 'gift',
                'description': 'Fresh roses wrapped neatly',
                'tags': ['romance', 'expensive'],
                'icon': '💐'
            }
        ],
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("item_optional")

    flowers = game_def.items[0]
    assert flowers.description == 'Fresh roses wrapped neatly'
    assert 'romance' in flowers.tags
    assert 'expensive' in flowers.tags
    assert flowers.icon == '💐'

    print("✅ Optional item fields work")


# =============================================================================
# § 11.3: Inventory Structure & State
# =============================================================================

def test_inventory_initialization(tmp_path: Path):
    """
    §11.3: Test that inventory state is properly initialized.
    """
    game_dir = tmp_path / "inventory_init"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'items': [
            {'id': 'flowers', 'name': 'Flowers', 'category': 'gift'}
        ],
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
    manager = StateManager(loader.load_game("inventory_init"))

    # Inventory should be initialized
    assert isinstance(manager.state.inventory, dict)
    assert 'player' in manager.state.inventory
    assert isinstance(manager.state.inventory['player'], dict)

    print("✅ Inventory initialization works")


def test_inventory_per_character(tmp_path: Path):
    """
    §11.3: Test that each character has their own inventory.
    """
    game_dir = tmp_path / "inventory_per_char"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'items': [
            {'id': 'key', 'name': 'Key', 'category': 'key'}
        ],
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
    engine = GameEngine(loader.load_game("inventory_per_char"), "test_session")

    # Give player a key
    engine.state_manager.state.inventory['player']['key'] = 1
    # Give Emma a different key
    engine.state_manager.state.inventory.setdefault('emma', {})['key'] = 1

    # Both should have separate inventories
    assert engine.state_manager.state.inventory['player']['key'] == 1
    assert engine.state_manager.state.inventory['emma']['key'] == 1

    # Removing from one shouldn't affect the other
    engine.state_manager.state.inventory['player']['key'] = 0
    assert engine.state_manager.state.inventory['emma']['key'] == 1

    print("✅ Per-character inventory works")


# =============================================================================
# § 11.4: Inventory Effects (add/remove)
# =============================================================================

def test_inventory_add_effect(tmp_path: Path):
    """
    §11.4: Test inventory_add effect.
    """
    game_dir = tmp_path / "inventory_add"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'items': [
            {'id': 'flowers', 'name': 'Flowers', 'category': 'gift'}
        ],
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    engine = GameEngine(loader.load_game("inventory_add"), "test_session")

    # Initially no flowers
    assert engine.state_manager.state.inventory['player'].get('flowers', 0) == 0

    # Add flowers
    effect = InventoryChangeEffect(
        type="inventory_add",
        owner="player",
        item="flowers",
        count=1
    )
    engine.inventory_manager.apply_effect(effect, engine.state_manager.state)

    # Should have 1 flowers
    assert engine.state_manager.state.inventory['player']['flowers'] == 1

    print("✅ inventory_add effect works")


def test_inventory_remove_effect(tmp_path: Path):
    """
    §11.4: Test inventory_remove effect.
    """
    game_dir = tmp_path / "inventory_remove"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'items': [
            {'id': 'flowers', 'name': 'Flowers', 'category': 'gift'}
        ],
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    engine = GameEngine(loader.load_game("inventory_remove"), "test_session")

    # Give player flowers
    engine.state_manager.state.inventory['player']['flowers'] = 3

    # Remove 1 flower
    effect = InventoryChangeEffect(
        type="inventory_remove",
        owner="player",
        item="flowers",
        count=1
    )
    engine.inventory_manager.apply_effect(effect, engine.state_manager.state)

    # Should have 2 left
    assert engine.state_manager.state.inventory['player']['flowers'] == 2

    print("✅ inventory_remove effect works")


def test_inventory_cannot_go_negative(tmp_path: Path):
    """
    §11.4: Test that inventory counts cannot go below 0.
    """
    game_dir = tmp_path / "inventory_negative"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'items': [
            {'id': 'flowers', 'name': 'Flowers', 'category': 'gift'}
        ],
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    engine = GameEngine(loader.load_game("inventory_negative"), "test_session")

    # Try to remove item that player doesn't have
    effect = InventoryChangeEffect(
        type="inventory_remove",
        owner="player",
        item="flowers",
        count=5
    )
    engine.inventory_manager.apply_effect(effect, engine.state_manager.state)

    # Should be clamped to 0
    assert engine.state_manager.state.inventory['player'].get('flowers', 0) == 0

    print("✅ Inventory cannot go negative")


# =============================================================================
# § 11.5: Consumable Items
# =============================================================================

def test_consumable_item_definition(tmp_path: Path):
    """
    §11.5: Test consumable items with effects_on_use.
    """
    game_dir = tmp_path / "consumable_def"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'energy': {'min': 0, 'max': 100, 'default': 50}
            }
        },
        'items': [
            {
                'id': 'energy_drink',
                'name': 'Energy Drink',
                'category': 'consumable',
                'consumable': True,
                'use_text': 'You chug the energy drink',
                'effects_on_use': [
                    {
                        'type': 'meter_change',
                        'target': 'player',
                        'meter': 'energy',
                        'op': 'add',
                        'value': 25
                    }
                ]
            }
        ],
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("consumable_def")

    # Check consumable definition
    energy_drink = game_def.items[0]
    assert energy_drink.consumable is True
    assert energy_drink.use_text == 'You chug the energy drink'
    assert len(energy_drink.effects_on_use) == 1
    assert energy_drink.effects_on_use[0].type == 'meter_change'

    print("✅ Consumable item definition works")


def test_using_consumable_item(tmp_path: Path):
    """
    §11.5: Test that using a consumable item applies effects and removes item.
    """
    game_dir = tmp_path / "use_consumable"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'energy': {'min': 0, 'max': 100, 'default': 50}
            }
        },
        'items': [
            {
                'id': 'energy_drink',
                'name': 'Energy Drink',
                'category': 'consumable',
                'consumable': True,
                'effects_on_use': [
                    {
                        'type': 'meter_change',
                        'target': 'player',
                        'meter': 'energy',
                        'op': 'add',
                        'value': 25
                    }
                ]
            }
        ],
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    engine = GameEngine(loader.load_game("use_consumable"), "test_session")

    # Give player an energy drink
    engine.state_manager.state.inventory['player']['energy_drink'] = 1
    initial_energy = engine.state_manager.state.meters['player']['energy']
    # Use the item
    effects = engine.inventory_manager.use_item('player', 'energy_drink', engine.state_manager.state)
    engine.apply_effects(effects)

    # Energy should increase
    assert engine.state_manager.state.meters['player']['energy'] == initial_energy + 25
    # Item should be consumed
    assert engine.state_manager.state.inventory['player']['energy_drink'] == 0

    print("✅ Using consumable items works")


# =============================================================================
# § 11.6: Gift Items & Gift Effects
# =============================================================================

def test_gift_item_definition(tmp_path: Path):
    """
    §11.6: Test gift items with can_give and gift_effects.
    """
    game_dir = tmp_path / "gift_def"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'character_template': {
                'attraction': {'min': 0, 'max': 100, 'default': 10}
            }
        },
        'items': [
            {
                'id': 'flowers',
                'name': 'Flowers',
                'category': 'gift',
                'can_give': True,
                'gift_effects': [
                    {
                        'type': 'meter_change',
                        'target': 'emma',
                        'meter': 'attraction',
                        'op': 'add',
                        'value': 15
                    }
                ]
            }
        ],
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
    game_def = loader.load_game("gift_def")

    # Check gift definition
    flowers = game_def.items[0]
    assert flowers.can_give is True
    assert len(flowers.gift_effects) == 1
    assert flowers.gift_effects[0].type == 'meter_change'

    print("✅ Gift item definition works")


# =============================================================================
# § 11.7: Key Items & Unlocks
# =============================================================================

def test_key_item_with_unlocks(tmp_path: Path):
    """
    §11.7: Test key items with unlocks definition.
    """
    game_dir = tmp_path / "key_unlock"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'dorm_room'}},
        'items': [
            {
                'id': 'dorm_key',
                'name': 'Dorm Key',
                'category': 'key',
                'droppable': False,
                'unlocks': {
                    'location': 'dorm_room'
                }
            }
        ],
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'dorm_room', 'name': 'Dorm Room'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("key_unlock")

    # Check key definition
    dorm_key = game_def.items[0]
    assert dorm_key.category == 'key'
    assert dorm_key.droppable is False
    assert dorm_key.unlocks is not None
    assert dorm_key.unlocks['location'] == 'dorm_room'

    print("✅ Key item with unlocks works")


# =============================================================================
# § 11.8: Equipment Items
# =============================================================================

def test_equipment_item_with_slots(tmp_path: Path):
    """
    §11.8: Test equipment items with slots and stat_mods.
    """
    game_dir = tmp_path / "equipment"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'items': [
            {
                'id': 'lucky_charm',
                'name': 'Lucky Charm',
                'category': 'equipment',
                'slots': ['accessory'],
                'stat_mods': {
                    'boldness': 5
                }
            }
        ],
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("equipment")

    # Check equipment definition
    charm = game_def.items[0]
    assert charm.category == 'equipment'
    assert 'accessory' in charm.slots
    assert charm.stat_mods['boldness'] == 5

    print("✅ Equipment item definition works")


# =============================================================================
# § 11.9: Economy (value, stackable, droppable)
# =============================================================================

def test_item_value_property(tmp_path: Path):
    """
    §11.9: Test item value for economy system.
    """
    game_dir = tmp_path / "item_value"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'items': [
            {
                'id': 'flowers',
                'name': 'Flowers',
                'category': 'gift',
                'value': 20
            },
            {
                'id': 'coffee',
                'name': 'Coffee',
                'category': 'consumable',
                'value': 5
            }
        ],
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("item_value")

    # Check values
    flowers = next(item for item in game_def.items if item.id == 'flowers')
    coffee = next(item for item in game_def.items if item.id == 'coffee')
    assert flowers.value == 20
    assert coffee.value == 5

    print("✅ Item value property works")


def test_stackable_items(tmp_path: Path):
    """
    §11.9: Test stackable vs non-stackable items.
    """
    game_dir = tmp_path / "stackable"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'items': [
            {
                'id': 'flowers',
                'name': 'Flowers',
                'category': 'gift',
                'stackable': False  # Unique item
            },
            {
                'id': 'potion',
                'name': 'Potion',
                'category': 'consumable',
                'stackable': True  # Can have multiple
            }
        ],
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    engine = GameEngine(loader.load_game("stackable"), "test_session")

    # Try to add 5 non-stackable items - should clamp to 1
    for _ in range(5):
        effect = InventoryChangeEffect(
            type="inventory_add",
            owner="player",
            item="flowers",
            count=1
        )
        engine.inventory_manager.apply_effect(effect, engine.state_manager.state)

    # Should only have 1
    assert engine.state_manager.state.inventory['player']['flowers'] == 1

    # Add 5 stackable items - should all be added
    for _ in range(5):
        effect = InventoryChangeEffect(
            type="inventory_add",
            owner="player",
            item="potion",
            count=1
        )
        engine.inventory_manager.apply_effect(effect, engine.state_manager.state)

    # Should have 5
    assert engine.state_manager.state.inventory['player']['potion'] == 5

    print("✅ Stackable vs non-stackable items work")


def test_droppable_property(tmp_path: Path):
    """
    §11.9: Test droppable property on items.
    """
    game_dir = tmp_path / "droppable"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'items': [
            {
                'id': 'quest_item',
                'name': 'Quest Item',
                'category': 'key',
                'droppable': False  # Cannot drop
            },
            {
                'id': 'junk',
                'name': 'Junk',
                'category': 'misc',
                'droppable': True  # Can drop
            }
        ],
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("droppable")

    quest_item = next(item for item in game_def.items if item.id == 'quest_item')
    junk = next(item for item in game_def.items if item.id == 'junk')

    assert quest_item.droppable is False
    assert junk.droppable is True

    print("✅ Droppable property works")


# =============================================================================
# § 11.10: Obtain Conditions
# =============================================================================

def test_item_obtain_conditions(tmp_path: Path):
    """
    §11.10: Test obtain_conditions for item acquisition gating.
    """
    game_dir = tmp_path / "obtain_conditions"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'confidence': {'min': 0, 'max': 100, 'default': 20}
            }
        },
        'items': [
            {
                'id': 'condoms',
                'name': 'Condoms',
                'category': 'consumable',
                'obtain_conditions': [
                    'meters.player.confidence >= 30'
                ]
            }
        ],
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("obtain_conditions")

    # Check obtain conditions
    condoms = game_def.items[0]
    assert len(condoms.obtain_conditions) == 1
    assert 'meters.player.confidence >= 30' in condoms.obtain_conditions

    print("✅ Obtain conditions definition works")


# =============================================================================
# § 11.11: Item Usage Mechanics
# =============================================================================

def test_item_use_text(tmp_path: Path):
    """
    §11.11: Test use_text flavor text for items.
    """
    game_dir = tmp_path / "use_text"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'items': [
            {
                'id': 'potion',
                'name': 'Health Potion',
                'category': 'consumable',
                'use_text': 'You drink the sweet-tasting potion and feel refreshed.',
                'consumable': True,
                'effects_on_use': []
            }
        ],
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("use_text")

    potion = game_def.items[0]
    assert potion.use_text == 'You drink the sweet-tasting potion and feel refreshed.'

    print("✅ Item use_text works")


def test_target_property_for_items(tmp_path: Path):
    """
    §11.11: Test target property (player/character/any).
    """
    game_dir = tmp_path / "item_target"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'items': [
            {
                'id': 'player_potion',
                'name': 'Player Potion',
                'category': 'consumable',
                'target': 'player'
            },
            {
                'id': 'gift_item',
                'name': 'Gift',
                'category': 'gift',
                'target': 'character'
            }
        ],
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("item_target")

    player_potion = next(item for item in game_def.items if item.id == 'player_potion')
    gift = next(item for item in game_def.items if item.id == 'gift_item')

    assert player_potion.target == 'player'
    assert gift.target == 'character'

    print("✅ Item target property works")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])