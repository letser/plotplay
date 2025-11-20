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
    assert payload.get("action_summary")

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
        assert action_payload.get("action_summary")

        # Fetch current state snapshot
        state_response = client.get(f"/api/game/session/{session_id}/state")
        assert state_response.status_code == 200
        state_payload = state_response.json()
        assert "state" in state_payload
        assert "history" in state_payload
    finally:
        # Ensure the in-memory session store does not leak across tests
        game_router.game_sessions.pop(session_id, None)


def test_deterministic_endpoints_flow(client: TestClient):
    start_response = client.post("/api/game/start", json={"game_id": "coffeeshop_date"})
    assert start_response.status_code == 200
    payload = start_response.json()
    session_id = payload["session_id"]

    engine = game_router.game_sessions[session_id]
    state = engine.state_manager.state
    state.present_characters = ["player", "alex"]
    engine.inventory.item_defs["spiced_matcha"].can_give = True

    try:
        move_resp = client.post(
            f"/api/game/move/{session_id}",
            json={"destination_id": "cafe_counter"},
        )
        assert move_resp.status_code == 200
        move_payload = move_resp.json()
        assert move_payload["success"] is True
        assert move_payload["state_summary"]["snapshot"]["location"]["id"] == "cafe_counter"
        assert move_payload.get("action_summary")
        state.present_characters = ["player", "alex"]

        take_resp = client.post(
            f"/api/game/inventory/{session_id}/take",
            json={"owner_id": "player", "item_id": "vanilla_latte", "count": 1},
        )
        assert take_resp.status_code == 200
        take_payload = take_resp.json()
        assert take_payload["success"] is True
        assert take_payload.get("action_summary")

        drop_resp = client.post(
            f"/api/game/inventory/{session_id}/drop",
            json={"owner_id": "player", "item_id": "vanilla_latte", "count": 1},
        )
        assert drop_resp.status_code == 200
        drop_payload = drop_resp.json()
        assert drop_payload["success"] is True
        assert drop_payload.get("action_summary")

        take_again = client.post(
            f"/api/game/inventory/{session_id}/take",
            json={"owner_id": "player", "item_id": "vanilla_latte", "count": 1},
        )
        assert take_again.status_code == 200
        take_again_payload = take_again.json()
        assert take_again_payload["success"] is True
        assert take_again_payload.get("action_summary")

        sell_resp = client.post(
            f"/api/game/shop/{session_id}/sell",
            json={"seller_id": "player", "item_id": "vanilla_latte", "count": 1, "price": 5},
        )
        assert sell_resp.status_code == 200
        sell_payload = sell_resp.json()
        assert sell_payload["success"] is True
        assert sell_payload.get("action_summary")

        purchase_resp = client.post(
            f"/api/game/shop/{session_id}/purchase",
            json={"buyer_id": "player", "item_id": "spiced_matcha", "count": 1, "price": 5},
        )
        assert purchase_resp.status_code == 200
        purchase_payload = purchase_resp.json()
        assert purchase_payload["success"] is True
        assert purchase_payload.get("action_summary")

        give_resp = client.post(
            f"/api/game/inventory/{session_id}/give",
            json={"source_id": "player", "target_id": "alex", "item_id": "spiced_matcha", "count": 1},
        )
        assert give_resp.status_code == 200
        give_payload = give_resp.json()
        assert give_payload["success"] is True
        assert give_payload["state_summary"]["snapshot"]["player"]["inventory"].get("spiced_matcha", 0) == 0
        assert give_payload.get("action_summary")

        move_back = client.post(
            f"/api/game/move/{session_id}",
            json={"direction": "s"},
        )
        assert move_back.status_code == 200
        back_payload = move_back.json()
        assert back_payload["success"] is True
        assert back_payload["state_summary"]["snapshot"]["location"]["id"] == "cafe_patio"
        assert back_payload.get("action_summary")
    finally:
        game_router.game_sessions.pop(session_id, None)


def test_move_endpoint_requires_parameters(client: TestClient):
    start_response = client.post("/api/game/start", json={"game_id": "coffeeshop_date"})
    assert start_response.status_code == 200
    session_id = start_response.json()["session_id"]

    try:
        resp = client.post(f"/api/game/move/{session_id}", json={})
        assert resp.status_code == 400
    finally:
        game_router.game_sessions.pop(session_id, None)


def test_inventory_take_requires_positive_count(client: TestClient):
    start_response = client.post("/api/game/start", json={"game_id": "coffeeshop_date"})
    assert start_response.status_code == 200
    session_id = start_response.json()["session_id"]

    try:
        resp = client.post(
            f"/api/game/inventory/{session_id}/take",
            json={"owner_id": "player", "item_id": "vanilla_latte", "count": 0},
        )
        assert resp.status_code == 400
    finally:
        game_router.game_sessions.pop(session_id, None)


def test_process_action_skip_ai_bypasses_llm(client: TestClient, monkeypatch):
    start_response = client.post("/api/game/start", json={"game_id": "coffeeshop_date"})
    assert start_response.status_code == 200
    payload = start_response.json()
    session_id = payload["session_id"]

    engine = game_router.game_sessions[session_id]

    def _fail(*args, **kwargs):
        pytest.fail("AI service should not be invoked when skip_ai=True")

    monkeypatch.setattr(engine.ai_service, "generate", _fail)

    try:
        response = client.post(
            f"/api/game/action/{session_id}",
            json={
                "action_type": "do",
                "action_text": "Take a steadying breath",
                "skip_ai": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action_summary"]
        assert data["narrative"] == data["action_summary"]
    finally:
        game_router.game_sessions.pop(session_id, None)
