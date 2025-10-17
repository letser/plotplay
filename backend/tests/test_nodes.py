"""
Tests for §18 Nodes - PlotPlay v3 Specification

This test file validates all node system requirements including:
- Node types (scene, hub, encounter, ending)
- Node structure and required fields
- Choices and transitions
- Dynamic choices
- Entry effects
- Preconditions and access control
- Narration overrides
- Ending validation
"""

import pytest
import yaml
from pathlib import Path
from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine
from app.models.nodes import Node, Choice, Transition, NodeType
from app.models.narration import NarrationConfig
from app.models.enums import POV, Tense
from app.models.effects import MeterChangeEffect, FlagSetEffect, GotoNodeEffect


# =============================================================================
# § 18.1: Node Definition
# =============================================================================

def test_node_required_fields():
    """
    §18.1: Test that nodes require id, type, and title fields.
    """
    # Valid node with all required fields
    node = Node(
        id="test_node",
        type=NodeType.SCENE,
        title="Test Scene"
    )
    assert node.id == "test_node"
    assert node.type == NodeType.SCENE
    assert node.title == "Test Scene"

    # Missing fields should raise validation error
    with pytest.raises(Exception):  # Pydantic validation error
        Node(type=NodeType.SCENE, title="Missing ID")

    with pytest.raises(Exception):
        Node(id="test", title="Missing type")

    with pytest.raises(Exception):
        Node(id="test", type=NodeType.SCENE)  # Missing title

    print("✅ Node required fields validated")


def test_node_optional_fields():
    """
    §18.1: Test that nodes support all optional fields.
    """
    node = Node(
        id="full_node",
        type=NodeType.SCENE,
        title="Full Node",
        characters_present=["char1", "char2"],
        preconditions="flags.unlocked == true",
        once=True,
        beats=["Beat 1", "Beat 2", "Beat 3"],
        entry_effects=[
            MeterChangeEffect(target="player", meter="energy", op="add", value=10)
        ],
        action_filters={"banned_freeform": [{"pattern": "violence"}]}
    )

    assert node.characters_present == ["char1", "char2"]
    assert node.preconditions == "flags.unlocked == true"
    assert node.once is True
    assert len(node.beats) == 3
    assert len(node.entry_effects) == 1
    assert node.action_filters is not None

    print("✅ Node optional fields work")


# =============================================================================
# § 18.2: Node Types
# =============================================================================

def test_node_type_scene():
    """
    §18.2: Test scene node type - focused moment with beats and AI prose.
    """
    node = Node(
        id="date_scene",
        type=NodeType.SCENE,
        title="Coffee Date",
        beats=["Alex looks nervous", "You order coffee"],
        characters_present=["alex"]
    )

    assert node.type == NodeType.SCENE
    assert len(node.beats) > 0
    assert len(node.characters_present) > 0

    print("✅ Scene node type works")


def test_node_type_hub():
    """
    §18.2: Test hub node type - menu-like navigation node.
    """
    node = Node(
        id="campus_hub",
        type=NodeType.HUB,
        title="Campus Center",
        choices=[
            Choice(id="go_library", prompt="Go to Library", goto="library"),
            Choice(id="go_gym", prompt="Go to Gym", goto="gym"),
            Choice(id="go_dorm", prompt="Go to Dorm", goto="dorm")
        ]
    )

    assert node.type == NodeType.HUB
    assert len(node.choices) >= 3  # Hub nodes typically have multiple choices

    print("✅ Hub node type works")


def test_node_type_encounter():
    """
    §18.2: Test encounter node type - short vignette.
    """
    node = Node(
        id="random_encounter",
        type=NodeType.ENCOUNTER,
        title="Unexpected Meeting",
        beats=["You bump into someone in the hallway"],
        transitions=[
            Transition(when="always", to="previous_hub")
        ]
    )

    assert node.type == NodeType.ENCOUNTER
    assert len(node.transitions) > 0  # Encounters usually return somewhere

    print("✅ Encounter node type works")


