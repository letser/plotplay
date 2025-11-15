"""
PlotPlay Game Models.
Inventory
"""
from dataclasses import dataclass, field

from pydantic import Field
from .model import SimpleModel, DSLExpression


class InventoryItem(SimpleModel):
    """Inventory item to represent an item, clothing item, or outfit."""
    id: str
    count: int = 1
    value: float | None = None
    infinite: bool = False
    discovered: bool = True
    discovered_when: DSLExpression | None = None


class Inventory(SimpleModel):
    """Inventory definition - combination of items, clothing items, and outfits."""
    items: dict[str, int] = Field(default_factory=dict)
    clothing: dict[str, int] = Field(default_factory=dict)
    outfits: dict[str, int] = Field(default_factory=dict)

@dataclass
class InventoryState:
    """Inventory state - runtime inventory representation."""
    items: dict[str, int] = field(default_factory=dict)
    clothing: dict[str, int] = field(default_factory=dict)
    outfits: dict[str, int] = field(default_factory=dict)

