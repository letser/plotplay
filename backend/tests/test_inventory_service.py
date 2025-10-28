"""Tests for InventoryService (migrated from InventoryManager)."""

import pytest
from tests.conftest_services import engine_fixture
from app.engine.inventory import InventoryService
from app.models.effects import InventoryChangeEffect


def test_inventory_service_initialization(engine_fixture):
    """Test that InventoryService initializes correctly."""
    inventory = engine_fixture.inventory

    assert isinstance(inventory, InventoryService)
    assert inventory.engine == engine_fixture
    assert inventory.game_def == engine_fixture.game_def
    # Coffee shop game has items
    assert len(inventory.item_defs) > 0


def test_apply_effect_adds_item(engine_fixture):
    """Test adding items to inventory."""
    inventory = engine_fixture.inventory
    state = engine_fixture.state_manager.state

    # Get first item from game
    first_item_id = list(inventory.item_defs.keys())[0]

    # Initially empty or has some amount
    initial_count = state.inventory.get("player", {}).get(first_item_id, 0)

    # Add 3 items
    effect = InventoryChangeEffect(
        type="inventory_add",
        owner="player",
        item=first_item_id,
        count=3
    )
    inventory.apply_effect(effect)

    assert state.inventory["player"][first_item_id] == initial_count + 3


def test_apply_effect_removes_item(engine_fixture):
    """Test removing items from inventory."""
    inventory = engine_fixture.inventory
    state = engine_fixture.state_manager.state

    # Get first item
    first_item_id = list(inventory.item_defs.keys())[0]

    # Add 5 items first
    state.inventory["player"] = {first_item_id: 5}

    # Remove 2
    effect = InventoryChangeEffect(
        type="inventory_remove",
        owner="player",
        item=first_item_id,
        count=2
    )
    inventory.apply_effect(effect)

    assert state.inventory["player"][first_item_id] == 3


def test_apply_effect_prevents_negative_count(engine_fixture):
    """Test that item count cannot go negative."""
    inventory = engine_fixture.inventory
    state = engine_fixture.state_manager.state

    first_item_id = list(inventory.item_defs.keys())[0]

    # Start with 2 items
    state.inventory["player"] = {first_item_id: 2}

    # Try to remove 5 (should clamp to 0)
    effect = InventoryChangeEffect(
        type="inventory_remove",
        owner="player",
        item=first_item_id,
        count=5
    )
    inventory.apply_effect(effect)

    assert state.inventory["player"][first_item_id] == 0


def test_apply_effect_ignores_invalid_item(engine_fixture):
    """Test that invalid item IDs are ignored."""
    inventory = engine_fixture.inventory
    state = engine_fixture.state_manager.state

    # Try to add non-existent item
    effect = InventoryChangeEffect(
        type="inventory_add",
        owner="player",
        item="nonexistent_item_xyz",
        count=1
    )
    inventory.apply_effect(effect)

    # Should not crash, inventory should not have invalid item
    assert state.inventory.get("player", {}).get("nonexistent_item_xyz", 0) == 0


def test_apply_effect_ignores_invalid_owner(engine_fixture):
    """Test that invalid owner IDs are ignored."""
    inventory = engine_fixture.inventory
    state = engine_fixture.state_manager.state

    first_item_id = list(inventory.item_defs.keys())[0]

    # Try to add item to non-existent character
    effect = InventoryChangeEffect(
        type="inventory_add",
        owner="nonexistent_character_xyz",
        item=first_item_id,
        count=1
    )
    inventory.apply_effect(effect)

    # Should not crash, no inventory created
    assert "nonexistent_character_xyz" not in state.inventory


def test_use_item_with_no_inventory(engine_fixture):
    """Test using item when player has none."""
    inventory = engine_fixture.inventory

    first_item_id = list(inventory.item_defs.keys())[0]

    # Player has no items of this type
    effects = inventory.use_item("player", first_item_id)

    # Should return empty list
    assert effects == []


def test_use_item_with_zero_count(engine_fixture):
    """Test using item when count is 0."""
    inventory = engine_fixture.inventory
    state = engine_fixture.state_manager.state

    first_item_id = list(inventory.item_defs.keys())[0]

    # Player has 0 items
    state.inventory["player"] = {first_item_id: 0}

    effects = inventory.use_item("player", first_item_id)

    # Should return empty list
    assert effects == []


def test_use_item_nonexistent_item(engine_fixture):
    """Test using an item that doesn't exist."""
    inventory = engine_fixture.inventory

    effects = inventory.use_item("player", "nonexistent_item_xyz")

    # Should return empty list
    assert effects == []


def test_stackable_items_accumulate(engine_fixture):
    """Test that stackable items accumulate correctly."""
    inventory = engine_fixture.inventory
    state = engine_fixture.state_manager.state

    # Find a stackable item
    stackable_item_id = None
    for item_id, item_def in inventory.item_defs.items():
        if item_def.stackable:
            stackable_item_id = item_id
            break

    if not stackable_item_id:
        pytest.skip("No stackable items in test game")

    # Add 3 items
    inventory.apply_effect(
        InventoryChangeEffect(type="inventory_add", owner="player", item=stackable_item_id, count=3)
    )

    # Add 2 more items
    inventory.apply_effect(
        InventoryChangeEffect(type="inventory_add", owner="player", item=stackable_item_id, count=2)
    )

    assert state.inventory["player"][stackable_item_id] == 5


def test_nonstackable_items_dont_exceed_one(engine_fixture):
    """Test that non-stackable items never exceed count of 1."""
    inventory = engine_fixture.inventory
    state = engine_fixture.state_manager.state

    # Find a non-stackable item
    nonstackable_item_id = None
    for item_id, item_def in inventory.item_defs.items():
        if not item_def.stackable:
            nonstackable_item_id = item_id
            break

    if not nonstackable_item_id:
        pytest.skip("No non-stackable items in test game")

    # Add an item
    inventory.apply_effect(
        InventoryChangeEffect(type="inventory_add", owner="player", item=nonstackable_item_id, count=1)
    )

    # Try to add another (should stay at 1)
    inventory.apply_effect(
        InventoryChangeEffect(type="inventory_add", owner="player", item=nonstackable_item_id, count=1)
    )

    assert state.inventory["player"][nonstackable_item_id] == 1
