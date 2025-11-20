"""
Placeholder time service for the new runtime engine.
"""

from __future__ import annotations

from app.runtime.session import SessionRuntime


class TimeService:
    """Handles time advancement and slot recalculation."""

    def __init__(self, runtime: SessionRuntime) -> None:
        self.runtime = runtime

    def advance_minutes(self, minutes: int) -> dict:
        state = self.runtime.state_manager.state
        if minutes <= 0:
            return {"minutes": 0, "slot_advanced": False, "day_advanced": False}

        previous_slot = state.time.slot

        current_minutes = self._hhmm_to_minutes(state.time.time_hhmm or "00:00")
        total = current_minutes + minutes
        day_advanced = total >= 24 * 60
        total %= 24 * 60
        state.time.time_hhmm = self._minutes_to_hhmm(total)

        new_slot = self._resolve_slot(total, previous_slot)
        if new_slot is not None:
            state.time.slot = new_slot

        if day_advanced:
            state.time.day += 1

        return {
            "minutes": minutes,
            "slot_advanced": (new_slot is not None and new_slot != previous_slot),
            "day_advanced": day_advanced,
        }

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
