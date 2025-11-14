"""
PlotPlay Game Models
Items
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from pydantic import Field

from .model import DescriptiveModel, DSLExpression, SimpleModel

if TYPE_CHECKING:
    from .effects import EffectsList
else:
    EffectsList = list


class Item(DescriptiveModel):
    """Item definition."""
    id: str
    name: str
    category: str | None = None
    icon: str | None = None

    # Economy
    value: float | None = None
    stackable: bool = True
    droppable: bool = True

    # Usage
    consumable: bool | None = False
    use_text: str | None = None

    can_give: bool | None = False

    #Locking
    locked: bool = False
    unlock_when: DSLExpression | None = None

    # Dynamic effects
    on_get: EffectsList = Field(default_factory=list)
    on_lost: EffectsList = Field(default_factory=list)
    on_use: EffectsList = Field(default_factory=list)
    on_give: EffectsList = Field(default_factory=list)

