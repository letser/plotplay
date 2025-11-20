"""Test TimeService time advancement and meter decay."""

import logging

from app.core.loader import GameLoader
from app.core.game_engine import GameEngine
from app.engine.time import TimeAdvance
from tests.conftest import minimal_game


def build_engine(tmp_path, monkeypatch) -> GameEngine:
    """Build a game engine with minimal game for testing."""
    def fake_logger(session_id: str) -> logging.Logger:
        logger = logging.getLogger(f"time-test-{session_id}")
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.NullHandler())
        return logger

    monkeypatch.setattr("app.engine.runtime.setup_session_logger", fake_logger)

    game_path = minimal_game(tmp_path)
    loader = GameLoader(games_dir=game_path.parent)
    game_def = loader.load_game(game_path.name)
    return GameEngine(game_def, session_id="time-session")


def test_time_service_advances_slot_and_day(tmp_path, monkeypatch):
    """Test that time service advances slot and day correctly."""
    engine = build_engine(tmp_path, monkeypatch)
    state = engine.state_manager.state
    time_config = engine.game_def.time

    # Since minimal game has slot_windows, use advance_slot() for slot-based advancement
    # Move to the last slot
    state.time.slot = time_config.slots[-1]
    original_day = state.time.day

    # Advance by one slot (should wrap to next day)
    info = engine.time.advance_slot(slots=1)

    assert info.slot_advanced is True
    assert state.time.day == original_day + 1
    assert state.time.slot == time_config.slots[0]


def test_time_service_applies_slot_decay(tmp_path, monkeypatch):
    """Test that time service applies meter decay on slot changes."""
    engine = build_engine(tmp_path, monkeypatch)
    state = engine.state_manager.state

    # Get the player meter definition and set decay
    player_energy_meter = engine.game_def.index.player_meters.get("energy")
    if player_energy_meter:
        # Set initial value
        state.characters["player"].meters["energy"] = 50

        # Manually set decay for testing (normally defined in game YAML)
        player_energy_meter.decay_per_slot = -5

        # Apply dynamics
        advance = TimeAdvance(day_advanced=False, slot_advanced=True, minutes_passed=0)
        engine.time.apply_meter_dynamics(advance)

        # Check decay was applied
        assert state.characters["player"].meters["energy"] == 45


def test_advance_wrapper_returns_dict(tmp_path, monkeypatch):
    """Test that time.advance() returns a TimeAdvance with expected fields."""
    engine = build_engine(tmp_path, monkeypatch)
    result = engine.time.advance()

    # Check that the result is a TimeAdvance with expected attributes
    assert hasattr(result, 'day_advanced')
    assert hasattr(result, 'slot_advanced')
    assert hasattr(result, 'minutes_passed')
    assert isinstance(result.day_advanced, bool)
    assert isinstance(result.slot_advanced, bool)
    assert isinstance(result.minutes_passed, int)
