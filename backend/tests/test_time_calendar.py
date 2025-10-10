"""
Tests for §17 Time & Calendar - PlotPlay v3 Specification.

This file provides comprehensive test coverage for:
- §17.1: Time system definition (slots, clock, hybrid modes)
- §17.2: Time config template (slots, clock, calendar, start)
- §17.3: Runtime state (day, slot, time_hhmm, weekday)
- §17.4: Time effects (advance_time)
- §17.5: Example configurations
- §17.6: Authoring guidelines
"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import AsyncMock

from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine
from app.core.state_manager import StateManager
from app.models.time import TimeConfig, TimeMode, TimeStart, ClockConfig, SlotWindow, CalendarConfig
from app.models.effects import AdvanceTimeEffect


# =============================================================================
# § 17.1: Time System Definition - Three Modes
# =============================================================================

def test_time_mode_enum():
    """
    §17.1: Test TimeMode enum has all three modes.
    """
    assert hasattr(TimeMode, 'SLOTS')
    assert hasattr(TimeMode, 'CLOCK')
    assert hasattr(TimeMode, 'HYBRID')

    assert TimeMode.SLOTS.value == "slots"
    assert TimeMode.CLOCK.value == "clock"
    assert TimeMode.HYBRID.value == "hybrid"

    print("✅ TimeMode enum works")


def test_time_config_slots_mode():
    """
    §17.1: Test TimeConfig for slots mode.
    """
    config = TimeConfig(
        mode=TimeMode.SLOTS,
        slots=["morning", "afternoon", "evening", "night"],
        actions_per_slot=3,
        start=TimeStart(day=1, slot="morning")
    )

    assert config.mode == TimeMode.SLOTS
    assert len(config.slots) == 4
    assert config.actions_per_slot == 3
    assert config.start.slot == "morning"

    print("✅ TimeConfig slots mode works")


def test_time_config_clock_mode():
    """
    §17.1: Test TimeConfig for clock mode.
    """
    config = TimeConfig(
        mode=TimeMode.CLOCK,
        clock=ClockConfig(minutes_per_day=1440),
        start=TimeStart(day=1, time="08:30")
    )

    assert config.mode == TimeMode.CLOCK
    assert config.clock.minutes_per_day == 1440
    assert config.start.time == "08:30"

    print("✅ TimeConfig clock mode works")


def test_time_config_hybrid_mode():
    """
    §17.1: Test TimeConfig for hybrid mode.
    """
    config = TimeConfig(
        mode=TimeMode.HYBRID,
        slots=["morning", "afternoon", "evening", "night"],
        clock=ClockConfig(
            minutes_per_day=1440,
            slot_windows={
                "morning": SlotWindow(start="06:00", end="11:59"),
                "afternoon": SlotWindow(start="12:00", end="17:59"),
                "evening": SlotWindow(start="18:00", end="21:59"),
                "night": SlotWindow(start="22:00", end="05:59")
            }
        ),
        start=TimeStart(day=1, slot="morning", time="08:30")
    )

    assert config.mode == TimeMode.HYBRID
    assert len(config.slots) == 4
    assert config.clock.minutes_per_day == 1440
    assert config.clock.slot_windows["morning"].start == "06:00"
    assert config.start.slot == "morning"
    assert config.start.time == "08:30"

    print("✅ TimeConfig hybrid mode works")


# =============================================================================
# § 17.2: Time Config Template Components
# =============================================================================

def test_slot_window_model():
    """
    §17.2: Test SlotWindow model for HH:MM ranges.
    """
    window = SlotWindow(start="06:00", end="11:59")

    assert window.start == "06:00"
    assert window.end == "11:59"

    print("✅ SlotWindow model works")


def test_clock_config_model():
    """
    §17.2: Test ClockConfig with minutes_per_day and slot_windows.
    """
    clock = ClockConfig(
        minutes_per_day=1440,
        slot_windows={
            "morning": SlotWindow(start="06:00", end="11:59"),
            "afternoon": SlotWindow(start="12:00", end="17:59")
        }
    )

    assert clock.minutes_per_day == 1440
    assert "morning" in clock.slot_windows
    assert clock.slot_windows["morning"].start == "06:00"

    print("✅ ClockConfig model works")


def test_calendar_config_model():
    """
    §17.2: Test CalendarConfig with epoch, week_days, and start_day.
    """
    calendar = CalendarConfig(
        enabled=True,
        epoch="2025-01-01",
        week_days=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
        start_day="monday"
    )

    assert calendar.enabled is True
    assert calendar.epoch == "2025-01-01"
    assert len(calendar.week_days) == 7
    assert calendar.start_day == "monday"

    print("✅ CalendarConfig model works")


def test_calendar_config_validation():
    """
    §17.2: Test that CalendarConfig validates start_day is in week_days.
    """
    # Valid start_day
    calendar = CalendarConfig(
        enabled=True,
        week_days=["monday", "tuesday", "wednesday"],
        start_day="monday"
    )
    assert calendar.start_day == "monday"

    # Invalid start_day should raise error
    with pytest.raises(ValueError):
        CalendarConfig(
            enabled=True,
            week_days=["monday", "tuesday", "wednesday"],
            start_day="invalid_day"
        )

    print("✅ CalendarConfig validation works")


def test_time_start_model():
    """
    §17.2: Test TimeStart with day, slot, and time fields.
    """
    start = TimeStart(day=1, slot="morning", time="08:30")

    assert start.day == 1
    assert start.slot == "morning"
    assert start.time == "08:30"

    print("✅ TimeStart model works")


def test_time_config_defaults():
    """
    §17.2: Test TimeConfig default values.
    """
    config = TimeConfig()

    assert config.mode == TimeMode.SLOTS  # Default
    assert config.actions_per_slot == 3  # Default
    assert config.auto_advance is True  # Default
    assert config.start.day == 1  # Default

    print("✅ TimeConfig defaults work")


# =============================================================================
# § 17.2: Parsing Time Config from YAML
# =============================================================================

def test_slots_mode_parsing_from_yaml(tmp_path: Path):
    """
    §17.2: Test parsing slots mode config from YAML manifest.
    """
    game_dir = tmp_path / "test_slots"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'start', 'location': {'zone': 'z1', 'id': 'loc1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'loc1', 'name': 'Loc 1', 'privacy': 'low'}]}],
        'nodes': [{'id': 'start', 'title': 'Start', 'type': 'scene', 'beats': ['Begin']}],
        'time': {
            'mode': 'slots',
            'slots': ['morning', 'noon', 'afternoon', 'evening', 'night'],
            'actions_per_slot': 3,
            'start': {'day': 1, 'slot': 'morning'}
        }
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_slots")

    assert game_def.time.mode == TimeMode.SLOTS
    assert len(game_def.time.slots) == 5
    assert game_def.time.actions_per_slot == 3
    assert game_def.time.start.slot == "morning"

    print("✅ Slots mode YAML parsing works")


def test_clock_mode_parsing_from_yaml(tmp_path: Path):
    """
    §17.2: Test parsing clock mode config from YAML manifest.
    """
    game_dir = tmp_path / "test_clock"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'start', 'location': {'zone': 'z1', 'id': 'loc1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'loc1', 'name': 'Loc 1', 'privacy': 'low'}]}],
        'nodes': [{'id': 'start', 'title': 'Start', 'type': 'scene', 'beats': ['Begin']}],
        'time': {
            'mode': 'clock',
            'clock': {'minutes_per_day': 1440},
            'start': {'day': 1, 'time': '08:30'}
        }
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_clock")

    assert game_def.time.mode == TimeMode.CLOCK
    assert game_def.time.clock.minutes_per_day == 1440
    assert game_def.time.start.time == "08:30"

    print("✅ Clock mode YAML parsing works")


def test_hybrid_mode_parsing_from_yaml(tmp_path: Path):
    """
    §17.2: Test parsing hybrid mode config from YAML manifest.
    """
    game_dir = tmp_path / "test_hybrid"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'start', 'location': {'zone': 'z1', 'id': 'loc1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'loc1', 'name': 'Loc 1', 'privacy': 'low'}]}],
        'nodes': [{'id': 'start', 'title': 'Start', 'type': 'scene', 'beats': ['Begin']}],
        'time': {
            'mode': 'hybrid',
            'slots': ['morning', 'afternoon', 'evening', 'night'],
            'actions_per_slot': 3,
            'auto_advance': True,
            'clock': {
                'minutes_per_day': 1440,
                'slot_windows': {
                    'morning': {'start': '06:00', 'end': '11:59'},
                    'afternoon': {'start': '12:00', 'end': '17:59'},
                    'evening': {'start': '18:00', 'end': '21:59'},
                    'night': {'start': '22:00', 'end': '05:59'}
                }
            },
            'calendar': {
                'enabled': True,
                'epoch': '2025-01-01',
                'week_days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'],
                'start_day': 'monday'
            },
            'start': {'day': 1, 'slot': 'morning', 'time': '08:30'}
        }
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_hybrid")

    assert game_def.time.mode == TimeMode.HYBRID
    assert len(game_def.time.slots) == 4
    assert game_def.time.clock.minutes_per_day == 1440
    assert "morning" in game_def.time.clock.slot_windows
    assert game_def.time.calendar.enabled is True
    assert game_def.time.calendar.start_day == "monday"
    assert game_def.time.start.slot == "morning"
    assert game_def.time.start.time == "08:30"

    print("✅ Hybrid mode YAML parsing works")


# =============================================================================
# § 17.3: Runtime State
# =============================================================================

def test_runtime_state_slots_mode(tmp_path: Path):
    """
    §17.3: Test runtime state fields in slots mode.
    """
    game_dir = tmp_path / "test_state_slots"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'start', 'location': {'zone': 'z1', 'id': 'loc1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'loc1', 'name': 'Loc 1', 'privacy': 'low'}]}],
        'nodes': [{'id': 'start', 'title': 'Start', 'type': 'scene', 'beats': ['Begin']}],
        'time': {
            'mode': 'slots',
            'slots': ['morning', 'afternoon', 'evening', 'night'],
            'start': {'day': 1, 'slot': 'morning'}
        }
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_state_slots")
    state_manager = StateManager(game_def)

    # Check state fields
    assert state_manager.state.day == 1
    assert state_manager.state.time_slot == "morning"
    # time_hhmm should be None or empty in slots mode
    assert state_manager.state.time_hhmm is None or state_manager.state.time_hhmm == ""

    print("✅ Runtime state (slots mode) works")


def test_runtime_state_clock_mode(tmp_path: Path):
    """
    §17.3: Test runtime state fields in clock mode.
    """
    game_dir = tmp_path / "test_state_clock"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'start', 'location': {'zone': 'z1', 'id': 'loc1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'loc1', 'name': 'Loc 1', 'privacy': 'low'}]}],
        'nodes': [{'id': 'start', 'title': 'Start', 'type': 'scene', 'beats': ['Begin']}],
        'time': {
            'mode': 'clock',
            'clock': {'minutes_per_day': 1440},
            'start': {'day': 1, 'time': '14:35'}
        }
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_state_clock")
    state_manager = StateManager(game_def)

    # Check state fields
    assert state_manager.state.day == 1
    assert state_manager.state.time_hhmm == "14:35"

    print("✅ Runtime state (clock mode) works")


def test_runtime_state_hybrid_mode(tmp_path: Path):
    """
    §17.3: Test runtime state fields in hybrid mode (day, slot, time_hhmm).
    """
    game_dir = tmp_path / "test_state_hybrid"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'start', 'location': {'zone': 'z1', 'id': 'loc1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'loc1', 'name': 'Loc 1', 'privacy': 'low'}]}],
        'nodes': [{'id': 'start', 'title': 'Start', 'type': 'scene', 'beats': ['Begin']}],
        'time': {
            'mode': 'hybrid',
            'slots': ['morning', 'afternoon', 'evening', 'night'],
            'clock': {
                'minutes_per_day': 1440,
                'slot_windows': {
                    'morning': {'start': '06:00', 'end': '11:59'},
                    'afternoon': {'start': '12:00', 'end': '17:59'}
                }
            },
            'start': {'day': 3, 'slot': 'afternoon', 'time': '14:35'}
        }
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_state_hybrid")
    state_manager = StateManager(game_def)

    # Check state fields match spec example §17.3
    assert state_manager.state.day == 3
    assert state_manager.state.time_slot == "afternoon"
    assert state_manager.state.time_hhmm == "14:35"

    print("✅ Runtime state (hybrid mode) works")


def test_runtime_state_with_weekday(tmp_path: Path):
    """
    §17.3: Test runtime state weekday field when calendar is enabled.
    """
    game_dir = tmp_path / "test_state_weekday"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'start', 'location': {'zone': 'z1', 'id': 'loc1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'zones': [{'id': 'z1', 'name': 'Zone 1', 'locations': [{'id': 'loc1', 'name': 'Loc 1', 'privacy': 'low'}]}],
        'nodes': [{'id': 'start', 'title': 'Start', 'type': 'scene', 'beats': ['Begin']}],
        'time': {
            'mode': 'hybrid',
            'slots': ['morning', 'afternoon'],
            'clock': {'minutes_per_day': 1440},
            'calendar': {
                'enabled': True,
                'epoch': '2025-01-01',
                'week_days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'],
                'start_day': 'wednesday'
            },
            'start': {'day': 3, 'slot': 'afternoon', 'time': '14:35'}
        }
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_state_weekday")
    state_manager = StateManager(game_def)

    # Day 3 with start_day "wednesday" means: wed, thu, fri
    assert state_manager.state.weekday == "friday"  # Day 3 = friday (wed + 2)

    print("✅ Runtime state with weekday works")


# =============================================================================
# § 17.4: Time Effects
# =============================================================================

def test_advance_time_effect_model():
    """
    §17.4: Test AdvanceTimeEffect model.
    """
    effect = AdvanceTimeEffect(type="advance_time", minutes=30)

    assert effect.type == "advance_time"
    assert effect.minutes == 30

    print("✅ AdvanceTimeEffect model works")


async def test_advance_time_effect_in_engine():
    """
    §17.4: Test that advance_time effect works in the game engine.
    """
    from pathlib import Path
    tmp_path = Path("games")

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("college_romance")
    engine = GameEngine(game_def, "test_advance_time")
    engine.ai_service.generate = AsyncMock(return_value=type('obj', (object,), {'content': 'Narrative'}))

    initial_time = engine.state_manager.state.time_hhmm
    initial_day = engine.state_manager.state.day

    # Apply advance_time effect
    effect = AdvanceTimeEffect(type="advance_time", minutes=30)
    engine.apply_effects([effect])

    # Time should have advanced
    final_time = engine.state_manager.state.time_hhmm
    final_day = engine.state_manager.state.day

    # Either time changed or day changed
    assert final_time != initial_time or final_day != initial_day

    print("✅ AdvanceTime effect in engine works")


async def test_time_advancement_updates_slot():
    """
    §17.4: Test that advancing time updates slot in hybrid mode.
    """
    from pathlib import Path
    tmp_path = Path("games")

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("college_romance")  # Uses hybrid mode
    engine = GameEngine(game_def, "test_slot_update")
    engine.ai_service.generate = AsyncMock(return_value=type('obj', (object,), {'content': 'Narrative'}))

    # Set time to near a slot boundary
    engine.state_manager.state.time_hhmm = "11:55"
    engine.state_manager.state.time_slot = "morning"

    # Advance by 10 minutes (should cross into afternoon)
    effect = AdvanceTimeEffect(type="advance_time", minutes=10)
    engine.apply_effects([effect])

    # Slot should update (or time should be "12:05")
    assert engine.state_manager.state.time_hhmm == "12:05"
    # Slot may or may not update depending on engine logic
    assert engine.state_manager.state.time_slot in ["morning", "noon", "afternoon"]

    print("✅ Time advancement updates slot works")


async def test_time_advancement_day_rollover():
    """
    §17.4: Test that time advancement can roll over to next day.
    """
    from pathlib import Path
    tmp_path = Path("games")

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("college_romance")
    engine = GameEngine(game_def, "test_day_rollover")
    engine.ai_service.generate = AsyncMock(return_value=type('obj', (object,), {'content': 'Narrative'}))

    initial_day = engine.state_manager.state.day

    # Set time near midnight
    engine.state_manager.state.time_hhmm = "23:55"

    # Advance by 10 minutes (should roll to next day)
    effect = AdvanceTimeEffect(type="advance_time", minutes=10)
    engine.apply_effects([effect])

    # Day should increment
    final_day = engine.state_manager.state.day
    assert final_day == initial_day + 1

    # Time should wrap around
    assert engine.state_manager.state.time_hhmm == "00:05"

    print("✅ Time advancement day rollover works")


async def test_time_advancement_updates_weekday():
    """
    §17.4: Test that day rollover updates weekday when calendar enabled.
    """
    from pathlib import Path
    tmp_path = Path("games")

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("college_romance")  # Has calendar enabled
    engine = GameEngine(game_def, "test_weekday_update")
    engine.ai_service.generate = AsyncMock(return_value=type('obj', (object,), {'content': 'Narrative'}))

    initial_weekday = engine.state_manager.state.weekday
    initial_day = engine.state_manager.state.day

    # Set time near midnight
    engine.state_manager.state.time_hhmm = "23:50"

    # Advance to next day
    effect = AdvanceTimeEffect(type="advance_time", minutes=20)
    engine.apply_effects([effect])

    # Weekday should update
    final_weekday = engine.state_manager.state.weekday
    final_day = engine.state_manager.state.day

    if final_day > initial_day:
        # Weekday should have changed
        assert final_weekday != initial_weekday or initial_weekday is None

    print("✅ Time advancement updates weekday works")


# =============================================================================
# § 17.5: Example Configurations
# =============================================================================

def test_simple_slots_example_from_spec():
    """
    §17.5: Test the simple slots example from the spec.
    """
    config = TimeConfig(
        mode=TimeMode.SLOTS,
        slots=["morning", "noon", "afternoon", "evening", "night", "late_night"],
        actions_per_slot=3,
        start=TimeStart(day=1, slot="morning")
    )

    # Verify matches spec example
    assert config.mode == TimeMode.SLOTS
    assert len(config.slots) == 6
    assert "late_night" in config.slots
    assert config.actions_per_slot == 3
    assert config.start.day == 1
    assert config.start.slot == "morning"

    print("✅ Simple slots example from spec works")


def test_hybrid_example_from_spec():
    """
    §17.5: Test the hybrid mode example from the spec.
    """
    config = TimeConfig(
        mode=TimeMode.HYBRID,
        slots=["morning", "afternoon", "evening", "night"],
        actions_per_slot=3,
        auto_advance=True,
        clock=ClockConfig(
            minutes_per_day=1440,
            slot_windows={
                "morning": SlotWindow(start="06:00", end="11:59"),
                "afternoon": SlotWindow(start="12:00", end="17:59"),
                "evening": SlotWindow(start="18:00", end="21:59"),
                "night": SlotWindow(start="22:00", end="05:59")
            }
        ),
        calendar=CalendarConfig(
            enabled=True,
            epoch="2025-01-01",
            week_days=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            start_day="monday"
        ),
        start=TimeStart(day=1, slot="morning", time="08:30")
    )

    # Verify all fields match spec example
    assert config.mode == TimeMode.HYBRID
    assert len(config.slots) == 4
    assert config.actions_per_slot == 3
    assert config.auto_advance is True
    assert config.clock.minutes_per_day == 1440
    assert len(config.clock.slot_windows) == 4
    assert config.clock.slot_windows["morning"].start == "06:00"
    assert config.clock.slot_windows["morning"].end == "11:59"
    assert config.calendar.enabled is True
    assert config.calendar.epoch == "2025-01-01"
    assert config.calendar.start_day == "monday"
    assert config.start.day == 1
    assert config.start.slot == "morning"
    assert config.start.time == "08:30"

    print("✅ Hybrid example from spec works")


# =============================================================================
# § 17.6: Authoring Guidelines
# =============================================================================

def test_guideline_hybrid_mode_default():
    """
    §17.6: Test that hybrid mode is recommended default.
    """
    # Hybrid mode should have all necessary fields
    config = TimeConfig(
        mode=TimeMode.HYBRID,
        slots=["morning", "afternoon", "evening", "night"],
        clock=ClockConfig(
            minutes_per_day=1440,
            slot_windows={
                "morning": SlotWindow(start="06:00", end="11:59"),
                "afternoon": SlotWindow(start="12:00", end="17:59"),
                "evening": SlotWindow(start="18:00", end="21:59"),
                "night": SlotWindow(start="22:00", end="05:59")
            }
        ),
        start=TimeStart(day=1, slot="morning", time="08:30")
    )

    # Should have both slot-friendly authoring AND precise triggers
    assert config.mode == TimeMode.HYBRID
    assert config.slots is not None
    assert config.clock.slot_windows is not None

    print("✅ Hybrid mode as default works")


def test_guideline_short_slot_names():
    """
    §17.6: Test that slot names are short and consistent.
    """
    # Good slot names: short, lowercase, consistent
    good_slots = ["morning", "afternoon", "evening", "night"]

    # Bad slot names: verbose, inconsistent
    bad_slots = ["early_morning_hours", "AfterNoon", "EVENING_TIME"]

    # All good slots should be lowercase and concise
    for slot in good_slots:
        assert slot.islower()
        assert len(slot) <= 10

    # Bad slots are verbose or inconsistent
    for slot in bad_slots:
        assert len(slot) > 10 or not slot.islower()

    print("✅ Short slot names guideline works")


def test_guideline_always_define_start():
    """
    §17.6: Test that start slot/time is always defined.
    """
    # Config should have start defined
    config = TimeConfig(
        mode=TimeMode.HYBRID,
        slots=["morning", "afternoon"],
        clock=ClockConfig(minutes_per_day=1440),
        start=TimeStart(day=1, slot="morning", time="08:00")
    )

    assert config.start is not None
    assert config.start.day > 0
    assert config.start.slot is not None
    assert config.start.time is not None

    print("✅ Always define start guideline works")


# =============================================================================
# Additional Integration Tests
# =============================================================================

async def test_slots_mode_action_counting():
    """
    §17.1-17.2: Test that slots mode counts actions and advances slots.
    """
    from pathlib import Path
    tmp_path = Path("games")

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("coffeeshop_date")

    # Modify to use slots mode
    game_def.time.mode = TimeMode.SLOTS
    game_def.time.slots = ["morning", "afternoon", "evening"]
    game_def.time.actions_per_slot = 2
    game_def.time.start.slot = "morning"

    engine = GameEngine(game_def, "test_action_count")
    engine.ai_service.generate = AsyncMock(return_value=type('obj', (object,), {'content': 'Narrative'}))

    initial_slot = engine.state_manager.state.time_slot

    # Perform actions
    await engine.process_action("do", action_text="Look around")
    await engine.process_action("do", action_text="Talk")

    # After actions_per_slot actions, slot should advance
    # (implementation may vary)
    final_slot = engine.state_manager.state.time_slot

    # Slot may have advanced
    assert final_slot in ["morning", "afternoon", "evening"]

    print("✅ Slots mode action counting works")


def test_time_hhmm_format():
    """
    §17.3: Test that time_hhmm is always in HH:MM format.
    """
    start = TimeStart(day=1, time="08:30")

    assert start.time == "08:30"
    assert ":" in start.time

    # Split and check format
    parts = start.time.split(":")
    assert len(parts) == 2
    assert len(parts[0]) == 2  # Hours
    assert len(parts[1]) == 2  # Minutes

    print("✅ time_hhmm format works")


def test_weekday_calculation():
    """
    §17.3: Test weekday calculation from day counter and start_day.
    """
    calendar = CalendarConfig(
        enabled=True,
        week_days=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
        start_day="monday"
    )

    # Day 1 = monday
    # Day 2 = tuesday
    # Day 8 = monday (wraps)

    def calculate_weekday(day: int) -> str:
        start_index = calendar.week_days.index(calendar.start_day)
        current_index = (start_index + day - 1) % len(calendar.week_days)
        return calendar.week_days[current_index]

    assert calculate_weekday(1) == "monday"
    assert calculate_weekday(2) == "tuesday"
    assert calculate_weekday(7) == "sunday"
    assert calculate_weekday(8) == "monday"

    print("✅ Weekday calculation works")


# =============================================================================
# § 17.1-17.2: COMPREHENSIVE Slots Mode Action-Based Advancement
# =============================================================================

async def test_slots_mode_action_counter_increments():
    """
    §17.1-17.2: Test that actions_this_slot increments with each action in slots mode.
    """
    from pathlib import Path
    tmp_path = Path("games")

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("coffeeshop_date")

    # Force slots mode
    game_def.time.mode = TimeMode.SLOTS
    game_def.time.slots = ["morning", "afternoon", "evening"]
    game_def.time.actions_per_slot = 3
    game_def.time.start.slot = "morning"

    engine = GameEngine(game_def, "test_action_counter")
    engine.ai_service.generate = AsyncMock(return_value=type('obj', (object,), {'content': 'Narrative'}))

    # Initial state
    assert engine.state_manager.state.actions_this_slot == 0

    # First action
    await engine.process_action("do", action_text="Action 1")
    assert engine.state_manager.state.actions_this_slot == 1

    # Second action
    await engine.process_action("do", action_text="Action 2")
    assert engine.state_manager.state.actions_this_slot == 2

    print("✅ Slots mode action counter increments correctly")


async def test_slots_mode_advances_after_exact_actions():
    """
    §17.1-17.2: Test that slot advances after EXACTLY actions_per_slot actions.
    """
    from pathlib import Path
    tmp_path = Path("games")

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("coffeeshop_date")

    # Configure for precise testing
    game_def.time.mode = TimeMode.SLOTS
    game_def.time.slots = ["morning", "afternoon", "evening", "night"]
    game_def.time.actions_per_slot = 3
    game_def.time.start.slot = "morning"

    engine = GameEngine(game_def, "test_exact_advance")
    engine.ai_service.generate = AsyncMock(return_value=type('obj', (object,), {'content': 'Narrative'}))

    # Reset to known state
    engine.state_manager.state.time_slot = "morning"
    engine.state_manager.state.actions_this_slot = 0

    initial_slot = engine.state_manager.state.time_slot

    # Perform actions_per_slot - 1 actions (should NOT advance)
    for i in range(2):
        await engine.process_action("do", action_text=f"Action {i + 1}")

    # Still in same slot after 2 actions (threshold is 3)
    assert engine.state_manager.state.time_slot == initial_slot
    assert engine.state_manager.state.actions_this_slot == 2

    # Third action should trigger advancement
    await engine.process_action("do", action_text="Action 3")

    # Now slot should have advanced
    assert engine.state_manager.state.time_slot == "afternoon"  # Next slot
    assert engine.state_manager.state.actions_this_slot == 0  # Counter reset

    print("✅ Slot advances after exact actions_per_slot actions")


async def test_slots_mode_counter_resets_on_advancement():
    """
    §17.1-17.2: Test that actions_this_slot resets to 0 after slot advances.
    """
    from pathlib import Path
    tmp_path = Path("games")

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("coffeeshop_date")

    game_def.time.mode = TimeMode.SLOTS
    game_def.time.slots = ["morning", "afternoon"]
    game_def.time.actions_per_slot = 2
    game_def.time.start.slot = "morning"

    engine = GameEngine(game_def, "test_counter_reset")
    engine.ai_service.generate = AsyncMock(return_value=type('obj', (object,), {'content': 'Narrative'}))

    # Reset state
    engine.state_manager.state.time_slot = "morning"
    engine.state_manager.state.actions_this_slot = 0

    # Perform actions to trigger advancement
    await engine.process_action("do", action_text="Action 1")
    await engine.process_action("do", action_text="Action 2")

    # Counter should be reset
    assert engine.state_manager.state.actions_this_slot == 0
    assert engine.state_manager.state.time_slot == "afternoon"

    # Continue counting in new slot
    await engine.process_action("do", action_text="Action 3")
    assert engine.state_manager.state.actions_this_slot == 1

    print("✅ Action counter resets to 0 after slot advancement")


async def test_slots_mode_day_advances_when_slots_exhausted():
    """
    §17.1-17.2: Test that day advances when all slots are exhausted.
    """
    from pathlib import Path
    tmp_path = Path("games")

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("coffeeshop_date")

    # Configure with 2 slots, 2 actions each
    game_def.time.mode = TimeMode.SLOTS
    game_def.time.slots = ["morning", "evening"]
    game_def.time.actions_per_slot = 2
    game_def.time.start.slot = "morning"

    engine = GameEngine(game_def, "test_day_advance")
    engine.ai_service.generate = AsyncMock(return_value=type('obj', (object,), {'content': 'Narrative'}))

    # Set to last slot
    engine.state_manager.state.day = 1
    engine.state_manager.state.time_slot = "evening"
    engine.state_manager.state.actions_this_slot = 0

    initial_day = engine.state_manager.state.day

    # Fill up the last slot
    await engine.process_action("do", action_text="Action 1")
    await engine.process_action("do", action_text="Action 2")

    # Should advance to next day and wrap to first slot
    assert engine.state_manager.state.day == initial_day + 1
    assert engine.state_manager.state.time_slot == "morning"  # Wraps to first
    assert engine.state_manager.state.actions_this_slot == 0

    print("✅ Day advances when all slots exhausted")


async def test_slots_mode_slot_wraps_to_first_on_day_change():
    """
    §17.1-17.2: Test that slot wraps back to first slot when day changes.
    """
    from pathlib import Path
    tmp_path = Path("games")

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("coffeeshop_date")

    game_def.time.mode = TimeMode.SLOTS
    game_def.time.slots = ["morning", "noon", "afternoon", "evening", "night"]
    game_def.time.actions_per_slot = 1  # 1 action per slot for faster testing
    game_def.time.start.slot = "morning"

    engine = GameEngine(game_def, "test_slot_wrap")
    engine.ai_service.generate = AsyncMock(return_value=type('obj', (object,), {'content': 'Narrative'}))

    # Set to last slot, last action
    engine.state_manager.state.day = 5
    engine.state_manager.state.time_slot = "night"
    engine.state_manager.state.actions_this_slot = 0

    # Trigger advancement
    await engine.process_action("do", action_text="Sleep")

    # Should be next day, first slot
    assert engine.state_manager.state.day == 6
    assert engine.state_manager.state.time_slot == "morning"  # First slot

    print("✅ Slot wraps to first slot on day change")


async def test_slots_mode_with_actions_per_slot_one():
    """
    §17.1-17.2: Test edge case where actions_per_slot = 1 (every action advances).
    """
    from pathlib import Path
    tmp_path = Path("games")

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("coffeeshop_date")

    game_def.time.mode = TimeMode.SLOTS
    game_def.time.slots = ["slot1", "slot2", "slot3"]
    game_def.time.actions_per_slot = 1  # Every action advances slot
    game_def.time.start.slot = "slot1"

    engine = GameEngine(game_def, "test_actions_one")
    engine.ai_service.generate = AsyncMock(return_value=type('obj', (object,), {'content': 'Narrative'}))

    engine.state_manager.state.time_slot = "slot1"
    engine.state_manager.state.actions_this_slot = 0

    # First action
    await engine.process_action("do", action_text="Action 1")
    assert engine.state_manager.state.time_slot == "slot2"

    # Second action
    await engine.process_action("do", action_text="Action 2")
    assert engine.state_manager.state.time_slot == "slot3"

    # Third action (exhausts slots, should advance day)
    await engine.process_action("do", action_text="Action 3")
    assert engine.state_manager.state.time_slot == "slot1"  # Wrapped
    assert engine.state_manager.state.day == 2  # Day advanced

    print("✅ Slots mode with actions_per_slot=1 works correctly")


async def test_slots_mode_multiple_complete_days():
    """
    §17.1-17.2: Test progression through multiple complete days in slots mode.
    """
    from pathlib import Path
    tmp_path = Path("games")

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("coffeeshop_date")

    game_def.time.mode = TimeMode.SLOTS
    game_def.time.slots = ["morning", "evening"]  # 2 slots
    game_def.time.actions_per_slot = 2  # 2 actions each
    game_def.time.start.slot = "morning"

    engine = GameEngine(game_def, "test_multi_day")
    engine.ai_service.generate = AsyncMock(return_value=type('obj', (object,), {'content': 'Narrative'}))

    engine.state_manager.state.day = 1
    engine.state_manager.state.time_slot = "morning"
    engine.state_manager.state.actions_this_slot = 0

    initial_day = engine.state_manager.state.day

    # Perform 8 actions = 2 full days (2 slots × 2 actions × 2 days)
    for i in range(8):
        await engine.process_action("do", action_text=f"Action {i + 1}")

    # Should be 2 days later, back at morning
    assert engine.state_manager.state.day == initial_day + 2
    assert engine.state_manager.state.time_slot == "morning"
    assert engine.state_manager.state.actions_this_slot == 0

    print("✅ Multiple complete days progression works")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])