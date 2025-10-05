# backend/app/core/game_engine.py
from typing import Any, Literal, cast
import json
import re
import random

from app.core.clothing_manager import ClothingManager
from app.core.conditions import ConditionEvaluator
from app.core.event_manager import EventManager
from app.core.arc_manager import ArcManager
from app.core.modifier_manager import ModifierManager
from app.core.inventory_manager import InventoryManager
from app.core.state_manager import StateManager
from app.models.action import GameAction
from app.models.character import Character
from app.models.effects import (
    AnyEffect, MeterChangeEffect, FlagSetEffect, GotoNodeEffect,
    ApplyModifierEffect, RemoveModifierEffect, InventoryChangeEffect,
    ClothingChangeEffect, MoveToEffect, UnlockEffect, ConditionalEffect, RandomEffect,
    AdvanceTimeEffect # <-- IMPORTED
)
from app.models.enums import NodeType
from app.models.game import GameDefinition
from app.models.location import Location, LocationConnection, LocationPrivacy
from app.models.node import Node, Choice
from app.services.ai_service import AIService
from app.services.prompt_builder import PromptBuilder
from app.core.logger import setup_session_logger


class GameEngine:
    def __init__(self, game_def: GameDefinition, session_id: str):
        self.game_def = game_def
        self.session_id = session_id
        self.logger = setup_session_logger(session_id)
        self.state_manager = StateManager(game_def)
        self.clothing_manager = ClothingManager(game_def, self.state_manager.state)
        self.arc_manager = ArcManager(game_def)
        self.event_manager = EventManager(game_def)
        self.modifier_manager = ModifierManager(game_def, self)
        self.inventory_manager = InventoryManager(game_def)
        self.ai_service = AIService()
        self.prompt_builder = PromptBuilder(game_def, self.clothing_manager)
        self.nodes_map: dict[str, Node] = {node.id: node for node in self.game_def.nodes}
        self.actions_map: dict[str, GameAction] = {action.id: action for action in self.game_def.actions}
        self.characters_map: dict[str, Character] = {char.id: char for char in self.game_def.characters}
        self.locations_map: dict[str, Location] = {
            loc.id: loc for zone in self.game_def.zones for loc in zone.locations
        }
        self.zones_map = {zone.id: zone for zone in self.game_def.zones}
        self.turn_meter_deltas: dict[str, dict[str, float]] = {}

        # --- Seed Initialization ---
        self.base_seed: int | None = None
        self.generated_seed: int | None = None
        if isinstance(self.game_def.rng_seed, int):
            self.base_seed = self.game_def.rng_seed
            self.logger.info(f"Using fixed RNG seed from game definition: {self.base_seed}")
        elif self.game_def.rng_seed == "auto":
            self.generated_seed = random.randint(0, 2 ** 32 - 1)
            self.base_seed = self.generated_seed
            self.logger.info(f"Auto-generated RNG seed for session: {self.base_seed}")

        self.logger.info(f"GameEngine for session {session_id} initialized.")

    async def process_action(
            self,
            action_type: str,
            action_text: str | None = None,
            target: str | None = None,
            choice_id: str | None = None,
            item_id: str | None = None
    ) -> dict[str, Any]:
        self.logger.info(f"--- Turn Start ---")
        self.turn_meter_deltas = {}
        state = self.state_manager.state
        current_node = self._get_current_node()

        if current_node.type == NodeType.ENDING:
            self.logger.warning("Attempted to process action in an ENDING node. Halting turn.")
            return {
                "narrative": "The story has concluded.",
                "choices": [],
                "current_state": self._get_state_summary()
            }

        if current_node.present_characters:
            state.present_chars = [char for char in current_node.present_characters if char in self.characters_map]
            self.logger.info(f"Set present characters from node '{current_node.id}': {state.present_chars}")

        # Initial action formatting for logging and AI prompts
        player_action_str = self._format_player_action(action_type, action_text, target, choice_id, item_id)
        self.logger.info(f"Player Action: {player_action_str}")

        # Handle both local and zone travel
        if choice_id and (choice_id.startswith("move_") or choice_id.startswith("travel_")):
            return await self._handle_movement_choice(choice_id)
        if action_type == "do" and action_text and self._is_movement_action(action_text):
            return await self._handle_movement(action_text)

        # Pre-AI effects
        active_events = self.event_manager.get_triggered_events(state, rng_seed=self._get_turn_seed())
        event_choices = [c for e in active_events for c in e.choices]
        event_narratives = [event.narrative for event in active_events if event.narrative]
        for event in active_events:
            self._apply_effects(event.effects)

        if action_type == "choice" and choice_id:
            await self._handle_predefined_choice(choice_id, event_choices)

        newly_entered_stages, newly_exited_stages = self.arc_manager.check_and_advance_arcs(state, rng_seed=self._get_turn_seed())
        for stage in newly_exited_stages:
            self._apply_effects(stage.effects_on_exit)
        for stage in newly_entered_stages:
            self._apply_effects(stage.effects_on_enter)
            self._apply_effects(stage.effects_on_advance)

        # AI Generation
        writer_prompt = self.prompt_builder.build_writer_prompt(state, player_action_str, current_node,
                                                                state.narrative_history, rng_seed=self._get_turn_seed())
        narrative_from_ai = (await self.ai_service.generate(writer_prompt)).content

        checker_prompt = self.prompt_builder.build_checker_prompt(narrative_from_ai, player_action_str, state)
        checker_response = await self.ai_service.generate(checker_prompt, model=self.ai_service.settings.checker_model,
                                                          json_mode=True)

        state_deltas = {}
        try:
            state_deltas = json.loads(checker_response.content)
            self.logger.info(f"State Deltas Parsed: {json.dumps(state_deltas, indent=2)}")
        except json.JSONDecodeError:
            self.logger.warning(f"Checker AI returned invalid JSON. Content: {checker_response.content}")

        # Handle Gifting Action
        if action_type == "give" and item_id and target:
            item_def = self.inventory_manager.item_defs.get(item_id)
            if item_def and item_def.can_give:
                # Apply gift effects
                self._apply_effects(item_def.gift_effects)
                # Remove item from the player inventory
                self.inventory_manager.apply_effect(
                    InventoryChangeEffect(type="inventory_remove", owner="player", item=item_id, count=1),
                    self.state_manager.state
                )
                self.logger.info(f"Player gave item '{item_id}' to '{target}'.")
            else:
                self.logger.warning(f"Player tried to give non-giftable item '{item_id}'.")

        # Post-AI State Updates
        reconciled_narrative = self._reconcile_narrative(player_action_str, narrative_from_ai, state_deltas, target)
        self._apply_ai_state_changes(state_deltas)
        final_narrative = "\n\n".join(event_narratives + [reconciled_narrative])
        state.narrative_history.append(final_narrative)

        if action_type == "use" and item_id:
            item_effects = self.inventory_manager.use_item("player", item_id, state)
            self._apply_effects(item_effects)

        self._check_and_apply_node_transitions()
        self.modifier_manager.update_modifiers_for_turn(state, rng_seed=self._get_turn_seed())
        self._update_discoveries()

        # Pass time advancement info to process meter dynamics
        time_advanced_info = self._advance_time()
        self.modifier_manager.tick_durations(state, time_advanced_info["minutes_passed"])
        self._process_meter_dynamics(time_advanced_info)
        self.event_manager.decrement_cooldowns(state)

        final_node = self._get_current_node()
        choices = self._generate_choices(final_node, event_choices)
        final_state_summary = self._get_state_summary()
        self.logger.info(f"End of Turn State: {json.dumps(final_state_summary, indent=2)}")
        self.logger.info(f"--- Turn End ---")

        return {"narrative": final_narrative, "choices": choices, "current_state": final_state_summary}

    def _update_discoveries(self):
        """Checks for and applies new location discoveries."""
        state = self.state_manager.state
        evaluator = ConditionEvaluator(state, state.present_chars, rng_seed=self._get_turn_seed())

        for zone in self.game_def.zones:
            # Check for zone discovery first
            if zone.discovery_conditions:
                for condition in zone.discovery_conditions:
                    if evaluator.evaluate(condition):
                        # If a zone is discovered, all its non-hidden locations become discovered
                        for loc in zone.locations:
                            if loc.id not in state.discovered_locations:
                                state.discovered_locations.append(loc.id)
                                self.logger.info(f"Discovered new location '{loc.id}' in zone '{zone.id}'.")
                        break  # Stop checking conditions for this zone once discovered

            # Check individual locations in already discovered zones
            for loc in zone.locations:
                if loc.id not in state.discovered_locations and loc.discovery_conditions:
                    for condition in loc.discovery_conditions:
                        if evaluator.evaluate(condition):
                            state.discovered_locations.append(loc.id)
                            self.logger.info(f"Discovered new location: '{loc.id}'.")
                            break

    async def _handle_movement_choice(self, choice_id: str) -> dict[str, Any]:
        state = self.state_manager.state

        if choice_id.startswith("move_"):
            # Local movement
            destination_id = choice_id.replace("move_", "")
            current_location = self._get_location(state.location_current)
            if current_location and current_location.connections:
                for connection in current_location.connections:
                    if isinstance(connection.to, str) and connection.to == destination_id:
                        return await self._execute_local_movement(destination_id, connection)
                    elif isinstance(connection.to, list) and destination_id in connection.to:
                        return await self._execute_local_movement(destination_id, connection)

        elif choice_id.startswith("travel_"):
            # Zone travel
            destination_zone_id = choice_id.replace("travel_", "")
            current_zone = self.zones_map.get(state.zone_current)
            if current_zone and current_zone.transport_connections:
                for connection in current_zone.transport_connections:
                    if connection.get("to") == destination_zone_id:
                        return await self._execute_zone_travel(destination_zone_id, connection)

        # Fallback if no valid movement found
        return {
            "narrative": "You can't seem to go that way.",
            "choices": self._generate_choices(self._get_current_node(), []),
            "current_state": self._get_state_summary()
        }

    async def _execute_zone_travel(self, destination_zone_id: str, connection: dict) -> dict[str, Any]:
        """Executes a player-initiated movement between zones."""
        state = self.state_manager.state
        move_rules = self.game_def.movement

        # Find the entry point of the destination zone
        dest_zone = self.zones_map.get(destination_zone_id)
        if not dest_zone or not dest_zone.locations:
            return {"narrative": "That area is not yet accessible.",
                    "choices": self._generate_choices(self._get_current_node(), []),
                    "current_state": self._get_state_summary()}

        # For simplicity, we'll assume the first location is the entry point
        destination_location_id = dest_zone.locations[0].id

        # --- Calculate Time Cost ---
        time_cost_minutes = 15  # Default
        if move_rules and move_rules.zone_travel:
            # Simple formula for now, which can be expanded later with DSL evaluation
            distance = connection.get("distance", 1)
            base_time = 10  # Placeholder for a more complex formula base
            time_cost_minutes = base_time * distance

        # --- Update State ---
        state.location_previous = state.location_current
        state.zone_current = destination_zone_id
        state.location_current = destination_location_id
        state.location_privacy = self._get_location_privacy(destination_location_id)

        state.present_chars = ["player"]  # Companions are left behind for zone travel for now
        self._advance_time(minutes=time_cost_minutes)
        self._update_npc_presence()

        new_location = self._get_location(destination_location_id)
        loc_desc = new_location.description if new_location and isinstance(new_location.description,
                                                                           str) else "You arrive in a new area."

        final_narrative = f"You travel to {dest_zone.name}.\n\n{loc_desc}"
        self.logger.info(f"Zone travel to '{destination_zone_id}' completed. Time cost: {time_cost_minutes}m.")

        return {"narrative": final_narrative, "choices": self._generate_choices(self._get_current_node(), []),
                "current_state": self._get_state_summary()}

    async def _execute_local_movement(self, destination_id: str, connection: LocationConnection) -> dict[str, Any]:
        """Executes a player-initiated movement between locations."""
        state = self.state_manager.state
        evaluator = ConditionEvaluator(state, state.present_chars, rng_seed=self._get_turn_seed())
        move_rules = self.game_def.movement

        # --- Companion Consent Check ---
        moving_companions = []
        for char_id in state.present_chars:
            if char_id == "player": continue

            character_def = self.characters_map.get(char_id)
            if not character_def or not character_def.movement:
                # If no rules, assume they stay behind.
                continue

            is_willing = False
            for rule in character_def.movement.willing_locations:
                if rule.get("location") == destination_id and evaluator.evaluate(rule.get("when")):
                    is_willing = True
                    break

            if is_willing:
                moving_companions.append(char_id)
            else:
                # Movement is blocked if any present NPC is unwilling to move.
                refusal_text = character_def.movement.refusal_text.get(
                    "low_trust") if character_def.movement.refusal_text else "They don't want to go there right now."
                return {
                    "narrative": f"{character_def.name} seems hesitant. \"{refusal_text}\"",
                    "choices": self._generate_choices(self._get_current_node(), []),
                    "current_state": self._get_state_summary()
                }

        # --- Movement Cost & Restriction Checks ---
        if move_rules and move_rules.restrictions:
            # Check for consciousness
            if move_rules.restrictions.requires_consciousness:
                # This is a placeholder for a future "conscious" flag/modifier
                is_conscious = state.flags.get("is_conscious", True)
                if not is_conscious:
                    return {
                        "narrative": "You are unconscious and cannot move.",
                        "choices": self._generate_choices(self._get_current_node(), []),
                        "current_state": self._get_state_summary()
                    }
            min_energy = move_rules.restrictions.min_energy or 0
            if state.meters.get("player", {}).get("energy", 100) < min_energy:
                return {
                    "narrative": "You are too exhausted to move.",
                    "choices": self._generate_choices(self._get_current_node(), []),
                    "current_state": self._get_state_summary()
                }

            energy_cost = move_rules.restrictions.energy_cost_per_move or 0
            self._apply_meter_change(
                MeterChangeEffect(target="player", meter="energy", op="subtract", value=energy_cost))

        # --- Calculate Time Cost ---
        time_cost_minutes = 0
        if move_rules and move_rules.local:
            base_cost = move_rules.local.base_time or 0
            modifier = move_rules.local.distance_modifiers.get(connection.distance, 1) if connection.distance else 1
            time_cost_minutes = base_cost * modifier

        # --- Update State ---
        state.location_previous = state.location_current
        state.location_current = destination_id
        state.location_privacy = self._get_location_privacy(destination_id)

        # Update presence: only player and willing companions are now present
        state.present_chars = ["player"] + moving_companions
        self._advance_time(minutes=time_cost_minutes)
        self._update_npc_presence() #

        new_location = self._get_location(destination_id)
        loc_desc = new_location.description if new_location and isinstance(new_location.description,
                                                                           str) else "You arrive."

        npc_names = [self.characters_map[cid].name for cid in state.present_chars if cid in self.characters_map]
        presence_desc = f"{', '.join(npc_names)} are here." if npc_names else ""
        final_narrative = f"You move to the {new_location.name}.\n\n{loc_desc}\n\n{presence_desc}".strip()

        self.logger.info(
            f"Movement from '{state.location_previous}' to '{destination_id}' completed. Time cost: {time_cost_minutes}m, Energy cost: {energy_cost if move_rules else 0}.")

        return {
            "narrative": final_narrative,
            "choices": self._generate_choices(self._get_current_node(), []),
            "current_state": self._get_state_summary()
        }

    def _advance_time(self, minutes: int | None = None) -> dict[str, bool]:
        """Advances game time by minutes (for clock/hybrid) or by a single action tick (for slots)."""
        state = self.state_manager.state
        time_config = self.game_def.time

        day_advanced = False
        slot_advanced = False

        original_day = state.day
        original_slot = state.time_slot

        minutes_passed = 0
        if time_config.mode in ("hybrid", "clock") and time_config.clock:
            minutes_passed = minutes if minutes is not None else 10
            time_cost = minutes_passed

            if time_cost != 0:
                current_hh, current_mm = map(int, state.time_hhmm.split(':'))
                total_minutes_today = current_hh * 60 + current_mm
                total_minutes_today += time_cost

                if total_minutes_today >= time_config.clock.minutes_per_day:
                    state.day += 1
                    total_minutes_today %= time_config.clock.minutes_per_day

                new_hh = total_minutes_today // 60
                new_mm = total_minutes_today % 60
                state.time_hhmm = f"{new_hh:02d}:{new_mm:02d}"

                if time_config.mode == "hybrid" and time_config.clock.slot_windows:
                    new_slot_found = False
                    for slot, window in time_config.clock.slot_windows.items():
                        start_hh, start_mm = map(int, window.start.split(':'))
                        end_hh, end_mm = map(int, window.end.split(':'))

                        if start_hh > end_hh:
                            if (new_hh > start_hh) or (new_hh < end_hh) or (
                                    new_hh == start_hh and new_mm >= start_mm) or (
                                    new_hh == end_hh and new_mm <= end_mm):
                                if state.time_slot != slot:
                                    state.time_slot = slot
                                    self.logger.info(f"Time slot advanced to '{slot}'.")
                                new_slot_found = True
                                break
                        else:
                            if window.start <= state.time_hhmm <= window.end:
                                if state.time_slot != slot:
                                    state.time_slot = slot
                                    self.logger.info(f"Time slot advanced to '{slot}'.")
                                new_slot_found = True
                                break
                    if not new_slot_found:
                        self.logger.warning(f"Could not find a slot for time {state.time_hhmm}")

                self.logger.info(f"Time advanced by {time_cost} minutes to {state.time_hhmm}.")

        elif time_config.mode == "slots":
            state.actions_this_slot += 1
            # In slots mode, we can estimate minutes passed if needed, or just tick by 1 "turn"
            # For simplicity, let's say one action is roughly 10 minutes.
            minutes_passed = 10
            if time_config.slots and state.actions_this_slot >= time_config.actions_per_slot:
                state.actions_this_slot = 0
                current_slot_index = time_config.slots.index(state.time_slot)
                if current_slot_index + 1 < len(time_config.slots):
                    state.time_slot = time_config.slots[current_slot_index + 1]
                else:
                    state.day += 1
                    state.time_slot = time_config.slots[0]
                self.logger.info(f"Time slot advanced to '{state.time_slot}'.")

        if state.day > original_day:
            day_advanced = True
            # Recalculate weekday when day changes
            self.state_manager.state.weekday = self._calculate_weekday()
            self.logger.info(
                f"Day advanced to {self.state_manager.state.day}, weekday is {self.state_manager.state.weekday}")

        if state.time_slot != original_slot:
            slot_advanced = True

        return {"day_advanced": day_advanced, "slot_advanced": slot_advanced, "minutes_passed": minutes_passed}


    def _is_movement_action(self, action_text: str) -> bool:
        patterns = [r'\b(go|walk|run|head|travel|enter|exit|leave)\b']
        return any(re.search(pattern, action_text, re.IGNORECASE) for pattern in patterns)

    async def _handle_movement(self, action_text: str) -> dict[str, Any]:
        current_location = self._get_location(self.state_manager.state.location_current)
        if not current_location or not current_location.connections:
            return {"narrative": "There's nowhere to go from here.", "choices": [],
                    "current_state": self._get_state_summary()}

        action_lower = action_text.lower()
        for connection in current_location.connections:
            # Ensure connection.to is not a list
            if isinstance(connection.to, str):
                dest_location = self._get_location(connection.to)
                if dest_location and dest_location.name.lower() in action_lower:
                    return await self._execute_local_movement(dest_location.id, connection)

        # If no match, defer to general action processing
        return await self.process_action("do", "look around for exits")

    def _update_npc_presence(self):
        state = self.state_manager.state
        current_time = state.time_slot
        current_loc = state.location_current
        for char in self.game_def.characters:
            if char.id != "player" and char.schedule:
                # Determine if it's a weekday or weekend for schedule lookup
                # This is a simplification; a full calendar system would be more robust.
                schedule_for_today = char.schedule.weekday
                if schedule_for_today and current_time in schedule_for_today:
                    if schedule_for_today[current_time].location == current_loc:
                        if char.id not in state.present_chars:
                            state.present_chars.append(char.id)

    def _reconcile_narrative(self, player_action: str, ai_narrative: str, deltas: dict,
                             target_char_id: str | None) -> str:
        gate_map = {"kiss": "accept_kiss", "sex": "accept_sex", "oral": "accept_oral"}
        for keyword, gate_id in gate_map.items():
            if keyword in player_action.lower() and target_char_id:
                evaluator = ConditionEvaluator(self.state_manager.state, self.state_manager.state.present_chars, rng_seed=self._get_turn_seed())
                target_char = self.characters_map.get(target_char_id)
                if not target_char or not target_char.behaviors: continue
                gate = next((g for g in target_char.behaviors.gates if g.id == gate_id), None)
                if not gate: continue
                condition = gate.when or (
                    " or ".join(f"({c})" for c in gate.when_any) if gate.when_any else " and ".join(
                        f"({c})" for c in gate.when_all))
                if not evaluator.evaluate(condition):
                    if f"{target_char_id}_first_{keyword}" not in deltas.get("flag_changes", {}):
                        if target_char.behaviors.refusals:
                            return target_char.behaviors.refusals.generic or "They are not comfortable with that right now."
                        return "They are not comfortable with that right now."
        return ai_narrative

    def _apply_ai_state_changes(self, deltas: dict):
        if meter_changes := deltas.get("meter_changes"):
            for char_id, meters in meter_changes.items():
                for meter, value in meters.items():
                    self._apply_meter_change(MeterChangeEffect(target=char_id, meter=meter, op="add", value=value))
        if flag_changes := deltas.get("flag_changes"):
            for key, value in flag_changes.items():
                self._apply_flag_set(FlagSetEffect(key=key, value=value))
        if inventory_changes := deltas.get("inventory_changes"):
            for owner_id, items in inventory_changes.items():
                effect_type = cast(Literal["inventory_add", "inventory_remove"],
                                   "inventory_add" if items.get(list(items.keys())[0], 0) > 0 else "inventory_remove")
                for item_id, count in items.items():
                    effect = InventoryChangeEffect(type=effect_type, owner=owner_id, item=item_id, count=abs(count))
                    self.inventory_manager.apply_effect(effect, self.state_manager.state)
        if clothing_changes := deltas.get("clothing_changes"):
            self.clothing_manager.apply_ai_changes(clothing_changes)

    def _format_player_action(self, action_type, action_text, target, choice_id, item_id) -> str:
        if action_type == 'use' and item_id:
            item_def = self.inventory_manager.item_defs.get(item_id)
            return item_def.use_text if item_def and item_def.use_text else f"Player uses {item_id}."
        elif action_type == 'choice' and choice_id:
            all_choices = self._get_current_node().choices + self._get_current_node().dynamic_choices
            # Also check unlocked actions
            unlocked_action_defs = [self.actions_map.get(act_id) for act_id in self.state_manager.state.unlocked_actions
                                    if act_id in self.actions_map]

            choice = next((c for c in all_choices if c.id == choice_id), None)
            if choice:
                return f"Player chooses to: '{choice.prompt}'"

            action = next((a for a in unlocked_action_defs if a.id == choice_id), None)
            if action:
                return f"Player chooses to: '{action.prompt}'"

            return f"Player chooses action: '{choice_id}'"

        elif action_type == 'say':
            return f"Player says to {target or 'everyone'}: \"{action_text}\""
        return f"Player action: {action_text}"

    def _check_and_apply_node_transitions(self):
        evaluator = ConditionEvaluator(self.state_manager.state, self.state_manager.state.present_chars, rng_seed=self._get_turn_seed())
        current_node = self._get_current_node()

        for transition in current_node.transitions:
            if evaluator.evaluate(transition.when):
                target_node = self.nodes_map.get(transition.to)
                if not target_node:
                    self.logger.warning(
                        f"Transition in node '{current_node.id}' points to non-existent node '{transition.to}'.")
                    continue

                # --- New Logic: Check for Ending Unlock ---
                if target_node.type == NodeType.ENDING:
                    if not target_node.ending_id or target_node.ending_id not in self.state_manager.state.unlocked_endings:
                        self.logger.info(
                            f"Transition to ending node '{target_node.id}' blocked: ending '{target_node.ending_id}' is not unlocked.")
                        continue  # Skip this transition

                self.state_manager.state.current_node = transition.to
                self.logger.info(
                    f"Transitioning from '{current_node.id}' to '{transition.to}' because '{transition.when}' was true.")
                return  # Stop after the first valid transition

    async def _handle_predefined_choice(self, choice_id: str, event_choices: list[Choice]):
        # Check node and event choices
        current_node = self._get_current_node()
        all_choices = event_choices + current_node.choices + current_node.dynamic_choices
        found_choice = next((c for c in all_choices if c.id == choice_id), None)
        if found_choice:
            if found_choice.effects: self._apply_effects(found_choice.effects)
            if found_choice.goto: self.state_manager.state.current_node = found_choice.goto
            return

        # Check unlocked actions
        if choice_id in self.state_manager.state.unlocked_actions:
            action_def = self.actions_map.get(choice_id)
            if action_def:
                if action_def.effects: self._apply_effects(action_def.effects)
                # Unlocked actions do not have a 'goto'

    def _apply_effects(self, effects: list[AnyEffect]):
        evaluator = ConditionEvaluator(self.state_manager.state, self.state_manager.state.present_chars, rng_seed=self._get_turn_seed())
        for effect in effects:
            if isinstance(effect, ConditionalEffect):
                self._apply_conditional_effect(effect)
            elif evaluator.evaluate(effect.when):
                if isinstance(effect, RandomEffect): self._apply_random_effect(effect)
                elif isinstance(effect, MeterChangeEffect): self._apply_meter_change(effect)
                elif isinstance(effect, FlagSetEffect): self._apply_flag_set(effect)
                elif isinstance(effect, GotoNodeEffect): self._apply_goto_node(effect)
                elif isinstance(effect, MoveToEffect): self._apply_move_to(effect)
                elif isinstance(effect, InventoryChangeEffect): self.inventory_manager.apply_effect(effect, self.state_manager.state)
                elif isinstance(effect, ClothingChangeEffect): self.clothing_manager.apply_effect(effect)
                elif isinstance(effect, (ApplyModifierEffect, RemoveModifierEffect)): self.modifier_manager.apply_effect(effect, self.state_manager.state)
                elif isinstance(effect, UnlockEffect): self._apply_unlock(effect)
                elif isinstance(effect, AdvanceTimeEffect): self._apply_advance_time(effect)


    def _apply_conditional_effect(self, effect: ConditionalEffect):
        """Applies a conditional effect."""
        evaluator = ConditionEvaluator(self.state_manager.state, self.state_manager.state.present_chars, rng_seed=self._get_turn_seed())
        if evaluator.evaluate(effect.when):
            self._apply_effects(effect.then)
        else:
            self._apply_effects(effect.else_effects)

    def _apply_random_effect(self, effect: RandomEffect):
        """Applies a random effect."""
        total_weight = sum(choice.weight for choice in effect.choices)
        if total_weight <= 0:
            return

        roll = random.Random(self._get_turn_seed()).uniform(0, total_weight)
        current_weight = 0
        for choice in effect.choices:
            current_weight += choice.weight
            if roll <= current_weight:
                self._apply_effects(choice.effects)
                return

    def _apply_unlock(self, effect: UnlockEffect):
        """Dispatches unlock effects to their specific handlers."""
        if effect.type == "unlock_outfit":
            self._apply_unlock_outfit(effect)
        elif effect.type == "unlock_ending":
            self._apply_unlock_ending(effect)
        elif effect.type == "unlock_actions":
            self._apply_unlock_actions(effect)

    def _apply_unlock_outfit(self, effect: UnlockEffect):
        """Applies an unlock_outfit effect."""
        if not effect.character or not effect.outfit:
            self.logger.warning(f"Invalid unlock_outfit effect: missing character or outfit. Effect: {effect}")
            return

        char_unlocks = self.state_manager.state.unlocked_outfits.setdefault(effect.character, [])
        if effect.outfit not in char_unlocks:
            char_unlocks.append(effect.outfit)
            self.logger.info(f"Unlocked outfit '{effect.outfit}' for character '{effect.character}'.")

    def _apply_unlock_ending(self, effect: UnlockEffect):
        """Applies an unlock_ending effect."""
        if not effect.ending:
            self.logger.warning(f"Invalid unlock_ending effect: missing ending ID. Effect: {effect}")
            return

        if effect.ending not in self.state_manager.state.unlocked_endings:
            self.state_manager.state.unlocked_endings.append(effect.ending)
            self.logger.info(f"Unlocked ending '{effect.ending}'.")

    def _apply_unlock_actions(self, effect: UnlockEffect):
        """Applies an unlock_actions effect."""
        if not effect.actions:
            self.logger.warning(f"Invalid unlock_actions effect: missing actions list. Effect: {effect}")
            return

        for action_id in effect.actions:
            if action_id not in self.state_manager.state.unlocked_actions:
                self.state_manager.state.unlocked_actions.append(action_id)
                self.logger.info(f"Unlocked action '{action_id}'.")

    def _apply_move_to(self, effect: MoveToEffect):
        """Applies a move_to effect and updates character presence."""
        self.state_manager.state.location_current = effect.location
        self.state_manager.state.location_privacy = self._get_location_privacy(effect.location)
        self._update_npc_presence()
        # After moving, immediately check the destination node for characters
        current_node = self._get_current_node()
        if current_node.present_characters:
            self.state_manager.state.present_chars = [
                char for char in current_node.present_characters if char in self.characters_map
            ]

    def _apply_meter_change(self, effect: MeterChangeEffect):
        """Applies a meter change, respecting turn-based delta caps."""
        target_meters = self.state_manager.state.meters.get(effect.target)
        if target_meters is None:
            return

        meter_def = self._get_meter_def(effect.target, effect.meter)
        value_to_apply = effect.value
        op_to_apply = effect.op

        # --- Delta Cap Logic ---
        if meter_def and meter_def.delta_cap_per_turn is not None:
            cap = meter_def.delta_cap_per_turn
            self.turn_meter_deltas.setdefault(effect.target, {}).setdefault(effect.meter, 0)
            current_turn_delta = self.turn_meter_deltas[effect.target][effect.meter]
            remaining_cap = cap - abs(current_turn_delta)

            if remaining_cap <= 0:
                self.logger.warning(f"Meter change for '{effect.target}.{effect.meter}' blocked by delta cap.")
                return

            if op_to_apply in ["add", "subtract"]:
                change_sign = 1 if op_to_apply == "add" else -1
                actual_change = max(-remaining_cap, min(remaining_cap, value_to_apply * change_sign))

                value_to_apply = abs(actual_change)
                op_to_apply = "add" if actual_change > 0 else "subtract"

                self.turn_meter_deltas[effect.target][effect.meter] += actual_change

        # --- Apply the change ---
        current_value = target_meters.get(effect.meter, 0)
        op_map = {
            "add": lambda a, b: a + b,
            "subtract": lambda a, b: a - b,
            "multiply": lambda a, b: a * b,
            "divide": lambda a, b: a / b if b != 0 else a,
            "set": lambda a, b: b}

        if operation := op_map.get(op_to_apply):
            new_value = operation(current_value, value_to_apply)

            effective_min = meter_def.min if meter_def else new_value
            effective_max = meter_def.max if meter_def else new_value

            active_modifiers = self.state_manager.state.modifiers.get(effect.target, [])
            for mod_state in active_modifiers:
                mod_def = self.modifier_manager.library.get(mod_state['id'])
                if mod_def and mod_def.clamp_meters:
                    if meter_clamp := mod_def.clamp_meters.get(effect.meter):
                        if 'min' in meter_clamp:
                            effective_min = max(effective_min, meter_clamp['min'])
                        if 'max' in meter_clamp:
                            effective_max = min(effective_max, meter_clamp['max'])

            new_value = max(effective_min, min(new_value, effective_max))
            target_meters[effect.meter] = new_value

    def _apply_flag_set(self, effect: FlagSetEffect):
        self.state_manager.state.flags[effect.key] = effect.value

    def _apply_goto_node(self, effect: GotoNodeEffect):
        if effect.node in self.nodes_map:
            self.state_manager.state.current_node = effect.node

    def _apply_advance_time(self, effect: AdvanceTimeEffect):
        """Applies an advance_time effect by calling the main time function."""
        self.logger.info(f"Applying AdvanceTimeEffect: {effect.minutes} minutes.")
        self._advance_time(minutes=effect.minutes)

    def _generate_choices(self, node: Node, event_choices: list[Choice]) -> list[dict[str, Any]]:
        evaluator = ConditionEvaluator(self.state_manager.state, self.state_manager.state.present_chars, rng_seed=self._get_turn_seed())
        available_choices = []

        active_choices = event_choices if event_choices else node.choices
        for choice in active_choices:
            if evaluator.evaluate(choice.conditions):
                available_choices.append({"id": choice.id, "text": choice.prompt, "type": "node_choice"})

        # Add dynamic choices if their conditions are met
        for choice in node.dynamic_choices:
            if evaluator.evaluate(choice.conditions):
                available_choices.append({"id": choice.id, "text": choice.prompt, "type": "node_choice"})

        # Add Unlocked Actions
        for action_id in self.state_manager.state.unlocked_actions:
            if action_def := self.actions_map.get(action_id):
                if evaluator.evaluate(action_def.conditions):
                    available_choices.append({
                        "id": action_def.id,
                        "text": action_def.prompt,
                        "type": "unlocked_action"
                    })

        # Local Movement Choices
        current_location = self._get_location(self.state_manager.state.location_current)
        if current_location and current_location.connections:
            for connection in current_location.connections:
                targets = [connection.to] if isinstance(connection.to, str) else connection.to
                for target_id in targets:
                    if target_id not in self.state_manager.state.discovered_locations:
                        continue
                    dest_location = self._get_location(target_id)
                    if dest_location:
                        choice = {"id": f"move_{dest_location.id}", "text": f"Go to {dest_location.name}",
                                  "type": "movement", "disabled": False}
                        if dest_location.access and dest_location.access.locked:
                            if not evaluator.evaluate(dest_location.access.unlocked_when):
                                choice["disabled"] = True
                        available_choices.append(choice)

        # Zone Travel Choices
        current_zone = self.zones_map.get(self.state_manager.state.zone_current)
        if current_zone and current_zone.transport_connections:
            for connection in current_zone.transport_connections:
                dest_zone_id = connection.get("to")
                if dest_zone := self.zones_map.get(dest_zone_id):
                    if dest_zone.discovered:
                        # For simplicity, we'll use the first travel method listed
                        method = connection.get("methods", ["travel"])[0]
                        choice = {
                            "id": f"travel_{dest_zone.id}",
                            "text": f"Take the {method} to {dest_zone.name}",
                            "type": "movement",
                            "disabled": not dest_zone.accessible
                        }
                        available_choices.append(choice)

        return available_choices

    def _get_state_summary(self) -> dict[str, Any]:
        state = self.state_manager.state
        evaluator = ConditionEvaluator(state, state.present_chars, rng_seed=self._get_turn_seed())

        summary_meters = {}
        for char_id, meter_values in state.meters.items():
            summary_meters[char_id] = {}
            if char_id == "player":
                meter_defs = self.game_def.meters.get("player", {})
            else:
                meter_defs = self.game_def.meters.get("character_template", {})

            for meter_id, value in meter_values.items():
                definition = meter_defs.get(meter_id)
                if definition:
                    if definition.visible:
                        summary_meters[char_id][meter_id] = {
                            "value": int(value),
                            "min": definition.min,
                            "max": definition.max,
                            "icon": definition.icon,
                            "visible": definition.visible
                        }
                else:
                    char_def = self.characters_map.get(char_id)
                    if char_def and char_def.meters and meter_id in char_def.meters:
                        definition = char_def.meters[meter_id]
                        if definition.visible:
                            summary_meters[char_id][meter_id] = {
                                "value": int(value),
                                "min": definition.min,
                                "max": definition.max,
                                "icon": definition.icon,
                                "visible": definition.visible
                            }

        summary_flags = {}
        # Combine global and character flags for evaluation
        all_flag_defs = self.game_def.flags.copy() if self.game_def.flags else {}
        for char in self.game_def.characters:
            if char.flags:
                for key, flag_def in char.flags.items():
                    all_flag_defs[f"{char.id}.{key}"] = flag_def

        if all_flag_defs:
            for flag_id, flag_def in all_flag_defs.items():
                # A flag is sent to the frontend if it's either explicitly visible
                # or if its reveal_when condition is met.
                if flag_def.visible or evaluator.evaluate(flag_def.reveal_when):
                    summary_flags[flag_id] = {
                        "value": state.flags.get(flag_id, flag_def.default),
                        "label": flag_def.label or flag_id
                    }


        summary_modifiers = {}
        for char_id, active_mods in state.modifiers.items():
            if active_mods:
                summary_modifiers[char_id] = [
                    self.modifier_manager.library[mod['id']].model_dump()
                    for mod in active_mods if mod['id'] in self.modifier_manager.library
                ]

        character_details = {}
        for char_id in state.present_chars:
            if char_def := self.characters_map.get(char_id):
                character_details[char_id] = {
                    "name": char_def.name,
                    "pronouns": char_def.pronouns,
                    "wearing": self.clothing_manager.get_character_appearance(char_id)
                }

        # Add player-specific details, including their clothing
        player_char_def = self.characters_map.get("player")
        player_details = {
            "name": "You",
            "pronouns": player_char_def.pronouns if player_char_def else ["you"],
            "wearing": self.clothing_manager.get_character_appearance("player")
        }

        player_inventory_details = {}
        if player_inv := state.inventory.get("player"):
            for item_id, count in player_inv.items():
                if count > 0 and (item_def := self.inventory_manager.item_defs.get(item_id)):
                    player_inventory_details[item_id] = item_def.model_dump()

        summary = {
            'day': state.day,
            'time': state.time_slot,
            'location': self.locations_map.get(
                state.location_current).name if state.location_current in self.locations_map else state.location_current,
            'present_characters': state.present_chars,
            'character_details': character_details,
            'player_details': player_details,
            'meters': summary_meters,
            'inventory': state.inventory.get("player", {}),
            'inventory_details': player_inventory_details,
            'flags': summary_flags,
            'modifiers': summary_modifiers
        }

        # Add time_hhmm if it exists (for hybrid/clock modes)
        if state.time_hhmm:
            summary['time_hhmm'] = state.time_hhmm

        return summary

    def _get_current_node(self) -> Node:
        node = self.nodes_map.get(self.state_manager.state.current_node)
        if not node: raise ValueError(f"FATAL: Current node '{self.state_manager.state.current_node}' not found.")
        return node

    def _get_character(self, char_id: str) -> Character | None:
        return self.characters_map.get(char_id)

    def _get_location(self, location_id: str) -> Location | None:
        return self.locations_map.get(location_id)

    def _process_meter_dynamics(self, time_advanced_info: dict[str, bool]):
        """Apply decay and process interactions at the end of a turn."""
        if time_advanced_info["day_advanced"]:
            self._apply_meter_decay("day")
        if time_advanced_info["slot_advanced"]:
            self._apply_meter_decay("slot")

    def _apply_meter_decay(self, decay_type: Literal["day", "slot"]):
        """Applies decay/regen to all relevant meters."""
        for char_id, meters in self.state_manager.state.meters.items():
            for meter_id in meters.keys():
                meter_def = self._get_meter_def(char_id, meter_id)
                if not meter_def:
                    continue

                decay_value = 0
                if decay_type == "day" and meter_def.decay_per_day != 0:
                    decay_value = meter_def.decay_per_day
                elif decay_type == "slot" and meter_def.decay_per_slot != 0:
                    decay_value = meter_def.decay_per_slot

                if decay_value != 0:
                    self._apply_meter_change(MeterChangeEffect(
                        target=char_id,
                        meter=meter_id,
                        op="add",  # Decay is just adding a negative value
                        value=decay_value
                    ))
        self.logger.info(f"Applied '{decay_type}' meter decay.")

    def _get_meter_def(self, char_id: str, meter_id: str) -> Any | None:
        """Helper to find the definition for a specific meter."""
        if char_id == "player" and self.game_def.meters and "player" in self.game_def.meters:
            return self.game_def.meters["player"].get(meter_id)

        char_def = self.characters_map.get(char_id)
        if char_def and char_def.meters:
            if meter_def := char_def.meters.get(meter_id):
                return meter_def

        if self.game_def.meters and "character_template" in self.game_def.meters:
            return self.game_def.meters["character_template"].get(meter_id)

        return None

    def _calculate_weekday(self) -> str | None:
        """Calculate the current weekday based on game day and calendar configuration."""
        if not self.game_def.time.calendar or not self.game_def.time.calendar.enabled:
            return None

        calendar = self.game_def.time.calendar
        week_days = calendar.week_days

        # Find the index of the start day
        try:
            start_index = week_days.index(calendar.start_day)
        except ValueError:
            self.logger.warning(f"Invalid start_day '{calendar.start_day}' not in week_days")
            return None

        # Calculate the current weekday index
        # (day - 1) because Day 1 should map to start_day
        current_index = (self.state_manager.state.day - 1 + start_index) % len(week_days)

        return week_days[current_index]

    def _get_turn_seed(self) -> int:
        """Generate a deterministic seed for the current turn."""
        # If seed was provided from the game config or generated before, then use it
        if self.base_seed is not None:
            return self.base_seed * self.state_manager.state.turn_count

        # Otherwise combine game ID, session ID, and turn count for deterministic randomness
        seed_string = f"{self.game_def.meta.id}_{self.session_id}_{self.state_manager.state.turn_count}"
        # Convert to integer hash
        return hash(seed_string) % (2 ** 32)

    def _get_location_privacy(self, location_id: str | None = None) -> LocationPrivacy:
        """Get the privacy level of a location."""
        if location_id is None:
            location_id = self.state_manager.state.location_current

        location = self.locations_map.get(location_id)
        if location and hasattr(location, 'privacy'):
            return location.privacy
        return LocationPrivacy.LOW  # Default