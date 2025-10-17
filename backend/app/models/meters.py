"""
PlotPlay Game Models.
Meters System
"""
from typing import Literal, NewType
from pydantic import Field, model_validator
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
    format: Literal["integer", "percent", "currency"] | None = None

    # Decay and caps
    decay_per_day: int = 0
    decay_per_slot: int = 0
    delta_cap_per_turn: int | None = None

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


MeterId = NewType("MeterId", str)

MetersDefinition = dict[MeterId, Meter]


class MetersConfig(SimpleModel):
    """Meters configuration."""
    player: MetersDefinition | None = Field(default_factory=dict)
    template: MetersDefinition | None = Field(default_factory=dict)
