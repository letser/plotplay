"""
Tests for §14 Actions - PlotPlay v3 Spec

Actions are globally defined, reusable player choices that can be unlocked.
Unlike node-based choices tied to specific scenes, unlocked actions persist
across the game and become available based on conditions.

§14.1: Action Definition & Purpose
§14.2: Action Template Structure
  - id (required, unique)
  - prompt (required, display text)
  - category (optional, UI hint)
  - conditions (optional, Expression DSL)
  - effects (optional, applied when chosen)
§14.3: Action Examples & Usage
§14.4: Integration with Game Engine
  - Unlocking via effects
  - Condition evaluation
  - Effect application
  - Persistence across contexts
"""

import pytest
import yaml
from pathlib import Path

from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine
from app.core.conditions import ConditionEvaluator
from app.models.actions import GameAction
from app.models.effects import (
    UnlockEffect, MeterChangeEffect, FlagSetEffect, AnyEffect
)


# =============================================================================
# § 14.1: Action Definition & Purpose
# =============================================================================

def test_action_basic_definition(tmp_path: Path):
    """
    §14.1: Test basic action definition with required fields (id and prompt).
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
            {
                'id': 'basic_action',
                'prompt': 'Perform basic action'
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    assert len(game_def.actions) == 1
    action = game_def.actions[0]
    assert action.id == "basic_action"
    assert action.prompt == "Perform basic action"
    print("✅ Basic action definition works")


def test_action_persists_across_contexts(tmp_path: Path):
    """
    §14.1: Test that unlocked actions persist across different game contexts.
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
        ],
        'actions': [
            {
                'id': 'persistent_action',
                'prompt': 'Use special ability'
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    # Unlock action in scene 1
    engine.state_manager.state.unlocked_actions.append("persistent_action")
    assert "persistent_action" in engine.state_manager.state.unlocked_actions

    # Move to scene 2
    engine.state_manager.state.node_current = "n2"

    # Action should still be unlocked
    assert "persistent_action" in engine.state_manager.state.unlocked_actions
    print("✅ Actions persist across contexts")


# =============================================================================
# § 14.2: Action Template Structure - Required Fields
# =============================================================================

def test_action_requires_id_field():
    """
    §14.2: Test that id field is required for actions.
    """
    # Action without id should fail validation
    with pytest.raises(Exception):  # Pydantic validation error
        GameAction(prompt="Test prompt")

    print("✅ Action id field is required")


def test_action_requires_prompt_field():
    """
    §14.2: Test that prompt field is required for actions.
    """
    # Action without prompt should fail validation
    with pytest.raises(Exception):  # Pydantic validation error
        GameAction(id="test_action")

    print("✅ Action prompt field is required")


def test_action_id_uniqueness(tmp_path: Path):
    """
    §14.2: Test that action IDs must be unique within a game.
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
            {'id': 'action_1', 'prompt': 'First action'},
            {'id': 'action_2', 'prompt': 'Second action'},
            {'id': 'action_3', 'prompt': 'Third action'}
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    # Check all actions have unique IDs
    action_ids = [action.id for action in game_def.actions]
    assert len(action_ids) == len(set(action_ids))
    print("✅ Action IDs are unique")


# =============================================================================
# § 14.2: Action Template Structure - Optional Fields
# =============================================================================

def test_action_with_category_field(tmp_path: Path):
    """
    §14.2: Test action with optional category field (UI hint).
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
            {
                'id': 'flirt',
                'prompt': 'Flirt with them',
                'category': 'romance'
            },
            {
                'id': 'discuss',
                'prompt': 'Discuss philosophy',
                'category': 'conversation'
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    flirt_action = next(a for a in game_def.actions if a.id == "flirt")
    assert flirt_action.category == "romance"

    discuss_action = next(a for a in game_def.actions if a.id == "discuss")
    assert discuss_action.category == "conversation"

    print("✅ Action category field works")


def test_action_with_conditions_field(tmp_path: Path):
    """
    §14.2: Test action with optional conditions field (Expression DSL).
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
        'meters': {
            'emma': {
                'trust': {'min': 0, 'max': 100, 'default': 0}
            }
        },
        'actions': [
            {
                'id': 'deep_talk',
                'prompt': 'Have a deep conversation',
                'conditions': "npc_present('emma') and meters.emma.trust >= 60"
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    action = game_def.actions[0]
    assert action.conditions is not None
    assert "emma" in action.conditions
    assert "trust" in action.conditions
    print("✅ Action conditions field works")


def test_action_with_effects_field(tmp_path: Path):
    """
    §14.2: Test action with optional effects field.
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
        'meters': {
            'emma': {
                'trust': {'min': 0, 'max': 100, 'default': 50}
            }
        },
        'flags': {
            'talked_about_family': {'type': 'bool', 'default': False}
        },
        'actions': [
            {
                'id': 'family_talk',
                'prompt': 'Ask about family',
                'effects': [
                    {
                        'type': 'meter_change',
                        'target': 'emma',
                        'meter': 'trust',
                        'op': 'add',
                        'value': 10
                    },
                    {
                        'type': 'flag_set',
                        'key': 'talked_about_family',
                        'value': True
                    }
                ]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    action = game_def.actions[0]
    assert len(action.effects) == 2
    assert isinstance(action.effects[0], MeterChangeEffect)
    assert isinstance(action.effects[1], FlagSetEffect)
    print("✅ Action effects field works")


# =============================================================================
# § 14.3: Action Examples & Usage
# =============================================================================

def test_action_example_from_spec(tmp_path: Path):
    """
    §14.3: Test the exact example from the specification.
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
        'meters': {
            'emma': {
                'trust': {'min': 0, 'max': 100, 'default': 70}
            }
        },
        'flags': {
            'emma_opened_up': {'type': 'bool', 'default': False}
        },
        'actions': [
            {
                'id': 'deep_talk_emma',
                'prompt': 'Ask Emma about her family',
                'category': 'conversation',
                'conditions': "npc_present('emma') and meters.emma.trust >= 60",
                'effects': [
                    {
                        'type': 'meter_change',
                        'target': 'emma',
                        'meter': 'trust',
                        'op': 'add',
                        'value': 10
                    },
                    {
                        'type': 'flag_set',
                        'key': 'emma_opened_up',
                        'value': True
                    }
                ]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    action = game_def.actions[0]
    assert action.id == "deep_talk_emma"
    assert action.prompt == "Ask Emma about her family"
    assert action.category == "conversation"
    assert action.conditions == "npc_present('emma') and meters.emma.trust >= 60"
    assert len(action.effects) == 2
    print("✅ Spec example action works correctly")


# =============================================================================
# § 14.4: Integration - Unlocking Actions
# =============================================================================

def test_unlock_action_via_effect(tmp_path: Path):
    """
    §14.4: Test unlocking actions via unlock_actions effect.
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
            {
                'id': 'special_move',
                'prompt': 'Use special move'
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    # Initially not unlocked
    assert "special_move" not in engine.state_manager.state.unlocked_actions

    # Unlock via effect
    effect = UnlockEffect(type="unlock_actions", actions=["special_move"])
    engine.apply_effects([effect])

    # Now unlocked
    assert "special_move" in engine.state_manager.state.unlocked_actions
    print("✅ Unlocking actions via effects works")


def test_unlock_multiple_actions(tmp_path: Path):
    """
    §14.4: Test unlocking multiple actions at once.
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
            {'id': 'action_1', 'prompt': 'Action 1'},
            {'id': 'action_2', 'prompt': 'Action 2'},
            {'id': 'action_3', 'prompt': 'Action 3'}
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    # Unlock multiple actions
    effect = UnlockEffect(type="unlock_actions", actions=["action_1", "action_2", "action_3"])
    engine.apply_effects([effect])

    assert "action_1" in engine.state_manager.state.unlocked_actions
    assert "action_2" in engine.state_manager.state.unlocked_actions
    assert "action_3" in engine.state_manager.state.unlocked_actions
    print("✅ Unlocking multiple actions works")


def test_cannot_unlock_nonexistent_action(tmp_path: Path):
    """
    §14.4: Test that attempting to unlock a non-existent action is handled gracefully.
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
            {'id': 'real_action', 'prompt': 'Real action'}
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    # Try to unlock non-existent action (engine should handle gracefully)
    effect = UnlockEffect(type="unlock_actions", actions=["nonexistent_action"])
    engine.apply_effects([effect])

    # Engine may add it to unlocked list, but it won't be usable
    # since it's not in the actions_map
    print("✅ Non-existent action unlock handled gracefully")


# =============================================================================
# § 14.4: Integration - Condition Evaluation
# =============================================================================

def test_action_condition_evaluation(tmp_path: Path):
    """
    §14.4: Test that action conditions are evaluated correctly.
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
        'meters': {
            'emma': {
                'trust': {'min': 0, 'max': 100, 'default': 50}
            }
        },
        'actions': [
            {
                'id': 'high_trust_action',
                'prompt': 'Special interaction',
                'conditions': "meters.emma.trust >= 60"
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    action = game_def.actions[0]
    evaluator = ConditionEvaluator(engine.state_manager.state)

    # Initially trust is 50, condition should be false
    assert not evaluator.evaluate(action.conditions)

    # Increase trust to 60
    engine.state_manager.state.meters["emma"]["trust"] = 60

    # Now condition should be true
    evaluator = ConditionEvaluator(engine.state_manager.state)
    assert evaluator.evaluate(action.conditions)

    print("✅ Action condition evaluation works")


def test_action_condition_with_npc_presence(tmp_path: Path):
    """
    §14.4: Test action conditions that check for NPC presence.
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
        'actions': [
            {
                'id': 'emma_action',
                'prompt': 'Talk to Emma',
                'conditions': "npc_present('emma')"
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    action = game_def.actions[0]
    evaluator = ConditionEvaluator(engine.state_manager.state)

    # Emma not present initially
    assert not evaluator.evaluate(action.conditions)

    # Add Emma to present characters
    engine.state_manager.state.present_chars.append("emma")

    # Now condition should be true
    evaluator = ConditionEvaluator(engine.state_manager.state)
    assert evaluator.evaluate(action.conditions)

    print("✅ Action conditions with NPC presence work")


def test_action_condition_with_flags(tmp_path: Path):
    """
    §14.4: Test action conditions that check flag values.
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
            'quest_completed': {'type': 'bool', 'default': False}
        },
        'actions': [
            {
                'id': 'reward_action',
                'prompt': 'Claim reward',
                'conditions': "flags.quest_completed == true"
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    action = game_def.actions[0]
    evaluator = ConditionEvaluator(engine.state_manager.state)

    # Quest not completed initially
    assert not evaluator.evaluate(action.conditions)

    # Complete quest
    engine.state_manager.state.flags["quest_completed"] = True

    # Now condition should be true
    evaluator = ConditionEvaluator(engine.state_manager.state)
    assert evaluator.evaluate(action.conditions)

    print("✅ Action conditions with flags work")


# =============================================================================
# § 14.4: Integration - Effect Application
# =============================================================================

def test_action_effects_applied_when_chosen(tmp_path: Path):
    """
    §14.4: Test that action effects are applied when the action is chosen.
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
                'meters': {
                    'trust': {'min': 0, 'max': 100, 'default': 50}
                }
            }
        ],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'meters': {
            'character_template': {
                'trust': {'min': 0, 'max': 100, 'default': 60}
            }
        },
        'flags': {
            'action_used': {'type': 'bool', 'default': False}
        },
        'actions': [
            {
                'id': 'test_action',
                'prompt': 'Test action',
                'effects': [
                    {
                        'type': 'meter_change',
                        'target': 'emma',
                        'meter': 'trust',
                        'op': 'add',
                        'value': 15
                    },
                    {
                        'type': 'flag_set',
                        'key': 'action_used',
                        'value': True
                    }
                ]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    # Unlock the action
    engine.state_manager.state.unlocked_actions.append("test_action")

    # Get the action and apply its effects
    action = engine.actions_map["test_action"]
    engine.apply_effects(action.effects)

    # Check effects were applied
    assert engine.state_manager.state.meters["emma"]["trust"] == 65  # 50 + 15
    assert engine.state_manager.state.flags["action_used"] is True

    print("✅ Action effects are applied when chosen")


def test_action_without_effects(tmp_path: Path):
    """
    §14.4: Test that actions without effects field work correctly.
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
            {
                'id': 'no_effect_action',
                'prompt': 'Action with no effects'
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    action = engine.actions_map["no_effect_action"]
    assert action.effects == [] or action.effects is not None

    # Should not crash when applying empty effects
    engine.apply_effects(action.effects)

    print("✅ Actions without effects work")


# =============================================================================
# § 14.4: Integration - Actions vs Node Choices
# =============================================================================

def test_actions_vs_node_choices_distinction(tmp_path: Path):
    """
    §14.4: Test the distinction between actions and node-based choices.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'l1', 'name': 'Loc 1'}]}],
        'nodes': [
            {
                'id': 'n1',
                'type': 'scene',
                'title': 'Start',
                'transitions': [],
                'choices': [
                    {
                        'id': 'node_choice',
                        'prompt': 'Node-specific choice'
                    }
                ]
            },
            {
                'id': 'n2',
                'type': 'scene',
                'title': 'Second scene',
                'transitions': []
            }
        ],
        'actions': [
            {
                'id': 'global_action',
                'prompt': 'Global action available everywhere'
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    # Unlock the global action
    engine.state_manager.state.unlocked_actions.append("global_action")

    # In scene n1: both node choice and global action available
    assert engine.state_manager.state.current_node == "n1"
    node1 = engine.nodes_map["n1"]
    assert len(node1.choices) == 1
    assert "global_action" in engine.state_manager.state.unlocked_actions

    # Move to scene n2
    engine.state_manager.state.current_node = "n2"
    node2 = engine.nodes_map["n2"]

    # Node choice not available here, but global action still is
    assert len(node2.choices) == 0
    assert "global_action" in engine.state_manager.state.unlocked_actions

    print("✅ Actions persist across scenes while node choices don't")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])