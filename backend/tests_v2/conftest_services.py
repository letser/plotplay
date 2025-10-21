import logging

import pytest

from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine
from tests_v2.conftest import minimal_game


@pytest.fixture
def engine_fixture(tmp_path, monkeypatch):
    """Provide a GameEngine with stubbed logger for service unit tests."""

    def fake_logger(session_id: str) -> logging.Logger:
        logger = logging.getLogger(f"service-test-{session_id}")
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.NullHandler())
        return logger

    monkeypatch.setattr("app.engine.runtime.setup_session_logger", fake_logger)

    game_path = minimal_game(tmp_path)
    loader = GameLoader(games_dir=game_path.parent)
    return GameEngine(loader.load_game(game_path.name), session_id="service-session")
