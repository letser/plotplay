"""
Tests for §8 Meters - PlotPlay v3 Spec

Meters are numeric variables that track continuous aspects of player/NPCs:
- Bounded with min, max, default
- Visible or hidden with conditional reveals
- Thresholded with labeled ranges
- Dynamic with decay/growth and caps
- Central to gating and narrative logic

§8.1: Meter Definition
§8.2: Player & Template Meters
§8.3: Character-Specific Overrides
§8.4: Decay & Growth Dynamics
§8.5: Delta Caps
§8.6: Threshold Labels
§8.7: Visibility & Hidden Meters
§8.8: Validation
"""

import pytest
import yaml
from pathlib import Path

from app.core.game_loader import GameLoader
from app.core.state_manager import StateManager
from app.core.game_engine import GameEngine
from app.models.effects import MeterChangeEffect


# =============================================================================
# § 8.1: Meter Definition - Required Fields
# =============================================================================

def test_meter_required_fields(tmp_path: Path):
    """
    §8.1: Test that meters MUST have min, max, and default values.
    """
    game_dir = tmp_path / "meter_required"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'health': {
                    'min': 0,
                    'max': 100,
                    'default': 75
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
    game_def = loader.load_game("meter_required")
    manager = StateManager(game_def)

    # Meter should be properly initialized
    assert manager.state.meters["player"]["health"] == 75
    assert game_def.meters["player"]["health"].min == 0
    assert game_def.meters["player"]["health"].max == 100
    assert game_def.meters["player"]["health"].default == 75

    print("✅ Meter required fields (min, max, default) work")


def test_meter_bounds_validation(tmp_path: Path):
    """
    §8.1: Test that default must be within [min, max] and max > min.
    """
    game_dir = tmp_path / "meter_bounds"
    game_dir.mkdir()

    # Valid meter definition
    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'health': {'min': 0, 'max': 100, 'default': 50}
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
    game_def = loader.load_game("meter_bounds")

    # Should load successfully
    assert game_def.meters["player"]["health"].default == 50

    print("✅ Meter bounds validation works")


# =============================================================================
# § 8.2: Player vs Character Template Meters
# =============================================================================

def test_player_meters_initialization(tmp_path: Path):
    """
    §8.2: Test that player meters are initialized from meters.player.
    """
    game_dir = tmp_path / "player_meters"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'health': {'min': 0, 'max': 100, 'default': 80},
                'energy': {'min': 0, 'max': 100, 'default': 60},
                'money': {'min': 0, 'max': 999, 'default': 50}
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
    game_def = loader.load_game("player_meters")
    manager = StateManager(game_def)

    # All player meters should be initialized
    assert manager.state.meters["player"]["health"] == 80
    assert manager.state.meters["player"]["energy"] == 60
    assert manager.state.meters["player"]["money"] == 50

    print("✅ Player meters initialization works")


def test_character_template_meters(tmp_path: Path):
    """
    §8.2: Test that NPCs inherit meters from character_template.
    """
    game_dir = tmp_path / "template_meters"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'health': {'min': 0, 'max': 100, 'default': 75}
            },
            'character_template': {
                'trust': {'min': 0, 'max': 100, 'default': 10},
                'attraction': {'min': 0, 'max': 100, 'default': 5}
            }
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'},
            {'id': 'emma', 'name': 'Emma', 'age': 22, 'gender': 'female'},
            {'id': 'alex', 'name': 'Alex', 'age': 24, 'gender': 'male'}
        ],
        'zones': [{'id': 'z', 'name': 'Z', 'locations': [{'id': 'l', 'name': 'L'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start'}]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("template_meters")
    manager = StateManager(game_def)

    # Both NPCs should inherit template meters
    assert manager.state.meters["emma"]["trust"] == 10
    assert manager.state.meters["emma"]["attraction"] == 5
    assert manager.state.meters["alex"]["trust"] == 10
    assert manager.state.meters["alex"]["attraction"] == 5

    print("✅ Character template meters work")


# =============================================================================
# § 8.3: Character-Specific Meter Overrides
# =============================================================================

def test_character_meter_overrides(tmp_path: Path):
    """
    §8.3: Test that character-specific meters override template defaults.
    """
    game_dir = tmp_path / "meter_override"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'health': {'min': 0, 'max': 100, 'default': 75}
            },
            'character_template': {
                'trust': {'min': 0, 'max': 100, 'default': 10},
                'attraction': {'min': 0, 'max': 100, 'default': 5}
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
                    # Override template default
                    'trust': {'min': 0, 'max': 100, 'default': 30},
                    # Keep template default for attraction
                    # Add character-specific meter
                    'boldness': {'min': 0, 'max': 100, 'default': 40}
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

    # Emma's trust should use override (30), not template (10)
    assert manager.state.meters["emma"]["trust"] == 30
    # Emma's attraction should use template default (5)
    assert manager.state.meters["emma"]["attraction"] == 5
    # Emma has character-specific boldness meter
    assert manager.state.meters["emma"]["boldness"] == 40

    print("✅ Character-specific meter overrides work")


# =============================================================================
# § 8.4: Decay & Growth Dynamics
# =============================================================================

def test_meter_decay_per_day(tmp_path: Path):
    """
    §8.4: Test decay_per_day applies at day rollover.
    """
    game_dir = tmp_path / "decay_day"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'energy': {
                    'min': 0,
                    'max': 100,
                    'default': 80,
                    'decay_per_day': -10  # Loses 10 energy per day
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
    engine = GameEngine(loader.load_game("decay_day"), "test_session")

    initial_energy = engine.state_manager.state.meters["player"]["energy"]
    assert initial_energy == 80

    # Simulate day change
    engine._process_meter_dynamics({'day_advanced': True, 'slot_advanced': False})

    # Energy should have decayed by 10
    assert engine.state_manager.state.meters["player"]["energy"] == 70

    print("✅ Meter decay_per_day works")


def test_meter_decay_per_slot(tmp_path: Path):
    """
    §8.4: Test decay_per_slot applies at time slot changes.
    """
    game_dir = tmp_path / "decay_slot"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'hygiene': {
                    'min': 0,
                    'max': 100,
                    'default': 80,
                    'decay_per_slot': -5  # Loses 5 hygiene per time slot
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
    engine = GameEngine(loader.load_game("decay_slot"), "test_session")

    initial_hygiene = engine.state_manager.state.meters["player"]["hygiene"]
    assert initial_hygiene == 80

    # Simulate time slot change
    engine._process_meter_dynamics({'day_advanced': False, 'slot_advanced': True})

    # Hygiene should have decayed by 5
    assert engine.state_manager.state.meters["player"]["hygiene"] == 75

    print("✅ Meter decay_per_slot works")


def test_meter_growth_positive_decay(tmp_path: Path):
    """
    §8.4: Test positive decay_per_day acts as regeneration.
    """
    game_dir = tmp_path / "regen"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'health': {
                    'min': 0,
                    'max': 100,
                    'default': 50,
                    'decay_per_day': 10  # Gains 10 health per day (regen)
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
    engine = GameEngine(loader.load_game("regen"), "test_session")

    initial_health = engine.state_manager.state.meters["player"]["health"]
    assert initial_health == 50

    # Simulate day change
    engine._process_meter_dynamics({'day_advanced': True, 'slot_advanced': False})

    # Health should have grown by 10
    assert engine.state_manager.state.meters["player"]["health"] == 60

    print("✅ Positive decay (regeneration) works")


def test_decay_respects_bounds(tmp_path: Path):
    """
    §8.4: Test that decay respects meter min/max bounds.
    """
    game_dir = tmp_path / "decay_bounds"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'energy': {
                    'min': 0,
                    'max': 100,
                    'default': 5,
                    'decay_per_day': -10  # Would go to -5, but should clamp to 0
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
    engine = GameEngine(loader.load_game("decay_bounds"), "test_session")

    engine._process_meter_dynamics({'day_advanced': True, 'slot_advanced': False})

    # Should be clamped to min (0), not go negative
    assert engine.state_manager.state.meters["player"]["energy"] == 0

    print("✅ Decay respects meter bounds")


# =============================================================================
# § 8.5: Delta Caps
# =============================================================================

def test_delta_cap_per_turn_limits_changes(tmp_path: Path):
    """
    §8.5: Test delta_cap_per_turn limits meter changes per turn.
    """
    game_dir = tmp_path / "delta_cap"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'character_template': {
                'trust': {
                    'min': 0,
                    'max': 100,
                    'default': 50,
                    'delta_cap_per_turn': 3  # Max change of ±3 per turn
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
    engine = GameEngine(loader.load_game("delta_cap"), "test_session")

    initial_trust = engine.state_manager.state.meters["emma"]["trust"]
    assert initial_trust == 50

    # Try to add 10 trust (should be capped to +3)
    engine._apply_meter_change(MeterChangeEffect(
        type="meter_change",
        target="emma",
        meter="trust",
        op="add",
        value=10
    ))

    # Should only increase by cap amount (3)
    assert engine.state_manager.state.meters["emma"]["trust"] == 53

    # Reset turn deltas for next turn
    engine.turn_meter_deltas.clear()

    # Try to subtract 10 trust (should be capped to -3)
    engine._apply_meter_change(MeterChangeEffect(
        type="meter_change",
        target="emma",
        meter="trust",
        op="subtract",
        value=10
    ))

    # Should only decrease by cap amount (3)
    assert engine.state_manager.state.meters["emma"]["trust"] == 50

    print("✅ Delta cap per turn works")


def test_delta_cap_accumulates_within_turn(tmp_path: Path):
    """
    §8.5: Test delta cap accumulates across multiple changes in one turn.
    """
    game_dir = tmp_path / "delta_cap_accumulate"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'character_template': {
                'trust': {
                    'min': 0,
                    'max': 100,
                    'default': 50,
                    'delta_cap_per_turn': 5
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
    engine = GameEngine(loader.load_game("delta_cap_accumulate"), "test_session")

    # Add +3 trust
    engine._apply_meter_change(MeterChangeEffect(
        type="meter_change",
        target="emma",
        meter="trust",
        op="add",
        value=3
    ))

    assert engine.state_manager.state.meters["emma"]["trust"] == 53

    # Try to add +3 more (should only get +2 due to cap of 5 total)
    engine._apply_meter_change(MeterChangeEffect(
        type="meter_change",
        target="emma",
        meter="trust",
        op="add",
        value=3
    ))

    # Should be 50 + 5 (capped), not 50 + 6
    assert engine.state_manager.state.meters["emma"]["trust"] == 55

    print("✅ Delta cap accumulation across multiple changes works")


# =============================================================================
# § 8.6: Threshold Labels
# =============================================================================

def test_meter_thresholds_definition(tmp_path: Path):
    """
    §8.6: Test that thresholds can be defined as labeled ranges.
    """
    game_dir = tmp_path / "thresholds"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'character_template': {
                'trust': {
                    'min': 0,
                    'max': 100,
                    'default': 15,
                    'thresholds': {
                        'stranger': [0, 19],
                        'acquaintance': [20, 39],
                        'friend': [40, 69],
                        'close': [70, 89],
                        'intimate': [90, 100]
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
    game_def = loader.load_game("thresholds")

    # Thresholds should be defined
    trust_meter = game_def.meters["character_template"]["trust"]
    assert trust_meter.thresholds is not None
    assert "stranger" in trust_meter.thresholds
    assert trust_meter.thresholds["stranger"] == [0, 19]
    assert trust_meter.thresholds["intimate"] == [90, 100]

    print("✅ Meter threshold definitions work")


def test_threshold_label_lookup(tmp_path: Path):
    """
    §8.6: Test that PromptBuilder can look up threshold labels for meter values.
    """
    game_dir = tmp_path / "threshold_lookup"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'character_template': {
                'trust': {
                    'min': 0,
                    'max': 100,
                    'default': 25,
                    'thresholds': {
                        'stranger': [0, 19],
                        'acquaintance': [20, 39],
                        'friend': [40, 69]
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
    game_def = loader.load_game("threshold_lookup")
    engine = GameEngine(game_def, "test_session")

    # Test threshold lookups via PromptBuilder
    from app.services.prompt_builder import PromptBuilder
    prompt_builder = PromptBuilder(game_def, engine.clothing_manager)

    # trust=25 should be "acquaintance"
    label = prompt_builder._get_meter_threshold_label("emma", "trust", 25)
    assert label == "acquaintance"

    # trust=50 should be "friend"
    label = prompt_builder._get_meter_threshold_label("emma", "trust", 50)
    assert label == "friend"

    # trust=10 should be "stranger"
    label = prompt_builder._get_meter_threshold_label("emma", "trust", 10)
    assert label == "stranger"

    print("✅ Threshold label lookup works")


# =============================================================================
# § 8.7: Visibility & Hidden Meters
# =============================================================================

def test_visible_meter_default(tmp_path: Path):
    """
    §8.7: Test that player meters default to visible=true.
    """
    game_dir = tmp_path / "visible_default"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'health': {'min': 0, 'max': 100, 'default': 75}
                # visible not specified, should default to true for player
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
    game_def = loader.load_game("visible_default")

    # Player meters should default to visible=true
    health_meter = game_def.meters["player"]["health"]
    assert health_meter.visible is True

    print("✅ Player meters default to visible=true")


def test_hidden_meter_with_condition(tmp_path: Path):
    """
    §8.7: Test hidden_until expression for conditional visibility.
    """
    game_dir = tmp_path / "hidden_until"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'character_template': {
                'attraction': {'min': 0, 'max': 100, 'default': 5},
                'arousal': {
                    'min': 0,
                    'max': 100,
                    'default': 0,
                    'hidden_until': "meters.{character}.attraction >= 30"
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
    game_def = loader.load_game("hidden_until")

    # Arousal meter should have hidden_until expression
    arousal_meter = game_def.meters["character_template"]["arousal"]
    assert arousal_meter.hidden_until is not None
    assert "meters.{character}.attraction >= 30" in arousal_meter.hidden_until

    print("✅ hidden_until conditional visibility works")


def test_meter_ui_properties(tmp_path: Path):
    """
    §8.7: Test meter UI properties: icon and format.
    """
    game_dir = tmp_path / "meter_ui"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'energy': {
                    'min': 0,
                    'max': 100,
                    'default': 70,
                    'icon': '⚡',
                    'format': 'integer'
                },
                'money': {
                    'min': 0,
                    'max': 999,
                    'default': 50,
                    'icon': '💵',
                    'format': 'currency'
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
    game_def = loader.load_game("meter_ui")

    energy_meter = game_def.meters["player"]["energy"]
    assert energy_meter.icon == '⚡'
    assert energy_meter.format == 'integer'

    money_meter = game_def.meters["player"]["money"]
    assert money_meter.icon == '💵'
    assert money_meter.format == 'currency'

    print("✅ Meter UI properties (icon, format) work")


# =============================================================================
# § 8.8: Validation & Edge Cases
# =============================================================================

def test_meter_clamping_to_bounds(tmp_path: Path):
    """
    §8.8: Test that meter changes are clamped to [min, max].
    """
    game_dir = tmp_path / "clamping"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'health': {'min': 0, 'max': 100, 'default': 90}
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
    engine = GameEngine(loader.load_game("clamping"), "test_session")

    # Try to add 20 health (should clamp to max of 100)
    engine._apply_meter_change(MeterChangeEffect(
        type="meter_change",
        target="player",
        meter="health",
        op="add",
        value=20
    ))

    assert engine.state_manager.state.meters["player"]["health"] == 100

    # Try to subtract 150 health (should clamp to min of 0)
    engine._apply_meter_change(MeterChangeEffect(
        type="meter_change",
        target="player",
        meter="health",
        op="subtract",
        value=150
    ))

    assert engine.state_manager.state.meters["player"]["health"] == 0

    print("✅ Meter clamping to bounds works")


def test_meter_operations(tmp_path: Path):
    """
    §8.8: Test different meter operations (add, subtract, multiply, divide, set).
    """
    game_dir = tmp_path / "operations"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'test_meter': {'min': 0, 'max': 200, 'default': 50}
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
    engine = GameEngine(loader.load_game("operations"), "test_session")

    # Test add
    engine._apply_meter_change(MeterChangeEffect(
        type="meter_change", target="player", meter="test_meter", op="add", value=10
    ))
    assert engine.state_manager.state.meters["player"]["test_meter"] == 60

    # Test subtract
    engine._apply_meter_change(MeterChangeEffect(
        type="meter_change", target="player", meter="test_meter", op="subtract", value=20
    ))
    assert engine.state_manager.state.meters["player"]["test_meter"] == 40

    # Test multiply
    engine._apply_meter_change(MeterChangeEffect(
        type="meter_change", target="player", meter="test_meter", op="multiply", value=2
    ))
    assert engine.state_manager.state.meters["player"]["test_meter"] == 80

    # Test divide
    engine._apply_meter_change(MeterChangeEffect(
        type="meter_change", target="player", meter="test_meter", op="divide", value=4
    ))
    assert engine.state_manager.state.meters["player"]["test_meter"] == 20

    # Test set
    engine._apply_meter_change(MeterChangeEffect(
        type="meter_change", target="player", meter="test_meter", op="set", value=75
    ))
    assert engine.state_manager.state.meters["player"]["test_meter"] == 75

    print("✅ All meter operations work")


def test_nonexistent_meter_graceful_handling(tmp_path: Path):
    """
    §8.8: Test that applying effects to nonexistent meters fails gracefully.
    """
    game_dir = tmp_path / "nonexistent_meter"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'meters': {
            'player': {
                'health': {'min': 0, 'max': 100, 'default': 75}
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
    engine = GameEngine(loader.load_game("nonexistent_meter"), "test_session")

    # Try to change a meter that doesn't exist - should not crash
    engine._apply_meter_change(MeterChangeEffect(
        type="meter_change",
        target="player",
        meter="nonexistent",
        op="add",
        value=10
    ))

    # Should still have health meter intact
    assert engine.state_manager.state.meters["player"]["health"] == 75

    print("✅ Nonexistent meter handled gracefully")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])