"""State summary builder for turn responses."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.conditions import ConditionEvaluator

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine


class StateSummaryService:
    """Constructs the public state snapshot returned to the client."""

    def __init__(self, engine: "GameEngine") -> None:
        self.engine = engine

    def build(self) -> dict:
        state = self.engine.state_manager.state
        evaluator = ConditionEvaluator(state, rng_seed=self.engine.get_turn_seed())

        def build_item_detail(item_id: str) -> dict | None:
            item_type = self.engine.inventory.get_item_type(item_id)
            if not item_type:
                return None

            if item_type == "item":
                item_def = self.engine.inventory.item_defs.get(item_id)
                if not item_def:
                    return None
                detail = item_def.model_dump()
                detail.setdefault("icon", "📦")
                detail["stackable"] = bool(getattr(item_def, "stackable", False))
                detail["type"] = "item"
                return detail

            if item_type == "clothing":
                clothing_def = self.engine.inventory.clothing_defs.get(item_id)
                if not clothing_def:
                    return None
                return {
                    "id": clothing_def.id,
                    "name": clothing_def.name,
                    "description": getattr(clothing_def, "description", None),
                    "icon": "🧥",
                    "stackable": False,
                    "type": "clothing",
                }

            if item_type == "outfit":
                outfit_def = self.engine.inventory.outfit_defs.get(item_id)
                if not outfit_def:
                    return None
                return {
                    "id": outfit_def.id,
                    "name": outfit_def.name,
                    "description": getattr(outfit_def, "description", None),
                    "icon": "👗",
                    "stackable": False,
                    "type": "outfit",
                }

            return None

        summary_meters: dict[str, dict] = {}
        for char_id, meter_values in state.meters.items():
            summary_meters[char_id] = {}
            if char_id == "player":
                meter_defs = self.engine.game_def.meters.player or {}
            else:
                meter_defs = self.engine.game_def.meters.template or {}

            for meter_id, value in meter_values.items():
                definition = meter_defs.get(meter_id)
                if definition and definition.visible:
                    summary_meters[char_id][meter_id] = {
                        "value": int(value),
                        "min": definition.min,
                        "max": definition.max,
                        "icon": definition.icon,
                        "visible": definition.visible,
                    }
                    continue

                    char_def = self.engine.characters_map.get(char_id)
                    if char_def and getattr(char_def, "meters", None):
                        definition = char_def.meters.get(meter_id)
                        if definition and definition.visible:
                            summary_meters[char_id][meter_id] = {
                                "value": int(value),
                                "min": definition.min,
                                "max": definition.max,
                                "icon": definition.icon,
                                "visible": definition.visible,
                            }

        summary_flags: dict[str, dict] = {}
        all_flag_defs = self.engine.game_def.flags.copy() if self.engine.game_def.flags else {}
        for char in self.engine.game_def.characters:
            char_flags = getattr(char, "flags", None)
            if char_flags:
                for key, flag_def in char_flags.items():
                    all_flag_defs[f"{char.id}.{key}"] = flag_def

        if all_flag_defs:
            for flag_id, flag_def in all_flag_defs.items():
                if flag_def.visible or (flag_def.reveal_when and evaluator.evaluate(flag_def.reveal_when)):
                    summary_flags[flag_id] = {
                        "value": state.flags.get(flag_id, flag_def.default),
                        "label": flag_def.label or flag_id,
                    }

        summary_modifiers: dict[str, list] = {}
        for char_id, active_mods in state.modifiers.items():
            if active_mods:
                summary_modifiers[char_id] = [
                    self.engine.modifiers.library[mod["id"]].model_dump()
                    for mod in active_mods
                    if mod["id"] in self.engine.modifiers.library
                ]

        character_details: dict[str, dict] = {}
        for char_id in state.present_chars:
            char_def = self.engine.characters_map.get(char_id)
            if not char_def:
                continue
            character_details[char_id] = {
                "name": char_def.name,
                "pronouns": char_def.pronouns,
                "wearing": self.engine.clothing.get_character_appearance(char_id),
            }

        player_char_def = self.engine.characters_map.get("player")
        player_details = {
            "name": "You",
            "pronouns": player_char_def.pronouns if player_char_def else ["you"],
            "wearing": self.engine.clothing.get_character_appearance("player"),
        }

        inventory_details: dict[str, dict] = {}
        player_inventory_raw = state.inventory.get("player", {}) or {}
        player_inventory = {
            item_id: count for item_id, count in player_inventory_raw.items() if count > 0
        }

        for item_id in player_inventory:
            if item_id in inventory_details:
                continue
            if detail := build_item_detail(item_id):
                inventory_details[item_id] = detail

        current_location = state.location_current
        location_inventory_raw = (
            state.location_inventory.get(current_location, {}) if current_location else {}
        ) or {}
        location_inventory = {
            item_id: count for item_id, count in location_inventory_raw.items() if count > 0
        }

        for item_id in location_inventory:
            if item_id in inventory_details:
                continue
            if detail := build_item_detail(item_id):
                inventory_details[item_id] = detail

        player_outfits = state.unlocked_outfits.get("player", []) if state.unlocked_outfits else []
        for outfit_id in player_outfits:
            if outfit_id in inventory_details:
                continue
            if detail := build_item_detail(outfit_id):
                inventory_details[outfit_id] = detail

        clothing_state = state.clothing_states.get("player") if state.clothing_states else None
        equipped_clothing: list[str] = []
        if isinstance(clothing_state, dict):
            slot_to_item = clothing_state.get("slot_to_item")
            if isinstance(slot_to_item, dict):
                equipped_clothing = sorted({
                    item_id for item_id in slot_to_item.values() if isinstance(item_id, str)
                })

        player_inventory_details = {
            item_id: inventory_details[item_id]
            for item_id in player_inventory
            if item_id in inventory_details
        }

        for outfit_id in player_outfits:
            if outfit_id in inventory_details:
                player_inventory_details[outfit_id] = inventory_details[outfit_id]

        location_inventory_details = {
            item_id: inventory_details[item_id]
            for item_id in location_inventory
            if item_id in inventory_details
        }

        summary = {
            "day": state.day,
            "time": state.time_slot,
            "location": self.engine.locations_map.get(
                state.location_current
            ).name if state.location_current in self.engine.locations_map else state.location_current,
            "location_id": state.location_current,
            "zone": state.zone_current,
            "meters": summary_meters,
            "flags": summary_flags,
            "modifiers": summary_modifiers,
            "present_characters": list(state.present_chars),
            "character_details": character_details,
            "player_details": player_details,
            "inventory": player_inventory,
            "inventory_details": player_inventory_details,
            "location_inventory": location_inventory,
            "location_inventory_details": location_inventory_details,
            "player_outfits": list(player_outfits),
            "player_current_outfit": (
                clothing_state.get("current_outfit") if isinstance(clothing_state, dict) else None
            ),
            "player_equipped_clothing": equipped_clothing,
            "turn_count": state.turn_count,
        }

        if state.time_hhmm:
            summary["time_hhmm"] = state.time_hhmm

        time_snapshot = {
            "day": state.day,
            "slot": state.time_slot,
            "time_hhmm": state.time_hhmm,
            "weekday": state.weekday,
            "mode": self.engine.game_def.time.mode.value if self.engine.game_def.time else "slots",
        }

        location_detail = {}
        current_location = self.engine.locations_map.get(state.location_current)
        if current_location:
            exits: list[dict] = []
            for connection in current_location.connections or []:
                targets = connection.to if isinstance(connection.to, list) else [connection.to]
                is_locked = bool(getattr(connection, "locked", False))
                if getattr(connection, "unlocked_when", None) and evaluator.evaluate(connection.unlocked_when):
                    is_locked = False

                for target_id in targets:
                    target_location = self.engine.locations_map.get(target_id)
                    is_discovered = target_id in state.discovered_locations
                    exits.append(
                        {
                            "direction": getattr(connection.direction, "value", connection.direction),
                            "to": target_id,
                            "name": target_location.name if target_location else target_id,
                            "discovered": is_discovered,
                            "available": is_discovered and not is_locked,
                            "locked": is_locked,
                            "description": getattr(connection, "description", None),
                        }
                    )

            # Build zone connections list
            zone_connections: list[dict] = []
            current_zone = self.engine.zones_map.get(state.zone_current)
            if current_zone and current_zone.connections:
                discovered_zones = set(state.discovered_zones or [])
                for connection in current_zone.connections:
                    dest_zone_ids = connection.to if isinstance(connection.to, list) else [connection.to]

                    for dest_zone_id in dest_zone_ids:
                        if dest_zone_id == "all" or dest_zone_id not in discovered_zones:
                            continue

                        dest_zone = self.engine.zones_map.get(dest_zone_id)
                        if not dest_zone:
                            continue

                        # Check access/locks
                        access = dest_zone.access if hasattr(dest_zone, 'access') else None
                        locked = access.locked if access else False
                        unlocked_when = access.unlocked_when if access else None
                        is_locked = locked and (not unlocked_when or not evaluator.evaluate(unlocked_when))

                        # Get available travel methods
                        available_methods = connection.methods if connection.methods else []
                        if not available_methods and self.engine.game_def.movement and self.engine.game_def.movement.methods:
                            # Use all game methods if connection doesn't specify
                            available_methods = [m.name for m in self.engine.game_def.movement.methods]

                        # Get entry locations based on use_entry_exit setting
                        entry_locations: list[dict] = []
                        if self.engine.game_def.movement and self.engine.game_def.movement.use_entry_exit:
                            # Only show designated entrances
                            if dest_zone.entrances:
                                for entry_loc_id in dest_zone.entrances:
                                    entry_loc = self.engine.get_location(entry_loc_id)
                                    if entry_loc:
                                        entry_locations.append({
                                            "id": entry_loc_id,
                                            "name": entry_loc.name
                                        })
                        else:
                            # Show all locations in the zone when use_entry_exit is false
                            for location in dest_zone.locations:
                                entry_locations.append({
                                    "id": location.id,
                                    "name": location.name
                                })

                        zone_connections.append({
                            "zone_id": dest_zone_id,
                            "zone_name": dest_zone.name,
                            "distance": connection.distance or 1.0,
                            "available_methods": available_methods,
                            "entry_locations": entry_locations,
                            "locked": is_locked,
                            "available": not is_locked,
                        })

            location_detail = {
                "id": current_location.id,
                "name": current_location.name,
                "zone": state.zone_current,
                "privacy": getattr(current_location.privacy, "value", current_location.privacy),
                "summary": current_location.summary,
                "description": getattr(current_location, "description", None),
                "has_shop": bool(getattr(current_location, "shop", None)),
                "exits": exits,
                "zone_connections": zone_connections,
            }
        else:
            location_detail = {
                "id": state.location_current,
                "name": state.location_current,
                "zone": state.zone_current,
                "privacy": getattr(state.location_privacy, "value", state.location_privacy),
                "summary": None,
                "description": None,
                "has_shop": False,
                "exits": [],
                "zone_connections": [],
            }

        player_snapshot = {
            "id": "player",
            "name": player_details["name"],
            "pronouns": player_details["pronouns"],
            "attire": player_details["wearing"],
            "meters": summary_meters.get("player", {}),
            "modifiers": summary_modifiers.get("player", []),
            "inventory": state.inventory.get("player", {}),
            "wardrobe_state": state.clothing_states.get("player"),
        }

        character_snapshots: list[dict] = []
        for char_id in state.present_chars:
            if char_id == "player":
                continue
            char_def = self.engine.characters_map.get(char_id)
            char_detail = character_details.get(char_id, {})
            character_snapshots.append(
                {
                    "id": char_id,
                    "name": char_detail.get("name") or (char_def.name if char_def else char_id),
                    "pronouns": char_detail.get("pronouns"),
                    "attire": char_detail.get("wearing"),
                    "meters": summary_meters.get(char_id, {}),
                    "modifiers": summary_modifiers.get(char_id, []),
                    "wardrobe_state": state.clothing_states.get(char_id),
                }
            )

        summary["snapshot"] = {
            "time": time_snapshot,
            "location": location_detail,
            "player": player_snapshot,
            "characters": character_snapshots,
        }

        economy = getattr(self.engine.game_def, "economy", None)
        if economy and economy.enabled:
            currency_name = economy.currency_name
            currency_symbol = economy.currency_symbol
            player_money = (
                summary_meters.get("player", {})
                .get("money", {})
                .get("value")
            )
            summary["economy"] = {
                "currency": currency_name,
                "symbol": currency_symbol,
                "player_money": player_money,
                "max_money": economy.max_money,
            }

        return summary

    def build_action_summary(self, action_description: str | None) -> str:
        """
        Produce a concise description of the player's action.
        Intended for UI display ahead of the narrative block.
        """
        if not action_description:
            return "Action taken"

        cleaned = action_description.strip()
        if not cleaned:
            return "Action taken"

        # Remove trailing period and capitalize
        cleaned = cleaned.rstrip(".")
        return cleaned[0].upper() + cleaned[1:]
