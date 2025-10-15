"""
PlotPlay Game Models.
Meters System
"""
from pydantic import Field
from .model import SimpleModel, DescriptiveModel, DSLExpression

class MeterThreshold(SimpleModel):
    """Meter threshold definition."""
    min: int
    max: int

class Meter(DescriptiveModel):
    """Meter definition with thresholds and visibility."""
    min: int = 0
    max: int = 100
    default: int = 0

    # Visibility and display
    visible: bool = True
    hidden_until: DSLExpression | None = None
    icon: str | None = None
    format: str | None = None

    # Decay and caps
    decay_per_day: int = 0
    decay_per_slot: int = 0
    delta_cap_per_turn: int | None = None

    # Named thresholds
    thresholds: list[MeterThreshold] | None = Field(default_factory=list)
