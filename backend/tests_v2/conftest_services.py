import logging

import pytest

from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine
from app.models.game import GameDefinition, MetaConfig, GameStartConfig
from app.models.time import TimeConfig
from app.models.meters import MetersConfig, Meter
from app.models.modifiers import ModifiersConfig, Modifier
from app.models.characters import Character
from app.models.locations import Zone, Location
from app.models.nodes import Node
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


@pytest.fixture
def engine_with_modifiers(monkeypatch):
    """Provide a GameEngine with modifiers for modifier service tests."""
    def fake_logger(session_id: str) -> logging.Logger:
        logger = logging.getLogger(f"modifier-test-{session_id}")
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.NullHandler())
        return logger

    monkeypatch.setattr("app.engine.runtime.setup_session_logger", fake_logger)

    # Create game with modifiers
    modifiers_config = ModifiersConfig(
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
        meta=MetaConfig(
            id="modifier_test",
            title="Modifier Test",
            version="1.0.0"
        ),
        start=GameStartConfig(
            node="start",
            location="room",
            day=1,
            slot="morning"
        ),
        time=TimeConfig(
            mode="slots",
            slots=["morning", "afternoon", "evening"]
        ),
        meters=MetersConfig(
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

    return GameEngine(game, session_id="modifier-session")
