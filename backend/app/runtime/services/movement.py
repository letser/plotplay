"""Movement and shop helpers for the new runtime."""

from __future__ import annotations

import math
from typing import List, Optional

from app.models.effects import (
    LockEffect,
    MoveEffect,
    MoveToEffect,
    TravelToEffect,
    UnlockEffect,
)
from app.models.locations import LocationConnection, LocalDirection, ZoneConnection
from app.runtime.session import SessionRuntime


class MovementService:
    """Handles movement, travel, and lock/unlock helpers."""

    def __init__(self, runtime: SessionRuntime) -> None:
        self.runtime = runtime
        self.logger = runtime.logger
        self.index = runtime.index
        self.evaluator = runtime.state_manager.create_evaluator

    # ------------------------------------------------------------------ #
    # Movement APIs
    # ------------------------------------------------------------------ #
    def move_to(self, effect: MoveToEffect) -> bool:
        """Teleport or relocate to a specific location."""
        moved = self._set_location(effect.location, effect.with_characters, is_travel=False)
        if moved:
            self._record_time_cost(self._calculate_local_minutes(effect.location), apply_cap=False)
        return moved

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
                    moved = self._set_location(target_id, effect.with_characters, is_travel=False)
                    if moved:
                        self._record_time_cost(self._calculate_local_minutes(target_id), apply_cap=False)
                    return moved
        return False

    def travel(self, effect: TravelToEffect) -> bool:
        """Travel to a location (typically across zones)."""
        minutes = self._calculate_travel_minutes(effect.location, effect.method)
        if minutes is None:
            return False
        moved = self._set_location(effect.location, effect.with_characters, is_travel=True, update_zone=True, method=effect.method)
        if moved:
            self._record_time_cost(minutes, apply_cap=False)
        return moved

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
    def _set_location(self, location_id: str, companions: list[str] | None, *, is_travel: bool, update_zone: bool = False, method: str | None = None) -> bool:
        state = self.runtime.state_manager.state
        if location_id not in self.index.locations:
            return False

        evaluator = self.evaluator()
        if not self._companions_allowed(companions, location_id, evaluator):
            return False

        zone_id = self.index.location_to_zone.get(location_id)
        if not self._zone_access_allowed(zone_id, evaluator):
            return False

        location_state = state.locations.get(location_id)
        if location_state and getattr(location_state, "locked", False):
            return False
        location_def = self.index.locations.get(location_id)
        if not self._location_access_allowed(location_def, evaluator):
            return False

        # Enforce entry/exit lists when changing zones
        if is_travel and getattr(self.runtime.game.movement, "use_entry_exit", False):
            origin_zone = self.index.zones.get(state.current_zone) if state.current_zone else None
            dest_zone = self.index.zones.get(zone_id) if zone_id else None
            if origin_zone and origin_zone.exits and state.current_location not in origin_zone.exits:
                return False
            if dest_zone and dest_zone.entrances and location_def and location_def.id not in dest_zone.entrances:
                return False

        state.current_location = location_id
        state.current_zone = zone_id or state.current_zone
        if location_def:
            state.current_privacy = location_def.privacy

        state.discovered_locations.add(location_id)
        if location_state:
            location_state.discovered = True
        if state.current_zone:
            state.discovered_zones.add(state.current_zone)
            zone_state = state.zones.get(state.current_zone)
            if zone_state:
                zone_state.discovered = True

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
        location_def = self.index.locations.get(location_id)
        if not self._location_access_allowed(location_def, evaluator):
            return False
        if location_state and not location_state.discovered:
            access = getattr(location_def, "access", None)
            condition = getattr(access, "discovered_when", None) if access else None
            if condition and evaluator and evaluator.evaluate(condition):
                state.discovered_locations.add(location_id)
                location_state.discovered = True
            elif not getattr(access, "discovered", True):
                return False
        zone_id = self.index.location_to_zone.get(location_id)
        if not self._zone_access_allowed(zone_id, evaluator):
            return False
        return True

    # ------------------------------------------------------------------ #
    # Time helpers
    # ------------------------------------------------------------------ #
    def _record_time_cost(self, minutes: Optional[int], apply_cap: bool) -> None:
        """Record an explicit time cost onto the current turn context."""
        if minutes is None or minutes <= 0:
            return
        ctx = getattr(self.runtime, "current_context", None)
        if not ctx:
            return
        ctx.time_explicit_minutes = (ctx.time_explicit_minutes or 0) + minutes
        ctx.time_apply_visit_cap = ctx.time_apply_visit_cap and apply_cap

    def _minutes_for_category(self, category: str | None) -> int:
        categories = self.runtime.game.time.categories or {}
        defaults = self.runtime.game.time.defaults
        resolved = category or defaults.movement
        if resolved in categories:
            return int(categories[resolved])
        return int(categories.get(defaults.movement, categories.get(defaults.default, 0)))

    def _calculate_local_minutes(self, target_location: str) -> int:
        """Resolve time for moving within the current zone."""
        state = self.runtime.state_manager.state
        zone = self.index.zones.get(self.index.location_to_zone.get(target_location) or state.current_zone)
        if zone:
            if zone.time_cost is not None:
                return max(0, int(zone.time_cost))
            if zone.time_category:
                return max(0, self._minutes_for_category(zone.time_category))
        return max(0, self._minutes_for_category(None))

    def _calculate_travel_minutes(self, target_location: str, method_name: str | None) -> Optional[int]:
        """Resolve zone-travel time using movement methods and zone distance."""
        state = self.runtime.state_manager.state
        from_zone = state.current_zone
        to_zone = self.index.location_to_zone.get(target_location)
        if not from_zone or not to_zone:
            return None

        connection = self._resolve_zone_connection(from_zone, to_zone)
        if from_zone != to_zone and not connection:
            return None
        distance = connection.distance if connection and connection.distance is not None else 1.0

        movement_cfg = getattr(self.runtime.game, "movement", None)
        methods = {m.name: m for m in getattr(movement_cfg, "methods", [])} if movement_cfg else {}
        chosen = methods.get(method_name or "walk") or next(iter(methods.values()), None)
        if not chosen or getattr(chosen, "active", True) is False:
            return None
        if connection and connection.methods:
            if chosen.name not in connection.methods:
                return None

        minutes: float = 0
        if chosen.time_cost is not None:
            minutes = distance * chosen.time_cost
        elif chosen.speed is not None:
            minutes = (distance / chosen.speed) * 60.0
        elif chosen.category:
            minutes = distance * self._minutes_for_category(chosen.category)
        return max(0, int(math.floor(minutes + 0.5)))

    def _resolve_zone_connection(self, from_zone: str, to_zone: str) -> Optional[ZoneConnection]:
        zone_def = self.index.zones.get(from_zone)
        if not zone_def:
            return None
        for conn in zone_def.connections or []:
            if to_zone in (conn.to or []):
                if conn.exceptions and to_zone in conn.exceptions:
                    continue
                return conn
        return None

    def _zone_access_allowed(self, zone_id: str | None, evaluator) -> bool:
        if not zone_id:
            return True
        state = self.runtime.state_manager.state
        zone_state = state.zones.get(zone_id)
        if zone_state and getattr(zone_state, "locked", False):
            return False
        zone_def = self.index.zones.get(zone_id)
        access = getattr(zone_def, "access", None) if zone_def else None
        if access and not evaluator.evaluate_object_conditions(access):
            return False
        return True

    def _location_access_allowed(self, location_def, evaluator) -> bool:
        if not location_def:
            return False
        access = getattr(location_def, "access", None)
        if access and not evaluator.evaluate_object_conditions(access):
            return False
        return True

    def _companions_allowed(self, companions: list[str] | None, destination: str, evaluator) -> bool:
        if not companions:
            return True
        dest_zone = self.index.location_to_zone.get(destination)
        for char_id in companions:
            char_def = self.index.characters.get(char_id)
            willingness = getattr(char_def, "movement", None) if char_def else None
            if not willingness:
                continue
            allowed = False
            for wl in willingness.willing_locations or []:
                if wl.location == destination and evaluator.evaluate_object_conditions(wl):
                    allowed = True
                    break
            if not allowed and dest_zone:
                for wz in willingness.willing_zones or []:
                    if wz.zone == dest_zone and evaluator.evaluate_object_conditions(wz):
                        allowed = True
                        break
            if not allowed:
                return False
        return True
