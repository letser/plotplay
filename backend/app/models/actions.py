"""
PlotPlay Game Models.
Actions.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from pydantic import Field

from .model import DescriptiveModel, DSLExpression, OptionalConditionalMixin

if TYPE_CHECKING:
    from .effects import EffectsList
else:
    EffectsList = list


class Action(OptionalConditionalMixin, DescriptiveModel):
    """A globally available, unlockable action."""
    id: str
    prompt: str
    category: str | None = None
    when: DSLExpression | None = None
    when_all: list[DSLExpression] | None = None
    when_any: list[DSLExpression] | None = None
    effects: EffectsList = Field(default_factory=list)
