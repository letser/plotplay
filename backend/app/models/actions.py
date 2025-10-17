"""
PlotPlay Game Models.
Actions.
"""
from typing import NewType
from pydantic import Field

from .model import DescriptiveModel, DSLExpression
from .effects import EffectsList

ActionId = NewType("ActionId", str)

class Action(DescriptiveModel):
    """A globally available, unlockable action."""
    id: ActionId
    prompt: str
    category: str | None = None
    when: DSLExpression | None = None
    when_all: list[DSLExpression] | None = None
    when_any: list[DSLExpression] | None = None
    effects: EffectsList = Field(default_factory=list)
