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
                if flag_def.visible or evaluator.evaluate(flag_def.reveal_when):
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

        return summary
