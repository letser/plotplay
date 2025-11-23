"""
Shared fixtures for the new PlotPlay runtime test suite.

These fixtures intentionally avoid importing from the legacy backend/tests
directory so we can build spec-compliant tests in isolation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.loader import GameLoader
from app.core.validator import GameValidator
from app.runtime.engine import PlotPlayEngine
from app.runtime.types import PlayerAction
from app.services.mock_ai_service import MockAIService


@pytest.fixture(scope="session")
def games_dir() -> Path:
    """Return the path to the repo's games directory."""
    return Path(__file__).resolve().parents[2] / "games"


@pytest.fixture
def loader(games_dir: Path) -> GameLoader:
    """GameLoader pointing at the repo games directory."""
    return GameLoader(games_dir=games_dir)


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Root path for test-only fixture data (YAML games, etc.)."""
    return Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def fixture_games_dir(fixtures_dir: Path) -> Path:
    """Path to the test fixture games."""
    return fixtures_dir / "games"


@pytest.fixture
def fixture_loader(fixture_games_dir: Path) -> GameLoader:
    """GameLoader scoped to the test fixture games."""
    return GameLoader(games_dir=fixture_games_dir)


@pytest.fixture
def mock_ai_service():
    """
    Fast mock AI service for tests - NO real API calls.

    IMPORTANT: Tests MUST use MockAIService to ensure:
    - Fast test execution (no network latency)
    - Deterministic results (no AI randomness)
    - No API costs (no OpenRouter charges)
    - Offline testing (no internet required)

    Production API uses real AIService (OpenRouter).
    """
    return MockAIService()


@pytest.fixture
def engine_factory(mock_ai_service, loader: GameLoader):
    """
    Simple factory that instantiates the new PlotPlayEngine for a given game id.
    Tests can call engine_factory('coffeeshop_date') to get a ready-to-use engine.

    IMPORTANT: Always injects MockAIService (never real AIService).
    """

    def _create(game_id: str, session_id: str = "test-session") -> PlotPlayEngine:
        game_def = loader.load_game(game_id)
        # IMPORTANT: Use mock_ai_service fixture (MockAIService, not real AIService)
        return PlotPlayEngine(game_def, session_id=session_id, ai_service=mock_ai_service)

    return _create


@pytest.fixture
async def started_engine(engine_factory):
    """
    Convenience fixture that returns an engine after running the default start turn.
    Yields (engine, initial_turn_result).
    """
    engine = engine_factory("sandbox", session_id="sandbox-session")
    initial_result = await engine.start()
    return engine, initial_result


@pytest.fixture
def fixture_engine_factory(mock_ai_service, fixture_loader: GameLoader):
    """
    Factory bound to the test fixture games directory.

    IMPORTANT: Always injects MockAIService (never real AIService).
    """

    def _create(game_id: str = "checklist_demo", session_id: str = "fixture-session") -> PlotPlayEngine:
        game_def = fixture_loader.load_game(game_id)
        # Explicit validator run for clarity in tests that want to assert preconditions
        GameValidator(game_def).validate()
        # IMPORTANT: Use mock_ai_service fixture (MockAIService, not real AIService)
        return PlotPlayEngine(game_def, session_id=session_id, ai_service=mock_ai_service)

    return _create


@pytest.fixture
async def started_fixture_engine(fixture_engine_factory):
    """Start a fixture-backed engine and return (engine, initial turn result)."""
    engine = fixture_engine_factory()
    initial_result = await engine.start()
    return engine, initial_result


@pytest.fixture
def fixture_game(fixture_loader: GameLoader):
    """Loaded modifier_auto fixture game definition."""
    game_def = fixture_loader.load_game("modifier_auto")
    GameValidator(game_def).validate()
    return game_def


@pytest.fixture
async def started_mod_engine(fixture_engine_factory):
    """Start the modifier_auto fixture engine."""
    engine = fixture_engine_factory(game_id="modifier_auto", session_id="modifier-session")
    initial_result = await engine.start()
    return engine, initial_result


@pytest.fixture
def fixture_event_game(fixture_loader: GameLoader):
    """Loaded event_cases fixture game definition."""
    game_def = fixture_loader.load_game("event_cases")
    GameValidator(game_def).validate()
    return game_def


@pytest.fixture
def fixture_gate_game(fixture_loader: GameLoader):
    """Loaded gate_cases fixture game definition."""
    game_def = fixture_loader.load_game("gate_cases")
    GameValidator(game_def).validate()
    return game_def


@pytest.fixture
async def started_event_engine(fixture_engine_factory):
    """Start the event_cases fixture engine."""
    engine = fixture_engine_factory(game_id="event_cases", session_id="event-session")
    initial_result = await engine.start()
    return engine, initial_result


@pytest.fixture
async def started_gate_engine(fixture_engine_factory):
    """Start the gate_cases fixture engine."""
    engine = fixture_engine_factory(game_id="gate_cases", session_id="gate-session")
    initial_result = await engine.start()
    return engine, initial_result


@pytest.fixture
def player_action():
    """Helper to construct PlayerAction instances with sensible defaults."""

    def _build(
        action_type: str,
        action_text: str | None = None,
        choice_id: str | None = None,
        item_id: str | None = None,
        target: str | None = None,
    ) -> PlayerAction:
        return PlayerAction(
            action_type=action_type,
            action_text=action_text,
            choice_id=choice_id,
            item_id=item_id,
            target=target,
        )

    return _build
