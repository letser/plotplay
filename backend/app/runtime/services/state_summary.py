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

        summary = {
            "turn": state.turn_count,
            "time": {
                "day": state.day,
                "slot": state.time.slot,
                "time_hhmm": state.time.time_hhmm,
            },
            "location": {
                "id": state.current_location,
                "zone": state.current_zone,
                "privacy": getattr(state.current_privacy, "value", None),
            },
            "present_characters": list(state.present_characters or []),
            "choices": [],
            "meters": {},
            "flags": {},
            "inventory": {},
        }

        # Player meters/flags (visible ones only)
        player_meters = game.meters.player or {}
        summary["meters"]["player"] = {
            meter_id: {
                "value": state.meters["player"].get(meter_id),
                "min": meter_def.min,
                "max": meter_def.max,
                "icon": meter_def.icon,
            }
            for meter_id, meter_def in player_meters.items()
            if meter_def.visible
        }

        for flag_id, flag_def in (game.flags or {}).items():
            if flag_def.visible or (flag_def.reveal_when and evaluator.evaluate(flag_def.reveal_when)):
                summary["flags"][flag_id] = state.flags.get(flag_id, flag_def.default)

        player_state = state.characters.get("player")
        if player_state:
            summary["inventory"]["player"] = dict(player_state.inventory.items)

        return summary
