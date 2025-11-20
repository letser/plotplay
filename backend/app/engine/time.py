"""Time management utilities for the PlotPlay engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TYPE_CHECKING

from app.models.effects import MeterChangeEffect

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine


@dataclass(slots=True)
class TimeAdvance:
    day_advanced: bool
    slot_advanced: bool
    minutes_passed: int


class TimeService:
    """Encapsulates time advancement and meter decay logic."""

    def __init__(self, engine: "GameEngine") -> None:
        self.engine = engine
        self.logger = engine.logger

    def advance(self, minutes: int | None = None) -> TimeAdvance:
        """
        Advance time by minutes or by one slot.

        If slot_windows are configured, tracks HH:MM time and updates slot based on windows.
        Otherwise, advances to next slot.
        """
        state = self.engine.state_manager.state
        time_config = self.engine.game_def.time

        day_advanced = False
        slot_advanced = False

        original_day = state.time.day
        original_slot = state.time.slot

        minutes_passed = minutes if minutes is not None else 10  # Default 10 minutes

        # If we have slot_windows, track time in HH:MM format
        if time_config.slot_windows and state.time.time_hhmm:
            if minutes_passed != 0:
                current_hh, current_mm = map(int, state.time.time_hhmm.split(':'))
                total_minutes_today = current_hh * 60 + current_mm
                total_minutes_today += minutes_passed

                minutes_per_day = 24 * 60  # Standard day
                if total_minutes_today >= minutes_per_day:
                    state.time.day += 1
                    total_minutes_today %= minutes_per_day

                new_hh = total_minutes_today // 60
                new_mm = total_minutes_today % 60
                state.time.time_hhmm = f"{new_hh:02d}:{new_mm:02d}"

                # Update slot based on current time
                self._update_slot_from_time()

                self.logger.info("Time advanced by %s minutes to %s.", minutes_passed, state.time.time_hhmm)

        # Otherwise, simple slot-based advancement
        elif time_config.slots:
            # Advance to next slot
            if state.time.slot and state.time.slot in time_config.slots:
                current_slot_index = time_config.slots.index(state.time.slot)
                if current_slot_index + 1 < len(time_config.slots):
                    state.time.slot = time_config.slots[current_slot_index + 1]
                else:
                    # Wrap to next day
                    state.time.day += 1
                    state.time.slot = time_config.slots[0]
            else:
                # No current slot, start at first slot
                state.time.slot = time_config.slots[0]

            self.logger.info("Time slot advanced to '%s'.", state.time.slot)

        # Check if day or slot advanced
        if state.time.day > original_day:
            day_advanced = True
            state.time.weekday = self._calculate_weekday()
            self.logger.info(
                "Day advanced to %s, weekday is %s",
                state.time.day,
                state.time.weekday,
            )

        if state.time.slot != original_slot:
            slot_advanced = True

        return TimeAdvance(
            day_advanced=day_advanced,
            slot_advanced=slot_advanced,
            minutes_passed=minutes_passed,
        )

    def _update_slot_from_time(self) -> None:
        """Update current slot based on HH:MM time and slot windows."""
        state = self.engine.state_manager.state
        time_config = self.engine.game_def.time

        if not time_config.slot_windows or not state.time.time_hhmm:
            return

        current_time = state.time.time_hhmm
        for slot, window in time_config.slot_windows.items():
            # Check if current time falls within this slot window
            if self._time_in_window(current_time, window.start, window.end):
                if state.time.slot != slot:
                    state.time.slot = slot
                    self.logger.info("Time slot updated to '%s' based on time %s.", slot, current_time)
                return

        self.logger.warning("Could not find a slot for time %s", current_time)

    def _time_in_window(self, time: str, start: str, end: str) -> bool:
        """Check if time falls within start-end window (handles wrap-around)."""
        if start <= end:
            # Normal window (e.g., 09:00 to 17:00)
            return start <= time <= end
        else:
            # Wrap-around window (e.g., 22:00 to 05:00)
            return time >= start or time <= end

    def _calculate_weekday(self) -> str:
        """Calculate weekday based on current day and start_day."""
        time_config = self.engine.game_def.time
        state = self.engine.state_manager.state

        if not time_config.week_days or not time_config.start_day:
            return "unknown"

        start_day_index = time_config.week_days.index(time_config.start_day)
        days_elapsed = state.time.day - 1  # day 1 is the start day
        current_day_index = (start_day_index + days_elapsed) % len(time_config.week_days)
        return time_config.week_days[current_day_index]

    def apply_meter_dynamics(self, time_info: TimeAdvance) -> None:
        """Apply meter decay based on time advancement."""
        if time_info.day_advanced:
            self.apply_meter_decay("day")
        if time_info.slot_advanced:
            self.apply_meter_decay("slot")

    def apply_meter_decay(self, decay_type: Literal["day", "slot"]) -> None:
        """Apply meter decay to all characters."""
        state = self.engine.state_manager.state

        for char_id, char_state in state.characters.items():
            for meter_id in list(char_state.meters.keys()):
                meter_def = self._get_meter_def(char_id, meter_id)
                if not meter_def:
                    continue

                decay_value = 0
                if decay_type == "day" and hasattr(meter_def, 'decay_per_day') and meter_def.decay_per_day != 0:
                    decay_value = meter_def.decay_per_day
                elif decay_type == "slot" and hasattr(meter_def, 'decay_per_slot') and meter_def.decay_per_slot != 0:
                    decay_value = meter_def.decay_per_slot

                if decay_value != 0:
                    self.engine.effect_resolver.apply_meter_change(
                        MeterChangeEffect(
                            target=char_id,
                            meter=meter_id,
                            op="add",
                            value=decay_value,
                        )
                    )
        self.logger.info("Applied '%s' meter decay.", decay_type)

    def _get_meter_def(self, char_id: str, meter_id: str):
        """Get meter definition for a character's meter."""
        # Check player meters
        if char_id == "player" and meter_id in self.engine.game_def.index.player_meters:
            return self.engine.game_def.index.player_meters[meter_id]

        # Check template meters for NPCs
        if char_id != "player" and meter_id in self.engine.game_def.index.template_meters:
            return self.engine.game_def.index.template_meters[meter_id]

        return None

    def advance_slot(self, slots: int = 1) -> TimeAdvance:
        """Advance time by a number of slots."""
        state = self.engine.state_manager.state
        time_config = self.engine.game_def.time

        if not time_config.slots:
            self.logger.warning("advance_slot called but no slots configured.")
            # Fallback: estimate minutes
            estimated_minutes = slots * 240  # Rough estimate: 1 slot ≈ 4 hours
            return self.advance(minutes=estimated_minutes)

        day_advanced = False
        slot_advanced = False
        original_day = state.time.day
        original_slot = state.time.slot

        # Advance by the specified number of slots
        for _ in range(slots):
            current_slot_index = time_config.slots.index(state.time.slot) if state.time.slot in time_config.slots else 0

            if current_slot_index + 1 < len(time_config.slots):
                state.time.slot = time_config.slots[current_slot_index + 1]
            else:
                # Wrap around to next day
                state.time.day += 1
                state.time.slot = time_config.slots[0]

        # Reset actions counter for the new slot
        state.actions_this_slot = 0

        if state.time.day > original_day:
            day_advanced = True
            state.time.weekday = self._calculate_weekday()
            self.logger.info("Day advanced to %s, weekday is %s", state.time.day, state.time.weekday)

        if state.time.slot != original_slot:
            slot_advanced = True
            self.logger.info("Time slot advanced to '%s'.", state.time.slot)

        # Estimate minutes passed (for compatibility)
        minutes_passed = slots * 240  # Rough estimate

        return TimeAdvance(
            day_advanced=day_advanced,
            slot_advanced=slot_advanced,
            minutes_passed=minutes_passed,
        )
