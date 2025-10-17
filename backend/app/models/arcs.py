"""
PlotPlay Game Models.
Arc System.
"""

from typing import NewType
from pydantic import Field, model_validator

from .model import DescriptiveModel, DSLExpression
from .effects import EffectsList
from .characters import CharacterId

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


ArcId = NewType("ArcId", str)

class Arc(DescriptiveModel):
    """Story arc definition."""
    id: ArcId
    title: str
    character: CharacterId | None = None
    category: str | None = None
    repeatable: bool = False
    stages: list[ArcStage] = Field(default_factory=list)
