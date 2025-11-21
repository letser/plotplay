"""Time utilities for the new runtime."""

from __future__ import annotations

from app.models.effects import MeterChangeEffect
from app.runtime.session import SessionRuntime


class TimeService:
    """Handles time advancement, slot recalculation, and meter decay."""

    def __init__(self, runtime: SessionRuntime) -> None:
        self.runtime = runtime

    def advance_minutes(self, minutes: int) -> dict:
        state = self.runtime.state_manager.state
        if minutes <= 0:
            return {"minutes": 0, "slot_advanced": False, "day_advanced": False}

        previous_slot = state.time.slot

        current_minutes = self._hhmm_to_minutes(state.time.time_hhmm or "00:00")
        total = current_minutes + minutes

        if total >= 24 * 60:
            self._trigger_day_end_effects()

        day_advanced = total >= 24 * 60
        total %= 24 * 60
        state.time.time_hhmm = self._minutes_to_hhmm(total)

        new_slot = self._resolve_slot(total, previous_slot)
        if new_slot is not None:
            state.time.slot = new_slot

        if day_advanced:
            state.time.day += 1
            self._trigger_day_start_effects()

        return {
            "minutes": minutes,
            "slot_advanced": (new_slot is not None and new_slot != previous_slot),
            "day_advanced": day_advanced,
        }

    def apply_meter_dynamics(self, *, day_advanced: bool, slot_advanced: bool) -> None:
        """Apply time-based meter decay."""
        if day_advanced:
            self._apply_meter_decay("day")
        if slot_advanced:
            self._apply_meter_decay("slot")

    def _apply_meter_decay(self, decay_type: str) -> None:
        state = self.runtime.state_manager.state
        index = self.runtime.index

        for char_id, char_state in state.characters.items():
            for meter_id, value in list(char_state.meters.items()):
                meter_def = index.player_meters.get(meter_id) if char_id == "player" else index.template_meters.get(meter_id)
                if not meter_def:
                    continue
                decay_value = 0
                if decay_type == "day" and getattr(meter_def, "decay_per_day", 0):
                    decay_value = meter_def.decay_per_day
                elif decay_type == "slot" and getattr(meter_def, "decay_per_slot", 0):
                    decay_value = meter_def.decay_per_slot
                if decay_value:
                    self.runtime.effect_resolver.apply_effects(
                        [MeterChangeEffect(target=char_id, meter=meter_id, op="add", value=decay_value, cap_per_turn=False)]
                    )

    def _resolve_slot(self, total_minutes: int, fallback: str | None) -> str | None:
        windows = getattr(self.runtime.game.time, "slot_windows", None) or {}
        for slot, window in windows.items():
            start = self._hhmm_to_minutes(window.start)
            end = self._hhmm_to_minutes(window.end)
            if start <= end:
                if start <= total_minutes <= end:
                    return slot
            else:  # wrap-around window
                if total_minutes >= start or total_minutes <= end:
                    return slot
        return fallback

    @staticmethod
    def _hhmm_to_minutes(value: str) -> int:
        hh, mm = map(int, value.split(":"))
        return (hh % 24) * 60 + mm

    @staticmethod
    def _minutes_to_hhmm(value: int) -> str:
        value %= 24 * 60
        return f"{value // 60:02d}:{value % 60:02d}"

    def _trigger_day_end_effects(self) -> None:
        effects = getattr(self.runtime.game.time, "day_end_effects", None) or getattr(self.runtime.game, "day_end_effects", None)
        if effects:
            self.runtime.effect_resolver.apply_effects(effects)

    def _trigger_day_start_effects(self) -> None:
        effects = getattr(self.runtime.game.time, "day_start_effects", None) or getattr(self.runtime.game, "day_start_effects", None)
        if effects:
            self.runtime.effect_resolver.apply_effects(effects)
