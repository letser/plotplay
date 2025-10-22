"""API integration tests for the PlotPlay FastAPI application."""

import pytest
from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from app.api import game as game_router


@pytest.fixture
def client():
    """Return a TestClient bound to the FastAPI app."""
    return TestClient(fastapi_app)


def test_health_endpoint(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_list_games_returns_known_game(client: TestClient):
    response = client.get("/api/game/list")
    assert response.status_code == 200
    games = response.json()["games"]
    assert any(game["id"] == "coffeeshop_date" for game in games)


def test_start_action_and_state_flow(client: TestClient):
    # Start a new session
    start_response = client.post("/api/game/start", json={"game_id": "coffeeshop_date"})
    assert start_response.status_code == 200
    payload = start_response.json()
    session_id = payload["session_id"]
    assert session_id
    assert "narrative" in payload
    assert "choices" in payload

    try:
        # Process a simple action
        action_response = client.post(
            f"/api/game/action/{session_id}",
            json={"action_type": "say", "action_text": "Say hello to everyone"},
        )
        assert action_response.status_code == 200
        action_payload = action_response.json()
        assert action_payload["session_id"] == session_id
        assert isinstance(action_payload["choices"], list)
        assert "state_summary" in action_payload

        # Fetch current state snapshot
        state_response = client.get(f"/api/game/session/{session_id}/state")
        assert state_response.status_code == 200
        state_payload = state_response.json()
        assert "state" in state_payload
        assert "history" in state_payload
    finally:
        # Ensure the in-memory session store does not leak across tests
        game_router.game_sessions.pop(session_id, None)
