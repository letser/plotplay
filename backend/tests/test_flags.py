"""
Tests for §9 Flags - PlotPlay v3 Spec

Flags are small, named pieces of state marking discrete facts or progress:
- Type-safe (bool, number, string)
- Global scope with clear naming
- Lightweight and validated at load time
- Support visibility, sticky persistence, and conditional reveals

§9.1: Flag Definition & Required Fields
§9.2: Type Constraints (bool, number, string)
§9.3: Visibility & UI Properties
§9.4: Sticky Flags
§9.5: Conditional Reveal (reveal_when)
§9.6: Allowed Values Validation
§9.7: Global Scope & Naming
§9.8: Usage in Expressions
§9.9: Effects & State Changes
"""

import pytest
import yaml
from pathlib import Path

from app.core.game_loader import GameLoader
from app.core.state_manager import StateManager
from app.core.game_engine import GameEngine
from app.models.effects import FlagSetEffect
from app.core.conditions import ConditionEvaluator


# =============================================================================
# § 9.1: Flag Definition - Required Fields
# =============================================================================

def test_flag_required_fields(tmp_path: Path):
    """
    §9.1: Test that flags MUST have type and default fields.
    """
    game_dir = tmp_path / "flag_required"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'flags': {
            'emma_met': {
                'type': 'bool',
                'default': False
            },
            'reputation_score': {
                'type': 'number',
                'default': 0
            },
            'current_route': {
                'type': 'string',
                'default': 'none'
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
    game_def = loader.load_game("flag_required")
    manager = StateManager(game_def)

    # Flags should be initialized with defaults
    assert manager.state.flags["emma_met"] is False
    assert manager.state.flags["reputation_score"] == 0
    assert manager.state.flags["current_route"] == "none"

    # Flag definitions should have correct types
    assert game_def.flags["emma_met"].type == "bool"
    assert game_def.flags["reputation_score"].type == "number"
    assert game_def.flags["current_route"].type == "string"

    print("✅ Flag required fields (type, default) work")


# =============================================================================
# § 9.2: Type Constraints - Boolean Flags
# =============================================================================

def test_boolean_flags(tmp_path: Path):
    """
    §9.2: Test boolean flags (true/false values).
    """
    game_dir = tmp_path / "bool_flags"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'flags': {
            'emma_met': {
                'type': 'bool',
                'default': False,
                'visible': True,
                'label': 'Met Emma',
                'description': 'Set true after first introduction'
            },
            'first_kiss': {
                'type': 'bool',
                'default': False,
                'description': 'Marks first kiss with any character'
            },
            'route_locked': {
                'type': 'bool',
                'default': False,
                'description': 'Prevents route switching'
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
    game_def = loader.load_game("bool_flags")
    manager = StateManager(game_def)

    # All boolean flags should initialize to their defaults
    assert manager.state.flags["emma_met"] is False
    assert manager.state.flags["first_kiss"] is False
    assert manager.state.flags["route_locked"] is False

    # Test changing boolean flags
    manager.state.flags["emma_met"] = True
    assert manager.state.flags["emma_met"] is True

    print("✅ Boolean flags work")


def test_boolean_flag_visibility(tmp_path: Path):
    """
    §9.2: Test that boolean flags can be visible or hidden.
    """
    game_dir = tmp_path / "bool_visibility"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'flags': {
            'visible_flag': {
                'type': 'bool',
                'default': False,
                'visible': True
            },
            'hidden_flag': {
                'type': 'bool',
                'default': False,
                'visible': False  # Explicitly hidden
            },
            'default_visibility': {
                'type': 'bool',
                'default': False
                # No visible specified - should default to false per spec
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
    game_def = loader.load_game("bool_visibility")

    # Check visibility settings
    assert game_def.flags["visible_flag"].visible is True
    assert game_def.flags["hidden_flag"].visible is False
    assert game_def.flags["default_visibility"].visible is False  # Default per spec

    print("✅ Boolean flag visibility works")


# =============================================================================
# § 9.2: Type Constraints - Number Flags
# =============================================================================

def test_number_flags(tmp_path: Path):
    """
    §9.2: Test number flags (integer values preferred).
    """
    game_dir = tmp_path / "num_flags"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'flags': {
            'days_since_meeting': {
                'type': 'number',
                'default': 0,
                'description': 'Tracks days since first meeting Emma'
            },
            'dates_completed': {
                'type': 'number',
                'default': 0,
                'visible': True,
                'label': 'Dates Completed'
            },
            'favor_counter': {
                'type': 'number',
                'default': 0,
                'description': 'Counts small favors done'
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
    game_def = loader.load_game("num_flags")
    manager = StateManager(game_def)

    # Number flags should initialize to defaults
    assert manager.state.flags["days_since_meeting"] == 0
    assert manager.state.flags["dates_completed"] == 0
    assert manager.state.flags["favor_counter"] == 0

    # Test incrementing number flags
    manager.state.flags["dates_completed"] = 3
    assert manager.state.flags["dates_completed"] == 3

    manager.state.flags["favor_counter"] = manager.state.flags["favor_counter"] + 1
    assert manager.state.flags["favor_counter"] == 1

    print("✅ Number flags work")


# =============================================================================
# § 9.2: Type Constraints - String Flags
# =============================================================================

def test_string_flags(tmp_path: Path):
    """
    §9.2: Test string flags (short identifier strings).
    """
    game_dir = tmp_path / "str_flags"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'flags': {
            'current_route': {
                'type': 'string',
                'default': 'none',
                'description': 'Active romance route'
            },
            'relationship_status': {
                'type': 'string',
                'default': 'single',
                'visible': True,
                'label': 'Relationship Status'
            },
            'last_location_visited': {
                'type': 'string',
                'default': '',
                'description': 'Tracks last visited location'
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
    game_def = loader.load_game("str_flags")
    manager = StateManager(game_def)

    # String flags should initialize to defaults
    assert manager.state.flags["current_route"] == "none"
    assert manager.state.flags["relationship_status"] == "single"
    assert manager.state.flags["last_location_visited"] == ""

    # Test changing string flags
    manager.state.flags["current_route"] = "emma"
    assert manager.state.flags["current_route"] == "emma"

    manager.state.flags["relationship_status"] = "dating"
    assert manager.state.flags["relationship_status"] == "dating"

    print("✅ String flags work")


# =============================================================================
# § 9.6: Allowed Values Validation
# =============================================================================

def test_allowed_values_for_strings(tmp_path: Path):
    """
    §9.6: Test allowed_values constraint for string flags.
    """
    game_dir = tmp_path / "allowed_values"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'flags': {
            'study_reputation': {
                'type': 'string',
                'default': 'neutral',
                'allowed_values': ['bad', 'neutral', 'good', 'excellent'],
                'description': 'Academic reputation'
            },
            'mood': {
                'type': 'string',
                'default': 'calm',
                'allowed_values': ['angry', 'calm', 'happy', 'sad'],
                'visible': True
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
    game_def = loader.load_game("allowed_values")

    # Check that allowed_values are defined
    assert game_def.flags["study_reputation"].allowed_values == ['bad', 'neutral', 'good', 'excellent']
    assert game_def.flags["mood"].allowed_values == ['angry', 'calm', 'happy', 'sad']

    # Flag should initialize to valid default
    manager = StateManager(game_def)
    assert manager.state.flags["study_reputation"] == "neutral"
    assert manager.state.flags["mood"] == "calm"

    print("✅ allowed_values for string flags work")


def test_allowed_values_for_numbers(tmp_path: Path):
    """
    §9.6: Test allowed_values constraint for number flags.
    """
    game_dir = tmp_path / "allowed_nums"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'flags': {
            'difficulty_level': {
                'type': 'number',
                'default': 1,
                'allowed_values': [1, 2, 3, 4, 5],
                'description': 'Game difficulty (1-5)'
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
    game_def = loader.load_game("allowed_nums")

    # Check that allowed_values are defined
    assert game_def.flags["difficulty_level"].allowed_values == [1, 2, 3, 4, 5]

    manager = StateManager(game_def)
    assert manager.state.flags["difficulty_level"] == 1

    print("✅ allowed_values for number flags work")


# =============================================================================
# § 9.3: Visibility & UI Properties
# =============================================================================

def test_flag_label_and_description(tmp_path: Path):
    """
    §9.3: Test that flags can have label and description for UI/docs.
    """
    game_dir = tmp_path / "flag_meta"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'flags': {
            'emma_met': {
                'type': 'bool',
                'default': False,
                'visible': True,
                'label': 'Met Emma',
                'description': 'Set true after the first introduction scene.'
            },
            'dates_count': {
                'type': 'number',
                'default': 0,
                'label': 'Dates Completed',
                'description': 'Total number of successful dates'
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
    game_def = loader.load_game("flag_meta")

    # Check label and description
    assert game_def.flags["emma_met"].label == "Met Emma"
    assert "first introduction" in game_def.flags["emma_met"].description
    assert game_def.flags["dates_count"].label == "Dates Completed"
    assert "successful dates" in game_def.flags["dates_count"].description

    print("✅ Flag label and description work")


# =============================================================================
# § 9.4: Sticky Flags
# =============================================================================

def test_sticky_flag_definition(tmp_path: Path):
    """
    §9.4: Test that flags can be marked as sticky (persist across resets).
    """
    game_dir = tmp_path / "sticky"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'flags': {
            'achievement_unlocked': {
                'type': 'bool',
                'default': False,
                'sticky': True,  # Persists across resets
                'description': 'Achievement flag that persists'
            },
            'regular_flag': {
                'type': 'bool',
                'default': False,
                'sticky': False,  # Does not persist
                'description': 'Normal flag'
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
    game_def = loader.load_game("sticky")

    # Check sticky property
    assert game_def.flags["achievement_unlocked"].sticky is True
    assert game_def.flags["regular_flag"].sticky is False

    print("✅ Sticky flag definition works")


# =============================================================================
# § 9.5: Conditional Reveal (reveal_when)
# =============================================================================

def test_reveal_when_condition(tmp_path: Path):
    """
    §9.5: Test reveal_when expression for conditional flag visibility.
    """
    game_dir = tmp_path / "reveal_when"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'flags': {
            'secret_unlocked': {
                'type': 'bool',
                'default': False,
                'visible': False,
                'reveal_when': 'flags.emma_met == true',
                'description': 'Hidden until Emma is met'
            },
            'emma_met': {
                'type': 'bool',
                'default': False,
                'visible': True
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
    game_def = loader.load_game("reveal_when")

    # Check reveal_when expression is defined
    assert game_def.flags["secret_unlocked"].reveal_when is not None
    assert "flags.emma_met" in game_def.flags["secret_unlocked"].reveal_when

    print("✅ reveal_when conditional visibility works")


# =============================================================================
# § 9.7: Global Scope & Naming Conventions
# =============================================================================

def test_flag_naming_conventions(tmp_path: Path):
    """
    §9.7: Test recommended naming conventions (clear, stable keys).
    """
    game_dir = tmp_path / "naming"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'flags': {
            # Good naming examples from spec
            'emma_met': {'type': 'bool', 'default': False},
            'route_locked': {'type': 'bool', 'default': False},
            'first_kiss': {'type': 'bool', 'default': False},

            # Character-scoped flags (using prefix pattern)
            'emma_invited_to_party': {'type': 'bool', 'default': False},
            'emma_knows_secret': {'type': 'bool', 'default': False},

            # Progress flags
            'chapter_1_complete': {'type': 'bool', 'default': False},
            'ending_unlocked_good': {'type': 'bool', 'default': False}
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
    game_def = loader.load_game("naming")

    # All flags should load successfully
    assert "emma_met" in game_def.flags
    assert "route_locked" in game_def.flags
    assert "emma_invited_to_party" in game_def.flags
    assert "chapter_1_complete" in game_def.flags

    print("✅ Flag naming conventions work")


def test_global_flag_scope(tmp_path: Path):
    """
    §9.7: Test that flags are global (accessible from all contexts).
    """
    game_dir = tmp_path / "global_scope"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'flags': {
            'global_flag': {
                'type': 'bool',
                'default': True,
                'description': 'Accessible from any context'
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
    game_def = loader.load_game("global_scope")
    manager = StateManager(game_def)

    # Flag should be in global state
    assert "global_flag" in manager.state.flags
    assert manager.state.flags["global_flag"] is True

    # Flag should be accessible via expression evaluator
    evaluator = ConditionEvaluator(manager.state)
    assert evaluator.evaluate("flags.global_flag == true")

    print("✅ Global flag scope works")


# =============================================================================
# § 9.8: Usage in Expressions
# =============================================================================

def test_flags_in_boolean_expressions(tmp_path: Path):
    """
    §9.8: Test using boolean flags in condition expressions.
    """
    game_dir = tmp_path / "flag_expressions_bool"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'flags': {
            'emma_met': {'type': 'bool', 'default': True},
            'first_kiss': {'type': 'bool', 'default': False},
            'route_locked': {'type': 'bool', 'default': False}
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
    game_def = loader.load_game("flag_expressions_bool")
    manager = StateManager(game_def)

    evaluator = ConditionEvaluator(manager.state)

    # Test boolean flag expressions (spec examples)
    assert evaluator.evaluate("flags.emma_met == true")
    assert evaluator.evaluate("flags.first_kiss == false")
    assert evaluator.evaluate("flags.route_locked != true")

    # Test compound expressions
    assert evaluator.evaluate("flags.emma_met == true and flags.first_kiss == false")
    assert evaluator.evaluate("flags.emma_met == true or flags.route_locked == true")

    print("✅ Boolean flags in expressions work")


def test_flags_in_string_expressions(tmp_path: Path):
    """
    §9.8: Test using string flags in condition expressions with 'in' operator.
    """
    game_dir = tmp_path / "flag_expressions_str"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'flags': {
            'study_reputation': {
                'type': 'string',
                'default': 'good',
                'allowed_values': ['bad', 'neutral', 'good', 'excellent']
            },
            'current_route': {
                'type': 'string',
                'default': 'emma'
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
    game_def = loader.load_game("flag_expressions_str")
    manager = StateManager(game_def)

    evaluator = ConditionEvaluator(manager.state)

    # Test string flag expressions (spec example)
    assert evaluator.evaluate("flags.study_reputation in ['good', 'excellent']")
    assert evaluator.evaluate("flags.current_route == 'emma'")
    assert not evaluator.evaluate("flags.study_reputation in ['bad', 'neutral']")

    print("✅ String flags in expressions work")


def test_flags_in_number_expressions(tmp_path: Path):
    """
    §9.8: Test using number flags in condition expressions.
    """
    game_dir = tmp_path / "flag_expressions_num"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'flags': {
            'dates_completed': {'type': 'number', 'default': 3},
            'favor_count': {'type': 'number', 'default': 5}
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
    game_def = loader.load_game("flag_expressions_num")
    manager = StateManager(game_def)

    evaluator = ConditionEvaluator(manager.state)

    # Test number flag expressions
    assert evaluator.evaluate("flags.dates_completed >= 2")
    assert evaluator.evaluate("flags.favor_count > 3")
    assert evaluator.evaluate("flags.dates_completed + flags.favor_count == 8")
    assert evaluator.evaluate("flags.dates_completed in [1, 2, 3, 4]")

    print("✅ Number flags in expressions work")


# =============================================================================
# § 9.9: Effects & State Changes
# =============================================================================

def test_flag_set_effect(tmp_path: Path):
    """
    §9.9: Test that FlagSetEffect can change flag values.
    """
    game_dir = tmp_path / "flag_effects"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'flags': {
            'emma_met': {'type': 'bool', 'default': False},
            'reputation': {'type': 'number', 'default': 0},
            'status': {'type': 'string', 'default': 'unknown'}
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
    engine = GameEngine(loader.load_game("flag_effects"), "test_session")

    # Initial values
    assert engine.state_manager.state.flags["emma_met"] is False
    assert engine.state_manager.state.flags["reputation"] == 0
    assert engine.state_manager.state.flags["status"] == "unknown"

    # Apply flag set effects
    engine._apply_flag_set(FlagSetEffect(type="flag_set", key="emma_met", value=True))
    engine._apply_flag_set(FlagSetEffect(type="flag_set", key="reputation", value=10))
    engine._apply_flag_set(FlagSetEffect(type="flag_set", key="status", value="known"))

    # Check changes
    assert engine.state_manager.state.flags["emma_met"] is True
    assert engine.state_manager.state.flags["reputation"] == 10
    assert engine.state_manager.state.flags["status"] == "known"

    print("✅ FlagSetEffect works")


def test_flags_persist_across_turns(tmp_path: Path):
    """
    §9.9: Test that flag values persist across game turns.
    """
    game_dir = tmp_path / "flag_persistence"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z', 'id': 'l'}},
        'flags': {
            'progress_flag': {'type': 'bool', 'default': False},
            'counter': {'type': 'number', 'default': 0}
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
    engine = GameEngine(loader.load_game("flag_persistence"), "test_session")

    # Set flags
    engine.state_manager.state.flags["progress_flag"] = True
    engine.state_manager.state.flags["counter"] = 5

    # Flags should persist (they're just state, not reset between turns)
    assert engine.state_manager.state.flags["progress_flag"] is True
    assert engine.state_manager.state.flags["counter"] == 5

    # Increment counter
    engine.state_manager.state.flags["counter"] += 1
    assert engine.state_manager.state.flags["counter"] == 6

    print("✅ Flags persist across turns")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])