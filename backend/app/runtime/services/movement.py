"""Movement and shop helpers for the new runtime."""

from __future__ import annotations

from typing import List

from app.models.effects import (
    MoveToEffect,
    MoveEffect,
    TravelToEffect,
    LockEffect,
    UnlockEffect,
)
from app.models.locations import LocationConnection, LocalDirection
from app.runtime.session import SessionRuntime


class MovementService:
    """Handles movement, travel, and lock/unlock helpers."""

    def __init__(self, runtime: SessionRuntime) -> None:
        self.runtime = runtime
        self.logger = runtime.logger
        self.index = runtime.index

    # ------------------------------------------------------------------ #
    # Movement APIs
    # ------------------------------------------------------------------ #
    def move_to(self, effect: MoveToEffect) -> bool:
        """Teleport or relocate to a specific location."""
        return self._set_location(effect.location, effect.with_characters)

    def move_relative(self, effect: MoveEffect) -> bool:
        """Follow a directional connection from the current location."""
        state = self.runtime.state_manager.state
        current = self.index.locations.get(state.current_location)
        if not current:
            return False

        evaluator = self.runtime.state_manager.create_evaluator()
        for connection in current.connections or []:
            if self._matches_direction(connection, effect.direction) and evaluator.evaluate_object_conditions(connection):
                target_id = connection.to
                if self._location_available(target_id, evaluator):
                    return self._set_location(target_id, effect.with_characters)
        return False

    def travel(self, effect: TravelToEffect) -> bool:
        """Travel to a location (typically across zones)."""
        return self._set_location(effect.location, effect.with_characters, update_zone=True)

    # ------------------------------------------------------------------ #
    # Locks and unlocks
    # ------------------------------------------------------------------ #
    def apply_lock(self, effect: LockEffect) -> None:
        state = self.runtime.state_manager.state
        for zone_id in effect.zones or []:
            if zone_id in state.zones:
                state.zones[zone_id].locked = True
        for loc_id in effect.locations or []:
            if loc_id in state.locations:
                state.locations[loc_id].locked = True
        for action_id in effect.actions or []:
            if action_id in state.unlocked_actions:
                state.unlocked_actions.remove(action_id)
        for ending_id in effect.endings or []:
            if ending_id in state.unlocked_endings:
                state.unlocked_endings.remove(ending_id)
        for item_id in effect.items or []:
            if item_id in state.unlocked_items:
                state.unlocked_items.remove(item_id)
        for clothing_id in effect.clothing or []:
            if clothing_id in state.unlocked_clothing:
                state.unlocked_clothing.remove(clothing_id)

    def apply_unlock(self, effect: UnlockEffect) -> None:
        state = self.runtime.state_manager.state
        for zone_id in effect.zones or []:
            state.discovered_zones.add(zone_id)
            if zone_id in state.zones:
                state.zones[zone_id].locked = False
        for loc_id in effect.locations or []:
            state.discovered_locations.add(loc_id)
            if loc_id in state.locations:
                state.locations[loc_id].locked = False
        for action_id in (effect.actions or []):
            if action_id not in state.unlocked_actions:
                state.unlocked_actions.append(action_id)
        for ending_id in (effect.endings or []):
            if ending_id not in state.unlocked_endings:
                state.unlocked_endings.append(ending_id)
        for item_id in effect.items or []:
            if item_id not in state.unlocked_items:
                state.unlocked_items.append(item_id)
        for clothing_id in effect.clothing or []:
            if clothing_id not in state.unlocked_clothing:
                state.unlocked_clothing.append(clothing_id)
        if effect.outfit:
            unlocked = state.unlocked_outfits.setdefault(effect.character or "player", [])
            if effect.outfit not in unlocked:
                unlocked.append(effect.outfit)
        for outfit_id in effect.outfits or []:
            unlocked = state.unlocked_outfits.setdefault(effect.character or "player", [])
            if outfit_id not in unlocked:
                unlocked.append(outfit_id)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _set_location(self, location_id: str, companions: list[str] | None, update_zone: bool = False) -> bool:
        state = self.runtime.state_manager.state
        if location_id not in self.index.locations:
            return False

        location_state = state.locations.get(location_id)
        if location_state and getattr(location_state, "locked", False):
            return False

        state.current_location = location_id
        state.current_zone = self.index.location_to_zone.get(location_id, state.current_zone)
        location_def = self.index.locations.get(location_id)
        if location_def:
            state.current_privacy = location_def.privacy

        state.discovered_locations.add(location_id)
        if state.current_zone:
            state.discovered_zones.add(state.current_zone)

        if companions:
            for char_id in companions:
                if char_id not in state.present_characters:
                    state.present_characters.append(char_id)

        return True

    @staticmethod
    def _matches_direction(connection: LocationConnection, direction: LocalDirection) -> bool:
        conn_dir = getattr(connection, "direction", None)
        return bool(conn_dir and conn_dir.value == direction.value)

    def _location_available(self, location_id: str, evaluator) -> bool:
        state = self.runtime.state_manager.state
        location_state = state.locations.get(location_id)
        if location_state and getattr(location_state, "locked", False):
            return False
        if location_state and not location_state.discovered:
            access = getattr(self.index.locations.get(location_id), "access", None)
            condition = getattr(access, "discovered_when", None) if access else None
            if condition and evaluator and evaluator.evaluate(condition):
                state.discovered_locations.add(location_id)
                location_state.discovered = True
            elif not getattr(access, "discovered", True):
                return False
        return True
