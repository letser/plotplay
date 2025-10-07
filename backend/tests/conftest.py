"""
Shared pytest fixtures and configuration for PlotPlay tests.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine
from app.services.ai_service import AIService, AIResponse
from app.models.game import GameDefinition, MetaConfig, StartConfig
from app.models.character import Character
from app.models.location import Zone, Location
from app.models.node import Node
from app.models.enums import NodeType
from app.models.meters import Meter
from app.models.flag import Flag


@pytest.fixture
def game_loader():
    """Provides a GameLoader instance."""
    return GameLoader()


@pytest.fixture
def mock_ai_service():
    """Provides a mock AI service with configurable responses."""
    service = MagicMock(spec=AIService)

    def create_response(content: str, memory: list[str] = None):
        if memory:
            return AIResponse(content=json.dumps({"memory": memory}))
        return AIResponse(content=content)

    service.create_response = create_response
    return service


@pytest.fixture
def minimal_game_def():
    """Creates a minimal valid game definition for testing."""
    from app.models.time import TimeConfig, TimeStart
    return GameDefinition(
        meta=MetaConfig(
            id="test_game",
            title="Test Game",
            authors=["tester"]
        ),
        start=StartConfig(
            node="start_node",
            location={"zone": "test_zone", "id": "test_location"}
        ),
        time=TimeConfig(
            start=TimeStart(day=1, slot="morning")
        ),
        nodes=[
            Node(
                id="start_node",
                type="scene",
                title="Start Node",
                transitions=[]
            )
        ],
        zones=[
            Zone(
                id="test_zone",
                name="Test Zone",
                locations=[
                    Location(
                        id="test_location",
                        name="Test Location"
                    )
                ]
            )
        ],
        characters=[
            Character(
                id="player",
                name="Player",
                age=25,
                gender="unspecified"
            )
        ],
        meters={
            "player": {
                "health": Meter(min=0, max=100, default=100)
            }
        },
        flags={
            "game_started": Flag(type="bool", default=False)
        }
    )

@pytest.fixture
async def mock_game_engine(minimal_game_def, mock_ai_service):
    """Creates a GameEngine with mocked AI service."""
    engine = GameEngine(minimal_game_def, "test_session")
    engine.ai_service = mock_ai_service

    # Mock standard AI responses
    async def mock_generate(*args, **kwargs):
        return AIResponse(content="Test narrative")

    engine.ai_service.generate = AsyncMock(side_effect=mock_generate)
    return engine


@pytest.fixture
def sample_game_state():
    """Provides a sample game state for testing."""
    from app.core.state_manager import GameState

    state = GameState()
    state.meters = {
        "player": {"health": 100, "energy": 75, "money": 50}
    }
    state.flags = {
        "game_started": True,
        "tutorial_complete": False
    }
    state.inventory = {
        "player": {"key": 1, "potion": 3}
    }
    state.current_node = "start_node"
    state.day = 1
    state.time_slot = "morning"
    state.location_current = "test_location"
    state.location_zone = "test_zone"
    state.present_chars = ["player"]

    return state


@pytest.fixture
def temp_game_dir(tmp_path):
    """Creates a temporary directory structure for game files."""
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    # Create minimal game.yaml
    game_yaml = game_dir / "game.yaml"
    game_yaml.write_text("""
meta:
  id: temp_test
  title: Temp Test Game
  authors: [tester]
start:
  node: start
  location:
    zone: main
    id: entrance
includes:
  - nodes.yaml
""")

    # Create minimal nodes.yaml
    nodes_yaml = game_dir / "nodes.yaml"
    nodes_yaml.write_text("""
nodes:
  - id: start
    type: normal
    transitions: []
""")

    return game_dir


# Async test markers
pytest.mark.asyncio_mode = "auto"