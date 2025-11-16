import logging
import os

import pytest

from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine
from app.models.game import GameDefinition, Meta, GameStart
from app.models.time import Time
from app.models.meters import MetersTemplate, Meter
from app.models.modifiers import Modifiers, Modifier
from app.models.characters import Character
from app.models.locations import Zone, Location
from app.models.nodes import Node
from app.services.mock_ai_service import MockAIService
from tests.conftest import minimal_game


@pytest.fixture
def mock_ai_service():
    """Provide mock AI service for fast tests."""
    return MockAIService()


@pytest.fixture
def use_real_ai():
    """Check if tests should use real AI service."""
    return os.environ.get("USE_REAL_AI", "false").lower() == "true"


@pytest.fixture
def engine_fixture(tmp_path, monkeypatch, mock_ai_service, use_real_ai):
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

    # Use real AI service if flag is set, otherwise use mock
    ai_service = None if use_real_ai else mock_ai_service
    return GameEngine(loader.load_game(game_path.name), session_id="service-session", ai_service=ai_service)


@pytest.fixture
def engine_with_modifiers(monkeypatch, mock_ai_service, use_real_ai):
    """Provide a GameEngine with modifiers for modifier service tests."""
    def fake_logger(session_id: str) -> logging.Logger:
        logger = logging.getLogger(f"modifier-test-{session_id}")
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.NullHandler())
        return logger

    monkeypatch.setattr("app.engine.runtime.setup_session_logger", fake_logger)

    # Create game with modifiers
    modifiers_config = Modifiers(
        library=[
            Modifier(
                id="energized",
                group="buff",
                description="Feeling energized",
                duration=60,
                when="meters.player.energy > 80"
            ),
            Modifier(
                id="exhausted",
                group="debuff",
                description="Completely exhausted",
                duration=30,
                when="meters.player.energy < 20"
            ),
            Modifier(
                id="focused",
                group="buff",
                description="Highly focused",
                duration=45,
                when="always"
            )
        ]
    )

    game = GameDefinition(
        meta=Meta(
            id="modifier_test",
            title="Modifier Test",
            version="1.0.0"
        ),
        start=GameStart(
            node="start",
            location="room",
            day=1,
            slot="morning"
        ),
        time=Time(
            mode="slots",
            slots=["morning", "afternoon", "evening"]
        ),
        meters=MetersTemplate(
            player={
                "energy": Meter(min=0, max=100, default=50, visible=True)
            }
        ),
        modifiers=modifiers_config,
        characters=[
            Character(id="player", name="You", age=20, gender="unspecified")
        ],
        zones=[
            Zone(
                id="zone1",
                name="Test Zone",
                locations=[Location(id="room", name="Test Room")]
            )
        ],
        nodes=[
            Node(id="start", type="scene", title="Start")
        ]
    )

    # Use real AI service if flag is set, otherwise use mock
    ai_service = None if use_real_ai else mock_ai_service
    return GameEngine(game, session_id="modifier-session", ai_service=ai_service)
