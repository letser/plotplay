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
        state = self.engine.state_manager.state
        time_config = self.engine.game_def.time

        day_advanced = False
        slot_advanced = False

        original_day = state.day
        original_slot = state.time_slot

        minutes_passed = 0
        if time_config.mode in ("hybrid", "clock"):
            # Clock/hybrid modes track time in HH:MM
            minutes_passed = minutes if minutes is not None else (time_config.minutes_per_action or 10)
            time_cost = minutes_passed

            if time_cost != 0 and state.time_hhmm:
                current_hh, current_mm = map(int, state.time_hhmm.split(':'))
                total_minutes_today = current_hh * 60 + current_mm
                total_minutes_today += time_cost

                minutes_per_day = 24 * 60  # Standard day
                if total_minutes_today >= minutes_per_day:
                    state.day += 1
                    total_minutes_today %= minutes_per_day

                new_hh = total_minutes_today // 60
                new_mm = total_minutes_today % 60
                state.time_hhmm = f"{new_hh:02d}:{new_mm:02d}"

                if time_config.mode == "hybrid" and time_config.slot_windows:
                    new_slot_found = False
                    for slot, window in time_config.slot_windows.items():
                        start_hh, start_mm = map(int, window.start.split(':'))
                        end_hh, end_mm = map(int, window.end.split(':'))

                        if start_hh > end_hh:
                            if (
                                (new_hh > start_hh)
                                or (new_hh < end_hh)
                                or (new_hh == start_hh and new_mm >= start_mm)
                                or (new_hh == end_hh and new_mm <= end_mm)
                            ):
                                if state.time_slot != slot:
                                    state.time_slot = slot
                                    self.logger.info("Time slot advanced to '%s'.", slot)
                                new_slot_found = True
                                break
                        else:
                            if window.start <= state.time_hhmm <= window.end:
                                if state.time_slot != slot:
                                    state.time_slot = slot
                                    self.logger.info("Time slot advanced to '%s'.", slot)
                                new_slot_found = True
                                break
                    if not new_slot_found:
                        self.logger.warning("Could not find a slot for time %s", state.time_hhmm)

                self.logger.info("Time advanced by %s minutes to %s.", time_cost, state.time_hhmm)

        elif time_config.mode == "slots":
            state.actions_this_slot += 1
            minutes_passed = 10
            if time_config.slots and state.actions_this_slot >= time_config.actions_per_slot:
                state.actions_this_slot = 0
                current_slot_index = time_config.slots.index(state.time_slot)
                if current_slot_index + 1 < len(time_config.slots):
                    state.time_slot = time_config.slots[current_slot_index + 1]
                else:
                    state.day += 1
                    state.time_slot = time_config.slots[0]
                self.logger.info("Time slot advanced to '%s'.", state.time_slot)

        if state.day > original_day:
            day_advanced = True
            state.weekday = self.engine.state_manager.calculate_weekday()
            self.logger.info(
                "Day advanced to %s, weekday is %s",
                state.day,
                state.weekday,
            )

        if state.time_slot != original_slot:
            slot_advanced = True

        return TimeAdvance(
            day_advanced=day_advanced,
            slot_advanced=slot_advanced,
            minutes_passed=minutes_passed,
        )

    def apply_meter_dynamics(self, time_info: TimeAdvance) -> None:
        if time_info.day_advanced:
            self.apply_meter_decay("day")
        if time_info.slot_advanced:
            self.apply_meter_decay("slot")

    def apply_meter_decay(self, decay_type: Literal["day", "slot"]) -> None:
        state = self.engine.state_manager.state
        for char_id, meters in state.meters.items():
            for meter_id in list(meters.keys()):
                meter_def = self.engine._get_meter_def(char_id, meter_id)
                if not meter_def:
                    continue

                decay_value = 0
                if decay_type == "day" and meter_def.decay_per_day != 0:
                    decay_value = meter_def.decay_per_day
                elif decay_type == "slot" and meter_def.decay_per_slot != 0:
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

    def advance_slot(self, slots: int = 1) -> TimeAdvance:
        """Advance time by a number of slots (for slot-based time mode)."""
        state = self.engine.state_manager.state
        time_config = self.engine.game_def.time

        if time_config.mode != "slots" or not time_config.slots:
            self.logger.warning(
                "advance_slot called but time mode is not 'slots'. Current mode: %s",
                time_config.mode
            )
            # Fallback: estimate minutes
            estimated_minutes = slots * 240  # Rough estimate: 1 slot ≈ 4 hours
            return self.advance(minutes=estimated_minutes)

        day_advanced = False
        slot_advanced = False
        original_day = state.day
        original_slot = state.time_slot

        # Advance by the specified number of slots
        for _ in range(slots):
            current_slot_index = time_config.slots.index(state.time_slot) if state.time_slot in time_config.slots else 0

            if current_slot_index + 1 < len(time_config.slots):
                state.time_slot = time_config.slots[current_slot_index + 1]
            else:
                # Wrap around to next day
                state.day += 1
                state.time_slot = time_config.slots[0]

        # Reset actions counter for the new slot
        state.actions_this_slot = 0

        if state.day > original_day:
            day_advanced = True
            state.weekday = self.engine.state_manager.calculate_weekday()
            self.logger.info("Day advanced to %s, weekday is %s", state.day, state.weekday)

        if state.time_slot != original_slot:
            slot_advanced = True
            self.logger.info("Time slot advanced to '%s'.", state.time_slot)

        # Estimate minutes passed (for compatibility)
        minutes_passed = slots * 240  # Rough estimate

        return TimeAdvance(
            day_advanced=day_advanced,
            slot_advanced=slot_advanced,
            minutes_passed=minutes_passed,
        )
