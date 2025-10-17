"""
PlotPlay Game Models
Items
"""

from typing import NewType
from pydantic import Field
from .model import DescriptiveModel, DSLExpression, SimpleModel
from .effects import EffectsList

ItemId = NewType("ItemId", str)

class Item(DescriptiveModel):
    """Item definition."""
    id: ItemId
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

    obtain_conditions: list[DSLExpression] = Field(default_factory=list)

    # Dynamic effects
    on_get: EffectsList = Field(default_factory=list)
    on_lost: EffectsList = Field(default_factory=list)
    on_use: EffectsList = Field(default_factory=list)
    on_give: EffectsList = Field(default_factory=list)


class InventoryItem(SimpleModel):
    """Inventory item definition."""
    item: ItemId
    count: int = 1
    replenish:  bool = False
    discovered:  bool= True
    discovered_when: DSLExpression | None = None
