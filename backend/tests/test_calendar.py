"""
Test for the Calendar System in PlotPlay v3
Add this to backend/tests/test_calendar.py
"""
import pytest
from app.models.time import TimeConfig, CalendarConfig
from app.models.game import GameDefinition, MetaConfig, StartConfig
from app.core.state_manager import StateManager
from app.core.game_engine import GameEngine


def test_calendar_disabled_by_default():
    """Verify calendar is disabled by default."""
    time_config = TimeConfig()
    assert time_config.calendar is None


def test_calendar_validation():
    """Test that start_day must be in week_days."""
    with pytest.raises(ValueError, match="start_day 'invalid' must be one of"):
        CalendarConfig(
            enabled=True,
            start_day="invalid",
            week_days=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        )


def test_weekday_calculation():
    """Test weekday calculation through multiple days."""
    # Create a minimal game definition with calendar enabled
    game_def = GameDefinition(
        meta=MetaConfig(
            id="test_game",
            title="Test Game",
            authors=["test"]
        ),
        start=StartConfig(
            node="test_node",
            location={"zone": "test_zone", "id": "test_location"}
        ),
        time=TimeConfig(
            calendar=CalendarConfig(
                enabled=True,
                start_day="wednesday",  # Day 1 is Wednesday
                week_days=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            )
        ),
        nodes=[],  # Minimal for testing
        zones=[]
    )

    # Initialize state manager
    state_manager = StateManager(game_def)

    # Day 1 should be Wednesday
    assert state_manager.state.weekday == "wednesday"

    # Simulate day advancement manually
    # (In real usage, GameEngine._advance_time would do this)
    engine = GameEngine(game_def, "test_session")

    # Day 1 = Wednesday
    assert engine.state_manager.state.day == 1
    assert engine.state_manager.state.weekday == "wednesday"

    # Advance to Day 2 = Thursday
    engine.state_manager.state.day = 2
    engine.state_manager.state.weekday = engine._calculate_weekday()
    assert engine.state_manager.state.weekday == "thursday"

    # Advance to Day 7 = Tuesday
    engine.state_manager.state.day = 7
    engine.state_manager.state.weekday = engine._calculate_weekday()
    assert engine.state_manager.state.weekday == "tuesday"

    # Advance to Day 8 = Wednesday (wraps around)
    engine.state_manager.state.day = 8
    engine.state_manager.state.weekday = engine._calculate_weekday()
    assert engine.state_manager.state.weekday == "wednesday"

    # Advance to Day 15 = Wednesday (two weeks later)
    engine.state_manager.state.day = 15
    engine.state_manager.state.weekday = engine._calculate_weekday()
    assert engine.state_manager.state.weekday == "wednesday"


def test_weekday_in_conditions():
    """Test that weekday is available in condition evaluation."""
    game_def = GameDefinition(
        meta=MetaConfig(
            id="test_game",
            title="Test Game",
            authors=["test"]
        ),
        start=StartConfig(
            node="test_node",
            location={"zone": "test_zone", "id": "test_location"}
        ),
        time=TimeConfig(
            calendar=CalendarConfig(
                enabled=True,
                start_day="monday",
                week_days=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            )
        ),
        nodes=[],
        zones=[]
    )

    from app.core.conditions import ConditionEvaluator
    engine = GameEngine(game_def, "test_session")

    # Day 1 = Monday
    evaluator = ConditionEvaluator(engine.state_manager.state, [])
    assert evaluator.evaluate("time.weekday == 'monday'") is True
    assert evaluator.evaluate("time.weekday == 'tuesday'") is False
    assert evaluator.evaluate("time.weekday in ['monday', 'wednesday', 'friday']") is True

    # Advance to Friday (Day 5)
    engine.state_manager.state.day = 5
    engine.state_manager.state.weekday = engine._calculate_weekday()
    evaluator = ConditionEvaluator(engine.state_manager.state, [])
    assert evaluator.evaluate("time.weekday == 'friday'") is True
    assert evaluator.evaluate("time.weekday in ['saturday', 'sunday']") is False


if __name__ == "__main__":
    test_calendar_disabled_by_default()
    test_calendar_validation()
    test_weekday_calculation()
    test_weekday_in_conditions()
    print("✅ All calendar tests passed!")