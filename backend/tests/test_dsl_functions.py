"""
Tests for Expression DSL functions in PlotPlay v3
"""
import pytest
from app.core.state_manager import GameState
from app.core.conditions import ConditionEvaluator


def test_has_function():
    """Test the has() function for inventory checking."""
    state = GameState()
    state.inventory = {
        "player": {"flowers": 3, "key": 1},
        "emma": {"book": 1}
    }

    evaluator = ConditionEvaluator(state, [])

    # Test has() function
    assert evaluator.evaluate("has('flowers')") is True
    assert evaluator.evaluate("has('key')") is True
    assert evaluator.evaluate("has('missing_item')") is False
    assert evaluator.evaluate("has('book')") is False  # Emma has it, not player

    # Test in complex expressions
    assert evaluator.evaluate("has('flowers') and has('key')") is True
    assert evaluator.evaluate("has('flowers') or has('missing')") is True


def test_npc_present_function():
    """Test the npc_present() function."""
    state = GameState()
    present_chars = ["emma", "alex"]

    evaluator = ConditionEvaluator(state, present_chars)

    assert evaluator.evaluate("npc_present('emma')") is True
    assert evaluator.evaluate("npc_present('alex')") is True
    assert evaluator.evaluate("npc_present('john')") is False

    # Test in complex expressions
    assert evaluator.evaluate("npc_present('emma') and npc_present('alex')") is True
    assert evaluator.evaluate("npc_present('emma') or npc_present('missing')") is True


def test_rand_function_deterministic():
    """Test that rand() is deterministic with same seed."""
    state = GameState()

    # Test with same seed produces same results
    eval1 = ConditionEvaluator(state, [], rng_seed=12345)
    eval2 = ConditionEvaluator(state, [], rng_seed=12345)

    # Both should produce same sequence of random results
    results1 = [eval1.evaluate("rand(0.5)") for _ in range(10)]
    results2 = [eval2.evaluate("rand(0.5)") for _ in range(10)]

    assert results1 == results2

    # Different seed should produce different results
    eval3 = ConditionEvaluator(state, [], rng_seed=99999)
    results3 = [eval3.evaluate("rand(0.5)") for _ in range(10)]
    assert results1 != results3


def test_get_function():
    """Test the get() function for safe path access."""
    state = GameState()
    state.meters = {
        "player": {"energy": 100, "money": 50},
        "emma": {"trust": 75, "attraction": 60}
    }
    state.flags = {
        "first_kiss": True,
        "route_locked": False,
        "emma.met": True  # Character-scoped flag
    }

    evaluator = ConditionEvaluator(state, [])

    # Test successful path access
    assert evaluator.evaluate("get('meters.emma.trust', 0) >= 75") is True
    assert evaluator.evaluate("get('meters.player.energy', 0) == 100") is True
    assert evaluator.evaluate("get('flags.first_kiss', false) == true") is True

    # Test default values for missing paths
    assert evaluator.evaluate("get('meters.missing.value', 999) == 999") is True
    assert evaluator.evaluate("get('flags.missing_flag', false) == false") is True
    assert evaluator.evaluate("get('totally.invalid.path', 'default') == 'default'") is True

    # Test nested access
    assert evaluator.evaluate("get('meters.emma.trust', 0) > get('meters.emma.attraction', 0)") is True


def test_math_functions():
    """Test min, max, abs, clamp functions."""
    state = GameState()
    state.meters = {"player": {"health": 25}}

    evaluator = ConditionEvaluator(state, [])

    # Test min/max
    assert evaluator.evaluate("min(10, 20) == 10") is True
    assert evaluator.evaluate("max(10, 20) == 20") is True
    assert evaluator.evaluate("min(meters.player.health, 50) == 25") is True

    # Test abs
    assert evaluator.evaluate("abs(-10) == 10") is True
    assert evaluator.evaluate("abs(10) == 10") is True

    # Test clamp
    assert evaluator.evaluate("clamp(5, 10, 20) == 10") is True  # Too low
    assert evaluator.evaluate("clamp(15, 10, 20) == 15") is True  # In range
    assert evaluator.evaluate("clamp(25, 10, 20) == 20") is True  # Too high
    assert evaluator.evaluate("clamp(meters.player.health, 0, 100) == 25") is True


def test_complex_expressions_with_functions():
    """Test complex expressions combining multiple functions."""
    state = GameState()
    state.meters = {
        "player": {"energy": 80, "money": 30},
        "emma": {"trust": 60, "attraction": 40}
    }
    state.inventory = {"player": {"flowers": 1}}
    state.flags = {"emma.met": True, "first_date": False}
    state.time_slot = "evening"
    state.weekday = "friday"

    evaluator = ConditionEvaluator(state, ["emma"])

    # Complex condition for date readiness
    date_ready = (
        "npc_present('emma') and "
        "meters.emma.trust >= 50 and "
        "has('flowers') and "
        "time.slot == 'evening' and "
        "time.weekday == 'friday' and "
        "get('flags.first_date', true) == false"
    )
    assert evaluator.evaluate(date_ready) is True

    # Complex condition with math
    can_afford = (
        "meters.player.money >= min(50, meters.emma.trust) or "
        "clamp(meters.player.energy, 0, 100) > 75"
    )
    assert evaluator.evaluate(can_afford) is True

    # Random event with other conditions
    random_event = "rand(0.99) and has('flowers') and npc_present('emma')"
    # This should almost always be true with 0.99 probability
    # but we can't guarantee it without controlling the seed more precisely


def test_safe_division_by_zero():
    """Test that division by zero returns false instead of crashing."""
    state = GameState()
    state.meters = {"player": {"money": 0}}

    evaluator = ConditionEvaluator(state, [])

    # Division by zero should return False
    assert evaluator.evaluate("10 / 0 > 5") is False
    assert evaluator.evaluate("meters.player.money / 0 == 1") is False

    # Normal division should work
    assert evaluator.evaluate("10 / 2 == 5") is True


def test_null_safety():
    """Test that missing paths and null values are handled safely."""
    state = GameState()

    evaluator = ConditionEvaluator(state, [])

    # Missing paths should be falsey
    assert evaluator.evaluate("meters.missing.value") is False
    assert evaluator.evaluate("flags.nonexistent") is False

    # Comparisons with null should be safe
    assert evaluator.evaluate("meters.missing.value == 0") is False
    assert evaluator.evaluate("meters.missing.value > 10") is False

    # But get() with defaults should work
    assert evaluator.evaluate("get('meters.missing.value', 100) == 100") is True


if __name__ == "__main__":
    test_has_function()
    test_npc_present_function()
    test_rand_function_deterministic()
    test_get_function()
    test_math_functions()
    test_complex_expressions_with_functions()
    test_safe_division_by_zero()
    test_null_safety()
    print("✅ All DSL function tests passed!")