"""
PlotPlay Game Models.
Arc System.
"""

from pydantic import Field

from .model import SimpleModel, DescriptiveModel, DSLExpression
from .effects import EffectsList
from .characters import CharacterId

class ArcStage(SimpleModel):
    """Arc stage/milestone."""
    id: str
    name: str
    advance_when: DSLExpression | None = None
    advance_when_all: list[DSLExpression] | None = None
    advance_when_any: list[DSLExpression] | None = None
    once_per_game: bool = True

    on_enter: EffectsList = Field(default_factory=list)
    on_advance: EffectsList = Field(default_factory=list)


class Arc(DescriptiveModel):
    """Story arc definition."""
    id: str
    name: str
    character: CharacterId | None = None
    category: str | None = None
    repeatable: bool = False
    stages: list[ArcStage] = Field(default_factory=list)

