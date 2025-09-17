"""
PlotPlay v3 Game Models - Complete game definition structures.

 ============== Time System ==============
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.enums import TimeMode

class TimeStart(BaseModel):
    """Starting time configuration."""
    day: int = 1
    slot: Optional[str] = None
    time: Optional[str] = None  # HH:MM for clock/hybrid


class SlotWindow(BaseModel):
    """Time window for a slot in hybrid mode."""
    start: str  # HH:MM
    end: str    # HH:MM


class ClockConfig(BaseModel):
    """Clock configuration for time modes."""
    minutes_per_day: int = 1440
    slot_windows: Optional[Dict[str, SlotWindow]] = None
    minutes_per_slot: Optional[Dict[str, int]] = None


class CalendarConfig(BaseModel):
    """Calendar system for weeks."""
    epoch: str = "2025-01-01"
    week_days: List[str] = Field(default_factory=lambda: [
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
    ])
    start_day_index: int = 0
    weeks_enabled: bool = False


class TimeConfig(BaseModel):
    """Complete time system configuration."""
    mode: TimeMode = TimeMode.SLOTS
    slots: Optional[List[str]] = None
    actions_per_slot: Optional[int] = 3
    auto_advance: bool = True
    clock: Optional[ClockConfig] = None
    calendar: Optional[CalendarConfig] = None
    start: TimeStart = Field(default_factory=TimeStart)