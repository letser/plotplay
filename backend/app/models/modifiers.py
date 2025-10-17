"""
PlotPlay Game Models.
Modifiers System.
"""
from enum import StrEnum

from pydantic import Field
from typing import NewType
from .model import SimpleModel, DescriptiveModel, DSLExpression
from .effects import EffectsList
from .characters import BehaviorGateId
from .meters import MeterId

class MeterClamp(SimpleModel):
    min: int
    max: int

ModifierId = NewType("ModifierId", str)

class Modifier(DescriptiveModel):
    id: ModifierId
    group: str | None = None

    when: DSLExpression | None = None
    when_all: list[DSLExpression] | None = None
    when_any: list[DSLExpression] | None = None

    priority: int | None = None

    duration: int | None = None

    # Character overrides
    mixins: list[str] | None = Field(default_factory=list)
    dialogue_style: str | None = None

    # Gate rules
    disallow_gates: list[BehaviorGateId] = Field(default_factory=list)
    allow_gates: list[BehaviorGateId] = Field(default_factory=list)

    # Meter clamping
    clamp_meters: dict[MeterId, MeterClamp] | None = Field(default_factory=dict)

    # Events
    on_entry: EffectsList = Field(default_factory=list)
    on_exit: EffectsList = Field(default_factory=list)


class ModifierStacking(StrEnum):
    HIGHEST = "highest"
    LOWEST = "lowest"
    ALL = "all"

class ModifiersConfig(SimpleModel):
    stacking: dict[str, ModifierStacking] = Field(default_factory=dict)
    library: list[Modifier] = Field(default_factory=list)
