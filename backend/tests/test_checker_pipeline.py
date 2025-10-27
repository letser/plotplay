"""Tests for applying checker deltas using the new schema."""

from tests_v2.conftest_services import engine_fixture  # noqa: F401


def test_apply_ai_state_changes_new_schema(engine_fixture):
    engine = engine_fixture
    state = engine.state_manager.state

    engine.inventory.item_defs["coffee"].can_give = True

    state.present_chars = ["player", "friend"]
    state.inventory.setdefault("player", {})
    state.inventory.setdefault("friend", {})
    state.location_inventory.setdefault(state.location_current, {"coffee": 1})

    baseline_energy = state.meters["player"]["energy"]
    baseline_money = state.meters["player"].get("money", 0)

    deltas = {
        "meters": {
            "player": [
                {"meter": "energy", "delta": -10},
            ]
        },
        "inventory": [
            {"op": "take", "owner": "player", "item": "coffee", "count": 1},
            {"op": "give", "from": "player", "to": "friend", "item": "coffee", "count": 1},
            {"op": "purchase", "buyer": "player", "item": "coffee", "count": 1, "price": 2},
            {"op": "sell", "seller": "player", "item": "coffee", "count": 1, "price": 2},
        ],
        "flags": [
            {"key": "met_friend", "value": True},
        ],
        "discoveries": {
            "locations": [state.location_current],
        },
    }

    engine._apply_ai_state_changes(deltas)

    assert state.meters["player"]["energy"] == baseline_energy - 10
    assert state.flags.get("met_friend") is True
    assert state.inventory["player"].get("coffee", 0) in (0, 1)
    assert state.inventory["friend"].get("coffee", 0) >= 1
    assert state.location_current in state.discovered_locations
    # Money should remain within bounds even after purchase/sell cycle
    assert state.meters["player"]["money"] <= baseline_money


def test_apply_ai_state_changes_handles_clothing_and_discoveries(engine_fixture):
    engine = engine_fixture
    state = engine.state_manager.state

    assert state.clothing_states["player"]["layers"]["top"] == "intact"
    assert "campus_quad" in state.discovered_locations

    deltas = {
        "clothing": [
        {"type": "slot_state", "character": "player", "slot": "top", "state": "removed"}
        ],
        "discoveries": {
            "locations": ["campus_quad"],
            "zones": ["campus"],
        },
    }

    engine._apply_ai_state_changes(deltas)

    assert state.clothing_states["player"]["layers"]["top"] == "removed"
    assert "campus" in state.discovered_zones
