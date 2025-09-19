"""
PlotPlay v3 Game Models - Complete game definition structures.

 ============== Time System ==============
"""

from pydantic import BaseModel, Field

from app.models.enums import TimeMode

class TimeStart(BaseModel):
    """Starting time configuration."""
    day: int = 1
    slot: str | None = None
    time: str | None = None  # HH:MM for clock/hybrid


class SlotWindow(BaseModel):
    """Time window for a slot in hybrid mode."""
    start: str  # HH:MM
    end: str # HH:MM


class ClockConfig(BaseModel):
    """Clock configuration for time modes."""
    minutes_per_day: int = 1440
    slot_windows: dict[str, SlotWindow] | None = None


class CalendarConfig(BaseModel):
    """Calendar system for weeks."""
    epoch: str = "2025-01-01"
    week_days: list[str] = Field(default_factory=lambda: [
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
    ])
    start_day_index: int = 0
    weeks_enabled: bool = True


class TimeConfig(BaseModel):
    """Complete time system configuration."""
    mode: TimeMode = TimeMode.SLOTS
    slots: list[str] | None = None
    actions_per_slot: int = 3
    auto_advance: bool = True
    clock: ClockConfig | None = None
    start: TimeStart = Field(default_factory=TimeStart)