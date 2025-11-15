"""
PlotPlay Game Models.
Arc System.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from pydantic import Field, model_validator

from .model import DescriptiveModel, DSLExpression, RequiredConditionalMixin

if TYPE_CHECKING:
    from .effects import EffectsList
else:
    EffectsList = list


class ArcStage(RequiredConditionalMixin, DescriptiveModel):
    """Arc stage/milestone."""
    id: str
    title: str
    when: DSLExpression | None = None
    when_all: list[DSLExpression] | None = None
    when_any: list[DSLExpression] | None = None
    once_per_game: bool = True

    on_enter: EffectsList = Field(default_factory=list)
    on_exit: EffectsList = Field(default_factory=list)


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
    id: str
    stage: str | None = None
    history: list[str] = field(default_factory=list) # list of passed stages
