"""
Tests for §10 Modifiers - PlotPlay v3 Spec

Modifiers are temporary state overlays that affect appearance/behavior:
- Named states like aroused, drunk, injured, tired
- Auto-activate from conditions or applied via effects
- Support duration, stacking, and exclusions
- Influence gates, dialogue, and presentation
- Can clamp meters and trigger entry/exit effects

§10.1: Modifier Definition & Structure
§10.2: System-Level Controls (stacking, exclusions)
§10.3: Auto-Activation via 'when' Conditions
§10.4: Manual Application/Removal via Effects
§10.5: Duration & Expiration
§10.6: Appearance & Behavior Overlays
§10.7: Safety (disallow_gates)
§10.8: Meter Clamping
§10.9: Entry/Exit Effects
§10.10: Exclusion Groups
"""

import pytest
import yaml
from pathlib import Path

from app.core.game_loader import GameLoader
from app.core.state_manager import StateManager
from app.core.game_engine import GameEngine
from app.models.effects import ApplyModifierEffect, RemoveModifierEffect, MeterChangeEffect


# =============================================================================
# § 10.1: Modifier Definition & Structure
# =============================================================================

def test_modifier_basic_definition(tmp_path: Path):
    """
    §10.1: Test basic modifier definition with id, group, and description.
    """
    game_dir = tmp_path / "modifier_basic"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'modifier_system': {
            'library': {
                'aroused': {
                    'id': 'aroused',
                    'group': 'emotional',
                    'description': 'Feeling desire and attraction'
                },
                'tired': {
                    'id': 'tired',
                    'group': 'physical',
                    'description': 'Low energy state'
                }
            }
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("modifier_basic")
    engine = GameEngine(game_def, "test_session")

    # Modifiers should be loaded into library
    assert 'aroused' in engine.modifier_manager.library
    assert 'tired' in engine.modifier_manager.library

    aroused = engine.modifier_manager.library['aroused']
    assert aroused.id == 'aroused'
    assert aroused.group == 'emotional'
    assert aroused.description == 'Feeling desire and attraction'

    print("✅ Basic modifier definition works")


def test_modifier_optional_fields(tmp_path: Path):
    """
    §10.1: Test optional modifier fields (tags, duration_default_min).
    """
    game_dir = tmp_path / "modifier_optional"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'modifier_system': {
            'library': {
                'drunk': {
                    'id': 'drunk',
                    'group': 'intoxication',
                    'duration_default_min': 120,
                    'description': 'Intoxicated state'
                }
            }
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("modifier_optional")
    engine = GameEngine(game_def, "test_session")

    drunk = engine.modifier_manager.library['drunk']
    assert drunk.duration_default_min == 120

    print("✅ Optional modifier fields work")


# =============================================================================
# § 10.2: System-Level Controls
# =============================================================================

def test_modifier_system_stacking_config(tmp_path: Path):
    """
    §10.2: Test modifier system stacking configuration.
    """
    game_dir = tmp_path / "stacking_config"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'modifier_system': {
            'library': {
                'aroused': {'id': 'aroused', 'group': 'emotional'}
            },
            'stacking': {
                'default': 'highest',
                'per_group': {
                    'emotional': 'additive',
                    'intoxication': 'highest'
                }
            }
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("stacking_config")

    # Check stacking configuration
    assert game_def.modifier_system.stacking.default == 'highest'
    assert game_def.modifier_system.stacking.per_group['emotional'] == 'additive'
    assert game_def.modifier_system.stacking.per_group['intoxication'] == 'highest'

    print("✅ Modifier stacking configuration works")


def test_modifier_system_exclusions(tmp_path: Path):
    """
    §10.2: Test modifier system exclusion rules.
    """
    game_dir = tmp_path / "exclusions"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'modifier_system': {
            'library': {
                'drunk': {'id': 'drunk', 'group': 'intoxication'},
                'high': {'id': 'high', 'group': 'intoxication'}
            },
            'exclusions': [
                {'group': 'intoxication', 'exclusive': True}
            ]
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("exclusions")

    # Check exclusions
    assert len(game_def.modifier_system.exclusions) == 1
    assert game_def.modifier_system.exclusions[0].group == 'intoxication'
    assert game_def.modifier_system.exclusions[0].exclusive is True

    print("✅ Modifier exclusion rules work")


# =============================================================================
# § 10.3: Auto-Activation via 'when' Conditions
# =============================================================================

def test_modifier_auto_activation_when_condition(tmp_path: Path):
    """
    §10.3: Test that modifiers auto-activate when their 'when' condition is true.
    """
    game_dir = tmp_path / "auto_activate"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'character_template': {
                'arousal': {'min': 0, 'max': 100, 'default': 0}
            }
        },
        'modifier_system': {
            'library': {
                'aroused': {
                    'id': 'aroused',
                    'group': 'emotional',
                    'when': 'meters.{character}.arousal >= 50'
                }
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
    engine = GameEngine(loader.load_game("auto_activate"), "test_session")

    # Initially, arousal is 0, so modifier should not be active
    engine.modifier_manager.update_modifiers_for_turn(engine.state_manager.state)
    assert 'aroused' not in [m['id'] for m in engine.state_manager.state.modifiers.get('emma', [])]

    # Raise arousal to 60
    engine.state_manager.state.meters['emma']['arousal'] = 60

    # Update modifiers - should auto-activate
    engine.modifier_manager.update_modifiers_for_turn(engine.state_manager.state)
    assert 'aroused' in [m['id'] for m in engine.state_manager.state.modifiers.get('emma', [])]

    print("✅ Auto-activation via 'when' condition works")


def test_modifier_auto_deactivation_when_false(tmp_path: Path):
    """
    §10.3: Test that auto-activated modifiers deactivate when condition becomes false.
    """
    game_dir = tmp_path / "auto_deactivate"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'energy': {'min': 0, 'max': 100, 'default': 50}
            }
        },
        'modifier_system': {
            'library': {
                'exhausted': {
                    'id': 'exhausted',
                    'group': 'physical',
                    'when': 'meters.{character}.energy < 20'
                }
            }
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    engine = GameEngine(loader.load_game("auto_deactivate"), "test_session")

    # Set energy to 10 (below threshold)
    engine.state_manager.state.meters['player']['energy'] = 10
    engine.modifier_manager.update_modifiers_for_turn(engine.state_manager.state)

    # Exhausted should be active
    assert 'exhausted' in [m['id'] for m in engine.state_manager.state.modifiers.get('player', [])]

    # Restore energy to 50 (above threshold)
    engine.state_manager.state.meters['player']['energy'] = 50
    engine.modifier_manager.update_modifiers_for_turn(engine.state_manager.state)

    # Exhausted should be removed
    assert 'exhausted' not in [m['id'] for m in engine.state_manager.state.modifiers.get('player', [])]

    print("✅ Auto-deactivation when condition becomes false works")


# =============================================================================
# § 10.4: Manual Application/Removal via Effects
# =============================================================================

def test_apply_modifier_effect(tmp_path: Path):
    """
    §10.4: Test manually applying a modifier via ApplyModifierEffect.
    """
    game_dir = tmp_path / "apply_effect"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'modifier_system': {
            'library': {
                'drunk': {
                    'id': 'drunk',
                    'group': 'intoxication',
                    'duration_default_min': 120
                }
            }
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    engine = GameEngine(loader.load_game("apply_effect"), "test_session")

    # Initially no modifiers
    assert 'drunk' not in [m['id'] for m in engine.state_manager.state.modifiers.get('player', [])]

    # Apply drunk modifier
    effect = ApplyModifierEffect(
        type="apply_modifier",
        character="player",
        modifier_id="drunk"
    )
    engine.modifier_manager.apply_effect(effect, engine.state_manager.state)

    # Drunk should now be active
    assert 'drunk' in [m['id'] for m in engine.state_manager.state.modifiers.get('player', [])]

    print("✅ ApplyModifierEffect works")


def test_apply_modifier_with_duration_override(tmp_path: Path):
    """
    §10.4: Test applying a modifier with custom duration override.
    """
    game_dir = tmp_path / "duration_override"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'modifier_system': {
            'library': {
                'drunk': {
                    'id': 'drunk',
                    'group': 'intoxication',
                    'duration_default_min': 120
                }
            }
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    engine = GameEngine(loader.load_game("duration_override"), "test_session")

    # Apply with custom duration
    effect = ApplyModifierEffect(
        type="apply_modifier",
        character="player",
        modifier_id="drunk",
        duration_min=60  # Override default 120
    )
    engine.modifier_manager.apply_effect(effect, engine.state_manager.state)

    # Check duration was set correctly
    drunk_mod = next(m for m in engine.state_manager.state.modifiers['player'] if m['id'] == 'drunk')
    assert drunk_mod['duration'] == 60

    print("✅ Duration override works")


def test_remove_modifier_effect(tmp_path: Path):
    """
    §10.4: Test manually removing a modifier via RemoveModifierEffect.
    """
    game_dir = tmp_path / "remove_effect"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'modifier_system': {
            'library': {
                'drunk': {
                    'id': 'drunk',
                    'group': 'intoxication'
                }
            }
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    engine = GameEngine(loader.load_game("remove_effect"), "test_session")

    # Apply modifier first
    apply_effect = ApplyModifierEffect(
        type="apply_modifier",
        character="player",
        modifier_id="drunk"
    )
    engine.modifier_manager.apply_effect(apply_effect, engine.state_manager.state)
    assert 'drunk' in [m['id'] for m in engine.state_manager.state.modifiers.get('player', [])]

    # Remove modifier
    remove_effect = RemoveModifierEffect(
        type="remove_modifier",
        character="player",
        modifier_id="drunk"
    )
    engine.modifier_manager.apply_effect(remove_effect, engine.state_manager.state)

    # Drunk should be removed
    assert 'drunk' not in [m['id'] for m in engine.state_manager.state.modifiers.get('player', [])]

    print("✅ RemoveModifierEffect works")


# =============================================================================
# § 10.5: Duration & Expiration
# =============================================================================

def test_modifier_duration_ticks_down(tmp_path: Path):
    """
    §10.5: Test that modifier duration ticks down over time.
    """
    game_dir = tmp_path / "duration_tick"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'modifier_system': {
            'library': {
                'drunk': {
                    'id': 'drunk',
                    'group': 'intoxication',
                    'duration_default_min': 120
                }
            }
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    engine = GameEngine(loader.load_game("duration_tick"), "test_session")

    # Apply modifier with 60 minute duration
    effect = ApplyModifierEffect(
        type="apply_modifier",
        character="player",
        modifier_id="drunk",
        duration_min=60
    )
    engine.modifier_manager.apply_effect(effect, engine.state_manager.state)

    # Check initial duration
    drunk_mod = next(m for m in engine.state_manager.state.modifiers['player'] if m['id'] == 'drunk')
    assert drunk_mod['duration'] == 60

    # Tick 30 minutes
    engine.modifier_manager.tick_durations(engine.state_manager.state, 30)
    drunk_mod = next(m for m in engine.state_manager.state.modifiers['player'] if m['id'] == 'drunk')
    assert drunk_mod['duration'] == 30

    print("✅ Duration ticks down correctly")


def test_modifier_expires_after_duration(tmp_path: Path):
    """
    §10.5: Test that modifiers are removed when duration reaches 0.
    """
    game_dir = tmp_path / "duration_expire"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'modifier_system': {
            'library': {
                'drunk': {
                    'id': 'drunk',
                    'group': 'intoxication',
                    'duration_default_min': 60
                }
            }
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    engine = GameEngine(loader.load_game("duration_expire"), "test_session")

    # Apply modifier
    effect = ApplyModifierEffect(
        type="apply_modifier",
        character="player",
        modifier_id="drunk",
        duration_min=30
    )
    engine.modifier_manager.apply_effect(effect, engine.state_manager.state)
    assert 'drunk' in [m['id'] for m in engine.state_manager.state.modifiers.get('player', [])]

    # Tick past expiration
    engine.modifier_manager.tick_durations(engine.state_manager.state, 40)

    # Drunk should be removed
    assert 'drunk' not in [m['id'] for m in engine.state_manager.state.modifiers.get('player', [])]

    print("✅ Modifier expiration works")


# =============================================================================
# § 10.6: Appearance & Behavior Overlays
# =============================================================================

def test_modifier_appearance_overlay(tmp_path: Path):
    """
    §10.6: Test that modifiers can define appearance overlays.
    """
    game_dir = tmp_path / "appearance"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'modifier_system': {
            'library': {
                'aroused': {
                    'id': 'aroused',
                    'group': 'emotional',
                    'appearance': {
                        'cheeks': 'flushed',
                        'eyes': 'dilated'
                    }
                }
            }
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("appearance")

    # Check appearance overlay
    aroused = game_def.modifier_system.library['aroused']
    assert aroused.appearance is not None
    assert aroused.appearance.cheeks == 'flushed'
    assert aroused.appearance.eyes == 'dilated'

    print("✅ Appearance overlay definition works")


def test_modifier_behavior_overlay(tmp_path: Path):
    """
    §10.6: Test that modifiers can define behavior overlays.
    """
    game_dir = tmp_path / "behavior"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'modifier_system': {
            'library': {
                'drunk': {
                    'id': 'drunk',
                    'group': 'intoxication',
                    'behavior': {
                        'dialogue_style': 'slurred',
                        'inhibition': -3,
                        'coordination': -2
                    }
                }
            }
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("behavior")

    # Check behavior overlay
    drunk = game_def.modifier_system.library['drunk']
    assert drunk.behavior is not None
    assert drunk.behavior.dialogue_style == 'slurred'
    assert drunk.behavior.inhibition == -3
    assert drunk.behavior.coordination == -2

    print("✅ Behavior overlay definition works")


# =============================================================================
# § 10.7: Safety (disallow_gates)
# =============================================================================

def test_modifier_safety_disallow_gates(tmp_path: Path):
    """
    §10.7: Test that modifiers can disallow specific gates.
    """
    game_dir = tmp_path / "safety"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'modifier_system': {
            'library': {
                'drunk': {
                    'id': 'drunk',
                    'group': 'intoxication',
                    'safety': {
                        'disallow_gates': ['accept_sex']
                    },
                    'description': 'Cannot consent while drunk'
                }
            }
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("safety")

    # Check safety rules
    drunk = game_def.modifier_system.library['drunk']
    assert drunk.safety is not None
    assert 'accept_sex' in drunk.safety.disallow_gates

    print("✅ Safety disallow_gates definition works")


# =============================================================================
# § 10.8: Meter Clamping
# =============================================================================

def test_modifier_meter_clamping(tmp_path: Path):
    """
    §10.8: Test that modifiers can clamp meter values temporarily.
    """
    game_dir = tmp_path / "clamp_meters"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'character_template': {
                'arousal': {'min': 0, 'max': 100, 'default': 50}
            }
        },
        'modifier_system': {
            'library': {
                'exhausted': {
                    'id': 'exhausted',
                    'group': 'physical',
                    'clamp_meters': {
                        'arousal': {'max': 40}
                    }
                }
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
    engine = GameEngine(loader.load_game("clamp_meters"), "test_session")

    # Set arousal to 70
    engine.state_manager.state.meters['emma']['arousal'] = 70

    # Apply exhausted modifier (clamps arousal max to 40)
    effect = ApplyModifierEffect(
        type="apply_modifier",
        character="emma",
        modifier_id="exhausted"
    )
    engine.modifier_manager.apply_effect(effect, engine.state_manager.state)

    # Try to increase arousal to 80 - should be clamped to 40
    engine._apply_meter_change(MeterChangeEffect(
        type="meter_change",
        target="emma",
        meter="arousal",
        op="set",
        value=80
    ))

    # Should be clamped to 40
    assert engine.state_manager.state.meters['emma']['arousal'] == 40

    print("✅ Meter clamping works")


# =============================================================================
# § 10.9: Entry/Exit Effects
# =============================================================================

def test_modifier_entry_effects(tmp_path: Path):
    """
    §10.9: Test that entry_effects trigger when modifier is applied.
    """
    game_dir = tmp_path / "entry_effects"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'energy': {'min': 0, 'max': 100, 'default': 100}
            }
        },
        'modifier_system': {
            'library': {
                'injured': {
                    'id': 'injured',
                    'group': 'status',
                    'entry_effects': [
                        {
                            'type': 'meter_change',
                            'target': 'player',
                            'meter': 'energy',
                            'op': 'subtract',
                            'value': 20
                        }
                    ]
                }
            }
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    engine = GameEngine(loader.load_game("entry_effects"), "test_session")

    initial_energy = engine.state_manager.state.meters['player']['energy']
    assert initial_energy == 100

    # Apply injured modifier - entry effect should trigger
    effect = ApplyModifierEffect(
        type="apply_modifier",
        character="player",
        modifier_id="injured"
    )
    engine.modifier_manager.apply_effect(effect, engine.state_manager.state)

    # Energy should be reduced by entry effect
    assert engine.state_manager.state.meters['player']['energy'] == 80

    print("✅ Entry effects work")


def test_modifier_exit_effects(tmp_path: Path):
    """
    §10.9: Test that exit_effects trigger when modifier is removed.
    """
    game_dir = tmp_path / "exit_effects"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'flags': {
            'injury_healed': {'type': 'bool', 'default': False}
        },
        'modifier_system': {
            'library': {
                'injured': {
                    'id': 'injured',
                    'group': 'status',
                    'exit_effects': [
                        {
                            'type': 'flag_set',
                            'key': 'injury_healed',
                            'value': True
                        }
                    ]
                }
            }
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    engine = GameEngine(loader.load_game("exit_effects"), "test_session")

    assert engine.state_manager.state.flags['injury_healed'] is False

    # Apply and then remove injured modifier
    apply_effect = ApplyModifierEffect(
        type="apply_modifier",
        character="player",
        modifier_id="injured"
    )
    engine.modifier_manager.apply_effect(apply_effect, engine.state_manager.state)

    remove_effect = RemoveModifierEffect(
        type="remove_modifier",
        character="player",
        modifier_id="injured"
    )
    engine.modifier_manager.apply_effect(remove_effect, engine.state_manager.state)

    # Exit effect should have set flag
    assert engine.state_manager.state.flags['injury_healed'] is True

    print("✅ Exit effects work")


# =============================================================================
# § 10.10: Exclusion Groups
# =============================================================================

def test_exclusive_group_prevents_multiple_modifiers(tmp_path: Path):
    """
    §10.10: Test that exclusive groups prevent multiple modifiers in same group.
    """
    game_dir = tmp_path / "exclusive_group"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'modifier_system': {
            'library': {
                'drunk': {'id': 'drunk', 'group': 'intoxication'},
                'high': {'id': 'high', 'group': 'intoxication'}
            },
            'exclusions': [
                {'group': 'intoxication', 'exclusive': True}
            ]
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    engine = GameEngine(loader.load_game("exclusive_group"), "test_session")

    # Apply drunk modifier
    apply_drunk = ApplyModifierEffect(
        type="apply_modifier",
        character="player",
        modifier_id="drunk"
    )
    engine.modifier_manager.apply_effect(apply_drunk, engine.state_manager.state)
    assert 'drunk' in [m['id'] for m in engine.state_manager.state.modifiers.get('player', [])]

    # Apply high modifier - should remove drunk (exclusive group)
    apply_high = ApplyModifierEffect(
        type="apply_modifier",
        character="player",
        modifier_id="high"
    )
    engine.modifier_manager.apply_effect(apply_high, engine.state_manager.state)

    # Only high should be active
    active_ids = [m['id'] for m in engine.state_manager.state.modifiers.get('player', [])]
    assert 'high' in active_ids
    assert 'drunk' not in active_ids

    print("✅ Exclusive groups work")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])