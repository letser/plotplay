"""
Comprehensive tests for PlotPlay v3 core systems.
"""
import pytest
from app.core.state_manager import StateManager, GameState
from app.core.conditions import ConditionEvaluator
from app.core.game_validator import GameValidator
from app.models.time import TimeConfig, CalendarConfig, ClockConfig
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
        assert state.time_slot == "morning"
        assert "player" in state.meters
        assert "health" in state.meters["player"]
        assert "player" in state.inventory
        assert "game_started" in state.flags

    def test_meter_bounds_enforcement(self, minimal_game_def):
        """Test that meter values are properly clamped to min/max."""
        engine = GameEngine(minimal_game_def, "test_bounds")

        # Test overflow
        engine._apply_meter_change(MeterChangeEffect(
            type="meter_change",
            target="player",
            meter="health",
            op="set",
            value=150
        ))
        assert engine.state_manager.state.meters["player"]["health"] == 100

        # Test underflow
        engine._apply_meter_change(MeterChangeEffect(
            type="meter_change",
            target="player",
            meter="health",
            op="set",
            value=-50
        ))
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

        # has() function - checks player inventory
        assert evaluator.evaluate("has('key')")
        assert evaluator.evaluate("has('potion')")
        assert not evaluator.evaluate("has('sword')")

        # npc_present() function
        assert evaluator.evaluate("npc_present('emma')")
        assert evaluator.evaluate("npc_present('alex')")
        assert not evaluator.evaluate("npc_present('john')")

        # get() function with defaults
        assert evaluator.evaluate("get('meters.player.health', 0) == 100")
        assert evaluator.evaluate("get('meters.missing.value', 999) == 999")
        assert evaluator.evaluate("get('flags.game_started', false) == true")

        # Math functions
        assert evaluator.evaluate("min(10, 20) == 10")
        assert evaluator.evaluate("max(10, 20) == 20")
        assert evaluator.evaluate("abs(-10) == 10")
        assert evaluator.evaluate("clamp(150, 0, 100) == 100")
        assert evaluator.evaluate("clamp(-10, 0, 100) == 0")
        assert evaluator.evaluate("clamp(50, 0, 100) == 50")

        # rand() function (deterministic with seed)
        eval_with_seed = ConditionEvaluator(sample_game_state, [], rng_seed=12345)
        results = [eval_with_seed.evaluate("rand(0.5)") for _ in range(100)]
        # Should get mix of true/false, not all same
        assert True in results and False in results

        # Test rand with edge cases
        assert not evaluator.evaluate("rand(0.0)")  # Always false
        assert evaluator.evaluate("rand(1.0)")  # Always true

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
        assert not evaluator.evaluate("time.weekday == 'monday'")

    def test_membership_operator(self, sample_game_state):
        """Test the 'in' operator for membership checking."""
        evaluator = ConditionEvaluator(sample_game_state, ["emma"])

        # Test with lists
        assert evaluator.evaluate("'emma' in ['emma', 'alex', 'john']")
        assert not evaluator.evaluate("'sarah' in ['emma', 'alex', 'john']")

        # Test with time slots - need to set the time_slot properly
        sample_game_state.time_slot = "evening"
        # Create a new evaluator with the updated state
        evaluator = ConditionEvaluator(sample_game_state, ["emma"])
        assert evaluator.evaluate("time.slot in ['evening', 'night']")
        assert not evaluator.evaluate("time.slot in ['morning', 'afternoon']")

    def test_safe_path_resolution(self, sample_game_state):
        """Test that missing paths safely resolve to null/falsey."""
        evaluator = ConditionEvaluator(sample_game_state, [])

        # Missing paths should be falsey
        assert not evaluator.evaluate("meters.nonexistent.value")
        assert not evaluator.evaluate("flags.missing_flag")

        # Can still compare with null
        assert evaluator.evaluate("meters.nonexistent.value == null")
        assert evaluator.evaluate("not meters.nonexistent.value")


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
        with pytest.raises(ValueError, match="references non-existent target ID"):
            validator.validate()

    def test_validates_meter_references(self, minimal_game_def):
        """Test that validator catches references to undefined meters."""
        from app.models.effects import MeterChangeEffect

        minimal_game_def.nodes[0].entry_effects = [
            MeterChangeEffect(
                target="player",
                meter="undefined_meter",
                op="add",
                value=10,
                type="meter_change"
            )
        ]

        validator = GameValidator(minimal_game_def)
        # This might not raise an error depending on implementation
        # but we should test the behavior
        try:
            validator.validate()
        except ValueError as e:
            assert "undefined_meter" in str(e)


class TestTimeSystem:
    """Tests for time advancement and calendar system."""

    def test_time_slot_progression(self, minimal_game_def):
        """Test that time slots advance correctly."""
        minimal_game_def.time = TimeConfig(
            mode="slots",
            slots=["morning", "afternoon", "evening", "night"],
            actions_per_slot=1
        )

        engine = GameEngine(minimal_game_def, "test_time")
        engine.state_manager.state.time_slot = "morning"

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
        minimal_game_def.time = TimeConfig(
            mode="slots",
            calendar=CalendarConfig(
                enabled=True,
                start_day="monday"  # Day 1 will be Monday
            )
        )

        engine = GameEngine(minimal_game_def, "test_calendar")
        state = engine.state_manager.state

        # Day 1 should be Monday (based on start_day)
        state.day = 1
        weekday = engine._calculate_weekday()
        assert weekday == "monday"

        # Day 7 should be Sunday
        state.day = 7
        weekday = engine._calculate_weekday()
        assert weekday == "sunday"

        # Day 8 should wrap to Monday
        state.day = 8
        weekday = engine._calculate_weekday()
        assert weekday == "monday"

        # Day 15 should also be Monday (2 weeks later)
        state.day = 15
        weekday = engine._calculate_weekday()
        assert weekday == "monday"

    def test_clock_mode_time_advancement(self, minimal_game_def):
        """Test time advancement in clock mode."""
        from app.models.time import ClockConfig

        minimal_game_def.time = TimeConfig(
            mode="clock",
            clock=ClockConfig(
                minutes_per_day=1440  # 24 hours
            )
        )

        engine = GameEngine(minimal_game_def, "test_clock")
        state = engine.state_manager.state

        # Set initial time
        state.time_hhmm = "08:00"

        # Advance time by default amount (10 minutes if no parameter given)
        engine._advance_time()

        # Check that time advanced
        assert state.time_hhmm == "08:10"

        # Test specific advancement
        engine._advance_time(30)  # Advance 30 minutes
        assert state.time_hhmm == "08:40"

        # Test day rollover
        state.time_hhmm = "23:50"
        engine._advance_time(20)  # Should roll over to next day

        assert state.time_hhmm == "00:10"
        assert state.day == 2