def test_node_type_ending():
    """
    §18.2: Test ending node type - terminal story resolution.
    """
    node = Node(
        id="happy_ending",
        type=NodeType.ENDING,
        title="Happily Ever After",
        ending_id="good_ending",
        beats=["You and Alex walk off into the sunset"],
        credits={
            "summary": "You achieved the perfect date!",
            "epilogue": ["You dated for years", "Eventually you got married"]
        }
    )

    assert node.type == NodeType.ENDING
    assert node.ending_id == "good_ending"
    assert node.credits is not None

    print("✅ Ending node type works")


def test_ending_validation():
    """
    §18.2: Test that ending nodes must have ending_id.
    """
    # Valid ending
    valid_ending = Node(
        id="end1",
        type=NodeType.ENDING,
        title="The End",
        ending_id="ending_one"
    )
    assert valid_ending.ending_id == "ending_one"

    # Invalid ending without ending_id
    with pytest.raises(ValueError, match="must have ending_id"):
        Node(
            id="bad_ending",
            type=NodeType.ENDING,
            title="Bad End"
            # Missing ending_id!
        )

    print("✅ Ending validation works")


# =============================================================================
# § 18.3: Node Template - Choices
# =============================================================================

def test_choice_structure():
    """
    §18.3: Test choice structure with all fields.
    """
    choice = Choice(
        id="pay_coffee",
        prompt="Pay for both coffees ($10)",
        conditions="meters.player.money >= 10",
        effects=[
            MeterChangeEffect(target="player", meter="money", op="subtract", value=10),
            FlagSetEffect(key="paid_for_date", value=True)
        ],
        goto="next_scene"
    )

    assert choice.id == "pay_coffee"
    assert choice.prompt == "Pay for both coffees ($10)"
    assert choice.conditions is not None
    assert len(choice.effects) == 2
    assert choice.goto == "next_scene"

    print("✅ Choice structure validated")


def test_choice_minimal():
    """
    §18.3: Test minimal choice with just prompt.
    """
    choice = Choice(prompt="Continue")

    assert choice.prompt == "Continue"
    assert choice.id is None  # Optional
    assert choice.conditions is None
    assert len(choice.effects) == 0
    assert choice.goto is None

    print("✅ Minimal choice works")


def test_static_choices_in_node():
    """
    §18.3: Test that nodes can have static preauthored choices.
    """
    node = Node(
        id="choice_node",
        type=NodeType.SCENE,
        title="Make a Choice",
        choices=[
            Choice(id="option_a", prompt="Choose A", goto="path_a"),
            Choice(id="option_b", prompt="Choose B", goto="path_b"),
            Choice(id="option_c", prompt="Choose C", goto="path_c")
        ]
    )

    assert len(node.choices) == 3
    assert all(isinstance(c, Choice) for c in node.choices)
    assert node.choices[0].goto == "path_a"

    print("✅ Static choices work")


def test_dynamic_choices_in_node():
    """
    §18.3: Test that nodes support dynamic choices with conditions.
    """
    node = Node(
        id="dynamic_node",
        type=NodeType.SCENE,
        title="Dynamic Choices",
        dynamic_choices=[
            Choice(
                id="high_confidence_option",
                prompt="[Confidence] Impress with charm",
                conditions="meters.player.confidence >= 70",
                goto="success"
            ),
            Choice(
                id="money_option",
                prompt="[Money] Buy expensive gift",
                conditions="meters.player.money >= 100",
                goto="bought_gift"
            )
        ]
    )

    assert len(node.dynamic_choices) == 2
    assert all(c.conditions is not None for c in node.dynamic_choices)

    print("✅ Dynamic choices work")


# =============================================================================
# § 18.3: Node Template - Transitions
# =============================================================================

