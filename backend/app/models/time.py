"""
PlotPlay Game Models.
Time System.
"""
from dataclasses import dataclass, InitVar
from typing import Annotated
from pydantic import Field, field_validator, model_validator, StringConstraints
from .model import SimpleModel


TimeHHMM = Annotated[str, StringConstraints(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")]

class TimeSlotWindow(SimpleModel):
    """Time window for a slot in hybrid mode."""
    start: TimeHHMM
    end: TimeHHMM

class TimeStart(SimpleModel):
    """Starting time configuration."""
    day: int = 1
    time: TimeHHMM | None = None  # HH:MM for clock/hybrid


TimeSlotWindows = dict[str, TimeSlotWindow]

class TimeDurations(SimpleModel):
    """Default durations configuration."""
    conversation: str    # Default for chat turns
    choice: str          # Default for choices
    movement: str        # Default for local movement
    default: str         # Fallback for unspecified actions
    cap_per_visit: int   # Max minutes accumulated per node visit

class Time(SimpleModel):
    """Complete time system configuration."""
    slots_enabled: bool = True    # show slots in the UI or not
    start: TimeStart = Field(default_factory=TimeStart)
    slots: list[str] | None = None
    slot_windows: TimeSlotWindows | None = Field(default_factory=TimeSlotWindows)

    # Time categories with default durations in minutes
    categories: dict[str, int] = Field(default_factory=dict)
    # Default durations
    defaults: TimeDurations = Field(default_factory=TimeDurations)

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

        if self.slots_enabled and not slots:
            raise ValueError("Slots require at least one slot to be defined.")

        if self.slots_enabled:
            if not slot_windows:
                raise ValueError("Slots require 'slot_windows' to be defined.")
            missing_windows = [slot for slot in slots if slot not in slot_windows]
            if missing_windows:
                raise ValueError(
                    f"Slot windows must be defined for all slots: missing {missing_windows}"
                )
        return self


def calculate_time_slot(value: TimeHHMM, slots: list[str], slot_windows: TimeSlotWindows) -> str | None:
    """
        Finds the corresponding slot name for a given HH:MM time string,
        correctly handling normal and overnight slots.
        """
    if not slots or not slot_windows:
        return None
    for slot_name in slots:
        window = slot_windows.get(slot_name)

        if not window:
            continue

        # Check if it's a normal day slot or an overnight slot
        if window.start < window.end:
            # --- Case 1: Normal Slot (e.g., 08:00 to 12:00) ---
            # Logic: time >= start AND time < end
            if window.start <= value < window.end:
                return slot_name
        else:
            # --- Case 2: Overnight Slot (e.g., 22:00 to 04:00) ---
            # Logic: time >= start OR time < end
            if value >= window.start or value < window.end:
                return slot_name

    # If no matching slot is found
    return None


def calculate_weekday(value: int, start_day: str, week_days: list[str]) -> str | None:
    """Calculate the current weekday based on time configuration."""
    if not week_days:
        return None

    if start_day not in week_days:
        return None

    start_index = week_days.index(start_day)
    offset = (value - 1) % len(week_days)
    weekday = week_days[(start_index + offset) % len(week_days)]
    return weekday


@dataclass
class TimeState:
    """Current in-game time snapshot."""
    # InitVars are used to inject dependencies into the constructor.
    # This is the helper block to calculate the slot and weekday based on
    # the current day, time_hhmm and injected dependencies.
    slots: InitVar[list[str] | None] = None
    slot_windows: InitVar[TimeSlotWindows | None] = None
    week_days: InitVar[list[str] | None] = None
    start_day: InitVar[str | None] = None
    __slots: list[str] | None = None
    __slot_windows: TimeSlotWindows | None = None
    __week_days: list[str] | None = None
    __start_day: str | None = None

    # This is actually stored values
    day: int = 1
    slot: str | None = None
    time_hhmm: TimeHHMM | None = None
    weekday: str | None = None

    def __post_init__(
            self,
            slots: list[str] | None,
            slot_windows: TimeSlotWindows | None,
            week_days: list[str] | None,
            start_day: int | None,
    ):
        """
        This method runs after __init__ and receives the InitVars.
        We use it to assign them to our private attributes.
        """
        self.__slots = slots
        self.__slot_windows = slot_windows
        self.__week_days = week_days
        self.__start_day = start_day

    def _recalculate_slot(self):
        """
        A private helper to calculate the slot based on
        the current time_hhmm and injected dependencies.
        """
        # We must use object.__setattr__ to set 'slot'
        # to avoid triggering our custom __setattr__ again
        # and causing an infinite loop.
        new_slot = calculate_time_slot(self.time_hhmm, self.__slots, self.__slot_windows)
        object.__setattr__(self, 'slot', new_slot)

    def _recalculate_weekday(self):
        """
        A private helper to calculate the weekday based on
        the current day and injected dependencies.
        """
        # We must use object.__setattr__ to set 'slot'
        # to avoid triggering our custom __setattr__ again
        # and causing an infinite loop.
        new_weekday = calculate_weekday(self.day, self.__start_day, self.__week_days)
        object.__setattr__(self, 'weekday', new_weekday)

    def __setattr__(self, name: str, value):
        """
        This method intercepts *all* attribute assignments.
        E.g., state.time_hhmm = "10:30"
        """
        # Set the attribute normally.
        # We must use object.__setattr__ to avoid recursion.
        object.__setattr__(self, name, value)

        # Check if the attribute being changed is 'time_hhmm'.
        if name == 'time_hhmm' and hasattr(self, '_TimeState__slots') and hasattr(self, '_TimeState__slot_windows'):
            self._recalculate_slot()

        # Check if the attribute being changed is 'day'.
        if name == 'day' and hasattr(self, '_TimeState__week_days') and hasattr(self, '_TimeState__start_day'):
            self._recalculate_weekday()