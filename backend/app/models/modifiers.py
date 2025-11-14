"""
PlotPlay Game Models.
Modifiers System.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import Field
from typing import TYPE_CHECKING
from .model import SimpleModel, DescriptiveModel, DSLExpression, OptionalConditionalMixin

if TYPE_CHECKING:
    from .effects import EffectsList
else:
    EffectsList = list

class MeterClamp(SimpleModel):
    min: int | float
    max: int | float


class Modifier(OptionalConditionalMixin, DescriptiveModel):
    id: str
    group: str | None = None

    # No conditions at all or exactly one must be set
    when: DSLExpression | None = None
    when_all: list[DSLExpression] | None = None
    when_any: list[DSLExpression] | None = None

    priority: int | None = None

    duration: int | None = None

    # Character overrides
    mixins: list[str] | None = Field(default_factory=list)
    dialogue_style: str | None = None

    # Gate rules
    disallow_gates: list[str] = Field(default_factory=list)
    allow_gates: list[str] = Field(default_factory=list)

    # Meter clamping
    clamp_meters: dict[str, MeterClamp] | None = Field(default_factory=dict)

    # Events
    on_entry: EffectsList = Field(default_factory=list)
    on_exit: EffectsList = Field(default_factory=list)


class ModifierStacking(StrEnum):
    HIGHEST = "highest"
    LOWEST = "lowest"
    ALL = "all"

class Modifiers(SimpleModel):
    stacking: dict[str, ModifierStacking] = Field(default_factory=dict)
    library: list[Modifier] = Field(default_factory=list)
