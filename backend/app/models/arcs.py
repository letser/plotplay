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
    def validate_advancement(self):
        """Ensure at least one advancement condition is defined."""
        if not (self.advance_when or self.advance_when_any or self.advance_when_all):
            raise ValueError(
                "Arc stage requires one of 'advance_when', 'advance_when_any', or 'advance_when_all'"
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
