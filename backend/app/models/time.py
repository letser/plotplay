"""
PlotPlay Game Models.
Time System.
"""
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated
from pydantic import Field, field_validator, model_validator, StringConstraints
from .model import SimpleModel


TimeHHMM = Annotated[str, StringConstraints(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")]

class TimeMode(StrEnum):
    SLOTS = "slots"
    CLOCK = "clock"
    HYBRID = "hybrid"


class TimeSlotWindow(SimpleModel):
    """Time window for a slot in hybrid mode."""
    start: TimeHHMM
    end: TimeHHMM


class TimeStart(SimpleModel):
    """Starting time configuration."""
    day: int = 1
    slot: str | None = None
    time: TimeHHMM | None = None  # HH:MM for clock/hybrid


TimeSlots = list[str]

TimeSlotWindows = dict[str, TimeSlotWindow]


class Time(SimpleModel):
    """Complete time system configuration."""
    mode: TimeMode = TimeMode.SLOTS
    slots: TimeSlots | None = Field(default_factory=TimeSlots)
    actions_per_slot: int | None = None
    minutes_per_action: int | None = None
    slot_windows: TimeSlotWindows | None = Field(default_factory=TimeSlotWindows)

    week_days: list[str] = Field(default_factory=lambda: [
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
    ])
    start_day: str = "monday"

    @field_validator('start_day')
    @classmethod
    def validate_start_day(cls, v: str, info) -> str:
        """Ensure start_day is in the week_days list."""
        week_days = info.data.get('week_days', [])
        if v not in week_days:
            raise ValueError(f"start_day '{v}' must be one of {week_days}")
        return v

    @model_validator(mode='after')
    def validate_mode_requirements(self):
        """Ensure mode-specific requirements are satisfied."""
        slots = self.slots or []
        slot_windows = self.slot_windows or {}

        if self.actions_per_slot is not None and self.actions_per_slot <= 0:
            raise ValueError("actions_per_slot must be a positive integer.")

        if self.minutes_per_action is not None and self.minutes_per_action <= 0:
            raise ValueError("minutes_per_action must be a positive integer.")

        if self.mode in (TimeMode.SLOTS, TimeMode.HYBRID) and not slots:
            raise ValueError("slots mode requires at least one slot to be defined.")

        if self.mode in (TimeMode.CLOCK, TimeMode.HYBRID):
            if self.minutes_per_action is None:
                raise ValueError(
                    "clock and hybrid modes require 'minutes_per_action' to be set."
                )

        if self.mode == TimeMode.HYBRID:
            if not slot_windows:
                raise ValueError("hybrid mode requires 'slot_windows' to be defined.")
            missing_windows = [slot for slot in slots if slot not in slot_windows]
            if missing_windows:
                raise ValueError(
                    f"hybrid mode requires slot windows for all slots: missing {missing_windows}"
                )
        else:
            if slot_windows:
                raise ValueError(
                    "slot_windows may only be provided when mode is 'hybrid'."
                )

        return self


@dataclass
class TimeState:
    """Current in-game time snapshot."""
    day: int = 1
    slot: str | None = None
    time_hhmm: TimeHHMM | None = None
    weekday: str | None = None
