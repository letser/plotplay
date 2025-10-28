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
        evaluator = ConditionEvaluator(state, rng_seed=self.engine._get_turn_seed())

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

        player_inventory_details: dict[str, dict] = {}
        if player_inv := state.inventory.get("player"):
            for item_id, count in player_inv.items():
                if count > 0 and (item_def := self.engine.inventory.item_defs.get(item_id)):
                    player_inventory_details[item_id] = item_def.model_dump()

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
            "inventory": state.inventory.get("player", {}),
            "inventory_details": player_inventory_details,
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

            location_detail = {
                "id": current_location.id,
                "name": current_location.name,
                "zone": state.zone_current,
                "privacy": getattr(current_location.privacy, "value", current_location.privacy),
                "summary": current_location.summary,
                "description": getattr(current_location, "description", None),
                "has_shop": bool(getattr(current_location, "shop", None)),
                "exits": exits,
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
