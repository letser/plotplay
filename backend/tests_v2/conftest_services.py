import logging

import pytest

from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine
from tests_v2.conftest import minimal_game


@pytest.fixture
def engine_fixture(tmp_path, monkeypatch):
    """Provide a GameEngine with stubbed logger/modifier manager for service unit tests."""

    def fake_logger(session_id: str) -> logging.Logger:
        logger = logging.getLogger(f"service-test-{session_id}")
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.NullHandler())
        return logger

    monkeypatch.setattr("app.engine.runtime.setup_session_logger", fake_logger)

    from app.core import modifier_manager as modifier_module

    class DummyModifierManager:
        def __init__(self, game_def, engine):
            self.game_def = game_def
            self.engine = engine
            self.library = {}
            self.exclusions = []

        def update_modifiers_for_turn(self, *args, **kwargs):
            return None

        def tick_durations(self, *args, **kwargs):
            return None

        def apply_effect(self, *args, **kwargs):
            return None

    monkeypatch.setattr(modifier_module, "ModifierManager", DummyModifierManager)
    monkeypatch.setattr("app.core.game_engine.ModifierManager", DummyModifierManager)

    game_path = minimal_game(tmp_path)
    loader = GameLoader(games_dir=game_path.parent)
    return GameEngine(loader.load_game(game_path.name), session_id="service-session")
