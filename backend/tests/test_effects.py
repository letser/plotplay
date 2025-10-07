"""
Test for Effect Processing in PlotPlay v3
"""
import pytest
from app.models.effects import (
    ConditionalEffect, RandomEffect, RandomChoice,
    MeterChangeEffect, FlagSetEffect
)
from app.models.game import GameDefinition, MetaConfig, StartConfig
from app.models.node import Node, NodeType
from app.models.location import Zone, Location
from app.core.game_engine import GameEngine


def create_test_game_def():
    """Create a minimal game definition for testing."""
    return GameDefinition(
        meta=MetaConfig(
            id="test_game",
            title="Test Game",
            authors=["test"]
        ),
        start=StartConfig(
            node="test_node",
            location={"zone": "test_zone", "id": "test_location"}
        ),
        nodes=[
            Node(id="test_node", type=NodeType.SCENE, title="Test Node", transitions=[])
        ],
        zones=[
            Zone(id="test_zone", name="Test Zone", locations=[
                Location(id="test_location", name="Test Location")
            ])
        ],
        meters={
            "player": {
                "health": {"min": 0, "max": 100, "default": 50},
                "energy": {"min": 0, "max": 100, "default": 75}

            }
        },
        flags={
            "test_flag": {"type": "bool", "default": False},
            "counter": {"type": "number", "default": 0},
            "low_health": {"type": "bool", "default": False},
            "high_health": {"type": "bool", "default": False},
            "both_conditions_true": {"type": "bool", "default": False},
            "only_first_true": {"type": "bool", "default": False},
            "first_false": {"type": "bool", "default": False},
            "outcome_a": {"type": "bool", "default": False},
            "outcome_b": {"type": "bool", "default": False},
        }
    )


def test_conditional_effect_then_branch():
    """Test that conditional effect executes 'then' branch when the condition is true."""
    game_def = create_test_game_def()
    engine = GameEngine(game_def, "test_session")

    # Set up state where condition will be true
    engine.state_manager.state.meters["player"]["health"] = 30

    # Create a conditional effect
    effect = ConditionalEffect(
        when="meters.player.health < 50",  # This will be true
        then=[
            FlagSetEffect(key="low_health", value=True),
            MeterChangeEffect(target="player", meter="energy", op="add", value=10)
        ],
        otherwise=[
            FlagSetEffect(key="high_health", value=True)
        ]
    )

    # Apply the effect
    engine.apply_effects([effect])

    # Check that the 'then' branch was executed
    assert engine.state_manager.state.flags.get("low_health") is True
    assert engine.state_manager.state.flags.get("high_health") is False
    assert engine.state_manager.state.meters["player"]["energy"] == 85  # 75 + 10


def test_conditional_effect_else_branch():
    """Test that conditional effect executes 'else' branch when condition is false."""
    game_def = create_test_game_def()
    engine = GameEngine(game_def, "test_session")

    # Set up state where condition will be false
    engine.state_manager.state.meters["player"]["health"] = 80

    # Create a conditional effect

    effect = ConditionalEffect(
        when="meters.player.health < 50",  # This will be false
        then=[
            FlagSetEffect(key="low_health", value=True)
        ],
        otherwise=[
            FlagSetEffect(key="high_health", value=True),
            MeterChangeEffect(target="player", meter="health", op="add", value=5)
        ]
    )

    # Apply the effect
    engine.apply_effects([effect])

    # Check that the 'else' branch was executed
    assert engine.state_manager.state.flags.get("high_health") is True
    assert engine.state_manager.state.flags.get("low_health") is False
    assert engine.state_manager.state.meters["player"]["health"] == 85  # 80 + 5


def test_random_effect_deterministic():
    """Test that a random effect is deterministic with the same seed."""
    game_def = create_test_game_def()

    # Create identical engines with the same session (same seed)
    engine1 = GameEngine(game_def, "test_session_123")
    engine2 = GameEngine(game_def, "test_session_123")

    # Create random effect with weighted choices
    effect = RandomEffect(
        choices=[
            RandomChoice(
                weight=30,
                effects=[FlagSetEffect(key="outcome_a", value=True)]
            ),
            RandomChoice(
                weight=70,
                effects=[FlagSetEffect(key="outcome_b", value=True)]
            )
        ]
    )

    # Apply to both engines
    engine1.apply_effects([effect])
    engine2.apply_effects([effect])


    # Both should have same outcome due to same seed
    outcome_a_1 = engine1.state_manager.state.flags.get("outcome_a")
    outcome_a_2 = engine2.state_manager.state.flags.get("outcome_a")
    outcome_b_1 = engine1.state_manager.state.flags.get("outcome_b")
    outcome_b_2 = engine2.state_manager.state.flags.get("outcome_b")

    assert outcome_a_1 == outcome_a_2
    assert outcome_b_1 == outcome_b_2
    assert (outcome_a_1 is True) != (outcome_b_1 is True)  # Only one should be true


def test_meter_multiply_divide():
    """Test multiply and divide operations for meter changes."""
    game_def = create_test_game_def()
    engine = GameEngine(game_def, "test_session")

    # Set initial value
    engine.state_manager.state.meters["player"]["health"] = 40

    # Test multiply
    multiply_effect = MeterChangeEffect(
        target="player",
        meter="health",
        op="multiply",
        value=2
    )
    engine.apply_effects([multiply_effect])
    assert engine.state_manager.state.meters["player"]["health"] == 80  # 40 * 2

    # Test divide
    divide_effect = MeterChangeEffect(
        target="player",
        meter="health",
        op="divide",
        value=4
    )
    engine.apply_effects([divide_effect])
    assert engine.state_manager.state.meters["player"]["health"] == 20  # 80 / 4

    # Test divide by zero protection
    divide_zero_effect = MeterChangeEffect(
        target="player",
        meter="health",
        op="divide",
        value=0
    )
    engine.apply_effects([divide_zero_effect])
    assert engine.state_manager.state.meters["player"]["health"] == 20  # Unchanged


def test_nested_conditional_effects():
    """Test that conditional effects can be nested."""
    game_def = create_test_game_def()
    engine = GameEngine(game_def, "test_session")

    # Create nested conditional
    nested_effect = ConditionalEffect(
        when="meters.player.energy > 50",  # True (75 > 50)
        then=[
            ConditionalEffect(
                when="meters.player.health < 60",  # True (50 < 60)
                then=[
                    FlagSetEffect(key="both_conditions_true", value=True)
                ],
                otherwise=[
                    FlagSetEffect(key="only_first_true", value=True)
                ]
            )
        ],
        otherwise=[
            FlagSetEffect(key="first_false", value=True)
        ]
    )

    # Apply the effect
    engine.apply_effects([nested_effect])

    # Both conditions should be true
    assert engine.state_manager.state.flags.get("both_conditions_true") is True
    assert engine.state_manager.state.flags.get("only_first_true") is False
    assert engine.state_manager.state.flags.get("first_false") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])