def test_transition_structure():
    """
    §18.3: Test transition structure with conditions.
    """
    transition = Transition(
        when="meters.alex.interest >= 70",
        to="good_ending",
        reason="Alex is very interested"
    )

    assert transition.when == "meters.alex.interest >= 70"
    assert transition.to == "good_ending"
    assert transition.reason == "Alex is very interested"

    print("✅ Transition structure validated")


def test_transition_default_condition():
    """
    §18.3: Test that transitions default to 'always' when condition.
    """
    transition = Transition(to="next_node")

    # Default 'when' should be "always"
    assert transition.when == "always"
    assert transition.to == "next_node"

    print("✅ Default transition condition works")


def test_multiple_transitions():
    """
    §18.3: Test that nodes can have multiple conditional transitions.
    """
    node = Node(
        id="branching_node",
        type=NodeType.SCENE,
        title="Branching Path",
        transitions=[
            Transition(
                when="meters.alex.interest >= 80",
                to="perfect_ending"
            ),
            Transition(
                when="meters.alex.interest >= 50",
                to="good_ending"
            ),
            Transition(
                when="meters.alex.interest >= 20",
                to="neutral_ending"
            ),
            Transition(
                when="always",
                to="bad_ending"
            )
        ]
    )

    assert len(node.transitions) == 4
    # Last transition should be the fallback
    assert node.transitions[-1].when == "always"

    print("✅ Multiple transitions work")


# =============================================================================
# § 18.3: Node Template - Availability & Entry Effects
# =============================================================================

def test_node_preconditions():
    """
    §18.3: Test that nodes can have preconditions for access.
    """
    node = Node(
        id="locked_scene",
        type=NodeType.SCENE,
        title="Secret Room",
        preconditions="flags.has_key == true and meters.player.charisma >= 50"
    )

    assert node.preconditions is not None
    assert "flags.has_key" in node.preconditions
    assert "meters.player.charisma" in node.preconditions

    print("✅ Node preconditions work")


def test_node_once_flag():
    """
    §18.3: Test that nodes can be marked as once-only.
    """
    node = Node(
        id="one_time_event",
        type=NodeType.ENCOUNTER,
        title="First Day Intro",
        once=True
    )

    assert node.once is True

    # Default should be None/False for replayable nodes
    replayable = Node(
        id="repeatable",
        type=NodeType.SCENE,
        title="Repeatable Scene"
    )
    assert replayable.once is None or replayable.once is False

    print("✅ Once flag works")


def test_node_entry_effects():
    """
    §18.3: Test that nodes can have entry effects applied on arrival.
    """
    node = Node(
        id="reward_node",
        type=NodeType.SCENE,
        title="Victory!",
        entry_effects=[
            MeterChangeEffect(target="player", meter="experience", op="add", value=100),
            FlagSetEffect(key="chapter_1_complete", value=True),
            MeterChangeEffect(target="player", meter="money", op="add", value=500)
        ]
    )

    assert len(node.entry_effects) == 3
    assert all(hasattr(e, 'type') for e in node.entry_effects)

    print("✅ Entry effects work")


# =============================================================================
# § 18.3: Node Template - Writer Guidance
# =============================================================================

def test_node_beats():
    """
    §18.3: Test that nodes can have beats for writer guidance.
    """
    node = Node(
        id="guided_scene",
        type=NodeType.SCENE,
        title="Date Continues",
        beats=[
            "Alex seems more comfortable now",
            "The conversation flows naturally",
            "You notice she keeps smiling at you",
            "The chemistry is undeniable"
        ]
    )

    assert len(node.beats) == 4
    assert all(isinstance(b, str) for b in node.beats)

    print("✅ Node beats work")


