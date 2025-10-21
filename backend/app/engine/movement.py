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

    async def handle_choice(self, choice_id: str) -> dict[str, Any]:
        """Process movement selections coming from predefined choices."""
        engine = self.engine
        state = engine.state_manager.state

        if choice_id.startswith("move_"):
            destination_id = choice_id.removeprefix("move_")
            current_location = engine._get_location(state.location_current)
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
            "choices": engine._generate_choices(engine._get_current_node(), []),
            "current_state": engine._get_state_summary(),
        }

    async def handle_freeform(self, action_text: str) -> dict[str, Any]:
        """Attempt to resolve freeform text as a movement action."""
        engine = self.engine
        current_location = engine._get_location(engine.state_manager.state.location_current)
        if not current_location or not current_location.connections:
            return {
                "narrative": "There's nowhere to go from here.",
                "choices": [],
                "current_state": engine._get_state_summary(),
            }

        action_lower = action_text.lower()
        for connection in current_location.connections:
            targets = [connection.to] if isinstance(connection.to, str) else connection.to
            for target_id in targets or []:
                if target_id and target_id in engine.state_manager.state.discovered_locations and target_id in action_lower:
                    return await self._execute_local_movement(target_id, connection)

        return {
            "narrative": "You try to move, but there's no clear path forward.",
            "choices": engine._generate_choices(engine._get_current_node(), []),
            "current_state": engine._get_state_summary(),
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
                "choices": engine._generate_choices(engine._get_current_node(), []),
                "current_state": engine._get_state_summary(),
            }

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

        state.present_chars = ["player"]
        engine._advance_time(minutes=time_cost_minutes)
        engine._update_npc_presence()

        new_location = engine._get_location(destination_location_id)
        loc_desc = (
            new_location.description
            if new_location and isinstance(new_location.description, str)
            else "You arrive in a new area."
        )

        final_narrative = f"You travel to {dest_zone.name}.\n\n{loc_desc}"
        self.logger.info(
            "Zone travel to '%s' completed. Time cost: %sm.",
            destination_zone_id,
            time_cost_minutes,
        )

        return {
            "narrative": final_narrative,
            "choices": engine._generate_choices(engine._get_current_node(), []),
            "current_state": engine._get_state_summary(),
        }

    async def _execute_local_movement(
        self,
        destination_id: str,
        connection: LocationConnection,
    ) -> dict[str, Any]:
        engine = self.engine
        state = engine.state_manager.state
        evaluator = ConditionEvaluator(state, rng_seed=engine._get_turn_seed())
        move_rules = engine.game_def.movement

        # Check if destination is discovered
        if destination_id not in state.discovered_locations:
            return {
                "narrative": "You haven't discovered that location yet.",
                "choices": engine._generate_choices(engine._get_current_node(), []),
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
                    "choices": engine._generate_choices(engine._get_current_node(), []),
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

        state.present_chars = ["player"] + moving_companions
        engine._advance_time(minutes=time_cost_minutes)
        engine._update_npc_presence()

        new_location = engine._get_location(destination_id)
        loc_desc = (
            new_location.description
            if new_location and isinstance(new_location.description, str)
            else "You arrive."
        )

        npc_names = [
            engine.characters_map[cid].name for cid in state.present_chars if cid in engine.characters_map
        ]
        presence_desc = f"{', '.join(npc_names)} are here." if npc_names else ""

        final_narrative = (
            f"You move to the {new_location.name}.\n\n{loc_desc}\n\n{presence_desc}".strip()
            if new_location
            else "You move."
        )

        self.logger.info(
            "Movement from '%s' to '%s' completed. Time cost: %sm.",
            state.location_previous,
            destination_id,
            time_cost_minutes,
        )

        return {
            "narrative": final_narrative,
            "choices": engine._generate_choices(engine._get_current_node(), []),
            "current_state": engine._get_state_summary(),
        }
