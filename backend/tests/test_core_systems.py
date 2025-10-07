"""
Comprehensive tests for PlotPlay v3 core systems.
"""
import pytest
from app.core.state_manager import StateManager, GameState
from app.core.conditions import ConditionEvaluator
from app.core.game_validator import GameValidator
from app.models.time import TimeConfig, CalendarConfig
from app.models.effects import *
from app.core.game_engine import GameEngine


class TestStateManager:
    """Tests for the StateManager class."""

    def test_state_initialization(self, minimal_game_def):
        """Test that state is properly initialized from game definition."""
        manager = StateManager(minimal_game_def)
        state = manager.state

        assert state.current_node == "start_node"
        assert state.zone_current == "test_zone"
        assert state.location_current == "test_location"
        assert state.day == 1
        assert state.time_slot == "morning"  # Correctly check for the defined start slot
        assert "player" in state.meters
        assert "health" in state.meters["player"]
        assert "player" in state.inventory
        assert "game_started" in state.flags

    def test_meter_bounds_enforcement(self, minimal_game_def):
        """Test that meter values are properly clamped to min/max."""
        engine = GameEngine(minimal_game_def, "test_bounds")

        # Test overflow
        engine._apply_meter_change(MeterChangeEffect(target="player", meter="health", op="set", value=150))
        assert engine.state_manager.state.meters["player"]["health"] == 100

        # Test underflow
        engine._apply_meter_change(MeterChangeEffect(target="player", meter="health", op="set", value=-50))
        assert engine.state_manager.state.meters["player"]["health"] == 0

class TestConditionEvaluator:
    """Tests for the ConditionEvaluator class."""

    def test_basic_operators(self, sample_game_state):
        """Test all basic comparison and logical operators."""
        evaluator = ConditionEvaluator(sample_game_state, [])

        # Comparison operators
        assert evaluator.evaluate("meters.player.health == 100")
        assert evaluator.evaluate("meters.player.energy != 100")
        assert evaluator.evaluate("meters.player.money < 100")
        assert evaluator.evaluate("meters.player.money <= 50")
        assert evaluator.evaluate("meters.player.health > 50")
        assert evaluator.evaluate("meters.player.health >= 100")

        # Logical operators
        assert evaluator.evaluate("true and true")
        assert not evaluator.evaluate("true and false")
        assert evaluator.evaluate("true or false")
        assert evaluator.evaluate("not false")

        # Complex expressions
        assert evaluator.evaluate("(meters.player.health > 50) and (meters.player.energy < 100)")

    def test_dsl_functions_complete(self, sample_game_state):
        """Test all DSL functions from the specification."""
        evaluator = ConditionEvaluator(sample_game_state, ["emma", "alex"])

        # has() function
        assert evaluator.evaluate("has('key')")
        assert evaluator.evaluate("has('potion')")
        assert not evaluator.evaluate("has('sword')")

        # npc_present() function
        assert evaluator.evaluate("npc_present('emma')")
        assert not evaluator.evaluate("npc_present('john')")

        # get() function with defaults
        assert evaluator.evaluate("get('meters.player.health', 0) == 100")
        assert evaluator.evaluate("get('meters.missing.value', 999) == 999")

        # Math functions
        assert evaluator.evaluate("min(10, 20) == 10")
        assert evaluator.evaluate("max(10, 20) == 20")
        assert evaluator.evaluate("abs(-10) == 10")
        assert evaluator.evaluate("clamp(150, 0, 100) == 100")

        # rand() function (deterministic with seed)
        eval_with_seed = ConditionEvaluator(sample_game_state, [], rng_seed=12345)
        results = [eval_with_seed.evaluate("rand(0.5)") for _ in range(100)]
        # Should get mix of true/false, not all same
        assert True in results and False in results

    def test_time_and_calendar_conditions(self, sample_game_state):
        """Test time-based condition evaluation."""
        sample_game_state.time_slot = "evening"
        sample_game_state.weekday = "friday"
        sample_game_state.day = 5

        evaluator = ConditionEvaluator(sample_game_state, [])

        assert evaluator.evaluate("time.slot == 'evening'")
        assert evaluator.evaluate("time.weekday == 'friday'")
        assert evaluator.evaluate("time.day == 5")
        assert evaluator.evaluate("time.weekday in ['friday', 'saturday']")


