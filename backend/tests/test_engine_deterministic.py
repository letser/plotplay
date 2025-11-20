"""Tests for deterministic helper methods on the GameEngine."""

import pytest

from tests.conftest_services import engine_fixture  # noqa: F401
from tests.test_effect_resolver import make_engine
from app.models.modifiers import Modifier


def test_purchase_item_success(engine_fixture):
    engine = engine_fixture
    state = engine.state_manager.state
    state.meters["player"]["money"] = 100

    success, message = engine.purchase_item("player", None, "coffee", count=1, price=10)

    assert success is True
    assert "purchase" in message.lower()
    player_items = state.characters["player"].inventory.items
    assert player_items.get("coffee", 0) == 1
    assert state.meters["player"]["money"] == 90


def test_purchase_item_insufficient_funds(engine_fixture):
    engine = engine_fixture
    state = engine.state_manager.state
    state.meters["player"]["money"] = 1

    success, message = engine.purchase_item("player", None, "coffee", count=1, price=50)

    assert success is False
    assert message == "Purchase could not be completed."


def test_sell_item_transfers_money(engine_fixture):
    engine = engine_fixture
    state = engine.state_manager.state
    player_inventory = state.characters["player"].inventory.items
    player_inventory["coffee"] = 2
    state.meters["player"]["money"] = 10

    success, message = engine.sell_item("player", None, "coffee", count=1, price=5)

    assert success is True
    assert "sell" in message.lower()
    assert player_inventory["coffee"] == 1
    assert state.meters["player"]["money"] == 15


def test_give_item_requires_presence(engine_fixture):
    engine = engine_fixture
    state = engine.state_manager.state
    state.present_characters = ["player", "friend"]
    state.characters["player"].inventory.items["coffee"] = 1
    engine.inventory.item_defs["coffee"].can_give = True

    success, message = engine.give_item("player", "friend", "coffee")

    assert success is True
    assert "hand" in message.lower()
    assert state.characters["player"].inventory.items.get("coffee", 0) == 0
    assert state.characters["friend"].inventory.items.get("coffee", 0) == 1

    # Remove friend from scene -> expect failure
    state.present_characters = ["player"]
    state.characters["player"].inventory.items["coffee"] = 1
    success, message = engine.give_item("player", "friend", "coffee")
    assert success is False
    assert message == "Gift could not be completed."


def test_take_and_drop_item_updates_location(engine_fixture):
    engine = engine_fixture
    state = engine.state_manager.state
    location_id = state.current_location
    location_inventory = state.locations[location_id].inventory.items
    location_inventory["coffee"] = 2

    success_take, _ = engine.take_item("player", "coffee", count=1)
    assert success_take is True
    assert state.characters["player"].inventory.items.get("coffee", 0) == 1
    assert location_inventory["coffee"] == 1

    success_drop, _ = engine.drop_item("player", "coffee", count=1)
    assert success_drop is True
    assert state.characters["player"].inventory.items.get("coffee", 0) == 0
    assert location_inventory["coffee"] == 2


def test_visit_cap_limits_minutes(tmp_path, monkeypatch, mock_ai_service):
    engine = make_engine(tmp_path, monkeypatch, mock_ai_service)
    state = engine.state_manager.state
    node = engine.get_current_node()

    state.current_visit_node = node.id
    state.current_visit_minutes = 28
    engine.game_def.time.defaults.cap_per_visit = 30

    minutes = engine._calculate_time_minutes(
        category="trivial",
        node=node,
        explicit_minutes=None,
        apply_visit_cap=True,
        method_active=True,
    )
    assert minutes == 2

    minutes_again = engine._calculate_time_minutes(
        category="trivial",
        node=node,
        explicit_minutes=None,
        apply_visit_cap=True,
        method_active=True,
    )
    assert minutes_again == 0


def test_time_multiplier_applies_to_active_actions(tmp_path, monkeypatch, mock_ai_service):
    engine = make_engine(tmp_path, monkeypatch, mock_ai_service)
    state = engine.state_manager.state

    if not hasattr(state, "modifiers"):
        state.modifiers = {}
    state.modifiers["player"] = [{"id": "speedy"}]
    engine.modifiers.library["speedy"] = Modifier(id="speedy", time_multiplier=0.5)

    minutes = engine._calculate_time_minutes(
        category="standard",
        node=engine.get_current_node(),
        explicit_minutes=None,
        apply_visit_cap=False,
        method_active=True,
    )
    assert minutes == 8

    passive_minutes = engine._calculate_time_minutes(
        category="standard",
        node=engine.get_current_node(),
        explicit_minutes=None,
        apply_visit_cap=False,
        method_active=False,
    )
    assert passive_minutes == 15
