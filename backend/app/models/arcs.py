"""
PlotPlay Game Models.
Arc System.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from pydantic import Field, model_validator

from .model import DescriptiveModel, DSLExpression

if TYPE_CHECKING:
    from .effects import EffectsList
else:
    EffectsList = list


class ArcStage(DescriptiveModel):
    """Arc stage/milestone."""
    id: str
    title: str
    advance_when: DSLExpression | None = None
    advance_when_all: list[DSLExpression] | None = None
    advance_when_any: list[DSLExpression] | None = None
    once_per_game: bool = True

    on_enter: EffectsList = Field(default_factory=list)
    on_advance: EffectsList = Field(default_factory=list)

    @model_validator(mode='after')
    def validate_conditions(self):
        if sum(bool(x) for x in (self.advance_when, self.advance_when_any, self.advance_when_all)) != 1:
            raise ValueError(
                "Exactly one of 'when', 'when_any', or 'when_all' must be defined."
            )
        return self


class Arc(DescriptiveModel):
    """Story arc definition."""
    id: str
    title: str
    character: str
    category: str | None = None
    repeatable: bool = False
    stages: list[ArcStage] = Field(default_factory=list)


@dataclass
class ArcState:
    """Tracks arc stage and history."""
    stage: str | None = None
    history: list[str] = field(default_factory=list)
