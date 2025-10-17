"""
PlotPlay Game Models.
Inventory
"""

from pydantic import Field
from .model import SimpleModel, DSLExpression
from .items import ItemId
from .wardrobe import ClothingId, OutfitId


class InventoryItemBase(SimpleModel):
    """Common fields for InventoryItem models."""
    count: int = 1
    value: float | None = None
    infinite: bool | None  = False
    discovered: bool | None = True
    discovered_when: DSLExpression | None = None


class InventoryItem(InventoryItemBase):
    id: ItemId

class InventoryClothingItem(InventoryItemBase):
    id: ClothingId

class InventoryOutfit(InventoryItemBase):
    id: OutfitId


class Inventory(SimpleModel):
    """Inventory definition - combination of Items, ClothingItems and Outfits."""
    items: list[InventoryItem] = Field(default_factory=list)
    clothing: list[InventoryClothingItem] = Field(default_factory=list)
    outfits: list[InventoryOutfit] = Field(default_factory=list)