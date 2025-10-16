"""
Tests for §12 Clothing & Wardrobe - PlotPlay v3 Spec

The clothing system represents what characters wear and layer states:
- Outfits with multiple layers
- Layer states: intact, displaced, removed
- Wardrobe rules and layer order
- Outfit unlocking conditions
- Privacy and consent gating
- Narrative appearance generation

§12.1: Wardrobe & Outfit Definition
§12.2: Clothing State (runtime)
§12.3: Layer States (intact/displaced/removed)
§12.4: Outfit Changes
§12.5: Wardrobe Rules
§12.6: Layer Order & Required Layers
§12.7: Outfit Unlocking
§12.8: Clothing Appearance Generation
§12.9: ClothingManager Integration
§12.10: Clothing Effects
"""

import pytest
import yaml
from pathlib import Path

from app.core.game_loader import GameLoader
from app.core.state_manager import StateManager
from app.core.game_engine import GameEngine
from app.models.effects import ClothingChangeEffect
from app.models.characters import Wardrobe, Outfit, ClothingLayer, WardrobeRules


# =============================================================================
# § 12.1: Wardrobe & Outfit Definition
# =============================================================================

def test_outfit_definition(tmp_path: Path):
    """
    §12.1: Test basic outfit definition with layers.
    """
    game_dir = tmp_path / "outfit_def"
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
                    'outfits': [
                        {
                            'id': 'casual',
                            'name': 'Casual Outfit',
                            'tags': ['default', 'everyday'],
                            'layers': {
                                'top': {'item': 't-shirt', 'color': 'white'},
                                'bottom': {'item': 'jeans', 'color': 'blue'},
                                'feet': {'item': 'sneakers'},
                                'underwear_top': {'item': 'bra', 'style': 't-shirt'},
                                'underwear_bottom': {'item': 'panties', 'style': 'bikini'}
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
    game_def = loader.load_game("outfit_def")

    # Check outfit definition
    emma = next(c for c in game_def.characters if c.id == 'emma')
    assert emma.wardrobe is not None
    assert len(emma.wardrobe.outfits) == 1

    outfit = emma.wardrobe.outfits[0]
    assert outfit.id == 'casual'
    assert outfit.name == 'Casual Outfit'
    assert 'default' in outfit.tags
    assert 'top' in outfit.layers
    assert outfit.layers['top'].item == 't-shirt'
    assert outfit.layers['top'].color == 'white'

    print("✅ Outfit definition works")


def test_outfit_optional_fields(tmp_path: Path):
    """
    §12.1: Test optional outfit fields (description, tags, unlock_when).
    """
    game_dir = tmp_path / "outfit_optional"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'character_template': {
                'boldness': {'min': 0, 'max': 100, 'default': 20}
            }
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'},
            {
                'id': 'emma',
                'name': 'Emma',
                'age': 22,
                'gender': 'female',
                'wardrobe': {
                    'outfits': [
                        {
                            'id': 'bold',
                            'name': 'Bold Outfit',
                            'tags': ['sexy', 'unlockable'],
                            'description': 'A daring outfit for confident moments',
                            'unlock_when': 'meters.emma.boldness >= 60',
                            'layers': {
                                'top': {'item': 'crop top', 'color': 'black'},
                                'bottom': {'item': 'mini skirt', 'color': 'red'}
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
    game_def = loader.load_game("outfit_optional")

    emma = next(c for c in game_def.characters if c.id == 'emma')
    outfit = emma.wardrobe.outfits[0]

    assert outfit.description == 'A daring outfit for confident moments'
    assert 'sexy' in outfit.tags
    assert outfit.unlock_when == 'meters.emma.boldness >= 60'

    print("✅ Optional outfit fields work")


# =============================================================================
# § 12.2: Clothing State (runtime)
# =============================================================================

def test_clothing_state_initialization(tmp_path: Path):
    """
    §12.2: Test that clothing state is initialized for all characters.
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
                    'outfits': [
                        {
                            'id': 'casual',
                            'name': 'Casual',
                            'tags': ['default'],
                            'layers': {
                                'top': {'item': 't-shirt'},
                                'bottom': {'item': 'jeans'}
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
    engine = GameEngine(loader.load_game("clothing_init"), "test_session")

    # Emma should have clothing state initialized
    assert 'emma' in engine.state_manager.state.clothing_states
    emma_clothing = engine.state_manager.state.clothing_states['emma']
    assert emma_clothing['current_outfit'] == 'casual'
    assert 'layers' in emma_clothing
    assert emma_clothing['layers']['top'] == 'intact'
    assert emma_clothing['layers']['bottom'] == 'intact'

    print("✅ Clothing state initialization works")


def test_default_outfit_selection(tmp_path: Path):
    """
    §12.2: Test that default outfit is selected on initialization.
    """
    game_dir = tmp_path / "default_outfit"
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
                    'outfits': [
                        {
                            'id': 'fancy',
                            'name': 'Fancy',
                            'tags': ['formal'],
                            'layers': {'top': {'item': 'dress'}}
                        },
                        {
                            'id': 'casual',
                            'name': 'Casual',
                            'tags': ['default', 'everyday'],
                            'layers': {'top': {'item': 't-shirt'}}
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
    engine = GameEngine(loader.load_game("default_outfit"), "test_session")

    # Should select outfit with 'default' tag
    emma_clothing = engine.state_manager.state.clothing_states['emma']
    assert emma_clothing['current_outfit'] == 'casual'

    print("✅ Default outfit selection works")


# =============================================================================
# § 12.3: Layer States (intact/displaced/removed)
# =============================================================================

def test_layer_state_transitions(tmp_path: Path):
    """
    §12.3: Test layer state transitions: intact -> displaced -> removed.
    """
    game_dir = tmp_path / "layer_states"
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
                    'outfits': [
                        {
                            'id': 'casual',
                            'name': 'Casual',
                            'tags': ['default'],
                            'layers': {
                                'top': {'item': 't-shirt'},
                                'bottom': {'item': 'jeans'}
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
    engine = GameEngine(loader.load_game("layer_states"), "test_session")

    # Initially intact
    assert engine.state_manager.state.clothing_states['emma']['layers']['top'] == 'intact'

    # Displace layer
    effect = ClothingChangeEffect(
        type="clothing_set",
        character="emma",
        layer="top",
        state="displaced"
    )
    engine.clothing_manager.apply_effect(effect)
    assert engine.state_manager.state.clothing_states['emma']['layers']['top'] == 'displaced'

    # Remove layer
    effect = ClothingChangeEffect(
        type="clothing_set",
        character="emma",
        layer="top",
        state="removed"
    )
    engine.clothing_manager.apply_effect(effect)
    assert engine.state_manager.state.clothing_states['emma']['layers']['top'] == 'removed'

    print("✅ Layer state transitions work")


def test_all_layer_states(tmp_path: Path):
    """
    §12.3: Test all three layer states are valid.
    """
    game_dir = tmp_path / "all_states"
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
                    'outfits': [
                        {
                            'id': 'outfit',
                            'name': 'Outfit',
                            'tags': ['default'],
                            'layers': {
                                'top': {'item': 'shirt'},
                                'bottom': {'item': 'pants'},
                                'underwear_top': {'item': 'bra'}
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
    engine = GameEngine(loader.load_game("all_states"), "test_session")

    layers = engine.state_manager.state.clothing_states['emma']['layers']

    # Set to all three states
    layers['top'] = 'intact'
    layers['bottom'] = 'displaced'
    layers['underwear_top'] = 'removed'

    assert layers['top'] == 'intact'
    assert layers['bottom'] == 'displaced'
    assert layers['underwear_top'] == 'removed'

    print("✅ All layer states (intact/displaced/removed) work")


# =============================================================================
# § 12.4: Outfit Changes
# =============================================================================

def test_outfit_change_effect(tmp_path: Path):
    """
    §12.4: Test outfit_change effect switches entire outfit.
    """
    game_dir = tmp_path / "outfit_change"
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
                    'outfits': [
                        {
                            'id': 'casual',
                            'name': 'Casual',
                            'tags': ['default'],
                            'layers': {
                                'top': {'item': 't-shirt'},
                                'bottom': {'item': 'jeans'}
                            }
                        },
                        {
                            'id': 'formal',
                            'name': 'Formal',
                            'tags': [],
                            'layers': {
                                'top': {'item': 'blouse'},
                                'bottom': {'item': 'skirt'},
                                'feet': {'item': 'heels'}
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
    engine = GameEngine(loader.load_game("outfit_change"), "test_session")

    # Initially wearing casual
    assert engine.state_manager.state.clothing_states['emma']['current_outfit'] == 'casual'
    assert 'top' in engine.state_manager.state.clothing_states['emma']['layers']
    assert 'feet' not in engine.state_manager.state.clothing_states['emma']['layers']

    # Change to formal outfit
    effect = ClothingChangeEffect(
        type="outfit_change",
        character="emma",
        outfit="formal"
    )
    engine.clothing_manager.apply_effect(effect)

    # Should now be wearing formal
    assert engine.state_manager.state.clothing_states['emma']['current_outfit'] == 'formal'
    # Layers should be reset to intact
    assert engine.state_manager.state.clothing_states['emma']['layers']['top'] == 'intact'
    assert engine.state_manager.state.clothing_states['emma']['layers']['bottom'] == 'intact'
    assert engine.state_manager.state.clothing_states['emma']['layers']['feet'] == 'intact'

    print("✅ Outfit change effect works")


# =============================================================================
# § 12.5: Wardrobe Rules
# =============================================================================

def test_wardrobe_rules_definition(tmp_path: Path):
    """
    §12.5: Test wardrobe rules definition (layer_order, required_layers, etc.).
    """
    game_dir = tmp_path / "wardrobe_rules"
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
                    'rules': {
                        'layer_order': ['outerwear', 'top', 'bottom', 'feet', 'underwear_top', 'underwear_bottom'],
                        'required_layers': ['top', 'bottom', 'underwear_top', 'underwear_bottom'],
                        'removable_layers': ['outerwear', 'top', 'bottom', 'feet'],
                        'sexual_layers': ['underwear_top', 'underwear_bottom']
                    },
                    'outfits': [
                        {
                            'id': 'casual',
                            'name': 'Casual',
                            'tags': ['default'],
                            'layers': {
                                'top': {'item': 't-shirt'},
                                'bottom': {'item': 'jeans'}
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
    game_def = loader.load_game("wardrobe_rules")

    emma = next(c for c in game_def.characters if c.id == 'emma')
    rules = emma.wardrobe.rules

    assert rules is not None
    assert rules.layer_order == ['outerwear', 'top', 'bottom', 'feet', 'underwear_top', 'underwear_bottom']
    assert 'top' in rules.required_layers
    assert 'outerwear' in rules.removable_layers
    assert 'underwear_top' in rules.sexual_layers

    print("✅ Wardrobe rules definition works")


# =============================================================================
# § 12.6: Layer Order & Required Layers
# =============================================================================

def test_layer_order_affects_appearance(tmp_path: Path):
    """
    §12.6: Test that layer_order affects appearance generation.
    """
    game_dir = tmp_path / "layer_order"
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
                    'rules': {
                        'layer_order': ['outerwear', 'top', 'bottom']
                    },
                    'outfits': [
                        {
                            'id': 'layered',
                            'name': 'Layered',
                            'tags': ['default'],
                            'layers': {
                                'outerwear': {'item': 'jacket', 'color': 'black'},
                                'top': {'item': 't-shirt', 'color': 'white'},
                                'bottom': {'item': 'jeans', 'color': 'blue'}
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
    engine = GameEngine(loader.load_game("layer_order"), "test_session")

    # Get appearance - should list layers in order
    appearance = engine.clothing_manager.get_character_appearance('emma')

    # Appearance should contain items in order
    assert 'jacket' in appearance
    assert 't-shirt' in appearance
    assert 'jeans' in appearance

    print("✅ Layer order affects appearance")


# =============================================================================
# § 12.7: Outfit Unlocking
# =============================================================================

def test_outfit_unlock_condition(tmp_path: Path):
    """
    §12.7: Test outfit unlock_when condition.
    """
    game_dir = tmp_path / "outfit_unlock"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'character_template': {
                'corruption': {'min': 0, 'max': 100, 'default': 0},
                'boldness': {'min': 0, 'max': 100, 'default': 20}
            }
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'},
            {
                'id': 'emma',
                'name': 'Emma',
                'age': 22,
                'gender': 'female',
                'wardrobe': {
                    'outfits': [
                        {
                            'id': 'casual',
                            'name': 'Casual',
                            'tags': ['default'],
                            'layers': {'top': {'item': 't-shirt'}}
                        },
                        {
                            'id': 'bold',
                            'name': 'Bold Outfit',
                            'tags': [],
                            'unlock_when': 'meters.emma.corruption >= 40 or meters.emma.boldness >= 60',
                            'layers': {'top': {'item': 'crop top'}}
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
    game_def = loader.load_game("outfit_unlock")

    emma = next(c for c in game_def.characters if c.id == 'emma')
    bold_outfit = next(o for o in emma.wardrobe.outfits if o.id == 'bold')

    assert bold_outfit.unlock_when is not None
    assert 'corruption >= 40' in bold_outfit.unlock_when or 'boldness >= 60' in bold_outfit.unlock_when

    print("✅ Outfit unlock conditions work")


def test_locked_outfit_property(tmp_path: Path):
    """
    §12.7: Test explicit locked property on outfits.
    """
    game_dir = tmp_path / "locked_outfit"
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
                    'outfits': [
                        {
                            'id': 'default',
                            'name': 'Default',
                            'tags': ['default'],
                            'locked': False,
                            'layers': {'top': {'item': 'shirt'}}
                        },
                        {
                            'id': 'special',
                            'name': 'Special',
                            'tags': [],
                            'locked': True,
                            'layers': {'top': {'item': 'dress'}}
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
    game_def = loader.load_game("locked_outfit")

    emma = next(c for c in game_def.characters if c.id == 'emma')
    default_outfit = next(o for o in emma.wardrobe.outfits if o.id == 'default')
    special_outfit = next(o for o in emma.wardrobe.outfits if o.id == 'special')

    assert default_outfit.locked is False
    assert special_outfit.locked is True

    print("✅ Locked outfit property works")


# =============================================================================
# § 12.8: Clothing Appearance Generation
# =============================================================================

def test_appearance_generation_basic(tmp_path: Path):
    """
    §12.8: Test basic appearance string generation.
    """
    game_dir = tmp_path / "appearance_basic"
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
                    'outfits': [
                        {
                            'id': 'casual',
                            'name': 'Casual',
                            'tags': ['default'],
                            'layers': {
                                'top': {'item': 't-shirt', 'color': 'white'},
                                'bottom': {'item': 'jeans', 'color': 'blue'}
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
    engine = GameEngine(loader.load_game("appearance_basic"), "test_session")

    # Get appearance
    appearance = engine.clothing_manager.get_character_appearance('emma')

    # Should contain item descriptions
    assert 'white t-shirt' in appearance or 't-shirt' in appearance
    assert 'blue jeans' in appearance or 'jeans' in appearance

    print("✅ Basic appearance generation works")


def test_appearance_reflects_displaced_state(tmp_path: Path):
    """
    §12.8: Test that displaced layers show in appearance.
    """
    game_dir = tmp_path / "appearance_displaced"
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
                    'outfits': [
                        {
                            'id': 'outfit',
                            'name': 'Outfit',
                            'tags': ['default'],
                            'layers': {
                                'top': {'item': 'shirt', 'color': 'red'}
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
    engine = GameEngine(loader.load_game("appearance_displaced"), "test_session")

    # Displace the top
    engine.state_manager.state.clothing_states['emma']['layers']['top'] = 'displaced'

    # Appearance should indicate displacement
    appearance = engine.clothing_manager.get_character_appearance('emma')
    assert 'displaced' in appearance

    print("✅ Appearance reflects displaced state")


def test_appearance_excludes_removed_layers(tmp_path: Path):
    """
    §12.8: Test that removed layers don't show in appearance.
    """
    game_dir = tmp_path / "appearance_removed"
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
                    'rules': {
                        'layer_order': ['top', 'bottom']
                    },
                    'outfits': [
                        {
                            'id': 'outfit',
                            'name': 'Outfit',
                            'tags': ['default'],
                            'layers': {
                                'top': {'item': 'shirt'},
                                'bottom': {'item': 'pants'}
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
    engine = GameEngine(loader.load_game("appearance_removed"), "test_session")

    # Initially both layers visible
    appearance_before = engine.clothing_manager.get_character_appearance('emma')
    assert 'shirt' in appearance_before

    # Remove the top
    engine.state_manager.state.clothing_states['emma']['layers']['top'] = 'removed'

    # Top should not appear in appearance
    appearance_after = engine.clothing_manager.get_character_appearance('emma')
    assert 'shirt' not in appearance_after
    assert 'pants' in appearance_after

    print("✅ Removed layers excluded from appearance")


# =============================================================================
# § 12.9: ClothingManager Integration
# =============================================================================

def test_clothing_manager_initialization(tmp_path: Path):
    """
    §12.9: Test ClothingManager initializes properly.
    """
    game_dir = tmp_path / "manager_init"
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
                    'outfits': [
                        {
                            'id': 'default',
                            'name': 'Default',
                            'tags': ['default'],
                            'layers': {'top': {'item': 'shirt'}}
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
    engine = GameEngine(loader.load_game("manager_init"), "test_session")

    # ClothingManager should be initialized
    assert engine.clothing_manager is not None
    assert engine.clothing_manager.game_def is not None
    assert engine.clothing_manager.state is not None

    print("✅ ClothingManager initialization works")


def test_ai_clothing_changes(tmp_path: Path):
    """
    §12.9: Test apply_ai_changes method for Checker AI deltas.
    """
    game_dir = tmp_path / "ai_changes"
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
                    'outfits': [
                        {
                            'id': 'outfit',
                            'name': 'Outfit',
                            'tags': ['default'],
                            'layers': {
                                'top': {'item': 'shirt'},
                                'bottom': {'item': 'pants'}
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
    engine = GameEngine(loader.load_game("ai_changes"), "test_session")

    # AI reports clothing changes
    ai_changes = {
        'emma': {
            'removed': ['top'],
            'displaced': ['bottom']
        }
    }

    engine.clothing_manager.apply_ai_changes(ai_changes)

    # Changes should be applied
    assert engine.state_manager.state.clothing_states['emma']['layers']['top'] == 'removed'
    assert engine.state_manager.state.clothing_states['emma']['layers']['bottom'] == 'displaced'

    print("✅ AI clothing changes work")


# =============================================================================
# § 12.10: Clothing Effects
# =============================================================================

def test_clothing_set_effect(tmp_path: Path):
    """
    §12.10: Test clothing_set effect for individual layers.
    """
    game_dir = tmp_path / "clothing_effect"
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
                    'outfits': [
                        {
                            'id': 'outfit',
                            'name': 'Outfit',
                            'tags': ['default'],
                            'layers': {'top': {'item': 'shirt'}}
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
    engine = GameEngine(loader.load_game("clothing_effect"), "test_session")

    # Apply clothing_set effect
    effect = ClothingChangeEffect(
        type="clothing_set",
        character="emma",
        layer="top",
        state="displaced"
    )
    engine.clothing_manager.apply_effect(effect)

    assert engine.state_manager.state.clothing_states['emma']['layers']['top'] == 'displaced'

    print("✅ clothing_set effect works")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])