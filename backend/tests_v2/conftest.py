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
    """Fast mock for writer/checker calls."""
    return MockAIService()


@pytest.fixture
def engine_factory(mock_ai_service, loader: GameLoader):
    """
    Simple factory that instantiates the new PlotPlayEngine for a given game id.
    Tests can call engine_factory('coffeeshop_date') to get a ready-to-use engine.
    """

    def _create(game_id: str, session_id: str = "test-session") -> PlotPlayEngine:
        game_def = loader.load_game(game_id)
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
    """

    def _create(game_id: str = "checklist_demo", session_id: str = "fixture-session") -> PlotPlayEngine:
        game_def = fixture_loader.load_game(game_id)
        # Explicit validator run for clarity in tests that want to assert preconditions
        GameValidator(game_def).validate()
        return PlotPlayEngine(game_def, session_id=session_id, ai_service=mock_ai_service)

    return _create


@pytest.fixture
async def started_fixture_engine(fixture_engine_factory):
    """Start a fixture-backed engine and return (engine, initial turn result)."""
    engine = fixture_engine_factory()
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
