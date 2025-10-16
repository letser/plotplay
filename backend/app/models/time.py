"""
PlotPlay Game Models.
Time System.
"""

from enum import StrEnum
from typing import NewType, Annotated
from pydantic import Field, field_validator, StringConstraints
from .model import SimpleModel


TimeSlot = NewType("TimeSlot", str)
TimeHHMM = Annotated[str, StringConstraints(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")]

class TimeMode(StrEnum):
    SLOTS = "slots"
    CLOCK = "clock"
    HYBRID = "hybrid"


class SlotWindow(SimpleModel):
    """Time window for a slot in hybrid mode."""
    start: str  # HH:MM
    end: str # HH:MM

WeekDay = NewType("WeekDay", str)


class TimeStart(SimpleModel):
    """Starting time configuration."""
    day: int = 1
    slot: str | None = None
    time: TimeHHMM | None = None  # HH:MM for clock/hybrid


class TimeConfig(SimpleModel):
    """Complete time system configuration."""
    mode: TimeMode = TimeMode.SLOTS
    slots: list[TimeSlot] | None = Field(default_factory=list)
    actions_per_slot: int = 5
    minutes_per_action: int = 30
    slot_windows: dict[TimeSlot, SlotWindow] | None = Field(default_factory=dict)

    week_days: list[WeekDay] = Field(default_factory=lambda: [
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
    ])
    start_day: WeekDay = "monday"

    @field_validator('start_day')
    @classmethod
    def validate_start_day(cls, v: str, info) -> str:
        """Ensure start_day is in the week_days list."""
        week_days = info.data.get('week_days', [])
        if v not in week_days:
            raise ValueError(f"start_day '{v}' must be one of {week_days}")
        return v
