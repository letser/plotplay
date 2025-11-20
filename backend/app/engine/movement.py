"""Movement utilities for the PlotPlay engine."""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING, Any

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

        state.present_characters = present
        engine._update_npc_presence()

    async def move_local(self, destination_id: str) -> bool:
        """Move to a specific location within the current zone."""
        state = self.engine.state_manager.state
        current_location = self.engine.get_location(state.current_location)
        if not current_location or not current_location.connections:
            return False

        for connection in current_location.connections:
            targets = [connection.to] if isinstance(connection.to, str) else (connection.to or [])
            if destination_id in targets:
                result = self._execute_local_movement(destination_id, connection)
                return "action_summary" in result
        return False

    async def move_zone(self, zone_id: str, method: str | None = None, entry_location_id: str | None = None) -> bool:
        """Travel to another zone using the provided method."""
        return self.travel_to_zone(zone_id=zone_id, entry_location_id=entry_location_id, method=method)

    async def handle_choice(self, choice_id: str) -> dict[str, Any]:
        """Process movement selections coming from predefined choices."""
        engine = self.engine
        state = engine.state_manager.state

        if choice_id.startswith("move_"):
            destination_id = choice_id.removeprefix("move_")
            current_location = engine.get_location(state.current_location)
            if current_location and current_location.connections:
                for connection in current_location.connections:
                    targets = [connection.to] if isinstance(connection.to, str) else (connection.to or [])
                    if destination_id in targets:
                        return self._execute_local_movement(destination_id, connection)

        if choice_id.startswith("travel_"):
            destination_zone_id = choice_id.removeprefix("travel_")
            current_zone = engine.zones_map.get(state.current_zone)
            if current_zone and current_zone.connections:
                for connection in current_zone.connections:
                    if destination_zone_id in connection.to:
                        return await self._execute_zone_travel(destination_zone_id, None)

        return {
            "narrative": "You can't seem to go that way.",
            "choices": engine._generate_choices(engine.get_current_node(), []),
            "current_state": engine.get_state_summary(),
            "action_summary": engine.state_summary.build_action_summary("You attempt to move, but the path is blocked."),
        }

    async def handle_freeform(self, action_text: str) -> dict[str, Any]:
        """Attempt to resolve freeform text as a movement action."""
        engine = self.engine
        current_location = engine.get_location(engine.state_manager.state.current_location)
        if not current_location or not current_location.connections:
            return {
                "narrative": "There's nowhere to go from here.",
                "choices": [],
                "current_state": engine.get_state_summary(),
                "action_summary": engine.state_summary.build_action_summary("You attempt to move, but remain in place."),
            }

        action_lower = action_text.lower()
        for connection in current_location.connections:
            targets = [connection.to] if isinstance(connection.to, str) else connection.to
            for target_id in targets or []:
                if target_id and target_id in engine.state_manager.state.discovered_locations and target_id in action_lower:
                    return self._execute_local_movement(target_id, connection)

        return {
            "narrative": "You try to move, but there's no clear path forward.",
            "choices": engine._generate_choices(engine.get_current_node(), []),
            "current_state": engine.get_state_summary(),
            "action_summary": engine.state_summary.build_action_summary("You look for a route but stay put."),
        }

    @staticmethod
    def is_movement_action(action_text: str) -> bool:
        return bool(MovementService._ACTION_PATTERN.search(action_text))

    async def _execute_zone_travel(self, destination_zone_id: str, connection: dict | None = None) -> dict[str, Any]:
        engine = self.engine
        state = engine.state_manager.state

        if not self.travel_to_zone(zone_id=destination_zone_id):
            return {
                "narrative": "You can't find a way to travel there right now.",
                "choices": engine._generate_choices(engine.get_current_node(), []),
                "current_state": engine.get_state_summary(),
            }

        dest_zone = engine.zones_map.get(state.current_zone)
        new_location = engine.get_location(state.current_location)
        loc_desc = (
            new_location.description
            if new_location and isinstance(new_location.description, str)
            else "You arrive in a new area."
        )

        final_narrative = f"You travel to {dest_zone.name if dest_zone else destination_zone_id}.\n\n{loc_desc}"

        return {
            "narrative": final_narrative,
            "choices": engine._generate_choices(engine.get_current_node(), []),
            "current_state": engine.get_state_summary(),
            "action_summary": engine.state_summary.build_action_summary(
                f"You travel to {dest_zone.name if dest_zone else destination_zone_id}."
            ),
        }

    def _execute_local_movement(
        self,
        destination_id: str,
        connection: LocationConnection,
        extra_companions: list[str] | None = None,
    ) -> dict[str, Any]:
        engine = self.engine
        state = engine.state_manager.state
        evaluator = engine.state_manager.create_evaluator()
        # Check if destination is discovered
        if destination_id not in state.discovered_locations:
            return {
                "narrative": "You haven't discovered that location yet.",
                "choices": engine._generate_choices(engine.get_current_node(), []),
                "current_state": engine.get_state_summary(),
            }

        moving_companions: list[str] = []
        for char_id in state.present_characters:
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
                    "current_state": engine.get_state_summary(),
                }

        # Calculate time cost for local movement
        zone = engine.zones_map.get(state.current_zone)
        explicit_minutes = getattr(zone, "time_cost", None) if zone else None
        category = getattr(zone, "time_category", None) if zone else None
        if explicit_minutes is None and not category:
            category = engine.game_def.time.defaults.movement

        time_cost_minutes = engine._calculate_time_minutes(
            category=category,
            node=engine.get_current_node(),
            explicit_minutes=explicit_minutes,
            apply_visit_cap=False,
            method_active=True,
        )

        state.location_previous = state.current_location
        state.current_location = destination_id
        state.location_privacy = engine._get_location_privacy(destination_id)

        engine._apply_time_minutes(time_cost_minutes)
        engine.check_and_apply_node_transitions()
        if extra_companions:
            for companion in extra_companions:
                if companion and companion not in moving_companions:
                    moving_companions.append(companion)

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
                engine.characters_map[cid].name for cid in state.present_characters
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
            "current_state": engine.get_state_summary(),
            "action_summary": engine.state_summary.build_action_summary(f"You move to the {new_location.name if new_location else destination_id}."),
        }

    def move_by_direction(self, direction: str, with_characters: list[str] | None = None) -> bool:
        """Move in a cardinal direction. Returns True if successful."""
        engine = self.engine
        state = engine.state_manager.state
        current_location = engine.get_location(state.current_location)

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

                    result = self._execute_local_movement(destination_id, connection, extra_companions=with_characters)
                    return "action_summary" in result

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
        if zone_id == state.current_zone:
            # Same zone, just do local movement if entry_location_id specified
            if entry_location_id:
                state.location_previous = state.current_location
                state.current_location = entry_location_id
                state.location_privacy = engine._get_location_privacy(entry_location_id)
                engine.check_and_apply_node_transitions()
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
        current_zone = engine.zones_map.get(state.current_zone)
        if not current_zone:
            return False

        previous_zone = state.current_zone

        # Find connection and calculate distance/methods
        distance = 1.0
        connection_methods: list[str] = []
        if current_zone and current_zone.connections:
            for connection in current_zone.connections:
                targets = connection.to or []
                reachable = False
                if "all" in targets:
                    exceptions = connection.exceptions or []
                    reachable = zone_id not in exceptions
                else:
                    reachable = zone_id in targets

                if reachable:
                    distance = connection.distance or 1.0
                    connection_methods = connection.methods or []
                    break

        method_defs = {
            travel_method.name: travel_method
            for travel_method in (move_rules.methods if move_rules else [])
        }

        candidate_methods = [m for m in connection_methods if m in method_defs]
        if not candidate_methods and not connection_methods:
            candidate_methods = list(method_defs.keys())

        chosen_method = None
        if method:
            if candidate_methods and method not in candidate_methods:
                return False
            chosen_method = method_defs.get(method)
            if not chosen_method:
                return False
        elif candidate_methods:
            chosen_method = method_defs.get(candidate_methods[0])

        method_active = True
        explicit_minutes: int | None = None
        if chosen_method:
            method_active = chosen_method.active
            if chosen_method.time_cost is not None:
                explicit_minutes = int(chosen_method.time_cost * distance)
            elif chosen_method.speed is not None:
                explicit_minutes = math.ceil((distance / chosen_method.speed) * 60)
            elif chosen_method.category:
                per_unit = self.engine._category_to_minutes(chosen_method.category)
                explicit_minutes = int(per_unit * distance)
        else:
            default_category = self.engine.game_def.time.defaults.movement
            per_unit = self.engine._category_to_minutes(default_category)
            explicit_minutes = int(per_unit * distance)

        time_cost_minutes = self.engine._calculate_time_minutes(
            category=None,
            node=self.engine.get_current_node(),
            explicit_minutes=explicit_minutes,
            apply_visit_cap=False,
            method_active=method_active,
        )

        # Execute travel
        state.location_previous = state.current_location
        state.current_zone = zone_id
        state.current_location = destination_location_id
        state.location_privacy = engine._get_location_privacy(destination_location_id)

        engine._apply_time_minutes(time_cost_minutes)
        engine.check_and_apply_node_transitions()
        self._sync_presence_after_move(with_characters)

        self.logger.info(
            "Zone travel from '%s' to '%s' (entry: %s) via '%s'. Time cost: %sm.",
            previous_zone,
            zone_id,
            destination_location_id,
            method or (chosen_method.name if chosen_method else "default"),
            time_cost_minutes,
        )

        return True