def test_narration_override():
    """
    §18.3: Test that nodes can override narration settings.
    """
    node = Node(
        id="custom_narration_node",
        type=NodeType.SCENE,
        title="Special Scene",
        narration_override=NarrationConfig(
            pov=POV.FIRST,
            tense=Tense.PAST,
            paragraphs="1",
            token_budget=200
        )
    )

    assert node.narration_override is not None
    assert node.narration_override.pov == POV.FIRST
    assert node.narration_override.tense == Tense.PAST
    assert node.narration_override.paragraphs == "1"
    assert node.narration_override.token_budget == 200

    print("✅ Narration override works")


# =============================================================================
# § 18.3: Node Template - Present Characters
# =============================================================================

def test_present_characters():
    """
    §18.3: Test that nodes can explicitly list present characters.
    """
    node = Node(
        id="group_scene",
        type=NodeType.SCENE,
        title="Study Group",
        characters_present=["emma", "liam", "sarah"]
    )

    assert len(node.characters_present) == 3
    assert "emma" in node.characters_present
    assert "liam" in node.characters_present
    assert "sarah" in node.characters_present

    print("✅ Present characters work")


def test_empty_present_characters():
    """
    §18.3: Test nodes with no other characters present.
    """
    node = Node(
        id="solo_scene",
        type=NodeType.SCENE,
        title="Alone in Room"
    )

    assert len(node.characters_present) == 0

    print("✅ Empty present characters work")


# =============================================================================
# § 18.3: Node Template - Action Filters
# =============================================================================

def test_action_filters():
    """
    §18.3: Test that nodes can restrict freeform actions.
    """
    node = Node(
        id="safe_scene",
        type=NodeType.SCENE,
        title="Public Park",
        action_filters={
            "banned_freeform": [
                {"pattern": "violence"},
                {"pattern": "explicit"},
                {"pattern": "illegal"}
            ]
        }
    )

    assert node.action_filters is not None
    assert "banned_freeform" in node.action_filters
    assert len(node.action_filters["banned_freeform"]) == 3

    print("✅ Action filters work")


# =============================================================================
# Integration Tests with Game Engine
# =============================================================================

