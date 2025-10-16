"""
PlotPlay Game Models
Items
"""

from typing import Literal, NewType
from pydantic import Field
from .model import DescriptiveModel, DSLExpression, SimpleModel
from .effects import AnyEffect

ItemID = NewType("ItemID", str)

class Item(DescriptiveModel):
    """Item definition."""
    id: ItemID
    name: str
    category: str
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
    on_get: list[AnyEffect] = Field(default_factory=list)
    on_lost: list[AnyEffect] = Field(default_factory=list)
    on_use: list[AnyEffect] = Field(default_factory=list)
    on_gift: list[AnyEffect] = Field(default_factory=list)


class InventoryItem(SimpleModel):
    """Inventory item definition."""
    item: ItemID
    count: int = 1
    replenish:  bool = False
    discovered:  bool= True
    discovered_when: DSLExpression | None = None