class TestGameValidator:
    """Tests for game validation."""

    def test_validates_node_references(self, minimal_game_def):
        """Test that validator catches invalid node references."""
        from app.models.node import Transition
        minimal_game_def.nodes[0].transitions = [
            Transition(to="non_existent_node")
        ]

        validator = GameValidator(minimal_game_def)
        with pytest.raises(ValueError, match="points to non-existent node ID"):
            validator.validate()

    def test_validates_location_references(self, minimal_game_def):
        """Test that validator catches invalid location references."""
        from app.models.effects import MoveToEffect
        minimal_game_def.nodes[0].entry_effects = [
            MoveToEffect(location="bad_loc", type="move_to")
        ]

        validator = GameValidator(minimal_game_def)
        with pytest.raises(ValueError, match="references non-existent location ID"):
            validator.validate()

    def test_validates_character_references(self, minimal_game_def):
        """Test that validator catches invalid character references."""
        # Add effect referencing non-existent character
        from app.models.effects import MeterChangeEffect

        minimal_game_def.nodes[0].entry_effects = [
            MeterChangeEffect(
                target="non_existent_char",
                meter="health",
                op="add",
                value=10,
                type="meter_change"
            )
        ]

        validator = GameValidator(minimal_game_def)
        # Correct the expected error message to match the validator's output
        with pytest.raises(ValueError, match="references non-existent target ID"):
            validator.validate()


class TestTimeSystem:
    """Tests for time advancement and calendar system."""

    def test_time_slot_progression(self, minimal_game_def):
        """Test that time slots advance correctly."""
        minimal_game_def.time = TimeConfig(
            mode="slots",
            slots=["morning", "afternoon", "evening", "night"],
            actions_per_slot=1
        )

        from app.core.game_engine import GameEngine
        engine = GameEngine(minimal_game_def, "test_time")
        engine.state_manager.state.time_slot = "morning"  # Manually set start slot

        assert engine.state_manager.state.time_slot == "morning"

        # Advance through all slots
        engine._advance_time()
        assert engine.state_manager.state.time_slot == "afternoon"

        engine._advance_time()
        assert engine.state_manager.state.time_slot == "evening"

        engine._advance_time()
        assert engine.state_manager.state.time_slot == "night"

        # Should wrap to next day
        engine._advance_time()
        assert engine.state_manager.state.time_slot == "morning"
        assert engine.state_manager.state.day == 2

    def test_calendar_weekday_calculation(self, minimal_game_def):
        """Test calendar weekday calculations."""
        # Correctly create and assign a new TimeConfig object
        minimal_game_def.time = TimeConfig(
            calendar=CalendarConfig(
                enabled=True,
                start_day="wednesday",
                week_days=["monday", "tuesday", "wednesday", "thursday",
                           "friday", "saturday", "sunday"]
            )
        )

        from app.core.game_engine import GameEngine
        engine = GameEngine(minimal_game_def, "test_calendar")

        # Manually trigger the initial weekday calculation since we modified the def
        engine.state_manager.state.weekday = engine._calculate_weekday()

        # Day 1 = Wednesday
        assert engine.state_manager.state.weekday == "wednesday"

        # Test various days
        test_cases = [
            (2, "thursday"),
            (5, "sunday"),
            (8, "wednesday"),  # Wraps around
            (14, "tuesday"),  # Two weeks
        ]

        for day, expected_weekday in test_cases:
            engine.state_manager.state.day = day
            assert engine._calculate_weekday() == expected_weekday


if __name__ == "__main__":
    pytest.main([__file__, "-v"])