"""
Builds prompts for the Writer and Checker AI models based on the game state.
"""

from __future__ import annotations

import json
from typing import Any, TYPE_CHECKING

from app.core.state_manager import GameState
from app.core.conditions import ConditionEvaluator
from app.models.characters import Character
from app.models.game import GameDefinition
from app.models.locations import Location
from app.models.economy import Shop
from app.models.nodes import Node

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine


class PromptBuilder:
    """Builds prompts for AI models."""

    MAX_MEMORY_ENTRIES = 10
    RECENT_NARRATIVE_COUNT = 2
    MEMORY_CUTOFF_OFFSET = 2

    def __init__(self, game_def: GameDefinition, engine: "GameEngine"):
        self.game_def = game_def
        self.engine = engine
        self.characters_map: dict[str, Character] = {char.id: char for char in self.game_def.characters}

    # ------------------------------------------------------------------ #
    # Writer prompt
    # ------------------------------------------------------------------ #
    def build_writer_prompt(
        self,
        state: GameState,
        player_action: str,
        node: Node,
        recent_history: list[str],
        rng_seed: int | None = None,
    ) -> str:
        narration_rules = self.game_def.narration

        location = next(
            (loc for zone in self.game_def.zones for loc in zone.locations if loc.id == state.location_current), None
        )
        zone = next(
            (zone for zone in self.game_def.zones for loc in zone.locations if loc.id == state.location_current), None
        )
        privacy_level = location.privacy if location else "public"
        location_desc = (
            location.description if location and isinstance(location.description, str) else "An undescribed room."
        )

        world = getattr(self.game_def, "world", None)
        world_setting = world.get("setting", "A generic setting.") if isinstance(world, dict) else ""
        tone = world.get("tone", "A neutral tone.") if isinstance(world, dict) else ""

        player_inventory: list[str] = []
        if player_inv := state.inventory.get("player", {}):
            for item_id, count in player_inv.items():
                if count > 0:
                    item_def = next((item for item in self.game_def.items if item.id == item_id), None)
                    if item_def:
                        player_inventory.append(f"{item_def.name} (x{count})")

        arc_status = ""
        if state.active_arcs:
            arc_lines = []
            for arc_id, stage_id in state.active_arcs.items():
                arc = next((a for a in self.game_def.arcs if a.id == arc_id), None)
                if not arc:
                    continue
                stage = next((s for s in arc.stages if s.id == stage_id), None)
                if stage:
                    arc_lines.append(f"- {arc.title}: {stage.title}")
            if arc_lines:
                arc_status = "**Story Arcs:**\n" + "\n".join(arc_lines)

        time_str = f"Day {state.day}, {state.time_slot}"
        if state.time_hhmm:
            time_str += f" ({state.time_hhmm})"
        if state.weekday:
            time_str += f", {state.weekday.capitalize()}"

        evaluator = ConditionEvaluator(state, rng_seed=rng_seed)
        character_cards = self._build_character_cards(state, evaluator)
        movement_context = self._build_movement_context(state, evaluator, location)
        shop_context = self._build_shop_context(state, evaluator, location)
        economy_context = self._build_economy_context(state)

        beats_instructions = self._format_beats(node)

        memory_context = ""
        recent_context = ""

        if hasattr(state, "memory_log") and state.memory_log:
            memory_cutoff = max(0, len(state.memory_log) - self.MEMORY_CUTOFF_OFFSET)
            if memory_cutoff > 0:
                older_memories = state.memory_log[:memory_cutoff]
                if older_memories:
                    relevant_memories = older_memories[-self.MAX_MEMORY_ENTRIES:]
                    memory_bullets = "\n".join(f"- {m}" for m in relevant_memories)
                    memory_context = f"""
        **Key Events:**
        {memory_bullets}
        """

        if recent_history:
            recent_narratives = recent_history[-self.RECENT_NARRATIVE_COUNT:]
            recent_context = "\n...\n".join(recent_narratives) if len(recent_narratives) > 1 else recent_narratives[0]
        else:
            recent_context = "The story is just beginning."

        if memory_context:
            story_context = f"{memory_context}\n**Recent Scene:**\n{recent_context}"
        else:
            story_context = f"**Story So Far:**\n{recent_context}"

        location_name = location.name if location else state.location_current

        system_prompt = f"""
        You are the PlotPlay Writer - a master storyteller for an adult interactive fiction game.
        Write from a **{narration_rules.pov} perspective** in the **{narration_rules.tense} tense**.

        **LENGTH REQUIREMENT:**
        - MAXIMUM: {narration_rules.paragraphs} paragraphs
        - DO NOT write more than this limit under any circumstances
        - Each paragraph should be 2-4 sentences
        - Keep responses concise and focused

        **CRITICAL SCENE CONSTRAINTS:**
        - The scene takes place at {location_name}
        - DO NOT change locations or narrate movement between places
        - Characters stay in this location unless the player explicitly chooses a movement action
        - DO NOT introduce new characters, items, or plot elements not in the scene beats
        - Stay within the given scene, beats, and character details

        **NARRATIVE RULES:**
        - Describe BOTH the player's action AND the immediate response/result
        - For dialogue: show what the player says, then how others react
        - For actions: show what the player does, then the outcome or reactions
        - Never explicitly mention game mechanics (items, points, meters, stats). Imply changes through narrative.
        - Respect consent boundaries. Use character refusal lines if an action is blocked.
        - Location privacy is {privacy_level}. Keep intimate actions appropriate to the setting.
        - Never speak for the player's internal thoughts or voice.
        - Keep dialogue consistent with each character's style as described.
        - This is a {node.type.value if node.type else 'scene'} node - pace accordingly.
        - Use the Key Events for factual continuity, but focus on the Recent Scene for tone and immediate context.
        - Beats, movement, and merchant notes are internal guardrails. Do not mention the bullet labels verbatim.
        """

        prompt = f"""
        {system_prompt.strip()}

        **Tone:** {tone}
        **World Setting:** {world_setting}
        **Zone:** {zone.name if zone else 'Unknown Area'}

        **Current Scene:** {node.title}
        **Location:** {location.name if location else state.location_current} - {location_desc}
        **Time:** {time_str}

        **Scene Beats (Internal Only):**
        {beats_instructions}

        **Characters Present:**
        {character_cards if character_cards else "No one else is here."}

        **Player Inventory:** {', '.join(player_inventory) if player_inventory else 'Nothing of note'}

        **Movement Options (FOR REFERENCE ONLY - DO NOT NARRATE):** {movement_context}
        **Merchants & Shops (FOR REFERENCE ONLY):** {shop_context}
        **Economy Context:** {economy_context}

        {arc_status}

        {story_context}

        **Player's Action:** {player_action}

        Continue the narrative at {location_name}. Write ONLY {narration_rules.paragraphs} paragraphs maximum. DO NOT change locations.
        """
        return "\n".join(line.strip() for line in prompt.split("\n"))

    # ------------------------------------------------------------------ #
    # Checker prompt
    # ------------------------------------------------------------------ #
    def build_checker_prompt(self, narrative: str, player_action: str, state: GameState) -> str:
        evaluator = ConditionEvaluator(state, rng_seed=self.engine.get_turn_seed())
        prompt_payload = {
            "player_action": player_action,
            "narrative": narrative,
            "pre_state": self._build_checker_state_snapshot(state, evaluator),
            "constraints": self._build_checker_constraints(state, evaluator),
            "response_contract": self._checker_response_contract(),
        }

        return json.dumps(prompt_payload, ensure_ascii=False)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _build_checker_state_snapshot(
        self,
        state: GameState,
        evaluator: ConditionEvaluator,
    ) -> dict[str, Any]:
        location_privacy = getattr(state.location_privacy, "value", str(state.location_privacy))
        snapshot = {
            "time": {
                "day": state.day,
                "slot": state.time_slot,
                "time_hhmm": state.time_hhmm,
                "weekday": state.weekday,
            },
            "location": {
                "id": state.location_current,
                "zone": state.zone_current,
                "privacy": location_privacy,
                "discovered_locations": list(state.discovered_locations),
                "discovered_zones": list(state.discovered_zones),
            },
            "present_characters": list(state.present_chars),
            "meters": state.meters,
            "inventory": state.inventory,
            "location_inventory": state.location_inventory,
            "modifiers": state.modifiers,
            "flags": state.flags,
            "clothing": state.clothing_states,
            "active_arcs": state.active_arcs,
            "current_node": state.current_node,
            "unlocked": {
                "outfits": state.unlocked_outfits,
                "actions": state.unlocked_actions,
                "endings": state.unlocked_endings,
            },
        }

        if state.location_current and state.location_current in self.engine.locations_map:
            location = self.engine.locations_map[state.location_current]
            snapshot["location"]["name"] = location.name
            snapshot["location"]["connections"] = [
                {
                    "to": connection.to if not isinstance(connection.to, list) else connection.to,
                    "direction": getattr(connection.direction, "value", connection.direction),
                    "locked": bool(getattr(connection, "locked", False)),
                    "currently_unlocked": (
                        not getattr(connection, "locked", False)
                        or (getattr(connection, "unlocked_when", None) and evaluator.evaluate(connection.unlocked_when))
                    ),
                    "description": getattr(connection, "description", None),
                }
                for connection in location.connections or []
            ]

        return snapshot

    def _build_checker_constraints(
        self,
        state: GameState,
        evaluator: ConditionEvaluator,
    ) -> dict[str, Any]:
        economy = getattr(self.game_def, "economy", None)

        constraints = {
            "meters": self._collect_meter_catalog(state),
            "inventory": self._collect_inventory_catalog(state),  # Pass state for optimization
            "clothing": {
                "slots": self._collect_clothing_slots(state),
                "states": ["intact", "opened", "displaced", "removed"],
            },
            "modifiers": list(getattr(self.engine.modifiers, "library", {}).keys()),
            "locations": self._collect_location_catalog(state, evaluator),
            "movement": self._collect_movement_catalog(),
            "flags": list(self.game_def.flags.keys()) if self.game_def.flags else [],
            "shops": self._collect_shop_catalog(state, evaluator),
            "inventory_ops": ["add", "remove", "take", "drop", "give", "purchase", "sell"],
            "currency": {
                "enabled": bool(economy and economy.enabled),
                "name": economy.currency_name if economy else None,
                "symbol": economy.currency_symbol if economy else None,
                "max": economy.max_money if economy else None,
            },
        }
        return constraints

    def _collect_meter_catalog(self, state: GameState) -> dict[str, dict[str, Any]]:
        """Collect meter catalog - OPTIMIZED to only include present characters."""
        catalog: dict[str, dict[str, Any]] = {}

        # Only include meters for present characters (player + present_chars)
        relevant_char_ids = {"player"} | set(state.present_chars)

        for char_id in relevant_char_ids:
            if char_id not in state.meters:
                continue

            meter_values = state.meters[char_id]
            char_catalog: dict[str, Any] = {}

            for meter_id in meter_values.keys():
                meter_def = self.engine._get_meter_def(char_id, meter_id)
                if not meter_def:
                    continue
                char_catalog[meter_id] = {
                    "min": meter_def.min,
                    "max": meter_def.max,
                    "format": getattr(meter_def, "format", None),
                    "visible": getattr(meter_def, "visible", True),
                    "decay": getattr(meter_def, "decay", None),
                }
            if char_catalog:
                catalog[char_id] = char_catalog
        return catalog

    def _collect_inventory_catalog(self, state: GameState | None = None) -> dict[str, Any]:
        """Collect inventory catalog - OPTIMIZED to only include relevant items."""
        inventory_service = self.engine.inventory
        catalog: dict[str, Any] = {"items": {}, "clothing": {}, "outfits": {}}

        # Collect only relevant item IDs (in player inventory or location inventory)
        relevant_item_ids = set()
        if state:
            # Player inventory
            player_inv = state.inventory.get("player", {})
            relevant_item_ids.update(player_inv.keys())

            # Current location inventory
            current_loc_inv = state.location_inventory.get(state.location_current, {})
            relevant_item_ids.update(current_loc_inv.keys())

            # Present characters' inventories
            for char_id in state.present_chars:
                char_inv = state.inventory.get(char_id, {})
                relevant_item_ids.update(char_inv.keys())

        # If no state provided, fall back to all items (for compatibility)
        if not relevant_item_ids:
            relevant_item_ids = set(inventory_service.item_defs.keys())

        # Only include relevant items
        for item_id in relevant_item_ids:
            item_def = inventory_service.item_defs.get(item_id)
            if item_def:
                catalog["items"][item_id] = {
                    "name": item_def.name,
                    "value": getattr(item_def, "value", None),
                    "stackable": getattr(item_def, "stackable", True),
                    "droppable": getattr(item_def, "droppable", True),
                    "consumable": getattr(item_def, "consumable", False),
                }

        # Collect only clothing worn by present characters
        relevant_clothing_ids = set()
        if state:
            for char_id in ["player"] + list(state.present_chars):
                char_clothing = state.clothing_states.get(char_id, {})
                if char_clothing and "layers" in char_clothing:
                    for slot_items in char_clothing["layers"].values():
                        if isinstance(slot_items, list):
                            relevant_clothing_ids.update(slot_items)

        # If no state, fall back to all clothing
        if not relevant_clothing_ids:
            relevant_clothing_ids = set(inventory_service.clothing_defs.keys())

        for clothing_id in relevant_clothing_ids:
            clothing_def = inventory_service.clothing_defs.get(clothing_id)
            if clothing_def:
                catalog["clothing"][clothing_id] = {
                    "name": clothing_def.name,
                    "slots": list(clothing_def.occupies),
                    "look": clothing_def.look.model_dump(),
                }

        # Outfits can stay minimal (just IDs and names)
        for outfit_id, outfit_def in inventory_service.outfit_defs.items():
            catalog["outfits"][outfit_id] = {
                "name": outfit_def.name,
                "items": list(outfit_def.items),
            }

        return catalog

    def _collect_clothing_slots(self, state: GameState) -> dict[str, list[str]]:
        slots: dict[str, set[str]] = {}

        for char_id in {"player", *state.present_chars, *state.clothing_states.keys()}:
            char_def = self.characters_map.get(char_id)
            if not char_def:
                continue

            slot_set = slots.setdefault(char_id, set())
            clothing_state = state.clothing_states.get(char_id)
            if clothing_state and clothing_state.get("layers"):
                slot_set.update(clothing_state["layers"].keys())

            wardrobe = getattr(char_def, "wardrobe", None)
            if wardrobe:
                if getattr(wardrobe, "slots", None):
                    slot_set.update(wardrobe.slots)
                if getattr(wardrobe, "outfits", None):
                    for outfit in wardrobe.outfits or []:
                        for clothing_id in outfit.items:
                            clothing_def = self.engine.inventory.clothing_defs.get(clothing_id)
                            if clothing_def:
                                slot_set.update(clothing_def.occupies)

        return {char_id: sorted(list(slot_names)) for char_id, slot_names in slots.items()}

    def _collect_location_catalog(
        self,
        state: GameState,
        evaluator: ConditionEvaluator,
    ) -> dict[str, Any]:
        """Collect location catalog - OPTIMIZED to only include current and connected locations."""
        catalog: dict[str, Any] = {}

        # Only include current location and directly connected locations
        relevant_location_ids = {state.location_current}

        # Add connected locations
        current_location = self.engine.locations_map.get(state.location_current)
        if current_location and current_location.connections:
            for connection in current_location.connections:
                targets = connection.to if isinstance(connection.to, list) else [connection.to]
                relevant_location_ids.update(targets)

        # Build catalog only for relevant locations
        for location_id in relevant_location_ids:
            location = self.engine.locations_map.get(location_id)
            if not location:
                continue
            zone = self.engine.state_manager.index.location_to_zone.get(location_id)
            connections = []
            for connection in location.connections or []:
                targets = connection.to if isinstance(connection.to, list) else [connection.to]
                connection_entry = {
                    "direction": getattr(connection.direction, "value", connection.direction),
                    "locked": bool(getattr(connection, "locked", False)),
                    "unlocked_now": (
                        not getattr(connection, "locked", False)
                        or (getattr(connection, "unlocked_when", None) and evaluator.evaluate(connection.unlocked_when))
                    ),
                    "description": getattr(connection, "description", None),
                    "targets": targets,
                }
                connections.append(connection_entry)

            catalog[location_id] = {
                "name": location.name,
                "zone": zone,
                "privacy": getattr(location.privacy, "value", location.privacy),
                "discovered": location_id in state.discovered_locations,
                "has_shop": bool(getattr(location, "shop", None)),
                "inventory": state.location_inventory.get(location_id, {}),
                "connections": connections,
            }
        return catalog

    def _collect_movement_catalog(self) -> dict[str, Any]:
        movement_config = getattr(self.game_def, "movement", None)
        if not movement_config:
            return {}

        methods = [
            {"name": method.name, "base_time": method.base_time}
            for method in movement_config.methods or []
        ]

        return {
            "base_time": movement_config.base_time,
            "use_entry_exit": getattr(movement_config, "use_entry_exit", False),
            "methods": methods,
        }

    def _collect_shop_catalog(self, state: GameState, evaluator: ConditionEvaluator) -> list[dict[str, Any]]:
        shops: list[dict[str, Any]] = []
        current_location = self.engine.locations_map.get(state.location_current)
        if current_location and getattr(current_location, "shop", None):
            shop = current_location.shop
            shops.append(
                {
                    "owner": current_location.id,
                    "name": shop.name,
                    "available": evaluator.evaluate(shop.when),
                    "can_buy": evaluator.evaluate(shop.can_buy) if shop.can_buy else True,
                }
            )

        for char_id in state.present_chars:
            if char_id == "player":
                continue
            char_def = self.characters_map.get(char_id)
            if not char_def or not getattr(char_def, "shop", None):
                continue
            shop = char_def.shop
            shops.append(
                {
                    "owner": char_id,
                    "name": shop.name,
                    "available": evaluator.evaluate(shop.when),
                    "can_buy": evaluator.evaluate(shop.can_buy) if shop.can_buy else True,
                }
            )
        return shops

    def _checker_response_contract(self) -> dict[str, Any]:
        return {
            "required_keys": [
                "meters",
                "inventory",
                "clothing",
                "movement",
                "discoveries",
                "modifiers",
                "flags",
                "memory",
            ],
            "schema": {
                "meters": {
                    "<character_id>": [
                        {
                            "meter": "<meter_id>",
                            "delta": 0,
                            "operation": "add|subtract|set|multiply|divide",
                            "value": 0,
                            "reason": "<brief justification>",
                        }
                    ]
                },
                "inventory": [
                    {
                        "op": "add|remove|take|drop|give|purchase|sell",
                        "owner": "<character_or_location>",
                        "item": "<item_id>",
                        "count": 1,
                        "from": "<source_owner>",
                        "to": "<target_owner>",
                        "price": 0,
                        "reason": "<brief justification>",
                    }
                ],
                "clothing": [
                    {
                        "type": "slot_state|item_state|put_on|take_off",
                        "character": "<character_id>",
                        "slot": "<slot_id>",
                        "item": "<clothing_id>",
                        "state": "intact|opened|displaced|removed",
                        "reason": "<brief justification>",
                    }
                ],
                "movement": [
                    {
                        "type": "move|move_to|travel_to",
                        "direction": "<local_direction>",
                        "location": "<location_id>",
                        "method": "<travel_method>",
                        "with": ["<character_id>"],
                        "reason": "<brief justification>",
                    }
                ],
                "discoveries": {
                    "locations": ["<location_id>"],
                    "zones": ["<zone_id>"],
                    "actions": ["<action_id>"],
                    "outfits": ["<outfit_id>"],
                    "modifiers": ["<modifier_id>"],
                    "nodes": ["<node_id>"],
                    "endings": ["<ending_id>"],
                },
                "modifiers": {
                    "add": [
                        {
                            "target": "<character_id>",
                            "modifier": "<modifier_id>",
                            "duration": 0,
                            "reason": "<brief justification>",
                        }
                    ],
                    "remove": [
                        {
                            "target": "<character_id>",
                            "modifier": "<modifier_id>",
                            "reason": "<brief justification>",
                        }
                    ],
                },
                "flags": [
                    {"key": "<flag_id>", "value": True, "reason": "<brief justification>"}
                ],
                "memory": ["<short factual memory>"],
            },
            "notes": [
                "Return every top-level key even if empty (use empty objects or lists).",
                "Prefer additive meter 'delta' values; use 'operation'+'value' only for non-additive changes.",
                "Inventory ops must respect availability (e.g., only purchase if a shop is open).",
                "Clothing changes must reference visible slots/items and respect concealment rules.",
                "Movement entries should only exist if the narrative explicitly moves characters.",
            ],
        }

    def _format_beats(self, node: Node) -> str:
        if not node.beats:
            return "- No authored beats for this scene; respond organically to the action."
        return "\n".join(f"- {beat}" for beat in node.beats)

    def _build_movement_context(
        self,
        state: GameState,
        evaluator: ConditionEvaluator,
        location: Location | None,
    ) -> str:
        if not location or not getattr(location, "connections", None):
            return "No obvious exits."

        exits: list[str] = []
        for connection in location.connections or []:
            targets = connection.to if isinstance(connection.to, list) else [connection.to]
            for destination_id in targets:
                if destination_id not in state.discovered_locations:
                    continue

                destination = self.engine.locations_map.get(destination_id)
                if not destination:
                    continue

                is_locked = bool(getattr(connection, "locked", False))
                if getattr(connection, "unlocked_when", None):
                    if evaluator.evaluate(connection.unlocked_when):
                        is_locked = False

                direction = getattr(connection.direction, "name", None) or str(connection.direction or "").upper()
                direction_label = direction.upper()

                description_hint = connection.description or getattr(destination, "summary", None) or ""
                status = "locked" if is_locked else "open"
                segment = f"{direction_label} to {destination.name} ({status})"
                if description_hint:
                    segment = f"{segment} – {description_hint}"

                exits.append(segment)

        if not exits:
            return "Stuck for now; no discovered exits."
        return "; ".join(exits)

    def _build_shop_context(
        self,
        state: GameState,
        evaluator: ConditionEvaluator,
        location: Location | None,
    ) -> str:
        merchant_notes: list[str] = []

        def _shop_status(owner_label: str, shop: Shop) -> None:
            is_open = evaluator.evaluate(shop.when)
            can_buy = evaluator.evaluate(shop.can_buy) if shop.can_buy else True
            sell_multiplier = evaluator.evaluate_value(shop.multiplier_sell, default=1.0)
            buy_multiplier = evaluator.evaluate_value(shop.multiplier_buy, default=1.0)

            status_parts = ["open" if is_open else "closed"]
            if is_open:
                if can_buy:
                    status_parts.append("trades both ways")
                else:
                    status_parts.append("selling only")

            inventory_items = [
                self.engine.items_map[item.id].name
                for item in shop.inventory.items
                if item.discovered is not False and item.id in self.engine.items_map
            ]
            inventory_summary = ", ".join(inventory_items) if inventory_items else "assorted goods"

            merchant_notes.append(
                f"{owner_label}: {'; '.join(status_parts)} — stock includes {inventory_summary} "
                f"(buy x{buy_multiplier}, sell x{sell_multiplier})"
            )

        if location and getattr(location, "shop", None):
            _shop_status(f"{location.name} counter", location.shop)

        for char_id in state.present_chars:
            if char_id == "player":
                continue
            char_def = self.characters_map.get(char_id)
            if not char_def or not getattr(char_def, "shop", None):
                continue
            _shop_status(char_def.name, char_def.shop)

        if not merchant_notes:
            return "No merchants are operating right now."

        return "; ".join(merchant_notes)

    def _build_economy_context(self, state: GameState) -> str:
        economy = getattr(self.game_def, "economy", None)
        if not economy or not economy.enabled:
            return "Economy systems inactive."

        money_value = (state.meters.get("player", {}) or {}).get("money")
        currency_name = economy.currency_name or "currency"
        currency_symbol = economy.currency_symbol or ""
        cap = economy.max_money

        if money_value is None:
            return f"Currency: {currency_name} (symbol {currency_symbol or '-'})"

        formatted_money = f"{money_value:.2f}" if isinstance(money_value, float) else str(int(money_value))
        cap_str = f", cap {currency_symbol}{int(cap)}" if cap else ""
        return f"{currency_symbol}{formatted_money} {currency_name} on hand{cap_str}"

    def _summarize_gates(self, evaluator: ConditionEvaluator, char_def: Character) -> list[str]:
        gates = getattr(char_def, "gates", None) or []
        summaries: list[str] = []

        for gate in gates:
            is_open = evaluator.evaluate_conditions(
                when=gate.when,
                when_all=gate.when_all,
                when_any=gate.when_any,
            )
            disposition = "ready" if is_open else "blocked"

            text = gate.acceptance if is_open else gate.refusal
            text = (text or "").strip()
            if not text:
                text = "No scripted response."

            summaries.append(f"{gate.id}: {disposition} — {text}")
        return summaries

    def _describe_wardrobe_layers(self, state: GameState, char_id: str) -> str:
        clothing_state = state.clothing_states.get(char_id) or {}
        layers = clothing_state.get("layers") or {}
        if not layers:
            return "No tracked layers."

        formatted = []
        for slot, status in sorted(layers.items()):
            slot_label = slot.replace("_", " ").title()
            formatted.append(f"{slot_label}: {status}")
        return "; ".join(formatted)

    def _build_character_cards(self, state: GameState, evaluator: ConditionEvaluator) -> str:
        cards = []

        for char_id in state.present_chars:
            char_def = self.characters_map.get(char_id)
            if not char_def:
                continue

            char_meters = state.meters.get(char_id, {})
            meter_parts = []
            for meter_name, value in sorted(char_meters.items()):
                threshold_label = self._get_meter_threshold_label(char_id, meter_name, value)
                meter_parts.append(f"{meter_name.capitalize()}: {int(value)} ({threshold_label})")
            meter_str = ", ".join(meter_parts) if meter_parts else "No meters"

            active_modifiers = state.modifiers.get(char_id, [])
            modifier_ids = [mod["id"] for mod in active_modifiers if "id" in mod]
            modifier_str = f"Active Modifiers: {', '.join(modifier_ids) or 'None'}"

            effective_dialogue_style = char_def.dialogue_style or "neutral"
            modifiers_config = getattr(self.game_def, "modifiers", None)
            if modifier_ids and modifiers_config and getattr(modifiers_config, "library", None):
                for modifier_id in modifier_ids:
                    modifier_def = modifiers_config.library.get(modifier_id)
                    if modifier_def:
                        behavior = getattr(modifier_def, "behavior", None)
                        if behavior and getattr(behavior, "dialogue_style", None):
                            effective_dialogue_style = behavior.dialogue_style
                            break

            dialogue_style_str = f"Dialogue Style: {effective_dialogue_style}"

            gate_summaries = self._summarize_gates(evaluator, char_def)

            role = getattr(char_def, "role", None) or "character"
            pronouns = getattr(char_def, "pronouns", None)
            personality = getattr(char_def, "personality", None)
            personality_values: list[Any]
            if isinstance(personality, dict):
                personality_values = [v for v in personality.values() if v]
            elif hasattr(personality, "core_traits"):
                personality_values = list(personality.core_traits)
            else:
                personality_values = []

            card_lines = [
                f"- **{char_def.name} ({role})**",
                f"  - Pronouns: {', '.join(pronouns) if pronouns else 'not specified'}",
                f"  - Personality: {', '.join(personality_values) or 'reserved'}",
                f"  - {dialogue_style_str}",
                f"  - Current State: {meter_str}",
                f"  - {modifier_str}",
                f"  - Outfit Glimpse: {self.engine.clothing.get_character_appearance(char_id)}",
                f"  - Wardrobe State: {self._describe_wardrobe_layers(state, char_id)}",
            ]

            if gate_summaries:
                card_lines.append("  - Consent Gates:")
                card_lines.extend(f"    - {summary}" for summary in gate_summaries)

            cards.append("\n".join(card_lines))

        return "\n".join(cards)

    def _get_meter_threshold_label(self, char_id: str, meter_name: str, value: int) -> str:
        char_def = self.characters_map.get(char_id)
        meter_def = None

        if char_def and char_def.meters and meter_name in char_def.meters:
            meter_def = char_def.meters[meter_name]

        if char_id != "player":
            template_meters = self.game_def.meters.template or {}
            if meter_name in template_meters:
                meter_def = template_meters[meter_name]
        else:
            player_meters = self.game_def.meters.player or {}
            if meter_name in player_meters:
                meter_def = player_meters[meter_name]

        if meter_def and meter_def.thresholds:
            threshold_value = self._get_threshold_name(value, meter_def.thresholds)
            if threshold_value is not None:
                return threshold_value

        if value >= 80:
            return "very high"
        if value >= 60:
            return "high"
        if value >= 40:
            return "medium"
        if value >= 20:
            return "low"
        return "very low"

    @staticmethod
    def _get_threshold_name(value: int, thresholds: dict[str, list[int]]) -> str | None:
        for threshold_value in sorted(thresholds.keys(), reverse=True):
            threshold_range = thresholds[threshold_value]
            if isinstance(threshold_range, list) and len(threshold_range) == 2:
                if threshold_range[0] <= value <= threshold_range[1]:
                    return threshold_value
        return None
