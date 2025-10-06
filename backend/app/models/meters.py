"""
PlotPlay v3 Game Models - Complete game definition structures.

 ============== Meter System ==============
"""

from pydantic import BaseModel, Field


class Meter(BaseModel):
    """Meter definition with thresholds and visibility."""
    min: int = 0
    max: int = 100
    default: int = 0
    visible: bool = True
    icon: str | None = None
    format: str | None = None
    decay_per_day: int = 0
    decay_per_slot: int = 0
    delta_cap_per_turn: int | None = None
    thresholds: dict[str, list[int]] | None = None
    hidden_until: str | None = None
