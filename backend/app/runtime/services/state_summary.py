"""
Spec-compliant state summary builder for PlotPlay runtime.
"""

from __future__ import annotations

from app.runtime.session import SessionRuntime


class StateSummaryService:
    """Constructs the public state snapshot returned to clients."""

    def __init__(self, runtime: SessionRuntime) -> None:
        self.runtime = runtime

    def build(self) -> dict:
        state = self.runtime.state_manager.state
        game = self.runtime.game
        evaluator = self.runtime.state_manager.create_evaluator()

        def _meters_for_character(char_id: str, values: dict) -> dict:
            meters: dict = {}
            meter_defs = self.runtime.index.player_meters if char_id == "player" else self.runtime.index.template_meters
            if not meter_defs:
                return meters
            for meter_id, meter_def in meter_defs.items():
                if not getattr(meter_def, "visible", True):
                    continue
                meters[meter_id] = {
                    "value": values.get(meter_id),
                    "min": meter_def.min,
                    "max": meter_def.max,
                    "icon": getattr(meter_def, "icon", None),
                    "format": getattr(meter_def, "format", None),
                }
            return meters

        flags: dict[str, dict] = {}
        for flag_id, flag_def in (game.flags or {}).items():
            if flag_def.visible or (flag_def.reveal_when and evaluator.evaluate(flag_def.reveal_when)):
                flags[flag_id] = {
                    "value": state.flags.get(flag_id, flag_def.default),
                    "label": flag_def.label or flag_id,
                }

        modifiers: dict[str, list] = {}
        for char_id, active_mods in state.modifiers.items():
            if active_mods:
                modifiers[char_id] = [mod.get("id") for mod in active_mods if mod.get("id")]

        inventory_snapshot: dict[str, dict] = {}
        for char_id, char_state in state.characters.items():
            inventory_snapshot[char_id] = dict(char_state.inventory.items)

        location_def = self.runtime.index.locations.get(state.current_location)
        summary = {
            "turn": state.turn_count,
            "time": {
                "day": state.day,
                "slot": state.time.slot,
                "time_hhmm": state.time.time_hhmm,
                "weekday": state.time.weekday,
            },
            "location": {
                "id": state.current_location,
                "name": getattr(location_def, "name", state.current_location),
                "zone": state.current_zone,
                "privacy": getattr(state.current_privacy, "value", None),
            },
            "present_characters": list(state.present_characters or []),
            "meters": {
                char_id: _meters_for_character(char_id, char_state.meters)
                for char_id, char_state in state.characters.items()
            },
            "flags": flags,
            "modifiers": modifiers,
            "inventory": inventory_snapshot,
            "discovered": {
                "zones": list(state.discovered_zones),
                "locations": list(state.discovered_locations),
            },
        }

        clothing_snapshot = {
            char_id: snapshot
            for char_id, snapshot in state.clothing_states.items()
            if snapshot
        }
        if clothing_snapshot:
            summary["clothing"] = clothing_snapshot

        economy = getattr(game, "economy", None)
        if economy and getattr(economy, "enabled", False):
            summary["economy"] = {
                "currency": economy.currency_name,
                "symbol": economy.currency_symbol,
            }

        return summary