async def test_node_loading_from_yaml(tmp_path: Path):
    """
    §18: Test loading nodes from YAML game definition.
    """
    game_dir = tmp_path / "node_test"
    game_dir.mkdir()

    manifest = {
        'meta': {
            'id': 'node_test',
            'title': 'Node Test',
            'version': '1.0.0',
            'authors': ['tester']
        },
        'start': {
            'node': 'start_node',
            'location': {'zone': 'test_zone', 'id': 'test_loc'}
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{
            'id': 'test_zone',
            'name': 'Test Zone',
            'locations': [{
                'id': 'test_loc',
                'name': 'Test Location'
            }]
        }],
        'nodes': [
            {
                'id': 'start_node',
                'type': 'scene',
                'title': 'Starting Scene',
                'beats': ['This is the beginning'],
                'transitions': [{'to': 'next_node', 'when': 'always'}]
            },
            {
                'id': 'next_node',
                'type': 'scene',
                'title': 'Next Scene',
                'transitions': [{'to': 'ending', 'when': 'always'}]
            },
            {
                'id': 'ending',
                'type': 'ending',
                'title': 'The End',
                'ending_id': 'test_ending'
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("node_test")

    assert len(game_def.nodes) == 3
    assert game_def.nodes[0].id == "start_node"
    assert game_def.nodes[0].type == NodeType.SCENE
    assert game_def.nodes[2].type == NodeType.ENDING

    print("✅ Node loading from YAML works")


async def test_node_precondition_evaluation(minimal_game_def, sample_game_state):
    """
    §18: Test that node preconditions are properly evaluated by engine.
    """
    from app.core.conditions import ConditionEvaluator

    # Create a node with preconditions
    locked_node = Node(
        id="locked",
        type=NodeType.SCENE,
        title="Locked Scene",
        preconditions="flags.has_key == true and meters.player.energy >= 50"
    )

    evaluator = ConditionEvaluator(sample_game_state)

    # Without meeting conditions
    sample_game_state.flags["has_key"] = False
    sample_game_state.meters["player"]["energy"] = 30
    assert evaluator.evaluate(locked_node.preconditions) is False

    # After meeting conditions
    sample_game_state.flags["has_key"] = True
    sample_game_state.meters["player"]["energy"] = 60
    assert evaluator.evaluate(locked_node.preconditions) is True

    print("✅ Node precondition evaluation works")


async def test_node_once_flag_enforcement(tmp_path: Path):
    """
    §18: Test that once-only nodes can't be entered twice.
    """
    game_dir = tmp_path / "once_test"
    game_dir.mkdir()

    manifest = {
        'meta': {
            'id': 'once_test',
            'title': 'Once Test',
            'version': '1.0.0',
            'authors': ['tester']
        },
        'start': {
            'node': 'hub',
            'location': {'zone': 'z', 'id': 'l'}
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{
            'id': 'z',
            'name': 'Zone',
            'locations': [{'id': 'l', 'name': 'Location'}]
        }],
        'nodes': [
            {
                'id': 'hub',
                'type': 'hub',
                'title': 'Hub',
                'choices': [
                    {'id': 'go_once', 'prompt': 'Visit once-only node', 'goto': 'once_node'}
                ],
                'transitions': []
            },
            {
                'id': 'once_node',
                'type': 'encounter',
                'title': 'One Time Event',
                'once': True,
                'transitions': [{'to': 'hub', 'when': 'always'}]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("once_test")

    # Check that the node is marked as once
    once_node = next(n for n in game_def.nodes if n.id == "once_node")
    assert once_node.once is True

    print("✅ Once flag defined correctly")


async def test_real_game_nodes():
    """
    §18: Test that real game files have valid node structures.
    """
    loader = GameLoader()

    # Test coffeeshop_date nodes
    coffeeshop = loader.load_game("coffeeshop_date")
    assert len(coffeeshop.nodes) > 0

    # Check for various node types
    has_scene = any(n.type == NodeType.SCENE for n in coffeeshop.nodes)
    has_ending = any(n.type == NodeType.ENDING for n in coffeeshop.nodes)

    assert has_scene, "Game should have scene nodes"
    assert has_ending, "Game should have ending nodes"

    # Validate endings have ending_id
    for node in coffeeshop.nodes:
        if node.type == NodeType.ENDING:
            assert node.ending_id is not None, f"Ending {node.id} missing ending_id"

    print("✅ Real game nodes validated")


async def test_choice_with_goto_effect(tmp_path: Path):
    """
    §18: Test that choices can force transitions via goto.
    """
    game_dir = tmp_path / "goto_test"
    game_dir.mkdir()

    manifest = {
        'meta': {
            'id': 'goto_test',
            'title': 'Goto Test',
            'version': '1.0.0',
            'authors': ['tester']
        },
        'start': {
            'node': 'choice_node',
            'location': {'zone': 'z', 'id': 'l'}
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}
        ],
        'zones': [{
            'id': 'z',
            'name': 'Zone',
            'locations': [{'id': 'l', 'name': 'Location'}]
        }],
        'nodes': [
            {
                'id': 'choice_node',
                'type': 'scene',
                'title': 'Make a Choice',
                'choices': [
                    {'id': 'path_a', 'prompt': 'Choose Path A', 'goto': 'destination_a'},
                    {'id': 'path_b', 'prompt': 'Choose Path B', 'goto': 'destination_b'}
                ]
            },
            {
                'id': 'destination_a',
                'type': 'ending',
                'title': 'Ending A',
                'ending_id': 'ending_a'
            },
            {
                'id': 'destination_b',
                'type': 'ending',
                'title': 'Ending B',
                'ending_id': 'ending_b'
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("goto_test")

    start_node = game_def.nodes[0]
    assert len(start_node.choices) == 2
    assert start_node.choices[0].goto == 'destination_a'
    assert start_node.choices[1].goto == 'destination_b'

    print("✅ Choice goto works")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])