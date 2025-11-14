"""
PlotPlay Game Models.
Meters System
"""
from typing import Literal
from pydantic import Field, model_validator
from .model import SimpleModel, DescriptiveModel, DSLExpression


class MeterThreshold(SimpleModel):
    """Meter threshold definition."""
    min: int | float
    max: int | float


MeterFormat = Literal["integer", "percent", "currency"]

class Meter(DescriptiveModel):
    """Meter definition with thresholds and visibility."""
    min: int | float = 0
    max: int | float= 100
    default: int | float = 0

    # Visibility and display
    visible: bool = True
    hidden_until: DSLExpression | None = None
    icon: str | None = None
    format: MeterFormat | None = None

    # Decay and caps
    decay_per_day: int | float = 0
    decay_per_slot: int | float = 0
    delta_cap_per_turn: int | float | None = None

    # Named thresholds
    thresholds: dict[str, MeterThreshold] = Field(default_factory=dict)

    @model_validator(mode='after')
    def validate_ranges(self):
        """Ensure meter defaults and thresholds lie within bounds."""
        if self.min >= self.max:
            raise ValueError("Meter 'min' must be less than 'max'.")

        if not (self.min <= self.default <= self.max):
            raise ValueError("Meter 'default' must lie within [min, max].")

        for name, threshold in self.thresholds.items():
            if threshold.min > threshold.max:
                raise ValueError(f"Threshold '{name}' must have min <= max.")
            if threshold.min < self.min or threshold.max > self.max:
                raise ValueError(
                    f"Threshold '{name}' must lie within the meter bounds."
                )
        return self


Meters = dict[str, Meter]

class MetersTemplate(SimpleModel):
    """Meters configuration."""
    player: Meters | None = Field(default_factory=dict)
    template: Meters | None = Field(default_factory=dict)

MetersState = dict[str, int | float]