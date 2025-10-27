import logging

from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine
from app.models.effects import MeterChangeEffect, ConditionalEffect, FlagSetEffect
from tests.conftest import minimal_game


def make_engine(tmp_path, monkeypatch) -> GameEngine:
    def fake_logger(session_id: str) -> logging.Logger:
        logger = logging.getLogger(f"test-{session_id}")
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.NullHandler())
        return logger

    monkeypatch.setattr("app.engine.runtime.setup_session_logger", fake_logger)


    game_path = minimal_game(tmp_path)
    loader = GameLoader(games_dir=game_path.parent)
    game_def = loader.load_game(game_path.name)
    return GameEngine(game_def, session_id="test-session", ai_service=mock_ai_service)


def test_meter_change_respects_delta_cap(tmp_path, monkeypatch, mock_ai_service):
    engine = make_engine(tmp_path, monkeypatch)
    state = engine.state_manager.state
    state.meters.setdefault("player", {})["energy"] = 50
    engine.game_def.meters.player["energy"].delta_cap_per_turn = 10

    engine.turn_meter_deltas = {}
    engine.apply_effects([
        MeterChangeEffect(target="player", meter="energy", op="add", value=7),
        MeterChangeEffect(target="player", meter="energy", op="add", value=7),
    ])

    assert state.meters["player"]["energy"] == 60


def test_conditional_effect_branches(tmp_path, monkeypatch, mock_ai_service):
    engine = make_engine(tmp_path, monkeypatch)
    state = engine.state_manager.state
    state.flags["met_friend"] = False
    state.meters.setdefault("player", {})["energy"] = 40

    conditional = ConditionalEffect(
        when="flags.met_friend",
        then=[MeterChangeEffect(target="player", meter="energy", op="add", value=5)],
        otherwise=[FlagSetEffect(key="met_friend", value=True)],
    )

    engine.turn_meter_deltas = {}
    engine.apply_effects([conditional])
    assert state.flags["met_friend"] is True
    assert state.meters["player"]["energy"] == 40

    # Re-run once the flag is set to ensure the positive branch fires.
    engine.turn_meter_deltas = {}
    engine.apply_effects([conditional])
    assert state.meters["player"]["energy"] == 45
