"""
PlotPlay v3 Game Models - Complete game definition structures.

 ============== Time System ==============
"""

from pydantic import BaseModel, Field, field_validator

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
    """Calendar system for week tracking."""
    enabled: bool = False  # Off by default for backwards compatibility
    epoch: str = "2025-01-01"  # Reference date (optional, for flavor/documentation)
    week_days: list[str] = Field(default_factory=lambda: [
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
    ])
    start_day: str = "monday"  # What weekday is Day 1 of the game?

    @field_validator('start_day')
    @classmethod
    def validate_start_day(cls, v: str, info) -> str:
        """Ensure start_day is in the week_days list."""
        week_days = info.data.get('week_days', [
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
        ])
        if v not in week_days:
            raise ValueError(f"start_day '{v}' must be one of {week_days}")
        return v


class TimeConfig(BaseModel):
    """Complete time system configuration."""
    mode: TimeMode = TimeMode.SLOTS
    slots: list[str] | None = None
    actions_per_slot: int = 3
    auto_advance: bool = True
    clock: ClockConfig | None = None
    calendar: CalendarConfig | None = None  # New calendar configuration
    start: TimeStart = Field(default_factory=TimeStart)