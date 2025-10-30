"""Movement utilities for the PlotPlay engine."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from app.core.conditions import ConditionEvaluator
from app.models.effects import MeterChangeEffect
from app.models.locations import LocationConnection

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine


class MovementService:
    """Handles movement-related logic for the engine."""

    _ACTION_PATTERN = re.compile(r"\b(go|walk|run|head|travel|enter|exit|leave)\b", re.IGNORECASE)

    def __init__(self, engine: "GameEngine") -> None:
        self.engine = engine
        self.logger = engine.logger

    def _sync_presence_after_move(self, companions: list[str] | None = None) -> None:
        """Align present characters with the active node and optional companions."""
        engine = self.engine
        state = engine.state_manager.state
        current_node = engine.get_current_node()

        present: list[str]
        if current_node.characters_present:
            present = [
                char_id
                for char_id in current_node.characters_present
                if char_id == "player" or char_id in engine.characters_map
            ]
        else:
            present = []

        if "player" not in present:
            present.insert(0, "player")

        if companions:
            for companion in companions:
                if companion and companion not in present:
                    present.append(companion)

        state.present_chars = present
        engine._update_npc_presence()

    async def handle_choice(self, choice_id: str) -> dict[str, Any]:
        """Process movement selections coming from predefined choices."""
        engine = self.engine
        state = engine.state_manager.state

        if choice_id.startswith("move_"):
            destination_id = choice_id.removeprefix("move_")
            current_location = engine.get_location(state.location_current)
            if current_location and current_location.connections:
                for connection in current_location.connections:
                    if isinstance(connection.to, str) and connection.to == destination_id:
                        return await self._execute_local_movement(destination_id, connection)
                    if isinstance(connection.to, list) and destination_id in connection.to:
                        return await self._execute_local_movement(destination_id, connection)

        if choice_id.startswith("travel_"):
            destination_zone_id = choice_id.removeprefix("travel_")
            current_zone = engine.zones_map.get(state.zone_current)
            if current_zone and current_zone.connections:
                for connection in current_zone.connections:
                    # Check if destination is in the connection's 'to' list
                    if destination_zone_id in connection.to:
                        # Convert ZoneConnection to dict for compatibility
                        connection_dict = {
                            "to": destination_zone_id,
                            "distance": connection.distance or 1.0
                        }
                        return await self._execute_zone_travel(destination_zone_id, connection_dict)

        return {
            "narrative": "You can't seem to go that way.",
            "choices": engine._generate_choices(engine.get_current_node(), []),
            "current_state": engine._get_state_summary(),
            "action_summary": engine.state_summary.build_action_summary("You attempt to move, but the path is blocked."),
        }

    async def handle_freeform(self, action_text: str) -> dict[str, Any]:
        """Attempt to resolve freeform text as a movement action."""
        engine = self.engine
        current_location = engine.get_location(engine.state_manager.state.location_current)
        if not current_location or not current_location.connections:
            return {
                "narrative": "There's nowhere to go from here.",
                "choices": [],
                "current_state": engine._get_state_summary(),
                "action_summary": engine.state_summary.build_action_summary("You attempt to move, but remain in place."),
            }

        action_lower = action_text.lower()
        for connection in current_location.connections:
            targets = [connection.to] if isinstance(connection.to, str) else connection.to
            for target_id in targets or []:
                if target_id and target_id in engine.state_manager.state.discovered_locations and target_id in action_lower:
                    return await self._execute_local_movement(target_id, connection)

        return {
            "narrative": "You try to move, but there's no clear path forward.",
            "choices": engine._generate_choices(engine.get_current_node(), []),
            "current_state": engine._get_state_summary(),
            "action_summary": engine.state_summary.build_action_summary("You look for a route but stay put."),
        }

    @staticmethod
    def is_movement_action(action_text: str) -> bool:
        return bool(MovementService._ACTION_PATTERN.search(action_text))

    async def _execute_zone_travel(self, destination_zone_id: str, connection: dict) -> dict[str, Any]:
        engine = self.engine
        state = engine.state_manager.state
        move_rules = engine.game_def.movement

        dest_zone = engine.zones_map.get(destination_zone_id)
        if not dest_zone or not dest_zone.locations:
            return {
                "narrative": "That area is not yet accessible.",
                "choices": engine._generate_choices(engine.get_current_node(), []),
                "current_state": engine._get_state_summary(),
            }

        # Determine entry location
        destination_location_id = None

        # Priority 1: use_entry_exit zones with entrances defined
        if move_rules and move_rules.use_entry_exit and dest_zone.entrances:
            destination_location_id = dest_zone.entrances[0]

        # Priority 2: First location in zone
        if not destination_location_id:
            destination_location_id = dest_zone.locations[0].id

        # Zone travel time calculation
        # According to spec: base_time * distance for the travel method
        distance = connection.get("distance", 1.0)

        # Default to 15 minutes if no methods configured
        time_cost_minutes = 15

        if move_rules and move_rules.methods:
            # Use first available method's base_time
            # (Spec allows connections to specify available methods, defaulting to all)
            base_time = move_rules.methods[0].base_time
            time_cost_minutes = int(base_time * distance)

        state.location_previous = state.location_current
        state.zone_current = destination_zone_id
        state.location_current = destination_location_id
        state.location_privacy = engine._get_location_privacy(destination_location_id)

        engine._advance_time(minutes=time_cost_minutes)
        engine._check_and_apply_node_transitions()
        self._sync_presence_after_move()

        new_location = engine.get_location(destination_location_id)
        loc_desc = (
            new_location.description
            if new_location and isinstance(new_location.description, str)
            else "You arrive in a new area."
        )

        final_narrative = f"You travel to {dest_zone.name}.\n\n{loc_desc}"
        self.logger.info(
            "Zone travel to '%s' (entry: %s) completed. Time cost: %sm.",
            destination_zone_id,
            destination_location_id,
            time_cost_minutes,
        )

        return {
            "narrative": final_narrative,
            "choices": engine._generate_choices(engine.get_current_node(), []),
            "current_state": engine._get_state_summary(),
            "action_summary": engine.state_summary.build_action_summary(f"You travel to {dest_zone.name}."),
        }

    async def _execute_local_movement(
        self,
        destination_id: str,
        connection: LocationConnection,
    ) -> dict[str, Any]:
        engine = self.engine
        state = engine.state_manager.state
        evaluator = ConditionEvaluator(state, rng_seed=engine.get_turn_seed())
        move_rules = engine.game_def.movement

        # Check if destination is discovered
        if destination_id not in state.discovered_locations:
            return {
                "narrative": "You haven't discovered that location yet.",
                "choices": engine._generate_choices(engine.get_current_node(), []),
                "current_state": engine._get_state_summary(),
            }

        moving_companions: list[str] = []
        for char_id in state.present_chars:
            if char_id == "player":
                continue

            character_def = engine.characters_map.get(char_id)
            if not character_def or not character_def.movement:
                continue

            is_willing = False
            for rule in character_def.movement.willing_locations:
                if rule.location == destination_id and evaluator.evaluate(rule.when or "always"):
                    is_willing = True
                    break

            if is_willing:
                moving_companions.append(char_id)
            else:
                return {
                    "narrative": f"{character_def.name} seems hesitant. They don't want to go there right now.",
                    "choices": engine._generate_choices(engine.get_current_node(), []),
                    "current_state": engine._get_state_summary(),
                }

        # Calculate time cost for local movement
        # According to spec: base_time is minutes in hybrid/clock modes, actions in slots mode
        time_cost_minutes = 0
        if move_rules and move_rules.base_time:
            time_cost_minutes = move_rules.base_time

        state.location_previous = state.location_current
        state.location_current = destination_id
        state.location_privacy = engine._get_location_privacy(destination_id)

        engine._advance_time(minutes=time_cost_minutes)
        engine._check_and_apply_node_transitions()
        self._sync_presence_after_move(moving_companions)

        new_location = engine.get_location(destination_id)

        # Build concise narrative
        parts = []
        if new_location:
            parts.append(f"You move to the {new_location.name}.")

            # Only add description if it's a real description (not empty/None)
            if new_location.description and isinstance(new_location.description, str) and new_location.description.strip():
                parts.append(new_location.description)

            # Add NPC presence if any (exclude player)
            npc_names = [
                engine.characters_map[cid].name for cid in state.present_chars
                if cid in engine.characters_map and cid != "player"
            ]
            if npc_names:
                parts.append(f"{', '.join(npc_names)} {'is' if len(npc_names) == 1 else 'are'} here.")
        else:
            parts.append("You move.")

        final_narrative = "\n\n".join(parts)

        self.logger.info(
            "Movement from '%s' to '%s' completed. Time cost: %sm.",
            state.location_previous,
            destination_id,
            time_cost_minutes,
        )

        return {
            "narrative": final_narrative,
            "choices": engine._generate_choices(engine.get_current_node(), []),
            "current_state": engine._get_state_summary(),
            "action_summary": engine.state_summary.build_action_summary(f"You move to the {new_location.name if new_location else destination_id}."),
        }

    def move_by_direction(self, direction: str, with_characters: list[str] | None = None) -> bool:
        """Move in a cardinal direction. Returns True if successful."""
        engine = self.engine
        state = engine.state_manager.state
        current_location = engine.get_location(state.location_current)

        if not current_location or not current_location.connections:
            return False

        # Normalize direction
        direction = direction.lower()

        # Find connection matching this direction
        for connection in current_location.connections:
            if hasattr(connection, 'direction') and connection.direction:
                if connection.direction.value == direction or connection.direction.name.lower() == direction:
                    destination_id = connection.to

                    # Check if destination is discovered
                    if destination_id not in state.discovered_locations:
                        return False

                    # Update location
                    state.location_previous = state.location_current
                    state.location_current = destination_id
                    state.location_privacy = engine._get_location_privacy(destination_id)

                    # Advance time
                    move_rules = engine.game_def.movement
                    time_cost = move_rules.base_time if move_rules and move_rules.base_time else 0
                    if time_cost > 0:
                        engine._advance_time(minutes=time_cost)

                    engine._check_and_apply_node_transitions()
                    self._sync_presence_after_move(with_characters)
                    return True

        return False

    def travel_to_zone(
        self,
        zone_id: str | None = None,
        location_id: str | None = None,
        entry_location_id: str | None = None,
        method: str | None = None,
        with_characters: list[str] | None = None
    ) -> bool:
        """Travel to another zone. Returns True if successful.

        Args:
            zone_id: Target zone ID (required if location_id not provided)
            location_id: Specific location ID (alternative to zone_id, deprecated)
            entry_location_id: Specific entry point location (overrides zone default)
            method: Travel method name (e.g., "walk", "bike")
            with_characters: List of character IDs to travel with
        """
        engine = self.engine
        state = engine.state_manager.state
        move_rules = engine.game_def.movement

        # Support legacy location_id parameter
        if location_id and not zone_id:
            target_zone_id = engine.state_manager.index.location_to_zone.get(location_id)
            if not target_zone_id:
                return False
            zone_id = target_zone_id
            if not entry_location_id:
                entry_location_id = location_id

        if not zone_id:
            return False

        target_zone = engine.zones_map.get(zone_id)
        if not target_zone or not target_zone.locations:
            return False

        # Check if it's actually a different zone
        if zone_id == state.zone_current:
            # Same zone, just do local movement if entry_location_id specified
            if entry_location_id:
                state.location_previous = state.location_current
                state.location_current = entry_location_id
                state.location_privacy = engine._get_location_privacy(entry_location_id)
                engine._check_and_apply_node_transitions()
                self._sync_presence_after_move(with_characters)
                return True
            return False

        # Determine entry location
        destination_location_id = None

        # Priority 1: User-specified entry location
        if entry_location_id:
            destination_location_id = entry_location_id

        # Priority 2: use_entry_exit zones with entrances defined
        elif move_rules and move_rules.use_entry_exit and target_zone.entrances:
            # Use first entrance by default
            destination_location_id = target_zone.entrances[0]

        # Priority 3: First location in zone
        if not destination_location_id:
            destination_location_id = target_zone.locations[0].id

        # Verify the destination location exists
        if not engine.get_location(destination_location_id):
            return False

        # Calculate travel time
        current_zone = engine.zones_map.get(state.zone_current)
        if not current_zone:
            return False

        # Find connection and calculate distance
        distance = 1.0
        available_methods = []
        for connection in current_zone.connections:
            if zone_id in connection.to:
                distance = connection.distance or 1.0
                available_methods = connection.methods if connection.methods else []
                break

        # If no connection found, travel is not possible
        if not available_methods and move_rules and move_rules.methods:
            # Use all game methods if connection doesn't restrict
            available_methods = [m.name for m in move_rules.methods]

        # Validate the requested method is available
        if method and available_methods and method not in available_methods:
            return False

        # Calculate time cost
        time_cost_minutes = 15  # Default

        if move_rules and move_rules.methods:
            # If method specified, find it
            if method:
                for travel_method in move_rules.methods:
                    if travel_method.name == method:
                        time_cost_minutes = int(travel_method.base_time * distance)
                        break
            else:
                # Use first available method
                time_cost_minutes = int(move_rules.methods[0].base_time * distance)

        # Execute travel
        state.location_previous = state.location_current
        state.zone_current = zone_id
        state.location_current = destination_location_id
        state.location_privacy = engine._get_location_privacy(destination_location_id)

        engine._advance_time(minutes=time_cost_minutes)
        engine._check_and_apply_node_transitions()
        self._sync_presence_after_move(with_characters)

        self.logger.info(
            "Zone travel from '%s' to '%s' (entry: %s) via '%s'. Time cost: %sm.",
            state.zone_current,
            zone_id,
            destination_location_id,
            method or "default",
            time_cost_minutes,
        )

        return True
