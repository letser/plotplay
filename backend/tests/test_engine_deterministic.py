"""Tests for deterministic helper methods on the GameEngine."""

import pytest

from tests.conftest_services import engine_fixture  # noqa: F401


def test_purchase_item_success(engine_fixture):
    engine = engine_fixture
    state = engine.state_manager.state
    state.meters["player"]["money"] = 100

    success, message = engine.purchase_item("player", None, "coffee", count=1, price=10)

    assert success is True
    assert "purchase" in message.lower()
    assert state.inventory["player"].get("coffee", 0) == 1
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
    inventory = state.inventory.setdefault("player", {})
    inventory["coffee"] = 2
    state.meters["player"]["money"] = 10

    success, message = engine.sell_item("player", None, "coffee", count=1, price=5)

    assert success is True
    assert "sell" in message.lower()
    assert inventory["coffee"] == 1
    assert state.meters["player"]["money"] == 15


def test_give_item_requires_presence(engine_fixture):
    engine = engine_fixture
    state = engine.state_manager.state
    state.present_chars = ["player", "friend"]
    state.inventory.setdefault("player", {})["coffee"] = 1
    engine.inventory.item_defs["coffee"].can_give = True

    success, message = engine.give_item("player", "friend", "coffee")

    assert success is True
    assert "hand" in message.lower()
    assert state.inventory["player"].get("coffee", 0) == 0
    assert state.inventory["friend"].get("coffee", 0) == 1

    # Remove friend from scene -> expect failure
    state.present_chars = ["player"]
    state.inventory["player"]["coffee"] = 1
    success, message = engine.give_item("player", "friend", "coffee")
    assert success is False
    assert message == "Gift could not be completed."


def test_take_and_drop_item_updates_location(engine_fixture):
    engine = engine_fixture
    state = engine.state_manager.state
    location_id = state.location_current
    state.location_inventory.setdefault(location_id, {})["coffee"] = 2

    success_take, _ = engine.take_item("player", "coffee", count=1)
    assert success_take is True
    assert state.inventory["player"].get("coffee", 0) == 1
    assert state.location_inventory[location_id]["coffee"] == 1

    success_drop, _ = engine.drop_item("player", "coffee", count=1)
    assert success_drop is True
    assert state.inventory["player"].get("coffee", 0) == 0
    assert state.location_inventory[location_id]["coffee"] == 2
