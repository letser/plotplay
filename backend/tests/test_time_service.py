import logging

from app.core.loader import GameLoader
from app.core.game_engine import GameEngine
from app.engine import TimeAdvance
from tests.conftest import minimal_game


def build_engine(tmp_path, monkeypatch) -> GameEngine:
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
    engine = build_engine(tmp_path, monkeypatch)
    state = engine.state_manager.state
    time_config = engine.game_def.time

    # Move to the last slot and the final action within that slot
    state.time_slot = time_config.slots[-1]
    state.actions_this_slot = time_config.actions_per_slot - 1
    original_day = state.day

    info = engine.time.advance()

    assert info.day_advanced is True
    assert info.slot_advanced is True
    assert state.day == original_day + 1
    assert state.time_slot == time_config.slots[0]
    assert state.actions_this_slot == 0


def test_time_service_applies_slot_decay(tmp_path, monkeypatch):
    engine = build_engine(tmp_path, monkeypatch)
    state = engine.state_manager.state

    # Configure decay and starting meter value
    player_meter = engine.game_def.meters.player["energy"]
    player_meter.decay_per_slot = -5
    state.meters.setdefault("player", {})["energy"] = 50

    advance = TimeAdvance(day_advanced=False, slot_advanced=True, minutes_passed=0)
    engine.time.apply_meter_dynamics(advance)

    assert state.meters["player"]["energy"] == 45


def test_advance_wrapper_returns_dict(tmp_path, monkeypatch):
    engine = build_engine(tmp_path, monkeypatch)
    result = engine._advance_time()
    assert {"day_advanced", "slot_advanced", "minutes_passed"} <= set(result.keys())
