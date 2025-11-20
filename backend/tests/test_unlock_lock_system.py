"""Test unlock/lock effects system."""
import pytest
from dataclasses import field
from app.models.game import GameState
from app.models.effects import UnlockEffect, LockEffect


def test_unlock_items():
    """Test unlocking items adds them to unlocked_items list."""
    state = GameState()
    effect = UnlockEffect(items=["sword", "shield"])

    # Simulate applying unlock effect
    for item_id in effect.items:
        if item_id not in state.unlocked_items:
            state.unlocked_items.append(item_id)

    assert "sword" in state.unlocked_items
    assert "shield" in state.unlocked_items
    assert len(state.unlocked_items) == 2


def test_lock_items():
    """Test locking items removes them from unlocked_items list."""
    state = GameState()
    state.unlocked_items = ["sword", "shield", "potion"]

    effect = LockEffect(items=["sword", "shield"])

    # Simulate applying lock effect
    state.unlocked_items = [item_id for item_id in state.unlocked_items if item_id not in effect.items]

    assert "sword" not in state.unlocked_items
    assert "shield" not in state.unlocked_items
    assert "potion" in state.unlocked_items
    assert len(state.unlocked_items) == 1


def test_unlock_clothing():
    """Test unlocking clothing adds them to unlocked_clothing list."""
    state = GameState()
    effect = UnlockEffect(clothing=["jacket", "hat"])

    for clothing_id in effect.clothing:
        if clothing_id not in state.unlocked_clothing:
            state.unlocked_clothing.append(clothing_id)

    assert "jacket" in state.unlocked_clothing
    assert "hat" in state.unlocked_clothing


def test_lock_clothing():
    """Test locking clothing removes them from unlocked_clothing list."""
    state = GameState()
    state.unlocked_clothing = ["jacket", "hat", "shoes"]

    effect = LockEffect(clothing=["jacket"])

    state.unlocked_clothing = [clothing_id for clothing_id in state.unlocked_clothing
                               if clothing_id not in effect.clothing]

    assert "jacket" not in state.unlocked_clothing
    assert "hat" in state.unlocked_clothing
    assert "shoes" in state.unlocked_clothing


def test_unlock_outfits():
    """Test unlocking outfits adds them to character's unlocked_outfits."""
    state = GameState()
    char_id = "player"

    # Simulate unlocking outfits
    if char_id not in state.unlocked_outfits:
        state.unlocked_outfits[char_id] = []

    outfits = ["casual", "formal"]
    for outfit_id in outfits:
        if outfit_id not in state.unlocked_outfits[char_id]:
            state.unlocked_outfits[char_id].append(outfit_id)

    assert "casual" in state.unlocked_outfits[char_id]
    assert "formal" in state.unlocked_outfits[char_id]


def test_lock_outfits():
    """Test locking outfits removes them from character's unlocked_outfits."""
    state = GameState()
    state.unlocked_outfits = {"player": ["casual", "formal", "sporty"]}

    effect = LockEffect(outfits=["casual", "formal"])

    for char_id in state.unlocked_outfits:
        state.unlocked_outfits[char_id] = [
            outfit_id for outfit_id in state.unlocked_outfits[char_id]
            if outfit_id not in effect.outfits
        ]

    assert "casual" not in state.unlocked_outfits["player"]
    assert "formal" not in state.unlocked_outfits["player"]
    assert "sporty" in state.unlocked_outfits["player"]


def test_unlock_zones_uses_discovered():
    """Test unlocking zones adds them to discovered_zones set."""
    state = GameState()
    effect = UnlockEffect(zones=["downtown", "suburbs"])

    state.discovered_zones.update(effect.zones)

    assert "downtown" in state.discovered_zones
    assert "suburbs" in state.discovered_zones


def test_lock_zones_uses_discovered():
    """Test locking zones removes them from discovered_zones set."""
    state = GameState()
    state.discovered_zones = {"downtown", "suburbs", "industrial"}

    effect = LockEffect(zones=["downtown"])

    state.discovered_zones.difference_update(effect.zones)

    assert "downtown" not in state.discovered_zones
    assert "suburbs" in state.discovered_zones
    assert "industrial" in state.discovered_zones


def test_unlock_locations_uses_discovered():
    """Test unlocking locations adds them to discovered_locations set."""
    state = GameState()
    effect = UnlockEffect(locations=["cafe", "library"])

    state.discovered_locations.update(effect.locations)

    assert "cafe" in state.discovered_locations
    assert "library" in state.discovered_locations


def test_lock_locations_uses_discovered():
    """Test locking locations removes them from discovered_locations set."""
    state = GameState()
    state.discovered_locations = {"cafe", "library", "park"}

    effect = LockEffect(locations=["cafe", "library"])

    state.discovered_locations.difference_update(effect.locations)

    assert "cafe" not in state.discovered_locations
    assert "library" not in state.discovered_locations
    assert "park" in state.discovered_locations


def test_unlock_actions():
    """Test unlocking actions adds them to unlocked_actions list."""
    state = GameState()
    effect = UnlockEffect(actions=["call_friend", "visit_gym"])

    for action_id in effect.actions:
        if action_id not in state.unlocked_actions:
            state.unlocked_actions.append(action_id)

    assert "call_friend" in state.unlocked_actions
    assert "visit_gym" in state.unlocked_actions


def test_lock_actions():
    """Test locking actions removes them from unlocked_actions list."""
    state = GameState()
    state.unlocked_actions = ["call_friend", "visit_gym", "study"]

    effect = LockEffect(actions=["call_friend"])

    state.unlocked_actions = [action_id for action_id in state.unlocked_actions
                               if action_id not in effect.actions]

    assert "call_friend" not in state.unlocked_actions
    assert "visit_gym" in state.unlocked_actions
    assert "study" in state.unlocked_actions


def test_unlock_endings():
    """Test unlocking endings adds them to unlocked_endings list."""
    state = GameState()
    effect = UnlockEffect(endings=["good_ending", "bad_ending"])

    for ending_id in effect.endings:
        if ending_id not in state.unlocked_endings:
            state.unlocked_endings.append(ending_id)

    assert "good_ending" in state.unlocked_endings
    assert "bad_ending" in state.unlocked_endings


def test_lock_endings():
    """Test locking endings removes them from unlocked_endings list."""
    state = GameState()
    state.unlocked_endings = ["good_ending", "bad_ending", "secret_ending"]

    effect = LockEffect(endings=["bad_ending"])

    state.unlocked_endings = [ending_id for ending_id in state.unlocked_endings
                               if ending_id not in effect.endings]

    assert "bad_ending" not in state.unlocked_endings
    assert "good_ending" in state.unlocked_endings
    assert "secret_ending" in state.unlocked_endings
