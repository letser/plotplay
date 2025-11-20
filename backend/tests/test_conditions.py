"""Test Expression DSL evaluation."""
import pytest
from app.core.loader import GameLoader
from app.core.state import StateManager
from app.models.characters import CharacterState
from app.models.clothing import ClothingState
from app.models.inventory import InventoryState


@pytest.fixture
def evaluator_with_state(tmp_path):
    """Create a ConditionEvaluator with a realistic game state."""
    # Load a real game for proper index
    loader = GameLoader()
    game_def = loader.load_game("coffeeshop_date")

    # Create state manager (auto-initializes state)
    state_manager = StateManager(game_def)

    # Get state reference
    state = state_manager.state
    state.day = 3
    state.time_slot = "evening"
    state.time_hhmm = "19:30"
    state.weekday = "wednesday"
    state.current_location = "cafe"
    state.current_zone = "downtown"
    state.present_characters = ["emma"]

    # Set up character data
    state.characters["player"] = CharacterState(
        meters={"energy": 65, "money": 40},
        inventory=InventoryState(items={"coffee": 1}),
        clothing=ClothingState()
    )

    state.characters["emma"] = CharacterState(
        meters={"trust": 55, "attraction": 42},
        inventory=InventoryState(),
        clothing=ClothingState()
    )

    state.flags = {
        "met_emma": True,
        "invitation_sent": False,
    }

    # Create evaluator
    evaluator = state_manager.create_evaluator()

    return evaluator, state_manager


def test_single_expression_evaluation(evaluator_with_state):
    """Test basic DSL expression evaluation."""
    evaluator, _ = evaluator_with_state

    # Test meter access
    assert evaluator.evaluate("meters.player.energy > 50")
    assert evaluator.evaluate("meters.player.energy == 65")
    assert not evaluator.evaluate("meters.player.energy < 50")

    # Test flag access
    assert evaluator.evaluate("flags.met_emma")
    assert evaluator.evaluate("flags.met_emma == true")
    assert not evaluator.evaluate("flags.invitation_sent")

    # Test inventory (access via .items subcategory)
    assert evaluator.evaluate("inventory.player.items.coffee > 0")
    assert not evaluator.evaluate("inventory.player.items.ticket > 0")


def test_evaluate_all_any(evaluator_with_state):
    """Test evaluate_all and evaluate_any helpers."""
    evaluator, _ = evaluator_with_state

    # Test evaluate_all - all conditions must be true
    assert evaluator.evaluate_all([
        "meters.player.energy > 50",
        "flags.met_emma"
    ])

    assert not evaluator.evaluate_all([
        "meters.player.energy > 50",
        "flags.invitation_sent"  # This is false
    ])

    # Test evaluate_any - at least one condition must be true
    assert evaluator.evaluate_any([
        "flags.invitation_sent",  # False
        "meters.player.money >= 40"  # True
    ])

    assert not evaluator.evaluate_any([
        "flags.invitation_sent",  # False
        "inventory.player.ticket > 0"  # False
    ])


def test_evaluate_conditions_helper(evaluator_with_state):
    """Test evaluate_conditions with when/when_all/when_any."""
    evaluator, state_manager = evaluator_with_state

    # Test with when + when_all
    assert evaluator.evaluate_conditions(
        when="meters.emma.trust >= 50",
        when_all=["flags.met_emma"],
    )

    assert not evaluator.evaluate_conditions(
        when="meters.emma.trust >= 50",
        when_all=["flags.invitation_sent"],  # This fails
    )

    # Test with when + when_all + when_any
    # Create evaluator with gates context
    gates = {"emma": {"accept_walk": True}}
    evaluator_with_gates = state_manager.create_evaluator(extra_context={"gates": gates})

    assert evaluator_with_gates.evaluate_conditions(
        when="meters.emma.trust >= 50",
        when_all=["flags.met_emma"],
        when_any=["gates.emma.accept_walk", "inventory.player.ticket > 0"],
    )


def test_rand_and_get_helpers(evaluator_with_state):
    """Test rand() and get() DSL functions."""
    evaluator, _ = evaluator_with_state

    # Test get() - safe access with default
    assert evaluator.evaluate("get('flags.met_emma', false)")
    assert not evaluator.evaluate("get('flags.missing_flag', false)")

    # Test rand() - should return both True and False over multiple calls
    results = {evaluator.evaluate("rand(0.5)") for _ in range(20)}
    assert results == {True, False}, "rand() should be probabilistic"


def test_context_includes_gates(evaluator_with_state):
    """Test that gates are accessible in DSL context."""
    evaluator, state_manager = evaluator_with_state

    gates = {
        "emma": {
            "accept_walk": True,
            "accept_kiss": False
        }
    }

    evaluator_with_gates = state_manager.create_evaluator(extra_context={"gates": gates})

    assert evaluator_with_gates.evaluate("gates.emma.accept_walk")
    assert not evaluator_with_gates.evaluate("gates.emma.accept_kiss")


def test_boolean_logic(evaluator_with_state):
    """Test boolean operators (and, or, not)."""
    evaluator, _ = evaluator_with_state

    # Test 'and'
    assert evaluator.evaluate("flags.met_emma and meters.player.energy > 50")
    assert not evaluator.evaluate("flags.met_emma and flags.invitation_sent")

    # Test 'or'
    assert evaluator.evaluate("flags.invitation_sent or flags.met_emma")
    assert not evaluator.evaluate("flags.invitation_sent or inventory.player.ticket > 0")

    # Test 'not'
    assert evaluator.evaluate("not flags.invitation_sent")
    assert not evaluator.evaluate("not flags.met_emma")


def test_comparison_operators(evaluator_with_state):
    """Test comparison operators."""
    evaluator, _ = evaluator_with_state

    # Equality
    assert evaluator.evaluate("meters.player.energy == 65")
    assert evaluator.evaluate("meters.player.money != 50")

    # Greater/less than
    assert evaluator.evaluate("meters.player.energy > 60")
    assert evaluator.evaluate("meters.player.energy >= 65")
    assert evaluator.evaluate("meters.player.energy < 70")
    assert evaluator.evaluate("meters.player.energy <= 65")


def test_special_constants(evaluator_with_state):
    """Test special constant expressions."""
    evaluator, _ = evaluator_with_state

    # Always true
    assert evaluator.evaluate("always")
    assert evaluator.evaluate("true")
    assert evaluator.evaluate("")
    assert evaluator.evaluate(None)

    # Always false
    assert not evaluator.evaluate("false")
    assert not evaluator.evaluate("never")
